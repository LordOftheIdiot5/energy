"""Build an explicit public artifact, never the checkout. Fail closed."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from publication_policy import write_projection,project_snapshot,project_economic,project_shared,SHARED_ZONES
from price_rights import permitted
from build_plant_pages import generate
ROOT=Path(__file__).resolve().parents[1]
SITE="index.html guide.html CNAME robots.txt style.css workspace.css portal.css energy-map.css research-tools.css premium.css terminal.css geography.css visual-terminal.css energy-pro.css asset-pages.css energy-contours.svg asset-research.js data-cache.js energy-atlas.js atlas-measured-flows.js atlas-gdw.js atlas-regional-grid.js atlas-projects.js atlas-uk-projects.js atlas-us-generators.js atlas-nacei-oilgas.js atlas-gem-pipelines.js atlas-gpu.js global-atlas.js atlas-assets.js hydro-atlas.js energy-land.js energy-map.js energy-topo.js feed-freshness.js geo-labels.js geography.js hydro-intelligence.js infrastructure.js map-navigation.js market-reference.js nordl-charts.js chart-lab.js ssb-energy.js energinet-energy.js plant-profile.js plant-tile-map.js portal.js project-atlas.js public-grid-map.js regional-atlas.js release-research.js research-tools.js satellite-layer.js shared-energy.js terminal.js terrain-relief.js visual-terminal.js weather-geography.js workspace.js nordic-observations.js energy-data-access.js daily-monitor.js brand/energy-mark.svg brand/energy-wordmark-dark.svg brand/energy-wordmark-light.svg brand/energy-social.svg brand/energy-social.png brand/energy-brand.css".split()
DATA="atlas-world-borders-v512.json atlas-world-land-v512.json catalog-v1.json commercial-catalog-v1.json hydro-v1.json hydro-plants-v1.json hydro-owners-v1.json hydro-validation-v1.json norway-zones-v1.json nve-catchments-v1.json nve-projects-v1.json uk-repd-projects-v1.json nacei-oilgas-2017-v1.json nve-reservoirs-v1.json nve-stations-v1.json europe-plants-v1.json weather-geography-v1.json weather-vintages-v1.json owner-company-links-v1.json".split()
DOCS="V89-API.md v85-benchmark-results.json v86-price-benchmark-results.json".split()
KINDS={"day-ahead","entsoe-series","gas-storage","snow-water","weather-forecast"}
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(root,out,name):
    a=root/name
    if not a.is_file() or a.is_symlink():raise ValueError("Missing or unsafe file: "+name)
    b=out/name;b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def assert_public(root):
    for file,fn in (("energy.json",project_snapshot),("economic-reference-v1.json",project_economic),("entsoe-open.json",project_shared)):
        d=load(root/"data"/file)
        if d!=fn(d):raise ValueError("Unapproved source snapshot: "+file)
def validate_uk_repd(d):
    if d.get("schema_version") != 1 or d.get("release") != "2026-10" or d.get("published") != "2026-11-13" or d.get("license") != "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" or d.get("source") != "https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract" or d.get("source_sha256") != "48e76c49f33a1090e78108d1ea9bfe689b35963ea3be1bb4f6516d038a5ff862":
        raise ValueError("Unapproved UK REPD project provenance")
    counts = d.get("counts", {})
    rows = d.get("rows")
    if counts.get("source_records") != 14968 or counts.get("mapped_records") != 14388 or counts.get("duplicate_source_rows") != 1 or not isinstance(rows, list) or len(rows) != 14388:
        raise ValueError("Unexpected UK REPD project coverage")
    seen = set()
    for r in rows:
        ident, g = r.get("id"), r.get("geometry")
        if not isinstance(ident, str) or not re.fullmatch(r"uk-repd-\d+", ident) or ident in seen or not isinstance(g, list) or len(g) != 2 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and -180<=v<=180 for v in g) or not (-13<=g[0]<=6 and 48<=g[1]<=63) or r.get("country") not in ("England","Scotland","Wales") or not r.get("status") or "generation_mw" in r or "operational" in r:
            raise ValueError("Unsafe UK REPD project record")
        seen.add(ident)
    return True

def stage(root,out):
    root=root.resolve();out=out.resolve()
    if out==root or out.is_relative_to(root) or root.is_relative_to(out) or out.exists():raise ValueError("Use a new separate output directory")
    assert_public(root)
    validate_uk_repd(load(root/"data/uk-repd-projects-v1.json"))
    out.mkdir(parents=True)
    for p in SITE:copy(root,out,p)
    for p in DATA:copy(root,out,"data/"+p)
    for p in DOCS:copy(root,out,"docs/"+p)
    write_projection(root/"data",out/"data")
    geo=load(root/"data/weather-geography-v1.json")
    radar=geo.get("radar")
    if radar:
        name=radar["file"]
        if not re.fullmatch(r"radar-nordic-[a-f0-9]{16}\.png",name) or not radar["source"].startswith("https://api.met.no/weatherapi/radar/2.0/") or sha(root/"data"/name)!=radar["sha256"]:raise ValueError("Invalid MET radar provenance")
        copy(root,out,"data/"+name)
    manifest=load(root/"data/archive/index-v1.json")
    for item in manifest["partitions"]:
        kind,month=item["kind"],item["month"]
        if kind not in KINDS or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",month) or item["path"]!=f"archive/{kind}/{month}.json":raise ValueError("Unknown partition")
        p=root/"data"/item["path"];obj=load(p)
        if sha(p)!=item["sha256"] or len(obj["rows"])!=item["rows"] or obj["kind"]!=kind or obj["month"]!=month:raise ValueError("Archive checksum/identity mismatch")
        for r in obj["rows"]:
            if not r.get("attribution") or not r.get("license"):raise ValueError("Missing archive rights")
            if kind=="day-ahead" and (not permitted(r.get("zone"),r["license"]) or not r.get("source","").startswith("https://api.energy-charts.info/")):raise ValueError("Unapproved price archive")
            if kind=="entsoe-series":
                category=r.get("kind");valid=(category=="day_ahead_load_forecast" and r.get("article")=="6.1.b" and r.get("zone") in SHARED_ZONES) or (category=="physical_flow" and r.get("article")=="12.1.g" and r.get("from") in SHARED_ZONES and r.get("to") in SHARED_ZONES)
                if not valid or r.get("source")!="https://transparency.entsoe.eu/" or r["license"]!="https://creativecommons.org/licenses/by/4.0/":raise ValueError("Unapproved ENTSO-E archive")
            if kind=="gas-storage" and r.get("source")!="https://agsi.gie.eu/":raise ValueError("Unapproved gas archive")
            if kind=="snow-water" and not r.get("source","").startswith("https://gts.nve.no/api/GridTimeSeries/"):raise ValueError("Unapproved snow archive")
            if kind=="weather-forecast" and r.get("source")!="https://api.met.no/weatherapi/locationforecast/2.0/":raise ValueError("Unapproved weather archive")
        copy(root,out,"data/"+item["path"])
    copy(root,out,"data/archive/index-v1.json")
    # Only publish the already licensed NVE register; curated third-party records remain private.
    from project_register import project_register
    (out/"data/energy-projects-v1.json").write_text(json.dumps(project_register(load(root/"data/nve-projects-v1.json")),ensure_ascii=False),encoding="utf-8")
    from nordic_observations import public_files
    from ssb_energy import public_files as ssb_files
    from energinet_energy import public_files as denmark_files
    from sodir_production import public_files as sodir_files
    from global_assets import public_files as global_files
    observations=[]
    for name in list(public_files(root/"data"))+list(ssb_files(root/"data"))+list(denmark_files(root/"data"))+list(sodir_files(root/"data"))+list(global_files(root/"data")):
        copy(root,out,"data/"+name)
        item=load(root/"data"/name)
        observations.append({"path":name,"provider":item["provider"],"rows":len(item["rows"]),"generated":item.get("generated"),"month":item.get("month"),"year":item.get("year"),"license":item["license"],"attribution":item["attribution"],"sha256":sha(root/"data"/name)})
    from hydapi_relationships import generate as generate_relationships
    from hydro_transfer_network import generate as generate_transfer
    for derived in (generate_relationships(out/"data"),generate_transfer(out/"data")):
        if derived:
            item=load(derived)
            observations.append({"path":derived.name,"provider":"nve-derived","rows":len(item["rows"]),"generated":item.get("generated"),"month":None,"license":item["license"],"attribution":item["attribution"],"sha256":sha(derived)})
    (out/"data/observations").mkdir(exist_ok=True)
    (out/"data/observations/index-v1.json").write_text(json.dumps({"schema_version":1,"datasets":observations},indent=2)+"\n",encoding="utf-8")
    generate(out)
    from osm_publication import stage_osm
    stage_osm(root/"data"/"osm-odbl",out/"data"/"osm-odbl")
    from gdw_publication import stage_gdw
    stage_gdw(root/"data"/"gdw",out/"data"/"gdw")
    from osm_grid_publication import stage_grid
    stage_grid(root/"data"/"osm-grid-odbl",out/"data"/"osm-grid-odbl")
    # Verified generator units are exposed through four on-demand inventories.
    # The 40,048-row source archive itself is not copied into the public artifact.
    from nacei_publication import validate as validate_nacei
    validate_nacei(load(root/"data/nacei-oilgas-2017-v1.json"))
    from gem_pipeline_publication import validate_files as validate_gem
    validate_gem(root/"data/gem-gas-202511")
    for name in ("gem-gas-pipelines-202511-v1.json","gem-gas-pipeline-routes-202511-v1.geojson"):
        copy(root,out,"data/gem-gas-202511/"+name)
    from eia_publication import stage as stage_eia
    stage_eia(root/"data",out/"data/eia860m")
    assert_public(out)
    print("Public artifact:",len(list(out.rglob("*.html"))),"HTML pages")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path);p.add_argument("--check-only",action="store_true");a=p.parse_args()
    if a.check_only:assert_public(ROOT)
    else:stage(ROOT,a.out)
