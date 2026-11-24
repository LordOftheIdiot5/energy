import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  validateEnvelope, ingestEnvelope, verifyIndex,
  restoreMissingPrimary, processInbox
} from "./worker.mjs";
import worker from "./worker.mjs";

const file = process.env.PRIVATE_ENVELOPE;
if (!file) throw new Error("PRIVATE_ENVELOPE must point to a temporary, real reviewed GEM fixture");
const fixture = new Uint8Array(readFileSync(file));
const SHA = "a6f040f7a1d43afa8020bf22168f0393edd8fceb8337b981c04445a6e6704cb3";
const KEY = "objects/" + SHA + ".json";
const INBOX = "inbox/reviewed-gem-gas-pipelines-2025-11.json";

class Bucket {
  constructor() { this.objects = new Map(); this.failPut = false; this.calls = []; }
  async head(key) { return this.objects.has(key) ? { size: this.objects.get(key).byteLength } : null; }
  async get(key) {
    const data = this.objects.get(key);
    if (!data) return null;
    return { size: data.byteLength, async arrayBuffer() { return data.slice().buffer; } };
  }
  async put(key, value, options = {}) {
    this.calls.push(["put", key, options]);
    if (this.failPut) throw new Error("R2 temporary failure");
    if (options.onlyIf?.etagDoesNotMatch === "*" && this.objects.has(key)) return null;
    this.objects.set(key, new Uint8Array(value));
    return { size: new Uint8Array(value).byteLength };
  }
  async delete(key) { this.calls.push(["delete", key]); this.objects.delete(key); }
  set(key, bytes) { this.objects.set(key, new Uint8Array(bytes)); }
}
class DB {
  constructor() { this.lock = null; this.rows = new Map(); this.failInsert = false; this.calls = []; }
  prepare(sql) {
    const make = (...values) => ({
      run: async () => {
        this.calls.push(["run", sql, values]);
        if (sql.startsWith("INSERT OR IGNORE INTO writer_lock")) {
          if (this.lock) return { success: true, meta: { changes: 0 } };
          this.lock = values[0];
          return { success: true, meta: { changes: 1 } };
        }
        if (sql.startsWith("DELETE FROM writer_lock")) {
          const matches = this.lock === values[0]; if (matches) this.lock = null;
          return { success: true, meta: { changes: matches ? 1 : 0 } };
        }
        if (sql.startsWith("INSERT INTO asset_vintages")) {
          if (this.failInsert) throw new Error("D1 unavailable");
          const [dataset, release, object_sha256, object_key, rows, source_url,
                 retrieved_at, rights_state, license_url, metadata_json, admitted_at] = values;
          if (this.rows.has(object_sha256)) throw new Error("D1 unique constraint");
          this.rows.set(object_sha256, { dataset, release, object_sha256, object_key, rows,
            source_url, retrieved_at, rights_state, license_url, metadata_json, admitted_at });
          return { success: true, meta: { changes: 1 } };
        }
        throw new Error("Unexpected SQL run: " + sql);
      },
      first: async () => {
        this.calls.push(["first", sql, values]);
        if (sql.startsWith("SELECT object_sha256, metadata_json")) {
          const row = this.rows.get(values[2]);
          return row && row.dataset === values[0] && row.release === values[1] ? row : null;
        }
        if (sql.startsWith("SELECT object_sha256 FROM asset_vintages")) {
          const row = this.rows.get(values[0]);
          return row ? { object_sha256: row.object_sha256 } : null;
        }
        throw new Error("Unexpected SQL first: " + sql);
      },
      all: async () => {
        this.calls.push(["all", sql, values]);
        if (!sql.startsWith("SELECT dataset, release")) throw new Error("Unexpected SQL all");
        return { success: true, results: [...this.rows.values()] };
      },
    });
    return { bind: (...values) => make(...values), all: async () => make().all() };
  }
}
const setup = (enabled = true) => ({
  IMPORT_ENABLED: enabled ? "true" : "false", ARCHIVE: new Bucket(),
  ARCHIVE_BACKUP: new Bucket(), DB: new DB(),
});
const clone = value => JSON.parse(JSON.stringify(value));
const rewrite = callback => {
  const d = JSON.parse(new TextDecoder().decode(fixture));
  callback(d);
  return new TextEncoder().encode(JSON.stringify(d));
};

