# 0001 · Computational Core is pillar 02; Aether is the layer across all pillars

**Status:** Accepted 2026-10-18 (decided by the project owner).

## Decision

| # | Pillar | Role |
|---|---|---|
| 00 | Validation Chamber | Evidence |
| 01 | Environmental Intelligence | Baselines |
| 02 | Computational Core | Computation: ML, mathematics, simulation, agents, integrations |
| 03 | NVTRA | Explanation |
| 04 | I³ | Interface |
| ·· | Aether | The soul layer across every pillar: the terminal, Easter eggs, purpose, authorship. Shown, never scored |

## Why

MTDI's computational work (machine learning, MATLAB, language models, storage, integrations)
had no home: it lived in loose modules. Making it a pillar gives every algorithm, engine and
integration one registry and one contract. Aether is not a stage data passes through; it is
the character of the whole system, so it is a layer, not a pillar in the signal path.

## Consequences

* `mtdi/pillars/__init__.py` defines `PILLARS` (five) and `AETHER` (the layer).
* The studio's MTDI page and constellation show the Computational Core; Aether stays reachable,
  with its terminal and every Easter egg (backlog S1-01).
* Optional specialist modules (Chronos, Memory, Adaptive) live inside the Computational Core.
