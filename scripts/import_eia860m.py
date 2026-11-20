"""Normalize official September 2026 EIA-860M generator inventories.

Project units are NOT generating output. Retired, standby, construction and
postponed units are distinct. Never geocode missing coordinates or infer
current operations from an inventory category alone.

Source fingerprint and immutable release pinned before production promotion.
"""
import argparse
import hashlib
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from audit_eia860m import MAX_BYTES, S, shared_strings, sheet_titles, SOURCE, SOURCE_PAGE, LICENSE

EXPECTED_SHA = "bcef74e1af991680731aeecfda967f5950db4ce739bb584edd8b8774c7e6da17"
RELEASE = "2026-09"
PUBLISHED = "2026-10-23"
CATEGORIES = {
    "Operating": ("operating", False),
    "Planned": ("planned", False),
    "Retired": ("retired", False),
    "Canceled or Postponed": ("canceled_postponed", False),
    "Operating_PR": ("operating", True),
    "Planned_PR": ("planned", True),
    "Retired_PR": ("retired", True),
}
REQUIRED = ("Plant ID","Plant Name","Generator ID","Plant State","Technology",
            "Energy Source Code","Nameplate Capacity (MW)","Latitude","Longitude")
MONTHLY = {
    "operating": ("Operating Month", "Operating Year"),
    "planned": ("Planned Operation Month", "Planned Operation Year"),
    "retired": ("Retirement Month", "Retirement Year"),
}

def col_number(col):
    n=0
    for char in col:
        if not "A"<=char<="Z":
            raise ValueError("Invalid Excel column")
        n=n*26+ord(char)-64
    return n-1

def cells(row, strings):
    values={}
    for cell in row.findall(S+"c"):
        match=re.fullmatch(r"([A-Z]+)\d+",cell.attrib.get("r",""))
        if not match:
            continue
        index=col_number(match.group(1))
        v=cell.find(S+"v")
        inline=cell.find(S+"is")
        if cell.attrib.get("t")=="s" and v is not None and v.text:
            idx=int(v.text)
            if not 0<=idx<len(strings):
                raise ValueError("Invalid EIA shared string index")
            value=strings[idx]
        elif inline is not None:
            value="".join(x.text or "" for x in inline.iter(S+"t"))
        else:
            value=v.text if v is not None else None
        if value is not None:
            values[index]=str(value).strip()
    return values

def rows(z, path, strings):
    header=None
    with z.open(path) as stream:
        for event,elem in ET.iterparse(stream,events=("end",)):
            if elem.tag!=S+"row":
                continue
            values=cells(elem,strings)
            row_number=int(elem.attrib.get("r","0"))
            elem.clear()
            if row_number==3:
                header={str(v).strip():i for i,v in values.items() if str(v).strip()}
                if not set(REQUIRED).issubset(header):
                    raise ValueError(f"Unexpected EIA-860M headers in {path}: {set(REQUIRED)-set(header)}")
                continue
            if row_number<=3:
                continue
            if header is None:
                raise ValueError("Missing EIA worksheet headings")
            if not values:
                continue
            yield {name:values.get(i) for name,i in header.items()}

def txt(v):
    s=str(v or "").strip()
    return s if s and s.lower() not in ("nan","n/a","not available","none",".") else None

def float_or_none(v):
    try:
        f=float(str(v).replace(",",""))
        return f if math.isfinite(f) else None
    except (ValueError,TypeError):
        return None

def valid_coordinate(lat,lon,territory):
    # Broad bounds include Alaska/Aleutians, Hawaii, continental US, and PR;
    # a coordinate must be explicitly reported by EIA, never inferred.
    if lat is None or lon is None or lat==0 or lon==0:
        return False
    if not -180<=lon<=180 or not -90<=lat<=90:
        return False
    if territory:
        return 16<=lat<=19.5 and -69<=lon<=-64.5
    return (16<=lat<=72 and -180<=lon<=-64) or (48<=lat<=55 and 169<=lon<=180)

def date_for(row, kind):
    keys=MONTHLY.get(kind)
    if not keys:
        return None
    m=txt(row.get(keys[0]));y=txt(row.get(keys[1]))
    try:
        mi=int(float(m)); yr=int(float(y))
        if 1<=mi<=12 and 1900<=yr<=2050:
            return f"{yr:04d}-{mi:02d}"
    except (ValueError,TypeError):
        pass
    return None

