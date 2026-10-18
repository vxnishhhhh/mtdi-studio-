# Architecture

```
            sources                          framework (mtdi/)                         studio (studio/)
  ┌───────────────────────┐   lines    ┌──────────────────────────────┐   bridge   ┌─────────────────────────────┐
  │ firmware (Arduino,    │──────────▶│ protocol → engine             │──────────▶│ feed_ch1 / ch2 / ch3        │
  │ MicroPython, C++ SDK) │  serial    │   00 Validation Chamber       │ in-process │ AnalysisEngine (baselines,  │
  │ programs (any lang.)  │  tcp, http │   01 Environmental Intel.     │  or HTTP   │   transients, MTDI score)   │
  │ this computer         │  process   │   core: 8-factor score        │  /api/     │ pages · NVTRA · hand vision │
  │ recordings            │  system    │   02 NVTRA rules              │  ingest    │ D4 analysis · reports       │
  └───────────────────────┘  replay    │ ml · storage · llm · voice    │           └─────────────────────────────┘
                                       │ bot · runtime (/mtdi/* API)    │                 ▲   browser: Dash, three.js,
                                       └──────────────────────────────┘                  │   MediaPipe, Spline, canvas
                                                                                  any program: POST /api/ingest
```

## Two halves, one process

* **`mtdi/`** is the framework: protocol, manifests, adapters, the evidence engine and pillars,
  plus ML, storage, language models, voice and the NVTRA bot. Pure Python (numpy optional),
  no web framework needed for the engine itself.
* **`studio/`** is the I³ interface: a Dash + Flask application with its own analysis engine
  (baseline lock, transient watch, axial consensus, MTDI score), NVTRA chat and voice, browser
  hand tracking, 3D scenes, the D4 analysis blocks, exports and reports.
* **`mtdi/bridge.py`** joins them. `python -m mtdi run <project>` starts the project's adapters
  and engine, imports the studio in the same process, adds the `/mtdi/*` API to its server and
  pushes each new sample into the studio's three display channels. `--studio-url` pushes to a
  studio running elsewhere instead (`POST /api/ingest` with the ingest token).

## Display channels

| Slot | Studio data | Pages |
|---|---|---|
| `ch1` | a three-axis vector (or a number as `[v, 0, 0]`): axes, magnitude, baseline, history | Page 1 first view, 3D views, Page 3 |
| `ch2` | one number per sample: level, baseline, relative index, history | Page 1 second view, Page 3 |
| `ch3` | a sweep: x and y series, peaks, max hold, waterfall | Page 2, Page 3 |

`feed_ch1/2/3` (in `studio/acquisition.py`) publish into the same structures the pages,
NVTRA and the MTDI score read, label every sample with its source (default `EXTERNAL`), and
archive it. Nothing is synthesised; with no feed the pages show their offline state.

## Entry points

| File | Purpose |
|---|---|
| `run.py` | local: `python run.py` serves the studio on :8050 (and HTTPS on :8443 for camera access on a LAN) |
| `app.py` | WSGI `app` for Vercel or any WSGI host; on serverless, state goes to /tmp and workers are daemons |
| `python -m mtdi …` | the framework's command line (`mtdi/__main__.py`) |

## Studio internals

The studio began as one large application split into sections that share one namespace
(`studio/_shared.py`, load order in `ORDER`): `common` (config, archive, state), `sensors`
(shared data structures), `intelligence` (providers, keys, NVTRA agent, speech), `system`
(lifecycle), `theme` (CSS, intro), `browser` (the browser runtime: shader, intro, orbits,
globe, constellation, hand vision), `webapp` (Flask, asset routes, layout), `reports`,
`charts`, `pages`, `routing` (callbacks). `runtime.py` adds the HTTP API, streams and threads;
`ui.py` adds Page 3, the NVTRA island and the canvas painters; `acquisition.py` holds the
feed; `analysis.py` the studio's engine; `d4*.py` the D4 analysis engine.

## Vercel

`vercel.json` points the Python runtime at `app.py`. `public/assets/` is served by Vercel's
CDN (no function size limit, so the 6 MB hand-tracking model loads), everything else runs in
the function. The live stream (`/api/events`) sends a few seconds of frames and closes; the
browser reconnects. Keys and the ingest token are Vercel environment variables.

## Tests

| File | Covers |
|---|---|
| `tests/test_mtdi.py` | protocol, manifests, environment, engine, adapters, runner API, adopt, MATLAB analysis agreement, the project wizard |
| `tests/test_backend.py` | ML, storage (local, S3 SigV4 against a local S3 server and AWS's published vector, encryption), LLM providers, voice, NVTRA bot, bridge, studio ingest |
| `tests/test_sdks.py` | C++, Java, JavaScript and MATLAB (Octave) produce the same numbers as Python; clients post with the token |
