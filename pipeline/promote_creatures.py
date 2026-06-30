#!/usr/bin/env python3
"""Promote species from `observations` to first-class `creatures` rows.

Promotion rule (M11, locked):
  A species with >=3 sightings in the last 30 days AND no obs already pointing
  at a curated creature (creature_slug IS NULL) becomes a creature.

For each candidate (capped at 20 per run):
  - Pick best common_name (most-common non-null, else Latin)
  - Pick taxon_group (most-common non-null, mapped to English)
  - Slugify the Latin name
  - Fetch a CC-licensed photo from iNat
  - Fetch Wikipedia summary (EN then NL)
  - Save photo to web/public/creature_photos/{slug}.jpg AND data/creature_pics/
  - Insert creature row with source='auto_observed', sprite_pending=true
  - Update all matching observations to point at the new slug

This script does NOT generate sprites — that's a separate step.

Run `backfill_creature_matches.py` FIRST to populate creature_slug for species
that already match existing creatures; this script only considers obs with
creature_slug IS NULL.
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

import psycopg2
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
PHOTO_DIR_WEB = REPO / "web" / "public" / "creature_photos"
PHOTO_DIR_DATA = REPO / "data" / "creature_pics"

UA = "Boomoorlog/0.1 (promote_creatures.py)"
WIKI_UA = "boomoorlog/0.1 (promote_creatures.py)"
ACCEPT_LICENSES = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}

# Waarneming numeric group -> English; iNat strings collapsed to same buckets.
TAXON_MAP = {
    "1": "Birds", "2": "Mammals", "3": "Reptiles & Amphibians",
    "4": "Butterflies", "5": "Dragonflies", "6": "Insects (other)",
    "7": "Molluscs", "8": "Moths", "9": "Fish",
    "13": "Other Arthropods", "14": "Locusts & Crickets",
    "15": "Bugs & Cicadas", "16": "Beetles", "17": "Bees, Wasps & Ants",
    "18": "Flies", "20": "Other Invertebrates",
    # iNat class strings
    "Aves": "Birds", "Mammalia": "Mammals", "Reptilia": "Reptiles & Amphibians",
    "Amphibia": "Reptiles & Amphibians", "Insecta": "Insects (other)",
    "Lepidoptera": "Butterflies", "Odonata": "Dragonflies",
    "Mollusca": "Molluscs", "Actinopterygii": "Fish",
    "Arachnida": "Other Arthropods", "Coleoptera": "Beetles",
    "Hymenoptera": "Bees, Wasps & Ants", "Diptera": "Flies",
}


def load_env(path: Path = REPO / ".env") -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s)


def map_taxon(raw):
    if not raw:
        return None
    return TAXON_MAP.get(str(raw).strip(), str(raw).strip())


# ---- iNat photo ----

def _http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def get_species_photo(latin_name):
    qs = urlencode({"q": latin_name, "rank": "species"})
    try:
        taxa = _http_json(f"https://api.inaturalist.org/v1/taxa?{qs}").get("results", [])
    except Exception:
        return None
    if not taxa:
        return None
    taxon = taxa[0]
    taxon_id = taxon["id"]
    dp = taxon.get("default_photo") or {}
    if dp.get("license_code") in ACCEPT_LICENSES:
        ext = dp["url"].rsplit(".", 1)[-1]
        return {
            "url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{dp['id']}/large.{ext}",
            "license": dp["license_code"],
            "attribution": dp.get("attribution", ""),
        }
    qs2 = urlencode({
        "taxon_id": taxon_id,
        "photo_license": ",".join(ACCEPT_LICENSES),
        "quality_grade": "research",
        "order_by": "votes",
        "per_page": 1,
    })
    try:
        obs = _http_json(f"https://api.inaturalist.org/v1/observations?{qs2}").get("results", [])
    except Exception:
        return None
    if not obs or not obs[0].get("photos"):
        return None
    photo = next((p for p in obs[0]["photos"] if p.get("license_code") in ACCEPT_LICENSES), None)
    if not photo:
        return None
    ext = photo["url"].rsplit(".", 1)[-1]
    return {
        "url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{photo['id']}/large.{ext}",
        "license": photo["license_code"],
        "attribution": photo.get("attribution", ""),
    }


# ---- Wikipedia ----

def fetch_wikipedia_summary(latin_name, lang="en"):
    title = latin_name.replace(" ", "_")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("type") == "disambiguation":
                return None
            return data.get("extract")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 429:
            time.sleep(int(e.headers.get("Retry-After", 5)))
            return fetch_wikipedia_summary(latin_name, lang)
        return None
    except Exception:
        return None


def get_summary(latin_name):
    return fetch_wikipedia_summary(latin_name, "en") or fetch_wikipedia_summary(latin_name, "nl")


# ---- Photo save ----

def save_photo_jpg(photo_url, out_paths):
    req = urllib.request.Request(photo_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    img = Image.open(io.BytesIO(data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    for out_path in out_paths:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=90)


# ---- Candidates ----

# Non-creature taxon groups to exclude from promotion. Plants are already
# `trees`; fungi/mosses/algae/disturbances are out of scope for the creature
# roster. Apply at SQL level for cheapness — observations with any of these
# taxon_group values never reach the candidate set.
#   waarneming: 10=Plants, 11=Fungi, 12=Mosses & Lichens,
#               19=Algae & unicellular, 30=Disturbances
#   inat (iconic taxon name): Plantae, Fungi, Protozoa, Chromista
NON_CREATURE_GROUPS = (
    '10', '11', '12', '19', '30',
    'Plantae', 'Fungi', 'Protozoa', 'Chromista',
)

CANDIDATES_SQL = """
select scientific_name,
       count(*) as cnt,
       array_agg(common_name) as common_names,
       array_agg(taxon_group) as taxon_groups
