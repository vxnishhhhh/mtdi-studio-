# Contributing to MTDI Studio

MTDI improves in two ways: by building projects on it, and by improving the framework.

* **Building a project** is a manifest, the project's own sources, and its own words in the
  interface. Follow [docs/AI.md](docs/AI.md). Do not add project-specific code to `mtdi/`.
* **Improving MTDI** means making the framework, the interface or an SDK more capable while keeping
  it universal (no sensor, unit or product named in `mtdi/`). Add a test, keep every project and SDK
  passing, and record the change in [CHANGELOG.md](CHANGELOG.md).

Before opening a pull request:

```bash
python -m unittest discover tests                    # needs g++, javac, node and octave for the SDK checks
STUDIO_HTTPS_PORT=0 python run.py --self-test
for p in projects/*/; do python -m mtdi check "$p"; done
```

Rules that apply to people and AI agents alike are in [AGENTS.md](AGENTS.md): never invent data,
nothing simulated by default, verify before claiming, keys only in the environment.
