# MTDI 5 backlog

Ordered by priority. A session takes the first item whose status is `ready` and whose
dependencies are `done`. Each item has an acceptance check; an item is `done` only when that
check passes in CI. Plan: the owner's doc "MTDI 5 Readiness Report and Plan". Decisions: docs/adr/.

Status: `ready` · `in progress (PR #n)` · `blocked (reason)` · `done (PR #n)`

## Stage 1 · Universal foundation (gate: an old sensor project and a software-only data project run on one set of contracts)

### S1-01 · Computational Core in the studio; Aether as the layer · ready
The studio's MTDI page orbit, its sections and the Home constellation show the five pillars of
ADR 0001 (00 Validation, 01 Environmental, 02 Computational Core, 03 NVTRA, 04 I³). Aether stays
reachable as the soul layer with its terminal, Fieldrun, Judge Mode, rickroll and classified file.
Add a Computational Core section listing its modules from `mtdi.pillars.COMPUTATIONAL_MODULES`.
**Check:** tour passes; the MTDI page shows "Computational Core" and the Aether terminal still opens.

### S1-02 · Registry: modules and integrations · ready
`mtdi/registry.py` + `registry/integrations.json`: provider, purpose, permissions, auth method,
capabilities, cost, risks, status (`connected` / `configured` / `not set up`), last test, fallback.
`python -m mtdi registry` prints it; `describe` includes it. Every Computational Core module
imports. Seed with GitHub, Vercel, Notion, MATLAB, Anthropic, OpenAI, Gemini, Groq, xAI,
ElevenLabs, S3, CodeRabbit, Codex, PlatformIO, KiCad, Ollama.
**Check:** tests validate the schema and that every listed module imports.

### S1-03 · Project-driven studio words · ready
Every placeholder the studio shows (intro words, header brand, page names, Home hero and cards,
constellation chips and details, globe nodes, typewriter lines, MTDI diagram labels, channel
names and units) comes from one content file: `studio/content/default.json`, overridable by a
project's `interface` block or `MTDI_CONTENT` path. Defaults reproduce today's placeholders exactly.
**Check:** a test renders the studio with a second content file and finds its words on every page.

### S1-04 · Reference project: Third Eye (MTDI 1 reborn) · ready
`projects/third-eye`: two ultrasonic sensors and a buzzer on an Arduino. Manifest, firmware
(`firmware/`, prints protocol lines), studio block, NVTRA rules, Aether purpose. A recorded
session for replay (`recordings/`), labelled with how it was produced; if no real recording exists,
leave replay empty and say so.
**Check:** `mtdi check`, firmware compiles in CI (arduino-cli or PlatformIO), replay drives the studio.

### S1-05 · Reference project: space weather (software only) · ready
`projects/space-weather`: a collector for NOAA SWPC planetary K-index (public JSON), run by a
GitHub Actions workflow on a schedule that commits dated recordings; a `replay` source for
offline use; channels Kp and its rate of change; ML monitor (CUSUM) on Kp.
**Check:** workflow runs once successfully; the project packet has live channels from real data.

### S1-06 · Universality test · blocked (needs S1-04, S1-05)
`tests/test_universality.py`: both reference projects load, run, bridge into the studio and answer
NVTRA questions through the same framework code paths, with no project-specific code in `mtdi/`.
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
