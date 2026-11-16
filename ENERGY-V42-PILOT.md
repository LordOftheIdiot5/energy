# V42.1 experimental catchment weather
NVE GTS supports area queries using EPSG:25833 polygon rings. This pilot uses an official NVE layer 8 OBJECTID and limits requests to small catchments (<=20 km²), 1–31 historical days, three themes (rr, swe, tm), and <=100 returned cells per theme. Missing days are null. Source attribution and methodological limitations travel with the output. See https://api.nve.no/doc/gridtimeseries-data-gts/.

Run offline fixtures:
    python -m unittest discover -s tests -p test_catchment_weather.py

After selecting an actual small catchment OBJECTID from the NVE registry, replace ID in:
    python scripts/catchment_weather.py --catchment-id ID --start 2025-01-01 --end 2025-01-31 --output /tmp/catchment-weather-pilot.json

This is deliberately not on the hourly collector or the public catalog: the live GTS response, theme units and ArcGIS field schema must be verified before publication. The test uses the published example schema, not a captured live response. Cell means are not exact area-weighted zonal statistics. Historical revised values are not issue-time weather forecasts. Next: validate actual coverage; identify stable catchment identity; aggregate zones without double-counting upstream/downstream catchments; version observed and forecast vintages separately; compare against the hydro baseline using rolling-origin splits.