from observations
where observed_on >= (current_date - interval '30 days')
  and creature_slug is null
  and scientific_name is not null
  and scientific_name <> ''
  and (taxon_group is null or taxon_group <> all(%s))
group by scientific_name
having count(*) >= 3
order by count(*) desc
"""


def pick_most_common(values):
    vals = [v for v in values if v]
    if not vals:
        return None
    return Counter(vals).most_common(1)[0][0]


def fetch_candidates(cur):
    cur.execute(CANDIDATES_SQL, (list(NON_CREATURE_GROUPS),))
    out = []
    for sci, cnt, common_names, taxon_groups in cur.fetchall():
        best_common = pick_most_common(common_names) or sci
        best_taxon = map_taxon(pick_most_common(taxon_groups))
        out.append({
            "scientific_name": sci,
            "count": cnt,
            "common_name": best_common,
            "taxon_group": best_taxon,
        })
    return out


INSERT_SQL = """
insert into creatures (
    slug, common_name, latin_name, pic_file, tree_count, tree_genera,
    source, promoted_at, taxon_group, wikipedia_summary,
    observations_count, sprite_pending
) values (
    %s, %s, %s, %s, 0, '{}'::text[],
    'auto_observed', now(), %s, %s,
    %s, true
) on conflict (slug) do nothing
returning slug
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print, don't touch DB or download photos")
    ap.add_argument("--max", type=int, default=20, help="cap on promotions this run (default 20)")
    args = ap.parse_args()

    env = load_env()
    db_url = env.get("SUPABASE_DB_URL")
    if not db_url:
        sys.exit("SUPABASE_DB_URL missing from .env")

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    candidates = fetch_candidates(cur)
    print(f"Candidates: {len(candidates)} species >=3 obs in last 30d (after backfill match)")
    if not candidates:
        return

    cap = args.max
    print(f"Promoting up to {cap}:")

    promoted = 0
    skipped = 0
    relinked_total = 0

    for c in candidates:
        if promoted >= cap:
            break
        sci = c["scientific_name"]
        slug = slugify(sci)
        common = c["common_name"]
        taxon = c["taxon_group"] or ""
        cnt = c["count"]

        if args.dry_run:
            print(f"  ~ {sci} -> {slug} ({common}, {taxon}, {cnt} obs) [dry-run]")
            promoted += 1
            continue

        # Check slug collision (curated creature with same slug)
        cur.execute("select 1 from creatures where slug = %s", (slug,))
        if cur.fetchone():
            print(f"  x {sci} -> {slug} - slug exists (curated?), skipped")
            skipped += 1
            continue

        # Photo
        photo = get_species_photo(sci)
        if not photo:
            print(f"  x {sci} - no photo found, skipped")
            skipped += 1
            continue

        # Wikipedia
        summary = get_summary(sci)

        # Save photo to both locations
        web_path = PHOTO_DIR_WEB / f"{slug}.jpg"
        data_path = PHOTO_DIR_DATA / f"{slug}.jpg"
        try:
            save_photo_jpg(photo["url"], [web_path, data_path])
        except Exception as e:
            print(f"  x {sci} - photo save failed ({e}), skipped")
            skipped += 1
            continue

        pic_file = f"data/creature_pics/{slug}.jpg"

        # Insert creature + re-link obs in one txn
        try:
            cur.execute(INSERT_SQL, (
                slug, common, sci, pic_file,
                taxon or None, summary, cnt,
            ))
            inserted = cur.fetchone()
            if not inserted:
                print(f"  x {sci} -> {slug} - insert conflict, skipped")
                skipped += 1
                conn.rollback()
                continue
            cur.execute(
                "update observations set creature_slug = %s "
                "where creature_slug is null and scientific_name = %s",
                (slug, sci),
            )
            relinked = cur.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"  x {sci} -> {slug} - db error ({e}), skipped")
            skipped += 1
            continue

        wiki_mark = "y" if summary else "-"
        print(f"  + {sci} -> {slug} ({common}, {taxon}, {cnt} obs, "
              f"photo {photo['license']}, wiki {wiki_mark}, {relinked} obs re-linked)")
        promoted += 1
        relinked_total += relinked
        # Small delay to be polite to iNat / Wikipedia
        time.sleep(0.5)

    print(f"\nPromoted: {promoted} - skipped: {skipped} - obs re-linked: {relinked_total}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
