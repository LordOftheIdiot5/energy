import io,sys,zipfile,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_eia860m import sheet_titles,peek,shared_strings,S,R,audit
def workbook(path):
    xml='''<?xml version="1.0"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
     xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
     <sheets><sheet name="Operating" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    rel='''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
     <Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="a"/></Relationships>'''
    sheet='''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData><row r="2"><c r="A2" t="inlineStr"><is><t>Plant ID</t></is></c>
    <c r="B2" t="inlineStr"><is><t>Generator ID</t></is></c></row>
    <row r="3"><c r="A3"><v>123</v></c><c r="B3" t="inlineStr"><is><t>A1</t></is></c></row></sheetData></worksheet>'''
    with zipfile.ZipFile(path,'w') as z:
        z.writestr("xl/workbook.xml",xml)
        z.writestr("xl/_rels/workbook.xml.rels",rel)
        z.writestr("xl/worksheets/sheet1.xml",sheet)
    return path
class EIAInventoryTests(unittest.TestCase):
    def test_headers_and_identity(self):
        with tempfile.TemporaryDirectory() as t:
            p=workbook(Path(t)/"test.xlsx")
            with zipfile.ZipFile(p) as z:
                self.assertEqual(sheet_titles(z),[("Operating","xl/worksheets/sheet1.xml")])
                rows=peek(z,"xl/worksheets/sheet1.xml",shared_strings(z))
                self.assertEqual(rows[0]["cells"][0]["value"],"Plant ID")
                self.assertEqual(rows[1]["cells"][1]["value"],"A1")
    def test_unsafe_small_workbook_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=workbook(Path(t)/"test.xlsx")
            with self.assertRaisesRegex(ValueError,"safe range"):
                audit(p)
if __name__=="__main__":unittest.main()
