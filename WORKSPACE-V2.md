# Energy workspace V2 preview

Stockwatch-inspired energy dashboard shell, persistent light/dark theme, section navigation, mobile drawer, zone filter, and overview cards derived from the existing published snapshot. No collector or data contract changes. Existing source charts and methodology are retained. Duplicate weather/news container IDs corrected. The source view describes availability rather than promising live upstream health.

## Validation

- Confirm all existing energy panels and source guide render with the current data/energy.json.
- Test at 390px, 768px, 1440px in dark/light modes, keyboard navigation, search, and zone filtering.
- Test unavailable, stale, missing optional gas, and fresh data. Check the published timestamp against the actual feed.
- Run python tests/test_payload.py against the current snapshot. Validate independently before promotion to main. No workflow changes.
