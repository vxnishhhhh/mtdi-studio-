# Building a project on MTDI 5.0: the procedure for AI assistants

You were given this repository and asked to build a project with it. This page is the
procedure. Follow it in order. Use what the framework already provides instead of writing
your own: the interface, engine, NVTRA, ML, storage, voice, SDKs and deployment all exist
and are tested. Do not summarise MTDI from memory and stop there.

## What MTDI is

MTDI (Microprocessing Technological Diagnostic Intelligence) turns anything that produces
numbers into **channels** and runs five pillars over them: **00 Validation Chamber** (is each
channel present, fresh, on time, in range), **01 Environmental Intelligence** (learn the
normal, lock it, compare against it), **02 NVTRA** (explain what is happening from evidence
only), **03 I³** (the interface) and **04 Aether** (purpose, never scored). It ships with a
complete interface (`studio/`) whose every title is a placeholder waiting for the project.

## Step 0: read, don't guess

Read, in this order: `README.md`, `docs/ARCHITECTURE.md`, `docs/MANIFEST.md`
(machine-readable: `docs/schema/project.schema.json`), `firmware/PROTOCOL.md`, and the
example closest to the user's field:

| Field | Example |
|---|---|
| Computers, single-board computers, DevOps | `projects/host-health` (real data, no wiring) |
| Networking | `projects/network-watch` |
| Cybersecurity | `projects/auth-watch` |
| Sensors, embedded | `projects/ultrasonic-room` |
| Anything else | `projects/_template` |

`python -m mtdi describe` prints every adapter, domain, detector, provider, SDK and command as JSON.

## Step 1: choose where the project lives

* **A new project:** fork or clone this repository; the project lives in `projects/<id>`
  (`python -m mtdi new <id>`). The interface, deployment and CI come with it.
* **An existing repository:** `python -m mtdi adopt <path> --studio` copies the framework
  (`mtdi/`), the interface (`studio/`, `public/`, `app.py`, `run.py`, `vercel.json`), the SDKs
  (`mtdi-sdk/`) and the MATLAB toolbox into it, creates `mtdi-project/project.json`, and adds
  MTDI's rules to its `AGENTS.md` without replacing anything.

## Step 2: map the project to channels (with the user)

One row per quantity. Ask about anything you cannot see in their code or hardware.

| What is measured | Where it comes from | Adapter | Keys | Unit | Domain |
|---|---|---|---|---|---|

| Field | Typical channels | Typical source |
|---|---|---|
| Hardware | distance, temperature, acceleration, level, current | firmware printing protocol lines → `serial` or `tcp` |
| Firmware | loop time, free memory, resets, error counters | the same firmware lines |
| Software | latency, error rate, queue depth, throughput | `process` (any program that prints lines), `http`, `python` |
| Computers | CPU, memory, load, temperature, network | `system` (built in) |
| Networking | round-trip time, loss, DNS time | a `process` probe |
| Security | failed logins, new connections, drops | a `process` probe reading logs |

Pick the three channels the interface shows: `ch1` (a vector or the most important number),
`ch2` (a number), `ch3` (a series, drawn as a sweep). They go in the manifest's `studio` block.

## Step 3: make the sources speak the protocol

One sample per line, `KEY=value,KEY=value` or one JSON object (`firmware/PROTOCOL.md`).
Use the SDK for the user's language instead of formatting by hand:

| Language | Use |
|---|---|
| Arduino / C++ on a microcontroller | `firmware/mtdi_template_arduino` |
| MicroPython | `firmware/mtdi_template_micropython` |
| C++ (desktop, Linux boards, ESP32) | `sdk/cpp/mtdi.hpp`: `mtdi::Line`, `mtdi::parse_line`, `mtdi::Ewma`, `mtdi::Cusum` |
| Java | `sdk/java/src/io/mtdi/Mtdi.java`: `Line`, `parseLine`, `Ewma`, `Cusum`, `StudioClient` |
| JavaScript (browser or Node) | `sdk/js/mtdi.mjs`: `Line`, `parseLine`, `Ewma`, `Cusum`, `StudioClient` |
| MATLAB | `matlab/+mtdi`: `packet`, `watch`, `send`, `ewma`, `cusum`, `analyze`, `verify` |
| Python | `mtdi` itself (`mtdi.protocol`, `mtdi.runtime.Runner`, `mtdi.bridge`) |

