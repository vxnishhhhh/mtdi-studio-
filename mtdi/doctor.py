"""`mtdi doctor`: is this machine ready to run MTDI? Run by the installer, safe to run any time.

Every check returns (name, status, detail) with status "ok", "warn" (works, something optional is
missing) or "fail" (MTDI will not work until it is fixed). Nothing is sent anywhere except a
local Ollama probe on 127.0.0.1.
GUIDE: add a check as a function returning that tuple, then list it in CHECKS.
"""
import importlib
import importlib.util
import json
import os
import pathlib
import platform
import shutil
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = ("dash", "flask", "werkzeug", "plotly", "numpy", "psutil", "requests", "qrcode", "cryptography")
SNAPSHOT_TARGET_MS = 100.0


def check_python():
    v = sys.version_info
    ok = v >= (3, 11)
    return "python", "ok" if ok else "fail", f"{platform.python_version()} ({'needs 3.11 or newer' if not ok else sys.executable})"


def check_packages():
    missing = [m for m in REQUIRED if importlib.util.find_spec(m) is None]
    if missing:
        return "packages", "fail", "missing " + ", ".join(missing) + " (re-run the installer)"
    return "packages", "ok", f"{len(REQUIRED)} required packages import"


def check_engine():
    try:
        from .engine import Engine
        from .project import normalise
        m = normalise({"project": {"id": "doctor"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "c", "keys": ["K"], "noise_floor": 0.1}]})
        clock = [0.0]
        engine = Engine(m, clock=lambda: clock[0])
        for n in range(50):
            clock[0] = n * 0.1
            engine.ingest_values("s", {"K": 20 + (n % 5) / 10})
        snap = engine.snapshot()
        assert snap is not None
    except Exception as error:   # any failure here means the core is broken on this machine
        return "engine", "fail", f"{type(error).__name__}: {error}"
    return "engine", "ok", "ingests and snapshots"


def check_speed(channels=128, packets=300):
    """Worst-case snapshot time (a new packet before each one) at 128 channels."""
    from .engine import Engine
    from .project import normalise
    m = normalise({"project": {"id": "bench"}, "sources": [{"id": "s", "adapter": "http"}],
                   "channels": [{"id": f"c{i}", "keys": [f"K{i}"], "noise_floor": 0.1} for i in range(channels)]})
    clock = [0.0]
    engine = Engine(m, clock=lambda: clock[0])

    def feed(n):
        clock[0] = n * 0.01
        engine.ingest_values("s", {f"K{i}": (n * 7 + i) % 100 / 10 for i in range(channels)})
    for n in range(packets):
        feed(n)
    engine.snapshot()
    total = 0.0
    for n in range(packets, packets + 5):
        feed(n)
        t = time.perf_counter()
        engine.snapshot()
        total += time.perf_counter() - t
    ms = total / 5 * 1000
    status = "ok" if ms <= SNAPSHOT_TARGET_MS else "warn"
    note = "" if status == "ok" else f"; above the {SNAPSHOT_TARGET_MS:.0f} ms target, fine for up to ~{int(channels * SNAPSHOT_TARGET_MS / ms)} channels"
    return "speed", status, f"{ms:.0f} ms per snapshot at {channels} channels{note}"


def check_studio():
    if not (ROOT / "run.py").exists():
        return "studio", "warn", "no studio interface in this copy (headless JSON API only)"
    if not (ROOT / "public" / "assets").is_dir():
        return "studio", "fail", "public/assets is missing; the interface would load without its scripts"
    return "studio", "ok", "interface present (start it with: mtdi studio)"


def check_serial():
    if importlib.util.find_spec("serial") is None:
        return "serial", "warn", "pyserial not installed; USB/UART sensors unavailable"
    ports = sorted(str(p) for pat in ("ttyUSB*", "ttyACM*", "ttyAMA*", "serial0", "cu.usb*") for p in pathlib.Path("/dev").glob(pat))
    return "serial", "ok", ("ports: " + ", ".join(ports)) if ports else "ready (no device plugged in)"


def check_local_model():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as r:
            models = [m.get("name") for m in json.loads(r.read()).get("models") or [] if isinstance(m, dict)]
        if models:
            return "local AI", "ok", "Ollama running with " + ", ".join(map(str, models[:3])) + "; NVTRA answers offline"
        return "local AI", "warn", "Ollama running but no model pulled (run: ollama pull llama3.2:3b)"
    except (OSError, ValueError, AttributeError):
        pass
    if shutil.which("ollama"):
        return "local AI", "warn", "Ollama installed but not running (start it: ollama serve)"
    keys = [k for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY") if os.environ.get(k)]
    if keys:
        return "local AI", "ok", "cloud model key set: " + ", ".join(keys)
    return "local AI", "warn", "no model; NVTRA uses its offline rules (still grounded, less fluent)"


def check_disk():
    free = shutil.disk_usage(ROOT).free / 2**30
    return "disk", "ok" if free >= 1 else "warn", f"{free:.1f} GB free"


CHECKS = (check_python, check_packages, check_engine, check_speed, check_studio, check_serial,
          check_local_model, check_disk)


def run(quick=False):
    results = []
    for check in CHECKS:
        if quick and check is check_speed:
            continue
        try:
            results.append(check())
        except Exception as error:
            results.append((check.__name__.removeprefix("check_"), "fail", f"{type(error).__name__}: {error}"))
        if results[-1][0] in ("python", "packages") and results[-1][1] == "fail":
            break                                  # nothing below can import
    return results


def main(quick=False):
    marks = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}
    results = run(quick=quick)
    print(f"MTDI doctor · {platform.node()} · {platform.machine()} · {platform.system()}")
    for name, status, detail in results:
        print(f"  [{marks[status]}] {name:<9} {detail}")
    failed = [r for r in results if r[1] == "fail"]
    print("ready" if not failed else f"{len(failed)} problem(s) to fix before MTDI will run")
    return 1 if failed else 0
