"""The Compatibility Laboratory (S1-05, ADR 0006): run what can honestly be run for each target,
then write docs/COMPATIBILITY.md from the results.

    python tools/compat/lab.py firmware --board arduino-uno     # compile every sketch for one board
    python tools/compat/lab.py core --label linux-x64            # the test suite on this machine
    python tools/compat/lab.py serverless                        # the studio as Vercel runs it
    python tools/compat/lab.py report                            # docs/COMPATIBILITY.md from the results

Each run writes one JSON file to docs/results/compat/ (or --out). The report reads those plus the
owner's hardware records (docs/results/compat/hardware/*.json) and keeps the evidence apart:
compiled (built, never run), emulated, ran (executed on a named machine of that kind, not the
owner's device) and tested on hardware. Only a hardware record can say "tested on hardware".
Stdlib only.
GUIDE: a new board is one BOARDS entry; a new ADR target row is one entry in target_rows().
"""
import argparse
import datetime
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs" / "results" / "compat"
REPORT = ROOT / "docs" / "COMPATIBILITY.md"

ESP32_INDEX = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"
BOARDS = {"arduino-uno": {"fqbn": "arduino:avr:uno", "core": "arduino:avr", "index": None},
          "esp32": {"fqbn": "esp32:esp32:esp32", "core": "esp32:esp32", "index": ESP32_INDEX}}
FLASH_WARN, RAM_WARN = 0.90, 0.75     # arduino-cli itself warns about stability above 75 % RAM
SKETCH_ROOTS = ("projects", "firmware", "sdk")
HARDWARE_FIELDS = ("target", "check", "result", "date", "by")
# Which capability records (mtdi/targets/) a hardware record can name for each ADR 0006 row.
ROW_TARGETS = {"Arduino-class (AVR)": ["arduino-uno"], "ESP32 + edge processing": ["esp32"],
               "Raspberry Pi + local AI": ["raspberry-pi-5", "raspberry-pi-4"],
               "Desktop scientific": ["desktop", "mac-m5"], "Cloud analysis": ["cloud-function"],
               "Software-only visual intelligence": []}


# ── firmware ───────────────────────────────────────────────────────────────────────────────

def sketches(root=ROOT):
    """Every Arduino sketch in the repository, as paths relative to root."""
    found = []
    for top in SKETCH_ROOTS:
        found += [p.relative_to(root) for p in (root / top).rglob("*.ino") if p.is_file()]
    return sorted(found)


def sketch_dir(ino, scratch):
    """The folder arduino-cli builds. It needs the sketch inside a folder of the same name; a sketch
    that is not gets copied into one under `scratch`, and the result says so."""
    ino = pathlib.Path(ino)
    if ino.parent.name == ino.stem:
        return ino.parent, None
    folder = pathlib.Path(scratch) / ino.stem
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(ino, folder / ino.name)
    return folder, "built from a copy in a folder of its own name (arduino-cli needs that)"


def sizes(compile_json):
    """{"flash": [used, max], "ram": [used, max]} from `arduino-cli compile --format json`."""
    sections = {s["name"]: s for s in (compile_json.get("builder_result") or {}).get("executable_sections_size") or []}
    out = {}
    for key, name in (("flash", "text"), ("ram", "data")):
        if name in sections:
            out[key] = [int(sections[name]["size"]), int(sections[name].get("max_size") or 0)]
    return out


def judge(success, used):
    """ok, warn (close to the board's limit), too-big or failed."""
    if not success:
        return "failed"
    status = "ok"
    for key, limit in (("flash", FLASH_WARN), ("ram", RAM_WARN)):
        size, most = used.get(key, (0, 0))
        if most and size > most:
            return "too-big"
        if most and size >= limit * most:
            status = "warn"
    return status


