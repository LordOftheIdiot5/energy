import sys,unittest,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_grid_expansion import EXPANSION
from osm_extract_sources import SOURCES,download
class ExpansionTests(unittest.TestCase):
    def test_separate_cohorts(self):
        self.assertEqual(set(SOURCES),{"IS","LU"})
        self.assertEqual(set(EXPANSION),{"EE","LV","FO","AL"})
        with tempfile.TemporaryDirectory() as t:
            def fake(args,check):
                self.assertEqual(args[-1],EXPANSION["EE"][0][1])
                Path(args[args.index("--output")+1]).write_bytes(b"x"*1024)
                Path(args[args.index("--dump-header")+1]).write_text("")
                return subprocess.CompletedProcess(args,0)
            p,meta=download("EE",t,fake,sources=EXPANSION)
            self.assertEqual(meta["extract_provider"],"Geofabrik")
            self.assertEqual(meta["source_bytes"],1024)
            self.assertEqual(set(SOURCES),{"IS","LU"})
