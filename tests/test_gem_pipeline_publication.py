import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from gem_pipeline_publication import check,validate_files,git_blob_hash,COUNTS
class GemPublicSafety(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  folder=ROOT/"data/gem-gas-202511"
  cls.tab=json.loads((folder/"gem-gas-pipelines-202511-v1.json").read_text(encoding="utf-8"))
  cls.geo=json.loads((folder/"gem-gas-pipeline-routes-202511-v1.geojson").read_text(encoding="utf-8"))
 def test_exact_reviewed_source(self):
  self.assertEqual(validate_files(ROOT/"data/gem-gas-202511")["routes"],3921)
  self.assertEqual(check(self.tab,self.geo)["unmapped"],325)
 def test_licensed_statuses_are_separate(self):
  self.assertEqual(self.tab["statuses"],COUNTS)
  self.assertEqual(self.tab["statuses"]["Status not reported"],1)
 def test_bad_rights_fails(self):
  bad={**self.tab,"license":"unknown"}
  with self.assertRaisesRegex(ValueError,"source release"):check(bad,self.geo)
 def test_fake_operational_assertion_fails(self):
  d={**self.tab,"rows":self.tab["rows"].copy()}
  d["rows"][0]={**d["rows"][0],"operating_now":True}
  with self.assertRaisesRegex(ValueError,"Unsafe current-operation"):check(d,self.geo)
 def test_no_invented_routes(self):
  d={**self.geo,"features":self.geo["features"][:-1]}
  with self.assertRaisesRegex(ValueError,"count mismatch"):check(self.tab,d)
 def test_sha_must_be_reviewed(self):
  self.assertNotEqual(git_blob_hash(b'{}'),'b2b3552e08129021fc2c2fb6114e7a12ae2e3259')
