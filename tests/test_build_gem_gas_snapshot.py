import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_gem_gas_snapshot import coords_valid,project
class GemProjectionTests(unittest.TestCase):
 def test_good_multi_line_geometry(self):
  self.assertTrue(coords_valid([[[10,60],[11,61]],[[-120,20],[-121,21]]]))
 def test_no_invented_endpoints(self):
  for bad in ([],[[[1,2]]],[[[200,40],[10,60]]],[[[None,2],[3,4]]]):
   self.assertFalse(coords_valid(bad))
 def test_source_fingerprint_gate_precedes_mapping(self):
  with self.assertRaisesRegex(ValueError,"Unapproved GEM source"):
   project({}, {}, "bad", "bad")
if __name__=="__main__":unittest.main()
