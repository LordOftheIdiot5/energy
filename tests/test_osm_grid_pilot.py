import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_grid_pilot import category,voltage,record
class GridPilotTests(unittest.TestCase):
    def test_category_and_voltage(self):
        self.assertEqual(category({"power":"cable","location":"underwater"}),"underwater_power_cable")
        self.assertEqual(category({"power":"cable"}),"power_cable_unspecified")
        self.assertIsNone(category({"power":"line","line":"busbar"}))
        self.assertIsNone(category({"power":"tower"}))
        self.assertIsNone(category({"power":"construction","construction":"line"}))
        self.assertEqual(voltage("220000;66000;220000"),[220000,66000])
        self.assertEqual(voltage("110 kV"),[])
    def test_record_and_geometry(self):
        r=record("way",1,{"power":"line","voltage":"220000","operator":"Example","access":"private"},[(10.12345,60),(11,61)])
        self.assertEqual(r["geometry"]["coordinates"][0],(10.123,60.0))
        self.assertNotIn("operator",r);self.assertNotIn("access",r)
        self.assertEqual(r["voltage_v"],[220000])
        self.assertIsNone(record("way",1,{"power":"line"},[(1,2),(1,2)]))
        self.assertIsNone(record("node",1,{"power":"substation"},[(181,2)]))
        self.assertIsNone(record("node",1,{"power":"substation"},[(float("nan"),2)]))

class ExtractFallbackTests(unittest.TestCase):
    def test_connection_only_fallback(self):
        import tempfile,subprocess
        from osm_extract_sources import download,SOURCES
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            def runner(args,check):
                calls.append(args[-1])
                if len(calls)==1:return subprocess.CompletedProcess(args,7)
                Path(args[args.index("--output")+1]).write_bytes(b"x"*1024)
                Path(args[args.index("--dump-header")+1]).write_text("Last-Modified: test")
                return subprocess.CompletedProcess(args,0)
            p,m=download("IS",tmp,runner)
            self.assertEqual(calls,[u for _,u in SOURCES["IS"]])
            self.assertEqual(m["extract_provider"],"BBBike")
            self.assertEqual(m["source_bytes"],1024)
    def test_denial_not_retried(self):
        import tempfile,subprocess
        from osm_extract_sources import download
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            def runner(args,check):
                calls.append(args[-1]);return subprocess.CompletedProcess(args,22)
            with self.assertRaises(RuntimeError):download("LU",tmp,runner)
            self.assertEqual(len(calls),1)
