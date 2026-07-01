"""Assign a form (+ aspect) to every sprite on disk.

The `/sprites` gallery groups sprites by form using
`data/full_sprite_backfill/backfill.csv`. That CSV only contains rows
for the sprites the full backfill actually rendered — everything
rendered earlier by `sample_sprite_batch.py` (turtles, capreolus,
sus-scrofa, vulpes, meles, herons, buteos, gulls, …) was skipped
because the sprite already existed on disk, so those sprites had no
form label and got lumped into an "other" bucket that the gallery
filters can't reach.

This script fills that gap. For every PNG in
`web/public/creature_sprites/`:
  1. Look up taxonomy from the CSVs.
  2. Assign form + aspect via the same classifier the full backfill uses.
  3. Merge with the existing backfill CSV (existing rows win).
  4. Rewrite the CSV.

Never touches the PNGs. Instant. Idempotent.

Usage:
    python3 pipeline/label_all_sprites.py
"""
from __future__ import annotations
import csv
import os
from pathlib import Path

# Reuse the classifier + taxonomy loader from full_sprite_backfill.py
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from full_sprite_backfill import (   # noqa: E402
    load_taxonomy, assign_form, SPRITE_DIR, LOG_DIR,
)

CSV_PATH = LOG_DIR / "backfill.csv"


def load_existing() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if not CSV_PATH.exists():
        return rows
    with CSV_PATH.open(newline="") as f:
        for r in csv.DictReader(f):
            slug = r.get("slug", "").strip()
            if slug:
                rows[slug] = r
    return rows


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tax = load_taxonomy()
    existing = load_existing()

    sprite_slugs = {
        Path(f).stem
        for f in os.listdir(SPRITE_DIR)
        if f.lower().endswith(".png")
    }

    added = 0
    labeled_existing_other = 0
    still_no_form = 0
    no_tax = 0

    for slug in sorted(sprite_slugs):
        t = tax.get(slug)
        assigned = assign_form(t) if t else None
        if assigned is None:
            # No taxonomy or no form rule — leave any existing row alone,
            # or record status=no_form so we can see what's still missing.
            if slug not in existing:
                still_no_form += 1
                existing[slug] = {
                    "slug": slug, "form": "", "hue": "", "aspect": "",
                    "sat": "", "tail": "", "head_stripe": "",
                    "status": "no_form" if t else "no_taxonomy",
                    "note": "",
                }
                if not t:
                    no_tax += 1
            continue

        form, cfg = assigned
        # If we already have a row with a real form, don't overwrite it —
        # the existing row (from the full backfill) probably has a more
        # accurate hue and status.
        if slug in existing and existing[slug].get("form"):
            # Existing row already labeled; nothing to do.
            continue

        # Either no row at all, or row exists with empty form → fill it in.
        existing[slug] = {
            "slug": slug,
            "form": form,
            "hue": "",           # unknown; sprite already rendered by another script
            "aspect": f"{cfg.get('aspect', 1.0):.2f}",
            "sat": f"{cfg.get('sat', 55):.0f}",
            "tail": cfg.get("tail", "thin"),
            "head_stripe": str(bool(cfg.get("head_stripe", False))),
            "status": "labeled_preexisting",
            "note": "sprite was rendered earlier; form applied here for gallery grouping",
        }
        if slug in existing and existing[slug].get("status", "") in ("no_form", ""):
            labeled_existing_other += 1
        else:
            added += 1

    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "slug", "form", "hue", "aspect", "sat", "tail",
            "head_stripe", "status", "note",
        ])
        w.writeheader()
        for slug in sorted(existing):
            w.writerow(existing[slug])

    total = len(existing)
    with_form = sum(1 for r in existing.values() if r.get("form"))
    print(f"Sprites on disk:    {len(sprite_slugs)}")
    print(f"CSV rows total:     {total}")
    print(f"  with a form:      {with_form}")
    print(f"  no_form / no_tax: {total - with_form}")
    print(f"Newly labeled:      {added}")
    print(f"Still no form:      {still_no_form} (of which no taxonomy: {no_tax})")
    print(f"\nWrote {CSV_PATH}")


if __name__ == "__main__":
    main()
