# 0002 · Claude develops MTDI in scheduled sessions and merges behind gates

**Status:** Accepted 2026-10-18 (decided by the project owner).

## Decision

Scheduled Claude Code sessions (Africa/Johannesburg time) work the backlog without prompting:
two build sessions each night and one midday check. Each session follows `ops/NIGHTLY.md`.

Claude merges its own pull request into `main` only when every gate passes:

1. CI is green on every job (all languages, self-test, manifests).
2. The studio browser tour (`tools/tour.mjs`) reports no errors on every page.
3. Reviews: CodeRabbit and Codex have no unresolved blocking finding, once installed.
4. The change does not touch deployment configuration (`vercel.json`, `app.py` entry,
   workflows), secrets, licences, or delete data. Those wait for the owner.

The owner reviews the morning report (`ops/reports/`) and can revert any merge.

## Why

The owner reviews rather than directs. A chat session cannot run indefinitely; scheduled
sessions can, and pull requests plus CI give every change a record and a referee.

## Guardrails

No paid API, paid service, hardware actuation, public posting or data deletion without the
owner's approval. One backlog item per session (two if both are small). Every session ends
with a report, even when it changes nothing. The owner stops everything by disabling the
scheduled tasks.
