# V90.6f4 USA candidate: preliminary EIA-860M monthly generator inventory

- Official source: https://www.eia.gov/electricity/data/eia860m/
- Latest as of 20 November 2026: September 2026 workbook; released 23 October 2026.
- Exact workbook: https://www.eia.gov/electricity/data/eia860m/xls/september_generator2026.xlsx
- Reuse: U.S. EIA copyright/reuse guidance, public-domain government data with date-aware attribution: https://www.eia.gov/about/copyrights_reuse.php
- Preliminary estimates; do not mistake announced/proposed/retired generators for operating capacity or committed new construction.
- Unit identity is expected to combine plant ID and generator ID, but must be VERIFIED from workbook before importer implementation.
- Geographic coordinates must come from an approved plant location field or a validated official join with annual EIA-860 plant file. Never geocode city/state into a fake exact power station.
- Source audit outputs only worksheet names, small header samples, size and hash, without copying or republishing the full EIA workbook.
- After schema audit, implement generator-status-preserving model and exact join gates; only then stage a public sample and browser tests.
