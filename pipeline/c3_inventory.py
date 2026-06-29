"""
C3 organism inventory builder.

Reads data/creatures.csv and emits data/c3_inventory.csv — the working file
the C3 labeling pass operates on. Each row records the minimal info the
parallel research agents need: slug, names, tree associations, whether a
photo already exists on disk.

Idempotent. Re-run any time creatures.csv changes.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CREATURES_CSV = REPO / "data" / "creatures.csv"
PIC_DIR = REPO / "data" / "creature_pics"
OUT_CSV = REPO / "data" / "c3_inventory.csv"

FIELDS = [
    "slug",
    "common_name",
    "latin_name",
    "tree_genera",
    "has_photo",
    "tree_count",
]


def main() -> None:
    rows: list[dict[str, str]] = []
    with CREATURES_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pic_path = (r.get("pic_file") or "").strip()
            has_photo = bool(pic_path) and (REPO / pic_path).exists()
            rows.append({
                "slug": r["slug"],
                "common_name": r["common_name"],
                "latin_name": r["latin_name"],
                "tree_genera": r.get("tree_genera", ""),
                "has_photo": "true" if has_photo else "false",
                "tree_count": r.get("tree_count", "0"),
            })

    # Sort by slug for deterministic batching downstream.
    rows.sort(key=lambda r: r["slug"])

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    has = sum(1 for r in rows if r["has_photo"] == "true")
    missing = len(rows) - has
    print(f"wrote {OUT_CSV.relative_to(REPO)}: {len(rows)} organisms")
    print(f"  with photo on disk:    {has}")
    print(f"  missing photo on disk: {missing}")


if __name__ == "__main__":
    main()
