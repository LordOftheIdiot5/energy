"""Read the single Stockwatch ENTSO-E feed without any API credentials."""
from datetime import datetime,timezone,timedelta
import json
import math
import urllib.request

URL="https://stocks.nordl.dev/data/entsoe-open.json"
ZONES={"NO1","NO2","NO3","NO4","NO5","SE1","SE2","SE3","SE4","DK1","DK2","FI","DE-LU","FR","NL"}
BORDERS={("NO1","SE3"),("NO4","SE1"),("NO2","DK1")}
BORDERS|={(b,a) for a,b in list(BORDERS)}
CAP=1_000_000

def dt(s):
    if not isinstance(s,str) or not s.endswith("Z"):
        raise ValueError("utc")
    return datetime.fromisoformat(s[:-1]+"+00:00")

def validate(doc,now=None):
    now=now or datetime.now(timezone.utc)
    if (doc.get("schemaVersion")!=1 or doc.get("source")!="ENTSO-E Transparency Platform"
            or doc.get("license")!="CC BY 4.0" or doc.get("reuseListDate")!="2023-10-18"):
        raise ValueError("scope")
    generated=dt(doc["generated"])
    if not now-timedelta(days=4)<=generated<=now+timedelta(minutes=5):
        raise ValueError("freshness")
    all_series=doc["series"]
    if not isinstance(all_series,list) or len(all_series)>21:
        raise ValueError("series")
    series=[]; ids=set()
    for s in all_series:
        if s["kind"]=="day_ahead_load_forecast" and s.get("zone") in ZONES and s.get("article")=="6.1.b":
            meta={"kind":s["kind"],"zone":s["zone"]}
            key="load-forecast:"+s["zone"]
        elif s["kind"]=="physical_flow" and (s.get("from"),s.get("to")) in BORDERS and s.get("article")=="12.1.g":
            meta={"kind":s["kind"],"from":s["from"],"to":s["to"]}
            key="flow:"+s["from"]+":"+s["to"]
        else:
            raise ValueError("unapproved_series")
        if s["id"]!=key or key in ids or s.get("unit")!="MW":
            raise ValueError("identity")
        ids.add(key)
        start,end=dt(s["startUtc"]),dt(s["endUtc"])
        if end-start!=timedelta(days=1) or not generated-timedelta(days=2)<=end<=generated:
            raise ValueError("window")
        if s.get("status")!="ok":
            if s.get("points"):
                raise ValueError("failed_points")
            continue
        points=s["points"]
        if not isinstance(points,list) or not 1<=len(points)<=96:
            raise ValueError("count")
        clean=[];prev=None
        for p in points:
            at=dt(p["startUtc"])
            value=p["mw"]
            if (not start<=at<end or prev is not None and at<=prev
                 or type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1_000_000
                 or meta["kind"]=="day_ahead_load_forecast" and value<0
                 or p["resolutionMinutes"] not in (15,30,60)
                 or p["curveType"] not in ("A01","A03")):
                raise ValueError("point")
            prev=at
            clean.append({k:p[k] for k in ("startUtc","mw","resolutionMinutes","curveType")})
        series.append({**meta,"id":key,"unit":"MW","startUtc":s["startUtc"],"endUtc":s["endUtc"],"points":clean})
    if not series:
        raise ValueError("no_valid_series")
    return {"status":"ok","generated":doc["generated"],"source":"ENTSO-E Transparency Platform",
            "sourceUrl":"https://transparency.entsoe.eu/","license":"CC BY 4.0",
            "licenseUrl":"https://creativecommons.org/licenses/by/4.0/",
            "changes":"Selected validated UTC MW points copied from Stockwatch, no interpolation or aggregation.",
            "series":series}

def collect_shared():
    try:
        req=urllib.request.Request(URL,headers={"User-Agent":"nordl-energy/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=12) as resp:
            if resp.geturl()!=URL:
                raise ValueError("redirect")
            raw=resp.read(CAP+1)
        if len(raw)>CAP:
            raise ValueError("size")
        return validate(json.loads(raw))
    except Exception:
        return {"status":"unavailable","source":"ENTSO-E Transparency Platform"}
