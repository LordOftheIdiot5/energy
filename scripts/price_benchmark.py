"""NO2 day-ahead daily mean benchmark. Research, not intraday or trading advice.
Target UTC day D. Simulated origin D-1 00 UTC (before target auction).
Use completed daily delivery intervals through D-2; no target price or future weather.
Retrospective revised prices, not archived publication vintages.
"""
import argparse,datetime as dt,hashlib,json,math,statistics as st,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from hydro_extended import write_json
UTC=dt.timezone.utc
URL="https://api.energy-charts.info/price"
ZONE="NO2"
def number(x):return type(x) in (int,float) and math.isfinite(x)
def open_license(s):
    s=str(s or "").lower()
    return ("cc by 4.0" in s or "creativecommons.org/licenses/by/4.0" in s) and not any(x in s for x in ("private and internal","private use","non-commercial","prohibited","not permitted"))
def day_prices(d,start,end):
    if not open_license(d.get("license_info")):raise ValueError("Price reuse not confirmed: "+str(d.get("license_info"))[:200])
    if d.get("unit")!="EUR/MWh":raise ValueError("Unexpected price unit")
    ts,ps=d.get("unix_seconds"),d.get("price")
    if not isinstance(ts,list) or not isinstance(ps,list) or len(ts)!=len(ps):raise ValueError("Price array mismatch")
    groups={};seen=set()
    for t,p in zip(ts,ps):
        if type(t)!=int or t in seen:raise ValueError("Duplicate or invalid timestamp")
        seen.add(t);x=dt.datetime.fromtimestamp(t,UTC)
        if start<=x.date()<=end:groups.setdefault(x.date(),{})[t]=p
    out={};bad=0
    for day,points in sorted(groups.items()):
        start_ts=int(dt.datetime.combine(day,dt.time(),UTC).timestamp())
        # EU day-ahead switched to quarter-hour on delivery 1 Oct 2025
        # local market time: 30 Sep 22:00 UTC. Validate every interval.
        change=int(dt.datetime(2025,9,30,22,tzinfo=UTC).timestamp())
        expected=[];t=start_ts
        while t<start_ts+86400:
            seconds=900 if t>=change else 3600
            expected.append((t,seconds));t+=seconds
        if set(points)!=set(t for t,_ in expected) or not all(number(points[t]) for t,_ in expected):bad+=1;continue
        out[day]=sum(points[t]*seconds for t,seconds in expected)/86400
    return out,bad
def download(year):
    start,end=dt.date(year,1,1),dt.date(year,12,31)
    url=f"{URL}?bzn={ZONE}&start={start}T00:00Z&end={end}T23:59Z"
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={"User-Agent":"NordlEnergy/1.0 (+https://energy.nordl.dev/)"}),timeout=60) as r:raw=r.read(8_000_001)
            if len(raw)>8_000_000:raise ValueError("Oversized price response")
            d=json.loads(raw);rows,bad=day_prices(d,start,end)
            if len(rows)<330:raise ValueError(f"Insufficient complete UTC days {year}: {len(rows)}, rejected {bad}")
            return rows,{"year":year,"days":len(rows),"rejected_days":bad,"source":url,"sha256":hashlib.sha256(raw).hexdigest(),"license":d["license_info"]}
        except HTTPError as e:
            if e.code!=429 or attempt==2:raise
            wait=e.headers.get("Retry-After","60")
            time.sleep(max(31,min(120,int(wait) if wait.isdigit() else 60)))
def feature_rows(prices):
    rows=[]
    for day,actual in sorted(prices.items()):
        lag=lambda n:prices.get(day-dt.timedelta(days=n))
        if any(lag(i) is None for i in range(2,30)):continue
        phase=2*math.pi*(day.timetuple().tm_yday-1)/365.2425
        recent=st.mean(lag(i) for i in range(2,9));monthly=st.median(lag(i) for i in range(2,30))
        rows.append({"day":day,"actual":actual,"recent":lag(2),"weekly":lag(7),"median":monthly,"x":[lag(2),lag(7),recent,monthly,math.sin(phase),math.cos(phase),int(day.weekday()>=5)]})
    return rows
