# Cloudflare private source-history staging — V90.6g3

**Current status: implementation staged in GitHub, NOT a deployed Cloudflare service.**
This is independent of the public Energy Pages build and the existing watchdog.

## Private resources and invariant

- Worker: nordl-energy-private-history, no public route, workers_dev=false,
  preview_urls=false, and no HTTP ingestion/admin endpoints (all return 404).
- R2 source archive: nordl-energy-history-private, private bucket with no public
  r2.dev/domain access. Binding ARCHIVE.
- **Separate** private R2 backup bucket:
  nordl-energy-history-private-backup. Binding ARCHIVE_BACKUP.
- D1: nordl-energy-history-index. Binding DB, migration
  migrations/0001_source_vintages.sql.
- One D1 writer lock at a time; a crashed writer leaves a retained lock and
  blocks new imports until an operator verifies both R2 copies and D1 before
  clearing it. No automatic lease stealing during a delayed/backfilled write.
- Archive objects have immutable, content-addressed names. R2 writes use
  etagDoesNotMatch="*" and every existing object is SHA-256 revalidated; corrupt
  objects are never overwritten. Both independent R2 copies must verify before
  the D1 index pointer is inserted.
- Staging object is deleted **only after** D1 commit plus dual-copy integrity
  verification. Otherwise the original private inbox remains for replay.
- Only the reviewed November **2025** GEM pipeline baseline is accepted
  (pinned object hash, upstream table and route hashes, 4,246 source IDs,
  exact URL/licence/rights-evidence and complete scope). No 2026 LNG/import
  permissions are inferred.
- D1 is a private **version index**, not proof of current operation or rights
  to publicly redistribute a new package.

## Before ANY real deployment

1. Use Wrangler on a trusted operator machine authenticated to the correct
   Nordl Cloudflare account. Review R2 and D1 storage pricing, retention, data
   location/compliance and billing limits. No account token goes into the repo.
2. Create the **two separate private R2 buckets** and the **new D1 database**.
   Confirm actual Cloudflare resource IDs. Never reuse the public Pages bucket
   or the watchdog's Durable Object.
3. Copy wrangler.template.toml to a local ignored wrangler.toml (or a file
   outside checkout), replace REPLACE_WITH_REAL_D1_DATABASE_UUID with the
   actual Cloudflare D1 UUID and verify resource/account match. The source
   template is intentionally **not deployable as-is**.
4. Apply the D1 migration to the intended database, inspect resulting tables
   and confirm no duplicate writer process. Do not create a new public route.
5. Deploy the Worker with IMPORT_ENABLED=false. Verify workers_dev and
   preview URLs are disabled, and the Worker has no public URL.
6. On a private machine (NOT a public Actions artifact), bootstrap the
   previously validated GEM source-history locally, export the exact inbox
   envelope, and upload **only to the private primary R2 inbox key**. Confirm
   original checksum and no leaked credentials.
7. Change IMPORT_ENABLED=true **only after** both R2 bindings, D1 schema,
   quota alerting, private bucket access policies, dry-run and restore tests
   are verified. Run a single scheduled ingest, inspect D1 and both R2 hashes.
   Turn IMPORT_ENABLED=false for steady state if there is no further approved
   release to import.
8. Exercise restoring a deliberately absent **test** primary object from the
   private backup bucket into an independent test namespace before depending
   on recovery. Do not delete a real live primary just to test restoration.
9. Configure production health monitoring: last successful ingest, stale
   writer lock, source hash mismatch, missing backup, D1 errors, R2 cost/usage.
   Alerts must never leak raw private records, API tokens or bucket endpoints.

Example manual commands (**review before running**):

    cd deploy/cloudflare-history
    npx wrangler@4.164.0 r2 bucket create nordl-energy-history-private
    npx wrangler@4.164.0 r2 bucket create nordl-energy-history-private-backup
    npx wrangler@4.164.0 d1 create nordl-energy-history-index
    # Copy and fill wrangler.toml *locally*; DO NOT commit credentials/IDs.
    npx wrangler@4.164.0 d1 migrations apply nordl-energy-history-index --remote
    npx wrangler@4.164.0 deploy --config wrangler.toml

After the local Python bootstrap:

    python scripts/private_asset_history.py bootstrap-gem --archive /secure/energy-history
    python scripts/export_private_cloudflare_envelope.py --archive /secure/energy-history --out /secure/reviewed-gem-2025-inbox.json
    # Inspect local SHA checks and the exact expected private target:
    npx wrangler@4.164.0 r2 object put nordl-energy-history-private/inbox/reviewed-gem-gas-pipelines-2025-11.json --file=/secure/reviewed-gem-2025-inbox.json --remote

**Important:** The exact CLI options can change by Wrangler version; inspect
wrangler help before running. Upload only to the private bucket, never through
GitHub Pages, a public artifact, or a public R2 URL.

## Operational acceptance still pending

- Verified real R2 bucket names/bindings, D1 UUID, successful remote migration,
  verified disabled-worker deployment, one real source import and D1 index,
  independent backup restore drill, concurrency conflict simulation, retention
  and cost guardrails, and alert delivery.
- This branch only tests local/offline code plus SQLite schema with fake R2/D1
  bindings and an actual previously vetted GEM source snapshot; **do not mark
  the persistent cloud archive operational** until the above is evidenced.
- The public MapLibre Atlas, historical 2025 pipeline data, its caveat labels,
  and all user-facing Energy pages remain unchanged.

References:
- Cloudflare R2 Workers API, conditional put/get semantics:
  https://developers.cloudflare.com/r2/api/workers/workers-api-reference/
- Cloudflare R2 consistency and conditional writes:
  https://developers.cloudflare.com/r2/reference/consistency/
- Cloudflare D1 batch, prepared statement and schema:
  https://developers.cloudflare.com/d1/worker-api/d1-database/
