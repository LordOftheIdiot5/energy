import sys,tempfile,unittest,json
from datetime import date,timedelta,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from delivery_prices import bounds,nordic_day,european_day
from open_history import append
class V901Data(unittest.TestCase):
    def slots(self,day,step=3600):
        a,b=bounds(day);rows=[]
        while a<b:
            x=a+timedelta(seconds=step);rows.append({"time_start":a.isoformat(),"time_end":x.isoformat(),"NOK_per_kWh":-1,"EUR_per_kWh":0});a=x
        return rows
    def test_dst_and_zero(self):
        for day,n in [(date(2026,3,29),23),(date(2026,10,25),25),(date(2026,11,17),24)]:
            rows=self.slots(day,900);r=nordic_day(rows,"NOK_per_kWh",day);self.assertEqual(len(r["hours"]),n);self.assertEqual(r["eur"],[0]*n);self.assertEqual(len(set(r["hourStartsUtc"])),n)
            with self.assertRaises(ValueError):nordic_day(rows[:-1],"NOK_per_kWh",day)
            bad=[dict(x) for x in rows];bad[0]["EUR_per_kWh"]=None
            with self.assertRaises(ValueError):nordic_day(bad,"NOK_per_kWh",day)
    def test_archive(self):
        day=date(2026,11,17);rows=self.slots(day,900);ts=[int(datetime.fromisoformat(r["time_start"]).timestamp()) for r in rows]
        v=european_day({"unix_seconds":ts,"price":[-10]*len(ts)},day)
        with self.assertRaises(ValueError):european_day({"unix_seconds":ts[:-1],"price":[0]*(len(ts)-1)},day)
        row={**v,"zone":"NO2","priceSource":"Energy-Charts / SMARD","licenseInfo":"CC BY 4.0"}
        payload={"generated":"2026-11-17T21:00:00+00:00","europe":[row,{**row,"zone":"FI"},{**row,"stale":True}]}
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(append(d,payload),1);self.assertEqual(append(d,payload),0)
            row["cents"][0]=2;self.assertEqual(append(d,payload),1)
            rec=json.loads((Path(d)/"archive/day-ahead/2026-11.json").read_text())["rows"]
            self.assertEqual(len(rec),2);self.assertEqual(rec[0]["prices"][0],-10);self.assertEqual(rec[1]["prices"][0],20)
