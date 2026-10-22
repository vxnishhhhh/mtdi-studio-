# MTDI 5 state

Updated by every session. Newest first.

* **Stage:** 1 · Universal foundation
* **Main:** green (CI on Python 3.11, 3.12, 3.13; 137 tests, MATLAB parity in GNU Octave)
* **Open PRs:** none
* **Next item:** studio panel for fused/calibrated channels (S1-11), S1-10 Hugging Face copy (needs a workflow: owner review per ADR 0002), S1-15 I³ refresh, S1-12 NVTRA brand beyond the chat header. Re-check S1-16b against real Pi numbers before more speed work.
* **Waiting on the owner:** network access for science hosts; branch protection on main;
  CodeRabbit install; Codex setup; Notion connector; Vercel connector team access (see the
  plan doc's checklist). None blocks Stage 1.

## Log

* 2026-10-22 midday · Main green, no open PRs. Paused for the owner's studio data-path decision (S1-11) and the Pi measurement. Merged since the night summary: #32 (`mtdi watch` fused/calibrated), #33 (phone nav fix), #34 (morning report).

* 2026-10-22 night · Merged #11-#30: NVTRA bot uses agents + brand mark; calibration, fused channels and drift checks in manifest/engine; Aether tags + hours counter + game spec + late-night CLI note; Pi budget doc + measure.py; snapshot 11x faster at 128 channels (1245 -> 116 ms); flaky test fixed; MATLAB fuse/calibrate/drift + examples (Octave parity); `mtdi calibrate`. Report: ops/reports/2026-10-21-night.md.

* 2026-10-21 evening · Merged S1-02 registry, S1-03 capabilities, S1-04 profiles, S1-10 research catalogue + credits, S1-11 fusion + calibration. #8 and #9 under review. Report: ops/reports/2026-10-21-evening.md.

* 2026-10-21 · S1-01: MTDI page now shows six pillars (Computational Core 02 with a live module check, Research 05 with an honest empty catalogue) plus Aether as the layer; constellation gains both branches. 56 tests, tour clean.

* 2026-10-18 · Owner added ADR 0006: Compatibility Laboratory, capability records and runtime
  selection, Intelligence Profiles (Edge, Scientific, Vision, Autonomous, Hybrid, Research). Backlog
  S1-03 to S1-05; reference projects and the universality gate renumbered S1-07 to S1-09.

* 2026-10-18 · Plan approved (all four decisions as recommended; Africa/Johannesburg time).
  Pillars per ADR 0001. Ops backbone, ADRs 0001-0005, tour tool. Scheduled sessions created.

## Owner to-do, deferred (raise at the next owner session)
* Codex: Settings → Code Review → mtdi-studio- → Trigger = every PR (no automatic review posted on PR #1).
* Vercel connector: grant team `vaishnavsh-3150s-projects` (the connector currently sees no teams).
* Keys: free Groq key in Vercel env; `NASA_API_KEY` (free) as a GitHub Actions secret.
