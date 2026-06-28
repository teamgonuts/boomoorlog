#!/usr/bin/env python3
"""Backfill `observations.creature_slug` by matching `scientific_name` against
the existing `creatures.latin_name` field.

Matching, first hit wins:
  1. Exact match (case-insensitive) against any comma/slash-separated component
     of `creatures.latin_name`.
  2. Genus-token match: the first whitespace-separated token of
     `observations.scientific_name` equals a single-word component of
     `creatures.latin_name` (case-insensitive).

If multiple creatures match, prefer highest `tree_count`, then alphabetically
first `slug`. Only rows with `creature_slug IS NULL` are updated, so it's safe
to re-run after future obs ingest.

Env: requires SUPABASE_DB_URL in .env at the repo root.
"""

import re
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

REPO = Path(__file__).resolve().parent


def load_env(path: Path = REPO / ".env") -> dict:
    env = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


SPLIT_RE = re.compile(r"[,/]")


def components(latin_name: str) -> list[str]:
    """Split `creatures.latin_name` into trimmed components by comma/slash."""
    return [c.strip() for c in SPLIT_RE.split(latin_name or "") if c.strip()]


def main() -> None:
    env = load_env()
    db_url = env.get("SUPABASE_DB_URL")
    if not db_url:
        sys.exit("SUPABASE_DB_URL missing from .env")

    with psycopg2.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from observations where creature_slug is not null")
        already_linked = cur.fetchone()[0]

        # Build the match index from creatures, sorted so the "best" creature
        # wins ties: highest tree_count first, then alphabetical slug.
        cur.execute(
            "select slug, latin_name, coalesce(tree_count, 0) as tree_count "
            "from creatures order by tree_count desc nulls last, slug asc"
        )
        creatures = cur.fetchall()

        # exact_idx[lower(component)] = first (best) slug
        # genus_idx[lower(single-word-component)] = first (best) slug
        exact_idx: dict[str, str] = {}
        genus_idx: dict[str, str] = {}
        for slug, latin_name, _tc in creatures:
            for comp in components(latin_name):
                key = comp.lower()
                exact_idx.setdefault(key, slug)
                if " " not in comp:  # single-word -> usable as genus
                    genus_idx.setdefault(key, slug)

        # Pull all unlinked obs (distinct names -> one decision per species).
        cur.execute(
            "select distinct scientific_name from observations "
            "where creature_slug is null and scientific_name is not null"
        )
        names = [r[0] for r in cur.fetchall()]

        updates: list[tuple[str, str]] = []  # (slug, scientific_name)
        for name in names:
            n = name.strip()
            if not n:
                continue
            slug = exact_idx.get(n.lower())
            if not slug:
                first_token = n.split()[0].lower()
                slug = genus_idx.get(first_token)
            if slug:
                updates.append((slug, name))

        if updates:
            execute_batch(
                cur,
                "update observations set creature_slug = %s "
                "where creature_slug is null and scientific_name = %s",
                updates,
                page_size=500,
            )

        cur.execute("select count(*) from observations where creature_slug is not null")
        now_linked = cur.fetchone()[0]
        newly_linked = now_linked - already_linked

        cur.execute("select count(*) from observations where creature_slug is null")
        unlinked = cur.fetchone()[0]

        print(f"already linked before run: {already_linked}")
        print(f"newly linked this run:     {newly_linked}")
        print(f"total linked now:          {now_linked}")
        print(f"remaining unlinked:        {unlinked}")
        print(f"distinct species matched:  {len(updates)}")

        print("\nverify — count linked:")
        cur.execute("select count(*) from observations where creature_slug is not null")
        print(f"  {cur.fetchone()[0]}")

        print("\nverify — top 5 linked (source, scientific_name, count):")
        cur.execute(
            "select o.source, o.scientific_name, count(*) from observations o "
            "join creatures c on o.creature_slug = c.slug "
            "group by o.source, o.scientific_name order by 3 desc limit 5"
        )
        for row in cur.fetchall():
            print(f"  {row[0]:11s} {row[1]:40s} {row[2]}")

        print("\nverify — top 10 unmatched species:")
        cur.execute(
            "select scientific_name, count(*) from observations "
            "where creature_slug is null group by 1 order by 2 desc limit 10"
        )
        for row in cur.fetchall():
            name = row[0] if row[0] is not None else "(null)"
            print(f"  {name:40s} {row[1]}")


if __name__ == "__main__":
    main()