def build_firmware(board, cli="arduino-cli", root=ROOT, run=subprocess.run):
    spec = BOARDS[board]
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for rel in sketches(root):
            folder, note = sketch_dir(root / rel, scratch)
            cmd = [cli, "compile", "--fqbn", spec["fqbn"], "--format", "json", str(folder)]
            if spec["index"]:
                cmd += ["--additional-urls", spec["index"]]
            done = run(cmd, capture_output=True, text=True, timeout=900)
            try:
                result = json.loads(done.stdout or "{}")
            except ValueError:
                result = {}
            success = done.returncode == 0 and result.get("success", False)
            used = sizes(result)
            row = {"sketch": rel.as_posix(), "status": judge(success, used), **used}
            if note:
                row["note"] = note
            if not success:
                row["error"] = (result.get("compiler_err") or done.stderr or done.stdout or "")[-1500:].strip()
            rows.append(row)
    return {"kind": "firmware", "board": board, "fqbn": spec["fqbn"], "evidence": "compiled",
            "tool": tool_version(cli, run), "sketches": rows, **provenance()}


def setup_board(board, cli="arduino-cli", run=subprocess.run):
    """Install the board support a build needs (the workflow calls this; BOARDS is the one list)."""
    spec = BOARDS[board]
    urls = ["--additional-urls", spec["index"]] if spec["index"] else []
    for cmd in ([cli, "core", "update-index", *urls], [cli, "core", "install", spec["core"], *urls]):
        run(cmd, check=True, timeout=1800)


def tool_version(cli, run=subprocess.run):
    try:
        return run([cli, "version"], capture_output=True, text=True, timeout=60).stdout.strip()[:120]
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# ── core suite ─────────────────────────────────────────────────────────────────────────────

_TEST = re.compile(r"^(\w+) \(([\w.]+)\)")
_OUTCOME = re.compile(r" \.\.\. (ok|FAIL|ERROR|skipped '(.*)'|expected failure|unexpected success)\s*$")


def parse_unittest(text):
    """{"ran": n, "ok": bool, "tests": {id: outcome}, "skipped": {id: reason}} from `unittest -v`."""
    tests, skipped, current = {}, {}, None
    for line in text.splitlines():
        start = _TEST.match(line)
        if start:
            current = start.group(2)
        end = _OUTCOME.search(line)
        if end and current:
            outcome = "skipped" if end.group(1).startswith("skipped") else end.group(1)
            tests[current] = outcome
            if outcome == "skipped":
                skipped[current] = end.group(2)
            current = None
    ran = re.findall(r"^Ran (\d+) tests? in", text, re.M)
    verdict = re.findall(r"^(OK|FAILED)\b", text, re.M)
    return {"ran": int(ran[-1]) if ran else 0, "ok": bool(verdict) and verdict[-1] == "OK",
            "tests": tests, "skipped": skipped}


def run_core(label, root=ROOT, run=subprocess.run):
    done = run([sys.executable, "-m", "unittest", "discover", "tests", "-v"], cwd=root,
               capture_output=True, text=True, timeout=3600)
    parsed = parse_unittest(done.stderr + done.stdout)
    failed = sorted(t for t, o in parsed["tests"].items() if o in ("FAIL", "ERROR", "unexpected success"))
    return {"kind": "core", "target": label, "evidence": "ran", "python": platform.python_version(),
            "ran": parsed["ran"], "ok": parsed["ok"] and done.returncode == 0, "failed": failed,
            "skipped": parsed["skipped"], "checks": {k: parsed["tests"].get(v, "not run") for k, v in CHECKS.items()},
            **provenance()}


# The tests that prove a target-specific claim; the report names them per machine.
CHECKS = {"cpp-sdk-matches-python": "test_sdks.SDKs.test_cpp",
          "octave-matches-python": "test_sdks.SDKs.test_matlab_fusion_calibration_drift_match_python",
          "studio-ingest-serverless": "test_backend.StudioIngest.test_samples_reach_every_channel"}


# ── serverless studio ──────────────────────────────────────────────────────────────────────