def fit(rows):
    x=[r["x"] for r in rows];y=[r["actual"] for r in rows];p=len(x[0]);m=[st.mean(v[j] for v in x) for j in range(p)];s=[st.pstdev(v[j] for v in x) or 1 for j in range(p)];xx=[[1]+[(v-a)/b for v,a,b in zip(row,m,s)] for row in x];n=p+1
    a=[[sum(v[i]*v[j] for v in xx)+(10 if i==j and i else 0) for j in range(n)]+[sum(v[i]*t for v,t in zip(xx,y))] for i in range(n)]
    for j in range(n):
        k=max(range(j,n),key=lambda i:abs(a[i][j]));a[j],a[k]=a[k],a[j]
        q=a[j][j]
        if abs(q)<1e-12:raise ValueError("Singular regression")
        a[j]=[v/q for v in a[j]]
        for i in range(n):
            if i!=j:
                q=a[i][j];a[i]=[v-q*w for v,w in zip(a[i],a[j])]
    beta=[v[-1] for v in a]
    return lambda row:sum(v*b for v,b in zip([1]+[(v-a)/b for v,a,b in zip(row["x"],m,s)],beta))
def quantile(v,p):
    s=sorted(v);i=(len(s)-1)*p;j=int(i);return s[j]+(i-j)*(s[min(j+1,len(s)-1)]-s[j])
def evaluate(rows):
    train=[r for r in rows if r["day"].year<=2023];cal=[r for r in rows if r["day"].year==2024];test=[r for r in rows if r["day"].year==2025]
    if len(train)<500 or len(cal)<250 or len(test)<250:raise ValueError("Insufficient chronological data")
    pred=fit(train);res=[r["actual"]-pred(r) for r in cal];lo,hi=quantile(res,.1),quantile(res,.9)
    funcs={"lag_2d":lambda r:r["recent"],"lag_7d":lambda r:r["weekly"],"median_28d":lambda r:r["median"],"ridge":pred}
    mae={k:st.mean(abs(f(r)-r["actual"]) for r in test) for k,f in funcs.items()}
    rmse={k:math.sqrt(st.mean((f(r)-r["actual"])**2 for r in test)) for k,f in funcs.items()}
    return {"train":len(train),"calibration":len(cal),"test":len(test),"mae_eur_mwh":mae,"rmse_eur_mwh":rmse,"ridge_beats_all":mae["ridge"]<min(mae[k] for k in funcs if k!="ridge"),"nominal_coverage":.8,"test_interval_coverage":st.mean(pred(r)+lo<=r["actual"]<=pred(r)+hi for r in test),"residual_interval_eur_mwh":[lo,hi],"negative_price_days":sum(r["actual"]<0 for r in test)}
def run():
    data={};sources=[]
    for year in range(2022,2026):
        if sources:time.sleep(31)
        rows,s=download(year);data.update(rows);sources.append(s);print("Price source",year,len(rows),"complete UTC days",flush=True)
    return {"schema_version":1,"status":"retrospective_research_only","zone":ZONE,"unit":"EUR/MWh","generated":dt.datetime.now(UTC).isoformat(),"attribution":"Energy-Charts.info / Bundesnetzagentur | SMARD.de; Nordl daily duration-weighted means and model evaluation","sources":sources,"train":"2022–2023","calibration":"2024","test":"2025","metrics":evaluate(feature_rows(data)),"notice":"Daily average day-ahead price, not intraday prices. Historical revised prices, no archived publication times. No load/weather/commodity forecast vintages or live recommendation. Negative prices preserved."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();d=run();a.output.parent.mkdir(parents=True,exist_ok=True);write_json(a.output,d);print("V86_BENCHMARK="+json.dumps(d,ensure_ascii=True),flush=True)
