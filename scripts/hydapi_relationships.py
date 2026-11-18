"""Exact source identifier joins, not inferred plant hydrology or ownership."""
import re,json
from pathlib import Path
from collections import defaultdict
from hydro_extended import write_json
def regine(value):
    # NVE REGINE identifiers, e.g. 016.BA11; retain leading zeroes.
    if not isinstance(value,str):return None
    value=value.strip().upper()
    return value if re.fullmatch(r"\d{3}\.[A-Z0-9]+",value) else None
def build(stations,plants,catchments):
    by_plants=defaultdict(list);by_catchments=defaultdict(list)
    for p in plants:
        k=regine(p.get("catchment_id"))
        if k and type(p.get("id")) is int:by_plants[k].append({"id":p["id"],"name":p.get("name"),"zone":p.get("zone")})
    for c in catchments:
        k=regine(c.get("delfeltNr"))
        if k:by_catchments[k].append(c["id"])
    rows=[]
    for s in stations:
        key=regine(s.get("regineNo"))
        ps=by_plants.get(key,[]);cs=by_catchments.get(key,[])
        if key and (ps or cs):
            rows.append({"stationId":s["stationId"],"regine":key,"catchmentRecordIds":cs,"plants":ps,"relationship":"same_reported_regine_identifier"})
    return rows
def generate(directory):
    directory=Path(directory)
    paths=[directory/n for n in ("hydapi-stations-v1.json","hydro-plants-v1.json","nve-catchments-v1.json")]
    if not all(p.exists() for p in paths):return None
    st,pl,ca=[json.loads(p.read_text(encoding="utf-8")) for p in paths]
    rows=build(st["rows"],pl["rows"],ca["rows"])
    out=directory/"hydapi-catchment-links-v1.json"
    write_json(out,{"schema_version":1,"attribution":"NVE; Nordl exact identifier join","license":"https://data.norge.no/nlod/","sources":[{"path":p.name,"generated":d.get("generated")} for p,d in zip(paths,(st,pl,ca))],"notice":"Exact shared source REGINE reference only; no proof of upstream/downstream connectivity, reservoir identity or plant-specific inflow.","rows":rows})
    print("HydAPI exact catchment links:",len(rows),"stations;",sum(bool(r["plants"]) for r in rows),"with matching plant register references")
    return out
