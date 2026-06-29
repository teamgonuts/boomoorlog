"""
C3.A — Enrich the long-tail observation organisms (the ~2,236 species that
landed in `organisms` via migration 021 step 3 but never went through GBIF
or the C3 labeling pass).

Pipeline:
  1. Pull the long-tail inventory from Supabase via psql COPY.
  2. Hit GBIF Species Match for each Latin name (cached, resumable).
  3. Emit `data/c3a_taxonomy.csv` for SQL ingest.

Run idempotently — re-running only hits GBIF for slugs whose taxonomy is
still missing (cached results are reused).

Usage:
    python3 pipeline/c3a_enrich_longtail.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
INVENTORY_CSV = REPO / "data" / "c3a_inventory.csv"
OUT_CSV = REPO / "data" / "c3a_taxonomy.csv"
CACHE = REPO / "data" / ".taxonomy_cache.json"  # shared with enrich_taxonomy.py

GBIF_URL = "https://api.gbif.org/v1/species/match?name={}"
UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"

FIELDS = [
    "slug",
    "latin_name",
    "query_name",
    "rank",
    "kingdom",
    "phylum",
    "class_name",
    "order_name",
    "family",
    "genus",
    "species",
    "scientific_name",
    "match_type",
    "confidence",
]


def pull_inventory() -> None:
    """Export the long-tail slugs to data/c3a_inventory.csv via psql COPY."""
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: set SUPABASE_DB_URL (source .env)", file=sys.stderr)
        sys.exit(1)
    INVENTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    # \copy is a psql meta-command — fine when invoked via psql -c "\copy ..."
    sql = (
        r"\copy (select slug, latin_name, taxon_group, "
        r"coalesce(common_name, '') as common_name, observations_count "
        r"from organisms where habitat_classes = '{}'::text[] "
        r"and category != 'tree' order by observations_count desc nulls last, slug) "
        f"to '{INVENTORY_CSV.as_posix()}' csv header"
    )
    r = subprocess.run(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    print(r.stdout.strip())


def clean_for_match(latin: str) -> list[str]:
    name = (latin or "").strip()
    candidates: list[str] = []
    if not name:
        return candidates
    candidates.append(name)
    for sep in [" / ", "/", ", ", ","]:
        if sep in name:
            for part in name.split(sep):
                part = part.strip()
                if part:
                    candidates.append(part)
    stripped = re.sub(r"\b(spp|sp|esp|incl|including|etc|indet)\.?\b", "",
                      name, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip(" ,")
    if stripped and stripped != name:
        candidates.append(stripped)
    words = re.findall(r"[A-Z][a-z]+", name)
    if len(words) >= 2:
        candidates.append(f"{words[0]} {words[1]}")
    if words:
        candidates.append(words[0])
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def gbif_match(name: str, cache: dict[str, dict]) -> dict | None:
    if name in cache:
        return cache[name]
    url = GBIF_URL.format(quote(name))
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  gbif error for {name!r}: {e}", file=sys.stderr)
        return None
    cache[name] = data
    return data


def is_useful_match(m: dict | None) -> bool:
    if not m:
        return False
    if m.get("matchType") in (None, "NONE"):
        return False
    return bool(m.get("kingdom") or m.get("genus") or m.get("family"))


def species_epithet(scientific: str | None, genus: str | None) -> str | None:
    if not scientific:
        return None
    parts = scientific.replace("(", " ").split()
    if not parts:
        return None
    if genus and len(parts) >= 2 and parts[0] == genus:
        return parts[1].lower()
    if len(parts) >= 2:
        return parts[1].lower()
    return None


def looks_compound(latin: str) -> bool:
    return any(ind in (latin or "") for ind in ["+", " and ", " & ", ";"])


def main() -> int:
    print("[step 1/2] exporting long-tail inventory from Supabase…")
    pull_inventory()

    print("[step 2/2] enriching via GBIF (cached)…")
    cache: dict[str, dict] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}

    with INVENTORY_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows: list[dict[str, str]] = []
    n_matched = 0
    n_compound = 0
    n_unmatched = 0

    for i, r in enumerate(rows, 1):
        slug = r["slug"]
        latin = (r.get("latin_name") or "").strip()
        out = {k: "" for k in FIELDS}
        out["slug"] = slug
        out["latin_name"] = latin

        if not latin or looks_compound(latin):
            out["rank"] = "compound"
            n_compound += 1
            out_rows.append(out)
            continue

        matched = None
        chosen_query = None
        for cand in clean_for_match(latin):
            m = gbif_match(cand, cache)
            if is_useful_match(m):
                matched, chosen_query = m, cand
                break
            time.sleep(0.02)  # gentle on the API for fresh names

        if not matched:
            out["rank"] = "unmatched"
            n_unmatched += 1
        else:
            out["query_name"] = chosen_query or ""
            out["rank"] = (matched.get("rank") or "").lower()
            out["kingdom"] = matched.get("kingdom", "") or ""
            out["phylum"] = matched.get("phylum", "") or ""
            out["class_name"] = matched.get("class", "") or ""
            out["order_name"] = matched.get("order", "") or ""
            out["family"] = matched.get("family", "") or ""
            out["genus"] = matched.get("genus", "") or ""
            out["species"] = species_epithet(matched.get("species"), matched.get("genus")) or ""
            out["scientific_name"] = matched.get("scientificName", "") or ""
            out["match_type"] = matched.get("matchType", "") or ""
            out["confidence"] = str(matched.get("confidence", "") or "")
            n_matched += 1

        out_rows.append(out)
        if i % 100 == 0:
            print(f"  [{i:>4}/{len(rows)}] {slug:<35s} {out['rank']:<10s} {out.get('genus','')}")
            CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))

    print()
    print(f"wrote {OUT_CSV.relative_to(REPO)}: {len(out_rows)} rows")
    print(f"  matched:   {n_matched}")
    print(f"  compound:  {n_compound}")
    print(f"  unmatched: {n_unmatched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
