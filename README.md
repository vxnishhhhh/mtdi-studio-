# MTDI Studio

**Microprocessing Technological Diagnostic Intelligence**, with the **I³** interface
(Induction · Interference · Intelligence) and **NVTRA**, the intelligence behind it.

A template studio: every page, animation and feature works, and every title and paragraph is
a placeholder (Title, Heading 1, Text, Paragraph. Enter your text here.) so it can be made
into any project. No data source is connected and nothing is simulated: every chart and
reading shows its empty, offline state until you connect a source of your own.

## Pages

| Page | Route | What is on it |
|---|---|---|
| Home | `/` | Intro, scroll hero, interactive globe, module orbit, constellation |
| Page 1 | `/em` | Channel 1 and Channel 2 views, live charts, 3D views, calibration blocks |
| Page 2 | `/spectrum` | Channel 3 views, waterfall, scans |
| MTDI | `/mtdi` | The five pillars: Validation Chamber, Environmental Intelligence, NVTRA, I³, Aether |
| Page 3 | `/sixth-sense` | Fused interpretation, panels, timeline, exports |
| Settings | `/settings` | Theme, AI keys, voice, hand calibration, exports, system |

## Features

* **NVTRA**: chat and voice agent (“Hey Novatra”). Navigates pages, scrolls, toggles the camera,
  answers questions. Works with Anthropic, OpenAI, Gemini, Groq, xAI or Kimi keys, or a local model.
* **Voice**: speech to text through Groq or OpenAI Whisper (or local faster-whisper when run on
  your own machine); speech out through ElevenLabs, or the browser voice when no key is set.
* **Hand vision**: MediaPipe hand tracking in the browser (camera stays on your device),
  finger cursor, pinch to hold and rotate the globe and constellation, gesture calibration.
* **3D**: robot hand, NVTRA robot (Spline), lunar scene, circuit boards, Plotly 3D charts.
* **MTDI**: baseline lock, transient watch, confidence scoring, D4 analysis engine, reports.

## Run it on your computer

```bash
pip install -r requirements-local.txt   # or requirements.txt without local speech recognition
python run.py                           # http://localhost:8050
python run.py --self-test               # software self test
```

## Vercel

`app.py` exposes the Flask/Dash `app`; pushing to `main` redeploys. To switch on the AI and
voice, add any of these in **Vercel → Project → Settings → Environment Variables**, then redeploy:

| Variable | Turns on |
|---|---|
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `XAI_API_KEY`, `KIMI_API_KEY` | NVTRA chat (any one) |
| `GROQ_API_KEY` or `OPENAI_API_KEY` | Voice input (Whisper) |
| `ELEVENLABS_API_KEY` | NVTRA's voice |
| `STUDIO_SECRET_KEY` | A fixed session secret (any long random string) |

Keys typed into Settings on the deployed site live only in that server instance's temporary
storage and can disappear; environment variables are the reliable place for them.

## Making it yours

Text lives in `studio/pages.py` (pages), `studio/ui.py` (Page 3, NVTRA island, painters),
`studio/theme.py` (intro), `studio/webapp.py` (header and navigation), `studio/browser.py`
(globe nodes, constellation, typewriter) and `studio/intelligence.py` (NVTRA's persona).
Channels are defined in `studio/analysis.py` (`CHANNELS`).

## License

MIT, see [LICENSE](LICENSE).
