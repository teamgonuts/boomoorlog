"""
C4 step 2 — build batches for sub-agent research of organisms still missing
a common_name after the iNat pass. Mirrors the C3.A batch structure so the
resume protocol is identical.

Usage:
    source .env
    python3 pipeline/c4_batches.py --batch 30
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
OUT_DIR  = REPO / "data" / "c4_batches"
PROGRESS = OUT_DIR / "progress.json"


def pull_unresolved(out_path: Path) -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL not set", file=sys.stderr); sys.exit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sql = (
        r"\copy (select slug, latin_name, "
        r"coalesce(taxon_group, '') as taxon_group, "
        r"coalesce(family, '') as family, "
        r"coalesce(genus, '') as genus, "
        r"observations_count "
        r"from organisms where common_name is null or common_name = '' "
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
    ap.add_argument("--batch", type=int, default=30)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = OUT_DIR / "candidates.csv"
    print(f"[1/2] pulling organisms missing common_name…")
    n = pull_unresolved(candidates)
    print(f"      {n} rows")

    if n == 0:
        print("      nothing to do — every organism has a common name")
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


if __name__ == "__main__":
    main()
