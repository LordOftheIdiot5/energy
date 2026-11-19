"""Bounded public OSM data-centre pilot; separate ODbL database, not a census."""
import argparse,hashlib,json,math,tempfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
REGIONS={"IS":"iceland","LU":"luxembourg"}
LICENSE="https://opendatacommons.org/licenses/odbl/1-0/"
ATTRIBUTION="© OpenStreetMap contributors; Geofabrik regional extract; selected and normalized by Nordl"
def classified(tags):
    return any(tags.get(k)==v for k,v in (("telecom","data_center"),("building","data_center"),("industrial","data_centre"),("industrial","data_center")))
def record(kind,ident,tags,lon,lat):
    if not classified(tags) or not tags.get("name") or not str(tags["name"]).strip():return None
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:return None
    return {"id":f"osm:{kind}:{ident}","name":str(tags["name"]).strip()[:240],"geometry":[round(lon,5),round(lat,5)],"source_object":f"https://www.openstreetmap.org/{kind}/{ident}","category":"data_centre","geometry_kind":"mapped point" if kind=="node" else "representative point of mapped area","classification":{k:tags[k] for k in ("telecom","building","industrial") if tags.get(k) in ("data_center","data_centre")}}
def extract(path):
    import osmium
    from shapely.geometry import shape
    rows={};rejected=0;factory=osmium.geom.GeoJSONFactory()
    class Handler(osmium.SimpleHandler):
        def add(self,kind,ident,tags,lon,lat):
            nonlocal rejected
            r=record(kind,ident,tags,lon,lat)
            if r:rows[r["id"]]=r
            else:rejected+=1
        def node(self,n):
            if classified(n.tags) and n.location.valid():self.add("node",n.id,n.tags,n.location.lon,n.location.lat)
        def area(self,a):
            nonlocal rejected
            if not classified(a.tags):return
            try:
                p=shape(json.loads(factory.create_multipolygon(a))).representative_point()
                self.add("way" if a.from_way() else "relation",a.orig_id(),a.tags,p.x,p.y)
            except (ValueError,RuntimeError):rejected+=1
    Handler().apply_file(str(path),locations=True,idx="flex_mem")
    return sorted(rows.values(),key=lambda x:x["id"]),rejected
def collect(region,root):
    slug=REGIONS[region];url=f"https://download.geofabrik.de/europe/{slug}-latest.osm.pbf"
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"extract.osm.pbf";h=hashlib.sha256();size=0
        with urlopen(Request(url,headers={"User-Agent":"Nordl Energy (https://energy.nordl.dev/)"}),timeout=90) as response,p.open("wb") as out:
            modified=response.headers.get("Last-Modified")
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>150_000_000:raise ValueError("Regional extract exceeds pilot cap")
                h.update(chunk);out.write(chunk)
        rows,rejected=extract(p)
    doc={"schema_version":1,"provider":"osm","region":region,"source":url,"source_sha256":h.hexdigest(),"source_last_modified":modified,"retrieved":datetime.now(timezone.utc).isoformat(),"license":LICENSE,"attribution":ATTRIBUTION,"source_notice":"Named, explicitly tagged OSM objects only. Counts are mapped source records, not unique verified facilities. Missing means unknown. No capacity, connectivity or operational status inferred. ODbL derived database kept separate.","rejected_tagged_objects":rejected,"rows":rows}
    root.mkdir(parents=True,exist_ok=True);p=root/f"{region.lower()}-datacentres.json";temp=p.with_suffix(".tmp");temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2));temp.replace(p)
    print("OSM pilot",region,"records",len(rows),"excluded tagged objects",rejected,"source bytes",size)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--region",choices=REGIONS,required=True);a.add_argument("--out",type=Path,required=True);args=a.parse_args();collect(args.region,args.out)
