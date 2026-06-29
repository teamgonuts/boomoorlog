"""
GBIF taxonomy enrichment for the organisms inventory.

For every row in data/creatures.csv, hit the GBIF Species Match API and
record the full taxonomy chain (kingdom → phylum → class → order → family
→ genus → species) plus the `rank` of the matched name. Output goes to
data/organisms_taxonomy.csv, which migration 025 ingests into the
`organisms` table.

Why GBIF: free, no key, well-known canonical taxonomy. The /species/match
endpoint takes a name and returns a single best-match record with the
full ancestry chain.

Run idempotently: writes a single CSV; existing rows are overwritten in
place. Caches successful matches in data/.taxonomy_cache.json so repeat
runs only hit GBIF for new / unresolved names.

Handles the messy bits of creatures.csv:
- "Aceria / Eriophyidae" (alternate Latin names): tries each split.
- "Apis spp.", "Bombus sp.": strips the suffix and matches the genus.
- "Aphidoidea, generalist greenfly" (free text): splits on comma and
  tries the first part.
- Compound slugs (wood-pigeon-magpie-carrion-crow) with no clean Latin:
  marked rank=compound, taxonomy left blank.

Usage:
    python3 pipeline/enrich_taxonomy.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
IN_CSV    = REPO / "data" / "creatures.csv"
OUT_CSV   = REPO / "data" / "organisms_taxonomy.csv"
CACHE     = REPO / "data" / ".taxonomy_cache.json"

GBIF_URL = "https://api.gbif.org/v1/species/match?name={}"
UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"

FIELDS = [
    "slug",
    "latin_name",          # original from creatures.csv
    "query_name",          # what we actually sent to GBIF
    "rank",                # 'species'|'genus'|'family'|...|'compound'|'unmatched'
    "kingdom",
    "phylum",
    "class_name",
    "order_name",
    "family",
    "genus",
    "species",             # epithet only
    "scientific_name",     # canonical from GBIF
    "match_type",
    "confidence",
]


def clean_for_match(latin: str) -> list[str]:
    """
    Produce an ordered list of candidate names to try against GBIF.

    Strategy: progressively simpler. First try the raw name. Then split
    on '/' and ',' to handle the "Aceria / Eriophyidae" pattern. Then
    strip "spp.", "sp.", and parenthetical annotations to get the bare
    binomial / genus.
    """
    name = latin.strip()
    candidates: list[str] = []

    if not name:
        return candidates

    # Try the raw thing first — GBIF is fairly forgiving.
    candidates.append(name)

    # Split on '/' and ',' — first part of each is usually the dominant taxon.
    for sep in [" / ", "/", ", ", ","]:
        if sep in name:
            for part in name.split(sep):
                part = part.strip()
                if part:
                    candidates.append(part)

    # Strip "spp.", "sp.", "indet.", "esp." and similar.
    stripped = re.sub(r"\b(spp|sp|esp|incl|including|etc|indet)\.?\b", "",
                      name, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip(" ,")
    if stripped and stripped != name:
        candidates.append(stripped)

    # If we have a "Family Genus" or "Genus species, Family", take just
    # the first two words as a binomial guess.
    words = re.findall(r"[A-Z][a-z]+", name)
    if len(words) >= 2:
        candidates.append(f"{words[0]} {words[1]}")
    if words:
        candidates.append(words[0])

    # Dedup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def gbif_match(name: str, cache: dict[str, dict]) -> dict | None:
    """Hit GBIF /species/match with caching. Returns the raw JSON or None."""
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
    """Filter out GBIF's NONE / HIGHERRANK / no-match responses."""
    if not m:
        return False
    if m.get("matchType") in (None, "NONE"):
        return False
    # Must at least know the kingdom for it to be useful.
    return bool(m.get("kingdom") or m.get("genus") or m.get("family"))


def best_match(latin: str, cache: dict[str, dict]) -> tuple[str | None, dict | None]:
    """Try each cleaned candidate; return (query_name, match) for the first useful hit."""
    for cand in clean_for_match(latin):
        m = gbif_match(cand, cache)
        if is_useful_match(m):
            return cand, m
    return None, None


def species_epithet(scientific: str | None, genus: str | None) -> str | None:
    """Extract the species epithet from 'Genus species (Author)' format."""
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


def looks_compound(slug: str, latin: str) -> bool:
    """Heuristic: slugs / names that bundle multiple taxa."""
    indicators = ["+", " and ", " & ", ";"]
    if any(ind in latin for ind in indicators):
        return True
    # multi-hyphen slugs that aren't simple binomials
    if slug.count("-") >= 3:
        # might still be a clean binomial (e.g. "common-eurasian-blackbird")
        # but usually compound. Trust the latin_name check too.
        if any(ind in latin for ind in [",", "/"]):
            # already handled by candidate splitting; only mark compound
            # if even the candidates fail.
            return False
    return False


def main() -> int:
    cache: dict[str, dict] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}

    with IN_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows: list[dict[str, str]] = []
    n_matched = 0
    n_compound = 0
    n_unmatched = 0

    for i, r in enumerate(rows, 1):
        slug = r["slug"]
        latin = r.get("latin_name", "").strip()

        out: dict[str, str] = {k: "" for k in FIELDS}
        out["slug"] = slug
        out["latin_name"] = latin

        # Detect obvious compound entries first.
        if not latin or looks_compound(slug, latin):
            out["rank"] = "compound"
            n_compound += 1
            out_rows.append(out)
            if i % 25 == 0:
                print(f"[{i:>3}/{len(rows)}] {slug:<40s} compound")
            continue

        query_name, m = best_match(latin, cache)
        if not m:
            out["rank"] = "unmatched"
            n_unmatched += 1
        else:
            out["query_name"]       = query_name or ""
            out["rank"]             = (m.get("rank") or "").lower()
            out["kingdom"]          = m.get("kingdom", "") or ""
            out["phylum"]           = m.get("phylum", "") or ""
            out["class_name"]       = m.get("class", "") or ""
            out["order_name"]       = m.get("order", "") or ""
            out["family"]           = m.get("family", "") or ""
            out["genus"]            = m.get("genus", "") or ""
            out["species"]          = species_epithet(m.get("species"), m.get("genus")) or ""
            out["scientific_name"]  = m.get("scientificName", "") or ""
            out["match_type"]       = m.get("matchType", "") or ""
            out["confidence"]       = str(m.get("confidence", "") or "")
            n_matched += 1

        out_rows.append(out)
        if i % 25 == 0:
            print(f"[{i:>3}/{len(rows)}] {slug:<40s} {out['rank']:<12s} {out.get('genus','')}")

        # Gentle on GBIF.
        if query_name and query_name not in cache:
            time.sleep(0.05)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))

    print()
    print(f"wrote {OUT_CSV.relative_to(REPO)}: {len(out_rows)} rows")
    print(f"  matched:   {n_matched}")
    print(f"  compound:  {n_compound}")
    print(f"  unmatched: {n_unmatched}")
    print(f"cache: {len(cache)} entries → {CACHE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
