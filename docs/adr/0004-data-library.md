# 0004 · Real data: collected by Actions, stored as releases, catalogued in Notion

**Status:** Accepted 2026-10-18.

## Decision

* Collectors (one small tested module per source) run in GitHub Actions on a schedule, which
  has open internet; the development sandbox does not reach science hosts.
* Data files (CSV/JSON, checksummed) are stored as versioned assets; small samples live in the
  repository for tests.
* Notion holds one catalog page per dataset: source, licence, retrieved-at, schema, rows,
  checksum, link, projects using it. Notion is not the bulk store: its API allows about three
  requests a second and small blocks.
* Real recorded data replaces simulation in the digital twin and Validation Chamber, always
  labelled with its source.

## Rules

Public data only; licence recorded before download; no personal or patient-identifiable data;
medical and drug data labelled research-only; computational results are hypotheses, never
clinical claims.
