# V90 release audit and remaining gates

This is a versioned release candidate, not certification of every dataset.

- V83: TYNDP workbook project-level redistribution permission remains pending (PR 22).
- V85: true historical test saved; marginal weather lift and undercoverage. Operational forecasts not released.
- V86: corrected source unit mismatch; actual licensed NO2 data complete 2022–2025; monthly median beats regression on MAE. Historical summary and tested code integrated, no operational forecast.
- V87: exact NVE owner orgnr 910261525 with issuer's stated orgnr and Euronext AFK/ISIN disclosure; Stockwatch reference-directory link. No inferred corporate parent, equity percentage, or market data rights. Other owners explicitly unmatched.
- V88: shared time chart now handles larger series without spread-limit failure and binary-search pointer lookup; plant profiles display regional history and hydro research shows actual benchmark comparisons. Existing market and weather charts retained; no claim every visual migrated.
- V89: seven source-attributed open files and a versioned public manifest; loopback bearer service, allowlisted paths, pagination and per-process throttling. No payment or hosted auth yet.
- V90: app and data tests, syntax, local desktop/mobile browser routes, exact identity, dataset API smoke and source checks. Initial V90 Actions run 43955547548 passed 21 Python tests, 7 datasets, direct issuer link, 12 workspace routes on each desktop/mobile viewport and no page errors; also passed actual map zoom and plant profile checks. Final integrated run required.
- Price rights remediation: block restricted FI/ES Energy-Charts feed, enforce explicit open license on new data and stale fallback; 31-second source pacing and Retry-After handling. Existing allowed-zone snapshot rows remain previous display records until refresh. Nordic reseller feeds, GB market index, quote, gas/news/licence scope require further review; do not bundle them commercially. 
- Known gaps: high-resolution aerial imagery, genuine 3D terrain, European physical transmission database, comprehensive weather grids, actual hydrological inflow/generation, archived issue-time features, crawlable individual pages, production secure API and billing, end-to-end rights review. 
