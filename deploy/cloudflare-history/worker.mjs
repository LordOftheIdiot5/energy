// Private R2/D1 asset-vintage archive. NO HTTP admin endpoint.
// Only the pinned, previously approved November 2025 GEM source can be admitted.
// No import is enabled unless private resources AND explicit IMPORT_ENABLED=true exist.
const SCHEMA = 1;
const SOURCE = Object.freeze({
  dataset: "gem-gas-pipelines",
  release: "2025-11",
  rows: 4246,
  sha256: "a6f040f7a1d43afa8020bf22168f0393edd8fceb8337b981c04445a6e6704cb3",
  upstream: "33cf8df6a6ba9bfaad0fd6c046b8b0be6d746bba014c7e31cd6b4618ed1605f1",
  geometry: "d2d940433656e58ba32a852aba6f30300846ab52375b0139f02df88d691f4378",
  url: "https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/",
  license: "https://creativecommons.org/licenses/by/4.0/",
});
const INBOX = "inbox/reviewed-gem-gas-pipelines-2025-11.json";
const MAX_BYTES = 9_000_000;
const MAX_SNAPSHOT = 6_000_000;
const SHA = /^[a-f0-9]{64}$/;
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
const encoder = new TextEncoder();

class GateError extends Error {
  constructor(code) { super(code); this.code = code; }
}
const guard = (ok, code) => { if (!ok) throw new GateError(code); };
const hash = async bytes => {
  const b = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return [...b].map(x => x.toString(16).padStart(2, "0")).join("");
};
const jsonObject = o => o !== null && typeof o === "object" && !Array.isArray(o);
const present = x => typeof x === "string" && x.trim().length > 0;
const eqJson = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const objectKey = sha => {
  guard(typeof sha === "string" && SHA.test(sha), "invalid-digest");
  return "objects/" + sha + ".json";
};
function bindings(env) {
  guard(env && env.ARCHIVE && env.ARCHIVE_BACKUP && env.DB, "missing-private-bindings");
  guard(env.ARCHIVE !== env.ARCHIVE_BACKUP, "backup-must-be-separate-bucket");
  return env;
}
async function readBounded(obj, limit = MAX_BYTES) {
  guard(obj && typeof obj.size === "number" && obj.size > 0 && obj.size <= limit, "r2-object-size");
  const bytes = new Uint8Array(await obj.arrayBuffer());
  guard(bytes.byteLength <= limit, "r2-read-size");
  return bytes;
}
function parseMeta(meta) {
  guard(jsonObject(meta), "invalid-provenance");
  guard(meta.dataset === SOURCE.dataset && meta.release === SOURCE.release, "unapproved-source-release");
  guard(meta.id_field === "id" && meta.coverage === "complete", "unapproved-source-scope");
  guard(meta.rights_state === "approved_public" && present(meta.rights_evidence) &&
        meta.rights_evidence.includes("PR #93"), "missing-specific-rights-review");
  guard(meta.source_url === SOURCE.url && meta.license === SOURCE.license && present(meta.attribution),
        "unapproved-source-rights");
  guard(meta.upstream_sha256 === SOURCE.upstream &&
        meta.geometry_upstream_sha256 === SOURCE.geometry, "unreviewed-upstream-fingerprint");
  guard(typeof meta.retrieved_at === "string" &&
        /(?:Z|[+-]\d{2}:\d{2})$/.test(meta.retrieved_at) &&
        Number.isFinite(Date.parse(meta.retrieved_at)), "undated-source-retrieval");
  guard(typeof meta.object_sha256 === "string" && meta.object_sha256 === SOURCE.sha256 &&
        meta.rows === SOURCE.rows, "unapproved-source-hash-or-count");
  return meta;
}
export async function validateEnvelope(bytes) {
  guard(bytes instanceof Uint8Array && bytes.byteLength <= MAX_BYTES && bytes.byteLength > 20, "invalid-envelope-size");
  let envelope;
  try { envelope = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
  catch { throw new GateError("malformed-envelope"); }
  guard(jsonObject(envelope) && envelope.schema_version === SCHEMA && present(envelope.snapshot_text),
        "missing-source-snapshot");
  const meta = parseMeta(envelope.metadata);
  guard(encoder.encode(envelope.snapshot_text).byteLength <= MAX_SNAPSHOT, "snapshot-too-large");
  const original = encoder.encode(envelope.snapshot_text);
  guard(await hash(original) === SOURCE.sha256, "snapshot-fingerprint-mismatch");
  let data;
  try { data = JSON.parse(envelope.snapshot_text); } catch { throw new GateError("malformed-snapshot"); }
  guard(data.schema_version === SCHEMA && data.dataset === SOURCE.dataset &&
        data.release === SOURCE.release && data.id_field === "id" &&
        Array.isArray(data.rows) && data.rows.length === SOURCE.rows, "snapshot-schema");
  const seen = new Set();
  for (const row of data.rows) {
    guard(jsonObject(row) && present(row.id) && row.id.length < 401 && !seen.has(row.id),
          "missing-or-duplicate-native-id");
    seen.add(row.id);
    guard(!Object.hasOwn(row, "operating_now") && !Object.hasOwn(row, "verified_current") &&
          !Object.hasOwn(row, "current_owner"), "invented-current-claims");
    guard(row.status === undefined || row.status === null || typeof row.status === "string",
          "invalid-source-status");
  }
  guard(seen.size === SOURCE.rows, "native-id-count");
  return { metadata: meta, sourceBytes: original, digest: SOURCE.sha256 };
}
async function verifyObject(bucket, key, digest) {
  const obj = await bucket.get(key);
  guard(obj, "missing-immutable-object");
  const bytes = await readBounded(obj, MAX_SNAPSHOT);
  guard(await hash(bytes) === digest, "immutable-object-corruption");
  return bytes;
}
async function ensureObject(bucket, key, raw, digest) {
  const existing = await bucket.head(key);
  if (existing) {
    await verifyObject(bucket, key, digest);
    return "existing";
  }
  // R2 Workers API precondition: create only if the key does not yet exist.
  const result = await bucket.put(key, raw, {
    onlyIf: { etagDoesNotMatch: "*" },
    httpMetadata: { contentType: "application/json" },
  });
  if (result === null) {
    await verifyObject(bucket, key, digest);
    return "existing";
  }
  await verifyObject(bucket, key, digest);
  return "created";
}
async function acquire(db) {
  const token = crypto.randomUUID();
  const acquired = new Date().toISOString();
  const result = await db.prepare(
    "INSERT OR IGNORE INTO writer_lock (id, token, acquired_at) VALUES (1, ?, ?)"
  ).bind(token, acquired).run();
  guard(result.success === true && result.meta && result.meta.changes === 1, "writer-locked");
  return token;
}
async function release(db, token) {
  const r = await db.prepare("DELETE FROM writer_lock WHERE id = 1 AND token = ?").bind(token).run();
  guard(r.success === true && r.meta?.changes === 1, "writer-lock-release-failed");
}
async function indexRow(db, meta) {
  return db.prepare("SELECT object_sha256, metadata_json, rows, object_key FROM asset_vintages WHERE dataset = ? AND release = ? AND object_sha256 = ?")
    .bind(meta.dataset, meta.release, meta.object_sha256).first();
}
function indexMeta(meta) {
  // Immutable source metadata, no current operations, and no credential fields.
  const fields = ["dataset","release","source_url","retrieved_at","license","attribution",
                  "rights_state","rights_evidence","coverage","id_field",
                  "upstream_sha256","geometry_upstream_sha256","rows","object_sha256","located_rows"];
  const clean = {};
  for (const field of fields) if (Object.hasOwn(meta, field)) clean[field] = meta[field];
  return JSON.stringify(clean);
}
export async function ingestEnvelope(env, bytes) {
  bindings(env);
  const parsed = await validateEnvelope(bytes); // No storage writes before all source gates.
  const meta = parsed.metadata, key = objectKey(parsed.digest);
  const token = await acquire(env.DB);
  let completed = false;
  try {
    const existing = await indexRow(env.DB, meta);
    const clean = indexMeta(meta);
    if (existing) {
      guard(existing.object_sha256 === parsed.digest && existing.metadata_json === clean &&
            existing.rows === SOURCE.rows && existing.object_key === key, "indexed-provenance-conflict");
      await verifyObject(env.ARCHIVE, key, parsed.digest);
      await verifyObject(env.ARCHIVE_BACKUP, key, parsed.digest);
      completed = true;
      return { status: "already-indexed", sha256: parsed.digest, rows: SOURCE.rows };
    }
    // Both primary AND independent backup commit before the D1 pointer can exist.
    await ensureObject(env.ARCHIVE, key, parsed.sourceBytes, parsed.digest);
    await ensureObject(env.ARCHIVE_BACKUP, key, parsed.sourceBytes, parsed.digest);
    const result = await env.DB.prepare(
      "INSERT INTO asset_vintages (dataset, release, object_sha256, object_key, rows, source_url, retrieved_at, rights_state, license_url, metadata_json, admitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(meta.dataset, meta.release, parsed.digest, key, SOURCE.rows, meta.source_url,
           meta.retrieved_at, meta.rights_state, meta.license, clean,
           new Date().toISOString()).run();
    guard(result.success === true && result.meta?.changes === 1, "index-commit-failed");
    completed = true;
    return { status: "indexed", sha256: parsed.digest, rows: SOURCE.rows };
  } finally {
    // Never automatically discard the lock if we cannot account for its token.
    await release(env.DB, token);
  }
}
export async function verifyIndex(env) {
  bindings(env);
  const result = await env.DB.prepare(
    "SELECT dataset, release, object_sha256, object_key, rows, source_url, rights_state, metadata_json FROM asset_vintages ORDER BY admitted_at, object_sha256 LIMIT 101"
  ).all();
  guard(result.success === true && Array.isArray(result.results) && result.results.length <= 100,
        "index-scan-failed-or-too-large");
  for (const row of result.results) {
    guard(row.dataset === SOURCE.dataset && row.release === SOURCE.release &&
          row.rows === SOURCE.rows && row.source_url === SOURCE.url &&
          row.rights_state === "approved_public" &&
          row.object_sha256 === SOURCE.sha256 &&
          row.object_key === objectKey(row.object_sha256), "unreviewed-index-entry");
    const meta = JSON.parse(row.metadata_json);
    parseMeta(meta);
    guard(indexMeta(meta) === row.metadata_json, "index-provenance-tamper");
    const [primary, backup] = await Promise.all([
      verifyObject(env.ARCHIVE, row.object_key, row.object_sha256),
      verifyObject(env.ARCHIVE_BACKUP, row.object_key, row.object_sha256),
    ]);
    guard(primary.byteLength === backup.byteLength, "backup-size-mismatch");
  }
  return { verified: result.results.length, archived: result.results.length > 0 };
}
export async function restoreMissingPrimary(env, digest) {
  bindings(env);
  guard(digest === SOURCE.sha256, "unreviewed-restore");
  const meta = await env.DB.prepare(
    "SELECT object_sha256 FROM asset_vintages WHERE object_sha256 = ?"
  ).bind(digest).first();
  guard(meta && meta.object_sha256 === digest, "restore-must-be-indexed");
  const key = objectKey(digest);
  const backup = await verifyObject(env.ARCHIVE_BACKUP, key, digest);
  const existing = await env.ARCHIVE.head(key);
  guard(!existing, "restore-will-not-overwrite-existing-object");
  await ensureObject(env.ARCHIVE, key, backup, digest);
  return { restored: true, sha256: digest };
}
export async function processInbox(env) {
  if (env?.IMPORT_ENABLED !== "true") return { status: "disabled" };
  bindings(env);
  const staged = await env.ARCHIVE.get(INBOX);
  if (!staged) return { status: "no-approved-staging-object" };
  const result = await ingestEnvelope(env, await readBounded(staged));
  // Keep inbox object if validation or index/backup commit fails.
  await verifyIndex(env);
  await env.ARCHIVE.delete(INBOX);
  return result;
}
export default {
  async fetch() { return new Response("Not Found", { status: 404, headers: { "Cache-Control": "no-store" } }); },
  async scheduled(_event, env, ctx) {
    // No public HTTP endpoint, credentials, or automatic third-party downloads.
    ctx.waitUntil((async () => {
      const result = await processInbox(env);
      if (env?.IMPORT_ENABLED === "true") {
        const audit = await verifyIndex(env);
        console.log("private-history", { status: result.status, verified: audit.verified });
      }
    })());
  },
};
