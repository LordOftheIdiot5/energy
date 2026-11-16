"""Retrospective seasonal baseline with chronological residual calibration.
No historical weather forecasts are supplied: this is NOT a weather model.
"""
import json,statistics,math
from pathlib import Path
from datetime import datetime,timezone
from hydro_extended import write_json
def monday(r): return datetime.fromisocalendar(r["year"],r["week"],1)
def q(v,p):
    s=sorted(v);i=(len(s)-1)*p;j=int(i)
    return s[j]+(s[min(j+1,len(s)-1)]-s[j])*(i-j)
def model(rows):
    rows=sorted(rows,key=monday)
    byweek={};residual=[];test=[];last=rows[-1] if rows else None
    # Rolling origin: prior-year weekly changes only; residual range uses earlier prediction errors.
    for a,b in zip(rows,rows[1:]):
        if (monday(b)-monday(a)).days!=7: continue
        k=a["week"];delta=b["fill_pct"]-a["fill_pct"];prior=[v for y,v in byweek.get(k,[]) if y<a["year"]]
        if len(prior)>=5:
            pred=max(0,min(100,a["fill_pct"]+statistics.median(prior)));actual=b["fill_pct"]
            if len(residual)>=100:
                lo=max(0,min(100,pred+q(residual[-260:],.1)));hi=max(0,min(100,pred+q(residual[-260:],.9)))
                test.append((abs(actual-pred),abs(actual-a["fill_pct"]),lo<=actual<=hi))
            residual.append(actual-pred)
        byweek.setdefault(k,[]).append((a["year"],delta))
    out={"evaluated":len(test),"seasonal_mae_pp":statistics.mean(t[0] for t in test) if test else None,"persistence_mae_pp":statistics.mean(t[1] for t in test) if test else None,"interval_coverage":statistics.mean(t[2] for t in test) if test else None}
    if last:
        prior=[v for y,v in byweek.get(last["week"],[]) if y<last["year"]]
        if len(prior)>=5 and len(residual)>=100:
            p=max(0,min(100,last["fill_pct"]+statistics.median(prior)))
            out.update({"origin_year":last["year"],"origin_week":last["week"],"baseline_pct":p,"low_pct":max(0,min(100,p+q(residual[-260:],.1))),"high_pct":max(0,min(100,p+q(residual[-260:],.9)))})
    return out
def refresh(directory):
    directory=Path(directory);src=json.loads((directory/"hydro-v1.json").read_text(encoding="utf-8"))
    rows=src["rows"];zones={}
    for z in ["NO1","NO2","NO3","NO4","NO5"]:
        valid=[r for r in rows if r["zone"]==z and isinstance(r.get("fill_pct"),(int,float)) and 0<=r["fill_pct"]<=100]
        zones[z]=model(valid)
    payload={"schema_version":1,"source":"hydro-v1.json","method":"Rolling historical seasonal-change baseline with preceding residual quantiles; retrospective revised observations, not archived forecast vintages; no weather inputs.","zones":zones}
    path=directory/"hydro-validation-v1.json"
    if not path.exists() or json.loads(path.read_text(encoding="utf-8"))!=payload: write_json(path,payload)
