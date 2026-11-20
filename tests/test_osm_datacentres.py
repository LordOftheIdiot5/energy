import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_datacentres import record,classified
class TestOSMPilot(unittest.TestCase):
    def test_only_explicit_named_tags(self):
        self.assertFalse(classified({"name":"Data centre"}))
        self.assertIsNone(record("node",1,{"telecom":"data_center"},1,2))
        self.assertIsNone(record("node",1,{"telecom":"data_center","name":"Example"},float("nan"),2))
        r=record("way",5,{"telecom":"data_center","name":"Example","contact:phone":"private","operator":"Example operator"},1,2)
        self.assertEqual(r["id"],"osm:way:5");self.assertEqual(r["geometry"],[1,2]);self.assertNotIn("contact:phone",r);self.assertNotIn("operator",r)
