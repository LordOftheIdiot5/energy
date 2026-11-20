"""Fail-closed publication gate for August 2017 NACEI reference assets."""
from collections import Counter
import math
SOURCE="https://geoappext.nrcan.gc.ca/arcgis/rest/services/NACEI/energy_infrastructure_of_north_america_en/MapServer"
ATTRIBUTION="North American Cooperation on Energy Information (NACEI), August 2017"
EXPECTED={"gas_processing":(4,1278),"lng_terminals":(5,15),"refineries":(10,168)}
def validate(doc):
    if doc.get("schema_version")!=1 or doc.get("source")!=SOURCE or doc.get("rights")!="free and unrestricted with acknowledgement (NACEI)" or doc.get("attribution")!=ATTRIBUTION or doc.get("source_period")!="2017-08":
        raise ValueError("NACEI source rights or history mismatch")
    if doc.get("layers",{}).get("refineries",{}).get("excluded",{}).get("facility_name_not_reported")!=141:
        raise ValueError("NACEI missing facility names changed unexpectedly")
    seen=set()
    for kind,(lid,n) in EXPECTED.items():
        meta=doc.get("layers",{}).get(kind,{})
        rows=doc.get("rows",{}).get(kind)
        if meta.get("source_rows")!=n or meta.get("mapped_rows")!=n or meta.get("layer_id")!=lid or not isinstance(rows,list) or len(rows)!=n:
            raise ValueError("NACEI historical coverage regression")
        for r in rows:
            g=r.get("geometry")
            if r.get("kind")!=kind or not isinstance(r.get("source_objectid"),int) or r.get("id")!=f"nacei-{lid}-{r['source_objectid']}" or r["id"] in seen:
                raise ValueError("Unsafe NACEI identity")
            if r.get("country") not in ("Canada","United States","Mexico") or not r.get("facility") or type(r.get("facility_name_reported")) is not bool:
                raise ValueError("Unsafe NACEI location / name")
            if r.get("status")!="Status not reported in historic source" or "operating" in r or "generation" in r:
                raise ValueError("NACEI current status or generation inferred")
            if not isinstance(g,list) or len(g)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in g) or not (-170<=g[0]<=-50 and 14<=g[1]<=74):
                raise ValueError("NACEI location invalid or invented")
            if r.get("reported_capacity") is not None and (type(r["reported_capacity"]) not in (int,float) or not math.isfinite(r["reported_capacity"]) or r["reported_capacity"]<0):
                raise ValueError("NACEI invalid capacity")
            seen.add(r["id"])
    if len(seen)!=1461:raise ValueError("NACEI total count mismatch")
    return True
