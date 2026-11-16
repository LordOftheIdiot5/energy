"""Build NVE historical archive and weather/plant inputs without invented observations."""
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE = "https://api.nve.no/doc/magasinstatistikk/"
PLANTS = "https://api.nve.no/web/Powerplant/GetHydroPowerPlantsInOperation"
LICENSE = "https://data.norge.no/nlod/"

def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, allow_nan=False)+"\n", encoding="utf-8")
    tmp.replace(path)

def hydro_backfill(path, raw, generated):
    """Use already fetched NVE rows, by ISO week and bidding area."""
    path = Path(path)
    prior = json.loads(path.read_text(encoding="utf-8"))
    if prior.get("schema_version") != 1 or prior.get("source") != SOURCE:
        raise ValueError("Unexpected archive")
    groups = {}
    for r in raw:
        y,w,area = r.get("iso_aar"),r.get("iso_uke"),r.get("omrnr")
        f = r.get("fyllingsgrad")
        if r.get("omrType")!="EL" or area not in (1,2,3,4,5) or not isinstance(y,int) or not 1995<=y<=2100 or not isinstance(w,int) or not 1<=w<=53 or not num(f) or not 0<=f<=1:
            continue
        try:
            datetime.fromisocalendar(y,w,1)
        except ValueError:
            continue
        groups.setdefault((area,w),{})[y]=r
    records={}
    for (area,w),years in groups.items():
        earlier=[]
        for y,r in sorted(years.items()):
            f=r["fyllingsgrad"]; twh=r.get("fylling_TWh")
            records[(y,w,"NO"+str(area))]={"year":y,"week":w,"zone":"NO"+str(area),"fill_pct":round(f*100,2),"normal_pct":round(statistics.median(earlier)*100,2) if earlier else None,"stored_twh":twh if num(twh) and twh>=0 else None,"snapshot_generated":generated}
            earlier.append(f)
    if len(records)<100 or len({k[2] for k in records})!=5:
        return 0
    old = {(r["year"],r["week"],r["zone"]):r for r in prior["rows"]}
    # Preserve timestamp for unchanged observations; avoid hourly full-file churn.
    for key,row in records.items():
        prev=old.get(key)
        if prev and all(prev.get(k)==row.get(k) for k in ("fill_pct","normal_pct","stored_twh")):
            row["snapshot_generated"]=prev.get("snapshot_generated")
    for key,row in old.items():
        records.setdefault(key,row)
    ordered=[records[k] for k in sorted(records)]
    if ordered!=prior["rows"]:
        prior["rows"]=ordered
        prior["coverage"]="Historical NVE weekly records since 1995 as available; seasonal median uses earlier years only. Missing weeks are not interpolated. Historical observations may be revised by NVE."
        prior["backfilled_at"]=generated
        write_json(path,prior)
    return len(records)

def point_weather(steps):
    """Nonoverlapping forecast intervals. Point data, not catchment totals."""
    intervals=[]; start=None; end=None
    for step in steps:
        try:
            t=datetime.fromisoformat(step["time"].replace("Z","+00:00"))
            if t.tzinfo is None: continue
        except (KeyError,TypeError,ValueError):
            continue
        if start is None: start=t
        elapsed=(t-start).total_seconds()/3600
        if elapsed<0 or elapsed>=168 or (end is not None and t<end): continue
        details=step.get("data",{})
        for h in (1,6):
            p=details.get("next_"+str(h)+"_hours",{}).get("details",{}).get("precipitation_amount")
            if num(p) and p>=0 and elapsed+h<=168:
                temp=details.get("instant",{}).get("details",{}).get("air_temperature")
                end=t+timedelta(hours=h)
                intervals.append((h,p,temp if num(temp) else None))
                break
    if not intervals: return {}
    hours=sum(r[0] for r in intervals)
    complete=all(r[2] is not None for r in intervals)
    return {"forecastStart":start.isoformat(),"forecastEnd":end.isoformat(),"precipCoverageHours":hours,"precipMm":round(sum(r[1] for r in intervals),2),"coldPrecipMm":round(sum(r[1] for r in intervals if r[2] is not None and r[2]<=0),2) if complete else None,"positiveDegreeHours":round(sum(max(0,r[2])*r[0] for r in intervals),2) if complete else None,"method":"MET Norway point forecasts; nonoverlapping precipitation intervals; cold precipitation and positive degree-hours are proxies, not snow water equivalent or melt volume."}

