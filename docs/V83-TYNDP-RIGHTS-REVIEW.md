# V83 European infrastructure — source and rights gate

Review date: 2026-11-16.

## Current findings

- ENTSO-E's 2 April 2026 announcement identifies 199 transmission projects and 69 storage projects in TYNDP 2026. This is a proposed/assessed portfolio, not an operating-asset registry.
- Earlier private parser validation (PR #6, scripts/tyndp_portfolio.py) found 365 investments and two unresolved border references. These are research results, not publication clearance.
- The September 2026 promoter update window means the factual workbook may differ from final project sheets. Treat dates and project stages as reported, not independently confirmed.
- ENTSO-E general site terms restrict commercial reuse unless otherwise permitted. The separately licensed TYNDP Scenarios 2026 market data explicitly permits CC BY 4.0 reuse; this exception does not establish the same rights for the project workbook, project-sheet content or mapped geometries.

## Evidence URLs
- Portfolio announcement: https://www.entsoe.eu/news/2026/04/02/tyndp-2026-project-portfolio-expands-further-to-199-transmission-and-69-storage-project/
- General terms: https://www.entsoe.eu/about/legal-and-regulatory/disclaimer/
- Scenarios data license (separate dataset): https://2026.entsos-tyndp-scenarios.eu/download/
- Promoter updates: https://tyndp.entsoe.eu/news/review-and-update-your-tyndp-2026-project-information
- Workbook: https://eepublicdownloads.blob.core.windows.net/public-cdn-container/tyndp-documents/TYNDP2026/20260203_TYNDP2026_project_portfolio_final.xlsx

## Release gates
1. Obtain explicit written permission or dataset-specific open license for project facts and geometry, including commercial displays, downloads/API and derivative datasets where desired.
2. Reconcile the two unmatched border references without inventing coordinates.
3. Keep project and investment IDs distinct; version source date and revision; distinguish proposal, construction and operational status.
4. Store geospatial origin and precision, use verified coordinates only; source-linked records without geography remain searchable but unmapped.
5. Preserve existing curated six-project dataset while rights review is unresolved.
6. Keep raw workbook, extracted rows and maps out of public repository/deploy artifacts until cleared; no data export sale on the strength of website visibility alone.

## Permission request draft (not sent)
To: tyndp@entsoe.eu
Subject: Permission to reuse TYNDP 2026 project and investment data

Hello,

We operate Nordl Energy (https://energy.nordl.dev/), an energy research platform. We would like to incorporate the TYNDP 2026 project portfolio and investment data in a source-attributed European infrastructure explorer.

Could you confirm the applicable license or grant permission for:
- commercial website display of normalized factual project and investment fields;
- mapped investment locations or route geometries, if available through an approved data feed;
- redistribution through CSV/JSON downloads and a commercial API;
- periodic retrieval and storage of versioned project updates?

We will distinguish reported project stages from operating assets, retain source links and dates, and use the attribution you specify. Please indicate any exclusions, third-party rights, usage restrictions, or recommended API/official download endpoint. We understand that the separate TYNDP Scenarios data are openly licensed, and are seeking confirmation specific to the project portfolio.

Thank you,
Nordl Energy
