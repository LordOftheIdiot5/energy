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

    def test_latvia_recovers_same_provider_after_partial_download(self):
        with tempfile.TemporaryDirectory() as t:
            calls=[];delays=[]
            def runner(args,check):
                calls.append(args[-1])
                output=Path(args[args.index("--output")+1])
                headers=Path(args[args.index("--dump-header")+1])
                self.assertFalse(output.exists())
                self.assertFalse(headers.exists())
                if len(calls)==1:
                    output.write_bytes(b"partial")
                    headers.write_text("stale header")
                    return subprocess.CompletedProcess(args,7)
                output.write_bytes(b"x"*1024)
                headers.write_text("Last-Modified: current")
                return subprocess.CompletedProcess(args,0)
            _,meta=download("LV",t,runner,sources=EXPANSION,sleep=delays.append)
            self.assertEqual(calls,[EXPANSION["LV"][0][1]]*2)
            self.assertEqual(delays,[2])
            self.assertEqual(meta["source_last_modified"],"current")

    def test_expansion_denial_and_size_limit_never_switch_provider(self):
        for code in (22,63):
            with self.subTest(code=code),tempfile.TemporaryDirectory() as t:
                calls=[]
                def runner(args,check):
                    calls.append(args[-1])
                    return subprocess.CompletedProcess(args,code)
                with self.assertRaises(RuntimeError):
                    download("EE",t,runner,sources=EXPANSION,sleep=lambda _:None)
                self.assertEqual(calls,[EXPANSION["EE"][0][1]])

    def test_fallback_limits_are_exact_provider_scoped(self):
        for region,expected in (("LV",175_000_000),("FO",150_000_000)):
            with self.subTest(region=region),tempfile.TemporaryDirectory() as t:
                calls=[]
                def runner(args,check):
                    calls.append((args[-1],int(args[args.index("--max-filesize")+1])))
                    if len(calls)<=2:
                        return subprocess.CompletedProcess(args,7)
                    Path(args[args.index("--output")+1]).write_bytes(b"x"*1024)
                    Path(args[args.index("--dump-header")+1]).write_text("Last-Modified: fixture")
                    return subprocess.CompletedProcess(args,0)
                _,meta=download(region,t,runner,sources=EXPANSION,sleep=lambda _:None)
                self.assertEqual(calls,[(EXPANSION[region][0][1],150_000_000)]*2+[(EXPANSION[region][1][1],expected)])
                self.assertEqual(meta["extract_provider"],"BBBike")
