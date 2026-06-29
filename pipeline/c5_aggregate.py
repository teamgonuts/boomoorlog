"""
Aggregate C5 sub-agent photo batches into one CSV ready for migration.
Updates progress.json based on what's actually on disk.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BATCH_DIR = REPO / "data" / "c5_batches"
PROGRESS  = BATCH_DIR / "progress.json"
OUT       = REPO / "data" / "c5_photos.csv"
PHOTOS    = REPO / "data" / "organism_photos"

FIELDS = ["slug", "latin_name", "taxon_id", "photo_url", "photo_license",
          "attribution", "status", "note"]


def main() -> None:
    progress = json.loads(PROGRESS.read_text())
    done = 0
    for b in progress["batches"]:
        tagged = BATCH_DIR / f"batch_{b['index']:02d}_photos.csv"
        if tagged.exists():
            b["status"] = "done"; done += 1
        else:
            b["status"] = "pending"
    PROGRESS.write_text(json.dumps(progress, indent=2))
    print(f"{done} / {len(progress['batches'])} batches complete")

    rows: list[dict[str, str]] = []
    for b in progress["batches"]:
        if b["status"] != "done":
            continue
        p = BATCH_DIR / f"batch_{b['index']:02d}_photos.csv"
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                # tolerate extra columns; pluck the ones we want
                rows.append({k: (r.get(k) or "") for k in FIELDS})

    # Drop rows where we don't actually have the photo on disk — protects
    # against status=ok but missing file (transient sub-agent download
    # failure, etc.)
    rows = [r for r in rows
            if r["status"] == "ok" and (PHOTOS / f"{r['slug']}.jpg").exists()
            or r["status"] != "ok"]

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

    ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} rows ({ok} ok)")


if __name__ == "__main__":
    main()
