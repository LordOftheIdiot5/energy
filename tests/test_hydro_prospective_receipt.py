import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from hydro_prospective_receipt import build, freeze, SOURCE, ZONES

NOW = datetime(2026, 11, 26, 20, tzinfo=timezone.utc)

def fixture():
    rows = []
    date = datetime(2000, 1, 3)
    end = datetime(2026, 11, 16)
    while date <= end:
        year, week, _ = date.isocalendar()
        for i, zone in enumerate(ZONES):
            rows.append({"year": year, "week": week, "zone": zone,
                         "fill_pct": 40 + i + (week % 26),
                         "snapshot_generated": "2026-11-25T12:00:00Z"})
        date += timedelta(days=7)
    return {"schema_version": 1, "source": SOURCE, "rows": rows}

def raw(d):
    return json.dumps(d).encode()

class ProspectiveTests(unittest.TestCase):
    def test_receipt_exact_week_and_append_only(self):
        receipt = build(raw(fixture()), NOW)
        self.assertEqual(receipt["target_iso_week"], 48)
        self.assertEqual(receipt["target_week_end_exclusive_utc"], "2026-11-29T23:00:00+00:00")
        self.assertEqual(receipt["lead_hours_to_week_end"], 75)
        self.assertEqual(len(receipt["zones"]), 5)
        self.assertEqual(len(receipt["source_sha256"]), 64)
        self.assertFalse(receipt["operational_forecast_approved"])
        with tempfile.TemporaryDirectory() as d:
            path = freeze(d, receipt)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                freeze(d, {**receipt, "issued_at": "changed"})
            self.assertEqual(before, path.read_bytes())
    def test_reject_finished_target_week(self):
        with self.assertRaisesRegex(ValueError, "target week"):
            build(raw(fixture()), datetime(2026, 11, 29, 23, tzinfo=timezone.utc))
    def test_reject_future_vintage_and_duplicate(self):
        d = fixture()
        d["rows"][-1]["snapshot_generated"] = "2026-11-27T12:00:00Z"
        with self.assertRaisesRegex(ValueError, "future source"):
            build(raw(d), NOW)
        d = fixture()
        d["rows"].append(d["rows"][-1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build(raw(d), NOW)
    def test_reject_incomplete_zone_and_already_observed_target(self):
        d = fixture()
        d["rows"].pop()
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            build(raw(d), NOW)
        d = fixture()
        d["rows"].append({**d["rows"][-1], "week": 48})
        with self.assertRaisesRegex(ValueError, "unfinished"):
            build(raw(d), NOW)
    def test_reject_missing_retrieval_and_repository_output(self):
        d = fixture()
        del d["rows"][-1]["snapshot_generated"]
        with self.assertRaisesRegex(ValueError, "missing retrieval"):
            build(raw(d), NOW)
        with self.assertRaisesRegex(ValueError, "outside repository"):
            freeze(Path(__file__).resolve().parents[1], {})

if __name__ == "__main__":
    unittest.main()
