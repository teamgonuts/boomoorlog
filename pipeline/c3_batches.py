"""
Split data/c3_inventory.csv into batch files for parallel research.

The C3 labeling pass farms out organisms to parallel agents. This script
writes one CSV per batch under data/c3_batches/batch_NN.csv plus a manifest
listing the slug ranges, so the orchestrator (and a re-runner later) can
reproduce the split.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_CSV = REPO / "data" / "c3_inventory.csv"
OUT_DIR = REPO / "data" / "c3_batches"
MANIFEST = OUT_DIR / "manifest.json"

# 11 batches over 319 organisms ~= 29/batch. Small enough that each agent's
# prompt stays comfortably under 4KB of batch payload.
BATCH_COUNT = 11


def main() -> None:
    with IN_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    # Even split: distribute remainder across the first N batches.
    base = total // BATCH_COUNT
    remainder = total % BATCH_COUNT

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    batches: list[dict[str, object]] = []
    idx = 0
    for i in range(BATCH_COUNT):
        size = base + (1 if i < remainder else 0)
        batch = rows[idx : idx + size]
        idx += size

        out_path = OUT_DIR / f"batch_{i:02d}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(batch)

        batches.append({
            "index": i,
            "path": str(out_path.relative_to(REPO)),
            "count": len(batch),
            "first": batch[0]["slug"],
            "last":  batch[-1]["slug"],
        })

    with MANIFEST.open("w", encoding="utf-8") as f:
        json.dump({"total": total, "batches": batches}, f, indent=2)

    print(f"split {total} organisms into {BATCH_COUNT} batches:")
    for b in batches:
        print(f"  {b['path']}: {b['count']:>3} rows  ({b['first']} … {b['last']})")


if __name__ == "__main__":
    main()
