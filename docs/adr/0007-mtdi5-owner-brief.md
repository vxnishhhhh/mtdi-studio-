# 0007 · MTDI 5 direction from the owner brief

Status: accepted (Claude, as director) · 21 Oct 2026 · Source: ops/inbox/2026-10-21-owner-brief.md

## Decisions
1. **The four cores of MTDI 5** are ML, data, MATLAB and agents. Every backlog item says which ones it serves.
2. **Pillars:** 00 Validation Chamber, 01 Environmental Intelligence, 02 Computational Core,
   03 NVTRA Intelligence, 04 I³, and a new **05 Research** pillar (working brand: *Horizon*). Research
   collects, licenses, credits and catalogues data and feeds pillars 00 and 01. Aether stays a layer.
   Data storage (the Data Library) is part of Research, not its own pillar, until there is evidence it
   needs to be. No other pillars yet.
3. **00 and 01 are linked:** Environmental Intelligence sends fused, calibrated estimates to Validation,
   and Validation sends quality and detection limits back to Environmental. They are two pillars and one loop.
4. **NVTRA layers:** a fixed system policy (safety and engineer persona, not editable by users), then
   tools and agents, then model routing (local first on Pi 5 or Mac, with cloud API as a fallback), then
   NVTRA-branded UI and effects. The design is modelled on Apple Intelligence's layering and is
   researched before it is built.
5. **Data at scale:** the git repo holds the catalogue (source, licence, checksum, size, credit), not the
   bulk files. Bulk data lives in object storage or GitHub Releases and is pulled for offline mode. A
   20 GB git repo would break cloning, CI and Vercel.
6. **3D and front end:** Claude writes specs and prompts for Astra (Codex). Claude cannot start Codex
   itself, so the owner relays the prompts or connects Codex to the repo.
7. **Reports** follow the owner's format, including the hardware owed by the owner.
