"""V85 retrospective weekly storage benchmark, not an operational forecast.

All hydro observations are revised historical values. Weather features are
lagged observed/modelled grid cells; no future realised weather is used.
Fixed training 2012–2017, calibration 2018–2020, untouched test 2021–2025.
Dates are storage ISO week labels, with a two-week lag for weather inputs.
This is a point-sample experiment, not a basin water-balance model.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import statistics as stats
from pathlib import Path
from weather_geography import POINTS, GTS, download
from hydro_extended import write_json

START=dt.date(2011,12,1)
END=dt.date(2025,12,31)
THEMES={"rr":{"mm"},"tm":{"celcius","celsius","°c","degc","c"},"swe":{"mm"}}
ZONES=("NO1","NO2","NO3","NO4","NO5")
def number(x):return type(x) in (int,float) and math.isfinite(x)
def monday(r):return dt.date.fromisocalendar(r["year"],r["week"],1)
def normalize(d,point,theme,start,end):
    if d.get("Theme")!=theme or str(d.get("Unit","")).lower() not in THEMES[theme] or d.get("TimeResolution")!=1440:
        raise ValueError("Unexpected theme/unit/resolution: "+str((d.get("Theme"),d.get("Unit"),d.get("TimeResolution"))))
    if not str(d.get("StartDate","")).startswith(start.strftime("%d.%m.%Y")) or not str(d.get("EndDate","")).startswith(end.strftime("%d.%m.%Y")):raise ValueError("Source dates differ")
    x,y=point[3:]
    if not number(d.get("X")) or not number(d.get("Y")) or abs(d["X"]-x)>1500 or abs(d["Y"]-y)>1500:raise ValueError("Source grid differs")
    raw=d.get("Data")
    if not isinstance(raw,list) or len(raw)!=(end-start).days+1:raise ValueError("Unexpected daily count")
    return {(start+dt.timedelta(days=i)):v for i,v in enumerate(raw) if number(v) and v!=d.get("NoDataValue") and (-80<=v<=60 if theme=="tm" else 0<=v<=5000)}
def collect():
    data={};sources=[]
    for p in POINTS:
        for theme in THEMES:
            url=f"{GTS}/{p[3]}/{p[4]}/{START.isoformat()}/{END.isoformat()}/{theme}.json"
            try:
                raw,_=download(url,2_000_000,"application/json")
                d=json.loads(raw);series=normalize(d,p,theme,START,END)
                data[(p[0],theme)]=series
                sources.append({"point":p[0],"theme":theme,"days":len(series),"source":url,"sha256":hashlib.sha256(raw).hexdigest(),"source_utm33":[d["X"],d["Y"]]})
                print("Source",p[0],theme,len(series),"days",flush=True)
            except Exception as e:
                print("Source failed",p[0],theme,str(e)[:180],flush=True)
                raise
    return data,sources
def weather_features(data,week):
    # Use only the 7-day interval 14–8 days before the origin ISO Monday.
    # No weather from the target week, or even the reported storage week.
    days=[week-dt.timedelta(days=i) for i in range(14,7,-1)]
    out=[]
    for theme in THEMES:
        per=[]
        for point in POINTS:
            series=data.get((point[0],theme),{})
            if any(d not in series for d in days):return None
            values=[series[d] for d in days]
            per.append(sum(values) if theme=="rr" else stats.mean(values))
        # Arithmetic mean across five research cells, not country/basin averages.
        out.append(stats.mean(per))
    return out
def samples(hydro,weather,zone):
    by={}
    for r in hydro:
        if r.get("zone")!=zone or not number(r.get("fill_pct")) or not 0<=r["fill_pct"]<=100:continue
        try:w=monday(r)
        except (ValueError,TypeError,KeyError):continue
        if w in by:raise ValueError("Duplicate archive week")
        by[w]=r["fill_pct"]
    weekly={}
    for w,v in sorted(by.items()):
        target=w+dt.timedelta(days=7)
        if target in by and target<dt.date(2018,1,1):
            weekly.setdefault(w.isocalendar().week,[]).append(by[target]-v)
    out=[]
    for w,fill in sorted(by.items()):
        prev=w-dt.timedelta(days=7);target=w+dt.timedelta(days=7)
        if w.year<2012 or target.year>2025 or prev not in by or target not in by:continue
        # Do not train with seasonal features estimated using later training years.
        phase=2*math.pi*(w.isocalendar().week-1)/52.1775
        x=[fill,fill-by[prev],math.sin(phase),math.cos(phase)]
        wx=weather_features(weather,w)
        if wx is None:continue
        seasonal=weekly.get(w.isocalendar().week,[])
        if not seasonal:continue
        out.append({"week":w,"target":target,"fill":fill,"actual":by[target],"x":x,"wx":wx,"seasonal":max(0,min(100,fill+stats.median(seasonal)))})
    return out
def fit(rows,weather):
    x=[r["x"]+(r["wx"] if weather else []) for r in rows];y=[r["actual"]-r["fill"] for r in rows]
    p=len(x[0]);means=[stats.mean(v[j] for v in x) for j in range(p)];scales=[stats.pstdev(v[j] for v in x) or 1 for j in range(p)]
    xx=[[1]+[(v-m)/s for v,m,s in zip(row,means,scales)] for row in x];n=p+1
    a=[[sum(z[i]*z[j] for z in xx)+(10 if i==j and i else 0) for j in range(n)]+[sum(z[i]*v for z,v in zip(xx,y))] for i in range(n)]
    for j in range(n):
        k=max(range(j,n),key=lambda i:abs(a[i][j]));a[j],a[k]=a[k],a[j];pivot=a[j][j]
        if abs(pivot)<1e-12:raise ValueError("Singular fit")
        a[j]=[v/pivot for v in a[j]]
        for i in range(n):
            if i!=j:
                q=a[i][j];a[i]=[v-q*w for v,w in zip(a[i],a[j])]
    beta=[r[-1] for r in a]
    def predict(r):
        v=r["x"]+(r["wx"] if weather else []);z=[1]+[(x-m)/s for x,m,s in zip(v,means,scales)]
        return max(0,min(100,r["fill"]+sum(x*b for x,b in zip(z,beta))))
    return predict
def quantile(v,p):
    s=sorted(v);i=(len(s)-1)*p;j=int(i);return s[j]+(i-j)*(s[min(j+1,len(s)-1)]-s[j])
def evaluate(rows):
    # Split by both origin and target, so no target crosses a split boundary.
    split=lambda lo,hi:[r for r in rows if lo<=r["week"].year and r["target"].year<=hi]
    train,cal,test=split(2012,2017),split(2018,2020),split(2021,2025)
    n={"train":len(train),"calibration":len(cal),"test":len(test)}
    if min(len(train)/200,len(cal)/100,len(test)/200)<1:return {"status":"insufficient_data",**n}
    baseline=fit(train,False);wx=fit(train,True)
    residual=[r["actual"]-wx(r) for r in cal];lo,hi=quantile(residual,.1),quantile(residual,.9)
    predictions={"persistence":lambda r:r["fill"],"seasonal":lambda r:r["seasonal"],"hydro_only":baseline,"weather_lagged":wx}
    mae={k:stats.mean(abs(fn(r)-r["actual"]) for r in test) for k,fn in predictions.items()}
    cover=stats.mean(max(0,wx(r)+lo)<=r["actual"]<=min(100,wx(r)+hi) for r in test)
    return {"status":"retrospective_evaluated",**n,"mae_pp":{k:round(v,4) for k,v in mae.items()},"weather_improves_all":mae["weather_lagged"]<min(mae["persistence"],mae["seasonal"],mae["hydro_only"]),"nominal_interval_coverage":0.8,"test_interval_coverage":round(cover,4),"calibration_residual_pp":[round(lo,3),round(hi,3)]}
def run(directory):
    directory=Path(directory);raw=(directory/"hydro-v1.json").read_bytes();hydro=json.loads(raw)
    if hydro.get("schema_version")!=1 or not isinstance(hydro.get("rows"),list):raise ValueError("Invalid hydro archive")
    weather,sources=collect()
    zones={z:evaluate(samples(hydro["rows"],weather,z)) for z in ZONES}
    return {"schema_version":1,"generated":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"retrospective_research_only","train":"2012–2017","calibration":"2018–2020","test":"2021–2025","weather_lag_days":"14–8 before origin ISO Monday","hydro_sha256":hashlib.sha256(raw).hexdigest(),"weather_sources":sources,"zones":zones,"notice":"Revised historical NVE storage and lagged seNorge research-cell values. Not as-of forecast vintages, catchment means or live predictions. Fixed chronological splits; no operational forecast authorized. MAE in percentage points."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=Path("data"));p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    d=run(a.data);a.output.parent.mkdir(parents=True,exist_ok=True);write_json(a.output,d)
    print("V85_BENCHMARK="+json.dumps(d,separators=(",",":"),ensure_ascii=True),flush=True)
    if any(v["status"]!="retrospective_evaluated" for v in d["zones"].values()):raise SystemExit("Insufficient benchmark coverage")
