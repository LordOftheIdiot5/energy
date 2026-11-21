"""Prepare a *private*, reviewed GEM 2025 inbox envelope for Cloudflare R2.

Never writes in the GitHub checkout or posts data to the Internet. The caller
must privately upload the resulting file to R2 only after provisioning review.
"""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from private_asset_history import (
    REPO, object_path, ledger, read_snapshot, private_root, sha, check_metadata
)

DATASET = "gem-gas-pipelines"
RELEASE = "2025-11"
PINNED_SHA = "a6f040f7a1d43afa8020bf22168f0393edd8fceb8337b981c04445a6e6704cb3"
PINNED_UPSTREAM = "33cf8df6a6ba9bfaad0fd6c046b8b0be6d746bba014c7e31cd6b4618ed1605f1"
PINNED_GEOMETRY = "d2d940433656e58ba32a852aba6f30300846ab52375b0139f02df88d691f4378"


def prepare(archive, output):
    root = private_root(archive)
    out = Path(output).expanduser()
    if out.is_symlink() or out.exists():
        raise ValueError("Output file must not already exist or be a symlink")
    parent = out.parent.resolve()
    if parent == REPO or parent.is_relative_to(REPO):
        raise ValueError("Source envelope must remain outside GitHub repository")
    versions = [v for v in ledger(root)["vintages"]
                if v.get("dataset") == DATASET and v.get("release") == RELEASE
                and v.get("object_sha256") == PINNED_SHA]
    if len(versions) != 1:
        raise ValueError("Expected exactly one pinned reviewed GEM 2025 vintage")
    entry = versions[0]
    check_metadata(entry)
    if (entry["rows"] != 4246 or entry["rights_state"] != "approved_public"
            or entry.get("upstream_sha256") != PINNED_UPSTREAM
            or entry.get("geometry_upstream_sha256") != PINNED_GEOMETRY
            or "PR #93" not in entry.get("rights_evidence", "")):
        raise ValueError("Source rights, rows or original source fingerprints have changed")
    snapshot = read_snapshot(root, entry)
    if len(snapshot["rows"]) != 4246:
        raise ValueError("Unexpected native source count")
    raw = object_path(root, PINNED_SHA).read_bytes()
    if sha(raw) != PINNED_SHA:
        raise ValueError("Immutable original source checksum mismatch")
    text = raw.decode("utf-8")
    envelope = json.dumps({"schema_version": 1, "metadata": entry,
                           "snapshot_text": text}, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(envelope) > 9_000_000:
        raise ValueError("Private Cloudflare envelope exceeds size limit")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(envelope)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    return {"source_rows": 4246, "snapshot_sha256": PINNED_SHA,
            "envelope_sha256": sha(envelope), "bytes": len(envelope),
            "output_path": str(out)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    info = prepare(a.archive, a.out)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
