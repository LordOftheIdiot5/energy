import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from project_register import project_register
class ProjectRegisterTests(unittest.TestCase):
    def test_actual_registry(self):
        d=json.loads((ROOT/"data/nve-projects-v1.json").read_text(encoding="utf-8"))
        p=project_register(d)
        self.assertGreater(len(p["rows"]),1000)
        self.assertEqual(len({r["id"] for r in p["rows"]}),len(p["rows"]))
        for r in p["rows"]:
            self.assertEqual(r["status"],"Licensing record")
            self.assertNotIn("generation_mw",r)
            self.assertNotIn("transfer_mw",r)
            self.assertEqual(r["developer"],"Not included")
    def test_bad_provenance(self):
        with self.assertRaises(ValueError): project_register({"schema_version":1,"source":"unapproved","rows":[]})
    def test_invalid_and_empty(self):
        d=json.loads((ROOT/"data/nve-projects-v1.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError): project_register({**d,"rows":[{"id":1,"vannkraftStasjonNavn":"bad","geometry":[999,0]}]})
