# Global atlas source admission — 19 November 2026
No public or commercial ingestion until source-specific rights, release and schema are documented. Data acquisition is independent of rendering and site planning. Source-reported counts are not Nordl counts.

| Source | Rights/access confirmed | Current integration action |
|---|---|---|
| WRI GPPD 1.3.0 (2021) | CC BY 4.0; official versioned ZIP | Collector, GPU layer and export implemented; live CI gate. Historical only. |
| GEM Global Integrated Power Tracker Sept 2026 | CC BY 4.0 except Other IDs (unit/phase) containing TZ ID, CC BY-NC 4.0; https://www.gem.wiki/Global_Integrated_Power_Tracker_Methodology | Obtain publisher workbook via https://globalenergymonitor.org/download-data ; require complete Other IDs field and release notice; exclude NC rows before public storage. Map unit/phase vs projects separately. |
| Global Dam Watch v1.0 | CC BY 4.0; authors request no whole original-format rehosting without permission; https://doi.org/10.1038/s41597-024-03752-9 | Ingest normalized barrier points/attributes from versioned https://doi.org/10.6084/m9.figshare.25988293.v1 ; preserve separate reservoir polygons and stable IDs. Original source link rather than mirror. |
| PeeringDB | Commercial and bulk reuse requires explicit permission; https://tools.peeringdb.com/aup | Block automated copying/redistribution. Request written permission via support@peeringdb.com. No API key circumvention. |
| OSM public data centres and infrastructure | ODbL; https://www.openstreetmap.org/copyright | Use Geofabrik regional extracts https://www.geofabrik.de/data/download.html ; separate ODbL dataset/tiles and source attribution. Exclude contact tags; no sensitive operational data. Pilot regional extract then scale. |
| Aqueduct 4.0 | CC BY 4.0; provider requests registration and attribution https://www.wri.org/aqueduct/faq | Register as requested, acquire baseline subbasin and country data from https://www.wri.org/data/aqueduct-global-maps-40-data ; water stress screen only, not site rights or real-time supply. |
| Global Wind Atlas / Global Solar Atlas | World Bank catalogue CC BY 4.0; exact raster product terms still review | Download region/variable metadata and plan raster tiles, not massive browser JSON. |
| EU data centre efficiency reporting | Public country-level aggregates; dataset download and reuse notice review | Country metrics only, no private facility estimates. |
| US DOE hosting capacity maps | Directory links; utility data separate terms | Source links and scope; never equate distributed generation hosting capacity to available industrial load. |
| US EIA / Sodir / NVE / MET / other existing sources | Existing source-specific gates retained | Continue approved feeds and archive, connect to atlas when matched. |

Design release gate: real staged browser screenshots at 1440/1024/390; label source coverage, inspect failures, no horizontal overflow, existing region tools and fallback continue. Approved look: charcoal map, coloured points scaled by reported capacity, distinct network layers, concise filters. Review screenshots before claiming design acceptance; support light theme and globe later without losing overlays.
