# energy.nordl.dev

What sets the price of energy in the Nordics, and why.

## What it shows

- **Day-ahead power by zone** — all nine Nordic bidding zones on one shared
  axis. The axis is euro cents, not local currency: a Norwegian krone and a
  Swedish krona are different rulers, and putting them side by side would
  invent a difference that is not there.
- **The day, hour by hour** — with the cheapest three-hour run marked, which
  is the window worth moving a car charge into. Tomorrow appears once Nord
  Pool publishes, around 13:00 CET.
- **Hydro storage against normal** — fill compared to the median for the same
  week of the year since 1995. A reservoir at 52% means nothing on its own;
  52% against a normal of 84% is why next February will be expensive.
- **Fuels, carbon and currency** — what the marginal plant burns, what it pays
  to emit, and the exchange rates between the price that is set and the bill
  that is paid.
- **Being built, laid and switched on** — projects and machines rather than
  share prices, searched by topic and de-duplicated.

## Sources

All keyless and public, which is the only way this still works in a year:

| What | Where |
|---|---|
| Nordic spot prices | hvakosterstrommen.no (NO), elprisetjustnu.se (SE) |
| Hydro reservoirs | NVE, weekly, back to 1995 |
| Fuels, carbon, FX | Yahoo Finance |
| News | Google News RSS, by topic |

Prices exclude grid rent, taxes and VAT, so a bill is always higher than the
number here. What moves is what matters.

## Running it

```bash
python scripts/fetch.py      # writes data/energy.json
python tests/test_payload.py # refuses to publish a payload that would lie
python scripts/news.py       # news on its own, for tuning the filters
```

The hourly fetch runs on GitHub Actions and publishes its own results — a push
made with the built-in `GITHUB_TOKEN` does not trigger other workflows, so a
deploy job waiting for that push would never fire.
