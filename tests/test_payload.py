"""Refuse to publish a payload that would render a broken or lying page.

The fetch runs unattended every hour. Without this, a source that starts
returning empty arrays, or prices in the wrong units, would be committed and
published with nothing to stop it - and a page that is confidently wrong is
worse than one that is obviously down.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "energy.json"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    if not DATA.exists():
        print(f"no payload at {DATA}")
        return 1
    d = json.loads(DATA.read_text(encoding="utf-8"))

    zones = d.get("zones") or []
    check("has zones", len(zones) >= 4, f"{len(zones)} zones")

    for z in zones:
        today = z.get("today") or {}
        local = today.get("local") or []
        eur = today.get("eur") or []
        check(f"{z.get('zone')} has 24 hours", len(local) == 24, f"{len(local)}")
        check(f"{z.get('zone')} has EUR alongside", len(eur) == len(local))
        # Nordic power has been negative and has been absurd, but never both
        # at once. These bounds catch a unit change, not a market event.
        if local:
            check(f"{z.get('zone')} prices plausible",
                  all(-5 < v < 50 for v in local),
                  f"{min(local):.3f}..{max(local):.3f} per kWh")

    eu = d.get("europe") or []
    check("has European zones", len(eu) >= 6, f"{len(eu)} zones")
    for z in eu:
        c = z.get("cents") or []
        check(f"{z.get('zone')} has prices", len(c) >= 20, f"{len(c)} points")
        # Euro cents per kWh. Europe has seen negative prices and has seen
        # 70c in a crisis; outside that range the unit has changed, not the
        # market.
        if c:
            check(f"{z.get('zone')} range plausible",
                  all(-20 < v < 120 for v in c), f"{min(c)}..{max(c)}")

            # Zeros have to be judged by SHAPE, not by count. The Elexon
            # two-provider bug alternated real,0,real,0 - many one-point
            # runs. A genuine price collapse is one long block, which
            # Germany does on windy Sundays: on 2026-10-25 DE-LU sat at
            # exactly 0 EUR/MWh for 48 of 100 quarter-hours and still
            # peaked at 71.61 that evening. Counting alone called that real
            # day a bug and blocked publishing for sixteen hours.
            #
            # Tiny prints either side of zero (-0.01, +0.01 EUR/MWh) belong
            # to the same collapse, so near-zero is a band rather than an
            # equality test - otherwise they shred one real run into nine
            # and it reads as dropouts.
            # The run ceiling is 8, not 3. The bug it guards against put a
            # zero between every real price - 48 runs in a 96-point day - so
            # 8 still catches it six times over. Real markets fragment more
            # than 3: on 2026-10-25 France ran 32/100 near zero across 6
            # runs and Denmark 23/100 across 6, both legitimate. A ceiling
            # of 3 would have failed either the moment it crossed 40%.
            near = [abs(v) < 0.01 for v in c]
            zeros = sum(near)
            runs = sum(1 for i, n in enumerate(near)
                       if n and (i == 0 or not near[i - 1]))
            dead = zeros >= len(c) * 0.95        # nothing traded all day
            shredded = zeros >= len(c) * 0.4 and runs > 8
            check(f"{z.get('zone')} zeros are a collapse, not dropouts",
                  not (dead or shredded),
                  f"{zeros}/{len(c)} near zero in {runs} run(s)")

    res = (d.get("reservoirs") or {}).get("zones") or {}
    check("has reservoirs", len(res) >= 4, f"{len(res)} areas")
    for k, v in res.items():
        check(f"{k} fill is a fraction", 0 <= (v.get("fill") or -1) <= 1,
              str(v.get("fill")))

    g = d.get("grid") or {}
    check("has a generation mix", bool(g.get("mix")), str((g.get("mix") or {}).get("hydro")))
    flows = g.get("flows") or []
    check("flows carry a direction, not a minus sign",
          all(f.get("mw", 0) > 0 for f in flows), f"{len(flows)} links")

    wx = d.get("weather") or {}
    check("has weather", len(wx) >= 6, f"{len(wx)} zones")

    com = d.get("commodities") or []
    check("has commodities", len(com) >= 8, f"{len(com)} instruments")
    check("every commodity has a sparkline",
          all(len(c.get("spark") or []) >= 2 for c in com))

    # Gas storage is optional - it needs a GIE key - but must be coherent
    # when present. A silently empty panel would read as "storage is zero".
    gas = (d.get("gasStorage") or {}).get("countries") or []
    if gas:
        check("gas storage percentages are percentages",
              all(0 <= (c.get("fullPct") or 0) <= 100 for c in gas),
              f"{len(gas)} countries")

    fuel = d.get("fuel") or {}
    fuels = fuel.get("fuels") or []
    check("has fuel breakdown", len(fuels) >= 1, f"{len(fuels)} fuels")
    for f in fuels:
        total = f.get("modelledTotal") or 0
        parts = sum(f.get(k) or 0 for k in
                    ("productNok", "roadTax", "co2Tax", "vat"))
        # The whole point of the panel is that the parts add up. If they
        # drift apart, the model is lying about its own arithmetic.
        check(f"{f.get('key')} parts sum to the total",
              abs(parts - total) < 0.02, f"{parts:.2f} vs {total:.2f}")
        check(f"{f.get('key')} is a plausible pump price",
              5 < total < 60, f"{total} NOK/l")

        # When the observed anchor is present it must be a believable pump
        # price too, or the comparison is noise against noise.
        obs = f.get("observedNok")
        if obs is not None:
            check(f"{f.get('key')} observed is plausible", 5 < obs < 60,
                  f"{obs} NOK/l ({f.get('observedMonth')})")

    fr = d.get("france") or {}
    if fr:
        check("French availability is a percentage",
              0 < (fr.get("availabilityPct") or 0) <= 100,
              f"{fr.get('availabilityPct')}%")

    mk = d.get("market") or {}
    margins = mk.get("margins") or []
    check("has margins", len(margins) >= 2, f"{len(margins)} spreads")
    for sp in margins:
        # A margin is a difference of two real prices; if it has exploded, a
        # unit has changed somewhere rather than the market having moved.
        check(f"{sp.get('key')} is sane", abs(sp.get("value") or 0) < 100000,
              f"{sp.get('value')} {sp.get('unit')}")
        check(f"{sp.get('key')} shows its working", len(sp.get("parts") or []) >= 2)
    coh = mk.get("cohorts") or []
    check("has cohorts", len(coh) >= 2, f"{len(coh)} groups")
    # The guard is the point of the correlation section; without the counts
    # it is just a list of suggestive numbers.
    check("correlations state what was tested",
          mk.get("tested") is not None and mk.get("expectedByChance") is not None,
          f"{mk.get('tested')} tested, ~{mk.get('expectedByChance')} by chance")
    check("survived count is not the truncated one",
          (mk.get("survived") or 0) >= len(mk.get("correlations") or []),
          f"{mk.get('survived')} survived, {len(mk.get('correlations') or [])} shown")

    # News is allowed to be empty - it is the least important part and the
    # most fragile - but it must not be malformed when present.
    news = d.get("news") or []
    check("news entries are well formed",
          all(n.get("title") and n.get("url") for n in news),
          f"{len(news)} stories")

    print()
    if failures:
        print(f"FAILED: {len(failures)}")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("payload OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
