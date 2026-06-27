#!/usr/bin/env python3
"""Map lat/long coordinates to Dutch postcodes (PC6 + PC4) via point-in-polygon.

Reads a CSV with longitude/latitude columns, finds which CBS Postcode-6 polygon
each point falls inside, and writes the CSV back with two new columns:
`postcode6` (e.g. 1011HL) and `postcode4` (the first four digits, e.g. 1011).

Boundary polygons come from the PDOK CBS Postcode6 OGC API and are cached to a
local GeoJSON on first run, so later runs are fully offline.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import shape

PC6_ITEMS_URL = (
    "https://api.pdok.nl/cbs/postcode6/ogc/v1/collections/postcode6/items"
)
# Generous WGS84 bbox around the Amsterdam municipality (minlon,minlat,maxlon,maxlat).
DEFAULT_BBOX = "4.70,52.27,5.10,52.44"
PAGE_LIMIT = 1000


def fetch_pc6_geojson(bbox, cache_path, page_limit=PAGE_LIMIT):
    """Return a list of (postcode6, shapely_geometry). Downloads + caches if needed."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        print(f"Using cached polygons: {cache_path}")
        fc = json.loads(cache_path.read_text())
        return _features_to_geoms(fc["features"])

    print(f"Downloading PC6 polygons from PDOK for bbox {bbox} ...")
    features = []
    url = f"{PC6_ITEMS_URL}?bbox={bbox}&limit={page_limit}&f=json"
    page = 0
    while url:
        data = _get_json(url)
        page_feats = data.get("features", [])
        for ft in page_feats:
            features.append(
                {
                    "type": "Feature",
                    "properties": {"postcode6": ft["properties"]["postcode6"]},
                    "geometry": ft["geometry"],
                }
            )
        page += 1
        print(f"  page {page}: +{len(page_feats)} features (total {len(features)})")
        url = _next_link(data)
        if page_feats:
            time.sleep(0.2)  # be polite to the API

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    print(f"Cached {len(features)} polygons to {cache_path}")
    return _features_to_geoms(features)


def _features_to_geoms(features):
    out = []
    for ft in features:
        out.append((ft["properties"]["postcode6"], shape(ft["geometry"])))
    return out


def _next_link(data):
    for link in data.get("links", []):
        if link.get("rel") == "next":
            return link["href"]
    return None


def _get_json(url, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            wait = 2 ** attempt
            print(f"  request failed ({exc}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def map_points(lons, lats, geoms, codes, max_snap_deg=0.0):
    """Return a list of postcode6 (or None) aligned with the input points.

    Uses a single vectorized point-in-polygon query. `max_snap_deg` > 0 snaps any
    unmatched point to the nearest polygon within that distance (in degrees).
    """
    tree = STRtree(geoms)
    pts = shapely.points(lons, lats)

    result = [None] * len(pts)
    # query returns pairs (input_index, tree_geom_index) for intersecting geoms.
    pairs = tree.query(pts, predicate="intersects")
    for in_idx, geom_idx in zip(pairs[0], pairs[1]):
        if result[in_idx] is None:  # keep first match on shared boundaries
            result[in_idx] = codes[geom_idx]

    if max_snap_deg > 0:
        missing = [i for i, r in enumerate(result) if r is None]
        if missing:
            miss_pts = pts[missing]
            nearest = tree.query_nearest(
                miss_pts, max_distance=max_snap_deg, all_matches=False
            )
            # query_nearest returns an array of tree-geom indices aligned with miss_pts;
            # -1 (or absence) means nothing within max_distance.
            for k, geom_idx in enumerate(np.atleast_1d(nearest)):
                if geom_idx is not None and geom_idx >= 0:
                    result[missing[k]] = codes[int(geom_idx)]
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_csv", help="input CSV with lon/lat columns")
    ap.add_argument("output_csv", help="output CSV path (postcode columns appended)")
    ap.add_argument("--lon-col", default="longitude")
    ap.add_argument("--lat-col", default="latitude")
    ap.add_argument("--bbox", default=DEFAULT_BBOX, help="WGS84 minlon,minlat,maxlon,maxlat")
    ap.add_argument(
        "--cache",
        default="data/amsterdam_pc6.geojson",
        help="local geojson cache of PC6 polygons",
    )
    ap.add_argument(
        "--snap-meters",
        type=float,
        default=25.0,
        help="snap unmatched points to nearest polygon within this many meters (0 to disable)",
    )
    ap.add_argument(
        "--unmatched-csv",
        default=None,
        help="optional path to write rows that got no postcode",
    )
    args = ap.parse_args()

    geoms_codes = fetch_pc6_geojson(args.bbox, args.cache)
    codes = [c for c, _ in geoms_codes]
    geoms = [g for _, g in geoms_codes]
    print(f"Loaded {len(geoms)} PC6 polygons")

    import csv

    with open(args.input_csv, newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    print(f"Read {len(rows)} rows from {args.input_csv}")

    lons, lats, valid_idx = [], [], []
    for i, row in enumerate(rows):
        try:
            lons.append(float(row[args.lon_col]))
            lats.append(float(row[args.lat_col]))
            valid_idx.append(i)
        except (KeyError, ValueError, TypeError):
            continue
    lons = np.asarray(lons, dtype="float64")
    lats = np.asarray(lats, dtype="float64")
    print(f"Parsed {len(valid_idx)} valid coordinate rows")

    # ~111_320 m per degree latitude; good enough for a small snap tolerance.
    snap_deg = args.snap_meters / 111_320.0 if args.snap_meters > 0 else 0.0
    matches = map_points(lons, lats, geoms, codes, max_snap_deg=snap_deg)

    for code in ("postcode6", "postcode4"):
        if code not in fieldnames:
            fieldnames = list(fieldnames) + [code]

    matched = 0
    for k, i in enumerate(valid_idx):
        pc6 = matches[k]
        rows[i]["postcode6"] = pc6 or ""
        rows[i]["postcode4"] = pc6[:4] if pc6 else ""
        if pc6:
            matched += 1
    for i in range(len(rows)):  # ensure columns exist on skipped rows too
        rows[i].setdefault("postcode6", "")
        rows[i].setdefault("postcode4", "")

    with open(args.output_csv, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    unmatched = total - matched
    print("\n=== Report ===")
    print(f"  total rows:     {total}")
    print(f"  matched:        {matched} ({matched/total*100:.2f}%)")
    print(f"  unmatched:      {unmatched} ({unmatched/total*100:.2f}%)")
    print(f"  wrote:          {args.output_csv}")

    if args.unmatched_csv and unmatched:
        with open(args.unmatched_csv, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(r for r in rows if not r["postcode6"])
        print(f"  unmatched rows: {args.unmatched_csv}")


if __name__ == "__main__":
    main()
