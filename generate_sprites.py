#!/usr/bin/env python3
"""Procedural SVG sprite generator for Boomoorlog tree-warrior characters.

Reads the genus roster table in memory/CHARACTERS.md and emits one stylized
SVG sprite per genus into data/sprites/. Every visual feature is driven by the
character's real stats and archetype so the roster reads as a coherent set:

  archetype  -> canopy silhouette (Juggernaut=broad, Skirmisher=spiky, ...)
  Rng        -> tree height
  HP         -> trunk width
  Atk        -> number / sharpness of thorns
  rarity     -> card border (common=slate, notable=blue, rare=gold/legendary)
  genus name -> deterministic leaf hue within a natural palette

A simple face on the trunk turns the tree into a "character".
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHARACTERS_MD = ROOT / "memory" / "CHARACTERS.md"
OUT_DIR = ROOT / "data" / "sprites"

W, H = 240, 300  # sprite canvas


def parse_roster():
    """Parse the markdown stat table into a list of dicts."""
    rows = []
    for line in CHARACTERS_MD.read_text().splitlines():
        if not line.startswith("| *"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 12:
            continue
        genus = cells[0].strip("* ")
        rows.append({
            "genus": genus,
            "common": cells[1],
            "nl": cells[2],
            "trees": int(cells[3]),
            "atk": int(cells[4]),
            "rng": int(cells[5]),
            "hp": int(cells[6]),
            "aspd": int(cells[7]),
            "move": int(cells[8]),
            "rarity": cells[9],
            "power": float(cells[10]),
            "archetype": cells[11],
        })
    return rows


def archetype_key(archetype):
    a = archetype.lower()
    if "juggernaut" in a:
        return "juggernaut"
    if "bruiser" in a:
        return "bruiser"
    if "skirmisher" in a:
        return "skirmisher"
    return "support"


def leaf_palette(genus):
    """Deterministic but natural-looking leaf colors from the genus name."""
    h = int(hashlib.md5(genus.encode()).hexdigest(), 16)
    # Hue families that look like foliage: greens, autumn golds/oranges.
    families = [
        (95, 120),   # green
        (75, 95),    # yellow-green
        (35, 50),    # gold / autumn
        (18, 32),    # orange / copper
        (140, 160),  # blue-green conifer
    ]
    lo, hi = families[h % len(families)]
    hue = lo + (h // 7) % (hi - lo)
    light = (h // 11) % 12  # 0..11
    dark = f"hsl({hue},55%,{28 + light}%)"
    mid = f"hsl({hue},60%,{40 + light}%)"
    bright = f"hsl({hue},65%,{52 + light}%)"
    return dark, mid, bright


RARITY_STYLE = {
    "common":   ("#3a4a52", "#0f1518"),
    "notable":  ("#2f7fb5", "#0c1a24"),
    "rare":     ("#d4a72c", "#241b06"),
}


def poly(points, **attrs):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    a = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {a}/>'


def canopy(arch, cx, top, width, height, dark, mid, bright, atk):
    """Return SVG for the canopy based on archetype silhouette."""
    half = width / 2
    bottom = top + height
    s = []
    if arch == "juggernaut":
        # Broad, blocky, layered fortress canopy.
        for i, col in enumerate((dark, mid, bright)):
            inset = i * width * 0.13
            ty = top + i * height * 0.18
            s.append(f'<rect x="{cx-half+inset:.1f}" y="{ty:.1f}" '
                     f'width="{width-2*inset:.1f}" height="{height*0.6:.1f}" '
                     f'rx="14" fill="{col}"/>')
    elif arch == "skirmisher":
        # Tall spiky cluster of triangles.
        spikes = max(3, min(7, atk))
        for i, col in enumerate((dark, mid, bright)):
            ty = top + i * height * 0.16
            pts = []
            step = width / spikes
            for k in range(spikes + 1):
                x = cx - half + k * step
                pts.append((x, bottom))
            top_pts = []
            for k in range(spikes):
                x = cx - half + (k + 0.5) * step
                top_pts.append((x, ty))
            merged = [(cx - half, bottom)]
            for k in range(spikes):
                merged.append((cx - half + (k + 0.5) * step, ty))
                merged.append((cx - half + (k + 1) * step, bottom))
            s.append(poly(merged, fill=col))
    elif arch == "bruiser":
        # Tall, sturdy rounded crown (egg/flame shape).
        for i, col in enumerate((dark, mid, bright)):
            inset = i * width * 0.12
            s.append(
                f'<ellipse cx="{cx:.1f}" cy="{top+height*0.45+i*height*0.06:.1f}" '
                f'rx="{half-inset:.1f}" ry="{height*0.5-inset:.1f}" fill="{col}"/>')
    else:  # support
        # Small, simple round bush.
        for i, col in enumerate((dark, mid, bright)):
            r = (half) * (1 - i * 0.22)
            s.append(f'<circle cx="{cx:.1f}" cy="{top+height*0.5:.1f}" '
                     f'r="{r:.1f}" fill="{col}"/>')
    return "\n".join(s)


def thorns(cx, trunk_top, trunk_w, atk, color):
    """Side thorns scaling with attack stat (only for high-atk units)."""
    if atk < 6:
        return ""
    n = atk - 5  # 1..5
    s = []
    for i in range(n):
        y = trunk_top + 10 + i * 16
        size = 6 + atk * 0.6
        # left
        s.append(poly([(cx - trunk_w / 2, y),
                       (cx - trunk_w / 2 - size, y + size * 0.4),
                       (cx - trunk_w / 2, y + size * 0.8)], fill=color))
        # right
        s.append(poly([(cx + trunk_w / 2, y),
                       (cx + trunk_w / 2 + size, y + size * 0.4),
                       (cx + trunk_w / 2, y + size * 0.8)], fill=color))
    return "\n".join(s)


def build_svg(c):
    arch = archetype_key(c["archetype"])
    dark, mid, bright = leaf_palette(c["genus"])
    border, bg = RARITY_STYLE.get(c["rarity"], RARITY_STYLE["common"])
    legendary = c["rarity"] == "rare"

    cx = W / 2
    ground_y = H - 46

    # Stat-driven geometry.
    crown_h = 70 + c["rng"] * 11          # height from Range
    crown_w = 90 + c["move"] * 6          # spread from Move
    trunk_w = 16 + c["hp"] * 5            # girth from HP
    trunk_top = ground_y - (40 + c["hp"] * 4)
    crown_top = trunk_top - crown_h + 18

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">']

    # Card background + rarity border.
    parts.append(f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="18" '
                 f'fill="{bg}" stroke="{border}" stroke-width="4"/>')
    if legendary:
        parts.append(f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="18" '
                     f'fill="none" stroke="#fff3c4" stroke-width="1" opacity="0.5"/>')

    # Ground shadow / roots.
    parts.append(f'<ellipse cx="{cx}" cy="{ground_y+6}" rx="{trunk_w*1.6:.1f}" '
                 f'ry="12" fill="#000" opacity="0.28"/>')

    # Trunk (tapered).
    tw = trunk_w
    parts.append(poly([
        (cx - tw / 2, ground_y),
        (cx + tw / 2, ground_y),
        (cx + tw / 2.6, trunk_top),
        (cx - tw / 2.6, trunk_top),
    ], fill="#5a3d27"))
    parts.append(poly([
        (cx - tw / 2, ground_y),
        (cx - tw / 2 + 4, ground_y),
        (cx - tw / 2.6 + 4, trunk_top),
        (cx - tw / 2.6, trunk_top),
    ], fill="#6e4d33"))

    # Thorns (attack).
    parts.append(thorns(cx, trunk_top, tw, c["atk"], dark))

    # Canopy.
    parts.append(canopy(arch, cx, crown_top, crown_w, crown_h,
                        dark, mid, bright, c["atk"]))

    # Face on the trunk -> character.
    fy = trunk_top + (ground_y - trunk_top) * 0.42
    eye_dx = max(7, tw * 0.22)
    for sign in (-1, 1):
        parts.append(f'<circle cx="{cx+sign*eye_dx:.1f}" cy="{fy:.1f}" r="6" fill="#f6f1e7"/>')
        parts.append(f'<circle cx="{cx+sign*eye_dx:.1f}" cy="{fy+1:.1f}" r="3" fill="#1a1208"/>')
    # Mouth varies with archetype mood.
    if arch == "juggernaut":
        parts.append(f'<path d="M{cx-7},{fy+13} L{cx+7},{fy+13}" stroke="#1a1208" stroke-width="2.5" fill="none"/>')
    elif arch == "skirmisher":
        parts.append(f'<path d="M{cx-6},{fy+12} L{cx},{fy+16} L{cx+6},{fy+12}" stroke="#1a1208" stroke-width="2" fill="none"/>')
    elif arch == "bruiser":
        parts.append(f'<path d="M{cx-7},{fy+12} Q{cx},{fy+18} {cx+7},{fy+12}" stroke="#1a1208" stroke-width="2.5" fill="none"/>')
    else:
        parts.append(f'<circle cx="{cx:.1f}" cy="{fy+13:.1f}" r="3" fill="#1a1208"/>')

    # Name banner.
    parts.append(f'<rect x="14" y="{H-34}" width="{W-28}" height="24" rx="8" '
                 f'fill="{border}" opacity="0.92"/>')
    parts.append(f'<text x="{cx}" y="{H-17}" text-anchor="middle" '
                 f'font-family="Georgia, serif" font-size="14" font-weight="bold" '
                 f'fill="#f6f1e7">{c["common"]}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    roster = parse_roster()
    targets = sys.argv[1:]  # optional genus filter
    made = 0
    for c in roster:
        if targets and c["genus"] not in targets:
            continue
        svg = build_svg(c)
        out = OUT_DIR / f"{c['genus']}.svg"
        out.write_text(svg)
        made += 1
        print(f"wrote {out.relative_to(ROOT)}")
    if made == 0 and targets:
        print(f"no genus matched {targets}; known: {[c['genus'] for c in roster][:5]}...")
    print(f"done: {made} sprite(s)")


if __name__ == "__main__":
    main()
