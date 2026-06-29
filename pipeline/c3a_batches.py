"""
Split the top-N most-observed long-tail organisms into research batches
for the C3.A sub-agent pass. The orchestrator (or a human) reads
data/c3a_batches/progress.json to know which batches still need work,
making the whole pipeline resumable across multiple conversations /
credit windows.

Usage:
    python3 pipeline/c3a_batches.py          # default: top 300, 30/batch
    python3 pipeline/c3a_batches.py --top 500 --batch 25
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
OUT_DIR = REPO / "data" / "c3a_batches"
PROGRESS = OUT_DIR / "progress.json"

# Pull the highest-observation rows that already have a real category
# (i.e. not still in 'other' with no GBIF class). These are the ones
# whose default may not fit and where sub-agent overrides add real value.
PULL_SQL = """
\\copy (
  select
    o.slug,
    o.latin_name,
    coalesce(o.common_name, '')  as common_name,
    o.category,
    coalesce(o.family, '')       as family,
    coalesce(o.genus, '')        as genus,
    coalesce(o.taxon_group, '')  as taxon_group,
    o.observations_count
  from organisms o
 where o.category != 'tree'
   and o.category != 'other'                -- skip GBIF-unmatched: they need the C3.B pass
   and array_length(o.habitat_classes, 1) = 1   -- only default-tagged rows (curated overrides have >1 OR were already overridden)
   and o.tags_source is null                 -- never overridden yet (column doesn't exist yet; harmless)
   and o.observations_count > 0
 order by o.observations_count desc, o.slug
 limit {top_n}
) to '{out_path}' csv header
"""


def pull_candidates(top_n: int, out_path: Path) -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: set SUPABASE_DB_URL (source .env)", file=sys.stderr)
        sys.exit(1)
    # The `tags_source` filter would only work if that column existed; remove it
    # for now since we don't track per-row override history yet.
    sql = (
        r"\copy (select o.slug, o.latin_name, "
        r"coalesce(o.common_name, '') as common_name, o.category, "
        r"coalesce(o.family, '') as family, coalesce(o.genus, '') as genus, "
        r"coalesce(o.taxon_group, '') as taxon_group, o.observations_count "
        r"from organisms o "
        r"where o.category != 'tree' and o.category != 'other' "
        r"and array_length(o.habitat_classes, 1) = 1 "
        r"and o.observations_count > 0 "
        f"order by o.observations_count desc, o.slug limit {top_n}) "
        f"to '{out_path.as_posix()}' csv header"
    )
    r = subprocess.run(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    # Count rows in the output (header + N rows)
    with out_path.open() as f:
        n = sum(1 for _ in f) - 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=300,
                    help="how many most-observed species to send to sub-agents")
    ap.add_argument("--batch", type=int, default=30, help="organisms per batch")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates_csv = OUT_DIR / "candidates.csv"

    print(f"[1/2] pulling top-{args.top} most-observed default-tagged organisms…")
    n_pulled = pull_candidates(args.top, candidates_csv)
    print(f"      wrote {candidates_csv.relative_to(REPO)}: {n_pulled} rows")

    print(f"[2/2] splitting into batches of {args.batch}…")
    with candidates_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n_batches = (len(rows) + args.batch - 1) // args.batch
    manifest: list[dict[str, object]] = []
    for i in range(n_batches):
        chunk = rows[i * args.batch : (i + 1) * args.batch]
        path = OUT_DIR / f"batch_{i:02d}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(chunk)
        manifest.append({
            "index": i,
            "path": str(path.relative_to(REPO)),
            "count": len(chunk),
            "first": chunk[0]["slug"],
            "last": chunk[-1]["slug"],
        })

    # progress.json — written/updated by the sub-agent wave runner. Initial
    # state: every batch is 'pending'; the runner flips them to 'done' once
    # the corresponding batch_NN_tagged.csv has been written.
    progress_state = {
        "total": len(rows),
        "batch_size": args.batch,
        "n_batches": n_batches,
        "batches": [
            {"index": b["index"], "path": b["path"], "status": "pending"}
            for b in manifest
        ],
        "manifest": manifest,
    }
    # Don't clobber existing progress if running on identical batches —
    # preserves the 'done' flags from a prior wave.
    if PROGRESS.exists():
        try:
            prior = json.loads(PROGRESS.read_text())
            prior_done = {
                b["index"] for b in prior.get("batches", [])
                if b.get("status") == "done"
            }
            for b in progress_state["batches"]:
                if b["index"] in prior_done:
                    b["status"] = "done"
        except Exception:
            pass
    PROGRESS.write_text(json.dumps(progress_state, indent=2))

    pending = sum(1 for b in progress_state["batches"] if b["status"] != "done")
    print(f"      wrote {n_batches} batches, {pending} pending")
    print(f"      manifest: {PROGRESS.relative_to(REPO)}")


if __name__ == "__main__":
    main()
