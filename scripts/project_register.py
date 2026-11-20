"""Project public NVE licensing records; never copy the pending curated register."""
import math
SOURCE = "https://gis3.nve.no/map/rest/services/Mapservices/VassdragsreguleringVannkraft/MapServer/11"
LICENSE = "https://data.norge.no/nlod/"
def project_register(data):
    if data.get("schema_version") != 1 or data.get("source") != SOURCE or data.get("license") != LICENSE or not isinstance(data.get("rows"), list):
        raise ValueError("Unexpected NVE licensing provenance")
    rows, seen = [], set()
    for r in data["rows"]:
        if not isinstance(r, dict): continue
        ident, name, point = r.get("id"), r.get("vannkraftStasjonNavn"), r.get("geometry")
        if type(ident) is not int or ident in seen or not isinstance(name, str) or not name.strip(): continue
        if not isinstance(point, list) or len(point) != 2 or not all(type(x) in (int,float) and math.isfinite(x) for x in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90): continue
        seen.add(ident)
        row = {"id":f"nve-{ident}", "name":name.strip(), "type":"Hydropower", "country":"Norway", "status":"Licensing record", "developer":"Not included", "location":r.get("kommuneNavn") if isinstance(r.get("kommuneNavn"), str) else "Norway", "points":[point], "source":SOURCE, "impact":"NVE licensing record; does not establish construction, commissioning or operating capacity."}
        for src,dst in (("kdbNr","source_record"),("konsesjonStatus","licensing_code"),("konsesjonStatusDato","status_date_ms")):
            if type(r.get(src)) is int: row[dst]=r[src]
        mw=r.get("maksYtelse_MW")
        if type(mw) in (int,float) and math.isfinite(mw) and mw>0: row["reported_mw"]=mw
        rows.append(row)
    if not rows: raise ValueError("NVE licensing projection empty")
    return {"schema_version":1,"generated":data.get("generated"),"coverage":"NVE hydro licensing records only; curated third-party register pending commercial review.","license":LICENSE,"attribution":"NVE; Nordl normalization","rows":rows}
