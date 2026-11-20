"""Create privately staged, immutable GEM Nov 2025 transmission pipeline projection.

Upstream JSON distribution explicitly carries GEM CC BY 4.0 attribution.
Never derive a route when none exists. Geometry is simplified by source and
may be approximated; not suitable for engineering/land parcel use.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from audit_gem_gas_pipelines import TABLE,ROUTES,ATTR,CC,EXPECTED,get_json,audit

TABLE_SHA="33cf8df6a6ba9bfaad0fd6c046b8b0be6d746bba014c7e31cd6b4618ed1605f1"
ROUTES_SHA="d2d940433656e58ba32a852aba6f30300846ab52375b0139f02df88d691f4378"
LICENSE="CC BY 4.0"
RELEASE="2025-11"

def coords_valid(points):
    if not isinstance(points,list) or not points:
        return False
    for line in points:
        if not isinstance(line,list) or len(line)<2:
            return False
        for xy in line:
            if not isinstance(xy,list) or len(xy)<2 or not all(type(v) in (int,float) and math.isfinite(v) for v in xy[:2]):
                return False
            if not (-180<=xy[0]<=180 and -90<=xy[1]<=90):
                return False
    return True

def project(table,geo,table_sha,route_sha):
    if table_sha!=TABLE_SHA or route_sha!=ROUTES_SHA:
        raise ValueError("Unapproved GEM source change; review release before accepting")
    summary=audit(table,geo)
    if summary["table_rows"]!=4246 or summary["matched_routes"]!=3921 or summary["missing_reported_status"]!=1:
        raise ValueError("Unexpected GEM pipeline identities or geometry coverage")
    records=[]
    for item in table["rows"]:
        record={
            "id":item["slug"],
            "name":item["name"],
            "status":item.get("status") or "Status not reported",
            "countries":item.get("countries"),
            "start_country":item.get("start_country"),
            "end_country":item.get("end_country"),
            "start_place":item.get("start_place"),
            "end_place":item.get("end_place"),
            "fuel":item.get("fuel"),
            "onshore_offshore":item.get("onshore_offshore"),
            "length_km":item.get("length_km"),
            "length_basis":item.get("length_basis"),
            "capacity_bcm_y":item.get("capacity_bcm_y"),
            "has_route":bool(item.get("has_route")),
            "source_url":item.get("url"),
            "data_source":item["data_source"],
        }
        records.append(record)
    indexed={r["id"] for r in records}
    lines=[]
    for feature in geo["features"]:
        props=feature.get("properties") or {}
        slug=props.get("slug") or props.get("id")
        if slug not in indexed:
            raise ValueError("Unexpected GEM pipeline map identity")
        geom=feature.get("geometry") or {}
        kind=geom.get("type")
        raw=geom.get("coordinates")
        if kind!="MultiLineString" or not coords_valid(raw):
            raise ValueError("Invalid simplified GEM pipeline route geometry")
        lines.append({"type":"Feature","properties":{"pipeline_id":slug},
                      "geometry":{"type":kind,"coordinates":raw}})
    if len(lines)!=3921 or len({x["properties"]["pipeline_id"] for x in lines})!=3921:
        raise ValueError("Incomplete or duplicate GEM mapped routes")
    common={"release":RELEASE,"license":LICENSE,
        "license_url":CC,"attribution":ATTR,
        "publisher":"Global Energy Monitor","distribution":"LNG Atlas",
        "table_sha256":TABLE_SHA,"routes_sha256":ROUTES_SHA,
        "caveat":"Simplified, sometimes approximated 2025 route geometry; not surveyed. Status is tracker-reported, not 2026 live operation.",
        "changes":"Selected/renamed tracker attributes; retained original status and attribution. Routes kept in source simplified form.",
    }
    return (
        {"schema_version":1,"dataset":"GEM global gas transmission pipelines",**common,
         "source_rows":4246,"mapped_routes":3921,"statuses":summary["statuses"],"rows":records},
        {"type":"FeatureCollection","schema_version":1,**common,"features":lines}
    )

def write(tab,geo,folder):
    output=Path(folder);output.mkdir(parents=True,exist_ok=True)
    tables=output/"gem-gas-pipelines-202511-v1.json"
    lines=output/"gem-gas-pipeline-routes-202511-v1.geojson"
    tables.write_text(json.dumps(tab,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    lines.write_text(json.dumps(geo,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("Staged GEM 2025:",len(tab["rows"]),"projects,",len(geo["features"]),"mapped routes; bytes:",tables.stat().st_size,lines.stat().st_size)

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    raw,tsha=get_json(TABLE);geo,gsha=get_json(ROUTES)
    tab,lines=project(raw,geo,tsha,gsha)
    write(tab,lines,a.out)
if __name__=="__main__":main()
