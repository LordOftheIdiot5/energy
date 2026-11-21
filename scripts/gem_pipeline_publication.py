"""Strict publication gate for the November 2025 GEM pipeline snapshot.

Allows only the two exact reviewed Git blobs from the source staging workflow.
A file passing metadata checks but with modified coordinates is never published.
The geometry is a simplified/approximate reference, not engineering GIS.
"""
import collections
import hashlib
import json
import math
from pathlib import Path

PROJECT_FILE="gem-gas-pipelines-202511-v1.json"
ROUTE_FILE="gem-gas-pipeline-routes-202511-v1.geojson"
PROJECT_BLOB="b2b3552e08129021fc2c2fb6114e7a12ae2e3259"
ROUTE_BLOB="51413741f7d822cf87ea746d9d4f42423ece58d9"
SOURCE_TABLE_SHA="33cf8df6a6ba9bfaad0fd6c046b8b0be6d746bba014c7e31cd6b4618ed1605f1"
SOURCE_ROUTE_SHA="d2d940433656e58ba32a852aba6f30300846ab52375b0139f02df88d691f4378"
ATTR="Data: Global Gas Infrastructure Tracker, Global Energy Monitor, November 2025"
CC="https://creativecommons.org/licenses/by/4.0/"
COUNTS={"operating":2975,"construction":282,"proposed":611,"idle":8,"cancelled":243,"shelved":103,"mothballed":9,"retired":14,"Status not reported":1}
MAX_FILE=15_000_000

def git_blob_hash(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def check_coords(geom):
    if not isinstance(geom,dict) or geom.get("type")!="MultiLineString":
        raise ValueError("Unsupported pipeline geometry")
    all_lines=geom.get("coordinates")
    if not isinstance(all_lines,list) or not all_lines:
        raise ValueError("Missing pipeline line geometry")
    for line in all_lines:
        if not isinstance(line,list) or len(line)<2:
            raise ValueError("Degenerate pipeline route")
        for q in line:
            if not isinstance(q,list) or len(q)<2 or any(type(c) not in (int,float) or not math.isfinite(c) for c in q[:2]):
                raise ValueError("Invalid geographic coordinate")
            if not -180<=q[0]<=180 or not -90<=q[1]<=90:
                raise ValueError("Out-of-range geographic coordinate")

def check(tab,lines):
    shared=("release","license","license_url","attribution","publisher","distribution","table_sha256","routes_sha256")
    expected=dict(release="2025-11",license="CC BY 4.0",license_url=CC,
                  attribution=ATTR,publisher="Global Energy Monitor",distribution="LNG Atlas",
                  table_sha256=SOURCE_TABLE_SHA,routes_sha256=SOURCE_ROUTE_SHA)
    for data in (tab,lines):
        if data.get("schema_version")!=1 or any(data.get(key)!=value for key,value in expected.items()):
            raise ValueError("Unapproved GEM source release, attribution or checksum")
        if "simplified" not in str(data.get("caveat","")).lower():
            raise ValueError("GEM geometric caveat is required")
    items=tab.get("rows")
    features=lines.get("features")
    if tab.get("dataset")!="GEM global gas transmission pipelines" or tab.get("source_rows")!=4246 or tab.get("mapped_routes")!=3921 or not isinstance(items,list) or len(items)!=4246:
        raise ValueError("GEM project directory coverage mismatch")
    if lines.get("type")!="FeatureCollection" or not isinstance(features,list) or len(features)!=3921:
        raise ValueError("GEM mapped pipeline route count mismatch")
    slugs=set()
    status_counts=collections.Counter()
    for r in items:
        slug=r.get("id")
        if not isinstance(slug,str) or not slug or len(slug)>250 or slug in slugs or not isinstance(r.get("name"),str) or not r["name"].strip():
            raise ValueError("Unsafe source pipeline identity")
        if r.get("data_source")!=ATTR or r.get("status") not in COUNTS:
            raise ValueError("Unapproved pipeline status or missing individual attribution")
        if "operating_now" in r or "surveyed_route" in r:
            raise ValueError("Unsafe current-operation or surveyed-line assertion")
        for value in ("length_km","capacity_bcm_y"):
            v=r.get(value)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0):
                raise ValueError("Unsafe pipeline length/capacity")
        slugs.add(slug);status_counts[r["status"]]+=1
    if dict(status_counts)!=COUNTS or tab.get("statuses")!=COUNTS:
        raise ValueError("GEM status inventory drift")
    route_ids=set()
    for item in features:
        if item.get("type")!="Feature":
            raise ValueError("Non-feature route entry")
        props=item.get("properties") or {}
        identity=props.get("pipeline_id")
        if identity not in slugs or identity in route_ids:
            raise ValueError("Unmatched or duplicate GEM pipeline route")
        check_coords(item.get("geometry"))
        route_ids.add(identity)
    if len(slugs-route_ids)!=325:
        raise ValueError("GEM routes without mapped geometries changed")
    return {"projects":len(slugs),"routes":len(route_ids),"unmapped":len(slugs-route_ids),
            "statuses":dict(status_counts)}

def validate_files(path):
    folder=Path(path)
    blobs=[]
    parsed=[]
    for name,expected in ((PROJECT_FILE,PROJECT_BLOB),(ROUTE_FILE,ROUTE_BLOB)):
        file=folder/name
        if not file.is_file() or file.is_symlink() or not 100<=file.stat().st_size<=MAX_FILE:
            raise ValueError("Missing or unsafe GEM public file")
        raw=file.read_bytes()
        if git_blob_hash(raw)!=expected:
            raise ValueError("GEM reviewed data blob checksum mismatch")
        parsed.append(json.loads(raw))
        blobs.append(expected)
    return check(*parsed)
