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
    def test_revision_schedule(self):
        now=datetime(2026,11,19,20,tzinfo=timezone.utc)
        self.assertEqual(revision_month(now,{}),("2026-10","preliminary"))
        self.assertEqual(revision_month(now,{"preliminary":["2026-10"]}),("2025-07","final"))
        self.assertEqual(revision_month(datetime(2026,2,1,tzinfo=timezone.utc),{}),("2024-01","final"))
    def test_metadata_gate(self):
        columns=[{"dbColumn":f,"unit":u,"comment":DIRECTIONS.get(f,"")} for f,u in UNITS.items()]
        meta={"datasetName":"GenerationProdTypeExchange","resolution":"1 hour (PT1H)","columns":columns,"caution":METHOD_CHANGE}
        verify_metadata(meta)
        columns[0]["unit"]="MW"
        with self.assertRaises(ValueError):verify_metadata(meta)
    def test_history_window_and_no_partial_response(self):
        now=datetime(2026,11,19,20,tzinfo=timezone.utc)
        row={k:0 for k in FIELDS};row.update(TimeUTC="2014-12-31T23:00:00",TimeDK="2015-01-01T00:00:00",PriceArea="DK1",Version="Final")
        d={"dataset":"GenerationProdTypeExchange","records":[row,{**row,"PriceArea":"DK2"}],"total":2}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises(ValueError):collect(p,True,getter=lambda _:dict(d,total=3),now=now)
            self.assertFalse((p/"energinet-backfill-state-v1.json").exists())
            collect(p,True,getter=lambda _:d,now=now)
            self.assertEqual(read(p/"energinet-backfill-state-v1.json",{})["next"],"2015-02")
            self.assertEqual(read(p/"energinet-backfill-state-v1.json",{})["completed"][0]["expected"],1488)
            self.assertTrue((p/"energinet-history/2014-12.json").exists())
