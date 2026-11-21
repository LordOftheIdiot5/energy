# Nordl Energy — current workplan and handoff

**Canonical next-work checkpoint:** 2026-11-21 (Europe/Oslo).  
**Production:** https://energy.nordl.dev/  
**Repository:** https://github.com/LordOftheIdiot5/energy  
**Current latest confirmed production merge:** [PR #93](https://github.com/LordOftheIdiot5/energy/pull/93), commit `a189d82cb7139ce32fcce0dd220a4c9c4d364e06`.  
**Broader product roadmap:** [docs/ENERGY-MASTER-ROADMAP-V91.md](docs/ENERGY-MASTER-ROADMAP-V91.md).  
**Detailed global atlas architecture and source gates:** [docs/GLOBAL-INFRASTRUCTURE-ATLAS.md](docs/GLOBAL-INFRASTRUCTURE-ATLAS.md).

> This document is the **single current execution checkpoint**, not a claim that all V90–V91 proposals are implemented. Every completed label below is backed by an actual GitHub check. Recheck repository state, PRs, runs, and the live site on every new session: this snapshot may become stale.

## How to resume — every session

1. Read **this file first**; read the master roadmap and the detailed atlas plan for dependencies. Follow [AGENTS.md](AGENTS.md).
2. Inspect `main`, the latest GitHub Actions **Deploy** and **production browser smoke** results, and all relevant open PRs. Do not assume a merge means a successful deployment.
3. Start with the **first unblocked item** under "Next work in priority order." Preserve the current site while researching a new source on a separate branch.
4. Work in small PRs. For each source validate terms, effective date, stable IDs, geography, duplicates, status, capacity/unit semantics, attribution and commercial redistribution before release.
5. Run source/rights tests, build the allowlisted public artifact, and browser-test real rendered data on desktop **1440 px** and mobile **390 px** (plus 1024/360 px as needed). Check coexistence with earlier map layers; preserve map fallback.
6. After merging, verify the actual **production deployment** and live GitHub Playwright tests. Record linked PR, exact Actions run, observed results, warnings and next task **in this file**. If incomplete, mark `In progress` or `Blocked`; never claim done.
7. Keep this as the authoritative up-to-date status checkpoint; longer-term goals stay in the master roadmap. Do not start a second divergent task list.

## Verified releases and current baseline

| Phase | Observed status (2026-11-21) | Evidence / important qualification |
| --- | --- | --- |
| V90.6 watchdog recovery | **Operational at last log** | On 2026-11-20 22:47 CET, tail reported `age=1`, `failures=0`, `action=none`, no diagnostics after Worker `46dd2b16-bf6a-4bd5-bad9-614a40afe5ff`. Continue monitoring; one healthy tick does not establish long-term reliability. |
| V90.6f4 UK REPD renewable projects | **Live, browser validated** | 14,388 mapped source records, Oct 2026; [PR #81](https://github.com/LordOftheIdiot5/energy/pull/81), [production tests](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697175). Status is original planning status, not verified construction. |
| V90.6f4 US EIA-860M generators | **Live, browser validated** | 40,048 geocoded units / 40,163 source rows, Sep 2026; separate operating, planned, retired and canceled/postponed inventories. [PR #86](https://github.com/LordOftheIdiot5/energy/pull/86), [production tests](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697126). Nameplate capacity is not measured generation. |
| V90.6g NACEI North American gas/LNG/refineries | **Live, browser validated** | 1,461 Aug **2017** reference points: 1,278 gas processing, 15 LNG, 168 refineries; 141 refinery names missing at source. [PR #90](https://github.com/LordOftheIdiot5/energy/pull/90), [production tests](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697148). Not current operating/ownership data. |
| V90.6g2 GEM global transmission pipelines | **Live, browser validated** | 4,246 Nov **2025** records; 3,921 simplified mapped routes, 325 without routes. CC BY 4.0; original statuses kept. [PR #93](https://github.com/LordOftheIdiot5/energy/pull/93), [production tests](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697166). Routes can be estimated, never survey grade. |
| Production deployment / existing maps | **Passed for PR #93** | [Deploy](https://github.com/LordOftheIdiot5/energy/actions/runs/44846620018), [production map smoke](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697198), [atlas delivery smoke](https://github.com/LordOftheIdiot5/energy/actions/runs/44846697363). Recheck after every subsequent release. |
| Overall V90.1 commercial readiness | **Partial / conditional** | Code and browser checks may pass; commercial redistribution rights, full forecasting claims, all historical coverage and paid API availability remain separately gated. Passing CI is not commercial clearance. |

Avoid summing these counts as unique assets: datasets can overlap, and records are at different granularities/vintages.

## 2026-11-21 active checkpoint — V91-P0 visitor recovery

**In progress, not deployed.** Branch `feature/v91-p0-bounded-snapshot-retry-20261121` adds a 12-second timeout to the initial public snapshot request, preserves the last successful snapshot on subsequent request failure, exposes a manual retry and official market-source link on first-load failure, and replays early failure events to deferred homepage modules. A new Playwright regression runs against the allowlisted public build at 1440 and 390 CSS px, testing failed initial requests and recovery. **CI result and production/browser acceptance pending**; do not mark V91-P0 complete until the failed, normal and slow-source scenarios and production smoke are verified. No new market data, licence permissions or atlas layers are introduced.

## Next work in priority order

- [ ] **V91-P0 — Visitor-first data visibility and fallback acceptance (2026-11-21 triage).** Before adding another low-priority atlas layer, verify *rendered* Energy home/monitor at 390/1440 CSS px under normal, slow and failed source requests; measure whether any `Loading published energy data…`, price/NO3, reservoir or Fingrid placeholder stays unresolved. Make the latest already-authorized observation or specific dated unavailable reason useful in the first fold, with its zone, unit, source date and next action; never generate fake values. Check no broken map/base navigation, add browser regression and a real production smoke. This is a **quality gate and time-boxed P0 investigation**, not licence approval, a new version stream or cancellation of the source/archive queue. Long-term specifics: [V91 visitor-quality assessment](docs/ENERGY-MASTER-ROADMAP-V91.md#2026-11-21-visitor-quality-assessment--align-external-review-to-existing-phases).
- [ ] **V90.6g3 — Newer global LNG and gas update source review.** Obtain the publisher's latest authorized LNG terminal extract (the October 2026 GEM release was identified; reconfirm latest release), inspect terms and specific download permissions; separately investigate the latest GGIT pipeline release. Do not bypass a publisher form or represent November 2025 pipeline records as 2026 current. Record changed/removed assets with dated evidence, not by name-only fuzzy merges.
- [ ] **V90.6g3 — Versioned source and change history.** Introduce a source/vintage registry with stable native IDs, checksum snapshots, effective release dates, normalized countries, statuses and explicit missing coordinates. Store verified historic versions in private R2/D1 as appropriate; publish only rights-cleared projections. Add point-in-time diffs (new, changed, retired, uncertain) with evidence. Validate storage and restoration, cost, and single-writer safety.
- [ ] **V90.6g4 — Pipeline map performance & UX audit.** Measure real GPU route layer latency, memory, pan/zoom across 390/1024/1440 px and mixed US/UK/NACEI overlays. Add viewport-filtered/vector-tiled rendering or other optimization if measured necessary; keep text search, original status filtering, inspector and fallback fully functional. Test dateline crossing, disabled layers and no-route records. No unverified engineering GIS claims.
- [ ] **V90.6g5 — Verified asset-to-company intelligence.** Start with Sodir/NVE/EIA issuer/owner identifiers and legal-entity relationships. Include dated direct/indirect ownership and confidence/evidence. Link confirmed companies to [Stockwatch](https://stocks.nordl.dev/) without inferring revenue, equity exposure or current operator from spatial proximity, asset capacity or historical owner names.
- [ ] **V90.6h — Remaining atlas source-gated expansion.** More global LNG/refineries, dams and hydrological topology, transmission/power projects, shipping ports, minerals/industrial sites and data centres, with explicit provenance, geographic precision, rights and coverage. Keep OSM/ODbL separate and do not ingest PHMSA restricted NPMS GIS.
- [ ] **V90.7 — Forecast model laboratory.** Only verified as-of input vintages, time-series backtests, baseline comparison and calibrated uncertainty; current forecasting research is not an operational forecast.
- [ ] **V90.8 — Energy × Stockwatch relationship graph.** Evidence-based upstream/downstream company and energy-asset links with effective dates and transparent data lineage.
- [ ] **V90.9 — Public Data Hub and potential paid managed API.** Dataset search, source dates, export/schema examples and version history first; scoped authentication, quotas, operational SLAs and commercial pricing only after rights, demand and live service readiness.
- [ ] **V91 — Integrated audit.** Navigation and visual simplicity; dark/light and mobile UX, no empty or stale-unlabeled data, live data/collector resilience, dataset continuity, map visibility at all zooms, accessibility, SEO, licensing, privacy and traffic.

### Parallel visitor experience quality gate (cross-cutting, not a new version)

- [ ] Integrate the [2026-11-21 visitor-quality assessment](docs/ENERGY-MASTER-ROADMAP-V91.md#2026-11-21-visitor-quality-assessment--align-external-review-to-existing-phases) with V90.3b/V90.6/V91 acceptance: verify initial `Loading` states actually resolve in browser, show accurate last-available dated snapshots during source failure, keep map overlays discoverable, and link relevant data/tool journeys. User-provided review is a hypothesis, not a measured failure. Do not reorder the first unblocked source-rights tasks without fresh evidence.

### Parallel maintenance / unresolved branches

- [ ] Review older open rendering/atlas PRs [#68](https://github.com/LordOftheIdiot5/energy/pull/68), [#69](https://github.com/LordOftheIdiot5/energy/pull/69) and [#70](https://github.com/LordOftheIdiot5/energy/pull/70) against current `main`. Rebase/close only after checking their actual changes and redundant regressions; **do not blindly merge**.
- [ ] Recheck outstanding research/licence PRs and data collection failures before marking them resolved. Preserve rights restrictions for day-ahead market, third-party financial and electricity network data.
- [ ] Verify watchdog Telegram notifications and GitHub dispatch independently when a genuine error occurs; avoid manufacturing production faults to trigger alerts.
- [ ] Continue official-source freshness and archival QA; retain last-known values with timestamps, never silently invent live values.

## Non-negotiable guardrails

- Source vintage, rights, identity, units, record granularity, geography and status **must be visible and testable**. Historical `operating` statuses are **source-reported**, not proof of present operation.
- Use no invented route geometry, current status, prices, forecasts, capacities, ownership or missing observations. Unknown is not zero.
- Commercial/public redistribution and private research are separate decisions. Data can appear in the private research repository without being licensed for public or paid API redistribution.
- No credentials or unrestricted private raw feeds in the built public artifact. Preserve existing atlas and data pages and other Nordl tools.
- Keep optional overlays off until explicitly enabled; preserve base map, fallback and previously working UI.
- Do not overwrite a failing release checkpoint with "passed" until real production browser checks succeed.

## Update template (append to this file when work advances)

```md
### YYYY-MM-DD — V... checkpoint
- Goal:
- Changed: PR #... / commit ...
- Data release & rights: ...
- Tests: Actions ... (result), desktop/mobile ...
- Production: Deploy ... (result), live smoke ... (result)
- Known issues/blocked: ...
- Next first unblocked work: ...
```

## Resume prompt

> Open `WORKPLAN.md` in `LordOftheIdiot5/energy`, verify the latest PRs/Actions/live site against it, then perform the first unblocked task. Preserve the roadmap, data-source rights and existing functionality; finish with actual test evidence and update `WORKPLAN.md`.