SMOKE = r'''
import json, os, sys, time
sys.path.insert(0, os.getcwd())
import app as entry
client, checks = entry.app.test_client(), {}
page = client.get("/")
checks["page"] = page.status_code == 200 and b"<html" in page.data.lower()
checks["ingest refused without the token"] = client.post("/api/ingest", json={"ch2": 1}).status_code == 403
auth = {"Authorization": "Bearer " + os.environ["STUDIO_INGEST_TOKEN"]}
replies = [client.post("/api/ingest", headers=auth, json={"source": "COMPAT", "ch2": 5 + i * 0.01}).get_json()
           for i in range(12)]
checks["ingest with the token"] = all(r == {"ok": True, "accepted": 1} for r in replies)
state = client.get("/api/instrument").get_json()["channels"]["ch2"]["state"]
checks["instrument shows the fed channel"] = state == "connected"
started = time.monotonic()
stream = client.get("/api/events")
body = b"".join(stream.response)
seconds = time.monotonic() - started
checks["event stream ends on its own"] = seconds < 20 and body.startswith(b"retry:")
entry.NAMESPACE["LIFECYCLE"].stop()
print("SMOKE " + json.dumps({"checks": checks, "stream_seconds": round(seconds, 1)}))
sys.stdout.flush()
os._exit(0)
'''


def run_serverless(root=ROOT, run=subprocess.run):
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, STUDIO_SERVERLESS="1", STUDIO_INGEST_TOKEN="compat-lab", HOME=home,
                   STUDIO_STATE_DIR=str(pathlib.Path(home, "state")), STUDIO_HTTPS_PORT="0")
        done = run([sys.executable, "-c", SMOKE], cwd=root, env=env, capture_output=True, text=True, timeout=600)
    lines = [line for line in done.stdout.splitlines() if line.startswith("SMOKE ")]
    smoke = json.loads(lines[-1][6:]) if lines else {}
    checks = smoke.get("checks", {})
    result = {"kind": "serverless", "target": "cloud", "evidence": "ran", "checks": checks,
              "stream_seconds": smoke.get("stream_seconds"), "ok": bool(checks) and all(checks.values()),
              **provenance()}
    if not lines:
        result["error"] = (done.stderr or done.stdout)[-1500:].strip()
    return result


# ── provenance, records, report ────────────────────────────────────────────────────────────

def provenance():
    if os.environ.get("GITHUB_ACTIONS"):
        where = f"GitHub Actions {os.environ.get('ImageOS') or os.environ.get('RUNNER_OS', '')} {os.environ.get('RUNNER_ARCH', '')}".strip()
        commit = os.environ.get("GITHUB_SHA", "")[:7]
    else:
        where = os.environ.get("COMPAT_WHERE") or f"local run, {platform.system()} {platform.machine()}"
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30).stdout.strip()
            # The lab's own output does not count; any other uncommitted change does.
            dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!docs/results/compat",
                                    ":!docs/COMPATIBILITY.md"], cwd=ROOT, capture_output=True, text=True,
                                   timeout=30).stdout.strip()
            commit += " + uncommitted changes" if commit and dirty else ""
        except (OSError, subprocess.SubprocessError):
            commit = ""
    return {"where": where, "when": datetime.date.today().isoformat(), "commit": commit}


def hardware_records(folder):
    """The owner's recorded runs on real devices. Each needs target, check, result, date and by."""
    records = []
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in HARDWARE_FIELDS if not str(record.get(k) or "").strip()]
        if missing:
            raise ValueError(f"{path.name}: a hardware record needs {', '.join(missing)}")
        known = sorted({t for ids in ROW_TARGETS.values() for t in ids})
        if record["target"] not in known:
            raise ValueError(f"{path.name}: unknown target {record['target']!r}; one of {', '.join(known)}")
        records.append(record)
    return records


def load_results(folder):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pathlib.Path(folder).glob("*.json"))]


def _bytes(pair):
    return f"{pair[0]:,} / {pair[1]:,} B" if pair else "—"


def _firmware_cell(result):
    if not result:
        return "not built yet", "—"
    rows = result["sketches"]
    good = [r for r in rows if r["status"] in ("ok", "warn")]
    worst = max(rows, key=lambda r: (r.get("flash") or [0, 1])[0] / max((r.get("flash") or [0, 1])[1], 1), default=None)
    text = f"{len(good)}/{len(rows)} sketches build for `{result['fqbn']}`"
    if worst and worst.get("flash"):
        text += f"; largest {_bytes(worst['flash'])} flash, {_bytes(worst.get('ram'))} RAM"
    return text, "compiled"


def _core_cell(results):
    if not results:
        return "not run yet", "—"
    parts = [f"{r['target']}: {'passed' if r['ok'] else 'FAILED'} ({r['ran']} tests, {len(r['skipped'])} skipped)"
             for r in results]
    return "; ".join(parts), "ran"


