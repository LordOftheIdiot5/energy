import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from publication_policy import project_snapshot, project_economic, project_shared, write_projection
DATA=Path(__file__).resolve().parents[1]/"data"
class PublicationPolicy(unittest.TestCase):
    def test_snapshot(self):
        d=json.loads((DATA/"energy.json").read_text())
        approved=project_snapshot(d)
        self.assertTrue(approved["europe"])
        for k in ("market","grid","fuel","france","zones","commodities","news"):self.assertFalse(approved[k],k)
        self.assertIsNone(approved["marketIndex"])
        self.assertTrue(approved["reservoirs"])
        self.assertTrue(approved["weather"])
        self.assertNotIn("unreviewed",project_snapshot({**d,"unreviewed":123}))
        sample=d["europe"][0]
        bad=[{**sample,"licenseInfo":"private use only"},{**sample,"sourceUrl":"https://api.energy-charts.info.example.com/price"},{**sample,"zone":"FI"},{**sample,"marketType":"market_index"}]
        self.assertFalse(project_snapshot({**d,"europe":bad})["europe"])
    def test_economic(self):
        d=json.loads((DATA/"economic-reference-v1.json").read_text())
        self.assertEqual({r["key"] for r in project_economic(d)["series"]},{"eia:RBRTE","eia:RWTC"})
        with self.assertRaises(ValueError):project_economic({**d,"series":[]})
    def test_projection_no_source_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"public"
            prior=(DATA/"energy.json").read_bytes()
            write_projection(DATA,out)
            self.assertEqual(prior,(DATA/"energy.json").read_bytes())
            self.assertFalse(json.loads((out/"energy.json").read_text())["commodities"])
            self.assertTrue(project_shared(json.loads((DATA/"entsoe-open.json").read_text()))["series"])
            with self.assertRaises(ValueError):write_projection(DATA,DATA/"output")
