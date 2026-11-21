// Real Cloudflare workerd/Miniflare R2+D1 integration (no account credentials/network).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { Miniflare } from "miniflare";

const worker = fileURLToPath(new URL("./worker.mjs", import.meta.url));
const sql = fileURLToPath(new URL("./migrations/0001_source_vintages.sql", import.meta.url));
const envelope = process.env.PRIVATE_ENVELOPE;
if (!envelope) throw new Error("PRIVATE_ENVELOPE required in temporary private CI workspace");
const approved = readFileSync(envelope);
const HASH = "a6f040f7a1d43afa8020bf22168f0393edd8fceb8337b981c04445a6e6704cb3";
const OBJECT = "objects/" + HASH + ".json";
const INBOX = "inbox/reviewed-gem-gas-pipelines-2025-11.json";
const digest = bytes => createHash("sha256").update(bytes).digest("hex");

async function runtime(enabled) {
  const mf = new Miniflare({
    modules: true,
    scriptPath: worker,
    compatibilityDate: "2026-11-21",
    cf: false,
    bindings: { IMPORT_ENABLED: enabled ? "true" : "false" },
    r2Buckets: { ARCHIVE: "private-archive", ARCHIVE_BACKUP: "private-archive-backup" },
    d1Databases: { DB: "private-vintage-index" },
  });
  const db = await mf.getD1Database("DB");
  await db.exec(readFileSync(sql, "utf8"));
  const primary = await mf.getR2Bucket("ARCHIVE");
  const backup = await mf.getR2Bucket("ARCHIVE_BACKUP");
  return { mf, db, primary, backup, scheduler: await mf.getWorker() };
}
const count = async db => (await db.prepare("SELECT count(*) AS n FROM asset_vintages").first()).n;

test("workerd: disabled importer preserves private staging and exposes no HTTP API", async () => {
  const { mf, db, primary, backup, scheduler } = await runtime(false);
  try {
    await primary.put(INBOX, approved);
    const response = await mf.dispatchFetch("http://localhost/ingest", { method: "POST" });
    assert.equal(response.status, 404);
    assert.equal(await response.text(), "Not Found");
    const result = await scheduler.scheduled({ cron: "31 3 * * *" });
    assert.equal(result.outcome, "ok");
    assert.equal(await count(db), 0);
    assert.ok(await primary.head(INBOX));
    assert.equal(await primary.head(OBJECT), null);
    assert.equal(await backup.head(OBJECT), null);
  } finally { await mf.dispose(); }
});

test("workerd: real R2 conditional objects + D1 index + cron idempotence", async () => {
  const { mf, db, primary, backup, scheduler } = await runtime(true);
  try {
    await primary.put(INBOX, approved);
    const first = await scheduler.scheduled({ cron: "31 3 * * *" });
    assert.equal(first.outcome, "ok");
    assert.equal(await count(db), 1);
    assert.equal(await primary.head(INBOX), null);
    const record = await db.prepare("SELECT object_sha256, object_key, dataset, rows, rights_state FROM asset_vintages").first();
    assert.deepEqual(
      { sha: record.object_sha256, key: record.object_key, dataset: record.dataset, rows: record.rows, rights: record.rights_state },
      { sha: HASH, key: OBJECT, dataset: "gem-gas-pipelines", rows: 4246, rights: "approved_public" }
    );
    const a = new Uint8Array(await (await primary.get(OBJECT)).arrayBuffer());
    const b = new Uint8Array(await (await backup.get(OBJECT)).arrayBuffer());
    assert.equal(digest(a), HASH);
    assert.equal(digest(b), HASH);
    assert.equal(a.byteLength, b.byteLength);
    await primary.put(INBOX, approved);
    const second = await scheduler.scheduled({ cron: "31 3 * * *" });
    assert.equal(second.outcome, "ok");
    assert.equal(await count(db), 1, "No new version on duplicate run");
    assert.equal(await primary.head(INBOX), null);
    assert.equal((await db.prepare("SELECT count(*) AS n FROM writer_lock").first()).n, 0);
    assert.equal((await mf.dispatchFetch("http://localhost/private/history")).status, 404);
  } finally { await mf.dispose(); }
});
