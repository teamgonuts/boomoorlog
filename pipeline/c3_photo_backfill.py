"""
Backfill missing CC-licensed photos for the small set of organisms whose
pic_file isn't on disk. Reads data/organism_tags.csv, finds rows where
`has_photo == 'false'` and there's a usable photo lead (either a direct
URL in `photo_suggestion`, or a Latin name we can ask iNaturalist about),
downloads the photo into data/organism_photos/<slug>.jpg, and reports.

The download path matches the convention web/lib/organisms.ts knows about
(data/organism_photos/* → /organism_photos/*).

Idempotent: skips a slug if its target file already exists.

Usage:
    python3 pipeline/c3_photo_backfill.py
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
TAGS_CSV = REPO / "data" / "organism_tags.csv"
PHOTOS_DIR = REPO / "data" / "organism_photos"
REPORT = REPO / "data" / "organism_photos_backfill.csv"

UA = "creatures-ams/0.1 (https://github.com/teamgonuts/boomoorlog)"
INAT_TAXA = "https://api.inaturalist.org/v1/taxa?q={}&per_page=1"


def fetch_json(url: str) -> dict | None:
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  fetch error: {e}", file=sys.stderr)
        return None


def fetch_bytes(url: str) -> bytes | None:
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=30) as r:
            return r.read()
    except Exception as e:
        print(f"  download error: {e}", file=sys.stderr)
        return None


def looks_like_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s))


def inat_lookup_photo(latin: str) -> tuple[str | None, str | None]:
    """Returns (photo_url, license) for the iNat default photo of the taxon."""
    if not latin:
        return None, None
    name = latin.split("/")[0].split(",")[0].strip()  # first variant only
    if not name:
        return None, None
    data = fetch_json(INAT_TAXA.format(quote(name)))
    if not data:
        return None, None
    results = data.get("results") or []
    if not results:
        return None, None
    photo = (results[0] or {}).get("default_photo") or {}
    return photo.get("medium_url"), photo.get("license_code")


def main() -> int:
    if not TAGS_CSV.exists():
        print(f"error: {TAGS_CSV} not found — run pipeline/c3_aggregate.py first")
        return 1

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    with TAGS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    missing = [r for r in rows if r["has_photo"] != "true"]
    print(f"{len(missing)} organisms missing photo on disk")

    report_rows = []
    for row in missing:
        slug = row["slug"]
        latin = row["latin_name"]
        suggestion = (row.get("photo_suggestion") or "").strip()
        target = PHOTOS_DIR / f"{slug}.jpg"

        result = {
            "slug": slug,
            "latin_name": latin,
            "suggestion": suggestion[:120],
            "status": "",
            "source_url": "",
            "license": "",
            "saved_to": "",
        }

        if target.exists():
            result["status"] = "already-on-disk"
            report_rows.append(result)
            print(f"[skip ] {slug}: already on disk")
            continue

        photo_url, license_code = None, None
        if looks_like_url(suggestion):
            photo_url = suggestion
            license_code = "agent-suggested"
        else:
            # Skip placeholder-only rows that don't represent a real species.
            if not latin or latin.lower() in ("qualitative",):
                result["status"] = "skipped-non-species"
                print(f"[skip ] {slug}: not a real species, no Latin name")
                report_rows.append(result)
                continue
            photo_url, license_code = inat_lookup_photo(latin)

        if not photo_url:
            result["status"] = "no-photo-found"
            print(f"[fail ] {slug}: no photo found")
            report_rows.append(result)
            continue

        data = fetch_bytes(photo_url)
        if not data:
            result["status"] = "download-failed"
            result["source_url"] = photo_url
            print(f"[fail ] {slug}: download failed for {photo_url}")
            report_rows.append(result)
            continue

        target.write_bytes(data)
        result["status"] = "downloaded"
        result["source_url"] = photo_url
        result["license"] = license_code or ""
        result["saved_to"] = str(target.relative_to(REPO))
        print(f"[ok   ] {slug}: → {target.relative_to(REPO)}  ({license_code or 'no-license'})")
        report_rows.append(result)
        time.sleep(0.3)  # gentle rate-limit

    with REPORT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["slug", "latin_name", "suggestion", "status", "source_url", "license", "saved_to"],
        )
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"\nreport: {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
