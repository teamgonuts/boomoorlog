#!/usr/bin/env python3
"""Extract all currently-living Amsterdam municipal trees to a single CSV.

Source: Amsterdam DSO open API, dataset `bomen`, table `stamgegevens`
        https://api.data.amsterdam.nl/v1/bomen/stamgegevens

Output: data/amsterdam_trees.csv  (one row per tree)
  - all native attributes from the API
  - rd_x, rd_y         : native Rijksdriehoek coords (EPSG:28992)
  - longitude, latitude: WGS84 (EPSG:4326)

"Currently living" filter: the master table only holds trees currently in
municipal management (removed trees move to the `kapenherplant` table). The API
exposes no usable condition/health field (`conditiescore` / `boomconditie` are
empty in v2), so we exclude the two available "not a living tree" signals:
  - typeObject == 'Stobbe'                              (tree stump)
  - boomhoogteklasseActueel starts with 'r.'           (boom te vellen / to be felled)
"""

import csv
import io
import re
import sys
import time
import urllib.request
import urllib.error

from pyproj import Transformer

BASE = "https://api.data.amsterdam.nl/v1/bomen/stamgegevens/"
PAGE_SIZE = 10000
OUT_PATH = "data/amsterdam_trees.csv"

_POINT_RE = re.compile(r"POINT\s*\(([-\d.eE]+)\s+([-\d.eE]+)\)")
_transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)


def is_living(row):
    if row.get("typeObject") == "Stobbe":
        return False
    if (row.get("boomhoogteklasseActueel") or "").startswith("r."):
        return False
    return True


def parse_rd(geom):
    """Return (x, y) RD floats from 'SRID=28992;POINT (x y)' or (None, None)."""
    if not geom:
        return None, None
    m = _POINT_RE.search(geom)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def fetch_page(page):
    url = f"{BASE}?_format=csv&_pageSize={PAGE_SIZE}&page={page}"
    last_err = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/csv"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            wait = 2 ** attempt
            print(f"  page {page} attempt {attempt+1} failed ({e}); retrying in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"page {page} failed after retries: {last_err}")


def main():
    total_seen = 0
    total_written = 0
    dropped = 0
    seen_first_id = None
    out_fields = None

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fout:
        writer = None
        page = 1
        while True:
            text = fetch_page(page)
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            if not rows:
                break

            # Guard against the API looping / ignoring `page` past the end.
            if rows[0].get("id") == seen_first_id:
                break
            seen_first_id = rows[0].get("id")

            if writer is None:
                out_fields = reader.fieldnames + ["rd_x", "rd_y", "longitude", "latitude"]
                writer = csv.DictWriter(fout, fieldnames=out_fields)
                writer.writeheader()

            # Batch-reproject for speed.
            living = []
            for r in rows:
                total_seen += 1
                if not is_living(r):
                    dropped += 1
                    continue
                x, y = parse_rd(r.get("geometrie"))
                r["rd_x"], r["rd_y"] = x, y
                living.append((r, x, y))

            xs = [x for _, x, y in living if x is not None]
            ys = [y for _, x, y in living if y is not None]
            if xs:
                lons, lats = _transformer.transform(xs, ys)
            it = iter(zip(lons, lats)) if xs else iter(())
            for r, x, y in living:
                if x is not None:
                    lon, lat = next(it)
                    r["longitude"], r["latitude"] = round(lon, 7), round(lat, 7)
                else:
                    r["longitude"], r["latitude"] = None, None
                writer.writerow(r)
                total_written += 1

            print(f"page {page}: {len(rows)} fetched, "
                  f"{total_written} written, {dropped} dropped (running)")
            if len(rows) < PAGE_SIZE:
                break
            page += 1

    print(f"\nDone. seen={total_seen} written={total_written} dropped={dropped}")
    print(f"Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
