#!/usr/bin/env python3
"""Fetch wildlife observations (with photos) from iNaturalist and/or Observation.org
within an area + recent time window. Reusable for any future "what's been seen near
this address in the last X days" query.

Usage examples:
    # last 7 days within 1km of Dam Square, both sources, write merged CSV
    python fetch_observations.py --source both --lat 52.3702 --lng 4.8952 \
        --radius-km 1 --days 7 --out data/obs_dam_7d.csv

    # last 30 days, iNat only, also download photos
    python fetch_observations.py --source inat --lat 52.3702 --lng 4.8952 \
        --radius-km 2 --days 30 --out data/obs_inat_30d.csv \
        --download-photos data/obs_photos

    # bounding box instead of point+radius (iNat only — Observation.org doesn't
    # honour bbox on the public endpoint)
    python fetch_observations.py --source inat --bbox 4.728,52.278,5.079,52.431 \
        --days 1 --out data/obs_ams_today.csv

Output CSV columns (unified across both sources):
    source            inat | waarneming
    obs_id            source-native observation id
    observed_on       ISO date
    lat, lng          point coords (WGS84)
    accuracy_m        positional accuracy in metres if known
    scientific_name   e.g. "Quercus robur"
    common_name       e.g. "English oak" (may be empty)
    taxon_group       iconic taxon (Animalia/Plantae/Insecta/Aves/...) or species_group id
    quality           inat: research|needs_id|casual · waarneming: rarity 1-4
    photo_url         first photo URL (may be empty)
    photo_license     inat per-photo license code; empty for waarneming
    permalink         link back to the observation
"""

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

UA = "Boomoorlog/0.1 (https://github.com/; data fetch script)"


def http_get(url: str, retries: int = 3) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


# ---------------------------------------------------------------- iNaturalist

def fetch_inat(lat, lng, radius_km, bbox, since, max_results) -> list[dict]:
    """Page iNat observations endpoint until exhausted or max_results hit."""
    base = "https://api.inaturalist.org/v1/observations"
    common = {"per_page": "200", "order": "desc", "order_by": "observed_on",
              "d1": since.isoformat()}
    if bbox:
        swlng, swlat, nelng, nelat = bbox
        common.update(swlng=str(swlng), swlat=str(swlat), nelng=str(nelng), nelat=str(nelat))
    else:
        common.update(lat=str(lat), lng=str(lng), radius=str(radius_km))

    out, page = [], 1
    while len(out) < max_results:
        params = dict(common, page=str(page))
        url = f"{base}?{urllib.parse.urlencode(params)}"
        data = http_get(url)
        results = data.get("results", [])
        if not results:
            break
        for r in results:
            geo = r.get("geojson") or {}
            coords = geo.get("coordinates") or [None, None]
            taxon = r.get("taxon") or {}
            photos = r.get("photos") or []
            p0 = photos[0] if photos else {}
            out.append({
                "source": "inat",
                "obs_id": r.get("id"),
                "observed_on": r.get("observed_on") or "",
                "lat": coords[1],
                "lng": coords[0],
                "accuracy_m": r.get("positional_accuracy") or "",
                "scientific_name": taxon.get("name") or "",
                "common_name": taxon.get("preferred_common_name") or "",
                "taxon_group": taxon.get("iconic_taxon_name") or "",
                "quality": r.get("quality_grade") or "",
                "photo_url": (p0.get("url") or "").replace("/square.", "/medium."),
                "photo_license": p0.get("license_code") or "",
                "permalink": r.get("uri") or f"https://www.inaturalist.org/observations/{r.get('id')}",
            })
            if len(out) >= max_results:
                break
        page += 1
        if page > 50:  # iNat hard-caps deep paging
            break
        time.sleep(1.0)  # respect ~60/min rate limit
    return out


# ------------------------------------------------------------ Observation.org

