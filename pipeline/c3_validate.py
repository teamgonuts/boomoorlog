"""
Sanity-check the aggregated tags in data/organism_tags.csv.

Flags rows whose habitat/movement values are implausible given their
category or taxonomy, so the user can spot-fix before the migration.

Output: data/organism_tags_review.csv with one row per flagged anomaly,
plus a count summary printed to stdout. Empty CSV = clean.

Rules (intentionally simple — false positives are fine; we want to surface
weirdness for a human glance):

  R1  movement=none → category must be tree, fungus, lichen, or plant
  R2  category=tree → habitat must include tree-rooted, movement=none
  R3  water-body habitat → category must be fish, mollusc, amphibian
  R4  sky-only habitat → category must be bird or mammal (bats)
  R5  flower-visitor habitat → category insect / arachnid (or bird like
       hummingbirds, but none in NL)
  R6  GBIF rank=species → genus column must be populated
  R7  category=fungus or lichen → movement must be none
  R8  habitat_classes empty → flagged (means the agent left it blank)
  R9  GBIF taxonomy disagreement → category=bird but class_name != Aves
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_CSV = REPO / "data" / "organism_tags.csv"
OUT_CSV = REPO / "data" / "organism_tags_review.csv"

EXPECTED_CLASS = {
    "bird": {"Aves"},
    "mammal": {"Mammalia"},
    "fish": {"Actinopterygii", "Chondrichthyes"},
    "amphibian": {"Amphibia"},
    "reptile": {"Reptilia", "Squamata", "Testudines"},
    "fungus": {"Agaricomycetes", "Sordariomycetes", "Dothideomycetes",
               "Lecanoromycetes", "Eurotiomycetes", "Tremellomycetes",
               "Pucciniomycetes", "Ustilaginomycetes",
               "Saccharomycetes", "Pezizomycetes"},
    "lichen": {"Lecanoromycetes"},
    "tree": {"Magnoliopsida", "Pinopsida", "Liliopsida", "Cycadopsida",
             "Ginkgoopsida"},
}


def parse_arr(s: str) -> list[str]:
    return [v.strip() for v in (s or "").split(";") if v.strip()]


def main() -> int:
    issues: list[dict[str, str]] = []

    with IN_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        slug = r["slug"]
        cat = r["category"]
        habs = parse_arr(r["habitat_classes"])
        movs = parse_arr(r["movement_classes"])
        rank = r["rank"]
        genus = r["genus"]
        class_name = r["class_name"]

        def flag(rule: str, detail: str) -> None:
            issues.append({
                "slug": slug,
                "rule": rule,
                "detail": detail,
                "category": cat,
                "habitat_classes": r["habitat_classes"],
                "movement_classes": r["movement_classes"],
                "rank": rank,
                "class_name": class_name,
                "latin_name": r["latin_name"],
            })

        # R1
        if "none" in movs and cat not in ("tree", "fungus", "lichen", "plant"):
            flag("R1", f"movement=none but category={cat}")

        # R2
        if cat == "tree":
            if "tree-rooted" not in habs:
                flag("R2a", "category=tree but tree-rooted not in habitat_classes")
            if movs and "none" not in movs:
                flag("R2b", f"category=tree but movement_classes={movs}")

        # R3
        if "water-body" in habs and cat not in ("fish", "mollusc", "amphibian"):
            flag("R3", f"water-body habitat but category={cat}")

        # R4
        if "sky-only" in habs and cat not in ("bird", "mammal"):
            flag("R4", f"sky-only habitat but category={cat}")

        # R5
        if "flower-visitor" in habs and cat not in ("insect", "arachnid", "bird"):
            flag("R5", f"flower-visitor habitat but category={cat}")

        # R6
        if rank == "species" and not genus:
            flag("R6", "GBIF rank=species but genus column is empty")

        # R7
        if cat in ("fungus", "lichen") and movs and "none" not in movs:
            flag("R7", f"category={cat} but movement_classes={movs}")

        # R8
        if not habs:
            flag("R8", "habitat_classes is empty")
        if not movs:
            flag("R8b", "movement_classes is empty")

        # R9
        if cat in EXPECTED_CLASS and class_name and class_name not in EXPECTED_CLASS[cat]:
            flag("R9", f"category={cat} but GBIF class_name={class_name!r}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "slug", "rule", "detail",
                "category", "habitat_classes", "movement_classes",
                "rank", "class_name", "latin_name",
            ],
        )
        writer.writeheader()
        writer.writerows(issues)

    # Stdout summary.
    by_rule: dict[str, int] = {}
    for i in issues:
        by_rule[i["rule"]] = by_rule.get(i["rule"], 0) + 1

    print(f"validation: {len(rows)} rows checked, {len(issues)} flags")
    for rule in sorted(by_rule):
        print(f"  {rule}: {by_rule[rule]}")
    print(f"detail in {OUT_CSV.relative_to(REPO)}")
    return 0 if len(issues) == 0 else 0  # never fail the build


if __name__ == "__main__":
    raise SystemExit(main())
