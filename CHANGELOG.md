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
  generator, replay, and a SIMULATED simulator; plus a recorder.

### Projects

* **inductra-vaion** (project 1): magnetic and electric channels from Inductra's own Uno
  firmware and Mac bridge (byte-identical copies), RF as an optional HTTP source, Inductra's
  three signature rules as NVTRA rules.
* **ultrasonic-room** (example): HC-SR04 echo distance, the first non-electromagnetic project.
