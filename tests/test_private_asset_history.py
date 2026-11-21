import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from private_asset_history import (
    add, bootstrap_reviewed_gem, differences, ledger, object_path,
    private_root, read_snapshot, restore, verify,
)


def sample_meta(release="2025-11", coverage="complete", rights="review_required"):
    return {
        "dataset": "gem-gas-pipelines", "release": release,
        "source_url": "https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/",
        "retrieved_at": datetime(2026, 11, 21, tzinfo=timezone.utc).isoformat(),
        "license": "CC BY 4.0 — package review pending",
        "attribution": "Global Energy Monitor",
        "rights_state": rights, "coverage": coverage, "id_field": "id",
    }


class PrivateVintageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "archive"
        self.base = [
            {"id": "gem-A", "country_codes": ["NO"], "geometry": None,
             "status": "Operating", "capacity_bcm_y": None},
            {"id": "gem-B", "country_codes": ["SE"], "geometry": [12.2, 58.4],
             "status": "Proposed", "capacity_bcm_y": 14},
        ]

    def test_atomic_content_addressing_idempotence_and_private_restore(self):
        first, created = add(self.root, sample_meta(), self.base)
        self.assertTrue(created)
        again = sample_meta()
        again["retrieved_at"] = "2026-11-22T11:00:00Z"
        saved, created = add(self.root, again, self.base)
        self.assertFalse(created)
        self.assertEqual(first, saved)
        self.assertEqual(verify(self.root), 1)
        self.assertEqual(read_snapshot(self.root, first)["rows"][0]["geometry"], None)
        self.assertEqual(first["located_rows"], 1)
        self.assertEqual(len(ledger(self.root)["vintages"]), 1)
        target = Path(self.tmp.name) / "restored"
        self.assertEqual(restore(self.root, target), target)
        self.assertEqual(verify(target), 1)
        self.assertEqual(read_snapshot(target, first)["rows"], self.base)
        with self.assertRaisesRegex(ValueError, "unused"):
            restore(self.root, target)

    def test_diff_uses_native_identity_not_names_or_fuzzy_routes(self):
        first, _ = add(self.root, sample_meta(), self.base)
        newer = [
            {"id": "gem-A", "country_codes": ["NO"], "geometry": None,
             "status": "Retired", "capacity_bcm_y": None},
            {"id": "gem-C", "country_codes": ["SE"], "geometry": [12.2, 58.4],
             "status": "Proposed", "capacity_bcm_y": 14},
        ]
        second, _ = add(self.root, sample_meta("2026-10"), newer)
        out = differences(self.root, first["object_sha256"], second["object_sha256"])
        self.assertEqual(out["added_ids"], ["gem-C"])
        self.assertEqual(out["missing_ids"], ["gem-B"])
        self.assertEqual(out["explicit_source_status_terminal_ids"], ["gem-A"])
        self.assertEqual(out["changed"], [{"id": "gem-A", "fields": ["status"]}])
        self.assertIn("NOT proof", out["notice"])

    def test_partial_coverage_never_calls_missing_asset_retired(self):
        a, _ = add(self.root, sample_meta(), self.base)
        b, _ = add(self.root, sample_meta("2026-10", coverage="partial"),
                   [self.base[0]])
        diff = differences(self.root, a["object_sha256"], b["object_sha256"])
        self.assertEqual(diff["missing_ids"], [])
        self.assertEqual(diff["unresolved_missing_ids"], ["gem-B"])
        self.assertEqual(diff["explicit_source_status_terminal_ids"], [])

    def test_duplicates_geometry_and_unknown_country_codes_fail_closed(self):
        cases = [
            self.base + [copy.deepcopy(self.base[0])],
            [{**self.base[0], "geometry": [200, 60]}],
            [{**self.base[0], "geometry": [float("nan"), 58]}],
            [{**self.base[0], "country_codes": ["Norway"]}],
            [{**self.base[0], "status": True}],
            [{**self.base[0], "id": ""}],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                add(self.root, sample_meta(), rows)
        self.assertFalse(self.root.exists(), "Malformed input should not open the archive")

    def test_provenance_and_rights_review_gate(self):
        meta = sample_meta()
        meta["rights_state"] = "approved_public"
        with self.assertRaisesRegex(ValueError, "evidence"):
            add(self.root, meta, self.base)
        meta = sample_meta()
        meta["source_url"] = "http://example.com/insecure"
        with self.assertRaisesRegex(ValueError, "URL"):
            add(self.root, meta, self.base)
        meta = sample_meta()
        meta["retrieved_at"] = "2026-11-21T18:30:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            add(self.root, meta, self.base)
        meta = sample_meta()
        meta["rights_state"] = "restricted"
        entry, _ = add(self.root, meta, self.base)
        self.assertEqual(entry["rights_state"], "restricted")
        self.assertEqual(verify(self.root), 1)
        self.assertFalse((ROOT / "data" / ".private-vintages" / "ledger-v1.json").exists(),
                         "No private ledger inside repository")

    def test_no_conflicting_provenance_for_same_object(self):
        add(self.root, sample_meta(), self.base)
        changed = sample_meta()
        changed["rights_state"] = "restricted"
        with self.assertRaisesRegex(ValueError, "conflicting provenance"):
            add(self.root, changed, self.base)
        self.assertEqual(verify(self.root), 1)

    def test_checksum_mutation_and_single_writer(self):
        entry, _ = add(self.root, sample_meta(), self.base)
        object_path(self.root, entry["object_sha256"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify(self.root)
        with self.assertRaisesRegex(ValueError, "checksum"):
            add(self.root, sample_meta("2026-10"), self.base)
        (self.root / ".writer.lock").write_text("stale test\n")
        with self.assertRaisesRegex(RuntimeError, "already has a writer"):
            add(self.root, sample_meta("2026-12"), [])
        self.assertTrue((self.root / ".writer.lock").exists())

    def test_reject_archive_inside_repo(self):
        with self.assertRaisesRegex(ValueError, "outside the public"):
            private_root(ROOT / "data" / ".private-vintages")
        with self.assertRaisesRegex(ValueError, "outside the public"):
            add(ROOT / "data" / ".private-vintages", sample_meta(), self.base)

    def test_real_pinned_gem_2025_can_bootstrap_without_new_download(self):
        # The existing reviewed source is safe for a private history baseline.
        source = ROOT / "data" / "gem-gas-202511"
        if not (source / "gem-gas-pipelines-202511-v1.json").exists():
            self.skipTest("Repository reviewed fixture unavailable")
        entry, created = bootstrap_reviewed_gem(self.root, source)
        self.assertTrue(created)
        self.assertEqual(entry["rows"], 4246)
        self.assertEqual(entry["release"], "2025-11")
        self.assertEqual(entry["rights_state"], "approved_public")
        self.assertEqual(verify(self.root), 1)
        # Every source ID remains exact; no geometry synthesized for the 325 without routes.
        self.assertEqual(len(read_snapshot(self.root, entry)["rows"]), 4246)
        with self.assertRaisesRegex(ValueError, "reviewed"):
            bootstrap_reviewed_gem(self.root, Path(self.tmp.name))


if __name__ == "__main__":
    unittest.main()
