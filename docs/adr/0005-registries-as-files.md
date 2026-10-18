# 0005 · Registries are versioned files first

**Status:** Accepted 2026-10-18.

## Decision

The module, integration, dataset, model and experiment registries are JSON files in the
repository (`registry/`), read and validated by `mtdi.registry`.

## Why

Overnight agents work through pull requests; files make every registry change reviewable,
diffable and revertible, with no database to provision. A hosted database (for example
Postgres through the Vercel Marketplace) comes when the deployed workbench needs shared,
writable state; a new record will decide it.
