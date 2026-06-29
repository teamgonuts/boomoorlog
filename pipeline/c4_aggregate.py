"""
Aggregate the C4 sub-agent name batches into one CSV ready for migration.
Also updates progress.json based on what's on disk.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BATCH_DIR = REPO / "data" / "c4_batches"
PROGRESS  = BATCH_DIR / "progress.json"
OUT       = REPO / "data" / "c4_names_resolved.csv"

FIELDS = ["slug", "latin_name", "common_name", "source"]


def main() -> None:
    progress = json.loads(PROGRESS.read_text())
    done = 0
    for b in progress["batches"]:
        tagged = BATCH_DIR / f"batch_{b['index']:02d}_named.csv"
        if tagged.exists():
            b["status"] = "done"
            done += 1
        else:
            b["status"] = "pending"
    PROGRESS.write_text(json.dumps(progress, indent=2))
    print(f"{done} / {len(progress['batches'])} batches complete")

    rows: list[dict[str, str]] = []
    for b in progress["batches"]:
        if b["status"] != "done":
            continue
        p = BATCH_DIR / f"batch_{b['index']:02d}_named.csv"
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({k: (r.get(k) or "") for k in FIELDS})

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

    resolved = sum(1 for r in rows if r["common_name"])
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} rows ({resolved} have a common name)")


if __name__ == "__main__":
    main()
