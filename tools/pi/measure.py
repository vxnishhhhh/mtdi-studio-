"""Measure what MTDI costs on this machine. Made for the Raspberry Pi 5; runs anywhere.

    python tools/pi/measure.py                 # prints a report, writes docs/results/pi-budget/<host>-<date>.{json,md}
    python tools/pi/measure.py --no-llm        # skip the local model test
    python tools/pi/measure.py --quick         # fewer repetitions (about 20 s)

Stdlib only, nothing installed, nothing sent anywhere except the local Ollama (if it runs).
GUIDE: add a measurement as a function returning a dict, then list it in main().
"""
import argparse
import datetime
import json
import os
import pathlib
import platform
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def machine():
    mem = None
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem = int(line.split()[1]) // 1024
    except OSError:
        pass
    model = None
    try:
        model = pathlib.Path("/proc/device-tree/model").read_text().strip("\x00\n ")
    except OSError:
        pass
    temp = None
    try:
        temp = int(pathlib.Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except (OSError, ValueError):
        pass
    return {"host": platform.node(), "model": model or platform.machine(), "python": platform.python_version(),
            "cpus": os.cpu_count(), "memory_mb": mem, "cpu_temp_c": temp, "os": platform.platform()}


def profile_imports(reps):
    """Cold start per Intelligence Profile: seconds to import its modules, and peak memory, in a fresh Python."""
    from mtdi.profiles import PROFILES
    code = ("import time,resource,importlib,sys;t=time.perf_counter();"
            "[importlib.import_module(m) for m in sys.argv[1:]];"
            "print(time.perf_counter()-t, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)")
    out = {}
    for name, prof in PROFILES.items():
        runs = []
        for _ in range(reps):
            res = subprocess.run([sys.executable, "-c", code, *prof["modules"]], cwd=ROOT,
                                 capture_output=True, text=True)
            if res.returncode:
                runs = None
                out[name] = {"error": (res.stderr.strip().splitlines() or ["failed"])[-1]}
                break
            seconds, rss = res.stdout.split()
            runs.append((float(seconds), int(rss)))
        if runs:
            out[name] = {"import_s": min(r[0] for r in runs),
                         "peak_mb": round(max(r[1] for r in runs) / (1024 if sys.platform != "darwin" else 1024 ** 2), 1)}
    return out


def engine_throughput(channels, packets):
    """Packets per second the engine ingests, and snapshot time, for a project with N scalar channels."""
    from mtdi.engine import Engine
    from mtdi.project import normalise
    m = normalise({"project": {"id": "bench"}, "sources": [{"id": "s", "adapter": "http"}],
                   "channels": [{"id": f"c{i}", "keys": [f"K{i}"], "noise_floor": 0.1} for i in range(channels)]})
    clock = [0.0]
    engine = Engine(m, clock=lambda: clock[0])
    t = time.perf_counter()
    for n in range(packets):
        clock[0] = n * 0.01
        engine.ingest_values("s", {f"K{i}": (n * 7 + i) % 100 / 10 for i in range(channels)})
    ingest = time.perf_counter() - t
    t = time.perf_counter()
    for _ in range(50):
        engine.snapshot()
    snap = (time.perf_counter() - t) / 50
    return {"channels": channels, "packets_per_s": round(packets / ingest), "snapshot_ms": round(snap * 1000, 2)}


def local_model(model):
    """Tokens per second from a local Ollama, if one is running. Reports its absence instead of failing."""
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    host = host if host.startswith("http") else "http://" + host
    body = json.dumps({"model": model, "prompt": "Explain a baseline in one sentence.", "stream": False,
                       "options": {"num_predict": 64}}).encode()
    try:
        req = urllib.request.Request(host.rstrip("/") + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001 - any failure means "not measured", and we say why
        return {"model": model, "measured": False, "why": f"{type(exc).__name__}: {exc}"}
    tokens, ns = data.get("eval_count") or 0, data.get("eval_duration") or 0
    load = (data.get("load_duration") or 0) / 1e9
    return {"model": model, "measured": True, "tokens_per_s": round(tokens / (ns / 1e9), 1) if ns else None,
            "load_s": round(load, 1), "tokens": tokens}


def render(r):
    m = r["machine"]
    out = [f"# MTDI budget · {m['model']} · {r['date']}", "",
           f"Measured with `tools/pi/measure.py` on {m['host']}: {m['cpus']} CPUs, {m['memory_mb']} MB RAM, "
           f"Python {m['python']}" + (f", CPU {m['cpu_temp_c']:.0f} °C at start" if m["cpu_temp_c"] else "") + ".", "",
           "## Cold start per profile", "", "| profile | import (s) | peak memory (MB) |", "|---|---|---|"]
    for name, p in r["profiles"].items():
        out.append(f"| {name} | {p['import_s']:.2f} | {p['peak_mb']} |" if "error" not in p else f"| {name} | error: {p['error']} | |")
    out += ["", "## Engine", "", "| channels | packets/s | snapshot (ms) |", "|---|---|---|"]
    out += [f"| {e['channels']} | {e['packets_per_s']} | {e['snapshot_ms']} |" for e in r["engine"]]
    llm = r.get("llm")
    if llm:
        out += ["", "## Local model", ""]
        out.append(f"{llm['model']}: {llm['tokens_per_s']} tokens/s, {llm['load_s']} s to load." if llm["measured"]
                   else f"{llm['model']}: not measured ({llm['why']}).")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--model", default=os.environ.get("MTDI_OLLAMA_MODEL", "llama3.2:3b"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "results" / "pi-budget"))
    args = ap.parse_args(argv)
    reps, packets = (1, 500) if args.quick else (3, 3000)
    result = {"date": datetime.date.today().isoformat(), "machine": machine(),
              "profiles": profile_imports(reps),
              "engine": [engine_throughput(n, packets) for n in (8, 32, 128)]}
    if not args.no_llm:
        result["llm"] = local_model(args.model)
    report = render(result)
    print(report)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{result['machine']['host'] or 'host'}-{result['date']}"
    (out / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / f"{stem}.md").write_text(report, encoding="utf-8")
    print(f"written: {out / stem}.json and .md")
    return result


if __name__ == "__main__":
    main()
