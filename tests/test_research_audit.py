import sys, unittest, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from project_changes import compare
from research_audit import inventory

class ResearchTests(unittest.TestCase):
    def test_snapshot_changes(self):
        a={"source":"test","complete":True,"observed_at":"2025-01-01T00:00:00+00:00","rows":[{"id":"a","status":"planned"},{"id":"b"}]}
        b={**a,"observed_at":"2025-02-01T00:00:00+00:00","rows":[{"id":"a","status":"operational"},{"id":"c"}]}
        self.assertEqual([e["event"] for e in compare(a,b,["status"])["events"]],["reported_fields_changed","not_in_new_snapshot","first_seen"])
        with self.assertRaises(ValueError):compare(a,{**b,"complete":False},["status"])
        with self.assertRaises(ValueError):compare(a,{**b,"rows":[{"id":"a"},{"id":"a"}]},["status"])
    def test_inventory_never_grants_rights(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"catalog-v1.json").write_text(json.dumps({"datasets":[{"id":"a","path":"a.json","status":"open_with_attribution"},{"id":"b","path":"b.json","status":"pending"}]}))
            (p/"a.json").write_text('{"rows":[{}]}')
            a,b=inventory(p)["datasets"]
            self.assertTrue(a["available"])
            self.assertFalse(a["commercial_redistribution_cleared"])
            self.assertEqual(a["row_count"],1)
            self.assertFalse(b["available"])
