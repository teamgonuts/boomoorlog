#!/usr/bin/env python3
"""Bulk-seed the `trees` table from data/amsterdam_trees_zip.csv (298k rows).

Walks the CSV once, transforms each row (parses the height/diameter class
strings into numeric height_m / diameter_cm, normalises empty strings to
NULL), then streams the result into Postgres via COPY for speed.

Re-runnable: TRUNCATEs `trees` before loading. `genera` is left alone — run
seed_genera.py separately.

Env: requires SUPABASE_DB_URL in .env at the repo root.
"""

import csv
import io
import sys

import psycopg2

from pipeline.stats import parse_diameter_cm, parse_height_m

CSV_PATH = "data/amsterdam_trees_zip.csv"

# Column order for the COPY statement. CSV stream is written in the same order.
DB_COLS = [
    "id", "genus_slug", "species_full", "species_top",
    "postcode6", "postcode4", "buurt_id",
    "longitude", "latitude", "rd_x", "rd_y", "geometrie_raw",
    "height_class", "diameter_class", "height_m", "diameter_cm",
    "planting_year",
    "owner", "manager", "location", "location_detail",
    "object_type", "species_type", "growing_location_id",
    "protection_status", "protection_status_detail",
    "valid_from", "mutated_at",
]


def load_env(path=".env"):
    env = {}
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _nullish(v):
    """Empty string → None, else passthrough. CSV writer turns None into ''
    which Postgres COPY (NULL '') reads as SQL NULL."""
    return None if v == "" else v


def transform(r):
    """One CSV row from the source → tuple in DB_COLS order."""
    g = r["soortnaamKort"].strip()
    if not g or g == "Onbekend":
        g = None

    yr = r["jaarVanAanleg"]
    planting_year = int(yr) if yr and yr.isdigit() else None
    # A handful of rows have corrupt years like 20141990 or 19921 — drop those.
    if planting_year is not None and not (1500 <= planting_year <= 2100):
        planting_year = None

    return (
        int(r["id"]),
        g,
        _nullish(r["soortnaam"]),
        _nullish(r["soortnaamTop"]),
        _nullish(r["postcode6"]),
        _nullish(r["postcode4"]),
        _nullish(r["gbdBuurtId"]),
        _nullish(r["longitude"]),
        _nullish(r["latitude"]),
        _nullish(r["rd_x"]),
        _nullish(r["rd_y"]),
        _nullish(r["geometrie"]),
        _nullish(r["boomhoogteklasseActueel"]),
        _nullish(r["stamdiameterklasse"]),
        parse_height_m(r["boomhoogteklasseActueel"]),
        parse_diameter_cm(r["stamdiameterklasse"]),
        planting_year,
        _nullish(r["typeEigenaarPlus"]),
        _nullish(r["typeBeheerderPlus"]),
        _nullish(r["standplaats"]),
        _nullish(r["standplaatsGedetailleerd"]),
        _nullish(r["typeObject"]),
        _nullish(r["typeSoortnaam"]),
        _nullish(r["groeiplaatsBoomId"]),
        _nullish(r["beschermingsstatus"]),
        _nullish(r["beschermingsstatusGedetailleerd"]),
        _nullish(r["geldigVanaf"]),
        _nullish(r["mutatieDatum"]),
    )


def build_buffer():
    """Stream the source CSV through the transform and emit a buffer of
    transformed CSV ready for COPY. Returns (buffer, row_count)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    n = 0
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            row = transform(r)
            # csv.writer turns None into ''; COPY (NULL '') reads '' as NULL.
            w.writerow(["" if v is None else v for v in row])
            n += 1
    buf.seek(0)
    return buf, n


def main():
    env = load_env()
    db_url = env.get("SUPABASE_DB_URL")
    if not db_url:
        sys.exit("SUPABASE_DB_URL missing from .env")

    print(f"Transforming {CSV_PATH}…")
    buf, expected = build_buffer()
    print(f"Prepared {expected} rows. Streaming to Postgres…")

    copy_sql = (
        f"COPY trees ({','.join(DB_COLS)}) "
        f"FROM STDIN WITH (FORMAT CSV, NULL '')"
    )
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE trees")
            cur.copy_expert(copy_sql, buf)
            cur.execute("SELECT COUNT(*) FROM trees")
            actual = cur.fetchone()[0]
        conn.commit()
    print(f"trees table now has {actual} rows.")


if __name__ == "__main__":
    main()
