import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from ssb_energy import normalize
class SSBTests(unittest.TestCase):
    def test_jsonstat_exact_cells(self):
        d={"class":"dataset","version":"2.0","id":["ContentsCode","Tid"],"size":[1,2],"dimension":{"ContentsCode":{"category":{"index":{"Prod":0},"label":{"Prod":"Production"},"unit":{"Prod":{"label":"MWh"}}}},"Tid":{"category":{"index":{"2026M01":0,"2026M02":1}}}},"value":[0,None],"status":{"1":":"}}
        rows=normalize(d,"14091")
        self.assertEqual(rows[0]["value"],0)
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[1]["status"],":")
        with self.assertRaises(ValueError):normalize(d,"08307")
        del d["dimension"]["ContentsCode"]["category"]["unit"]
        self.assertEqual(normalize(d,"14091")[0]["unit"],"MWh")
