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
