"""Publish crawlable NVE plant profiles from the versioned source register.
Static HTML is generated from current persisted data at each Pages deployment.
No inferred coordinates, live generation or ownership percentages.
"""
import argparse,html,json,math,re
from pathlib import Path
from european_plant_pages import historic,coverage
from xml.sax.saxutils import escape as xml
BASE="https://energy.nordl.dev"
def e(v):return html.escape(str(v),quote=True)
def val(v,unit=""):
    if type(v) in (int,float) and math.isfinite(v):return f"{v:,.2f}".rstrip("0").rstrip(".")+(" "+unit if unit else "")
    if isinstance(v,str) and v.strip():return v
    return "Not supplied"
def read(root,path):return json.loads((root/"data"/path).read_text(encoding="utf-8"))
def page(title,description,canonical,body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Nordl Energy</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{e(canonical)}"><link rel="icon" href="/brand/energy-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="/asset-pages.css"><link rel="stylesheet" href="/brand/energy-brand.css?v=903a"><meta name="color-scheme" content="dark light"></head><body><header><a class="energy-brand energy-static-brand" href="/" aria-label="Nordl Energy home"><img class="energy-brand-icon" src="/brand/energy-mark.svg" width="48" height="48" alt=""/><span class="energy-brand-name"><strong>NORDL</strong><b>ENERGY</b></span></a><nav><a href="/#prices">Power prices</a><a href="/#plants">Interactive maps</a><a href="/plants/">Plant directory</a><a href="/#datasets">Datasets</a><a href="/data-coverage/">Data coverage</a></nav></header><main>{body}</main><footer>Nordl Energy · Source-attributed research, not a live generation or investment forecast. <a href="/#sources">Sources and rights</a></footer></body></html>"""
def generate(root):
    data=read(root,"hydro-plants-v1.json")
    if data.get("schema_version")!=1 or not isinstance(data.get("rows"),list) or not str(data.get("source","")).startswith("https://api.nve.no/"):raise ValueError("Invalid NVE register")
    rows=sorted(data["rows"],key=lambda r:(str(r.get("name","")).casefold(),str(r.get("id"))));seen=set();urls=[BASE+"/",BASE+"/guide.html",BASE+"/plants/"];links=[]
    for row in rows:
        id=str(row.get("id",""));name=row.get("name")
        if not re.fullmatch(r"[1-9][0-9]*",id) or id in seen or not isinstance(name,str) or not name.strip():raise ValueError("Invalid or duplicate NVE plant")
        seen.add(id);path=f"/plants/nve/{id}/";url=BASE+path;urls.append(url)
        desc=f"{name} hydro power plant in {val(row.get('municipality'))}, Norway. NVE plant register, reported capacity, main owner and regional energy research."
        items=[("NVE plant ID",id),("Municipality",val(row.get("municipality"))),("Bidding zone",val(row.get("zone"))),("Reported capacity",val(row.get("capacity_mw"),"MW")),("Normal annual generation, 1991–2020",val(row.get("annual_generation_gwh_1991_2020"),"GWh/year")),("Reported main owner",val(row.get("owner"))),("Owner organisation number",val(row.get("owner_orgnr"))),("Head",val(row.get("head_m"),"m")),("Energy equivalent",val(row.get("energy_kwh_m3"),"kWh/m³")),("Catchment reference",val(row.get("catchment_id")))]
        body=f'<p class="crumb"><a href="/plants/norway/">Norwegian hydro plants</a> / NVE {e(id)}</p><h1>{e(name)}</h1><p>{e(desc)}</p><section><h2>Plant register</h2><dl>'+''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k,v in items)+f'</dl></section><section><h2>Research and geography</h2><p>Capacity is a reported plant attribute, not current output. The main-owner entry does not establish an equity share. Annual normal generation is historical.</p><a class="action" href="/#asset/nve/{id}">Open interactive plant profile and map</a></section><section><h2>Source</h2><p>Norwegian Water Resources and Energy Directorate (NVE) · register retrieved {e(data.get("generated","Not supplied"))}. <a href="{e(data["source"])}">Original source</a> · <a href="https://data.norge.no/nlod/">NLOD licence</a>. Nordl normalized register fields.</p></section>'
        dest=root/path.strip("/")/"index.html";dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(page(name,desc,url,body),encoding="utf-8")
        links.append(f'<li><a href="{path}">{e(name)}</a> <span>{e(val(row.get("municipality")))} · {e(val(row.get("capacity_mw"),"MW"))}</span></li>')
    body=f'<h1>Norwegian hydropower plant directory</h1><p>{len(links):,} source-linked NVE plant records. Browse individual plant capacities, reported owners and research profiles.</p><ul class="directory">{"".join(links)}</ul>'
    norway=root/"plants"/"norway"/"index.html"
    norway.parent.mkdir(parents=True,exist_ok=True)
    norway.write_text(page("Norwegian hydropower plants","Source-linked NVE plant register directory",BASE+"/plants/norway/",body),encoding="utf-8")
    urls.append(BASE+"/plants/norway/")
    europe_urls,europe_count=historic(root,read(root,"europe-plants-v1.json"),BASE,page,e,val)
    urls.extend(europe_urls)
    urls.append(coverage(root,BASE,page,e))
    overview=f'<h1>Power plant directory</h1><p>Two source-attributed registers; source records are not deduplicated physical assets.</p><section><h2>Norwegian NVE register</h2><p>{len(seen):,} retrieved plant records</p><a class="action" href="/plants/norway/">Norwegian hydro plants</a></section><section><h2>European WRI archive</h2><p>{europe_count:,} historical records from the 2021 release, organized by country</p><a class="action" href="/plants/europe/">European plant archive</a></section>'
    (root/"plants"/"index.html").write_text(page("Power plant directory","Norwegian NVE and European historical WRI plant directories",BASE+"/plants/",overview),encoding="utf-8")
    (root/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{xml(u)}</loc></url>' for u in urls)+'</urlset>\n',encoding="utf-8")
    print("Crawlable NVE profiles:",len(seen),"sitemap URLs:",len(urls));return len(seen)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();generate(a.root)
