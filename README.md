# MTDI Studio · MTDI 5.0

**Microprocessing Technological Diagnostic Intelligence.** MTDI is a set of pillars that
work together to tell you whether a system's measurements can be trusted, what the
environment around them looks like, and what is happening, for any hardware,
firmware or software that produces numbers.

MTDI Studio is MTDI 5.0 as a working system: every pillar implemented, wired together,
and driven by one manifest per project. A project joins MTDI by writing a
`project.json`. It does not need new code. Every project integrated makes the studio
better for the next.

```
  firmware (any board)        software (any program)        recordings
        │  KEY=value lines           │  HTTP / Python             │  JSONL
        └──────────────┬─────────────┴───────────────┬────────────┘
                       ▼                              ▼
                  adapters: serial · tcp · http · python · replay · simulator
                       ▼
   00  Validation Chamber           presence · freshness · timing · range · LOD/LOQ
   01  Environmental Intelligence   learn · lock · compare the real environment
                       ▼
              MTDI core: 8 weighted factors per channel → one score you can take apart
                       ▼
   02  NVTRA        plain-language interpretation, grounded answers
   03  I³           the interface everything is seen through
   04  Aether       purpose and authorship (non-functional)
```

## Run it

```bash
pip install -r requirements.txt
python -m mtdi run projects/inductra-vaion --simulate     # no hardware needed
python -m mtdi run projects/ultrasonic-room --simulate    # a non-electromagnetic project
python -m mtdi run projects/inductra-vaion --host 0.0.0.0 # real Uno on USB, or Inductra's Mac bridge on :8765
python -m unittest discover tests                         # 19 tests, standard library only
```

Open `http://127.0.0.1:8050`. Other commands: `python -m mtdi check|new|parse|packet`
(see `python -m mtdi -h`).

## Projects

| Project | Status | What it proves |
|---|---|---|
| [`inductra-vaion`](projects/inductra-vaion) | Integrated (project 1) | Inductra's own firmware and Mac bridge run unchanged on MTDI |
| [`ultrasonic-room`](projects/ultrasonic-room) | Example | The same pillars serve a sensor that is not electromagnetic |
| AstroTech | Next, not started | Will be created with `python -m mtdi new astrotech` |

**Inductra Vaion is its own repository and is not modified here.** Its folder holds a manifest
plus byte-identical copies of its firmware, checked by the test suite.

## Repository

```
mtdi/
  protocol.py            the MTDI line protocol (firmware → MTDI)
  project.py             project.json loading and validation
  engine.py              sources in, MTDI packet out
  core.py                the 8-factor score
  pillars/
    validation.py        00 Validation Chamber
    environment.py       01 Environmental Intelligence
    nvtra.py             02 NVTRA
    i3/                  03 I³ (interface framework: assets, components, pages)
    aether.py            04 Aether
  adapters/              serial · tcp · http · python · replay · simulator
  studio/                the studio: builds every page from a project
projects/                one folder per integrated project, plus _template
firmware/                PROTOCOL.md and firmware templates (Arduino, MicroPython)
examples/                feeding MTDI from software
docs/MANIFEST.md         every project.json field
INTEGRATING.md           how to bring a new project into MTDI (humans and AIs)
AGENTS.md                rules for AI agents working in this repository
```

## What it is honest about

* The MTDI score is a heuristic evidence-quality score, **not a calibrated probability**, and the
  interface says so wherever it shows it.
* Simulated data is labelled at every layer. The interface watermarks it, NVTRA prefixes it,
  the recorder skips it and Environmental Intelligence refuses to save it as an environment.
* Detection limits come from measured noise (LOD = 3σ, LOQ = 10σ), never typed in.
* The firmware templates and the ultrasonic sketch have **not** been run on hardware in this
  repository yet. The Inductra firmware has, in Inductra.
