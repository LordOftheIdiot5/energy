# US generator normalization, September 2026

- Source file: https://www.eia.gov/electricity/data/eia860m/xls/september_generator2026.xlsx
- Source workbook SHA-256: bcef74e1af991680731aeecfda967f5950db4ce739bb584edd8b8774c7e6da17
- Source page and attribution: https://www.eia.gov/electricity/data/eia860m/
- EIA government-data reuse statement: https://www.eia.gov/about/copyrights_reuse.php
- Source tabs: Operating, Planned, Retired, Canceled or Postponed; separately Operating_PR, Planned_PR, Retired_PR.
- Preserve record identity (source tab, EIA plant ID, generator ID) and exact status string. A generator in Planned is not proven operational, and a generator in an operating inventory can be listed as standby/backup.
- Decline rows missing explicit EIA coordinates; do not invent coordinates using city, state, or county.
- Generator electric nameplate MW is not measured generation, operating generation, or confirmed net capacity.
- The review artifact must pass actual-source schema, identity uniqueness, geolocation, and coverage gates before being eligible for map publication.
