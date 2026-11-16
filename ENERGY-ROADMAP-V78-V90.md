# Energy master roadmap V78–V90
Approved 2026-11-16. Production: https://energy.nordl.dev/
Keep this file current with PRs, test runs, deployment evidence and known blockers. Do not declare a milestone complete on code or fixture tests alone.
| Version | Objective | Status | Acceptance gate |
|---|---|---|---|
| V78 | Automated visual quality checks | Merged; production smoke passed | Real basemap, actual overlays, zero page errors, screenshots; run after deployments |
| V79 | Topography and shaded terrain | Merged; real source and interaction tests passed, production visual test pending | Optional real elevation relief, preserve full context and overlays; verify actual tiles and rendered map |
| V80 | Satellite and aerial imagery | Historical Sentinel-2 merged; real imagery/elevation tile browser test passed; aerial pending | Verified commercial display permissions and coverage; preserve labels and overlays |
| V81 | Actual transmission lines and substations | Norwegian direct-display merged; 23 actual map images tested; European coverage pending | Source-linked real geometry, voltage and provenance; distinguish schematic routes |
| V82 | Geographical weather, precipitation and snow layers | Radar and 5-cell SWE pilot merged, source/browser tests passed; optional map markers merged and browser tested; continuous gridded map and forecasts pending | Dated, unit-labelled gridded observations/forecasts; coverage and uncertainty |
| V83 | Expanded European infrastructure database | Rights review; permission draft PR #22 | TYNDP reconciliation, geometry and redistribution rights; retain source exceptions |
| V84 | Individual power-plant research pages | Live; production smoke passed | Stable IDs, source links, coverage and historical/current distinction |
| V85 | Weather-based hydropower forecasting | Retrospective benchmark validated; weather uplift marginal; operational forecast blocked | Historical catchment and inflow data, time-aware holdout benchmark against seasonal/persistence baselines |
| V86 | Electricity price forecasting | NO2 benchmark initial unit mismatch; corrected in PR #26, live rerun pending | Issue-time features, price/load history, rolling-origin evaluation and calibrated errors |
| V87 | Stockwatch company and ownership integration | Direct legal-entity pilot AFK with source links; wider parent/issuer matching pending | Verified legal identifiers, dated ownership, no inferred equity exposures |
| V88 | Professional interactive graphs across all workspaces | Shared history chart performance/plant context and benchmark dashboard in release validation; further coverage audit remains | Units, axes, dates, legends, interactive inspection, source and missing-data handling |
| V89 | Commercial datasets and API | Selected open catalog and tested loopback API service; production authentication/billing not deployed | Rights register, versioned schemas, access control, quotas, exports and documentation |
| V90 | Full design, data quality and performance audit | Consolidated release audit under validation; open risks retained | Mobile/desktop tests, accessibility, data freshness, source coverage and performance budgets |

## Release discipline
- Preserve V77 full-context maps, visible markers/clusters, fallback overview, zoom, pan, fullscreen and asset inspection.
- Keep observations, historical archives, scenarios and model forecasts distinct; never invent data or source geometry.
- Use separate research branches for unverified sources or models; release only validated features.
- Verify source licensing and attribution before public or commercial redistribution.
- Prioritize V85–V87 commercially while resolving geographical and data dependencies in parallel.
- Use shared data infrastructure with Stockwatch and Leivro where verified; avoid mixing unrelated source identities.

## Evidence
- V77 production release: c2130a5504b529ddc411bd2a7f9128696a64620a.
- V78 live smoke: https://github.com/LordOftheIdiot5/energy/actions/runs/43943335361 (10,212 European records, 69 visible clusters/markers, 3,092 catchments, 2,104 rendered polygon fragments, 54 actual vector tiles, zero page errors).
- V78 merge: aa8efc3ac368321ec8652a2e0dd56911a636055a.
- Earlier research PR #6: TYNDP parser and catchment/forecast experiments; unresolved source and commercial rights checks remain. Do not label the forecasting system trained.

