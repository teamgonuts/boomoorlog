#!/usr/bin/env python3
"""Build the master creature database from per-genus character files.

Walks `memory/characters/*.md`, parses every bullet in each `## Living creatures`
section, dedupes by the pic-file slug (already unique per creature), and writes
`data/creatures.csv`. Re-run any time character files change.

CSV columns (start minimal — enhance later):
    slug          — unique key (matches data/creature_pics/{slug}.{ext})
    common_name   — English/Dutch common name pulled from the bullet
    latin_name    — everything inside parens (genus/species/family)
    pic_file      — repo-relative path to the picture, or empty
    tree_count    — how many tree genera this creature appears on
    tree_genera   — semicolon-separated list of those genera

For bullets without a [pic] link (a tiny handful — Cedrobium laportei,
Stomaphis yanonis, etc.) we still include the creature with a slug derived
from the latin name and an empty pic_file, so the master is complete.
"""

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
CHARS_DIR = REPO / "memory" / "characters"
OUT = REPO / "data" / "creatures.csv"

# Bullet:  - **Common name (Latin / family)** — rest of line including [pic](...)
BULLET_RE = re.compile(r"^- \*\*(?P<name>.+?)\*\*\s*[—-]\s*(?P<rest>.*)$")
NAME_SPLIT_RE = re.compile(r"^(?P<common>[^()]+?)\s*\((?P<latin>[^)]+)\)\s*$")
PIC_RE = re.compile(r"\[pic\]\(\.\./\.\./(?P<path>data/creature_pics/[^\)]+)\)")
SECTION_RE = re.compile(
    r"^## Living creatures\s*\n(.*?)(?=^## )", re.DOTALL | re.MULTILINE
)


def slugify(text: str) -> str:
    """Lowercase, hyphenate, strip duplicate hyphens — same rule the pic
    downloaders used so slugs derived here match existing pic filenames."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s)


def parse_name(name: str) -> tuple[str, str]:
    m = NAME_SPLIT_RE.match(name)
    if m:
        return m.group("common").strip(), m.group("latin").strip()
    return name.strip(), ""


def main() -> None:
    creatures: dict[str, dict] = {}
    bullets_seen = bullets_no_pic = 0

    for md in sorted(CHARS_DIR.glob("*.md")):
        if md.name == "_TEMPLATE.md":
            continue
        genus = md.stem
        sec = SECTION_RE.search(md.read_text())
        if not sec:
            continue

        for line in sec.group(1).splitlines():
            bm = BULLET_RE.match(line)
            if not bm:
                continue
            bullets_seen += 1
            common, latin = parse_name(bm.group("name"))
            rest = bm.group("rest")
            pic_m = PIC_RE.search(rest)

            if pic_m:
                path = pic_m.group("path")
                slug = Path(path).stem
            else:
                bullets_no_pic += 1
                # Fall back to a slug from latin name (or common if no latin).
                slug = slugify(latin.split("/")[0] if latin else common)
                path = ""

            row = creatures.setdefault(slug, {
                "slug": slug,
                "common_name": common,
                "latin_name": latin,
                "pic_file": path,
                "tree_genera": set(),
            })
            # Backfill pic_file if a later bullet for the same slug has one.
            if path and not row["pic_file"]:
                row["pic_file"] = path
            row["tree_genera"].add(genus)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["slug", "common_name", "latin_name",
                    "pic_file", "tree_count", "tree_genera"])
        for slug in sorted(creatures):
            row = creatures[slug]
            genera = sorted(row["tree_genera"])
            w.writerow([row["slug"], row["common_name"], row["latin_name"],
                        row["pic_file"], len(genera), ";".join(genera)])

    print(f"Wrote {len(creatures)} unique creatures → {OUT.relative_to(REPO)}")
    print(f"Parsed {bullets_seen} bullets across 55 genera "
          f"({bullets_no_pic} without a [pic] link).")


if __name__ == "__main__":
    main()
