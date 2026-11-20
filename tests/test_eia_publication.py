import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from eia_publication import check,stage,TOTAL,SPLITS
class EiaPublicTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=json.loads((ROOT/"data/eia860m-generators-v1.json").read_text(encoding="utf-8"))
 def test_real_source_provenance_and_categories(self):
  self.assertTrue(check(self.doc))
  self.assertEqual(len(self.doc["rows"]),TOTAL)
  self.assertEqual(sum(SPLITS.values()),TOTAL)
 def test_no_false_licence(self):
  with self.assertRaisesRegex(ValueError,"Unapproved"):
   check({**self.doc,"rights":"third-party-unapproved"})
 def test_reject_inferred_output(self):
  d={**self.doc,"rows":self.doc["rows"].copy()}
  d["rows"][0]={**d["rows"][0],"generation_mw":123}
  with self.assertRaisesRegex(ValueError,"Inferred"):
   check(d)
 def test_split_public_files_and_manifest(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=stage(ROOT/"data",Path(tmp))
   self.assertEqual(sum(e["records"] for e in m["inventories"]),TOTAL)
   self.assertEqual({e["id"] for e in m["inventories"]},set(SPLITS))
   self.assertTrue((Path(tmp)/"planned-v1.json").is_file())
   self.assertFalse((Path(tmp)/"eia860m-generators-v1.json").exists())
   self.assertEqual(len(json.loads((Path(tmp)/"planned-v1.json").read_text())["rows"]),SPLITS["planned"])
