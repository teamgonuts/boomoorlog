"""
C3.B — Retry GBIF lookups for the organisms that came back rank='unmatched'.

Most failures are caused by ambiguous genus names (e.g. "Acanthus" exists in
both Plantae and Arthropoda → GBIF returns matchType=NONE). Re-querying with
a kingdom/class hint derived from `taxon_group` resolves the ambiguity for
the vast majority of these.

Output: data/c3b_taxonomy_retry.csv. Migration 029 ingests it.
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
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
IN_CSV  = REPO / "data" / "c3b_unmatched_input.csv"
OUT_CSV = REPO / "data" / "c3b_taxonomy_retry.csv"
CACHE   = REPO / "data" / ".taxonomy_cache.json"

GBIF_BASE = "https://api.gbif.org/v1/species/match"
UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"

# Map taxon_group → GBIF hint parameters. Alpha keys are the Waarneming /
# iNaturalist text labels we see in the data.
TAXON_HINT: dict[str, dict[str, str]] = {
    "Aves":           {"class": "Aves"},
    "Mammalia":       {"class": "Mammalia"},
    "Insecta":        {"class": "Insecta"},
    "Arachnida":      {"class": "Arachnida"},
    "Plantae":        {"kingdom": "Plantae"},
    "Fungi":          {"kingdom": "Fungi"},
    "Reptilia":       {"class": "Reptilia"},
    "Amphibia":       {"class": "Amphibia"},
    "Actinopterygii": {"class": "Actinopterygii"},
    "Mollusca":       {"phylum": "Mollusca"},
}

FIELDS = [
    "slug", "latin_name", "query_name", "rank", "kingdom", "phylum",
    "class_name", "order_name", "family", "genus", "species",
    "scientific_name", "match_type", "confidence",
]


def pull_unmatched() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL not set", file=sys.stderr)
        sys.exit(1)
    IN_CSV.parent.mkdir(parents=True, exist_ok=True)
    sql = (
        r"\copy (select slug, latin_name, "
        r"coalesce(taxon_group, '') as taxon_group "
        r"from organisms where rank = 'unmatched' "
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


def gbif_match_with_hint(name: str, hint: dict[str, str], cache: dict[str, dict]) -> dict | None:
    cache_key = f"{name}|{urlencode(sorted(hint.items()))}" if hint else name
    if cache_key in cache:
        return cache[cache_key]
    params = {"name": name, **hint}
    url = f"{GBIF_BASE}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  gbif error for {name!r} {hint}: {e}", file=sys.stderr)
        return None
    cache[cache_key] = data
    return data


def is_useful(m: dict | None) -> bool:
    return bool(m) and m.get("matchType") not in (None, "NONE") and bool(
        m.get("kingdom") or m.get("genus") or m.get("family")
    )


def clean_candidates(latin: str) -> list[str]:
    name = (latin or "").strip()
    out: list[str] = []
    if not name: return out
    out.append(name)
    # Strip 'spec.', 'spp.', etc. (this version of the regex catches "spec")
    stripped = re.sub(r"\s+(spec|sp|spp|esp|indet|etc)\.?\s*$", "", name, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped and stripped != name:
        out.append(stripped)
    # First two capitalised words (binomial guess)
    words = re.findall(r"[A-Z][a-z]+", name)
    if len(words) >= 2:
        out.append(f"{words[0]} {words[1]}")
    if words:
        out.append(words[0])
    seen, dedup = set(), []
    for c in out:
        if c not in seen:
            seen.add(c); dedup.append(c)
    return dedup


def species_epithet(scientific: str | None, genus: str | None) -> str | None:
    if not scientific: return None
    parts = scientific.replace("(", " ").split()
    if not parts: return None
    if genus and len(parts) >= 2 and parts[0] == genus:
        return parts[1].lower()
    if len(parts) >= 2:
        return parts[1].lower()
    return None


def main() -> int:
    print("[step 1/2] pulling unmatched from Supabase…")
    n = pull_unmatched()
    print(f"  {n} unmatched rows")

    cache: dict[str, dict] = {}
    if CACHE.exists():
        try: cache = json.loads(CACHE.read_text())
        except Exception: cache = {}

    print("[step 2/2] retrying GBIF with taxon-group hints…")
    rows = list(csv.DictReader(IN_CSV.open(newline="", encoding="utf-8")))
    out_rows: list[dict[str, str]] = []
    n_fixed = 0
    for r in rows:
        slug, latin, tg = r["slug"], r["latin_name"], r.get("taxon_group", "").strip()
        hint = TAXON_HINT.get(tg, {})
        out: dict[str, str] = {k: "" for k in FIELDS}
        out["slug"], out["latin_name"] = slug, latin
        matched, used = None, None
        for cand in clean_candidates(latin):
            m = gbif_match_with_hint(cand, hint, cache)
            if is_useful(m):
                matched, used = m, cand; break
            # If hint was set, also try unhinted (sometimes GBIF still has it but the hint conflicts)
            if hint:
                m2 = gbif_match_with_hint(cand, {}, cache)
                if is_useful(m2):
                    matched, used = m2, cand; break
            time.sleep(0.02)
        if matched:
            out["query_name"]      = used or ""
            out["rank"]            = (matched.get("rank") or "").lower()
            out["kingdom"]         = matched.get("kingdom", "") or ""
            out["phylum"]          = matched.get("phylum", "") or ""
            out["class_name"]      = matched.get("class", "") or ""
            out["order_name"]      = matched.get("order", "") or ""
            out["family"]          = matched.get("family", "") or ""
            out["genus"]           = matched.get("genus", "") or ""
            out["species"]         = species_epithet(matched.get("species"), matched.get("genus")) or ""
            out["scientific_name"] = matched.get("scientificName", "") or ""
            out["match_type"]      = matched.get("matchType", "") or ""
            out["confidence"]      = str(matched.get("confidence", "") or "")
            n_fixed += 1
        else:
            out["rank"] = "unmatched"
        out_rows.append(out)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out_rows)
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))
    print(f"wrote {OUT_CSV.relative_to(REPO)}: {len(out_rows)} rows ({n_fixed} fixed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
