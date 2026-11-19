# Nordl Global Infrastructure Atlas
Owner direction: 2026-11-19. Goal: best-in-class global public infrastructure research experience, not an unsupported claim to completeness. Single map with toggleable layers, source inspector, compare/export and Stockwatch links; build on existing MapLibre atlas.

## Layer priorities and source gates
| Scope | Candidate source | Rights and publication gate |
|---|---|---|
| Power plants incl. wind, solar, nuclear, coal, gas, hydro, geothermal | Global Energy Monitor GIPT https://globalenergymonitor.org/projects/global-integrated-power-tracker ; WRI archive; EIA-860 and national registers | GEM workbook-specific permissions, citations, exclude TransitionZero TZ ID CC BY-NC rows and any unresolved mixed rights; verify coordinates/status/source vintage. WRI archive historical only. |
| Transmission lines, substations, pipelines, telecom, water and transport | OpenStreetMap https://www.openstreetmap.org/copyright ; OpenInfraMap reference https://openinframap.org/copyright | ODbL database kept separate; attribution, share-alike assessment, self-host extracts/vector tiles. Do not use public OSM tile servers as bulk source. |
| Oil/gas fields, licence ownership, production, facilities and pipelines | Sodir https://www.sodir.no/en/facts/data-and-analyses/open-data/ ; GEM oil and gas trackers https://globalenergymonitor.org/download-data | NLOD/third-party exclusions; source-specific geometry/ownership and licence ID join. Verify date-effective ownership. |
| Dams, river barriers, reservoirs | Global Dam Watch https://www.globaldamwatch.org/database ; HydroSHEDS; NVE | GDW v1 CC BY reported; validate exact release and attribution. Hydrological connectivity only from documented topology. |
| Ports, shipping terminals, AIS-derived aggregates | NGA World Port Index, IMF PortWatch, official port registers | Verify current dataset-specific terms; no unlicensed live AIS or tracking. |
| Rail, roads, airports, bridges and tunnels | OSM; national transport open registers | ODbL isolation; public infrastructure only. |
| Industrial sites, steel, cement, mines, refineries, LNG, storage | GEM sector trackers, government registers | Dataset-specific rights, ordinary public records only. |
| Public data centres and communications | Public directories and open OSM layers | No private facility data, security/access details or inferred vulnerabilities. |
| Weather, hydrology, prices, trade, generation and capacity | Existing Nordl datasets plus MET, EIA, ENTSO-E permitted categories | Keep measured, forecast, historical and calculated values distinct; no invented real-time status. |

## Ordered implementation
1. V90.6d: add world navigation, source inventory, coverage notice; preserve Nordic zoom, search, fallback, maps and all existing datasets. Parallel: production verification and petroleum ownership metadata/endpoints.
2. V90.6e: canonical asset/geometry registry and candidate source snapshots; import licensed sample cohorts, then full approved data; source/license/vintage and location accuracy per field. Country coverage report and stable IDs.
3. V90.6f: scalable global renderer: GPU vector layers, clustering at each zoom, lazy tile requests, filter by category/status/country/owner/capacity; 2D first, optional globe. Search by names/IDs and regional summary. No global DOM marker loop.
4. V90.6g: oil/gas assets and date-effective ownership, dams/reservoirs, grids and pipelines as separately licensed layers. No inferred geometry or double-counted capacity.
5. V90.7: forecast overlays with archived vintages; measured inputs only; model acceptance stays unchanged.
6. V90.8: Stockwatch legal entity links, ownership portfolio, actual production series; no estimated profits or revenue from capacity. Link both sites.
7. V90.9: shareable map state, local saved layers, side-by-side map comparison, historical timeline, source downloads and commercial API; permitted dataset exports remain open.
8. V91: performance, attribution, accessibility and coverage audit. Further ports, transport, industry, public telecommunications and other civil layers follow as rights and quality allow.

## Architecture
Keep current MapLibre and SVG fallback. Use versioned source partitions/immutable checksums and separate ODbL extracts rather than mixing into proprietary datasets. Evaluate GeoParquet for archive/analysis, PMTiles on R2 for public read-only vector tiles with Range/CORS support, and a scoped query service for search and joins. https://maplibre.org/projects/gl-js/ ; https://docs.protomaps.com/pmtiles/cloud-storage. Infrastructure metadata stays in source registries; stable canonical IDs and versioned edge tables carry evidence, ownership effective dates, degree of confidence and source references. GPU points/lines/polygons can aggregate at global scales; maintain zoom-in drilldown. Do not ship bulk world assets in the initial homepage payload.

## Acceptance criteria
- Every published layer has source, licence, version date, geometry type, coverage and update status. No unapproved or noncommercial rows in commercial artifacts.
- World/Nordic/Norway navigation, combined layer toggles, search, keyboard accessible asset inspector, 390/1440 viewport, light/dark, share links and fallback tested. World basemap does not imply global asset coverage.
- At each zoom, source record accounting and drilldown; invalid coordinates and duplicates quarantined; no disappearing assets without explicit zoom/coverage note.
- Separate asset count/record count/capacity totals and report source coverage by country/category/quality. Initial target 100k+ approved power facilities if licence gates and data match allow it, then expand. No arbitrary count assertions.
- Target initial map interaction under 3 seconds on representative broadband and smooth pan/zoom with large approved cohorts; measure real browser/device results rather than advertise guarantees.
- Public, already published civil/industrial data for research; do not expose unpublished locations, personal information, security/access details or vulnerability rankings.

