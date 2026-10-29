# Changelog

## Unreleased

### Framework
* `mtdi.fusion.fit_csv(text, ...)`: the CSV calibration fit shared by `mtdi calibrate` and the studio. It
  refuses a column named twice and any fit a manifest would reject (NaN, infinite or overflowing values).
* `mtdi.project.normalise` raises `ManifestError` naming the field for any wrong JSON shape (null,
  list, text, number, boolean or object where another is expected) or a number too large for a float;
  before, some escaped as `TypeError`, `AttributeError` or `OverflowError` from `mtdi check` and the studio.
* `mtdi.project.summary(project, target=None)`: what `mtdi check` reports, as data. The CLI and the
  studio's PROJECT CHECK both use it.
* `mtdi.protocol.parse_line` rejects a JSON integer too large for a float, and JSON nested deeper
  than the stack, as `ProtocolError` instead of `OverflowError` or `RecursionError`.

### Studio
* Settings → CSV CALIBRATION FIT: `mtdi calibrate` from pasted readings, with the fit shown and the
  calibration file offered as a download (`POST /api/calibration-fit`; nothing is written on the server).
* Settings → PROJECT CHECK: `mtdi check` for a bundled project and `mtdi parse` for one protocol line
  (`GET /api/project-check`, `POST /api/parse-line`).

## 5.0.0 — MTDI Studio

First release of MTDI as a complete studio: one repository holds the interface, the framework,
the intelligence and the SDKs, and every part is tested.

### Interface (I³)
* The full I³ interface: startup intro, scroll openings, interactive globe, constellation, module
  orbits, Home, Page 1, Page 2, MTDI, Page 3 and Settings, live charts and 3D views.
* Every title and paragraph is a placeholder (Title, Heading 1, Text, Paragraph); every identifier
  uses neutral channel vocabulary (ch1, ch2, ch3).
* NVTRA chat and voice agent, key manager for six providers, browser hand tracking with gesture
  calibration, robot hand and Spline scenes.
* No hardware readers and no simulator start: with no feed, every view shows its offline state.
* `POST /api/ingest` feeds Channel 1 (vector), Channel 2 (number) and Channel 3 (sweep) from any
  program, protected by `STUDIO_INGEST_TOKEN` on public deployments.
* Runs on Vercel: WSGI entry `app.py`, assets from the CDN, serverless-safe workers and stream.

### Framework
* Engine and five pillars: Validation Chamber, Environmental Intelligence, NVTRA, I³, Aether; an
  eight-factor evidence score; strict line protocol; manifests with a JSON schema.
* Adapters: serial, tcp, http, python, process, system, replay, simulator (labelled).
* `mtdi.runtime.Runner` with the `/mtdi/*` API; `mtdi.bridge.StudioBridge` shows any project in the
  studio, in-process or over HTTP (`run --studio-url`).
* `mtdi.ml`: ZScore, EWMA, MAD, CUSUM, PageHinkley; KNN, NearestCentroid, LogisticRegression,
  GaussianNB; KMeans; Holt, OnlineLinear; window features, band power, dominant frequency; Monitor.
* `mtdi.storage`: local folders, S3-compatible storage with AWS Signature V4 (AWS, R2, MinIO, B2),
  AES-256-GCM client-side encryption, project backup and restore.
* `mtdi.llm` (Anthropic, OpenAI, Gemini, Groq, xAI), `mtdi.voice` (Whisper, ElevenLabs, OpenAI TTS),
  `mtdi.bot` (NVTRA grounded on the live packet, rule-based offline).
* Command line: run, watch, ask, chat, voice, anomalies, send, store, check, new, adopt (`--studio`),
  create, publish, packet, analyze, parse, matlab, describe.
* Integrations: GitHub repository, Vercel deployment of the live studio (with a fresh ingest token),
  Notion page, MATLAB Online.

### SDKs
* C++ (header only), Java, JavaScript, MATLAB, Arduino and MicroPython templates. The C++, Java, JS
  and MATLAB detectors and protocol parsers are verified to match Python to 1e-9.

### Projects
* host-health (this computer, real data), network-watch, auth-watch, ultrasonic-room, and a template.
