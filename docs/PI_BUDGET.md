# Pi 5 budget

What MTDI runs on the owner's Raspberry Pi 5 (8 GB, no AI HAT) and what goes to the M5 Mac or the cloud.
**Status: estimates plus one cloud reference measurement. Nothing here has been measured on the Pi yet.**
Run `python tools/pi/measure.py` on the Pi (about 2 minutes, stdlib only, sends nothing anywhere except to a
local Ollama if one is running). It writes `docs/results/pi-budget/<host>-<date>.md`; commit that file and
this page gets real numbers.

## Placement

| Work | Where | Basis |
|---|---|---|
| Line protocol, engine, Validation, Environmental, fusion, calibration, drift checks | **Pi** | measured light (table below); pure Python, no NumPy needed |
| Anomaly ML (`mtdi.ml.anomaly`, edge profile) | **Pi** | streaming, stdlib only |
| Studio UI (Dash) | Pi for one viewer, **Mac or Vercel** for more | estimate: Dash plus a browser on the same Pi competes for 4 cores |
| NVTRA answers, rules engine | **Pi** | no model needed |
| NVTRA answers, language model `llama3.2:3b` | **Pi, slow** · Mac preferred | unverified guess: a few tokens per second on a Pi 5 CPU, probably fine for short answers and slow for long ones. `measure.py` will give the real number. The fallback chain already tries the next provider if the Pi model is down |
| Larger models (7B and up) | **Mac** | estimate: too slow on the Pi to be useful for chat |
| Research agent, Hugging Face datasets | **cloud** (free tiers) | network-bound; nothing gained locally |
| Model training, big datasets | **Mac or cloud** | 8 GB of RAM with no accelerator |

## Reference measurement (cloud container, x86_64, 4 CPUs, **not a Pi**)

From `docs/results/pi-budget/cloud-reference-2026-10-21.md`. Expect the Pi to be several times slower; how much slower is exactly what the Pi run will tell us.

| Channels | Packets/s ingested | Snapshot |
|---|---|---|
| 8 | ~22,500 | 8.5 ms |
| 32 | ~7,400 | 58 ms |
| 128 | ~1,700 | **691 ms** |

Every profile cold-starts in under 0.1 s with about 21 MB of peak memory.

## Finding: snapshot cost grows with channels squared

`mtdi.core.correlation` compares every pair of channels on every snapshot. At 128 channels that is 8,128
pairs, and it accounts for over 90% of snapshot time in a profile. Up to about 32 channels it doesn't matter.
Beyond that, a Pi studio refreshing several times a second will fall behind. Tracked as backlog item **S1-16b**:
cache by sequence number, cap the pairs, or compute incrementally, without changing results for small projects.

## Hardware the owner needs to do
1. On the Pi: `git pull`, then `python3 tools/pi/measure.py --no-llm` (no install needed).
2. Optional, for the model row: install Ollama (free), `ollama pull llama3.2:3b`, then run it again without `--no-llm`.
3. Commit the generated file in `docs/results/pi-budget/`, or paste it to Claude.
