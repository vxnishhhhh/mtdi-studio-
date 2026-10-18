# 0006 · Compatibility Laboratory, capability advertisement and Intelligence Profiles

**Status:** Accepted 2026-10-18 (requested by the project owner).

## Decision

1. **Capability advertisement.** Every execution target describes itself in a capability record:
   class (microcontroller, edge board, single-board computer, desktop, cloud, browser), memory,
   storage, floating point, network, operating system, languages, accelerators, and which MTDI
   runtime it can host. MTDI never assumes the full framework runs everywhere.
2. **Runtime selection.** From the capability record and the project's profile, MTDI chooses how
   each part runs: the line protocol only (a microcontroller prints, a host computes), the
   lightweight edge runtime (C++ SDK detectors on the device), the full Python runtime, or a remote
   service (the device streams to a studio or the cloud). The choice and its reason are reported.
3. **Intelligence Profiles.** A project declares a profile; the profile decides which modules load,
   which dependencies are required, and the minimum capabilities:

   | Profile | For | Loads |
   | --- | --- | --- |
   | MTDI Edge | sensors, actuators, lightweight firmware | protocol, adapters, Validation, Environmental Intelligence, C++/Arduino SDKs |
   | MTDI Scientific | MATLAB, experiments, numerical analysis | Edge + Computational Core maths, MATLAB toolbox, recordings, analysis |
   | MTDI Vision | computer vision, relational reasoning | Computational Core vision and features, hand vision, image datasets |
   | MTDI Autonomous | engineering agents, project creation | agent system, LLM providers, task queue, approvals |
   | MTDI Hybrid | hardware + firmware + cloud + AI together | Edge + Scientific + Autonomous + studio bridge |
   | MTDI Research | datasets, ML experiments, reproducibility | data library, dataset/model/experiment registries, ML |

4. **Compatibility Laboratory.** A test matrix in CI proves the same core contracts operate across
   execution environments, each tested as far as CI honestly can:

   | Target | How it is exercised in CI | Real hardware |
   | --- | --- | --- |
   | Arduino-class (AVR) | firmware compiled for an Uno; protocol output checked on the host; size against the board's flash and RAM | owner's board, recorded result |
   | ESP32 + edge processing | firmware compiled for ESP32; C++ SDK detectors run on the host and must match Python | owner's board, recorded result |
   | Raspberry Pi + local AI | core suite on an ARM64 runner; local-AI provider against a small local model | owner's Pi, recorded result |
   | Desktop scientific | core + MATLAB/Octave cross-check on Linux, macOS and Windows | n/a |
   | Cloud analysis | studio in serverless mode, ingest, stream; Vercel deployment smoke check | live deployment |
   | Software-only visual intelligence | Vision profile on recorded real images, no hardware | n/a |

   The lab publishes `docs/COMPATIBILITY.md`: target × capability × result, with "compiled",
   "emulated", "tested on hardware" kept distinct. Nothing is marked hardware-verified until a run on
   real hardware is recorded.

## Why

Many projects sharing one dashboard is not universality. The iOS analogy holds only if one core runs
across different devices by knowing what each can do and adapting to it. Profiles keep small
targets small: a project loads only what its profile needs.
