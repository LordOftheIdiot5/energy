"""Immutable WRI 2021 European plant reference and NVE owner aggregation."""
import csv,io,json,math,zipfile,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from hydro_extended import write_json
WRI="https://datasets.wri.org/datasets/global-power-plant-database"
ZIP="https://datasets.wri.org/private-admin/dataset/53623dfd-3df6-4f15-a091-67457cdb571f/resource/66bcdacc-3d0e-46ad-9271-a5a76b1853d2/download/globalpowerplantdatabasev130.zip"
COUNTRIES=set("ALB AUT BEL BGR BIH CHE CYP CZE DEU DNK ESP EST FIN FRA GBR GRC HRV HUN IRL ISL ITA LTU LUX LVA MDA MKD MNE NLD NOR POL PRT ROU SRB SVK SVN SWE TUR UKR".split())
def number(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):return None
def normalize(reader):
    rows={}
    for r in reader:
        if r.get("country") not in COUNTRIES:continue
        lon,lat,mw=map(number,[r.get("longitude"),r.get("latitude"),r.get("capacity_mw")])
        ident=r.get("gppd_idnr")
        if not ident or not r.get("name") or lon is None or lat is None or not (-16<=lon<=42 and 34<=lat<=72):continue
        if ident in rows:raise ValueError("Duplicate source ID")
        rows[ident]={"id":ident,"name":r["name"],"country":r["country"],"fuel":r.get("primary_fuel"),"geometry":[lon,lat],"capacity_mw":mw if mw is not None and mw>=0 else None,"owner":r.get("owner"),"commissioning_year":number(r.get("commissioning_year"))}
    return list(rows.values())
def europe(directory):
    p=Path(directory)/"europe-plants-v1.json"
    if p.exists():return
    req=urllib.request.Request(ZIP,headers={"User-Agent":"Nordl Energy (https://energy.nordl.dev/)"})
    with urllib.request.urlopen(req,timeout=90) as response:data=response.read(60000001)
    if len(data)>60000000:raise ValueError("Archive too large")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members=[m for m in z.infolist() if m.filename.lower().endswith("global_power_plant_database.csv")]
        if len(members)!=1 or members[0].file_size>100000000:raise ValueError("Unexpected archive")
        with z.open(members[0]) as s:
            reader=csv.DictReader(io.TextIOWrapper(s,encoding="utf-8-sig"))
            if not {"gppd_idnr","name","country","longitude","latitude","capacity_mw","primary_fuel"}.issubset(reader.fieldnames or []):raise ValueError("Unexpected schema")
            rows=normalize(reader)
    if len(rows)<1000 or len({r["country"] for r in rows})<20:raise ValueError("Incomplete coverage")
    write_json(p,{"schema_version":1,"generated":datetime.now(timezone.utc).isoformat(),"release_year":2021,"source":WRI,"license":"https://creativecommons.org/licenses/by/4.0/","attribution":"Global Energy Observatory, Google, KTH Royal Institute of Technology in Stockholm, Enipedia, World Resources Institute (2021), Global Power Plant Database v1.3.0; Nordl regional subset","notice":"Historical archive, not current operation or ownership. Geographic subset excludes remote territories.","rows":rows})
def aggregate(registry):
    out={};seen=set()
    for r in registry["rows"]:
        key=str(r.get("owner_orgnr") or "")
        if len(key)!=9 or not key.isascii() or not key.isdigit() or not r.get("owner"):continue
        if r["id"] in seen:raise ValueError("Duplicate registry ID")
        seen.add(r["id"])
        x=out.setdefault(key,{"orgnr":key,"name":r["owner"],"plant_ids":[],"zones":[],"reported_capacity_mw":0,"capacity_records":0})
        x["plant_ids"].append(r["id"])
        if r.get("zone") and r["zone"] not in x["zones"]:x["zones"].append(r["zone"])
        v=r.get("capacity_mw")
        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0:
            x["reported_capacity_mw"]+=v;x["capacity_records"]+=1
    for x in out.values():
        x["reported_capacity_mw"]=round(x["reported_capacity_mw"],3) if x["capacity_records"] else None
        x["plant_ids"].sort();x["zones"].sort()
    return {"schema_version":1,"generated":registry["generated"],"source":"hydro-plants-v1.json","license":"https://data.norge.no/nlod/","notice":"NVE reported main owner by organisation number; capacity is plant nameplate, not equity-adjusted exposure or listed-parent ownership.","rows":[out[k] for k in sorted(out)]}
def owners(directory):
    directory=Path(directory);p=directory/"hydro-owners-v1.json"
    d=aggregate(json.loads((directory/"hydro-plants-v1.json").read_text(encoding="utf-8")))
    if not p.exists() or json.loads(p.read_text(encoding="utf-8"))!=d:write_json(p,d)