## Approved visual direction and enterprise research (19 November 2026)
Owner approved the reference screenshot: charcoal/night basemap, restrained luminous infrastructure lines, category colours, capacity-scaled symbols, compact layer groups with legends, full-screen map, optional 3D globe and click-to-inspect. Original Nordl visual language, accessible contrast, non-colour indicators, light mode and reduced motion; never copy competitor assets. Keep regional data and global coverage explicitly distinguished.

### Priority product: Data Centre & Industrial Site Planner
Bring this into V90.6e/f alongside power and water layers rather than defer all telecom to post-launch. Public facility/interconnection directory (not a complete census of compute sites), regional power prices and mix, water stress, climate, renewables, land-use and published industrial zones. Compare proposed user-entered sites or regions, allow configurable weights, hard constraints and transparent evidence grades. No claim of spare grid capacity, connection feasibility, fibre service, water rights, available land or guaranteed permits based on proximity. Use published utility availability only when its scope/units/date and rights are confirmed; otherwise flag for operator diligence. No facility-level sensitive operational details or vulnerability assessment. Public facilities only; user plans private by default. No server upload of private project coordinates without explicit consent.
- PeeringDB https://api.peeringdb.com/ : 5,910 facilities, 1,333 exchanges at review; dynamic directory, interconnection rather than all data centres. API documentation https://www.peeringdb.com/apidocs/ ; permitted bulk/local-cache method https://docs.peeringdb.com/blog/web_rate_limiting/ . Verify database commercial redistribution licence before ingest/publication; no contact/private fields, no website scraping. Track API changes https://docs.peeringdb.com/blog/a_new_api/ .
- OpenStreetMap telecom=data_center, building=data_center, public industrial sites: https://wiki.openstreetmap.org/wiki/Tag:telecom%3Ddata_center ; ODbL isolation and coverage caveats.
- EU data-centre energy/water reporting https://energy.ec.europa.eu/topics/energy-efficiency/energy-efficiency-targets-directive-and-rules/energy-efficiency-directive/energy-performance-data-centres_en ; https://eur-lex.europa.eu/eli/reg_del/2024/1364/eng : public EU/member-state aggregates, not individual facility operating metrics.
- WRI Aqueduct 4.0 https://www.wri.org/aqueduct/faq : CC BY 4.0, register/attribute as requested, basin-level screening not site-specific water supply. 
- Global Solar Atlas and Global Wind Atlas World Bank catalogue https://datacatalog.worldbank.org/search/dataset/0038509/global-solar-atlas-application and https://datacatalog.worldbank.org/search/dataset/0038957/global-wind-atlas : CC BY 4.0 catalogue, verify selected downloadable raster terms.
- US DOE hosting capacity map directory https://www.energy.gov/cmei/vehicles/us-atlas-electric-distribution-system-hosting-capacity-maps : link to utilities, not uniform nationwide available load capacity. LBNL queues https://emp.lbl.gov/queues/ : generation and storage project queues, not spare load capacity; data licence separate review.
- IEA 2026 https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary : 485 TWh global data-centre electricity in 2025, 950 TWh central projection for 2030; contextual data distinct from observed asset records.

### Differentiating work packages
A. Site comparison: select user-defined candidate regions or sites; constraint screening, evidence coverage, weighted scoring only for comparable available fields. Missing means unknown, not zero; show score sensitivity, weights and separate completeness. Nordic pilot then international expansion. 
B. Scenario economics: IT/facility load distinction and PUE, run hours, electricity cost bands, grid tariffs separately, cooling/water assumptions, waste-heat reuse and renewable procurement scenarios. No claimed real-world economics from assumed inputs. Link to Leivro for equipment planning where appropriate.
C. Industrial symbiosis: map public district-heating, heat consumers, waste-heat suppliers and renewable projects; proximity is an opportunity to investigate, not a verified connection or commercial contract. 
D. Project intelligence: official announced/permitted/construction/operating/cancelled status with source, effective dates, changelog and optional user alerts. No fabricated projects or capacity.
E. Evidence graph: canonical company, project, facility, region, source and time identifiers; signed/evidenced ownership and reported commercial relationships, never infer a supplier contract from shared geography. Stockwatch linked portfolio and news.
F. Natural-language research assistant: convert user intent to visible map filters, compare candidates, generate cited feasibility screening reports with uncertainty and source/version; not a planning approval or engineering certification. No sensitive facility security queries.
G. Delivery: free public map and standard downloads, candidate paid workspaces, private project lists, comparative reports, historical change feeds, licensed API and managed research. Keep existing open access. V90.9 commercial gate unchanged.
H. Quality: evidence-first ranking, explicit spatial resolution, time conventions, data lineage, historical reproducibility, per-layer zoom/accounting and 390/1440 desktop/mobile tests. Target business value via task completion and candidate comparison accuracy, not just marker count.
