"""Read-only, version-pinned Global Dam Watch acquisition pilot; no production publication."""
import argparse,hashlib,json,math,io,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from datetime import datetime,timezone
ARTICLE="https://api.figshare.com/v2/articles/25988293/versions/1"
DOI="10.6084/m9.figshare.25988293.v1"
LICENSE="https://creativecommons.org/licenses/by/4.0/"
ATTR="Lehner et al. (2024), Global Dam Watch database version 1.0, Figshare; normalized by Nordl"
EXPECTED=41145
def fetch(url,cap,timeout=90):
    with urlopen(Request(url,headers={"User-Agent":"Nordl Energy (https://energy.nordl.dev/)"}),timeout=timeout) as response:
        raw=response.read(cap+1)
    if len(raw)>cap:raise ValueError("Source exceeds bounded size")
    return raw
def admit(meta):
    if meta.get("doi")!=DOI or meta.get("version")!=1:raise ValueError("Unexpected dataset version")
    lic=meta.get("license") or {}
    if lic.get("url","").rstrip("/")!="https://creativecommons.org/licenses/by/4.0":raise ValueError("Unapproved licence")
    candidates=[f for f in meta.get("files",[]) if f.get("name")=="GDW_v1_0_shp.zip"]
    if len(candidates)!=1:raise ValueError("Unexpected publisher archive")
    f=candidates[0]
    if type(f.get("size")) is not int or not 0<f["size"]<=500_000_000:raise ValueError("Archive outside pilot budget")
    # Figshare v2 returns downloadUrl in some clients, download_url in JSON.
    url=f.get("download_url") or f.get("downloadUrl")
    if not isinstance(url,str):raise ValueError("Missing publisher download URL; fields: "+", ".join(sorted(f)))
    f={**f,"downloadUrl":url}
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname not in ("figshare.com","api.figshare.com","ndownloader.figshare.com") or not u.path:raise ValueError("Unexpected publisher download URL")
    return f
def normalize(attrs,geometry):
    a={k.upper():v for k,v in attrs.items()}
    ident=a.get("GDW_ID")
    if isinstance(ident,bool) or not isinstance(ident,(int,float)) or not math.isfinite(ident) or int(ident)!=ident or ident<=0:raise ValueError("Invalid GDW identity")
    lon,lat=geometry
    if not all(math.isfinite(v) for v in (lon,lat)) or abs(lon)>180 or abs(lat)>90:raise ValueError("Invalid WGS84 geometry")
    def val(k):
        v=a.get(k)
        if not isinstance(v,str):return None
        v=v.strip()
        return v if v and v.lower() not in ("unknown","not available","n/a","-9999") else None
    return {"id":int(ident),"geometry":[round(lon,5),round(lat,5)],"dam_name":val("DAM_NAME"),"reservoir_name":val("RES_NAME"),"barrier_type":val("DAM_TYPE"),"country":val("COUNTRY"),"river":val("RIVER")}
def collect(out):
    import shapefile
    from pyproj import CRS
    meta=json.loads(fetch(ARTICLE,2_000_000))
    f=admit(meta);raw=fetch(f["downloadUrl"],f["size"],180)
    if len(raw)!=f["size"] or not f.get("computed_md5") or hashlib.md5(raw).hexdigest()!=f["computed_md5"]:raise ValueError("Publisher size/checksum failure")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=[m for m in z.infolist() if Path(m.filename).stem.lower()=="gdw_barriers_v1_0" and Path(m.filename).suffix.lower() in (".shp",".shx",".dbf",".prj")]
        parts={Path(m.filename).suffix.lower():m for m in members}
        if len(members)!=4 or set(parts)!={".shp",".shx",".dbf",".prj"} or sum(m.file_size for m in members)>100_000_000:raise ValueError("Unexpected barrier shapefile")
        crs=CRS.from_wkt(z.read(parts[".prj"]).decode())
        if not crs.equals(CRS.from_epsg(4326),ignore_axis_order=True):raise ValueError("Unexpected coordinate reference system")
        with shapefile.Reader(shp=io.BytesIO(z.read(parts[".shp"])),shx=io.BytesIO(z.read(parts[".shx"])),dbf=io.BytesIO(z.read(parts[".dbf"])),encoding="utf-8",encodingErrors="strict") as rd:
            if rd.shapeType!=shapefile.POINT:raise ValueError("Unexpected geometry type")
            fields={f[0].upper() for f in rd.fields[1:]}
            if not {"GDW_ID","DAM_NAME","RES_NAME","DAM_TYPE","COUNTRY","RIVER"}<=fields:raise ValueError("Unexpected attribute schema")
            rows=[normalize(x.record.as_dict(),x.shape.points[0]) for x in rd.iterShapeRecords()]
    if len(rows)!=EXPECTED or len({r["id"] for r in rows})!=EXPECTED:raise ValueError("Source count or identity mismatch")
    doc={"schema_version":1,"provider":"global-dam-watch","release":"1.0","source":"https://doi.org/"+DOI,"source_file":f["name"],"source_sha256":hashlib.sha256(raw).hexdigest(),"license":LICENSE,"attribution":ATTR,"retrieved":datetime.now(timezone.utc).isoformat(),"source_records":EXPECTED,"notice":"Published historical river-barrier reference. Not all barriers are dams; locations are source-mapped, not verified current operation. No reservoir polygons, capacity or live water conditions inferred. Normalized selected fields only.","rows":sorted(rows,key=lambda r:r["id"])}
    out.mkdir(parents=True,exist_ok=True);(out/"gdw-barriers-v1.json").write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":")))
    print("GDW source validated",len(rows),"unique barrier records",len({r["country"] for r in rows if r["country"]}),"country labels")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);collect(p.parse_args().out)
