import io,sys,json,tempfile,zipfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from import_eia860m import normalize,valid_coordinate
from audit_eia860m import SOURCE
HEADERS=["Plant ID","Plant Name","Generator ID","Plant State","Technology","Energy Source Code","Nameplate Capacity (MW)","Latitude","Longitude","Status","Planned Operation Month","Planned Operation Year"]
def xcol(n):
 s=""
 while n: n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
def fixture():
 names=["Operating","Planned","Retired","Canceled or Postponed","Operating_PR","Planned_PR","Retired_PR"]
 main='''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'''+''.join(f'<sheet name="{name}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i,name in enumerate(names))+'</sheets></workbook>'
 rel='''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'''+''.join(f'<Relationship Id="rId{i+1}" Target="worksheets/sheet{i+1}.xml" Type="a"/>' for i in range(len(names)))+'</Relationships>'
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,"w") as z:
  z.writestr("xl/workbook.xml",main);z.writestr("xl/_rels/workbook.xml.rels",rel)
  for i,name in enumerate(names):
   hdr=''.join(f'<c r="{xcol(j+1)}3" t="inlineStr"><is><t>{h}</t></is></c>' for j,h in enumerate(HEADERS))
   sample=["123","Test Plant","G1","PR" if name.endswith("_PR") else "WA","Hydroelectric Conventional","WAT","1.2","18.4" if name.endswith("_PR") else "47.3","-66.3" if name.endswith("_PR") else "-122.3","(OP) Operating" if name.startswith("Operating") else "(V) Under construction", "11","2027"]
   vals=''.join(f'<c r="{xcol(j+1)}4" t="inlineStr"><is><t>{v}</t></is></c>' for j,v in enumerate(sample))
   xml=f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="3">{hdr}</row><row r="4">{vals}</row></sheetData></worksheet>'
   z.writestr(f"xl/worksheets/sheet{i+1}.xml",xml)
 return buf.getvalue()
class NormalizationTests(unittest.TestCase):
 def test_expected_tabs_and_inventory_separation(self):
  r=normalize(fixture(),min_records=0,expected_sha=None)
  self.assertEqual(len(r["rows"]),7)
  self.assertEqual(len({x["id"] for x in r["rows"]}),7)
  self.assertEqual({x["inventory"] for x in r["rows"]},{"operating","planned","retired","canceled_postponed"})
  self.assertTrue(all(x["nameplate_mw"]==1.2 for x in r["rows"]))
  self.assertEqual(r["rows"][0]["status"],"Canceled / indefinitely postponed (EIA inventory)")
 def test_source_immutable(self):
  with self.assertRaisesRegex(ValueError,"checksum"):normalize(fixture(),min_records=0)
 def test_coordinate_missing_or_impossible(self):
  for lat,lon in [(None,-100),(0,-100),(50,0),(100,-100),(50,100)]:
   self.assertFalse(valid_coordinate(lat,lon,False))
  self.assertTrue(valid_coordinate(18.44,-66.5,True))
  self.assertTrue(valid_coordinate(47.1,-122.5,False))
  self.assertFalse(valid_coordinate(47.1,-122.5,True))
 def test_no_inferred_generation(self):
  r=normalize(fixture(),min_records=0,expected_sha=None)["rows"]
  self.assertTrue(all("generation_mw" not in x and "capacity_factor" not in x for x in r))
if __name__=="__main__":unittest.main()
