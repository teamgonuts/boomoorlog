"""
C4 — Backfill common_name for every organism missing one.

Strategy: query iNaturalist's /v1/taxa endpoint for each Latin name (it
exposes `preferred_common_name` for nearly every taxon humans observe).
Cached, resumable, idempotent. Falls back to leaving common_name null
when iNat has nothing — those rows will get a sub-agent pass after.

Output: data/c4_common_names.csv  (slug, latin_name, common_name, source)
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
IN_CSV  = REPO / "data" / "c4_missing_names.csv"
OUT_CSV = REPO / "data" / "c4_common_names.csv"
CACHE   = REPO / "data" / ".inat_taxa_cache.json"

INAT_URL = "https://api.inaturalist.org/v1/taxa?q={}&per_page=1&locale=en"
UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"

FIELDS = ["slug", "latin_name", "common_name", "source", "inat_taxon_id"]


def pull_missing() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL not set", file=sys.stderr); sys.exit(1)
    IN_CSV.parent.mkdir(parents=True, exist_ok=True)
    sql = (
        r"\copy (select slug, latin_name, "
        r"coalesce(taxon_group, '') as taxon_group "
        r"from organisms "
        r"where (common_name is null or common_name = '') "
        r"order by observations_count desc nulls last, slug) "
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


def inat_lookup(name: str, cache: dict[str, dict]) -> dict | None:
    if name in cache:
        return cache[name]
    url = INAT_URL.format(quote(name))
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  inat error for {name!r}: {e}", file=sys.stderr)
        return None
    cache[name] = data
    return data


def clean_latin(latin: str) -> list[str]:
    """Generate candidate query strings — strip 'spec.', alternate names."""
    name = (latin or "").strip()
    out = []
    if not name: return out
    out.append(name)
    # Try the first variant on multi-name fields like "Aceria / Eriophyidae"
    for sep in [" / ", "/", ", ", ","]:
        if sep in name:
            first = name.split(sep)[0].strip()
            if first: out.append(first); break
    # Strip "spec." / "sp." / "indet." trailing words
    import re
    stripped = re.sub(r"\s+(spec|sp|spp|indet)\.?\s*$", "", name, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped and stripped != name:
        out.append(stripped)
    # Dedupe
    seen, dedup = set(), []
    for c in out:
        if c not in seen:
            seen.add(c); dedup.append(c)
    return dedup


def main() -> int:
    print("[step 1/2] pulling organisms missing common_name…")
    n = pull_missing()
    print(f"  {n} rows missing common_name")

    cache: dict[str, dict] = {}
    if CACHE.exists():
        try: cache = json.loads(CACHE.read_text())
        except Exception: cache = {}

    print("[step 2/2] resolving via iNaturalist /v1/taxa…")
    rows = list(csv.DictReader(IN_CSV.open(newline="", encoding="utf-8")))
    out_rows: list[dict[str, str]] = []
    n_resolved = 0
    for i, r in enumerate(rows, 1):
        slug, latin = r["slug"], r["latin_name"]
        common, taxon_id = "", ""
        for candidate in clean_latin(latin):
            data = inat_lookup(candidate, cache)
            if data and data.get("results"):
                top = data["results"][0]
                pn = (top.get("preferred_common_name") or "").strip()
                if pn:
                    common = pn
                    taxon_id = str(top.get("id", ""))
                    break
            time.sleep(0.05)  # respect iNat rate limits
        out_rows.append({
            "slug": slug,
            "latin_name": latin,
            "common_name": common,
            "source": "inat" if common else "unresolved",
            "inat_taxon_id": taxon_id,
        })
        if common:
            n_resolved += 1
        if i % 100 == 0:
            print(f"  [{i:>4}/{n}] {slug:<35s} → {common[:40]}")
            CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out_rows)
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))

    print(f"\nwrote {OUT_CSV.relative_to(REPO)}: {len(out_rows)} rows ({n_resolved} resolved, {len(out_rows)-n_resolved} unresolved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