def target_rows(results, hardware):
    """The ADR 0006 table: one row per target, from whatever results exist."""
    firmware = {r["board"]: r for r in results if r["kind"] == "firmware"}
    core = {r["target"]: r for r in results if r["kind"] == "core"}
    serverless = next((r for r in results if r["kind"] == "serverless"), None)
    on_hw = {}
    for rec in hardware:
        on_hw.setdefault(rec["target"], []).append(f"{rec['check']}: {rec['result']} ({rec['date']}, {rec['by']})")

    def check(name):
        seen = {r["target"]: r["checks"].get(name, "not run") for r in core.values()}
        return ", ".join(f"{t} {o}" for t, o in sorted(seen.items())) or "not run yet"

    rows = []
    text, evidence = _firmware_cell(firmware.get("arduino-uno"))
    rows.append(("Arduino-class (AVR)", text, evidence))
    text, evidence = _firmware_cell(firmware.get("esp32"))
    rows.append(("ESP32 + edge processing",
                 f"{text}. C++ SDK detectors match Python on the host: {check('cpp-sdk-matches-python')}",
                 evidence + (", ran" if core else "")))
    pi = [core[t] for t in sorted(core) if "arm64" in t and t.startswith("linux")]
    text, evidence = _core_cell(pi)
    rows.append(("Raspberry Pi + local AI",
                 f"core suite on Linux ARM64: {text}. Local AI against a small model: not exercised in CI yet",
                 evidence))
    text, evidence = _core_cell([core[t] for t in sorted(core)])
    rows.append(("Desktop scientific", f"{text}. Octave matches Python: {check('octave-matches-python')}", evidence))
    if serverless:
        failed = [k for k, ok in serverless["checks"].items() if not ok]
        text = ("serverless studio: " + ("all %d checks passed" % len(serverless["checks"]) if serverless["ok"]
                                          else "FAILED: " + (", ".join(failed) or serverless.get("error", "no output")[:200])))
        evidence = "ran"
    else:
        text, evidence = "serverless studio: not run yet", "—"
    rows.append(("Cloud analysis", text + ". Live Vercel deployment: not checked by the lab", evidence))
    rows.append(("Software-only visual intelligence", "not exercised: the repository has no Vision-profile "
                 "pipeline or recorded images yet", "—"))
    out = []
    for name, text, evidence in rows:
        hw = "; ".join(x for t in ROW_TARGETS[name] for x in on_hw.get(t, [])) or "none recorded"
        out.append((name, text, evidence, hw))
    return out


