# Spec for Astra · the Aether game (3D)

A small 3D game inside the Aether terminal of the MTDI studio. Owner brief, ADR 0007: "an MTDI game in 3D".
This is a spec to build from. It is not built yet.

## Constraints (hard)
- **Free only.** Three.js is already vendored at `public/assets/lunar/three.min.js`. Use it; no new paid or keyed services.
- **Runs on a Pi 5 (8 GB, no GPU accelerator) in Chromium.** Target 30 fps at 1280×720 there. Under 300 draw calls, under 100k triangles, no post-processing by default.
- **Loads lazily.** Nothing is downloaded until the player opens it. Total assets under 3 MB.
- **Respects `prefers-reduced-motion`** with a calm mode: no camera shake, slower motion.
- **Never touches the signal path.** It may *read* the live packet (`/mtdi/packet`) for flavour; it never writes or acts.

## Concept: "Baseline"
The player flies a small probe through a field that is drawn from the project's live channels.
- Each channel is a lane. Its height follows the channel's `deviation`, so a quiet environment gives a calm field and an event gives a spike.
- Collect "evidence" orbs. Clipped or stale channels turn their lane grey: no points there, which teaches what those states mean.
- With no hardware connected the game uses SIMULATED data and says so on screen, in the same way the rest of MTDI labels it.
- Score screen: hours played, next to the repo's real `HOURS-WASTED` total (from `python -m mtdi aether --json`, baked at build time). This is the joke.

## Look
- Gold `#E3B945` on near-black, matching the NVTRA mark. Thin lines, no textures.
- Font: DM Mono, as used in the studio.

## Deliverables
1. `public/assets/aether-game/game.js`: a self-contained ES module exporting `mount(host, {packetUrl})`.
2. A button in the Aether section that loads and mounts it.
3. A Playwright smoke test: it opens, renders one frame, and closes with no console errors.
