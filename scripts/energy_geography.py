"""NVE geography and project revisions; fail closed, preserve last known data."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from hydro_extended import num, write_json, LICENSE
BASE="https://gis3.nve.no/map/rest/services/Mapservices/VassdragsreguleringVannkraft/MapServer/"
SPECS={
 "stations":(1,"vannkraftverkNr,vannkraftStasjonNr,vannkraftStasjonNavn,maksYtelse_MW,bruttoFallhoyde_m,energiEkvivalent_kWh_m3,vannkraftverkEier,idriftsattAar"),
 "reservoirs":(9,"magasinNr,magasinNavn,vannkraftverkNr,delfeltNr,magasinArealHRV_km2,regulertOppdemt_Mm3,HRV_NN2000"),
 "catchments":(8,"delfeltNr,delfeltNavn,delfeltAreal_km2,vannkraftverkNr,magasinNr,nesteDelfeltNr,QNormalDelfelt9120_Mm3Aar"),
 "projects":(11,"vannkraftStasjonNr,vannkraftStasjonNavn,kdbNr,konsesjonStatus,konsesjonStatusDato,maksYtelse_MW,vannkraftverkEier,kommuneNavn"),
}
def get_all(kind,get_json):
    layer,fields=SPECS[kind]
    url=BASE+str(layer)+"/query?"
    count=get_json(url+urlencode({"where":"1=1","returnCountOnly":"true","f":"json"}),timeout=40).get("count")
    if not isinstance(count,int) or not 1<=count<=30000: raise ValueError("Invalid layer count")
    out=[]; seen=set()
    while len(out)<count:
        params={"where":"1=1","outFields":"OBJECTID,"+fields,"returnGeometry":"true","outSR":"4326","f":"geojson","orderByFields":"OBJECTID ASC","resultOffset":len(out),"resultRecordCount":500}
        if kind in ("reservoirs","catchments"): params["maxAllowableOffset"]="0.01"
        data=get_json(url+urlencode(params),timeout=50)
        if data.get("type")!="FeatureCollection": raise ValueError("Invalid feature collection")
        page=data.get("features",[])
        if not page: raise ValueError("Incomplete pagination")
        for item in page:
            ident=item.get("properties",{}).get("OBJECTID")
            if not isinstance(ident,int) or ident in seen: raise ValueError("Duplicate or missing OBJECTID")
            seen.add(ident);out.append(item)
        if len(out)>count: raise ValueError("Layer changed during fetch")
    return out

def point(p):
    return isinstance(p,list) and len(p)>=2 and num(p[0]) and num(p[1]) and 3<=p[0]<=32 and 56<=p[1]<=72

def normalize(kind,items):
    rows=[]
    for f in items:
        p=f["properties"];g=f.get("geometry") or {};t=g.get("type");coords=g.get("coordinates")
        if kind in ("stations","projects"):
            if t!="Point" or not point(coords): continue
            geom=[round(coords[0],5),round(coords[1],5)]
        else:
            polys=coords if t=="MultiPolygon" else [coords] if t=="Polygon" else []
            if not polys or not all(isinstance(poly,list) and poly and all(isinstance(r,list) and len(r)>=4 and all(point(v) for v in r) for r in poly) for poly in polys): continue
            geom=[[[[round(v[0],5),round(v[1],5)] for v in ring] for ring in poly] for poly in polys]
        row={"id":p["OBJECTID"],"geometry":geom}
        for name in SPECS[kind][1].split(","):
            v=p.get(name)
            if isinstance(v,str) or num(v): row[name]=v
        rows.append(row)
    # Invalid coordinates are not guessed. Refuse a mostly broken import.
    if len(rows)<len(items)*.95: raise ValueError("Too many invalid geometries")
    return rows

def fresh(path,days):
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        return 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(d["generated"])).total_seconds()<days*86400
    except (OSError,ValueError,KeyError,TypeError): return False

def refresh(kind,directory,get_json):
    path=Path(directory)/("nve-"+kind+"-v1.json")
    if fresh(path,1 if kind=="projects" else 30): return
    rows=normalize(kind,get_all(kind,get_json))
    stamp=datetime.now(timezone.utc).isoformat()
    data={"schema_version":1,"generated":stamp,"source":BASE+str(SPECS[kind][0]),"license":LICENSE,"attribution":"NVE; Nordl normalization and simplified polygon geometry","rows":rows}
    if kind=="projects":
        history=[]
        if path.exists():
            old=json.loads(path.read_text(encoding="utf-8"))
            history=old.get("changes",[])
            # Use station identifier, not mutable GIS object ID, and reject ambiguity.
            def keyed(rows):
                keys={}
                for r in rows:
                    k=r.get("vannkraftStasjonNr")
                    if not isinstance(k,int) or k<=0: continue
                    if k in keys: keys[k]=None
                    else: keys[k]=r
                return {k:v for k,v in keys.items() if v is not None}
            prev=keyed(old["rows"])
            for k,r in keyed(rows).items():
                if k in prev and r.get("konsesjonStatus")!=prev[k].get("konsesjonStatus"):
                    history.append({"station_id":k,"name":r.get("vannkraftStasjonNavn"),"before":prev[k].get("konsesjonStatus"),"after":r.get("konsesjonStatus"),"observed_at":stamp})
        data["changes"]=history[-1000:]
        data["method"]="Observed licensing-code changes only; absence does not prove cancellation or commissioning."
    write_json(path,data)

def collect_all(directory,get_json):
    for kind in SPECS:
        try: refresh(kind,directory,get_json)
        except Exception as e: print("  ! NVE geography",kind,type(e).__name__,str(e)[:160])
