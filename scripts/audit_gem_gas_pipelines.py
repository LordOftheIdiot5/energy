"""Read-only GEM / LNG Atlas global gas-pipeline release and geometry audit.

These publicly downloadable November 2025 JSON files explicitly state
underlying Global Energy Monitor CC BY 4.0 attribution. Never describe the
simplified/estimated routes as surveyed linework. Never merge non-operating
statuses into currently operating pipeline length.
"""
import argparse
import collections
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

TABLE="https://lngatlas.org/data/pipelines.json"
ROUTES="https://www.lngatlas.org/api/map/pipelines.json"
GEM="https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker"
ATTR="Data: Global Gas Infrastructure Tracker, Global Energy Monitor, November 2025"
CC="https://creativecommons.org/licenses/by/4.0/"
MAX_BYTES=35_000_000
EXPECTED=4246

def get_json(url):
    if url not in (TABLE,ROUTES):
        raise ValueError("Unapproved external pipeline endpoint")
    req=urllib.request.Request(url,headers={"User-Agent":"Nordl-Energy-Research/1.0 (+https://energy.nordl.dev)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=75) as response:
        if urllib.parse.urlsplit(response.url).hostname not in ("lngatlas.org","www.lngatlas.org"):
            raise ValueError("Unapproved pipeline data redirect")
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise ValueError("Source exceeds pipeline research size guard")
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def audit(table,geo):
    if table.get("dataset")!="Gas pipelines" or table.get("release")!="November 2025" or table.get("attribution")!=ATTR or table.get("licence")!="CC BY 4.0" or table.get("licence_url")!=CC or table.get("count")!=EXPECTED:
        raise ValueError("Unapproved GEM pipeline source release/rights")
    items=table.get("rows")
    if not isinstance(items,list) or len(items)!=EXPECTED:
        raise ValueError("GEM pipeline table coverage regression")
    statuses=collections.Counter()
    ids=set()
    for r in items:
        slug=r.get("slug")
        if not isinstance(slug,str) or not slug or slug in ids or not r.get("name"):
            issue="duplicate-slug" if isinstance(slug,str) and slug in ids else "missing-slug/name/status"
            raise ValueError("GEM pipeline row identity missing or duplicate: "+issue+
                " row="+str(len(ids))+" slug="+repr(str(slug)[:100])+
                " name_present="+str(bool(r.get("name")))+" status="+repr(r.get("status"))+
                " keys="+repr(sorted(r.keys())))
        if r.get("data_source")!=ATTR:
            raise ValueError("GEM attribution not retained per row")
        if r.get("length_km") is not None and (not isinstance(r["length_km"],(int,float)) or r["length_km"]<0):
            raise ValueError("Unsafe GEM pipeline length")
        statuses[r["status"] if r.get("status") is not None else "Status not reported"]+=1;ids.add(slug)
    if geo.get("type")!="FeatureCollection" or not isinstance(geo.get("features"),list):
        raise ValueError("GEM pipeline geometry source changed")
    types=collections.Counter()
    geom_ids=set()
    omitted=0
    for f in geo["features"]:
        p=f.get("properties") or {}
        slug=p.get("slug")
        if slug is None:slug=p.get("id")
        if slug not in ids:omitted+=1;continue
        geom=f.get("geometry") or {}
        kind=geom.get("type")
        if kind not in ("LineString","MultiLineString"):raise ValueError("Invalid pipeline line geometry")
        if not geom.get("coordinates"):raise ValueError("Empty pipeline line geometry")
        types[kind]+=1;geom_ids.add(slug)
    if not geom_ids:
        raise ValueError("No matched mapped GEM pipelines")
    if len(geom_ids)<int(EXPECTED*.65):
        raise ValueError("Unsafe loss of mapped GEM gas routes")
    if len(geo["features"])>EXPECTED*3:
        raise ValueError("Unexpected oversized geometry release")
    return {
        "schema_version":1,"dataset":"Global gas transmission pipelines",
        "publisher":"Global Energy Monitor","distribution":"LNG Atlas",
        "source":GEM,"table_url":TABLE,"map_url":ROUTES,
        "release":"November 2025","license":"CC BY 4.0","license_url":CC,
        "attribution":ATTR,
        "warning":"Routes are simplified map geometries (about 2 km) and may be approximations. Not survey-accurate, verified current, distribution/gathering or complete transmission coverage.",
        "table_rows":len(items),"statuses":dict(statuses),"missing_reported_status":statuses.get("Status not reported",0),
        "map_features":len(geo["features"]),"matched_routes":len(geom_ids),
        "unmatched_features":omitted,"geometry_types":dict(types),
        "route_coverage_pct":round(100*len(geom_ids)/EXPECTED,2)
    }

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    table,table_sha=get_json(TABLE);geo,geo_sha=get_json(ROUTES)
    result=audit(table,geo)
    result["table_sha256"]=table_sha
    result["routes_sha256"]=geo_sha
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("GEM CC BY global gas pipeline audit:",result)
if __name__=="__main__":main()
