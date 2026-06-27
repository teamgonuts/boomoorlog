---
name: tree-to-zipcode
description: >-
  Map GPS coordinates (latitude/longitude) to Dutch postcodes — PC6 (e.g.
  1011HL) and PC4 (e.g. 1011) — by point-in-polygon against official CBS
  Postcode-6 boundaries. Use this whenever the user has a CSV of points with
  lon/lat columns (especially Amsterdam trees) and wants a postcode / ZIP code
  per row, or wants to enrich a dataset with postcodes. Trigger on requests like
  "what ZIP code is this lat/long in", "add a postcode column", "map trees to
  ZIP codes", or "which Amsterdam postcode does each tree belong to".
---

# Tree → ZIP code (Dutch postcode mapping)

Assign a Dutch postcode to every point in a CSV by testing which **CBS
Postcode-6 polygon** contains the point. PC4 is derived as the first four
characters of PC6, so one dataset yields both columns and they are always
consistent.

The boundary polygons come from the **PDOK CBS Postcode6 OGC API** (official,
free, no key). They are downloaded once for the requested bounding box and
cached to a local GeoJSON, so every later run is fully offline.

## When to use
- A CSV already has `longitude` / `latitude` columns (WGS84). No geocoding API
  calls per row — we do a local spatial join, which is fast (~seconds) and
  works for hundreds of thousands of points.
- Default bbox covers the Amsterdam municipality. For other areas, pass `--bbox`.

## Workflow
1. Ensure `shapely` is installed (`pip3 install shapely`). `numpy` comes with it.
2. Run the script:
   ```
   python3 .claude/skills/tree-to-zipcode/scripts/map_to_postcode.py \
       data/amsterdam_trees.csv data/amsterdam_trees_zip.csv \
       --unmatched-csv data/trees_unmatched.csv
   ```
3. First run downloads + caches polygons to `data/amsterdam_pc6.geojson`
   (delete that file to force a refresh). It prints a match-rate report.
4. The output CSV is the input plus `postcode6` and `postcode4` columns.

## Key options
- `--lon-col` / `--lat-col`: coordinate column names (default `longitude` /
  `latitude`).
- `--bbox minlon,minlat,maxlon,maxlat`: WGS84 area to fetch polygons for.
- `--cache PATH`: polygon cache location (default `data/amsterdam_pc6.geojson`).
- `--snap-meters N`: snap points that land just outside any polygon (water,
  boundary slivers) to the nearest polygon within N meters. Default 25; set 0
  to disable and leave them blank.
- `--unmatched-csv PATH`: write rows that got no postcode for inspection.

## Validating
Spot-check a few rows against the PDOK reverse geocoder:
`https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse?lat=<lat>&lon=<lon>&type=postcode`

## Notes
- Boundaries are CBS data via PDOK — attribute "CBS / Esri Nederland" if you
  republish the polygon data.
- Points exactly on a shared boundary match one of the neighbours (first found);
  that's acceptable for ZIP assignment.
