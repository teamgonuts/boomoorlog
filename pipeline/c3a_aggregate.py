"""
C3.A aggregator. Merges every data/c3a_batches/batch_NN_tagged.csv that
exists on disk into one canonical override file (data/c3a_overrides.csv).
Migration 030 ingests that file.

Also flips progress.json entries to status='done' for any batch whose
tagged CSV exists — keeps the resume protocol accurate.

Re-runnable; idempotent.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BATCH_DIR = REPO / "data" / "c3a_batches"
PROGRESS  = BATCH_DIR / "progress.json"
OUT       = REPO / "data" / "c3a_overrides.csv"

FIELDS = [
    "slug",
    "category",
    "habitat_classes",
    "movement_classes",
    "source",
    "reason",
    "photo_suggestion",
]


def main() -> None:
    # Sync progress.json status with what's on disk.
    progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else None
    if progress is None:
        print("error: progress.json missing — run pipeline/c3a_batches.py first")
        return

    done_count = 0
    for b in progress["batches"]:
        idx = b["index"]
        tagged = BATCH_DIR / f"batch_{idx:02d}_tagged.csv"
        if tagged.exists():
            b["status"] = "done"
            done_count += 1
        else:
            b["status"] = "pending"
    PROGRESS.write_text(json.dumps(progress, indent=2))

    print(f"{done_count} / {len(progress['batches'])} batches done")

    # Aggregate.
    rows: list[dict[str, str]] = []
    for b in progress["batches"]:
        if b["status"] != "done":
            continue
        idx = b["index"]
        tagged = BATCH_DIR / f"batch_{idx:02d}_tagged.csv"
        with tagged.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                # Some sub-agents may include extra columns; pluck the ones we
                # care about and ignore the rest.
                rows.append({k: (r.get(k) or "") for k in FIELDS})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    overrides = sum(1 for r in rows if r["source"] == "override")
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} rows ({overrides} overrides)")


if __name__ == "__main__":
    main()
