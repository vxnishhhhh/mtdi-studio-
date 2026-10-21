"""Capability records and runtime selection (S1-03, ADR 0006).

Every execution target describes itself in a capability record (registry/targets/*.json, or
`detect_host()` for the machine this runs on). From that record and a project's Intelligence
Profile, `select_runtime` picks how MTDI runs there, and always says why:

    line-protocol  the device only prints KEY=value lines; a host computes everything
    edge           the C++ SDK detectors run on the device itself (EWMA, CUSUM, ...)
    full           the whole Python framework runs on the target
    remote         the target streams to a studio or the cloud, which does the work

The rules are deliberately plain so a person can check them by hand (and so can a reviewer
bot at 3 a.m. — hi CodeRabbit). Memory thresholds are rough engineering estimates, not
benchmarks; S1-16 replaces them with numbers measured on the owner's Pi 5 and Mac.
"""
import json
import os
import pathlib
import platform
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGETS = ROOT / "registry" / "targets"
CLASSES = ("microcontroller", "edge-board", "single-board", "desktop", "cloud", "browser")
RUNTIMES = ("line-protocol", "edge", "full", "remote")
FIELDS = ("id", "name", "class", "memory_mb", "storage_mb", "float", "network", "os",
          "languages", "accelerators", "notes", "source")

# Minimum memory (MB) for the full Python runtime under each profile. Edge is small; Vision,
# Research and Autonomous hold images, datasets or language-model context. Estimates.
PROFILE_MIN_MB = {"edge": 256, "scientific": 1024, "hybrid": 1024, "vision": 2048,
                  "research": 2048, "autonomous": 2048}
EDGE_MIN_KB = 64          # C++ detectors plus buffers; an Uno's 2 KB cannot hold them


def validate(rec):
    missing = [k for k in FIELDS if k not in rec]
    if missing:
        raise ValueError(f"target {rec.get('id', '?')}: missing {', '.join(missing)}")
    if rec["class"] not in CLASSES:
        raise ValueError(f"target {rec['id']}: unknown class {rec['class']!r}")
    return rec


def load_targets(folder=TARGETS):
    return {r["id"]: r for r in (validate(json.loads(p.read_text())) for p in sorted(pathlib.Path(folder).glob("*.json")))}


def detect_host():
    """A capability record for the machine this code runs on (measured, not assumed)."""
    mem = None
    try:
        import psutil
        mem = psutil.virtual_memory().total / 2**20
    except Exception:
        if hasattr(os, "sysconf"):
            try:
                mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**20
            except (ValueError, OSError):
                pass
    disk = shutil.disk_usage(str(ROOT)).free / 2**20
    system, machine = platform.system().lower(), platform.machine().lower()
    langs = ["python"] + [name for exe, name in (("g++", "cpp"), ("octave", "octave"), ("node", "node"),
                                                   ("javac", "java"), ("matlab", "matlab")) if shutil.which(exe)]
    serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    cls = "cloud" if serverless else ("single-board" if machine in ("aarch64", "armv7l") and system == "linux"
                                      and pathlib.Path("/proc/device-tree/model").exists() else "desktop")
    return validate({"id": "host", "name": f"{platform.node() or 'this machine'} ({system} {machine})",
                     "class": cls, "memory_mb": round(mem or 0), "storage_mb": round(disk),
                     "float": "double", "network": ["detected"], "os": f"{system}-{machine}",
                     "languages": langs, "accelerators": [], "notes": "detected at runtime",
                     "source": "mtdi.capabilities.detect_host"})


def select_runtime(target, profile="hybrid"):
    """(runtime, reason) for running a project with `profile` on `target`."""
    if profile not in PROFILE_MIN_MB:
        raise ValueError(f"unknown profile {profile!r}; one of {', '.join(PROFILE_MIN_MB)}")
    cls, mem = target["class"], float(target["memory_mb"] or 0)
    if cls == "browser":
        return "remote", "a browser shows the interface; computation runs in a studio or the cloud"
    if "python" not in target["languages"]:
        if "cpp" in target["languages"] and mem * 1024 >= EDGE_MIN_KB and target["float"] != "software":
            return "edge", f"no Python, but {mem * 1024:.0f} KB RAM and hardware floats fit the C++ SDK detectors"
        return "line-protocol", (f"{mem * 1024:.0f} KB RAM" if mem < 1 else "no Python runtime") + \
            ": the device prints protocol lines and a host computes"
    need = PROFILE_MIN_MB[profile]
    if cls == "cloud" and profile in ("autonomous", "research"):
        return "remote", "serverless limits (60 s, state resets) cannot hold long agent or dataset jobs"
    if mem >= need:
        return "full", f"{mem:.0f} MB RAM meets the {profile} profile's {need} MB estimate"
    return "remote", f"{mem:.0f} MB RAM is below the {profile} profile's {need} MB estimate; stream to a larger host"


def matrix(profiles=None, targets=None):
    """{target_id: {profile: (runtime, reason)}} for every reference target."""
    targets = targets or load_targets()
    profiles = profiles or list(PROFILE_MIN_MB)
    return {tid: {p: select_runtime(t, p) for p in profiles} for tid, t in targets.items()}
