"""
C3.C — Backfill the full taxonomy chain (phylum / class / order / family)
for the 167 tree genera.

Trees took a coarse default in migration 025 (`kingdom=Plantae,
genus=slug, rank=genus`) because they weren't in `data/creatures.csv` and
so never went through `pipeline/enrich_taxonomy.py`. This script fixes
that by hitting GBIF with `kingdom=Plantae` as the disambiguator (some
tree genera like Acer collide with insect / animal genera otherwise).

Output: data/c3c_taxonomy_trees.csv. Migration 032 ingests it.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
IN_CSV  = REPO / "data" / "c3c_trees_input.csv"
OUT_CSV = REPO / "data" / "c3c_taxonomy_trees.csv"
CACHE   = REPO / "data" / ".taxonomy_cache.json"

GBIF_BASE = "https://api.gbif.org/v1/species/match"
UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"

FIELDS = [
    "slug", "latin_name", "query_name", "rank", "kingdom", "phylum",
    "class_name", "order_name", "family", "genus", "species",
    "scientific_name", "match_type", "confidence",
]


def pull_trees() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL not set", file=sys.stderr); sys.exit(1)
    IN_CSV.parent.mkdir(parents=True, exist_ok=True)
    sql = (
        r"\copy (select slug, latin_name from organisms "
        r"where category = 'tree' and phylum is null "
        r"order by slug) "
        f"to '{IN_CSV.as_posix()}' csv header"
    )
    r = subprocess.run(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr); sys.exit(r.returncode)
    with IN_CSV.open() as f:
        return sum(1 for _ in f) - 1


def gbif_match(name: str, cache: dict[str, dict]) -> dict | None:
    # Always pass kingdom=Plantae for tree genera so we don't get the
    # arthropod / mollusc homonyms.
    hint = {"kingdom": "Plantae"}
    key = f"{name}|{urlencode(sorted(hint.items()))}"
    if key in cache:
        return cache[key]
    params = {"name": name, **hint}
    url = f"{GBIF_BASE}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  gbif error for {name!r}: {e}", file=sys.stderr)
        return None
    cache[key] = data
    return data


def main() -> int:
    print("[step 1/2] pulling tree organisms missing phylum…")
    n = pull_trees()
    print(f"  {n} tree rows")

    cache: dict[str, dict] = {}
    if CACHE.exists():
        try: cache = json.loads(CACHE.read_text())
        except Exception: cache = {}

    print("[step 2/2] GBIF (kingdom=Plantae hint)…")
    rows = list(csv.DictReader(IN_CSV.open(newline="", encoding="utf-8")))
    out_rows: list[dict[str, str]] = []
    n_matched = 0
    for r in rows:
        slug, latin = r["slug"], r["latin_name"]
        out = {k: "" for k in FIELDS}
        out["slug"], out["latin_name"] = slug, latin
        m = gbif_match(latin, cache)
        if m and m.get("matchType") not in (None, "NONE") and m.get("kingdom"):
            out["query_name"]      = latin
            out["rank"]            = (m.get("rank") or "").lower()
            out["kingdom"]         = m.get("kingdom", "") or ""
            out["phylum"]          = m.get("phylum", "") or ""
            out["class_name"]      = m.get("class", "") or ""
            out["order_name"]      = m.get("order", "") or ""
            out["family"]          = m.get("family", "") or ""
            out["genus"]           = m.get("genus", "") or latin  # fall back to the slug
            out["species"]         = ""
            out["scientific_name"] = m.get("scientificName", "") or ""
            out["match_type"]      = m.get("matchType", "") or ""
            out["confidence"]      = str(m.get("confidence", "") or "")
            n_matched += 1
        else:
            out["rank"] = "unmatched"
        out_rows.append(out)
        time.sleep(0.02)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out_rows)
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))
    print(f"wrote {OUT_CSV.relative_to(REPO)}: {len(out_rows)} rows ({n_matched} matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
