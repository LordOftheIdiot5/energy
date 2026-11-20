import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from nacei_publication import validate,EXPECTED
class NaceiPublication(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=json.loads((ROOT/"data/nacei-oilgas-2017-v1.json").read_text(encoding="utf-8"))
 def test_exact_historic_source(self):
  self.assertTrue(validate(self.doc))
  self.assertEqual(sum(n for _,n in EXPECTED.values()),1461)
 def test_no_conflation_with_current(self):
  d={**self.doc,"source_period":"2026-11"}
  with self.assertRaisesRegex(ValueError,"rights or history"):validate(d)
 def test_no_fake_operational_status(self):
  d=copy.deepcopy(self.doc);d["rows"]["lng_terminals"][0]["operating"]=True
  with self.assertRaisesRegex(ValueError,"status or generation"):validate(d)
 def test_no_missing_source_records(self):
  d=copy.deepcopy(self.doc);d["rows"]["gas_processing"]=d["rows"]["gas_processing"][1:]
  with self.assertRaisesRegex(ValueError,"coverage"):validate(d)
 def test_no_invented_geo(self):
  d=copy.deepcopy(self.doc);d["rows"]["refineries"][0]["geometry"]=[500,600]
  with self.assertRaisesRegex(ValueError,"location"):validate(d)
