<div align="center">

# MTDI Studio · 5.0

**Microprocessing Technological Diagnostic Intelligence**

A complete framework for building any project that produces data: a live interface,
an evidence engine, an AI that explains it, machine learning, voice, signed cloud storage,
SDKs in six languages and one-command deployment.

![version](https://img.shields.io/badge/MTDI-5.0.0-00e5ff?style=flat-square)
![tests](https://img.shields.io/badge/tests-52%20passing-00e676?style=flat-square)
![python](https://img.shields.io/badge/python-3.11%E2%80%933.13-2979ff?style=flat-square)
![sdks](https://img.shields.io/badge/SDKs-Python%20%C2%B7%20C%2B%2B%20%C2%B7%20Java%20%C2%B7%20JS%20%C2%B7%20MATLAB%20%C2%B7%20Arduino-b388ff?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-ffab40?style=flat-square)

</div>

## Build a project with MTDI from any AI

Paste this into ChatGPT, Claude, Gemini or any coding assistant:

```text
Build my project on MTDI 5.0: https://github.com/vxnishhhhh/mtdi-studio-
Read docs/AI.md in that repository first and follow it step by step. Use the framework's
studio interface, engine, NVTRA, ML, storage and SDKs instead of writing your own, verify
with the commands it lists, and tell me exactly what was and was not verified.
My project: <describe it>.
```

The repository is written to be read by machines as well as people:
[`llms.txt`](llms.txt), [`docs/AI.md`](docs/AI.md) (the procedure),
[`AGENTS.md`](AGENTS.md) (the rules), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/schema/project.schema.json`](docs/schema/project.schema.json) and
`python -m mtdi describe` (every capability, as JSON).

## What is in the box

| Layer | What you get | Where |
|---|---|---|
| **I³ interface** | Intro, scroll openings, interactive globe, constellation, module orbits, five pages, live charts, 3D views, settings, exports. Every title is a placeholder (Title, Heading 1, Text) waiting for your project | `studio/`, `public/assets/` |
| **NVTRA** | Chat and voice agent in the interface ("Hey Novatra"), a grounded bot for any project (`mtdi ask`, `mtdi chat`, `mtdi voice`), rule-based answers offline | `studio/intelligence.py`, `mtdi/bot.py` |
| **Hand vision** | MediaPipe hand tracking in the browser, finger cursor, pinch to hold and rotate 3D objects, gesture calibration | `studio/browser.py`, `public/assets/mediapipe` |
| **Engine** | Strict line protocol, manifests, eight adapters, baselines that learn their environment, evidence scoring you can take apart | `mtdi/` |
| **Machine learning** | Streaming anomaly detection (z-score, EWMA, MAD, CUSUM, Page-Hinkley), KNN, nearest centroid, logistic regression, Gaussian NB, k-means, Holt and online linear forecasting, signal features | `mtdi/ml/` |
| **Language models** | One call for Anthropic, OpenAI, Gemini, Groq and xAI | `mtdi/llm.py` |
| **Voice** | Speech to text (Whisper via Groq or OpenAI), text to speech (ElevenLabs or OpenAI) | `mtdi/voice.py` |
| **Cloud storage** | S3-compatible with AWS Signature V4 (AWS, Cloudflare R2, MinIO, Backblaze B2), local folders, client-side AES-256-GCM encryption, project backup and restore | `mtdi/storage/` |
| **Deployment** | Vercel (the interface runs as a Python function; assets from the CDN), project wizard that creates the GitHub repo, Vercel deployment, Notion page and MATLAB starter | `app.py`, `mtdi/create.py`, `mtdi/integrations/` |
| **SDKs** | Python, C++ (header only), Java, JavaScript, MATLAB, Arduino and MicroPython: same protocol, same detectors, same numbers | `sdk/`, `matlab/+mtdi`, `firmware/` |
| **Verification** | 52 tests including a cross-language check that C++, Java, JS and MATLAB agree with Python to 1e-9 | `tests/` |

## Quick start

```bash
git clone https://github.com/vxnishhhhh/mtdi-studio- mtdi && cd mtdi
pip install -r requirements.txt

python run.py                                   # the interface, http://localhost:8050
python -m mtdi run projects/host-health         # the interface, live on this computer's own data
python -m mtdi ask projects/host-health "is anything unusual?"
python -m unittest discover tests               # 52 tests
```

Nothing is simulated. Until a source is connected every chart shows its empty, offline state.

## Feed it anything

The interface has three display channels: **Channel 1** (a vector or a number), **Channel 2**
(a number) and **Channel 3** (a sweep of points). Fill them in any of these ways:

| From | How |
|---|---|
| An MTDI project | `python -m mtdi run projects/<id>`; choose channels with a `"studio"` block in the manifest |
| A deployed studio | `python -m mtdi run projects/<id> --studio-url https://<you>.vercel.app` |
| Any program | `POST /api/ingest {"ch1": [x, y, z], "ch2": 3.1, "ch3": {"x": [...], "y": [...]}}` |
| Python / C++ / Java / JS / MATLAB | `mtdi.bridge.StudioBridge`, `mtdi::Line`, `Mtdi.StudioClient`, `StudioClient`, `mtdi.send` |
| Firmware | print `KEY=value,KEY=value` lines; MTDI reads serial, TCP, HTTP or any program's output |
| The command line | `python -m mtdi send http://localhost:8050 --ch2 3.1` |

On a public deployment, ingest needs `Authorization: Bearer $STUDIO_INGEST_TOKEN`.

## The five pillars

| | Pillar | Role |
|---|---|---|
| 00 | **Validation Chamber** | Is each channel present, fresh, on time, in range? Detection limits from measured noise (LOD = 3σ, LOQ = 10σ) |
| 01 | **Environmental Intelligence** | Learn each channel's normal, lock it, save it as a named environment, compare later |
| 02 | **Computational Core** | ML, numerical analysis and the language runtimes (Python, C++, Java, JS, MATLAB) ([ADR 0001](docs/adr/0001-pillars-and-aether-layer.md)) |
| 03 | **NVTRA** | Explain what the evidence shows, in plain language, never inventing a reading |
| 04 | **I³** | Induction · Interference · Intelligence: the interface |

**Aether** runs across all five as the layer of purpose and authorship (and the terminal). It is shown, never scored.

A core fuses 00 and 01 into one score from eight named, weighted factors. It is an
evidence-quality score you can take apart, **not a probability**.

## Command line

```text
python -m mtdi run <project> [--studio-url URL | --headless] [--record f.jsonl]
python -m mtdi watch | ask | chat | voice | packet <project>
python -m mtdi anomalies <project> <recording> [--detector mad|zscore|ewma|cusum]
python -m mtdi store put|get|ls|rm|backup|restore ... [--encrypt]
python -m mtdi send <studio-url> --ch1 x y z --ch2 n --ch3 y1 y2 ...
python -m mtdi new <id> | adopt <repo> [--studio] | create | publish vercel|notion|matlab <project>
python -m mtdi check <project> | parse "<line>" | analyze <project> <recording> | describe
```

## Environment

Every key is read from the environment only and never written to disk.
[`.env.example`](.env.example) lists them all. The essentials:

| Variable | Turns on |
|---|---|
| `ANTHROPIC_API_KEY` · `OPENAI_API_KEY` · `GEMINI_API_KEY` · `GROQ_API_KEY` · `XAI_API_KEY` | NVTRA chat (any one) |
| `GROQ_API_KEY` or `OPENAI_API_KEY` | voice input |
| `ELEVENLABS_API_KEY` | NVTRA's voice |
| `STUDIO_INGEST_TOKEN` | feeding a public studio |
| `MTDI_S3_*`, `MTDI_STORAGE_KEY` | cloud storage and encryption |
| `VERCEL_TOKEN`, `GITHUB_TOKEN`, `NOTION_TOKEN` | the project wizard |

## Repository

```
studio/           the I³ interface: pages, NVTRA, hand vision, runtime, exports (Dash + Flask)
public/assets/    interface assets, served by Vercel's CDN
app.py · run.py   WSGI entry (Vercel) · local entry
mtdi/             the framework: engine, pillars, adapters, ml, storage, llm, voice, bot, bridge, integrations
sdk/              C++ (header only), Java and JavaScript SDKs
matlab/+mtdi      MATLAB toolbox
firmware/         line protocol, Arduino and MicroPython templates
projects/         example projects (computing, networking, security, ultrasonic) and _template
docs/             AI playbook, architecture, manifest reference and JSON schema
tests/            core, backend, studio ingest and cross-language SDK tests
```

## Honest about

* The score is a heuristic evidence-quality score, **not a calibrated probability**.
* LLM, voice, S3 and Vercel requests are tested against local servers that speak each
  protocol (and SigV4 against AWS's published example), not against the live services.
* The interface needs an API key for NVTRA's chat and voice; without one NVTRA answers from
  its rules and uses the browser's voice. Local Whisper and local models run only on your own machine.
* On Vercel the interface runs as serverless functions: state lives per instance, settings typed
  into the page can reset, and the live stream reconnects every few seconds.

## License

MIT. See [LICENSE](LICENSE).
