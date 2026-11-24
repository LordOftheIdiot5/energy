# Repository work instructions — Nordl Energy

Before proposing or changing code, **read [WORKPLAN.md](WORKPLAN.md)** for the latest validated checkpoint and first unblocked task; then [docs/ENERGY-MASTER-ROADMAP-V91.md](docs/ENERGY-MASTER-ROADMAP-V91.md) and [docs/GLOBAL-INFRASTRUCTURE-ATLAS.md](docs/GLOBAL-INFRASTRUCTURE-ATLAS.md) for strategy and dependencies.

The workplan is the **single source of truth for execution status**. Other roadmaps are historical/long-range references. When a change is validated, update WORKPLAN.md **in the same PR or a immediately following checkpoint PR**, including release, source/rights, PR, tests, production Deploy and live browser evidence, blockers and next priority. Do not mark production complete based only on commit/merge/staged tests.

On resumption, first check current `main`, open PRs and recent Actions. Do not assume that this static snapshot reflects newer work. Prioritize the first unblocked item while preserving all earlier maps, features and existing public endpoints.

Never invent missing values or asset geometry. Distinguish source vintages, planned vs operational/retired status, observations vs estimates/forecasts and private collection vs public/commercial redistribution rights. Keep credentials out of public artifacts. Run real-source schema tests, allowlisted public builds and responsive desktop/mobile Playwright before merging; verify the deployed site afterwards.

For feature-specific instructions, inspect existing tests, workflow files and the relevant source-specific documentation. Follow existing data-release gates and keep changes auditable.