def normalize(raw, min_records=30000, expected_sha=EXPECTED_SHA):
    digest=hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and digest!=expected_sha:
        raise ValueError("Official EIA-860M source checksum differs from approved release")
    if not (100<=len(raw)<=MAX_BYTES):
        raise ValueError("EIA workbook source size invalid")
    from io import BytesIO
    counts=Counter()
    by_class=Counter()
    seen=set()
    output=[]
    with zipfile.ZipFile(BytesIO(raw)) as z:
        for item in z.infolist():
            if item.filename.startswith("/") or ".." in Path(item.filename).parts or item.file_size>MAX_BYTES*10:
                raise ValueError("Unsafe workbook ZIP payload")
        sheets=sheet_titles(z)
        if set(x[0] for x in sheets)!=set(CATEGORIES):
            raise ValueError("Unexpected EIA-860M workbook tabs")
        strings=shared_strings(z)
        for title,path in sheets:
            kind,territory=CATEGORIES[title]
            for row in rows(z,path,strings):
                counts["source_rows"]+=1
                by_class[title+"_source"]+=1
                raw_plant=txt(row.get("Plant ID"))
                plant=raw_plant
                gen=txt(row.get("Generator ID"))
                if not plant or not re.fullmatch(r"\d{1,8}(?:\.0)?",plant) or not gen or len(gen)>40:
                    counts["invalid_identity"]+=1
                    continue
                plant=str(int(float(plant)))
                identity=f"{title}:{plant}:{gen}"
                if identity in seen:
                    raise ValueError("Duplicate generator identity in same EIA inventory")
                seen.add(identity)
                lat=float_or_none(row.get("Latitude"))
                lon=float_or_none(row.get("Longitude"))
                if not valid_coordinate(lat,lon,territory):
                    counts["missing_or_invalid_coordinates"]+=1
                    continue
                cap=float_or_none(row.get("Nameplate Capacity (MW)"))
                if cap is not None and (cap<0 or cap>30000):
                    counts["invalid_capacity"]+=1
                    continue
                plant_name=txt(row.get("Plant Name"))
                tech=txt(row.get("Technology"))
                if not plant_name or not tech:
                    counts["missing_plant_or_technology"]+=1
                    continue
                status=txt(row.get("Status")) if kind in ("operating","planned") else None
                if kind in ("operating","planned") and status is None:
                    counts["missing_reported_status"]+=1
                    continue
                state=txt(row.get("Plant State"))
                if territory and state!="PR":
                    raise ValueError("Puerto Rico sheet has an unexpected state")
                if not territory and state=="PR":
                    raise ValueError("US inventory includes PR without PR sheet")
                record={
                    "id":f"eia860m-{title.lower().replace(' ','_')}:{plant}:{gen}",
                    "inventory":kind,
                    "source_tab":title,
                    "plant_id":plant,
                    "generator_id":gen,
                    "plant":plant_name,
                    "entity":txt(row.get("Entity Name")),
                    "state":state,
                    "county":txt(row.get("County")),
                    "territory":"Puerto Rico" if territory else "United States",
                    "balancing_authority":txt(row.get("Balancing Authority Code")),
                    "technology":tech,
                    "fuel":txt(row.get("Energy Source Code")),
                    "prime_mover":txt(row.get("Prime Mover Code")),
                    "status":status if status else ("Retired (EIA inventory)" if kind=="retired" else "Canceled / indefinitely postponed (EIA inventory)"),
                    "nameplate_mw":round(cap,4) if cap is not None else None,
                    "net_summer_mw":float_or_none(row.get("Net Summer Capacity (MW)")),
                    "date":date_for(row,kind),
                    "coordinates":[round(lon,6),round(lat,6)],
                }
                output.append(record)
                by_class[title+"_mapped"]+=1
    if len(output)<min_records:
        raise ValueError("Insufficient EIA mapped generator inventory: "+str(len(output)))
    if counts["source_rows"] and len(output)/counts["source_rows"]<.75:
        raise ValueError("Unsafe EIA geocoded record retention rate")
    if min_records>0 and (by_class["Operating_mapped"]<15000 or by_class["Planned_mapped"]<2000 or by_class["Retired_mapped"]<2000 or by_class["Canceled or Postponed_mapped"]<100):
        raise ValueError("Unexpected EIA generator category regression")
    output.sort(key=lambda x:(x["source_tab"],int(x["plant_id"]),x["generator_id"]))
    return {
        "schema_version":1,"release":RELEASE,"published":PUBLISHED,
        "source":SOURCE_PAGE,"source_file":SOURCE,"rights":LICENSE,
        "source_sha256":digest,"attribution":"U.S. Energy Information Administration (EIA), Preliminary Monthly Electric Generator Inventory, September 2026",
        "caveat":"EIA-860M is a preliminary unit inventory; source-reported statuses do not independently verify commissioning, active generation or future construction.",
        "coordinates":"EIA-provided WGS84 location only; invalid or missing coordinates withheld, not geocoded",
        "counts":{**dict(counts),**dict(by_class),"mapped_rows":len(output)},
        "rows":output,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=normalize(args.source.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("EIA-860M normalized:",json.dumps(result["counts"],sort_keys=True),"sha256",result["source_sha256"])
if __name__=="__main__":
    main()
