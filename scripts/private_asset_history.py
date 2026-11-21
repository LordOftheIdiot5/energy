"""Private, content-addressed source-vintage ledger for historical asset research.

This is NOT a public dataset catalogue or an R2/D1 deployment. No network access.
The caller must supply an archive directory OUTSIDE the GitHub checkout.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile

REPO = Path(__file__).resolve().parents[1]
SCHEMA = 1
DATASET = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
RELEASE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
RIGHTS = {"approved_public", "review_required", "restricted"}
COVERAGE = {"complete", "partial"}
TERMINAL = {"retired", "cancelled", "canceled", "shelved", "mothballed"}
REQUIRED = {"dataset", "release", "source_url", "retrieved_at",
            "license", "attribution", "rights_state", "coverage", "id_field"}


def packed(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def private_root(root):
    original = Path(root).expanduser()
    if original.is_symlink():
        raise ValueError("Archive root cannot be a symlink")
    path = original.resolve()
    if path == REPO or path.is_relative_to(REPO):
        raise ValueError("Private archive must be outside the public repository")
    return path


def utc(value):
    if not isinstance(value, str):
        raise ValueError("Missing source/retrieval timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp needs an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def check_metadata(meta):
    if not isinstance(meta, dict) or not REQUIRED.issubset(meta):
        raise ValueError("Missing required source provenance")
    if not isinstance(meta["dataset"], str) or not DATASET.fullmatch(meta["dataset"]):
        raise ValueError("Invalid source namespace")
    if not isinstance(meta["release"], str) or not RELEASE.fullmatch(meta["release"]):
        raise ValueError("Release must be YYYY-MM")
    if not isinstance(meta["source_url"], str) or not meta["source_url"].startswith("https://"):
        raise ValueError("Source URL required")
    if not isinstance(meta["license"], str) or not meta["license"].strip():
        raise ValueError("Source-specific licence must be recorded")
    if not isinstance(meta["attribution"], str) or not meta["attribution"].strip():
        raise ValueError("Attribution required")
    if meta["rights_state"] not in RIGHTS or meta["coverage"] not in COVERAGE:
        raise ValueError("Unknown rights state or coverage")
    if not isinstance(meta["id_field"], str) or not DATASET.fullmatch(meta["id_field"]):
        # "id" is permitted, even though the dataset namespace is >= 3 chars.
        if meta["id_field"] != "id":
            raise ValueError("Invalid native identifier field")
    # This records an existing rights review; it never approves a new licence.
    if meta["rights_state"] == "approved_public" and not meta.get("rights_evidence"):
        raise ValueError("Public rights state needs a reviewed evidence reference")
    utc(meta["retrieved_at"])
    return meta


def row_index(rows, key):
    if not isinstance(rows, list):
        raise ValueError("Snapshot must contain full row list")
    out = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Non-object source record")
        ident = item.get(key)
        if not isinstance(ident, str) or not ident.strip() or len(ident) > 400:
            raise ValueError("Missing or invalid native source ID")
        if ident in out:
            raise ValueError("Duplicate native source ID: " + ident)
        # Exact explicit ISO country codes only. Missing means unknown.
        codes = item.get("country_codes")
        if codes is not None:
            if not isinstance(codes, list) or any(not isinstance(v, str) or
                    not re.fullmatch(r"[A-Z]{2}", v) for v in codes) or len(set(codes)) != len(codes):
                raise ValueError("Country codes must be distinct ISO-2 strings")
        xy = item.get("geometry")
        if xy is not None:
            if (not isinstance(xy, list) or len(xy) != 2 or
                    any(type(n) not in (int, float) or not math.isfinite(n) for n in xy) or
                    not (-180 <= xy[0] <= 180 and -90 <= xy[1] <= 90)):
                raise ValueError("Geometry must be a source-confirmed lon/lat pair or null")
        # All original status strings are preserved without translating to current operation.
        if "status" in item and item["status"] is not None and not isinstance(item["status"], str):
            raise ValueError("Invalid reported status")
        out[ident] = item
    packed(rows)  # fail on NaN, Inf or non-JSON values before writing
    return out


@contextmanager
def single_writer(root):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = root / ".writer.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Archive already has a writer; inspect lock before manual removal") from exc
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(str(os.getpid()) + "\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def atomic_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False) as f:
        name = Path(f.name)
        os.chmod(name, 0o600)
        try:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    try:
        os.replace(name, path)
    finally:
        name.unlink(missing_ok=True)


def ledger(root):
    path = root / "ledger-v1.json"
    if not path.exists():
        return {"schema_version": SCHEMA, "vintages": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA or not isinstance(data.get("vintages"), list):
        raise ValueError("Invalid vintage manifest")
    return data


def object_path(root, digest):
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ValueError("Invalid content-addressed object hash")
    return root / "objects" / (digest + ".json")


def add(root, meta, rows):
    root = private_root(root)
    check_metadata(meta)
    index = row_index(rows, meta["id_field"])
    snapshot = {"schema_version": SCHEMA, "dataset": meta["dataset"],
                "release": meta["release"], "id_field": meta["id_field"], "rows": rows}
    raw = packed(snapshot)
    digest = sha(raw)
    entry = {**meta, "retrieved_at": utc(meta["retrieved_at"]),
             "object_sha256": digest, "rows": len(index),
             "located_rows": sum(x.get("geometry") is not None for x in rows)}
    with single_writer(root):
        current = ledger(root)
        # Fail closed on a broken object before accepting another revision.
        if current["vintages"]:
            verify(root)
        for prior in current["vintages"]:
            if prior["dataset"] == entry["dataset"] and prior["release"] == entry["release"] \
                    and prior["object_sha256"] == digest:
                comparable = lambda d: {k: v for k, v in d.items() if k != "retrieved_at"}
                if comparable(prior) != comparable(entry):
                    raise ValueError("Same source content with conflicting provenance")
                return prior, False
        path = object_path(root, digest)
        if path.exists():
            if sha(path.read_bytes()) != digest:
                raise ValueError("Existing immutable object was modified")
        else:
            atomic_bytes(path, raw)
        current["vintages"].append(entry)
        atomic_bytes(root / "ledger-v1.json", packed(current))
    return entry, True


def read_snapshot(root, entry):
    root = private_root(root)
    path = object_path(root, entry["object_sha256"])
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing/unsafe immutable object")
    raw = path.read_bytes()
    if sha(raw) != entry["object_sha256"]:
        raise ValueError("Source-object checksum mismatch")
    doc = json.loads(raw)
    if (doc.get("schema_version") != SCHEMA or doc.get("dataset") != entry["dataset"] or
            doc.get("release") != entry["release"] or doc.get("id_field") != entry["id_field"]):
        raise ValueError("Snapshot does not match manifest")
    if len(row_index(doc["rows"], entry["id_field"])) != entry["rows"]:
        raise ValueError("Record count mismatch")
    return doc


def verify(root):
    root = private_root(root)
    manifest = ledger(root)
    seen = set()
    for entry in manifest["vintages"]:
        check_metadata(entry)
        key = (entry["dataset"], entry["release"], entry["object_sha256"])
        if key in seen:
            raise ValueError("Duplicate ledger pointer")
        seen.add(key)
        doc = read_snapshot(root, entry)
        if sum(row.get("geometry") is not None for row in doc["rows"]) != entry["located_rows"]:
            raise ValueError("Reported location count mismatch")
    return len(seen)


def differences(root, old_sha, new_sha):
    entries = ledger(private_root(root))["vintages"]
    versions = {x["object_sha256"]: x for x in entries}
    if old_sha not in versions or new_sha not in versions:
        raise ValueError("Both versions must exist in private ledger")
    a, b = versions[old_sha], versions[new_sha]
    if a["dataset"] != b["dataset"] or a["id_field"] != b["id_field"]:
        raise ValueError("Cannot compare unrelated source identifiers")
    key = a["id_field"]
    old = row_index(read_snapshot(root, a)["rows"], key)
    new = row_index(read_snapshot(root, b)["rows"], key)
    added = sorted(set(new) - set(old))
    missing = sorted(set(old) - set(new))
    changed = [{"id": ident, "fields": sorted(
                   field for field in old[ident].keys() | new[ident].keys()
                   if field not in old[ident] or field not in new[ident]
                   or old[ident][field] != new[ident][field])}
               for ident in sorted(set(old) & set(new))
               if old[ident] != new[ident]]
    explicit_terminal = [ident for ident in sorted(set(old) & set(new))
                         if str(old[ident].get("status") or "").casefold() not in TERMINAL
                         and str(new[ident].get("status") or "").casefold() in TERMINAL]
    return {"dataset": a["dataset"], "from_release": a["release"],
            "to_release": b["release"], "added_ids": added,
            "changed": changed,
            "missing_ids": missing if b["coverage"] == "complete" else [],
            "unresolved_missing_ids": missing if b["coverage"] == "partial" else [],
            "explicit_source_status_terminal_ids": explicit_terminal,
            "notice": "Missing in a source release is NOT proof of physical retirement; "
                      "source-reported status changes are not verified real-time operations."}


def restore(source, target):
    source, target = private_root(source), private_root(target)
    if target.exists() or target == source or target.is_relative_to(source):
        raise ValueError("Restore requires an unused, independent private destination")
    verify(source)
    target.mkdir(mode=0o700, parents=True)
    for entry in ledger(source)["vintages"]:
        digest = entry["object_sha256"]
        destination = object_path(target, digest)
        if not destination.exists():
            atomic_bytes(destination, object_path(source, digest).read_bytes())
    atomic_bytes(target / "ledger-v1.json", (source / "ledger-v1.json").read_bytes())
    if verify(target) != verify(source):
        raise ValueError("Restore verification failed")
    return target


def bootstrap_reviewed_gem(root, source_folder):
    """Only the already-reviewed 2025 project table, never an unreviewed newer feed."""
    from gem_pipeline_publication import validate_files
    folder = Path(source_folder).resolve()
    if folder != (REPO / "data" / "gem-gas-202511").resolve():
        raise ValueError("Bootstrap accepts only the repository's reviewed GEM path")
    validate_files(folder)  # checks the pinned Git blobs, licence and route accounting
    file = folder / "gem-gas-pipelines-202511-v1.json"
    doc = json.loads(file.read_text(encoding="utf-8"))
    if doc.get("release") != "2025-11" or len(doc.get("rows", [])) != 4246:
        raise ValueError("GEM baseline changed unexpectedly")
    meta = {"dataset": "gem-gas-pipelines", "release": "2025-11",
            "source_url": "https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "attribution": doc["attribution"], "license": doc["license_url"],
            "rights_state": "approved_public", "coverage": "complete", "id_field": "id",
            "rights_evidence": "Reviewed Nordl Energy PR #93, GEM CC BY 4.0 November 2025 package"}
    return add(root, meta, doc["rows"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("bootstrap-gem", "verify", "restore", "diff"):
        sub = commands.add_parser(name)
        sub.add_argument("--archive", type=Path, required=True)
        if name == "bootstrap-gem":
            sub.add_argument("--source-folder", type=Path, default=REPO / "data" / "gem-gas-202511")
        if name == "restore":
            sub.add_argument("--target", type=Path, required=True)
        if name == "diff":
            sub.add_argument("--from-sha", required=True)
            sub.add_argument("--to-sha", required=True)
    args = parser.parse_args()
    if args.command == "bootstrap-gem":
        entry, created = bootstrap_reviewed_gem(args.archive, args.source_folder)
        print(json.dumps({"created": created, "release": entry["release"],
                          "rows": entry["rows"], "sha256": entry["object_sha256"]}))
    elif args.command == "verify":
        print(json.dumps({"verified_vintages": verify(args.archive)}))
    elif args.command == "restore":
        print(json.dumps({"restored_to": str(restore(args.archive, args.target))}))
    else:
        print(json.dumps(differences(args.archive, args.from_sha, args.to_sha), indent=2))


if __name__ == "__main__":
    main()
