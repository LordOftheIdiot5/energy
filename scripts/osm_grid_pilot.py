"""Read-only public grid mapping pilot, isolated ODbL source records. No inferred topology or load."""
import argparse,hashlib,json,math,re,subprocess,tempfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from osm_datacentres import REGIONS,LICENSE,ATTRIBUTION
def category(tags):
    if tags.get("power")=="line" and tags.get("line") not in ("busbar","bay"):return "overhead_line"
    if tags.get("power")=="cable" and tags.get("line") not in ("busbar","bay"):
        return {"underwater":"underwater_power_cable","underground":"underground_power_cable"}.get(tags.get("location"),"power_cable_unspecified")
    if tags.get("power")=="substation":return "substation"
    return None
def voltage(raw):
    if not isinstance(raw,str) or not re.fullmatch(r"[0-9]{1,7}(;[0-9]{1,7})*",raw):return []
    return sorted({int(v) for v in raw.split(";") if 0<int(v)<=1500000},reverse=True)
def record(kind,ident,tags,geometry):
    cat=category(tags)
    if not cat:return None
    # Regional display geometry only; keep precise source route at the original publisher.
    pts=[tuple(round(float(v),3) for v in p) for p in geometry]
    if not pts or any(len(p)!=2 or not all(math.isfinite(v) for v in p) or abs(p[0])>180 or abs(p[1])>90 for p in pts):return None
    unique=[p for i,p in enumerate(pts) if i==0 or p!=pts[i-1]]
    if cat=="substation":
        if len(unique)!=1:return None
        geom={"type":"Point","coordinates":unique[0]}
    else:
        if len(unique)<2:return None
        geom={"type":"LineString","coordinates":unique}
    name=tags.get("name")
    return {"id":f"osm:{kind}:{ident}","category":cat,"name":str(name)[:160] if name else None,"voltage_v":voltage(tags.get("voltage")),"geometry":geom,"source_object":f"https://www.openstreetmap.org/{kind}/{ident}"}
def extract(path):
    import osmium
    from shapely.geometry import shape
    rows={};rejected=Counter();factory=osmium.geom.GeoJSONFactory()
    class Handler(osmium.SimpleHandler):
        def add(self,kind,ident,tags,points):
            cat=category(tags);r=record(kind,ident,tags,points)
            if r:rows[r["id"]]=r
            else:rejected[cat or "unclassified"]+=1
        def node(self,n):
            if category(n.tags)=="substation":
                if n.location.valid():self.add("node",n.id,n.tags,[(n.location.lon,n.location.lat)])
                else:rejected["substation"]+=1
        def way(self,w):
            cat=category(w.tags)
            if not cat or cat=="substation":return
            try:
                if not all(n.location.valid() for n in w.nodes):raise ValueError("Missing coordinates")
                # Simplify regional display lines in geographic coordinates, not engineering geometry.
                line=shape(json.loads(factory.create_linestring(w))).simplify(.002,preserve_topology=True)
                self.add("way",w.id,w.tags,list(line.coords))
            except (RuntimeError,ValueError):rejected[cat]+=1
        def area(self,a):
            if category(a.tags)!="substation":return
            try:
                p=shape(json.loads(factory.create_multipolygon(a))).representative_point()
                self.add("way" if a.from_way() else "relation",a.orig_id(),a.tags,[(p.x,p.y)])
            except (RuntimeError,ValueError):rejected["substation"]+=1
    Handler().apply_file(str(path),locations=True,idx="flex_mem")
    return sorted(rows.values(),key=lambda r:r["id"]),dict(rejected)
def collect(region,out):
    from osm_extract_sources import download
    with tempfile.TemporaryDirectory() as tmp:
        p,source=download(region,tmp)
        rows,rejected=extract(p)
    counts=dict(Counter(r["category"] for r in rows))
    if not rows or not counts.get("overhead_line") or not counts.get("substation"):raise ValueError("Empty network cohort")
    doc={"schema_version":1,"provider":"osm","region":region,**source,"retrieved":datetime.now(timezone.utc).isoformat(),"license":LICENSE,"attribution":"© OpenStreetMap contributors; "+source["extract_provider"]+" regional extract; selected and normalized by Nordl","source_records":len(rows),"category_counts":counts,"rejected_objects":rejected,"notice":"Regional generalized public map reference. Counts are source objects, not distinct grid circuits or verified facilities. Underwater includes rivers/lakes; not necessarily submarine. Missing voltage unknown. No measured flow, spare capacity, circuit connectivity or operational status inferred. No internal components, access or security attributes. Source geometry is generalized and unsuitable for engineering.","rows":rows}
    out.mkdir(parents=True,exist_ok=True);(out/f"{region.lower()}-grid-pilot.json").write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":")))
    print("OSM grid source validated",region,len(rows),"records",json.dumps(counts),"rejected",json.dumps(rejected))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--region",choices=REGIONS,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args();collect(a.region,a.out)
