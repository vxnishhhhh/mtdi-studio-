# 0003 · The workbench lives inside the existing studio

**Status:** Accepted 2026-10-18 (decided by the project owner).

## Decision

Project creation, the agent center, the registries and the data library are new pages in the
existing I³ studio (Dash + Flask), sharing its theme, NVTRA, hand vision and Aether.

## Why

One application, one deployment, one test suite. A second React application (for example
with 21st.dev components) would double the stacks to maintain for a visual gain the studio's
own design system already provides.

## Revisit when

A workbench feature needs client-side interaction Dash cannot deliver acceptably. Then a new
record weighs a React island inside the studio against a separate app.
