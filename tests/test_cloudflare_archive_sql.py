"""Execute the actual Cloudflare D1 migration against SQLite and test constraints."""
import json
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "deploy/cloudflare-history/migrations/0001_source_vintages.sql"
SHA = "a6f040f7a1d43afa8020bf22168f0393edd8fceb8337b981c04445a6e6704cb3"


class SourceArchiveSchemaTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript(SQL.read_text(encoding="utf-8"))

    def test_lock_is_strict_and_single_writer(self):
        self.db.execute("INSERT INTO writer_lock VALUES (1, ?, ?)",
                        ("writer-" + "z" * 32, "2026-11-21T19:00:00Z"))
        self.db.execute("INSERT OR IGNORE INTO writer_lock VALUES (1, ?, ?)",
                        ("other-" + "y" * 32, "2026-11-21T19:01:00Z"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM writer_lock").fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO writer_lock VALUES (2, ?, ?)",
                            ("writer-" + "b" * 32, "2026-11-21T19:02:00Z"))

    def insert(self, sha=SHA, rights="approved_public", rows=4246, metadata=None):
        meta = json.dumps(metadata or {"source": "GEM", "release": "2025-11"})
        return self.db.execute(
            """INSERT INTO asset_vintages
               (dataset, release, object_sha256, object_key, rows, source_url,
                retrieved_at, rights_state, license_url, metadata_json, admitted_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            ("gem-gas-pipelines", "2025-11", sha, f"objects/{sha}.json",
             rows, "https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/",
             "2026-11-21T19:00:00+00:00", rights,
             "https://creativecommons.org/licenses/by/4.0/",
             meta, "2026-11-21T19:01:00Z")
        )

    def test_index_uniqueness_and_strict_provenance_fields(self):
        self.insert()
        self.assertEqual(self.db.execute("SELECT rows FROM asset_vintages").fetchone()[0], 4246)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert()
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("q" * 64, "not_a_rights_state")

    def test_invalid_object_checksum_and_json_fail(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("abc")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(rows=0)
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute(
                """INSERT INTO asset_vintages VALUES
                   ('gem-gas-pipelines','2025-11',?, 'objects/x.json',4246,'https://example.com',
                    '2026-11-21T19:00:00Z','approved_public','https://example.com',?,
                    '2026-11-21T19:00:00Z')""",
                ("0" * 64, "{broken json")
            )

    def test_migration_is_idempotent(self):
        self.db.executescript(SQL.read_text(encoding="utf-8"))
        self.insert()
        self.db.executescript(SQL.read_text(encoding="utf-8"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM asset_vintages").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
