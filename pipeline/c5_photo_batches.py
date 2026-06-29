"""
C5 — Build batches for sub-agent photo collection.

Pulls every organism still missing a photo_path, prioritised by
observations_count descending (most-seen species first — they're the ones
most likely to be visible to users), then splits into batches that sonnet
sub-agents can process in parallel.

Each sub-agent's job: per organism, look up the iNaturalist taxon, fetch
candidate photos, vision-QA them for "clear, full-body, recognisable",
and save the chosen photo to data/organism_photos/<slug>.jpg. Resume
protocol mirrors C3.A and C4 — see data/c5_batches/RESUME.md.

Usage:
    source .env
    python3 pipeline/c5_photo_batches.py --batch 25
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR  = REPO / "data" / "c5_batches"
PROGRESS = OUT_DIR / "progress.json"
PHOTOS_DIR = REPO / "data" / "organism_photos"


def pull_missing_photos(out_path: Path) -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL not set", file=sys.stderr); sys.exit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sql = (
        r"\copy (select slug, latin_name, "
        r"coalesce(common_name, '') as common_name, "
        r"category, "
        r"coalesce(family, '') as family, "
        r"coalesce(genus, '') as genus, "
        r"observations_count "
        r"from organisms "
        r"where (photo_path is null or photo_path = '') "
        r"and category != 'tree' "  # trees use a separate /photos/ folder and the user has been adding them by hand
        r"order by observations_count desc nulls last, slug) "
        f"to '{out_path.as_posix()}' csv header"
    )
    r = subprocess.run(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr); sys.exit(r.returncode)
    with out_path.open() as f:
        return sum(1 for _ in f) - 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=25,
                    help="organisms per batch (smaller than C4 because vision QA is heavier)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = OUT_DIR / "candidates.csv"

    print(f"[1/2] pulling organisms missing photo_path…")
    n = pull_missing_photos(candidates)
    print(f"      {n} rows")
    if n == 0:
        print("      every organism already has a photo — nothing to do")
        return

    with candidates.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n_batches = (len(rows) + args.batch - 1) // args.batch
    manifest = []
    for i in range(n_batches):
        chunk = rows[i * args.batch : (i + 1) * args.batch]
        p = OUT_DIR / f"batch_{i:02d}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader(); w.writerows(chunk)
        manifest.append({
            "index": i, "path": str(p.relative_to(REPO)),
            "count": len(chunk), "first": chunk[0]["slug"], "last": chunk[-1]["slug"],
        })

    state = {
        "total": len(rows), "batch_size": args.batch, "n_batches": n_batches,
        "batches": [{"index": b["index"], "path": b["path"], "status": "pending"} for b in manifest],
        "manifest": manifest,
    }
    if PROGRESS.exists():
        try:
            prior = json.loads(PROGRESS.read_text())
            done = {b["index"] for b in prior.get("batches", []) if b.get("status") == "done"}
            for b in state["batches"]:
                if b["index"] in done:
                    b["status"] = "done"
        except Exception:
            pass
    PROGRESS.write_text(json.dumps(state, indent=2))

    pending = sum(1 for b in state["batches"] if b["status"] != "done")
    print(f"[2/2] {n_batches} batches × {args.batch} ({pending} pending)")
    print(f"      manifest: {PROGRESS.relative_to(REPO)}")
    print(f"      photos land in: {PHOTOS_DIR.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
