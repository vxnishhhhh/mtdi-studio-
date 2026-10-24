# MTDI 5 backlog

Ordered by priority. A session takes the first item whose status is `ready` and whose
dependencies are `done`. Each item has an acceptance check; an item is `done` only when that
check passes in CI. Plan: the owner's doc "MTDI 5 Readiness Report and Plan". Decisions: docs/adr/.

Status: `ready` · `in progress (PR #n)` · `blocked (reason)` · `done (PR #n)`

## Stage 1 · Universal foundation (gate: an old sensor project and a software-only data project run on one set of contracts, each on a runtime chosen from its target's capabilities)

### S1-01 · Computational Core in the studio; Aether as the layer · done (PR #2)
The studio's MTDI page orbit, its sections and the Home constellation show the five pillars of
ADR 0001 (00 Validation, 01 Environmental, 02 Computational Core, 03 NVTRA, 04 I³). Aether stays
reachable as the soul layer with its terminal, Fieldrun, Judge Mode, rickroll and classified file.
Add a Computational Core section listing its modules from `mtdi.pillars.COMPUTATIONAL_MODULES`.
**Check:** tour passes; the MTDI page shows "Computational Core" and the Aether terminal still opens.

### S1-02 · Registry: modules and integrations · done (merged 2026-10-21)
`mtdi/registry.py` + `registry/integrations.json`: provider, purpose, permissions, auth method,
capabilities, cost, risks, status (`connected` / `configured` / `not set up`), last test, fallback.
`python -m mtdi registry` prints it; `describe` includes it. Every Computational Core module
imports. Seed with GitHub, Vercel, Notion, MATLAB, Anthropic, OpenAI, Gemini, Groq, xAI,
ElevenLabs, S3, CodeRabbit, Codex, PlatformIO, KiCad, Ollama.
**Check:** tests validate the schema and that every listed module imports.

### S1-03 · Capability records and runtime selection (ADR 0006) · done (merged 2026-10-21)
`mtdi/capabilities.py`: a capability record schema (class, memory, storage, float, network, OS,
languages, accelerators, runtime it can host), records for reference targets in `registry/targets/`
(Arduino Uno, ESP32, Raspberry Pi 4/5, desktop, cloud function, browser), host self-detection
(`python -m mtdi capabilities`), and `select_runtime(target, profile)` returning line-protocol / edge /
full / remote with its reason.
**Check:** tests cover every reference target and the selection rules; `describe` lists them.

### S1-04 · Intelligence Profiles (ADR 0006) · done (merged 2026-10-21)
Manifest field `profile` (edge, scientific, vision, autonomous, hybrid, research; default hybrid).
`mtdi/profiles.py` defines the modules, dependencies and minimum capabilities per profile; `Runner`
loads only the profile's modules; `mtdi check` reports the profile and whether the target qualifies.
**Check:** a test per profile proves it loads its modules and refuses an under-capable target.

### S1-05 · Compatibility Laboratory, first matrix (ADR 0006) · ready
`.github/workflows/compat.yml` (nightly + on PR): Arduino Uno and ESP32 firmware builds with size
checks; core suite on an ARM64 runner; desktop matrix (Linux, macOS, Windows); serverless studio
smoke test; Vision profile on recorded images. A script writes `docs/COMPATIBILITY.md` (target ×
capability × result, compiled / emulated / hardware kept distinct).
**Check:** the workflow runs green and the report is generated; nothing claims hardware verification.

