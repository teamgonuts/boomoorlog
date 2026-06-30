#!/usr/bin/env python3
"""Seed the `observations` table in Supabase with recent wildlife sightings
from iNaturalist + Observation.org / Waarneming.nl.

Reuses the fetch logic from `fetch_observations.py` (no CSV intermediate) and
UPSERTs into the DB by the natural key (source, source_obs_id).

Defaults:
  - last 30 days
  - 7 km radius around Amsterdam city centre (52.3702, 4.8952)
  - both sources

Override with CLI flags (see --help). Re-running is safe: existing rows are
updated with the latest photo/quality/permalink and `fetched_at` is bumped.

Env: requires SUPABASE_DB_URL in .env at the repo root (same as seed_genera).
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from fetch_observations import fetch_inat, fetch_waarneming

REPO = Path(__file__).resolve().parents[1]


def load_env(path: Path = REPO / ".env") -> dict:
    env = {}
    with path.open() as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


UPSERT = """
INSERT INTO observations (
    source, source_obs_id, observed_on, point, lat, lng, accuracy_m,
    scientific_name, common_name, taxon_group, quality,
    photo_url, photo_license, permalink, fetched_at
)
VALUES %s
ON CONFLICT (source, source_obs_id) DO UPDATE SET
    observed_on     = EXCLUDED.observed_on,
    point           = EXCLUDED.point,
    lat             = EXCLUDED.lat,
    lng             = EXCLUDED.lng,
    accuracy_m      = EXCLUDED.accuracy_m,
    scientific_name = EXCLUDED.scientific_name,
    common_name     = EXCLUDED.common_name,
    taxon_group     = EXCLUDED.taxon_group,
    quality         = EXCLUDED.quality,
    photo_url       = EXCLUDED.photo_url,
    photo_license   = EXCLUDED.photo_license,
    permalink       = EXCLUDED.permalink,
    fetched_at      = now()
"""

TEMPLATE = (
    "(%s, %s, %s, "
    "  CASE WHEN %s IS NULL OR %s IS NULL THEN NULL "
    "       ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography END, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())"
)


def to_row(r: dict) -> tuple:
    lat = r.get("lat")
    lng = r.get("lng")
    # accuracy may arrive as "" — coerce
    acc = r.get("accuracy_m")
    acc = int(acc) if (acc not in (None, "", "0") and str(acc).strip().isdigit()) else None
    return (
        r["source"],
        int(r["obs_id"]),
        r["observed_on"] or None,
        lng, lat,            # NULL check args for point CASE
        lng, lat,            # ST_MakePoint args (lng, lat order)
        lat, lng,            # plain lat/lng columns
        acc,
        r["scientific_name"],
        r.get("common_name") or None,
        str(r.get("taxon_group")) if r.get("taxon_group") not in (None, "") else None,
        str(r.get("quality")) if r.get("quality") not in (None, "") else None,
        r.get("photo_url") or None,
        r.get("photo_license") or None,
        r.get("permalink") or None,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, default=52.3702, help="default: Dam Square")
    ap.add_argument("--lng", type=float, default=4.8952)
    ap.add_argument("--radius-km", type=float, default=7.0, help="default 7km covers most of Amsterdam")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--source", choices=["inat", "waarneming", "both"], default="both")
    ap.add_argument("--max-per-source", type=int, default=20000)
    args = ap.parse_args()

    env = load_env()
    db_url = env.get("SUPABASE_DB_URL")
    if not db_url:
        sys.exit("SUPABASE_DB_URL missing from .env")

    since = date.today() - timedelta(days=args.days)
    print(f"fetching observations since {since} ({args.days} days), "
          f"{args.radius_km}km around ({args.lat}, {args.lng})")

    rows = []
    if args.source in ("inat", "both"):
        print("→ iNaturalist…")
        r = fetch_inat(args.lat, args.lng, args.radius_km, None, since, args.max_per_source)
        print(f"  {len(r)} obs")
        rows.extend(r)
    if args.source in ("waarneming", "both"):
        print("→ Observation.org / Waarneming.nl…")
        r = fetch_waarneming(args.lat, args.lng, args.radius_km, since, args.max_per_source)
        print(f"  {len(r)} obs")
        rows.extend(r)

    if not rows:
        print("nothing to insert")
        return

    print(f"upserting {len(rows)} rows…")
    db_rows = [to_row(r) for r in rows]
    with psycopg2.connect(db_url) as conn, conn.cursor() as cur:
        execute_values(cur, UPSERT, db_rows, template=TEMPLATE, page_size=500)
        cur.execute("select count(*) from observations")
        total = cur.fetchone()[0]
        cur.execute(
            "select count(distinct scientific_name) from observations "
            "where observed_on >= %s", (since,)
        )
        uniq = cur.fetchone()[0]
    print(f"done. observations now: {total} total · {uniq} unique species in last {args.days}d")


if __name__ == "__main__":
    main()
