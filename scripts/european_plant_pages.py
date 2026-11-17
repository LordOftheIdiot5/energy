"""Source-attributed, static European archive profiles, distinct from NVE."""
import re
from pathlib import Path
from collections import defaultdict

COUNTRIES=dict(ALB="Albania",AUT="Austria",BEL="Belgium",BGR="Bulgaria",BIH="Bosnia and Herzegovina",CHE="Switzerland",CYP="Cyprus",CZE="Czechia",DEU="Germany",DNK="Denmark",ESP="Spain",EST="Estonia",FIN="Finland",FRA="France",GBR="United Kingdom",GRC="Greece",HRV="Croatia",HUN="Hungary",IRL="Ireland",ISL="Iceland",ITA="Italy",LTU="Lithuania",LUX="Luxembourg",LVA="Latvia",MDA="Moldova",MKD="North Macedonia",MNE="Montenegro",NLD="Netherlands",NOR="Norway",POL="Poland",PRT="Portugal",ROU="Romania",SRB="Serbia",SVK="Slovakia",SVN="Slovenia",SWE="Sweden",TUR="Türkiye",UKR="Ukraine")
SOURCE="https://datasets.wri.org/datasets/global-power-plant-database"
LICENSE="https://creativecommons.org/licenses/by/4.0/"

def historic(root,data,base,page,e,val):
    if data.get("schema_version")!=1 or data.get("release_year")!=2021 or data.get("source")!=SOURCE or data.get("license")!=LICENSE or not data.get("attribution") or not isinstance(data.get("rows"),list) or not data["rows"]:
        raise ValueError("Invalid or unlicensed WRI archive")
    seen=set()
    groups=defaultdict(list)
    for r in data["rows"]:
        ident=r.get("id")
        country=r.get("country")
        if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",ident) or ident.casefold() in seen or country not in COUNTRIES or not isinstance(r.get("name"),str) or not r["name"].strip():
            raise ValueError("Invalid or duplicate WRI plant")
        seen.add(ident.casefold())
        groups[country].append(r)
    urls=[]
    def write(path,title,description,body):
        dest=root/path.strip("/")/"index.html"
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(page(title,description,base+path,body),encoding="utf-8")
        urls.append(base+path)
    attribution=f'<p>{e(data["attribution"])}. Normalized regional subset; published source release 2021, archive retrieved {e(data.get("generated","Not supplied"))}. <a href="{SOURCE}">Original dataset</a> · <a href="{LICENSE}">CC BY 4.0</a>.</p>'
    country_links=[]
    for country,rows in sorted(groups.items(),key=lambda item:COUNTRIES[item[0]]):
        label=COUNTRIES[country]
        cp=f"/plants/europe/{country.lower()}/"
        links=[]
        for r in sorted(rows,key=lambda x:(x["name"].casefold(),x["id"])):
            ident=r["id"]
            p=f"/plants/wri/{ident}/"
            name=r["name"]
            desc=f"{name} — historical {label} power plant record in the WRI 2021 archive."
            fields=[("WRI source ID",ident),("Country",label),("Fuel / technology",val(r.get("fuel"))),("Historical reported capacity",val(r.get("capacity_mw"),"MW")),("Reported commissioning year",val(r.get("commissioning_year"))),("Historical reported owner",val(r.get("owner")))]
            geometry=r.get("geometry")
            if isinstance(geometry,list) and len(geometry)==2:
                fields.extend([("Source longitude",val(geometry[0])),("Source latitude",val(geometry[1]))])
            body=f'<p class="crumb"><a href="/plants/">Plant directory</a> / <a href="{cp}">{e(label)}</a></p><p class="archive-label">Historical archive · 2021</p><h1>{e(name)}</h1><p>{e(desc)} The record does not establish present operation, ownership or actual generation.</p><section><h2>Historical plant attributes</h2><dl>'+''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k,v in fields)+f'</dl></section><section><h2>Geographical research</h2><a class="action" href="/#asset/wri/{e(ident)}">Open interactive profile and map</a></section><section><h2>Source and licence</h2>{attribution}</section>'
            write(p,name,desc,body)
            links.append(f'<li><a href="{p}">{e(name)}</a><span>{e(val(r.get("fuel")))} · {e(val(r.get("capacity_mw"),"MW"))}</span></li>')
        write(cp,f"{label}: historical power plants",f"{len(rows)} WRI 2021 plant records for {label}.",f'<p><a href="/plants/europe/">European archive</a></p><h1>{e(label)} power plants</h1><p>{len(rows):,} historical WRI 2021 records; not a current operating register.</p><ul class="directory">{"".join(links)}</ul><section><h2>Source</h2>{attribution}</section>')
        country_links.append(f'<li><a href="{cp}">{e(label)}</a><span>{len(rows):,} historical records</span></li>')
    write("/plants/europe/","European historical power plants","Country-organized European historical power plant archive from WRI 2021.",f'<p><a href="/plants/">All plant directories</a></p><h1>European historical power plants</h1><p>{len(seen):,} source records across {len(groups)} countries. The archive is not a current operating register.</p><ul class="directory">{"".join(country_links)}</ul><section><h2>Source and coverage</h2>{attribution}<p>Some remote territories are outside the geographic subset. NVE Norway listings are separate source records; do not sum the two datasets as unique physical assets.</p></section>')
    return urls,len(seen)

def coverage(root,base,page,e):
    rows=[
        ("NVE register / hydro observations","Open with NLOD attribution","https://data.norge.no/nlod/"),
        ("WRI European plant archive (2021)","Open with CC BY 4.0 attribution","https://datasets.wri.org/datasets/global-power-plant-database"),
        ("EIA public-domain petroleum references","Open for public-domain series; check third-party exceptions","https://www.eia.gov/about/copyrights_reuse.php"),
        ("Energy-Charts prices","Only source-confirmed CC BY responses for approved zones","https://api.energy-charts.info/"),
        ("ENTSO-E load forecasts and physical flows","Only reviewed categories and geographical scope","https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions"),
        ("ENTSO-E day-ahead prices","Official link; general free-reuse list does not establish permission","https://transparency.entsoe.eu/"),
        ("Yahoo financial price and derived market inputs","Official link; commercial redistribution not established","https://finance.yahoo.com/"),
        ("Elexon GB market index","Review source and upstream exceptions independently of FX; link until cleared","https://bmrs.elexon.co.uk/"),
        ("Nordic reseller prices","Official link; verify upstream exchange rights","https://www.nordpoolgroup.com/"),
        ("MET forecasts and GIE AGSI","Attribution required; respect dataset-specific terms","https://iip.gie.eu/data-usage"),
    ]
    body='<h1>Data coverage and publication rights</h1><p>API access does not imply commercial redistribution. This is a source-specific review, not a legal certification. A reference link does not confer publication rights.</p><section><h2>Source-by-source review</h2><ul class="rights-list">'+''.join(f'<li><strong>{e(name)}</strong><p>{e(status)} · <a href="{e(url)}">Official source / terms</a></p></li>' for name,status,url in rows)+'</ul></section><section><h2>Open dataset access</h2><p>Only the reviewed dataset catalog is approved for structured commercial export. Mixed market display data is not a licensed export.</p><a class="action" href="/#datasets">Browse reviewed datasets</a></section>'
    p=root/"data-coverage"/"index.html"
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(page("Data coverage and rights","Source-specific data permissions and coverage.",base+"/data-coverage/",body),encoding="utf-8")
    return base+"/data-coverage/"