test("original pinned 2025 source passes fingerprint, source IDs and licence gate", async () => {
  const a = await validateEnvelope(fixture);
  assert.equal(a.metadata.rows, 4246);
  assert.equal(a.digest, SHA);
  assert.equal(a.metadata.rights_state, "approved_public");
  assert.equal(a.metadata.upstream_sha256.length, 64);
});
test("private import disabled by default, including when no bindings exist", async () => {
  assert.deepEqual(await processInbox({ IMPORT_ENABLED: "false" }), { status: "disabled" });
  const env = setup(false); env.ARCHIVE.set(INBOX, fixture);
  assert.equal((await processInbox(env)).status, "disabled");
  assert.equal(env.DB.rows.size, 0);
});
test("ingest commits verified primary and distinct backup before D1 pointer, then idempotent", async () => {
  const env = setup();
  env.ARCHIVE.set(INBOX, fixture);
  const result = await processInbox(env);
  assert.equal(result.status, "indexed");
  assert.equal(env.ARCHIVE.objects.has(INBOX), false);
  assert.equal(env.ARCHIVE.objects.has(KEY), true);
  assert.equal(env.ARCHIVE_BACKUP.objects.has(KEY), true);
  assert.equal((await verifyIndex(env)).verified, 1);
  assert.equal(env.DB.rows.size, 1);
  assert.equal(env.DB.lock, null);
  const again = await ingestEnvelope(env, fixture);
  assert.equal(again.status, "already-indexed");
  assert.equal(env.DB.rows.size, 1);
  assert.equal(env.ARCHIVE.calls.filter(x => x[1] === KEY && x[0] === "put").length, 1);
  assert.equal(env.ARCHIVE_BACKUP.calls.filter(x => x[1] === KEY && x[0] === "put").length, 1);
});
test("backup write fails => no published index, inbox retained, lock released", async () => {
  const env = setup();
  env.ARCHIVE.set(INBOX, fixture); env.ARCHIVE_BACKUP.failPut = true;
  await assert.rejects(processInbox(env), /R2 temporary failure/);
  assert.equal(env.DB.rows.size, 0);
  assert.equal(env.DB.lock, null);
  assert.ok(env.ARCHIVE.objects.has(INBOX));
  assert.ok(env.ARCHIVE.objects.has(KEY));
  assert.equal(env.ARCHIVE_BACKUP.objects.has(KEY), false);
});
test("D1 failure retains both immutable objects and inbox for retry", async () => {
  const env = setup();
  env.ARCHIVE.set(INBOX, fixture); env.DB.failInsert = true;
  await assert.rejects(processInbox(env), /D1 unavailable/);
  assert.equal(env.DB.lock, null);
  assert.equal(env.DB.rows.size, 0);
  assert.ok(env.ARCHIVE.objects.has(INBOX));
  assert.ok(env.ARCHIVE_BACKUP.objects.has(KEY));
  env.DB.failInsert = false;
  assert.equal((await processInbox(env)).status, "indexed");
});
test("tampered primary or backup is detected; no automatic overwrite", async () => {
  const env = setup();
  await ingestEnvelope(env, fixture);
  env.ARCHIVE_BACKUP.set(KEY, new TextEncoder().encode("{}"));
  await assert.rejects(verifyIndex(env), /immutable-object-corruption/);
  await assert.rejects(ingestEnvelope(env, fixture), /immutable-object-corruption/);
  assert.equal(env.DB.rows.size, 1);
  env.ARCHIVE_BACKUP.set(KEY, env.ARCHIVE.objects.get(KEY));
  env.ARCHIVE.set(KEY, new TextEncoder().encode("{}"));
  await assert.rejects(ingestEnvelope(env, fixture), /immutable-object-corruption/);
});
test("restore can repair only absent primary from verified independent backup", async () => {
  const env = setup();
  await ingestEnvelope(env, fixture);
  env.ARCHIVE.objects.delete(KEY);
  assert.deepEqual(await restoreMissingPrimary(env, SHA), { restored: true, sha256: SHA });
  assert.equal((await verifyIndex(env)).verified, 1);
  await assert.rejects(restoreMissingPrimary(env, SHA), /restore-will-not-overwrite/);
  await assert.rejects(restoreMissingPrimary(env, "x".repeat(64)), /unreviewed-restore/);
});
test("existing writer lock prevents imports and preserves source staging", async () => {
  const env = setup();
  env.DB.lock = "another-archive-writer";
  env.ARCHIVE.set(INBOX, fixture);
  await assert.rejects(processInbox(env), /writer-locked/);
  assert.equal(env.DB.lock, "another-archive-writer");
  assert.equal(env.DB.rows.size, 0);
  assert.ok(env.ARCHIVE.objects.has(INBOX));
});
test("unknown release, rights mismatch and source-content tampering fail before R2 or D1", async () => {
  const cases = [
    d => { d.metadata.release = "2026-10"; },
    d => { d.metadata.rights_state = "review_required"; },
    d => { d.metadata.rights_evidence = ""; },
    d => { d.metadata.license = "not cleared"; },
    d => { d.metadata.upstream_sha256 = "0".repeat(64); },
    d => { d.metadata.rows = 4245; },
    d => { d.snapshot_text = d.snapshot_text.replace("2025-11", "2026-10"); },
  ];
  for (const change of cases) {
    const env = setup();
    await assert.rejects(ingestEnvelope(env, rewrite(change)));
    assert.equal(env.DB.rows.size, 0);
    assert.equal(env.DB.lock, null);
    assert.equal(env.ARCHIVE.objects.size, 0);
    assert.equal(env.ARCHIVE_BACKUP.objects.size, 0);
  }
});
test("no public Worker endpoint accepts any method or path", async () => {
  for (const path of ["/", "/ingest", "/admin/status", "/api/v1/download"]) {
    const r = await worker.fetch(new Request("https://example.test" + path, { method: "POST" }));
    assert.equal(r.status, 404);
    assert.equal(await r.text(), "Not Found");
  }
});
test("schedule in default disabled mode never requires credentials or touches stores", async () => {
  const promises = [];
  const ctx = { waitUntil(p) { promises.push(p); } };
  await worker.scheduled({}, { IMPORT_ENABLED: "false" }, ctx);
  await Promise.all(promises);
  assert.equal(promises.length, 1);
});
