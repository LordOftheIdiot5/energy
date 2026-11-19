"""Bounded authenticated collectors; credentials never enter published files."""
import hashlib,json,math,os,re,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from hydro_extended import write_json
NVE="https://hydapi.nve.no/api/v1/"
FG="https://data.fingrid.fi/api/datasets/"
LICENSES={"hydapi":"https://data.norge.no/nlod/","fingrid":"https://creativecommons.org/licenses/by/4.0/"}
SOURCES={"hydapi":"NVE HydAPI","fingrid":"Fingrid / data.fingrid.fi"}
FG_IDS={192:"Electricity production",193:"Electricity consumption",181:"Wind power production",191:"Hydro power production"}
STATION=re.compile(r"^\d+\.\d+\.\d+$")
PARAMS={1000:"Water stage",1001:"Discharge",1003:"Water temperature"}
def number(v):return type(v) in (int,float) and math.isfinite(v)
def utc(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Timestamp missing offset")
    return t.astimezone(timezone.utc).isoformat()
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def request(url,key):
    with urlopen(Request(url,headers={"X-API-Key":key,"Accept":"application/json","User-Agent":"Nordl Energy research / energy.nordl.dev"}),timeout=40) as r:
        return json.loads(r.read(25_000_000))
def read(path,default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
def base(provider):
    return {"schema_version":1,"provider":provider,"attribution":SOURCES[provider],"license":LICENSES[provider],"notice":"Normalized source observations; gaps not filled, provisional measurements may change."}
def nve_data(d):
    if d.get("license","").rstrip("/") not in ("https://data.norge.no/nlod","https://data.norge.no/nlod/en","https://data.norge.no/nlod/no"):raise ValueError("NVE licence not confirmed")
    if not isinstance(d.get("data"),list):raise ValueError("NVE response schema")
    return d["data"]
def normalize_stations(d):
    rows=[];seen=set()
    for s in nve_data(d):
        sid=s.get("stationId","");lat=s.get("latitude");lon=s.get("longitude")
        if not STATION.fullmatch(str(sid)) or sid in seen or not number(lat) or not number(lon) or not(-90<=lat<=90 and -180<=lon<=180):continue
        seen.add(sid)
        series=[]
        for r in s.get("seriesList") or []:
            if type(r.get("parameter")) is not int:continue
            series.append({k:r[k] for k in ("parameter","parameterName","versionNo","unit","serieFrom","serieTo","resolutionList") if k in r})
        rows.append({"stationId":sid,"name":s.get("stationName") or sid,"geometry":[lon,lat],"river":s.get("riverName"),"county":s.get("countyName"),"council":s.get("councilName"),"regineNo":s.get("regineNo"),"reservoirNo":s.get("reservoirNo"),"status":s.get("stationStatusName"),"series":series})
    if not rows:raise ValueError("No hydrological stations")
    return rows
def select_samples(stations):
    # A stable stratified sample, not asserted to represent reservoirs or price zones.
    groups={}
    for s in stations:
        if str(s.get("status")).lower() not in ("aktiv","active"):continue
        available={r["parameter"] for r in s["series"] if r.get("serieTo") is None}
        if 1001 not in available:continue
        groups.setdefault(s.get("county") or "Unknown",[]).append(s)
    chosen=[]
    for county,rows in sorted(groups.items()):
        chosen.append(sorted(rows,key=lambda s:s["stationId"])[0])
    return chosen[:20]
def expanded_samples(stations,stamp,extra=8):
    # Keep the established county sample stable. Rotate a bounded additional
    # station batch daily, prioritising explicitly active discharge series.
    core=select_samples(stations)
    existing={s["stationId"] for s in core}
    candidates=sorted((s for s in stations if s["stationId"] not in existing and str(s.get("status")).lower() in ("aktiv","active") and any(r["parameter"]==1001 and r.get("serieTo") is None for r in s["series"])),key=lambda s:s["stationId"])
    if not candidates:return core
    day=datetime.fromisoformat(stamp).date().toordinal()
    start=(day*extra)%len(candidates)
    return core+[candidates[(start+i)%len(candidates)] for i in range(min(extra,len(candidates)))]
def hydro_rows(d,selected):
    result=[]
    for s in nve_data(d):
        sid=s.get("stationId");p=s.get("parameter");unit=s.get("unit")
        if sid not in selected or p not in PARAMS or not isinstance(unit,str) or not unit:continue
        for o in s.get("observations") or []:
            if not number(o.get("value")):continue
            try:stamp=utc(o["time"])
            except (KeyError,ValueError,TypeError):continue
            result.append({"id":f"{sid}:{p}:{s.get('versionNo',0)}:1440","stationId":sid,"parameter":p,"name":PARAMS[p],"unit":unit,"version":s.get("versionNo"),"resolutionMinutes":1440,"time":stamp,"value":o["value"],"quality":o.get("quality"),"correction":o.get("correction")})
    return result
def fg_rows(d,dataset):
    rows=d.get("data") if isinstance(d,dict) else d
    if not isinstance(rows,list):raise ValueError("Fingrid schema")
    if isinstance(d,dict) and (d.get("pagination") or {}).get("lastPage",1)>1:raise ValueError("Fingrid response exceeds bounded page")
    result=[]
    for r in rows:
        if r.get("datasetId")!=dataset or not number(r.get("value")):continue
        try:a=utc(r["startTime"]);z=utc(r["endTime"])
        except (KeyError,ValueError,TypeError):continue
        if (datetime.fromisoformat(z)-datetime.fromisoformat(a)).total_seconds()!=180:continue
        result.append({"id":str(dataset),"datasetId":dataset,"name":FG_IDS[dataset],"unit":"MW","time":a,"endTime":z,"value":r["value"]})
    return result
def store(directory,provider,rows,stamp,archive_only=False):
    root=Path(directory)/"observations"/provider;root.mkdir(parents=True,exist_ok=True)
    groups={}
    for r in rows:groups.setdefault(r["time"][:7],[]).append(r)
    for month,items in groups.items():
        path=root/(month+".json")
        doc=read(path,{**base(provider),"month":month,"rows":[]})
        seen={r["revision"] for r in doc["rows"]}
        for r in items:
            rev=hashlib.sha256(json.dumps(r,sort_keys=True,allow_nan=False).encode()).hexdigest()
            if rev not in seen:doc["rows"].append({**r,"revision":rev,"firstRetrievedAt":stamp});seen.add(rev)
        if items:write_json(path,doc)
    if archive_only:
        print(provider,len(rows),"historical observations archived")
        return
    # Preserve latest observations and short chart history when one series fails.
    path=Path(directory)/(provider+"-v1.json");old=read(path,{**base(provider),"rows":[]})
    combined={(r["id"],r["time"]):r for r in old["rows"]}
    for r in rows:combined[(r["id"],r["time"]) ]={**r,"retrievedAt":stamp}
    by={}
    for r in combined.values():by.setdefault(r["id"],[]).append(r)
    recent=[r for group in by.values() for r in sorted(group,key=lambda x:x["time"])[-480:]]
    write_json(path,{**base(provider),"generated":stamp,"rows":recent})
    print(provider, len(rows),"observations received;",len(recent),"recent observations retained")
def refresh_hydapi(directory,key,get=request):
    root=Path(directory);stamp=now();registry=root/"hydapi-stations-v1.json"
    old=read(registry,{})
    if not old.get("generated") or datetime.fromisoformat(stamp)-datetime.fromisoformat(old["generated"])>timedelta(days=1):
        stations=normalize_stations(get(NVE+"Stations",key))
        write_json(registry,{**base("hydapi"),"generated":stamp,"rows":stations})
    else:stations=old["rows"]
    samples=expanded_samples(stations,stamp);rows=[]
    for start in range(0,len(samples),5):
        ids=[s["stationId"] for s in samples[start:start+5]]
        # Avoid cross-products of unsupported stations and parameters.
        # Use independent GET queries for available parameters, with a bounded
        # history window and throttling. Save successful rows on partial failure.
        for station in samples[start:start+5]:
            sid=station["stationId"]
            available={s["parameter"] for s in station["series"] if s.get("serieTo") is None}
            for parameter in sorted(available & PARAMS.keys()):
                url=NVE+"Observations?"+urlencode({"StationId":sid,"Parameter":parameter,"ResolutionTime":"1440","ReferenceTime":"P30D/"})
                try:rows.extend(hydro_rows(get(url,key),{sid}))
                except HTTPError as e:
                    if e.code in (401,403,429):
                        if rows:store(root,"hydapi",rows,stamp)
                        raise
                    print("HydAPI",sid,parameter,"HTTP",e.code)
                time.sleep(1)
    if not rows:raise ValueError("No HydAPI observations returned")
    store(root,"hydapi",rows,stamp)
def refresh_fingrid(directory,key,get=request):
    stamp=now();end=datetime.fromisoformat(stamp);start=end-timedelta(hours=24);rows=[]
    for dataset in FG_IDS:
        url=FG+str(dataset)+"/data?"+urlencode({"startTime":start.isoformat(),"endTime":end.isoformat(),"format":"json","pageSize":1000})
        try:rows.extend(fg_rows(get(url,key),dataset))
        except HTTPError as e:
            if e.code in (401,403,429):raise
            print("Fingrid dataset",dataset,"HTTP",e.code)
        time.sleep(2.1)
    if not rows:raise ValueError("No Fingrid observations returned")
    store(directory,"fingrid",rows,stamp)
def refresh(directory):
    if os.environ.get("NORDIC_OBSERVATIONS_DEDICATED")=="1":
        print("Nordic observations: dedicated collector owns these files");return
    for provider,names,fn in (("hydapi",("NVE_HYDAPI_KEY","HYDAPI_API_KEY","HYDAPI_KEY","NVE_HYDAPI_API_KEY"),refresh_hydapi),("fingrid",("FINGRID_API_KEY","FINGRID_KEY"),refresh_fingrid)):
        key=next((os.environ.get(n) for n in names if os.environ.get(n)),None)
        if not key:print(provider+": missing repository secret; retaining existing observations");continue
        try:fn(directory,key)
        except HTTPError as e:print(provider+": HTTP",e.code,"; retaining existing observations")
        except Exception as e:print(provider+":",type(e).__name__,"; retaining existing observations")
def public_files(directory):
    directory=Path(directory)
    for provider in LICENSES:
        for p in [directory/(provider+"-v1.json"),*sorted((directory/"observations"/provider).glob("*.json"))]+([directory/"hydapi-stations-v1.json"] if provider=="hydapi" else []):
            if not p.exists():continue
            d=read(p,{})
            if d.get("provider")!=provider or d.get("license")!=LICENSES[provider] or d.get("attribution")!=SOURCES[provider] or d.get("schema_version")!=1 or not isinstance(d.get("rows"),list):raise ValueError("Observation publication schema")
            if p.parent.name==provider and (not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",p.stem) or d.get("month")!=p.stem):raise ValueError("Observation archive path")
            yield p.relative_to(directory).as_posix()
if __name__=="__main__":refresh(Path(__file__).resolve().parents[1]/"data")
