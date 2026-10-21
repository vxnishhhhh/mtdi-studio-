# Owner brief for MTDI 5 (21 Oct 2026, answer to "question 10")

> **Hard rule (owner, 21 Oct): never start a subscription, trial or anything the owner has to pay for. Free tiers only. The only paid thing is the owner's Claude subscription.**

Binding input for every session. It goes with `2026-10-21-whiteboard.md` and `2026-10-21-chatgpt-handoff.md`.
The owner dictated it by voice: "MTTI" means **MTDI**, "Ether" means **Aether**, "EVS" means Environmental
Intelligence. The owner says this is about 10% of the planning. Claude directs the project, makes its own
decisions and adds features. The plan is a guide, not a straight line: ideas found along the way are welcome.

## The four things that make MTDI 5 what it is
1. **Machine learning**: the focus of MTDI 5. It gets better over time.
2. **Data**: "ML without data is nothing". Store everything; make the database as large as possible.
3. **MATLAB**: the primary ML and maths tool. Other tools too (Create ML on Mac, Python and more).
4. **Agents**: AI agents that actually do work (graphs, analysis and more). Add an agent only where one is missing.
- Everything must run on a **Raspberry Pi 5** where feasible (also Mac). Estimate what fits on the Pi and
  what goes to the cloud.
- Software and firmware only. **After every update, tell the owner what hardware they need to do.**

## Pillar by pillar (MTDI 4 weakness -> MTDI 5 requirement)
- **Environmental Intelligence**: today only one baseline for one sensor at a time. Needs sensor fusion,
  more algorithms, **calibration** (missing in 4.0), real data, and to be universal for almost every sensor.
- **Validation Chamber**: today it has **no real data**. Expand the database. It stays a **separate pillar**
  but is **linked** to Environmental Intelligence: each feeds the other for accuracy.
- **Computational Core**: today the tools are **not fused**. Fuse Notion, GitHub, MATLAB, Vercel,
  CodeRabbit, Cursor and a heavy research tool; Claude picks the rest. All processing happens here; must run on a Pi 5.
- **NVTRA Intelligence**: today it is API-key only. Add **local AI** too. Add a back-end-only system prompt
  the user cannot edit that enforces safety and makes it think like an engineer and act human
  ("be conscious"). Model it on **Apple Intelligence**: research what Apple puts on top of the models
  (own instructions, UI, effects, privacy) and build NVTRA the same way. It must be able to **go online**.
  **NVTRA branding**: NVTRA (Navatra) is the owner's website business ("we vibe code websites"), a sponsor of
  MTDI 5. Bring the brand into the intelligence and the site.
- **I³ interface**: "not perfect, getting boring". Keep it and build on it: more scroll animations,
  presets and templates (21st.dev and other front-end tools), fix the current imperfections, **much more 3D**.
  3D and front-end design go to **Astra (Codex)**, working with Claude.
- **Aether**: the human layer. Jokes in code comments, a "hours wasted here" counter (meme), visual
  elements, personality based on the owner, and an **MTDI game in 3D** (by Astra) inside the Aether terminal.
  Keep the existing terminal and Easter eggs and add more.
- **New pillars**: add them where they make MTDI more accurate or efficient, not for the sake of it.
  Example from the owner: a **Research** pillar (brand it better) where the AI goes online and gathers data.

## Research and data
- Claude does research and collects as much data as possible: sensor readings, live readings, experiments,
  datasets, algorithms, ML patterns, hypotheses, cancer research and "everything related to tech".
  An offline mode is needed. Size isn't a concern ("20 GB is fine").
- **Credit everything.** A credits page on the site credits every dataset, source and kilobyte, with no
  length limit. It includes the acknowledgements in the Inductra Vaion ISF final report (owner's desktop,
  Eskom Expo 2026 folder).

## Code conventions
- Comments are guides: context, how the owner prompts Claude, what is happening and what to do next, so
  another AI or person can extend the code. Add Aether jokes and the "hours wasted" counters in comments.
- Codex reviews code; Astra (Codex) works with Claude on UI and 3D.

## Reporting (each update in chat)
A table, plus: new features, ideas, next steps, what Claude struggled with, weaknesses, what should have
been done, and **hardware the owner needs to do**.

## Follow-up answers (21 Oct)
- Bulk data can be 100 GB or more, in free cloud storage. Notion holds the catalogue and notes. Data must be useful for ML; start with 25 high-value datasets and keep growing.
- The Computational Core lists every service used to build MTDI 5, and users can use the same services to build their own projects.
- Hardware: Raspberry Pi 5 with 8 GB RAM, no AI HAT. MacBook Pro M5 (base chip), 24 GB RAM, 1 TB SSD.
- MATLAB licence is unknown. Name of the event: Eskom Expo **ISF** (not ISEF).
- NVTRA: website https://nvtra-xxxx.vercel.app; logo `brand/nvtra-logo.webp`; gold #E3B945 on black.
- NVTRA personality: think exactly like an engineer, talk like a person, with personality and Aether.
- NVTRA vs Computational Core: NVTRA is its own pillar. It takes the Computational Core's processed output and processes it further with AI.
- Aether voice: Gen Z, like a 17-18 year old, jokes, the owner's humour, "2 a.m. coding" energy that changes with the time of day. **No brain rot.**
- Storage: anything online that holds a lot of data; **not local** unless the owner sets something up.
- The owner reports a MATLAB link (files edited from the MATLAB app). No MATLAB tool is visible in these sessions yet; find out which path it uses (MATLAB Drive or GitHub sync).
