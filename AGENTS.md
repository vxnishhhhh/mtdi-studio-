# Rules for AI agents working with MTDI 5.0

**If you were asked to build a project with MTDI, read `docs/AI.md` first and follow it step by
step.** It covers hardware, firmware, software, computers, networking, security and any other
field that produces numbers.

1. **Use the framework.** The interface (`studio/`), engine, NVTRA, ML (`mtdi/ml`), storage
   (`mtdi/storage`), LLM and voice (`mtdi/llm.py`, `mtdi/voice.py`), SDKs and deployment exist and
   are tested. Build on them; do not rewrite them.
2. **Projects are manifests.** A project is `projects/<id>/project.json` here, or
   `mtdi-project/project.json` in a repository set up with `python -m mtdi adopt`. Never add
   project-specific code to `mtdi/`.
3. **The framework stays universal.** `mtdi/` never names a specific sensor, unit, product or field.
   Everything specific comes from the manifest or the project's own code.
4. **Never invent data.** No made-up readings, calibration constants, noise floors, training labels
   or results. Unknown values stay at defaults and are written down as unknown.
5. **Nothing simulated by default.** The simulator adapter exists for development only, labels every
   sample `SIMULATED`, is never recorded and never saved as an environment.
6. **The interface keeps its design.** Replace placeholder words with the project's words; keep the
   pages, animations, 3D scenes, hand vision and NVTRA working.
7. **Verify before claiming.** `python -m mtdi check`, `python -m mtdi packet`, `python -m unittest
   discover tests`, `STUDIO_HTTPS_PORT=0 python run.py --self-test`. Report failures as failures and say
   what was not tested.
8. **Improving MTDI.** If a manifest cannot express something, change the framework generically, add
   a test, keep every project and SDK passing, and record it in `CHANGELOG.md`.
9. **Secrets.** API keys, tokens and the ingest token come from environment variables only. Never write
   them into files, manifests, logs or commits.
