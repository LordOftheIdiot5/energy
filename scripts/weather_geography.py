"""V82 weather evidence: bounded radar images and dated seNorge SWE samples.
No interpolation, basin averages or forecasts inferred from these points.
"""
import datetime as dt
import email.utils
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import urllib.request
from hydro_extended import write_json

RADAR="https://api.met.no/weatherapi/radar/2.0/?type=5level_reflectivity&area=nordic&content=image"
GTS="https://gts.nve.no/api/GridTimeSeries"
UA="NordlEnergy/1.0 (+https://energy.nordl.dev/)"
# Representative research points, not plant or catchment centroids. ETRS89 UTM33
# transformed from the documented lon/lat with EPSG:25833 (pyproj).
POINTS=[
 ("Finse",7.50,60.60,89875,6741670),
 ("Hjerkinn",9.54,62.22,216328,6910660),
 ("Sirdal",6.85,58.91,31285,6558652),
 ("Sjusjoen",10.70,61.15,268645,6787104),
 ("Kautokeino",23.04,69.01,820622,7676523)
]
def iso_time():
    return dt.datetime.now(dt.timezone.utc).isoformat()
def download(url,limit,accept):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept})
    with urllib.request.urlopen(req,timeout=25) as response:
        raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError("Response too large")
        return raw,response.headers
def finite(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def normalize_swe(d,point,day,url):
    name,lon,lat,x,y=point
    if d.get("Theme")!="swe" or d.get("Unit")!="mm" or d.get("TimeResolution")!=1440:raise ValueError("Unexpected SWE theme or units")
    values=d.get("Data")
    if not isinstance(values,list) or len(values)!=1:raise ValueError("Unexpected day count")
    if not str(d.get("StartDate","")).startswith(day.strftime("%d.%m.%Y")) or not str(d.get("EndDate","")).startswith(day.strftime("%d.%m.%Y")):raise ValueError("Source dates differ")
    value=values[0]
    if not finite(value) or value<0 or value==d.get("NoDataValue"):raise ValueError("Missing SWE")
    if not finite(d.get("X")) or not finite(d.get("Y")) or abs(d["X"]-x)>1500 or abs(d["Y"]-y)>1500:raise ValueError("Source grid coordinates differ")
    return {"id":name,"geometry":[lon,lat],"requested_utm33":[x,y],"source_utm33":[d["X"],d["Y"]],"date":day.isoformat(),"value_mm":value,"altitude_m":d.get("Altitude") if finite(d.get("Altitude")) else None,"source":url}
def atomic_bytes(path,data):
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        try:
            f.write(data)
            tmp=f.name
        except BaseException:
            os.unlink(f.name);raise
    try:os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def refresh(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    dest=directory/"weather-geography-v1.json"
    try:old=json.loads(dest.read_text(encoding="utf-8"))
    except (OSError,ValueError):old={}
    now=dt.datetime.now(dt.timezone.utc);day=now.date()-dt.timedelta(days=2)
    radar=old.get("radar") or None
    try:
        raw,headers=download(RADAR,5_000_000,"image/png")
        if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw)<100:raise ValueError("Not a PNG")
        digest=hashlib.sha256(raw).hexdigest()
        fn="radar-nordic-"+digest[:16]+".png"
        atomic_bytes(directory/fn,raw)
        radar={"file":fn,"retrieved":iso_time(),"last_modified":headers.get("Last-Modified"),"source":RADAR,"sha256":digest}
    except Exception as e:print("  ! weather radar:",type(e).__name__)
    rows=[]
    # Do not repeat successfully fetched daily grid samples each hourly run.
    cached={r["id"]:r for r in old.get("snow",[]) if r.get("date")==day.isoformat()}
    for point in POINTS:
        if point[0] in cached:rows.append(cached[point[0]]);continue
        x,y=point[3:];url=f"{GTS}/{x}/{y}/{day.isoformat()}/{day.isoformat()}/swe.json"
        try:
            raw,_=download(url,200_000,"application/json")
            rows.append(normalize_swe(json.loads(raw),point,day,url))
        except Exception as e:print("  ! SWE",point[0],type(e).__name__)
    snapshot={"schema_version":1,"generated":iso_time(),"requested_day":day.isoformat(),"radar":radar,"snow":rows,"snow_expected":len(POINTS),"snow_source":"https://api.nve.no/doc/gridtimeseries-data-gts/","snow_license":"https://data.norge.no/nlod/","notice":"SWE model samples in mm water, not catchment means; radar source retrieval time is not capture time."}
    write_json(dest,snapshot)
    # Only clean files belonging to this collector after metadata is published.
    for p in directory.glob("radar-nordic-*.png"):
        if not radar or p.name!=radar["file"]:p.unlink(missing_ok=True)
    print("Weather geography:",len(rows),"SWE cells;",bool(radar),"radar snapshot")
    return snapshot
if __name__=="__main__":
    import sys
    refresh(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent/"data")
