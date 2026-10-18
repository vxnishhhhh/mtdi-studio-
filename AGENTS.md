# Rules for AI agents working with MTDI Studio

You are working with MTDI 5.0. **If you were asked to use MTDI for a project, read
`docs/AI.md` first and follow it step by step.** It covers hardware, firmware, software,
computers, networking, cybersecurity and any other field that produces numbers.

1. **Projects are manifests.** A project is `projects/<id>/project.json` here, or
   `mtdi-project/project.json` in a repository set up with `python -m mtdi adopt`. Never add
   project-specific code to `mtdi/`.
2. **Pillars stay universal.** `mtdi/pillars/`, `mtdi/core.py` and `mtdi/engine.py` must never name
   a specific sensor, unit, product or field. Everything specific comes from the manifest.
3. **Never invent data.** No made-up readings, calibration constants, noise floors or results.
   Unknown values stay at defaults and are written down as unknown in the project README.
4. **Simulated stays labelled.** Simulator data is `SIMULATED` end to end: never remove the label,
   never record it, never save it as an environment.
5. **Other repositories are read-only** unless the user asks. Inductra Vaion lives in its own
   repository; `projects/inductra-vaion/firmware` and `bridge/` are byte-identical copies guarded
   by `tests/test_mtdi.py`.
6. **Placeholders are generic.** Templates and examples meant to be copied say Title, Subtext,
   Text, Label and Value, never a product word.
7. **Verify before claiming.** `python -m mtdi check <project>`, `python -m mtdi run <project> --simulate`,
   `python -m unittest discover tests`. Report failures as failures, and say what was not tested.
8. **Improving MTDI.** If a manifest cannot express what a project needs, change the pillar
   generically, add a test, keep every project passing, and record it in `CHANGELOG.md`.
9. **Secrets.** Integration tokens (GitHub, Vercel, Notion) come from environment variables only.
   Never write them into files, manifests or commits.
