"""Inspect official NACEI oil-and-gas point infrastructure data before publication.

North American Cooperation on Energy Information (NACEI) REST service.
Permits use with attribution. Dataset service copyright indicates August 2017;
do not infer a site is active, currently owned, or has reported live throughput.
No private PHMSA NPMS GIS layers are collected.
"""
import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE="https://geoappext.nrcan.gc.ca/arcgis/rest/services/NACEI/energy_infrastructure_of_north_america_en/MapServer"
LICENSE="free and unrestricted with acknowledgement (NACEI)"
ATTRIBUTION="North American Cooperation on Energy Information (NACEI), August 2017"
SOURCE_PAGE=BASE
LAYERS={
  "gas_processing":(4,{"OBJECTID","Country","Facility","Capa_MMcfd","Period"}),
  "lng_terminals":(5,{"OBJECTID","Country","Facility","ImpExp","Regas_Bcfd","Liq_Bcfd","Period"}),
  "refineries":(10,{"OBJECTID","Country","Facility","Type","AD_Mbpd","Period"}),
}
MAX_BYTES=15_000_000

def fetch(url,params):
    if not (url==BASE or url.startswith(BASE+"/")):
        raise ValueError("Unapproved NACEI endpoint")
    uri=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(uri,headers={"User-Agent":"Nordl-Energy-Research/1.0 (+https://energy.nordl.dev)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as response:
        if urllib.parse.urlsplit(response.url).hostname!="geoappext.nrcan.gc.ca":
            raise ValueError("Unexpected NACEI redirect")
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError("Oversized NACEI response")
    doc=json.loads(raw)
    if "error" in doc:raise ValueError("NACEI service error "+str(doc["error"].get("code")))
    return doc

def finite(v):
    return type(v) in (int,float) and math.isfinite(v)

def normalize(layer, data):
    kind=next((k for k,(id,_) in LAYERS.items() if id==layer),None)
    if kind is None:raise ValueError("Unknown NACEI layer")
    features=data.get("features")
    if not isinstance(features,list):raise ValueError("NACEI feature list missing")
    output=[]
    rejected=Counter()
    seen=set()
    for item in features:
        attrs=item.get("attributes") or {}
        loc=item.get("geometry") or {}
        oid=attrs.get("OBJECTID")
        name=(attrs.get("Facility") or "").strip()
        country=(attrs.get("Country") or "").strip()
        lng,lat=loc.get("x"),loc.get("y")
        if not isinstance(oid,int) or oid<1 or oid in seen:
            rejected["invalid_or_duplicate_id"]+=1;continue
        seen.add(oid)
        if not name or not country:rejected["missing_name_country"]+=1;continue
        if not finite(lng) or not finite(lat) or not (-170<=lng<=-50 and 14<=lat<=74):
            rejected["invalid_geography"]+=1;continue
        if country.lower() not in {"canada","united states","usa","united states of america","mexico"}:
            rejected["unexpected_country"]+=1;continue
        capacity={
          "gas_processing":("Capa_MMcfd","MMcf/d"),
          "lng_terminals":("Liq_Bcfd","Bcf/d"),
          "refineries":("AD_Mbpd","thousand barrels/d"),
        }[kind]
        raw_cap=attrs.get(capacity[0])
        cap=raw_cap if finite(raw_cap) and raw_cap>=0 else None
        output.append({
            "id":f"nacei-{layer}-{oid}","source_layer":layer,"source_objectid":oid,
            "facility":name,"country":country,
            "owner":attrs.get("Owner"),"operator":attrs.get("Operator"),
            "kind":kind,"type":attrs.get("Type") if kind=="refineries" else attrs.get("ImpExp") if kind=="lng_terminals" else "Processing facility",
            "reference_period":attrs.get("Period"),
            "reported_capacity":cap,"capacity_unit":capacity[1],
            "geometry":[round(lng,6),round(lat,6)],
            "status":"Status not reported in historic source",
        })
    output.sort(key=lambda r:r["source_objectid"])
    return output,dict(rejected)

def inspect(fetcher=fetch):
    root=fetcher(BASE,{"f":"json"})
    if "NACEI" not in root.get("serviceDescription","") and "NACEI" not in root.get("copyrightText",""):
        raise ValueError("NACEI service provenance mismatch")
    if "unrestricted" not in root.get("serviceDescription","").lower():
        raise ValueError("NACEI use statement missing")
    collection={}
    summaries={}
    for kind,(id,req) in LAYERS.items():
        meta=fetcher(BASE+f"/{id}",{"f":"json"})
        fields={x.get("name") for x in meta.get("fields",[])}
        if not req.issubset(fields):raise ValueError("NACEI layer field schema changed")
        if meta.get("geometryType")!="esriGeometryPoint":
            raise ValueError("NACEI layer geometry changed")
        if "2017" not in meta.get("copyrightText",""):
            raise ValueError("NACEI historical period missing")
        ids=fetcher(BASE+f"/{id}/query",{"f":"json","where":"1=1","returnIdsOnly":"true"}).get("objectIds")
        if not isinstance(ids,list) or not ids or len(set(ids))!=len(ids):
            raise ValueError("Missing or duplicate official NACEI feature IDs")
        data=[]
        for start in range(0,len(ids),200):
            batch=ids[start:start+200]
            response=fetcher(BASE+f"/{id}/query",{
                "f":"json","objectIds":",".join(map(str,batch)),
                "outFields":"*","returnGeometry":"true","outSR":"4326"})
            data.extend(response.get("features",[]))
        if len(data)!=len(ids):raise ValueError("Partial NACEI official query")
        rows,exclusions=normalize(id,{"features":data})
        if len(rows)<max(3,int(.7*len(ids))):raise ValueError("Unsafe NACEI record loss")
        collection[kind]=rows
        summaries[kind]={"source_rows":len(ids),"mapped_rows":len(rows),"excluded":exclusions,
            "layer_id":id,"copyright":meta["copyrightText"],"field_names":sorted(fields)}
    return {"schema_version":1,"source":SOURCE_PAGE,"rights":LICENSE,
            "attribution":ATTRIBUTION,"source_period":"2017-08",
            "audit_date":datetime.now(timezone.utc).date().isoformat(),
            "caveat":"Historic August 2017 NACEI facility reference. Presence and capacity do not imply current operation, ownership or throughput.",
            "layers":summaries,"rows":collection}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    d=inspect()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("NACEI historic official reference:",{k:(v["source_rows"],v["mapped_rows"],v["excluded"]) for k,v in d["layers"].items()})
if __name__=="__main__":main()
