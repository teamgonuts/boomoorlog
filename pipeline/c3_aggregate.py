"""
Aggregate the 11 C3 research-batch tagged CSVs into one canonical file,
joined with the GBIF taxonomy from data/organisms_taxonomy.csv and the
inventory metadata.

Inputs (all in data/):
  c3_inventory.csv                  — slug, common_name, latin_name, ...
  c3_batches/batch_NN_tagged.csv    — slug, category, habitat_classes, ...
  organisms_taxonomy.csv            — slug, rank, kingdom, phylum, ...

Output: data/organism_tags.csv — one row per organism with everything
merged. This is the artefact migration 026 (later) will use to populate
organisms' habitat_classes / movement_classes / lore / category /
category-default-source.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INVENTORY = REPO / "data" / "c3_inventory.csv"
BATCHES_DIR = REPO / "data" / "c3_batches"
TAXONOMY = REPO / "data" / "organisms_taxonomy.csv"
OUT = REPO / "data" / "organism_tags.csv"

OUT_FIELDS = [
    # identity
    "slug",
    "common_name",
    "latin_name",
    # behavior tags (from research agents)
    "category",
    "habitat_classes",
    "movement_classes",
    "source",                 # 'default' | 'override'
    "reason",
    # taxonomy (from GBIF)
    "rank",
    "kingdom",
    "phylum",
    "class_name",
    "order_name",
    "family",
    "genus",
    "species",
    # supplemental
    "has_photo",
    "tree_genera",
    "tree_count",
    "photo_suggestion",
]


def load_csv(path: Path) -> dict[str, dict[str, str]]:
    """Load a CSV keyed by slug."""
    out: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["slug"]] = row
    return out


def main() -> None:
    inventory = load_csv(INVENTORY)
    taxonomy = load_csv(TAXONOMY)

    # Merge all batch tagged CSVs into one slug→tags map.
    tags: dict[str, dict[str, str]] = {}
    for i in range(11):
        batch_path = BATCHES_DIR / f"batch_{i:02d}_tagged.csv"
        if not batch_path.exists():
            print(f"warn: missing {batch_path}")
            continue
        for row in load_csv(batch_path).values():
            tags[row["slug"]] = row

    # Compose one output row per inventory slug.
    rows = []
    n_missing_tags = 0
    n_missing_taxa = 0
    for slug, inv in inventory.items():
        t = tags.get(slug)
        tx = taxonomy.get(slug, {})
        if t is None:
            n_missing_tags += 1
            t = {}
        if not tx:
            n_missing_taxa += 1

        rows.append({
            "slug":             slug,
            "common_name":      inv.get("common_name", ""),
            "latin_name":       inv.get("latin_name", ""),
            "category":         t.get("category", ""),
            "habitat_classes":  t.get("habitat_classes", ""),
            "movement_classes": t.get("movement_classes", ""),
            "source":           t.get("source", ""),
            "reason":           t.get("reason", ""),
            "rank":             tx.get("rank", ""),
            "kingdom":          tx.get("kingdom", ""),
            "phylum":           tx.get("phylum", ""),
            "class_name":       tx.get("class_name", ""),
            "order_name":       tx.get("order_name", ""),
            "family":           tx.get("family", ""),
            "genus":            tx.get("genus", ""),
            "species":          tx.get("species", ""),
            "has_photo":        inv.get("has_photo", ""),
            "tree_genera":      inv.get("tree_genera", ""),
            "tree_count":       inv.get("tree_count", ""),
            "photo_suggestion": t.get("photo_suggestion", ""),
        })

    rows.sort(key=lambda r: r["slug"])

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} rows")
    if n_missing_tags:
        print(f"  missing tags:     {n_missing_tags}")
    if n_missing_taxa:
        print(f"  missing taxonomy: {n_missing_taxa}")


if __name__ == "__main__":
    main()
