"""Build and independently decode a bounded PMTiles pilot from the admitted WRI archive."""
import argparse,gzip,hashlib,json,math,time
from collections import defaultdict,Counter
from pathlib import Path
from global_assets import validate,LICENSE,ATTR
MAX_Z=8
AGG_MAX_Z=4
MAX_LAT=85.05112878
EXTENT=4096
def project(lon,lat):
    # Web Mercator world fraction. Points outside the projection must be separately counted, not shifted.
    if not -180<=lon<=180 or not -MAX_LAT<=lat<=MAX_LAT:return None
    x=(lon+180)/360
    y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2
    return max(0,min(math.nextafter(1,0),x)),max(0,min(math.nextafter(1,0),y))
def band(mw):
    if mw is None:return "unknown"
    if mw>=1000:return "1000+"
    if mw>=100:return "100-999"
    if mw>=10:return "10-99"
    return "0-9"
def tile_records(rows,z):
    """One assignment per source row per zoom; lower zooms aggregate within cell, fuel, country and capacity filter band."""
    n=2**z;buckets=defaultdict(list)
    for r,xy in rows:
        x,y=xy[0]*n,xy[1]*n;tx,ty=int(x),int(y)
        px,py=(x-tx)*EXTENT,(y-ty)*EXTENT
        buckets[tx,ty].append((r,px,py))
    for (tx,ty),items in sorted(buckets.items()):
        features=[]
        if z<=AGG_MAX_Z:
            cells=defaultdict(list)
            for r,x,y in items:cells[int(x//256),int(y//256),r["fuel"],r["country"],band(r["capacity_mw"])].append((r,x,y))
            for (_,_,fuel,country,cap),members in sorted(cells.items()):
                count=len(members)
                known=[r["capacity_mw"] for r,_,_ in members if r["capacity_mw"] is not None]
                props={"count":count,"fuel":fuel,"country":country,"capacity_band":cap,"known_capacity_count":len(known)}
                if known:props["reported_mw_sum"]=sum(known)
                features.append({"geometry":{"type":"Point","coordinates":[sum(x for _,x,_ in members)/count,sum(y for _,_,y in members)/count]},"properties":props})
            name="plant_clusters"
        else:
            for r,x,y in items:
                props={"id":r["id"],"name":r["name"],"country":r["country"],"fuel":r["fuel"],"capacity_band":band(r["capacity_mw"]),"count":1}
                if r["capacity_mw"] is not None:props["capacity_mw"]=r["capacity_mw"]
                features.append({"geometry":{"type":"Point","coordinates":[min(EXTENT-1,max(0,round(x))),min(EXTENT-1,max(0,round(y)))]},"properties":props})
            name="plants"
        yield tx,ty,{"name":name,"features":features}
def build(source,out):
    import mapbox_vector_tile as mvt
    from pmtiles.writer import write
    from pmtiles.tile import TileType,Compression,zxy_to_tileid
    from pmtiles.reader import Reader,MemorySource,all_tiles
    started=time.monotonic()
    raw=source.read_bytes();doc=validate(json.loads(raw));rows=[];excluded=[]
    for r in sorted(doc["rows"],key=lambda x:x["id"]):
        xy=project(*r["geometry"])
        if xy is None:excluded.append(r["id"])
        else:rows.append((r,xy))
    if not rows:raise ValueError("No projected records")
    metadata={"name":"Nordl historical power plants — pilot","format":"pbf","attribution":ATTR,"license":LICENSE,"description":"WRI 2021 archive; source counts not current operating plants; cluster sums of known reported MW only.","source_sha256":hashlib.sha256(raw).hexdigest(),"vector_layers":[{"id":"plant_clusters","minzoom":0,"maxzoom":AGG_MAX_Z,"fields":{"count":"Number","fuel":"String","country":"String","capacity_band":"String","known_capacity_count":"Number","reported_mw_sum":"Number"}},{"id":"plants","minzoom":AGG_MAX_Z+1,"maxzoom":MAX_Z,"fields":{"id":"String","name":"String","country":"String","fuel":"String","capacity_band":"String","capacity_mw":"Number","count":"Number"}}]}
    out.mkdir(parents=True,exist_ok=True);path=out/"wri-v130-pilot.pmtiles";size_by_zoom={};tile_counts={}
    with write(str(path)) as writer:
        for z in range(MAX_Z+1):
            tiles=[]
            for x,y,layer in tile_records(rows,z):
                # Clamp aggregate centroids to the tile integer extent.
                for f in layer["features"]:
                    f["geometry"]["coordinates"]=[min(EXTENT-1,max(0,round(v))) for v in f["geometry"]["coordinates"]]
                b=gzip.compress(mvt.encode(layer,default_options={"y_coord_down":True,"extents":EXTENT}),mtime=0)
                if len(b)>500_000:raise ValueError("Tile exceeds pilot payload cap")
                tiles.append((zxy_to_tileid(z,x,y),b))
            for tid,b in sorted(tiles):writer.write_tile(tid,b)
            tile_counts[z]=len(tiles);size_by_zoom[z]=max(len(b) for _,b in tiles)
        writer.finalize({"tile_type":TileType.MVT,"tile_compression":Compression.GZIP,"min_zoom":0,"max_zoom":MAX_Z,"min_lon_e7":-1800000000,"min_lat_e7":-850511287,"max_lon_e7":1800000000,"max_lat_e7":850511287,"center_zoom":1,"center_lon_e7":0,"center_lat_e7":0},metadata)
    # Read back every archived tile and reconcile counts/group identities; at detailed zooms every ID exactly once.
    archive=path.read_bytes();src=MemorySource(archive);reader=Reader(src)
    if reader.header()["max_zoom"]!=MAX_Z or reader.metadata()["source_sha256"]!=metadata["source_sha256"]:raise ValueError("Header or source mismatch")
    expected=Counter((r["fuel"],r["country"],band(r["capacity_mw"])) for r,_ in rows);expected_ids={r["id"] for r,_ in rows}
    got=defaultdict(Counter);ids=defaultdict(Counter);counts=Counter()
    for (z,x,y),b in all_tiles(src):
        name="plant_clusters" if z<=AGG_MAX_Z else "plants";layer=mvt.decode(gzip.decompress(b))[name]
        counts[z]+=1
        for f in layer["features"]:
            p=f["properties"];got[z][p["fuel"],p["country"],p["capacity_band"]]+=p["count"]
            if z>AGG_MAX_Z:ids[z][p["id"]]+=1
    for z in range(MAX_Z+1):
        if counts[z]!=tile_counts[z] or got[z]!=expected:raise ValueError(f"Source count mismatch at zoom {z}")
        if z>AGG_MAX_Z and (set(ids[z])!=expected_ids or any(n!=1 for n in ids[z].values())):raise ValueError(f"Source ID mismatch at zoom {z}")
    manifest={"schema_version":1,"source":doc["source"],"source_release":"1.3.0 (2021 historical)","attribution":ATTR,"license":LICENSE,"source_sha256":metadata["source_sha256"],"archive_sha256":hashlib.sha256(archive).hexdigest(),"archive_bytes":len(archive),"source_json_bytes":len(raw),"source_records":len(doc["rows"]),"projected_records":len(rows),"outside_mercator_ids":excluded,"max_tile_compressed_bytes":size_by_zoom,"tile_counts":tile_counts,"verified_decoded_record_counts":{z:sum(got[z].values()) for z in got},"elapsed_seconds":round(time.monotonic()-started,2),"notice":"Experimental archive only, not adopted by production. Individual records at z5–8; lower zoom cell aggregates; source JSON remains authoritative."}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n");print("Nordl PMTiles pilot",json.dumps(manifest))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args();build(a.source,a.out)
