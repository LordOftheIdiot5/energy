# V90.6g3 — private infrastructure source-vintage ledger

Status: **first implementation / local and CI research only**. This is not a running
Cloudflare R2/D1 archive or proof that 2026 GEM LNG data have been obtained.
It adds no website endpoints, new rows, licence approvals or public layers.

## Purpose

The current reviewed **November 2025** GEM gas pipeline atlas contains 4,246 projects
and 3,921 mapped routes (325 without). Future extracts may change IDs, status,
geometry and attributes. Never overwrite source history or treat a missing record
as a physical retirement.

The Python utility at scripts/private_asset_history.py implements a deterministic,
content-addressed **private local** ledger, separate from the public Pages builder.

## Retention and safety contract

- Explicit private directory **outside the GitHub repository**; the CLI rejects
  project-internal destinations. No raw archive committed or uploaded as public artifact.
- Single-writer exclusive file lock, failing on contention; stale locks require
  manual investigation rather than automatic unsafe removal.
- Immutable source-vintage objects under objects/<sha256>.json, with a SHA-256 verified
  ledger manifest retaining dataset, release YYYY-MM, retrieval UTC, source URL,
  licence, attribution, rights review, native-ID field, record count and coverage.
- Distinct native IDs only; non-finite numbers, malformed lon/lat geometry,
  duplicate IDs, missing provenance and unverified timestamps are rejected.
  Missing coordinates remain missing; country codes are accepted only as
  explicit two-letter uppercase identifiers. No synthetic coordinates.
- New corrected releases become additional immutable versions. Repeat input
  content is idempotent; conflicting rights notes for identical content are rejected.
- Change reports compare **exact source IDs**, never names or spatial proximity.
  New, changed, missing-from-next-complete-release, unresolved missing in partial
  releases and **explicit reported** retired/cancelled status transitions are
  separate classifications. Missing never means physically retired.
- Restore copies objects into an unused private directory and verifies all records
  and checksums. Public clearance requires specific reviewed rights evidence;
  that bookkeeping alone does not constitute legal permission.

## Example — existing reviewed 2025 pipeline baseline

The bootstrap calls the existing pinned GEM public-source validator and preserves
the 2025 data exactly. It does not download new GEM releases:

    python scripts/private_asset_history.py bootstrap-gem --archive /private/energy-history
    python scripts/private_asset_history.py verify --archive /private/energy-history
    python scripts/private_asset_history.py restore --archive /private/energy-history --target /private/energy-history-recovery

Use a separate actual private directory on the operating system. The add(root,
metadata, rows) Python API will admit a future LNG package only after official
download, package checksum, source-ID/geometry validation and source-specific rights
review. A new source remains review-required until that happens.

## Future private R2/D1 production gate — NOT IMPLEMENTED

1. Create a private R2 bucket for **original upstream bytes** and immutable revision
   objects, retaining checksum, attribution, vintage and source-specific licence.
   Use no public bucket access.
2. Build a private D1 index of source ID, release, status, provenance, object hash,
   completeness and geographic quality. Use version-checked/transactional
   single-writer admission; do not publish an index pointing to absent objects.
3. Run full restoration into a separate namespace, prove idempotent replay, and
   measure object-storage/API and D1 costs. Plan retention and backup policy.
4. Feed a separate rights-allowlisted public projection. The existing 2025 map
   stays unchanged until an authorized newer download and all UI regressions pass.
5. Require evidence dates for any owner relationship or operating status;
   source-reported 2025 status is not verified current operation.

## Test and release gate

The new GitHub workflow runs the local history tests, bootstraps reviewed GEM 2025
into a temporary **private** archive, verifies and restores it, and builds the
rights-allowlisted public site. The private ledger and immutable history objects
must not be included in the public artifact. Full production Atlas browser smoke
must pass after merge. A workflow success is not proof of a deployed R2/D1 database.
