import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from asset_reference import normalize,aggregate
class AssetTests(unittest.TestCase):
    def test_normalize(self):
        r={"country":"NOR","gppd_idnr":"a","name":"X","longitude":"10","latitude":"60","capacity_mw":"20","primary_fuel":"Hydro"}
        self.assertEqual(normalize([r])[0]["geometry"],[10,60])
        self.assertEqual(normalize([{**r,"latitude":"nan"}]),[])
        with self.assertRaises(ValueError):normalize([r,r])
    def test_owner(self):
        r={"id":1,"owner":"A","owner_orgnr":"123456789","capacity_mw":12,"zone":"NO1"}
        d=aggregate({"generated":"test","rows":[r,{**r,"id":2,"capacity_mw":None}]})
        self.assertEqual(d["rows"][0]["reported_capacity_mw"],12)
        self.assertEqual(d["rows"][0]["plant_ids"],[1,2])
        self.assertEqual(d["rows"][0]["capacity_records"],1)

class CollectorRegressionTests(unittest.TestCase):
    def test_european_prices_survive_plant_refresh(self):
        import json
        import tempfile
        from contextlib import ExitStack
        from unittest.mock import patch
        import fetch
        import asset_reference
        from datetime import date,datetime,timezone
        from delivery_prices import bounds,european_day
        day=date(2026,11,17);a,b=bounds(day)
        series=european_day({"unix_seconds":list(range(int(a.timestamp()),int(b.timestamp()),3600)),"price":[50]*24},day)
        prices=[{**series,"zone":"DE-LU","name":"Germany / Luxembourg","country":"DE","unit":"eurocent/kWh","priceSource":"Energy-Charts.info / SMARD","sourceUrl":"https://api.energy-charts.info/price","licenseInfo":"CC BY 4.0","retrievedAt":datetime.now(timezone.utc).isoformat(),"stale":False}]
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            out = root / "data" / "energy.json"
            stack.enter_context(patch.object(fetch, "ROOT", root))
            stack.enter_context(patch.object(fetch, "OUT", out))
            for name, value in {
                "collect_spot": [], "collect_reservoirs": {},
                "collect_europe": prices, "collect_market": {},
                "collect_gas_storage": {}, "collect_fuel": {},
                "collect_france": {}, "collect_grid": {},
                "collect_weather": {}, "collect_commodities": [],
            }.items():
                stack.enter_context(patch.object(fetch, name, return_value=value))
            for target in (
                "shared_energy.refresh_shared", "hydro_extended.refresh_plants",
                "hydro_extended.refresh_geometry", "energy_geography.collect_all",
                "asset_reference.owners", "economic_reference.refresh",
                "news.collect", "hydro_archive.append_snapshot",
                "economic_reference.archive_weather", "hydro_validation.refresh",
                "weather_geography.refresh",
            ):
                stack.enter_context(patch(target, return_value=[]))
            plant_refresh = stack.enter_context(patch.object(asset_reference, "europe"))
            self.assertEqual(fetch.main(), 0)
            plant_refresh.assert_called_once_with(out.parent)
            from publication_policy import project_snapshot
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["europe"], project_snapshot({"generated":"test","europe":prices})["europe"])
            for name in ("collect_spot","collect_market","collect_fuel","collect_france","collect_grid","collect_commodities"):
                getattr(fetch,name).assert_not_called()
            previous = out.read_bytes()
            fetch.collect_europe.return_value = lambda: None
            with self.assertRaises(TypeError):
                fetch.main()
            self.assertEqual(out.read_bytes(), previous)