- V79: 39d9936a09f3ed3a1fbc24a462440bb18dc66a3b; test https://github.com/LordOftheIdiot5/energy/actions/runs/43944443661. Optional 2D hillshade, not 3D.
- V80: EOX 2016 vintage (2016–17 acquisitions) CC BY 4.0, commercial public tiles with reasonable traffic and attribution. https://cloudless.eox.at/documentation/faq and https://cloudless.eox.at/license-non-commercial. Newer vintages require paid license; Norwegian detailed aerial photography remains rights-gated. No sale of raw imagery.

- V80: b1d820537ed4fac2543fa80b6fd5fe07380ad55d; browser real tiles (4 terrain, 7 satellite): https://github.com/LordOftheIdiot5/energy/actions/runs/43945619631.
- V81: NVE public Nettanlegg5 direct display, NLOD 1.0: https://data.norge.no/en/data-services/f109b2a7-1693-3c84-bd02-b06c0fad83f8/nettanlegg-utbygd-wms. No new asset inventory or raw geometry export; source scale and freshness limitations apply; distribution and underground land cables excluded.

- V81: e0e3a6660a7a3f2d02dfed315080ef02d8eaa1ad; validated real NVE images and flow data https://github.com/LordOftheIdiot5/energy/actions/runs/43947002157.
- V82: MET radar image (https://api.met.no/weatherapi/radar/2.0/documentation) and NVE GTS SWE (https://api.nve.no/doc/gridtimeseries-data-gts/). Uses explicit historical dates and sample grid coordinates, no catchment-wide estimates. Continuous forecast grids and basin aggregation require separate validated imports.

- V82 pilot: 4e5892784730a61aa6a75c104a4af4d9732f1bb7; real radar image and all five SWE cells dated 2026-11-14 validated; 14 regression tests passed: https://github.com/LordOftheIdiot5/energy/actions/runs/43948248753. First collector deployment still to verify.

- V82.1: bc4ca2eaca0398a317bb84f732302d5b3b069e72; five SWE markers and popup validation https://github.com/LordOftheIdiot5/energy/actions/runs/43948546527.
- V82.2: main atlas historical plant marker repair, grid scale guidance; validated and deployed; test real selected overlays together rather than just the basemap.

- V82.3: scale-aware grid overview from source-rendered imagery; detail scale limits, persistent on-map coverage/focus control, zoom regression test. No synthetic physical lines or override of provider render scale.

- V82.3: 01235eb5a5aebb1fb01f30375cebc310af442482; zoom persistence validated and deployed. https://github.com/LordOftheIdiot5/energy/actions/runs/43949944498.
- V84: client-side shareable profiles use original NVE plant IDs and WRI IDs, explicit registry/geography joins and zone-level reservoir context; no inferred asset output, shareholding or WRI current status.

- V84: f4c00acc7f8afb377bfda026fb3038b4840773e1; real plant profile validation https://github.com/LordOftheIdiot5/energy/actions/runs/43951765223.
- V85: fixed chronological benchmark, 5 research cells x 3 weather themes, persistence/seasonal/hydro-only ablation. Revised history only, no live forecast. See docs/V85-HYDRO-RESEARCH.md.

- V85 benchmark: https://github.com/LordOftheIdiot5/energy/actions/runs/43952611956. 17 tests passed, 15 series x 5,145 daily values, 1,295 test transitions. Weather beats all comparators in NO3 and NO4 only, marginally; interval coverage below 80% in all zones. Preserve results in docs/v85-benchmark-results.json; no operational forecast. Catchment-weighted weather, actual inflow/generation and forecast vintages remain required.

- V90 release consolidates V87 direct identity pilot, V88 chart improvements, V89 explicit seven-dataset catalogue/API service, V90 audit; excludes restricted FI/ES Energy-Charts rows. No operational forecasts, paid hosted API, or comprehensive parent/equity links claimed. See docs/V90-AUDIT.md.
