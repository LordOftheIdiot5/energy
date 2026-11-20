# International infrastructure project source — UK REPD pilot

- Official source: https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract
- Released: 13 November 2026, REPD October 2026 (Q3) CSV, approximately 4.98 MB.
- Licence: UK Open Government Licence v3.0 (commercial reuse subject to attribution).
- Project lifecycle: explicit REPD development statuses; **not** independently verified construction or generation.
- Geography: original UK British National Grid X/Y to WGS84 using EPSG:27700; no geocoding guessed.
- Public projection: only stable project ID, name, technology, GB country/region/county, original planning status, reported electric capacity, source updated date and point.
- Provenance: source URL, exact release month, SHA-256 of source bytes, row/withheld counts, OGL attribution.
- Safeguards: no publish from this PR; real-source CI must pass and output an artifact for inspection before any frontend or catalog promotion; reject duplicates, unknown schema, major count regression, corrupt coordinates and improbable MW.
- Missing coordinates: withhold record rather than invent an approximate location; Northern Ireland not asserted to use British National Grid.
- Follow-up source: US EIA-860M; plan separate schema as generator units rather than UK planning-project applications.

No staged or live project-count increase can be claimed until official-source download, transformation and publication validation have passed.
