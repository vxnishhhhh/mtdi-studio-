# Contributing to MTDI Studio

MTDI improves in two ways: by integrating projects, and by improving the pillars.

* **Integrating a project** is a manifest and, if needed, firmware or a probe. Follow
  [INTEGRATING.md](INTEGRATING.md). Do not add project-specific code to `mtdi/`.
* **Improving MTDI** means making a pillar, the core, an adapter or I³ more general. Keep it
  universal (no sensor, unit or product named in `mtdi/`), add a test, keep every project
  passing, and record the change in [CHANGELOG.md](CHANGELOG.md).

Before opening a pull request:

```bash
python -m unittest discover tests
for p in projects/*/; do python -m mtdi check "$p"; done
python -m mtdi site build      # then commit site/dist: Vercel serves it as-is
```

Rules that apply to people and AI agents alike are in [AGENTS.md](AGENTS.md). The short
version: never invent data, keep simulated data labelled, verify before claiming.
