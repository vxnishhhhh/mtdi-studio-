"""Put MTDI inside another repository: `python -m mtdi adopt <dir>`.

This is how a new project becomes "heavily dependent on MTDI" instead of only
describing it: the framework is copied into the project, a manifest is created,
and the project's AI instructions are pointed at it.

    <dir>/
      mtdi/                 the MTDI package, copied verbatim (do not edit; re-adopt to upgrade)
      mtdi-project/         this project's MTDI manifest and firmware
        project.json
        README.md
      MTDI.md               how this repository uses MTDI
      AGENTS.md             gains an MTDI section (appended, never replaced)

Afterwards, from <dir>:  python -m mtdi run mtdi-project --simulate
"""
import json
import pathlib
import re
import shutil
import subprocess

from . import __version__

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "<!-- MTDI:BEGIN -->"


def _source_commit():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def adopt(target, project_id=None, name=None, force=False):
    target = pathlib.Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    project_id = project_id or re.sub(r"[^a-z0-9\-]", "-", target.name.lower()).strip("-") or "project"
    done = []

    vendored = target / "mtdi"
    if vendored.exists() and not force:
        raise FileExistsError(f"{vendored} exists; use --force to upgrade the vendored framework")
    if vendored.exists():
        shutil.rmtree(vendored)
    shutil.copytree(ROOT / "mtdi", vendored, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (vendored / "VENDORED.json").write_text(json.dumps(
        {"mtdi": __version__, "source": "https://github.com/vxnishhhhh/mtdi-studio", "commit": _source_commit(),
         "note": "Copied by `python -m mtdi adopt`. Do not edit here: improve MTDI Studio and re-adopt."}, indent=2) + "\n")
    done.append(f"copied MTDI {__version__} into {vendored}")

    proj = target / "mtdi-project"
    if not (proj / "project.json").exists():
        shutil.copytree(ROOT / "projects" / "_template", proj, dirs_exist_ok=True)
        manifest = json.loads((proj / "project.json").read_text(encoding="utf-8"))
        manifest["project"]["id"] = project_id
        manifest["project"]["name"] = name or "Title"
        (proj / "project.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        shutil.copytree(ROOT / "firmware", proj / "firmware", dirs_exist_ok=True)
        done.append(f"created {proj / 'project.json'} from the template")
    else:
        done.append(f"kept existing {proj / 'project.json'}")

    if (ROOT / "matlab" / "+mtdi").exists():
        shutil.copytree(ROOT / "matlab", target / "mtdi-matlab", dirs_exist_ok=True)
        done.append("copied the MATLAB toolbox into mtdi-matlab/")
    for doc in ("INTEGRATING.md", "docs/MANIFEST.md", "docs/AI.md", "firmware/PROTOCOL.md"):
        dest = target / "mtdi-docs" / pathlib.Path(doc).name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / doc, dest)
    done.append("copied the integration guide, manifest reference, AI playbook and protocol into mtdi-docs/")

    (target / "MTDI.md").write_text(_mtdi_md(project_id), encoding="utf-8")
    agents = target / "AGENTS.md"
    block = f"{MARK}\n{_agents_block()}\n<!-- MTDI:END -->\n"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    if MARK in text:
        text = re.sub(r"<!-- MTDI:BEGIN -->.*?<!-- MTDI:END -->\n?", block, text, flags=re.S)
    else:
        text = (text.rstrip() + "\n\n" if text else "") + block
    agents.write_text(text, encoding="utf-8")
    done.append("wrote MTDI.md and the MTDI section of AGENTS.md")

    req = target / "requirements.txt"
    lines = req.read_text(encoding="utf-8").splitlines() if req.exists() else []
    for dep in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if dep and dep.split("==")[0] not in {l.split("==")[0] for l in lines}:
            lines.append(dep)
    req.write_text("\n".join(lines) + "\n", encoding="utf-8")
    done.append("merged MTDI's requirements into requirements.txt")
    return done


def _mtdi_md(project_id):
    return f"""# This repository runs on MTDI {__version__}

MTDI (Microprocessing Technological Diagnostic Intelligence) is vendored in `mtdi/`.
This project's MTDI manifest is `mtdi-project/project.json`.

```bash
pip install -r requirements.txt
python -m mtdi check mtdi-project
python -m mtdi run mtdi-project --simulate      # interface at http://127.0.0.1:8050
python -m mtdi run mtdi-project                  # real sources
python -m mtdi run mtdi-project --headless       # JSON API only, for small boards
```

* How to map measurements: `mtdi-docs/INTEGRATING.md`
* Every manifest field: `mtdi-docs/MANIFEST.md`
* Firmware line format: `mtdi-docs/PROTOCOL.md`
* Rules for AI agents: `AGENTS.md` (MTDI section) and `mtdi-docs/AI.md`

Do not edit `mtdi/`. Improve MTDI Studio (https://github.com/vxnishhhhh/mtdi-studio) and
re-run `python -m mtdi adopt . --force` from a checkout of it to upgrade.
Project id: `{project_id}`.
"""


def _agents_block():
    return """## MTDI

This repository is built on MTDI 5.0 (vendored in `mtdi/`, manifest in `mtdi-project/`).

1. Every measurement, metric or event this project produces becomes an MTDI channel in
   `mtdi-project/project.json`. Follow `mtdi-docs/INTEGRATING.md` step by step.
2. Firmware prints MTDI protocol lines (`mtdi-docs/PROTOCOL.md`); software feeds MTDI through
   the `process`, `python` or `http` adapters. Do not write a parallel monitoring system.
3. Never edit `mtdi/`. If MTDI cannot express something, say so; it is fixed in MTDI Studio.
4. Never invent readings, constants or results. Simulated data stays labelled SIMULATED.
5. Verify with `python -m mtdi check mtdi-project` and `python -m mtdi run mtdi-project --simulate`."""
