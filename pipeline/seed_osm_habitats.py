#!/usr/bin/env python3
"""Seed the `osm_habitats` table from Overpass API (C5).

Imports two polygon "kinds":
  * `water` — natural=water. Catches the Grachtengordel, the IJ river, the
    Amstel, and every pond in Vondelpark. Home to ducks, coots, herons,
    fish and everything else with a `water-*` habitat_class.
  * `park`  — leisure=park + landuse=grass|cemetery|recreation_ground.
    Catches Vondelpark, Sarphatipark, Oosterpark, plus every neighbourhood
    green and cemetery. Home to squirrels, hedgehogs, ground insects,
    bees on flowering plants — everything with `ground-park` or
    `flower-visitor`.

Buildings (`wall-and-roof`) deliberately skipped: ~200k polygons for
Amsterdam, only ~4 species use that class, and their raw observation
coords are usually already accurate.

Env: reads SUPABASE_DB_URL from .env at repo root.
Deps: psycopg2 only (no shapely, no overpy). WKT is built by hand from the
Overpass `out geom` response.

Idempotent — upserts on (osm_type, osm_id). Safe to re-run.

Usage:
    python pipeline/seed_osm_habitats.py                  # all kinds
    python pipeline/seed_osm_habitats.py --kind water     # water only
    python pipeline/seed_osm_habitats.py --kind park      # park only
    python pipeline/seed_osm_habitats.py --dry-run        # counts, no writes
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

# Overpass QL queries keyed by habitat kind. `out geom;` returns each way's
# node coordinates inline so we don't need node lookups. Relations (multi-
# part polygons) skipped — Amsterdam habitat polygons are almost entirely
# simple ways, and the few we miss (e.g. the IJ river as a relation) don't
# meaningfully affect creature placement.
BBOX = f"{AMS_BBOX[0]},{AMS_BBOX[1]},{AMS_BBOX[2]},{AMS_BBOX[3]}"

def _q(*filters: str) -> str:
    """Build an Overpass query fetching ways matching any of the given tag
    filters (as OR). One filter per line inside the union."""
    body = "\n  ".join(f'way{f}({BBOX});' for f in filters)
    return f"[out:json][timeout:180];\n(\n  {body}\n);\nout geom;"

# Per-kind: a list of separate Overpass queries, results merged locally.
# Splitting park lookups into multiple small queries dodges Overpass 504s that
# happen when a single UNION query stays open too long.
QUERY_BATCHES: dict[str, list[str]] = {
    "water": [
        _q('["natural"="water"]'),
    ],
    "park": [
        # One tag filter per batch — Overpass 504s repeatedly on Amsterdam's
        # big grass footprint if we UNION multiple filters into one query.
        _q('["leisure"="park"]'),
        _q('["leisure"="garden"]'),
        _q('["landuse"="grass"]'),
        _q('["landuse"="village_green"]'),
        _q('["landuse"="recreation_ground"]'),
        _q('["landuse"="cemetery"]'),
        _q('["natural"="grassland"]'),
    ],
}


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


def fetch_overpass(query: str) -> dict | None:
    """POST the query, return parsed JSON. Up to 3 attempts with exponential
    backoff on 429/504. Returns None if all attempts fail so callers can
    skip that batch instead of crashing the whole seed."""
    body = f"data={query}".encode("utf-8")
    for attempt in range(3):
        req = Request(
            OVERPASS_URL,
            data=body,
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(req, timeout=240) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            wait = [20, 60, 120][attempt]
            print(f"[warn] overpass attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt < 2:
                print(f"[warn] backing off {wait}s before retry...", file=sys.stderr)
                time.sleep(wait)
    print("[warn] giving up on this batch — will continue with the next.", file=sys.stderr)
    return None


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


def build_rows_for_kind(kind: str) -> list[tuple]:
    """Fetch + WKT-convert one habitat kind. Returns rows ready for upsert.
    Runs each Overpass batch query, dedupes across batches (a way can match
    multiple filters, e.g. a park with a grass sub-polygon), and returns
    the merged row set."""
    batches = QUERY_BATCHES[kind]
    print(
        f"[info] querying Overpass for kind={kind} ({len(batches)} batch"
        f"{'es' if len(batches) > 1 else ''}) in bbox {AMS_BBOX}...",
        flush=True,
    )

    seen: dict[int, dict] = {}
    failed_batches: list[int] = []
    for i, query in enumerate(batches, 1):
        data = fetch_overpass(query)
        if data is None:
            failed_batches.append(i)
            continue
        ways = [e for e in data.get("elements", []) if e.get("type") == "way"]
        for w in ways:
            seen[w["id"]] = w
        print(f"[info]   batch {i}/{len(batches)}: +{len(ways)} ways (cumulative {len(seen)})", flush=True)
        if i < len(batches):
            time.sleep(4)  # be polite between batches
    if failed_batches:
        print(f"[warn] {len(failed_batches)} batch(es) failed: {failed_batches}. Re-run to backfill.", file=sys.stderr)

    rows: list[tuple] = []
    skipped_degenerate = 0
    for w in seen.values():
        wkt = way_to_wkt_multipolygon(w.get("geometry") or [])
        if wkt is None:
            skipped_degenerate += 1
            continue
        rows.append((
            "way",
            w["id"],
            kind,
            json.dumps(w.get("tags") or {}),
            wkt,
        ))
    print(
        f"[info] built {len(rows)} {kind} polygons "
        f"({skipped_degenerate} skipped as degenerate)",
        flush=True,
    )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--kind",
        choices=list(QUERY_BATCHES.keys()) + ["all"],
        default="all",
        help="Which habitat kind to seed. Default: all.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print counts, skip writes.")
    args = ap.parse_args()

    kinds = list(QUERY_BATCHES.keys()) if args.kind == "all" else [args.kind]
    rows: list[tuple] = []
    for kind in kinds:
        rows.extend(build_rows_for_kind(kind))
        # Be polite to Overpass between separate kind queries.
        if len(kinds) > 1 and kind != kinds[-1]:
            time.sleep(2)

    if args.dry_run:
        print("[info] --dry-run: not writing to DB.")
        for r in rows[:5]:
            print(f"    kind={r[2]} osm_id={r[1]} tags={r[3][:120]}")
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