def plant_records(raw):
    result={}
    for r in raw:
        ident,name,area=r.get("VannKraftverkID"),r.get("Navn"),str(r.get("ElspotomraadeNummer"))
        if not isinstance(ident,int) or not isinstance(name,str) or not name.strip() or r.get("ErIDrift") is False: continue
        cap,prod=r.get("MaksYtelse"),r.get("MidProd_91_20")
        result[ident]={"id":ident,"name":name,"zone":"NO"+area if area in ("1","2","3","4","5") else None,"municipality":r.get("Kommune"),"type":r.get("VannKVType"),"capacity_mw":cap if num(cap) else None,"annual_generation_gwh_1991_2020":prod if num(prod) else None,"owner":r.get("HovedEier"),"owner_orgnr":r.get("HovedEier_OrgNr"),"head_m":r.get("BruttoFallhoyde_M"),"energy_kwh_m3":r.get("EnEkv"),"catchment_id":r.get("RegineNr")}
    return [result[k] for k in sorted(result)]

def refresh_plants(path,get_json):
    path=Path(path)
    if path.exists():
        try:
            old=json.loads(path.read_text(encoding="utf-8"))
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(old["generated"])).total_seconds()
            if 0<=age<7*86400 and len(old["rows"])>=100 and old.get("schema_version")==1 and "owner" in old["rows"][0]: return
        except (ValueError,KeyError,TypeError):
            pass
    records=plant_records(get_json(PLANTS,timeout=40))
    if len(records)<100: raise ValueError("Incomplete NVE plant register")
    write_json(path,{"schema_version":1,"generated":datetime.now(timezone.utc).isoformat(),"source":PLANTS,"license":LICENSE,"attribution":"NVE; Nordl normalization","rows":records})

# NVE public map layer N5000; explicit geographic coordinates requested.
ZONE_LAYER = "https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/0/query"
def normalize_zone_geometry(raw):
    if raw.get("type")!="FeatureCollection" or raw.get("exceededTransferLimit"):
        raise ValueError("Incomplete zone response")
    features=[]
    seen=set()
    for item in raw.get("features",[]):
        raw_id=str(item.get("properties",{}).get("ElSpotOmr","")).strip().upper().replace(" ","")
        zone="NO"+raw_id if raw_id in ("1","2","3","4","5") else raw_id
        if zone not in ("NO1","NO2","NO3","NO4","NO5"): continue
        geo=item.get("geometry") or {}
        if geo.get("type") not in ("Polygon","MultiPolygon"): continue
        polys=geo["coordinates"] if geo["type"]=="MultiPolygon" else [geo["coordinates"]]
        rings=[]
        for poly in polys:
            for ring in poly:
                if len(ring)<4 or not all(isinstance(p,list) and len(p)>=2 and num(p[0]) and num(p[1]) and -1<=p[0]<=35 and 56<=p[1]<=72 for p in ring): raise ValueError("Invalid Norwegian geographic coordinates")
                rings.append([[round(p[0],5),round(p[1],5)] for p in ring])
        if not rings: continue
        features.append({"zone":zone,"rings":rings})
        seen.add(zone)
    if seen!={"NO1","NO2","NO3","NO4","NO5"}: raise ValueError("Missing Norwegian price areas")
    return features

def refresh_geometry(path,get_json):
    import urllib.parse
    path=Path(path)
    if path.exists():
        try:
            old=json.loads(path.read_text(encoding="utf-8"))
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(old["generated"])).total_seconds()
            if 0<=age<30*86400 and len({f["zone"] for f in old["features"]})==5: return
        except (ValueError,KeyError,TypeError): pass
    query=urllib.parse.urlencode({"where":"1=1","outFields":"ElSpotOmr","returnGeometry":"true","outSR":4326,"f":"geojson","maxAllowableOffset":"0.015"})
    raw=get_json(ZONE_LAYER+"?"+query,timeout=40)
    features=normalize_zone_geometry(raw)
    write_json(path,{"schema_version":1,"generated":datetime.now(timezone.utc).isoformat(),"source":ZONE_LAYER,"license":LICENSE,"attribution":"NVE; simplified boundaries for overview visualization","features":features})