### S1-06 · Project-driven studio words · in progress (slices 1–2 merged: shell, page titles, Home hero and cards; channel names and units)
Every placeholder the studio shows (intro words, header brand, page names, Home hero and cards,
constellation chips and details, globe nodes, typewriter lines, MTDI diagram labels, channel
names and units) comes from one content file: `studio/content/default.json`, overridable by a
project's `interface` block or `MTDI_CONTENT` path. Defaults reproduce today's placeholders exactly.
**Check:** a test renders the studio with a second content file and finds its words on every page.
Slice 1 (2026-10-24): `studio/content.py`, `studio/content/default.json` (42 keys), `MTDI_CONTENT`, the
manifest's `interface` block (`mtdi run` applies it, `mtdi check` validates it). Covers the brand,
author credit, nav, boot screen, startup intro, Home hero and cards, and every page's eyebrow,
title and subtitle. Defaults render identically to before on every page. Next slices: section
heads and cards on each page, channel names and units (from the project's channels), tab and
button labels, typewriter lines, constellation and globe words.

### S1-07 · Reference project: Third Eye (MTDI 1 reborn) · ready
`projects/third-eye`: two ultrasonic sensors and a buzzer on an Arduino. Manifest, firmware
(`firmware/`, prints protocol lines), studio block, NVTRA rules, Aether purpose. A recorded
session for replay (`recordings/`), labelled with how it was produced; if no real recording exists,
leave replay empty and say so.
**Check:** `mtdi check`, firmware compiles in CI (arduino-cli or PlatformIO), replay drives the studio.

### S1-08 · Reference project: space weather (software only) · ready
`projects/space-weather`: a collector for NOAA SWPC planetary K-index (public JSON), run by a
GitHub Actions workflow on a schedule that commits dated recordings; a `replay` source for
offline use; channels Kp and its rate of change; ML monitor (CUSUM) on Kp.
**Check:** workflow runs once successfully; the project packet has live channels from real data.

### S1-09 · Universality test · blocked (needs S1-07, S1-08)
`tests/test_universality.py`: both reference projects load under their profiles (Edge, Research),
get a runtime chosen from their target's capabilities, run, bridge into the studio and answer NVTRA
questions through the same framework code paths, with no project-specific code in `mtdi/`.
**Check:** the test passes in CI. This is the Stage 1 gate.

## Stage 2 · Engineering runtime
* S2-01 Hardware abstraction layer: sensor, actuator, bus, board contracts; capability declarations.
* S2-02 PlatformIO firmware builds in CI for Arduino Uno, ESP32, Pico; edge-agent template.
* S2-03 Local AI provider in `mtdi.llm` (Ollama, llama.cpp); offline mode documented.
* S2-04 Actuator safety: simulation by default, explicit arm step, limits, stop.

## Stage 3 · Engineering Agent System
* S3-01 Task contracts and a persistent queue (`registry/tasks/`), budgets, approvals, audit.
* S3-02 Planner agent: idea → requirements, constraints, risks, architecture.
* S3-03 Hardware, firmware, software, research, test, security, docs agents.
* S3-04 Workbench pages: idea input, plan review, task board, artifacts.

## Stage 4 · Science tools
* S4-01 Data library collectors (NASA DONKI, Exoplanet Archive, PhysioNet EEG, PubChem, ChEMBL, USGS, UCI).
* S4-02 Dataset, model and experiment registries; held-out evaluation; promotion and rollback.
* S4-03 Digital twin: recorded real data as virtual devices, provenance-labelled.
* S4-04 MATLAB in GitHub Actions alongside Octave.

## Stage 5 · Autonomous operations hardened
* Budgets, audit log, observability, rollback drills, secret scanning.

## Stage 6 · Advanced intelligence
* Feedback learning, active learning, Aether Intelligence (guided help, new Easter eggs),
  Framework Improvement Lab (benchmarks → proposals as PRs).

## Stage 7 · MTDI 5.0 release
* Demos A, B, C pass nightly; docs; migration notes for 5.1.

## Stage 1 additions from the owner brief (ADR 0007), ordered
- S1-10 (in progress: catalogue + credits merged; bulk copy to Hugging Face and offline pull next) Research pillar: catalogue schema, licence and credit fields, the first 25 real datasets (sensor, physics, biomedical including cancer research, space weather), offline pull. **Credits page** generated from the catalogue.
- S1-11 (in progress: inverse-variance fusion, calibration, fused channels and drift checks are done in the manifest, engine, `mtdi watch` and the studio panel (#39, reads /mtdi/packet). Not done: Kalman/complementary filtering over time; the current fusion combines simultaneous readings only) Environmental Intelligence 2.0: multi-sensor fusion (Kalman/complementary), calibration routines (offset, gain, temperature), and the link to Validation.
- S1-12 (in progress: policy, local-first LLM, agents, bot uses validator + researcher done; NVTRA brand in the studio next) NVTRA 2.0: fixed safety and engineer system policy, local models (llama.cpp/Ollama on Pi 5 and Mac), online research tool, agents (analyst, grapher, researcher, validator), NVTRA brand.
- S1-13 (in progress: fuse, calibrate, applyCalibration and drift in +mtdi with Octave parity tests done; three Octave-tested examples in matlab/examples; Coder path next, needs a MATLAB licence) MATLAB first: ML toolbox parity, a MATLAB Coder path to C for the Pi, and an MLX notebooks gallery.
- S1-14 (in progress: comment tags, `mtdi aether` hours counter, docs/AETHER.md, the Astra game spec and a late-night CLI note done; studio Easter eggs next) Aether: comment conventions (guides, context, "hours wasted" counters), more Easter eggs, a 3D game spec for Astra.
- S1-15 I³ refresh: fix imperfections, scroll animations, presets, 21st.dev components, 3D specs for Astra.
- S1-16 (in progress: docs/PI_BUDGET.md, tools/pi/measure.py, a cloud reference run, install.sh, `mtdi doctor` (measures the machine it is installed on) and `mtdi update` done; a real Pi run is the owner's and nothing waits on it) Pi 5 budget: what runs on the device and what runs in the cloud, measured.
- S1-16b (in progress: shared-clock fast path and per-sequence cache took 128 channels with a fresh packet from 1245 to ~116 ms in the cloud; the check asks for well under 100 ms, so not done. `mtdi doctor` now measures this case on each install) Correlation cost: `core.correlation` is O(channels²) per snapshot (691 ms at 128 channels in the cloud reference). Cache, cap or compute incrementally without changing small-project results.
  **Check:** `tools/pi/measure.py` shows the 128-channel snapshot well under 100 ms with a fresh packet before each snapshot, and a test compares old and new correlation on random histories with identical results for small projects.
