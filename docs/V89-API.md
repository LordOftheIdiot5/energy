# V89 source-attributed API

Public GitHub Pages hosts the seven selected versioned JSON files and data/commercial-catalog-v1.json. These are open source-attributed datasets, not exclusive proprietary rights. Mixed prices, news, gas, commodities, market quotes and TYNDP research records are excluded from the export allowlist. Source licences and attribution must be preserved; no guarantee of fitness, source completeness or freshness.

Optional authenticated service: Python 3.12, standard library only. It is not deployed on GitHub Pages. Set a securely generated environment secret (minimum 32 chars), then run python scripts/dataset_api.py --data /path/to/energy/data --port 8788. It binds to loopback only. Provision a TLS reverse proxy, separate API credentials, quotas, monitoring, billing, process supervision, backups and security review before production. Never place the key in a public file or client-side JS.

GET /v1/catalog and GET /v1/datasets/hydro-weekly?offset=0&limit=100 accept Authorization: Bearer <key>. Max 200 records per page; returns next_offset, original source date, source SHA256, licence, attribution and rows. In-process 60 requests/minute across the one service key; not a distributed commercial quota or billing system. HTTP 401/404/429 states are explicit. No arbitrary path or URL parameters. The static public catalog remains available separately.