def report(results, hardware, runtimes):
    lines = ["# Compatibility", "",
             "Generated by `python tools/compat/lab.py report` from `docs/results/compat/`. Do not edit by hand.", "",
             "Evidence: **compiled** (built for the target, never run) · **emulated** · **ran** (executed on a named "
             "machine of that kind, not the owner's device) · **tested on hardware** (a recorded run on a real device). "
             "Only a record in `docs/results/compat/hardware/` puts anything in the hardware column.", "",
             "CI runs the same commands (`.github/workflows/compat.yml`) on every pull request and nightly; "
             "each run's summary holds its own report. This file is the last run recorded in the repository.", "",
             "## Targets (ADR 0006)", "", "| Target | What the lab ran | Evidence | Tested on hardware |",
             "|---|---|---|---|"]
    lines += [f"| {n} | {t} | {e} | {h} |" for n, t, e, h in target_rows(results, hardware)]

    firmware = [r for r in results if r["kind"] == "firmware"]
    if firmware:
        lines += ["", "## Firmware", "", "| Sketch | Board | Result | Flash | RAM |", "|---|---|---|---|---|"]
        for r in sorted(firmware, key=lambda r: r["board"]):
            for s in r["sketches"]:
                status = s["status"] + (f" ({s['note']})" if s.get("note") else "")
                lines.append(f"| `{s['sketch']}` | {r['board']} | {status} | {_bytes(s.get('flash'))} | {_bytes(s.get('ram'))} |")
        errors = [(r["board"], s) for r in firmware for s in r["sketches"] if s.get("error")]
        for board, s in errors:
            lines += ["", f"`{s['sketch']}` on {board}:", "", "```", s["error"], "```"]

    core = sorted((r for r in results if r["kind"] == "core"), key=lambda r: r["target"])
    if core:
        lines += ["", "## Core suite", "", "| Machine | Python | Tests | Result | Skipped |", "|---|---|---|---|---|"]
        for r in core:
            skipped = "; ".join(f"{t.split('.')[-1]} ({why})" for t, why in sorted(r["skipped"].items())) or "none"
            result = "passed" if r["ok"] else "FAILED: " + ", ".join(t.split(".")[-1] for t in r["failed"])
            lines.append(f"| {r['target']} | {r['python']} | {r['ran']} | {result} | {skipped} |")

    serverless = [r for r in results if r["kind"] == "serverless"]
    if serverless:
        lines += ["", "## Serverless studio", ""]
        lines += [f"- {'passed' if ok else 'FAILED'}: {name}" for name, ok in serverless[-1]["checks"].items()]
        if serverless[-1].get("error"):
            lines += ["", "```", serverless[-1]["error"], "```"]

    profiles = list(next(iter(runtimes.values()), {}))
    lines += ["", "## What MTDI would choose on each target", "",
              "From the capability records in `mtdi/targets/` (`mtdi.capabilities.select_runtime`). "
              "A choice, not a test result.", "",
              "| Target | " + " | ".join(profiles) + " |", "|---|" + "---|" * len(profiles)]
    lines += [f"| {t} | " + " | ".join(runtimes[t][p][0] for p in profiles) + " |" for t in sorted(runtimes)]

    lines += ["", "## Runs", "", "| Result | Where | When | Commit |", "|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (r["kind"], r.get("board") or r.get("target", ""))):
        lines.append(f"| {r['kind']} {r.get('board') or r.get('target', '')} | {r['where']} | {r['when']} | {r['commit'] or '—'} |")
    return "\n".join(lines) + "\n"


def write(result, out, name):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out / name


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    fw = sub.add_parser("firmware", help="compile every sketch for one board")
    fw.add_argument("--board", choices=sorted(BOARDS), required=True)
    fw.add_argument("--cli", default="arduino-cli")
    setup = sub.add_parser("setup", help="install the board support for one board")
    setup.add_argument("--board", choices=sorted(BOARDS), required=True)
    setup.add_argument("--cli", default="arduino-cli")
    core = sub.add_parser("core", help="the test suite on this machine")
    core.add_argument("--label", required=True, help="e.g. linux-x64, linux-arm64, macos-arm64, windows-x64")
    sub.add_parser("serverless", help="the studio as a serverless host runs it")
    rep = sub.add_parser("report", help="write docs/COMPATIBILITY.md from the results")
    rep.add_argument("--report", default=str(REPORT))
    rep.add_argument("--check", action="store_true", help="fail if the report on disk is out of date")
    for p in (fw, core, sub.choices["serverless"], rep):
        p.add_argument("--out", default=str(RESULTS), help="results folder")
    args = parser.parse_args(argv)

    if args.command == "setup":
        setup_board(args.board, args.cli)
        return 0
    if args.command == "firmware":
        result = build_firmware(args.board, args.cli)
        print(write(result, args.out, f"firmware-{args.board}.json"))
        bad = [s for s in result["sketches"] if s["status"] in ("failed", "too-big")]
        for s in bad:
            print(f"{s['sketch']}: {s['status']}\n{s.get('error', '')}", file=sys.stderr)
        return 1 if bad else 0
    if args.command == "core":
        result = run_core(args.label)
        print(write(result, args.out, f"core-{args.label}.json"))
        return 0 if result["ok"] else 1
    if args.command == "serverless":
        result = run_serverless()
        print(write(result, args.out, "serverless.json"))
        return 0 if result["ok"] else 1
    sys.path.insert(0, str(ROOT))
    from mtdi.capabilities import matrix
    text = report(load_results(args.out), hardware_records(pathlib.Path(args.out) / "hardware"), matrix())
    target = pathlib.Path(args.report)
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            print(f"{target} is out of date: run python tools/compat/lab.py report", file=sys.stderr)
            return 1
        return 0
    target.write_text(text, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
