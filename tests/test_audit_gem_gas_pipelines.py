import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_gem_gas_pipelines import audit,EXPECTED,ATTR,CC
def fixture():
 rows=[{"slug":f"pipeline-{i}","name":f"Pipeline {i}","status":"operating" if i%2 else "proposed","data_source":ATTR,"length_km":110.0} for i in range(EXPECTED)]
 geo={"type":"FeatureCollection","features":[{"type":"Feature","properties":{"slug":r["slug"]},"geometry":{"type":"LineString","coordinates":[[10,60],[11,61]]}} for r in rows]}
 return {"dataset":"Gas pipelines","release":"November 2025","attribution":ATTR,"licence":"CC BY 4.0","licence_url":CC,"count":EXPECTED,"rows":rows},geo
class GasPipelineAuditTests(unittest.TestCase):
 def test_release_rights_and_geo(self):
  t,g=fixture();result=audit(t,g)
  self.assertEqual(result["table_rows"],EXPECTED)
  self.assertEqual(result["matched_routes"],EXPECTED)
 def test_wrong_release(self):
  t,g=fixture();t["release"]="October 2026"
  with self.assertRaisesRegex(ValueError,"release/rights"):audit(t,g)
 def test_missing_row_credit_rejected(self):
  t,g=fixture();t["rows"][0]["data_source"]=None
  with self.assertRaisesRegex(ValueError,"attribution"):audit(t,g)
 def test_geo_can_be_partial_but_not_unsafe(self):
  t,g=fixture();g["features"]=g["features"][:100]
  with self.assertRaisesRegex(ValueError,"Unsafe loss"):audit(t,g)
 def test_no_unsupported_geometry(self):
  t,g=fixture();g["features"][0]["geometry"]["type"]="Point"
  with self.assertRaisesRegex(ValueError,"line geometry"):audit(t,g)
if __name__=="__main__":unittest.main()
