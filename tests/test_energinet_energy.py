import sys,unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from energinet_energy import *
class EnerginetTests(unittest.TestCase):
    def test_source_and_revisions(self):
        now=datetime(2026,11,19,20,tzinfo=timezone.utc)
        row={k:0 for k in FIELDS};row.update(TimeUTC="2026-11-19T18:00:00",TimeDK="2026-11-19T19:00:00",PriceArea="DK1",Version="Initial",Biogas=-1,HydroPower=None)
        def norm(r):return normalize({"dataset":"GenerationProdTypeExchange","records":[r]},now)
        a=norm(row);self.assertEqual(a[0]["Biogas"],-1);self.assertIsNone(a[0]["HydroPower"])
        with self.assertRaises(ValueError):norm({**row,"TimeDK":"2026-11-19T18:00:00"})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);archive(p,a,now.isoformat());archive(p,norm({**row,"Version":"Final","GrossCon":10}),now.isoformat());archive(p,a,now.isoformat())
            self.assertEqual(read(p/"energinet-v1.json",{})["rows"][0]["GrossCon"],10)
            self.assertEqual(len(read(p/"energinet-revisions/2026-11.json",{})["rows"]),1)
            self.assertEqual(len(list(public_files(p))),2)
