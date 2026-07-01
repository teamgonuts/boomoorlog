#!/usr/bin/env python3
"""Seed the `osm_habitats` table from Overpass API (C5 — Slice 1).

Slice 1 imports only **water polygons** (natural=water) inside a bounding box
that covers Amsterdam. Canals in Amsterdam are almost all mapped as area
features with natural=water + water=canal, so this single query catches the
Grachtengordel, the IJ river, the Amstel, and every pond in Vondelpark.

Follow-up slices will add parks (leisure=park, landuse=grass, landuse=cemetery),
and possibly `waterway=canal` linear features buffered into polygons for the
few canals not mapped as areas.

Env: reads SUPABASE_DB_URL from .env at repo root.
Deps: psycopg2 only (no shapely, no overpy). WKT is built by hand from the
Overpass `out geom` response.

Idempotent — upserts on (osm_type, osm_id). Safe to re-run.

Usage:
    python pipeline/seed_osm_habitats.py            # canals + water, ~5s
    python pipeline/seed_osm_habitats.py --dry-run  # print counts, no writes
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg2
from psycopg2.extras import execute_values

REPO = Path(__file__).resolve().parents[1]

# Amsterdam bounding box, slightly padded so bordering polygons (e.g. IJ river
# extending east into IJmeer, Amsterdamse Bos to the south-west) are included.
# Order for Overpass: south, west, north, east.
AMS_BBOX = (52.28, 4.72, 52.44, 5.02)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
UA = "creatures-ams/0.1 (github.com/teamgonuts/boomoorlog; C5 habitat seed)"

# Overpass QL: fetch every `natural=water` way inside the bbox. `out geom;`
# returns each way's node coordinates inline so we don't need to resolve node
# references separately. Relations (multi-part polygons like the IJ) skipped
# in Slice 1 — Amsterdam canals are almost entirely simple ways.
QUERY = f"""
[out:json][timeout:120];
(
  way["natural"="water"]({AMS_BBOX[0]},{AMS_BBOX[1]},{AMS_BBOX[2]},{AMS_BBOX[3]});
);
out geom;
""".strip()


def load_env(path: Path = REPO / ".env") -> dict:
    env = {}
    with path.open() as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def fetch_overpass() -> dict:
    """POST the query, return parsed JSON. Retries once on 429/504."""
    body = f"data={QUERY}".encode("utf-8")
    for attempt in range(2):
        req = Request(
            OVERPASS_URL,
            data=body,
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[warn] overpass attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt == 0:
                time.sleep(30)  # Overpass rate-limits; back off before retry.
                continue
            raise


def way_to_wkt_multipolygon(geometry: list) -> str | None:
    """Convert an Overpass way's geometry list (list of {lat, lon} dicts) into
    a WKT MULTIPOLYGON string. Returns None if the ring is degenerate (<3
    unique points) so caller can skip the row."""
    if not geometry or len(geometry) < 3:
        return None
    pts = [(g["lon"], g["lat"]) for g in geometry]
    # Force closure — Overpass usually closes rings but we shouldn't assume.
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    if len(pts) < 4:  # 3 unique + closure
        return None
    ring = ", ".join(f"{lon} {lat}" for lon, lat in pts)
    return f"MULTIPOLYGON((({ring})))"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print counts, skip writes.")
    args = ap.parse_args()

    print(f"[info] querying Overpass for natural=water in bbox {AMS_BBOX}...", flush=True)
    data = fetch_overpass()
    elements = data.get("elements", [])
    ways = [e for e in elements if e.get("type") == "way"]
    print(f"[info] overpass returned {len(ways)} ways", flush=True)

    rows: list[tuple] = []
    skipped_degenerate = 0
    for w in ways:
        wkt = way_to_wkt_multipolygon(w.get("geometry") or [])
        if wkt is None:
            skipped_degenerate += 1
            continue
        rows.append((
            "way",
            w["id"],
            "water",
            json.dumps(w.get("tags") or {}),
            wkt,
        ))
    print(
        f"[info] built {len(rows)} water polygons "
        f"({skipped_degenerate} skipped as degenerate)",
        flush=True,
    )

    if args.dry_run:
        print("[info] --dry-run: not writing to DB.")
        # Report a few sample tag bags so the user can sanity-check the query.
        for r in rows[:5]:
            print(f"    osm_id={r[1]} tags={r[3][:120]}")
        return 0

    env = load_env()
    dsn = env.get("SUPABASE_DB_URL")
    if not dsn:
        print("error: SUPABASE_DB_URL not set in .env", file=sys.stderr)
        return 2

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO osm_habitats
                    (osm_type, osm_id, kind, tags, geom)
                VALUES %s
                ON CONFLICT (osm_type, osm_id) DO UPDATE SET
                    kind        = EXCLUDED.kind,
                    tags        = EXCLUDED.tags,
                    geom        = EXCLUDED.geom,
                    imported_at = now()
                """,
                rows,
                template="(%s, %s, %s, %s::jsonb, ST_Multi(ST_MakeValid(ST_GeomFromText(%s, 4326)))::geography)",
                page_size=200,
            )
        conn.commit()
        print(f"[ok] upserted {len(rows)} rows into osm_habitats.", flush=True)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
