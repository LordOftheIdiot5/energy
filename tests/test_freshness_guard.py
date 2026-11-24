import sys,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from freshness_guard import decide
class FreshnessGuardTests(unittest.TestCase):
    def test_schedule(self):
        now=datetime(2026,11,20,7,24,tzinfo=timezone.utc)
        def doc(m):return {"generated":(now-timedelta(minutes=m)).isoformat()}
        self.assertEqual(decide(doc(20),doc(20),now),"skip")
        self.assertEqual(decide(doc(20),doc(40),now),"deploy")
        self.assertEqual(decide(doc(20),{},now),"deploy")
        self.assertEqual(decide(doc(70),doc(70),now),"collect")
        self.assertEqual(decide(doc(240),doc(240),now),"collect")
        self.assertEqual(decide(doc(-1),doc(20),now),"collect")
        self.assertEqual(decide({},doc(20),now),"collect")
        self.assertEqual(decide(doc(20),doc(-1),now),"deploy")
