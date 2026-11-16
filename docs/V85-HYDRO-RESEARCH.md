# V85 research protocol

Target: next consecutive ISO-week reservoir fill, separately for NO1–NO5. Target is a storage percentage, not a plant generation prediction. All results are percentage-point MAE, with test counts and empirical interval coverage.

Use existing NVE storage archive and the five existing seNorge research-cell coordinates. Retrieve precipitation, temperature, and SWE 2011-12-01 to 2025-12-31, validate dates, units, coordinates and missing flags, preserve source hashes. Features are lagged 14–8 days before the origin Monday; no target-week realized weather. The unweighted average over five cells is a research feature only, not an area or basin mean.

Fixed chronological train 2012–17; interval calibration 2018–20; test 2021–25. Ridge hyperparameter fixed in advance. Compare persistence, historical seasonal change, same regression without weather, and regression with lagged weather. No target crosses a split. Do not optimize hyperparameters against the test period. Report even if worse. Require at least 200 training and test transitions, 100 calibration transitions.

The archive contains revised observations and the MET forecast-vintage archive is too short. This is a retrospective experiment, not an as-of operational forecast. Actual issue-time meteorological forecast retrieval, NVE release dates/revisions, catchment weighting, observed inflow and generation are still required before production prediction. No plant-level forecast or public forecast numbers.

Sources: https://api.nve.no/doc/gridtimeseries-data-gts/ (NLOD), https://api.nve.no/doc/magasinstatistikk/; no raw source arrays added to public site. Summary artifact and log from CI; evaluate actual outcomes before deciding next model.
