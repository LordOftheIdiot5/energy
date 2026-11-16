import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from entsoe_shared import validate
NOW=datetime(2026,11,16,12,tzinfo=timezone.utc)
def fixture():
    return {"schemaVersion":1,"source":"ENTSO-E Transparency Platform","license":"CC BY 4.0","reuseListDate":"2023-10-18","generated":"2026-11-16T10:00:00Z","series":[{"id":"load-forecast:NO1","kind":"day_ahead_load_forecast","zone":"NO1","article":"6.1.b","unit":"MW","startUtc":"2026-11-15T00:00:00Z","endUtc":"2026-11-16T00:00:00Z","status":"ok","points":[{"startUtc":"2026-11-15T00:00:00Z","mw":42,"resolutionMinutes":15,"curveType":"A03","extra":"not retained"}]}]}
class SharedTests(unittest.TestCase):
    def test_valid_sparse(self):
        r=validate(fixture(),NOW)
        self.assertEqual(r["series"][0]["points"][0]["mw"],42)
        self.assertNotIn("extra",r["series"][0]["points"][0])
    def test_unapproved_and_stale(self):
        d=fixture();d["series"][0]["article"]="6.1.a"
        with self.assertRaises(ValueError):validate(d,NOW)
        d=fixture();d["generated"]="2026-11-01T00:00:00Z"
        with self.assertRaises(ValueError):validate(d,NOW)
    def test_missing_is_not_zero(self):
        d=fixture();d["series"][0]["status"]="unavailable";d["series"][0]["points"]=[]
        with self.assertRaises(ValueError):validate(d,NOW)
