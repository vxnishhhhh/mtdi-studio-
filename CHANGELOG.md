# Changelog

MTDI's version moves when a pillar's behaviour changes. Projects are listed when they
are integrated.

## 5.0.0 — MTDI Studio

First release of MTDI as a studio: every pillar implemented and working together, for any
hardware, firmware or software, driven by one manifest per project.

* **00 Validation Chamber:** presence, freshness, achieved vs expected rate, timing
  regularity, clipping against a declared raw range, dropped-line counting, LOD = 3σ and
  LOQ = 10σ from measured noise.
* **01 Environmental Intelligence:** Inductra's Baseline Lock and Transient Watch made
  sensor-agnostic. Per-axis baselines and axial consensus for any vector sensor, a
  stale-lock watch, learn/lock/unlock, and named environments saved from real data only,
  then recalled to compare against.
* **Core:** Inductra's 8-factor weighted score with per-project weights, cross-channel
  correlation, completeness, and optional channels.
* **02 NVTRA:** universal interpretation rules, project domain rules as data, and grounded
  answers from the live packet, with a hook for a language model.
* **03 I³:** the interface framework extracted from Inductra Vaion, now a pillar, with live
  traces, live sentences and action buttons. Every page is generated from the manifest.
* **04 Aether:** purpose and authorship per project, non-functional.
* **Protocol:** `KEY=value` / JSON lines, strict; Inductra's firmware format unchanged.
* **Adapters:** serial (USB, socket://, rfc2217://), TCP listen/connect, HTTP ingest, Python
  generator, `process` (any program in any language), `system` (host telemetry, standard library
  on Linux), replay, and a SIMULATED simulator; plus a recorder.
* **Any field:** a channel's `domain` is an open word (sensors, compute, network, security, …).
* **Small boards:** `run --headless` (JSON API, no Dash) and `watch` (terminal view over SSH).
* **AI-operable:** `llms.txt`, `docs/AI.md` playbook, `AGENTS.md`, a JSON Schema for manifests,
  `python -m mtdi describe`, and `python -m mtdi adopt` to build another repository on MTDI.
* **Integrations:** `python -m mtdi create` wizard and `publish`: GitHub repository, Vercel
  deployment, Notion page, MATLAB Online starter. Tokens from the environment only.
* **Two implementations:** `matlab/+mtdi` independently recomputes `python -m mtdi analyze`;
  verified to agree in GNU Octave by the test suite.
* **Website:** `python -m mtdi site build` renders the docs, articles and a replay of the real
  engine for every example project with the same I³ components (`mtdi/pillars/i3/static.py`).
* **Placeholders:** templates use only Title, Subtext, Text, Label and Value.

### Projects

* **inductra-vaion** (project 1): magnetic and electric channels from Inductra's own Uno
  firmware and Mac bridge (byte-identical copies), RF as an optional HTTP source, Inductra's
  three signature rules as NVTRA rules.
* **ultrasonic-room** (example): HC-SR04 echo distance, the first non-electromagnetic project.
* **host-health** (example): the computer MTDI runs on, real telemetry with no wiring.
* **network-watch** (example): TCP connect latency and failures from a plain-Python probe.
* **auth-watch** (example): failed and accepted logins per window from a Linux auth log.