If a sensor cannot be read, print nothing for that sample. Never print a stand-in value.

## Step 4: write project.json

Start from the template. Fill `project`, `sources`, `channels` (keys, unit, `noise_floor`,
`raw_range`, `expected_rate`), `environment`, the `studio` block, NVTRA `rules` (domain
knowledge as data: `{"when": {"a": ">=6", "b": "<3"}, "condition": "...", "text": "..."}`)
and `aether`. Every field is in `docs/MANIFEST.md`. Unknown values stay at their defaults
and are written down as unknown in the project's README.

Check it: `python -m mtdi check projects/<id>`.

## Step 5: make the interface the project's own

The interface is complete and working; its words are placeholders. Replace them with the
project's own words. Keep every animation, page and element as it is.

| What | Where |
|---|---|
| Intro (title words, card, item grid, credit) | `studio/theme.py` → `startup_intro()` |
| Header brand and page names (Page 1, Page 2, Page 3) | `studio/webapp.py` (layout), `studio/ui.py` (Page 3 button) |
| Home: hero, module cards, constellation chips | `studio/pages.py` → `home_page`, `discipline_block`; chip details `studio/browser.py` → `CHIP_INFO` |
| Globe research nodes, typewriter lines, constellation labels | `studio/browser.py` → `researchNodes`, `phrases`, `GROUPS` |
| Page 1, Page 2, MTDI, Settings | `studio/pages.py` (one function per page) |
| Page 3 | `studio/ui.py` → `page()` |
| MTDI signal-path diagram | `studio/ui.py` → `mtdiFlowPainter` |
| Channel names and units | `studio/analysis.py` → `CHANNELS` |
| NVTRA's persona and what it knows | `studio/intelligence.py` → `NVTRA_PERSONA`, `AGENT_PAGES`, `WHISPER_PROMPT` |

Search for the placeholders to find every spot: `Title`, `Heading 1`, `Heading 2`, `Text`,
`Subtext`, `Label`, `Paragraph. Enter your text here.`, `Item 1`, `TITLE · 01`.

## Step 6: intelligence, ML and storage

* **NVTRA:** set a key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` or
  `XAI_API_KEY`). In the interface NVTRA chats and talks; for the project, `mtdi.bot.Bot` answers
  from the live packet (`python -m mtdi ask|chat|voice`). Without a key it answers from rules.
* **ML:** choose from `mtdi.ml`: streaming anomaly detection on channel deviations
  (`Monitor(lambda: MAD(threshold=4))`), change detection (`CUSUM`, `PageHinkley`),
  classification of labelled windows (`KNN`, `NearestCentroid`, `LogisticRegression`,
  `GaussianNB` with `window_features`), clustering (`KMeans`), forecasting (`Holt`,
  `OnlineLinear.time_to(threshold)`). Train only on the user's real, labelled data.
* **Storage:** `mtdi.storage.open("s3://bucket/prefix")` (AWS, R2, MinIO, B2), `encrypted(...)`
  for client-side AES-256-GCM, `backup_project(...)` for manifests, environments and recordings.

## Step 7: deploy

* **Vercel:** `python -m mtdi create` (wizard) or `python -m mtdi publish vercel projects/<id> --name <name>`
  deploys the interface, sets a fresh `STUDIO_INGEST_TOKEN` and prints it once. Then stream the
  project to it: `python -m mtdi run projects/<id> --studio-url https://<name>.vercel.app`.
  A repository connected to Vercel redeploys on every push (`vercel.json`, `app.py` are ready).
* **GitHub:** the wizard creates the repository; `.github/workflows/ci.yml` tests every language.
* Keys go in the host's environment variables, never in files.

## Step 8: verify, then report

```bash
python -m mtdi check projects/<id>
python -m mtdi packet projects/<id> --seconds 5       # real data arrives, channels connect
python -m mtdi run projects/<id>                      # open http://127.0.0.1:8050
python -m unittest discover tests
STUDIO_HTTPS_PORT=0 python run.py --self-test
```

Tell the user exactly what ran and passed, what was not tested (hardware you could not reach,
services without keys), and every value you left as unknown.

## Rules

Read `AGENTS.md`. In short: never invent data; simulated data stays labelled `SIMULATED`
and is never the default; keep `mtdi/` universal (no project-specific code in it); keys come
from the environment only; verify before claiming.
