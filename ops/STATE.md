# MTDI 5 state

Updated by every session. Newest first.

* **Stage:** 1 · Universal foundation
* **Main:** green (CI on Python 3.11, 3.12, 3.13; 94 tests)
* **Open PRs:** #8 (S1-12a NVTRA policy + local LLM), #9 (S1-12b agents)
* **Next item:** S1-12 part 3 (bot uses agents, NVTRA brand), then S1-11 part 2, S1-10 HF copy, S1-13 to S1-16
* **Waiting on the owner:** network access for science hosts; branch protection on main;
  CodeRabbit install; Codex setup; Notion connector; Vercel connector team access (see the
  plan doc's checklist). None blocks Stage 1.

## Log

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
