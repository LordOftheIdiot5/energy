import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from import_uk_repd import REQUIRED, project, LICENSE

def fixture(**overrides):
    r={field:"Not set" for field in REQUIRED}
    r.update({"Ref ID":"123","Site Name":"North Test","Technology Type":"Wind Onshore",
              "Country":"Scotland","Development Status":"Planning Permission Granted",
              "Development Status (short)":"Awaiting Construction",
              "Installed Capacity (MWelec)":"52.5","X-coordinate":"438000",
              "Y-coordinate":"680000"})
    r.update(overrides)
    output=io.StringIO()
    writer=csv.DictWriter(output, fieldnames=list(REQUIRED)+["Region","County","Record Last Updated (dd/mm/yyyy)"])
    writer.writeheader();writer.writerow(r)
    return output.getvalue().encode("utf-8")

def convert(x,y):
    if x==438000 and y==680000: return (-3.4, 55.9)
    return (100,100)

class UkRepdImporterTests(unittest.TestCase):
    def test_status_source_and_mw_preserved(self):
        d=project(fixture(),convert,1)
        self.assertEqual(d["license"],LICENSE)
        self.assertEqual(d["counts"]["mapped_records"],1)
        self.assertEqual(d["rows"][0]["status"],"Planning Permission Granted")
        self.assertEqual(d["rows"][0]["status_short"],"Awaiting Construction")
        self.assertEqual(d["rows"][0]["reported_mw"],52.5)
        self.assertEqual(d["rows"][0]["geometry"],[-3.4,55.9])
        self.assertNotIn("generation_mw",d["rows"][0])
    def test_unknown_status_is_never_inferred(self):
        d=project(fixture(**{"Development Status":"Not set"}),convert,1)
        self.assertEqual(d["rows"][0]["status"],"Not specified")
    def test_missing_location_has_no_invented_centroid(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):
            project(fixture(**{"X-coordinate":"Not set"}),convert,1)
    def test_unexpected_schema_rejected(self):
        with self.assertRaisesRegex(ValueError,"column schema"):
            project(b"foo,bar\n1,2\n",convert,1)
    def test_unsafe_coordinate_rejected(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):
            project(fixture(**{"X-coordinate":"99999999"}),convert,1)
    def test_invalid_mw_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Invalid reported"):
            project(fixture(**{"Installed Capacity (MWelec)":"999999"}),convert,1)
    def test_no_empty_source_or_large_source(self):
        with self.assertRaises(ValueError):
            project(b"",convert,1)
    def test_identical_duplicate_reference_collapsed(self):
        raw=fixture().decode().splitlines()
        d=project(("\n".join(raw+[raw[-1]])+"\n").encode(),convert,1)
        self.assertEqual(d["counts"]["source_records"],2)
        self.assertEqual(d["counts"]["duplicate_source_rows"],1)
        self.assertEqual(len(d["rows"]),1)
    def test_conflicting_duplicate_reference_rejected(self):
        raw=fixture().decode().splitlines()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            project(("\n".join(raw+[raw[-1].replace("North Test","Other Project")])+"\n").encode(),convert,1)

if __name__=="__main__":
    unittest.main()
