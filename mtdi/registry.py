"""Registry of everything the Computational Core is built with (S1-02, ADR 0005, ADR 0007).

Two lists, both files first:

* integrations: `registry/integrations.json`, one record per external service (purpose,
  auth, cost, risks, fallback, last verified fact).
* modules: `mtdi.pillars.COMPUTATIONAL_MODULES`, every in-repo module, checked by import.

Status is derived, never typed in by hand, so it cannot go stale:

    configured   one of the record's env vars is set in this environment
    not set up   it needs env vars and none is set
    available    it needs no env var (an app, a local tool or a public feed)

`verified` is the only hand-written fact and must say when and how it was checked.
Owner rule (ops/inbox): anything whose cost says "paid" stays off unless the owner says so.

How to add one: append a record to registry/integrations.json with every REQUIRED field,
run `python -m mtdi registry`, and the tests will tell you what you forgot.
(Aether: they always forget `risks`. Everything has risks. Even this docstring.)
"""
import importlib
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "registry" / "integrations.json"
REQUIRED = ("id", "provider", "purpose", "area", "auth", "env", "permissions", "capabilities",
            "cost", "risks", "fallback", "verified")


def load_integrations(path=INTEGRATIONS):
    data = json.loads(pathlib.Path(path).read_text())
    records = data["integrations"]
    seen = set()
    for rec in records:
        missing = [k for k in REQUIRED if k not in rec]
        if missing:
            raise ValueError(f"integration {rec.get('id', '?')}: missing {', '.join(missing)}")
        if rec["id"] in seen:
            raise ValueError(f"integration {rec['id']}: duplicate id")
        seen.add(rec["id"])
    return records


def status(rec, environ=None):
    environ = os.environ if environ is None else environ
    if not rec["env"]:
        return "available"
    return "configured" if any(environ.get(k) for k in rec["env"]) else "not set up"


def paid(rec):
    return "paid" in rec["cost"].lower()


def check_modules():
    """Import every Computational Core module; returns [(area, module, ok, error)]."""
    from .pillars import COMPUTATIONAL_MODULES
    rows = []
    for area, modules in COMPUTATIONAL_MODULES.items():
        for name in modules:
            try:
                importlib.import_module(name)
                rows.append((area, name, True, ""))
            except Exception as exc:  # shown, not hidden: a missing optional dependency is a fact
                rows.append((area, name, False, f"{type(exc).__name__}: {exc}"))
    return rows


def snapshot(environ=None):
    """Everything, as plain data (used by `describe` and the studio)."""
    return {
        "integrations": [{**{k: r[k] for k in ("id", "provider", "area", "purpose", "cost", "fallback", "verified")},
                          "status": status(r, environ), "paid": paid(r)} for r in load_integrations()],
        "modules": [{"area": a, "module": m, "ok": ok, "error": e} for a, m, ok, e in check_modules()],
    }


def render(snap):
    lines = ["INTEGRATIONS"]
    for r in snap["integrations"]:
        flag = "  $" if r["paid"] else ""
        lines.append(f"  {r['status']:<11} {r['id']:<14} {r['area']:<10} {r['cost']}{flag}")
    lines.append("")
    lines.append("COMPUTATIONAL CORE MODULES")
    for m in snap["modules"]:
        lines.append(f"  {'ok' if m['ok'] else 'MISSING':<8} {m['module']}" + (f"  ({m['error']})" if m["error"] else ""))
    return "\n".join(lines)