def fetch_waarneming(lat, lng, radius_km, since, max_results) -> list[dict]:
    """Page Observation.org /around-point/. Date filter is unreliable on this
    endpoint, so we sort by date desc and stop when we cross the cutoff."""
    base = "https://observation.org/api/v1/observations/around-point/"
    common = {"lat": str(lat), "lng": str(lng), "radius": str(int(radius_km * 1000)),
              "ordering": "-date", "limit": "500"}
    out, offset = [], 0
    while len(out) < max_results:
        params = dict(common, offset=str(offset))
        url = f"{base}?{urllib.parse.urlencode(params)}"
        data = http_get(url)
        results = data.get("results", [])
        if not results:
            break
        oldest_in_page = None
        for r in results:
            d = r.get("date") or ""
            if d:
                oldest_in_page = d if (oldest_in_page is None or d < oldest_in_page) else oldest_in_page
            if d and d < since.isoformat():
                continue  # skip older obs that snuck into the page
            pt = r.get("point") or {}
            coords = pt.get("coordinates") or [None, None]
            sp = r.get("species_detail") or {}
            photos = r.get("photos") or []
            out.append({
                "source": "waarneming",
                "obs_id": r.get("id"),
                "observed_on": d,
                "lat": coords[1],
                "lng": coords[0],
                "accuracy_m": r.get("accuracy") or "",
                "scientific_name": sp.get("scientific_name") or "",
                "common_name": sp.get("name") or "",
                "taxon_group": sp.get("group") or "",
                "quality": r.get("rarity") or "",
                "photo_url": photos[0] if photos else "",
                "photo_license": "",
                "permalink": r.get("permalink") or "",
            })
            if len(out) >= max_results:
                break
        if oldest_in_page and oldest_in_page < since.isoformat():
            break
        offset += 500
        time.sleep(0.5)
    return out


# --------------------------------------------------------------------- photos

def download_photos(rows: list[dict], out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in rows:
        url = r.get("photo_url")
        if not url:
            continue
        ext = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
        fname = f"{r['source']}_{r['obs_id']}{ext}"
        path = out_dir / fname
        if path.exists():
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp, open(path, "wb") as f:
                f.write(resp.read())
            n += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"  photo failed {url}: {e}", file=sys.stderr)
    return n


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["inat", "waarneming", "both"], default="both")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--radius-km", type=float, default=1.0)
    ap.add_argument("--bbox", help="swlng,swlat,nelng,nelat (iNat only)")
    ap.add_argument("--days", type=int, default=7, help="how many days back (default 7)")
    ap.add_argument("--max-results", type=int, default=5000, help="cap per source")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--download-photos", type=Path, help="if set, download photo files here")
    args = ap.parse_args()

    bbox = None
    if args.bbox:
        bbox = [float(x) for x in args.bbox.split(",")]
        if len(bbox) != 4:
            ap.error("--bbox needs 4 comma-separated floats")
    elif args.lat is None or args.lng is None:
        ap.error("provide either --lat/--lng or --bbox")

    since = date.today() - timedelta(days=args.days)
    print(f"fetching obs since {since} (last {args.days} days)")

    rows = []
    if args.source in ("inat", "both"):
        print("→ iNaturalist…")
        r = fetch_inat(args.lat, args.lng, args.radius_km, bbox, since, args.max_results)
        print(f"  {len(r)} obs")
        rows.extend(r)
    if args.source in ("waarneming", "both"):
        if bbox and not (args.lat and args.lng):
            print("  (skipping waarneming — needs --lat/--lng, not --bbox)", file=sys.stderr)
        else:
            print("→ Observation.org / Waarneming.nl…")
            r = fetch_waarneming(args.lat, args.lng, args.radius_km, since, args.max_results)
            print(f"  {len(r)} obs")
            rows.extend(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source", "obs_id", "observed_on", "lat", "lng", "accuracy_m",
              "scientific_name", "common_name", "taxon_group", "quality",
              "photo_url", "photo_license", "permalink"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows → {args.out}")

    uniq_species = {r["scientific_name"] for r in rows if r["scientific_name"]}
    print(f"  unique species: {len(uniq_species)}")

    if args.download_photos:
        print(f"→ downloading photos to {args.download_photos}…")
        n = download_photos(rows, args.download_photos)
        print(f"  downloaded {n} new photos")


if __name__ == "__main__":
    main()
