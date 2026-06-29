"""
Extract the prose body from each memory/organisms/<slug>.md file into a
CSV the C3-backfill migration can ingest as organisms.lore.

Each markdown file is YAML frontmatter (between --- fences) + a few
sentences of plain prose. We want just the prose, stripped and joined
on single spaces.

Output: data/organism_lore.csv with columns: slug, lore.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "memory" / "organisms"
OUT = REPO / "data" / "organism_lore.csv"

FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def extract_body(text: str) -> str:
    body = FRONTMATTER_RE.sub("", text, count=1).strip()
    # Collapse internal whitespace runs into single spaces; keep the
    # text on one line per row in the CSV.
    body = re.sub(r"\s+", " ", body)
    return body


def main() -> None:
    rows: list[dict[str, str]] = []
    for md in sorted(SRC.glob("*.md")):
        if md.name.startswith("."):
            continue
        slug = md.stem
        body = extract_body(md.read_text(encoding="utf-8"))
        if not body:
            continue
        rows.append({"slug": slug, "lore": body})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "lore"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} organisms with lore")


if __name__ == "__main__":
    main()
