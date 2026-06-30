#!/usr/bin/env python3
"""Seed the `genera` table in Supabase from the offline data + research files.

Steps:
  1. collect_all_genera()  → every genus seen in the trees CSV (lightweight).
  2. compute_genus_rows()  → full stat blocks for the ~55 fully stat-blocked
     genera (count >= MIN_COUNT AND has a research MD).
  3. UPSERT all of (1), overlaying stats from (2). Genera lacking stats get
     a row with null stats so trees can still FK to them.

`genera.tree_count`, `avg_height_m`, `avg_diameter_cm` are left at their
defaults; step 7 backfills them with a SQL UPDATE that aggregates from the
fully-loaded `trees` table.

Env: requires SUPABASE_DB_URL in .env at the repo root.
"""

import os
import sys

import psycopg2
from psycopg2.extras import execute_values

from pipeline.stats import collect_all_genera, compute_genus_rows

SPRITE_DIR = "data/sprites_pixel"


def load_env(path=".env"):
    """Tiny KEY=VALUE .env loader — no extra dependency."""
    env = {}
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def sprite_path(slug):
    p = os.path.join(SPRITE_DIR, f"{slug}.png")
    return p if os.path.exists(p) else None


def build_rows():
    """Merge all-genera (universe) with stat-blocked rows (overlay)."""
    universe = {g['slug']: g for g in collect_all_genera()}
    stats_by_slug = {r['slug']: r for r in compute_genus_rows()}

    out = []
    for slug, base in universe.items():
        s = stats_by_slug.get(slug)
        out.append((
            slug,
            base['latin_name'],
            base['dutch_name'],
            base['display_name'],
            s['attack']                  if s else None,
            s['range']                   if s else None,
            s['health']                  if s else None,
            s['attack_speed']            if s else None,
            s['move_speed']              if s else None,
            s['world_rarity_multiplier'] if s else 1.00,
            s['personality']             if s else None,
            sprite_path(slug),
            s['lore']                    if s else None,
        ))
    return out


UPSERT = """
INSERT INTO genera (
    slug, latin_name, dutch_name, display_name,
    attack, range, health, attack_speed, move_speed,
    world_rarity_multiplier, personality, sprite_path, lore
) VALUES %s
ON CONFLICT (slug) DO UPDATE SET
    latin_name              = EXCLUDED.latin_name,
    dutch_name              = EXCLUDED.dutch_name,
    display_name            = EXCLUDED.display_name,
    attack                  = EXCLUDED.attack,
    range                   = EXCLUDED.range,
    health                  = EXCLUDED.health,
    attack_speed            = EXCLUDED.attack_speed,
    move_speed              = EXCLUDED.move_speed,
    world_rarity_multiplier = EXCLUDED.world_rarity_multiplier,
    personality             = EXCLUDED.personality,
    sprite_path             = EXCLUDED.sprite_path,
    lore                    = EXCLUDED.lore
"""


def main():
    env = load_env()
    db_url = env.get("SUPABASE_DB_URL")
    if not db_url:
        sys.exit("SUPABASE_DB_URL missing from .env")

    rows = build_rows()
    stat_blocked = sum(1 for r in rows if r[4] is not None)
    print(f"Prepared {len(rows)} genera ({stat_blocked} with full stats, "
          f"{len(rows) - stat_blocked} sparse).")

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT, rows)
            cur.execute("SELECT COUNT(*) FROM genera")
            n = cur.fetchone()[0]
        conn.commit()
    print(f"genera table now has {n} rows.")


if __name__ == "__main__":
    main()
