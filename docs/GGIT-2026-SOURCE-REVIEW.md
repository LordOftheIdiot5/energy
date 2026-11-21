# V90.6g3 — GEM LNG / gas infrastructure source and rights review

Research checkpoint: 2026-11-21. **Documentation only. No dataset downloaded, imported, mirrored, or published in this change.**

## Publisher source and observed release labels

- Primary publisher: Global Energy Monitor (GEM), [Global Gas Infrastructure Tracker](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker), [download page](https://globalenergymonitor.org/download-data).
- Publisher's current search-indexed page on 2026-11-21 reports **October 2026 for LNG terminals**, **November 2025 for gas transmission pipelines** and **June 2026 for LNG carriers**. The older cached page can still present September 2025 LNG / December 2025 carriers; **do not use a cached page alone to pick the release**. Verify the file's included release label and date upon official download.
- Publisher lists gas transmission pipelines and LNG import/export terminals; the scope excludes distribution/gathering lines and LNG storage/bunkering-only facilities. GEM states some pipeline routes are *approximated* from research, some are absent from map geometry, and locations may be marked approximate rather than exact.
- GEM offers spreadsheets and GIS formats (GeoJSON, GeoPackage, shapefiles) **via its official download form**. Obtain using the publisher's intended process, not an unauthenticated API endpoint or hidden/guessed URL.
- [Global Energy Ownership Tracker](https://globalenergymonitor.org/projects/global-energy-ownership-tracker) was indexed with a **November 2026** release covering gas pipelines and LNG terminals. This is a **candidate** input for the later ownership graph, not confirmed as downloaded or validated. A cached page displayed July 2026; only an actual verified release package can establish the vintage. Do not merge company names alone.

## Reuse gate

- GEM publishes a [Creative Commons Attribution 4.0 licence](https://globalenergymonitor.org/creative-commons-license). CC BY 4.0 generally allows commercial reproduction and adaptation with attribution, a link to licence, and modification disclosure. **Confirm that the exact downloaded tracker package and each source/geometry sheet are covered**, and check for third-party carve-outs and any extra download conditions. Do not infer blanket commercial rights from the availability of a web page.
- Preserve publisher/source URL, release date, source licence notice, attribution and checksum in every retained package and derived public projection. Public use is gated independently from private source access.
- Current Nordl global pipeline layer uses **4,246 Nov 2025 source records; 3,921 mapped routes and 325 without mapped routes** ([PR #93](https://github.com/LordOftheIdiot5/energy/pull/93)). Do not treat changing public tracker headline counts (or number of phases/routes) as a comparable diff or assert a 2026 pipeline refresh without new evidence.

## Next importer acceptance checklist

1. Acquire the authorized **October 2026 LNG terminal workbook/GIS release** using the official form. Record an unmodified private snapshot, SHA-256, exact release notice, country fields, schema, native project/phase IDs, status codes, licence and provenance. A missing archive or permission means **not imported**.
2. Confirm the actual **latest gas pipeline** download vintage separately. If November 2025 remains latest, retain it as the historical current baseline and do not overwrite the existing layer with a differently parsed source.
3. Build a reviewed mapping from native IDs to existing internal IDs; explicit unmatched/duplicated native IDs, multi-phase terminals, approximate locations, missing coordinates, status/vintage distinctions and source-specific capacities. No coordinate invention or name-only fuzzy join.
4. Reconcile totals against the workbook and GIS with discrepancy notes. Preserve cancelled/shelved/mothballed/retired statuses rather than implying operating status from public map presence.
5. Only after rights and identity review, stage a limited allowlisted public projection, run the global-map Playwright + production health gates, and archive previous versions for point-in-time changes.
6. Treat the 2026 ownership release as a **separate later V90.6g5 candidate** with identity/ownership effective dates. A relationship graph requires verified owner/LEI/registry links, not name or spatial proximity.

## Research decision

**V90.6g3 remains open, importer blocked at official file retrieval / package-specific rights verification.** The official publisher and candidate release labels have been identified. No source records or licence approvals were changed by this review.
