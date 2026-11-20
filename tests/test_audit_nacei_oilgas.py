import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_nacei_oilgas import normalize,inspect,LAYERS,BASE
class NaceiAudits(unittest.TestCase):
 def test_point_projection_keeps_historic_labels(self):
  data={"features":[{"attributes":{"OBJECTID":17,"Country":"Canada","Facility":"Plant Test","Owner":"Owner Old","Period":"2017","Capa_MMcfd":3.5},
                     "geometry":{"x":-115.1,"y":52.2}}]}
  a,b=normalize(4,data)
  self.assertEqual(len(a),1);self.assertEqual(a[0]["reported_capacity"],3.5)
  self.assertEqual(a[0]["status"],"Status not reported in historic source")
  self.assertEqual(a[0]["reference_period"],"2017")
  self.assertEqual(a[0]["geometry"],[-115.1,52.2])
 def test_no_approximate_coords(self):
  a,b=normalize(4,{"features":[{"attributes":{"OBJECTID":1,"Country":"Canada","Facility":"Unknown Plant"},
                                "geometry":{"x":None,"y":None}}]})
  self.assertEqual(len(a),0);self.assertEqual(b["invalid_geography"],1)
 def test_empty_official_facility_name_is_explicit(self):
  row={"attributes":{"OBJECTID":141,"Country":"United States","Facility":None,"Owner":"Owner Name","Period":"20170101"},
       "geometry":{"x":-95.0,"y":29.3}}
  out,counts=normalize(10,{"features":[row]})
  self.assertEqual(len(out),1)
  self.assertEqual(out[0]["facility"],"Facility name not reported (NACEI #141)")
  self.assertEqual(out[0]["facility_name_reported"],False)
  self.assertEqual(counts["facility_name_not_reported"],1)
 def test_unapproved_types_rejected(self):
  with self.assertRaisesRegex(ValueError,"Unknown"):normalize(12,{"features":[]})
 def test_service_provenance_and_missing_permissions_fail(self):
  def fake(url,params):
   if url==BASE:return {"serviceDescription":"NACEI free, licence unknown","copyrightText":"NACEI"}
   raise AssertionError("source should fail at licence gate")
  with self.assertRaisesRegex(ValueError,"use statement"):inspect(fake)
if __name__=="__main__":unittest.main()
