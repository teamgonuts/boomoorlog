#!/usr/bin/env python3
"""Photo-inspired SVG sprite generator for Boomoorlog tree-warriors.

Like generate_sprites.py, but instead of hashing a color and picking a generic
archetype shape, this reads the real photo in data/tree_pics/<Genus>.jpg and:

  * extracts a real foliage palette (dark / mid / bright greens) from the pixels
  * traces the tree's actual upper silhouette so the crown shape matches the
    real species (a conifer comes out pointed, an oak rounded, a willow domed)

Stats still drive trunk girth (HP) and crown height (Rng); rarity drives the
card border; a face on the trunk makes it a character.

Usage: python3 generate_sprites_v2.py [Genus ...]
"""

import sys
from pathlib import Path

from PIL import Image

from generate_sprites import (
    parse_roster, RARITY_STYLE, poly, W, H,
)

ROOT = Path(__file__).resolve().parent
PICS = ROOT / "data" / "tree_pics"
OUT_DIR = ROOT / "data" / "sprites"

SAMPLE_W = 80  # downscale width for pixel analysis


def is_foliage(r, g, b):
    """Green-dominant, not sky, not too dark/bright."""
    if b > g and b > r:          # sky / blue
        return False
    if g < 45:                   # too dark
        return False
    if r > 200 and g > 200 and b > 200:  # near white (building/clouds)
        return False
    return g >= r - 12 and g >= b - 5


def is_bark(r, g, b):
    return r > g >= b and 40 < r < 180 and (r - b) > 20


def analyze_photo(path):
    """Return (palette, top_contour) from the photo.

    palette = (dark, mid, bright, trunk) hex colors
    top_contour = list of (x01, y01) normalized points tracing the crown top,
                  left->right, or None if extraction failed.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    sh = max(1, int(SAMPLE_W * h / w))
    img = img.resize((SAMPLE_W, sh))
    px = img.load()

    foliage = []
    bark = []
    # First foliage pixel (from top) per column = crown upper outline.
    top_y = [None] * SAMPLE_W
    for x in range(SAMPLE_W):
        for y in range(sh):
            r, g, b = px[x, y]
            if is_foliage(r, g, b):
                if top_y[x] is None:
                    top_y[x] = y
                foliage.append((r, g, b))
            elif is_bark(r, g, b):
                bark.append((r, g, b))

    if len(foliage) < 30:
        return None, None

    # Horizontal extent of the crown.
    cols = [x for x in range(SAMPLE_W) if top_y[x] is not None]
    x0, x1 = min(cols), max(cols)
    span = max(1, x1 - x0)

    # Drop the lawn: a column counts toward the crown only if its top sits above
    # the median tree top + a margin (lawn columns start much lower down).
    tops = sorted(top_y[x] for x in cols)
    med_top = tops[len(tops) // 2]
    crown_floor = med_top + 0.55 * (sh - med_top)
    crown_cols = [x for x in cols if top_y[x] <= crown_floor]
    if len(crown_cols) >= 8:
        x0, x1 = min(crown_cols), max(crown_cols)
        span = max(1, x1 - x0)

    # Build + smooth the contour over the crown extent.
    raw = []
    for x in range(x0, x1 + 1):
        ty = top_y[x] if top_y[x] is not None and top_y[x] <= crown_floor else crown_floor
        raw.append(ty)
    smooth = []
    k = 2
    for i in range(len(raw)):
        lo, hi = max(0, i - k), min(len(raw), i + k + 1)
        smooth.append(sum(raw[lo:hi]) / (hi - lo))

    y_min, y_max = min(smooth), max(smooth)
    yspan = max(1.0, (y_max - y_min) + 0.15 * (y_max - y_min))
    contour = []
    n = len(smooth)
    stepn = max(1, n // 40)
    for i in range(0, n, stepn):
        x01 = (i) / max(1, n - 1)
        y01 = (smooth[i] - y_min) / yspan
        contour.append((x01, y01))
    if contour[-1][0] < 1.0:
        contour.append((1.0, (smooth[-1] - y_min) / yspan))

    # Palette from foliage luminance percentiles.
    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    foliage.sort(key=lum)

    def pct(p):
        return foliage[min(len(foliage) - 1, int(p * len(foliage)))]
    dark = pct(0.22)
    mid = pct(0.55)
    bright = pct(0.85)

    if bark:
        bark.sort(key=lum)
        trunk = bark[len(bark) // 2]
    else:
        trunk = (95, 67, 43)

    def hexc(c):
        return "#%02x%02x%02x" % (int(c[0]), int(c[1]), int(c[2]))

    return (hexc(dark), hexc(mid), hexc(bright), hexc(trunk)), contour


def build_svg(c, palette, contour):
    dark, mid, bright, trunk_col = palette
    border, bg = RARITY_STYLE.get(c["rarity"], RARITY_STYLE["common"])
    legendary = c["rarity"] == "rare"

    cx = W / 2
    ground_y = H - 46

    trunk_w = 16 + c["hp"] * 5
    trunk_top = ground_y - (40 + c["hp"] * 4)

    # Crown box: width from photo aspect-ish + Move, height from Rng.
    crown_h = 80 + c["rng"] * 12
    crown_w = 110 + c["move"] * 5
    crown_top = trunk_top - crown_h + 22
    cw_half = crown_w / 2

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">']

    grad_id = f"g{c['genus']}"
    p.append(f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{bright}"/>'
             f'<stop offset="0.55" stop-color="{mid}"/>'
             f'<stop offset="1" stop-color="{dark}"/></linearGradient></defs>')

    p.append(f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="18" '
             f'fill="{bg}" stroke="{border}" stroke-width="4"/>')
    if legendary:
        p.append(f'<rect x="3" y="3" width="{W-6}" height="{H-6}" rx="18" '
                 f'fill="none" stroke="#fff3c4" stroke-width="1" opacity="0.5"/>')

    p.append(f'<ellipse cx="{cx}" cy="{ground_y+6}" rx="{trunk_w*1.6:.1f}" '
             f'ry="12" fill="#000" opacity="0.28"/>')

    # Trunk.
    tw = trunk_w
    p.append(poly([(cx - tw / 2, ground_y), (cx + tw / 2, ground_y),
                   (cx + tw / 2.6, trunk_top), (cx - tw / 2.6, trunk_top)],
                  fill=trunk_col))

    # Canopy from the real silhouette: contour across the top, flat-ish base.
    base_y = crown_top + crown_h
    pts = []
    pts.append((cx - cw_half, base_y))
    for x01, y01 in contour:
        x = cx - cw_half + x01 * crown_w
        y = crown_top + y01 * (crown_h * 0.92)
        pts.append((x, y))
    pts.append((cx + cw_half, base_y))
    p.append(poly(pts, fill=f"url(#{grad_id})"))

    # A couple of lighter interior blobs for depth.
    p.append(f'<ellipse cx="{cx-crown_w*0.12:.1f}" cy="{crown_top+crown_h*0.45:.1f}" '
             f'rx="{crown_w*0.18:.1f}" ry="{crown_h*0.2:.1f}" fill="{bright}" opacity="0.35"/>')

    # Face on trunk.
    fy = trunk_top + (ground_y - trunk_top) * 0.42
    eye_dx = max(7, tw * 0.22)
    for sign in (-1, 1):
        p.append(f'<circle cx="{cx+sign*eye_dx:.1f}" cy="{fy:.1f}" r="6" fill="#f6f1e7"/>')
        p.append(f'<circle cx="{cx+sign*eye_dx:.1f}" cy="{fy+1:.1f}" r="3" fill="#1a1208"/>')
    p.append(f'<path d="M{cx-7},{fy+12} Q{cx},{fy+18} {cx+7},{fy+12}" '
             f'stroke="#1a1208" stroke-width="2.5" fill="none"/>')

    # Name banner.
    p.append(f'<rect x="14" y="{H-34}" width="{W-28}" height="24" rx="8" '
             f'fill="{border}" opacity="0.92"/>')
    p.append(f'<text x="{cx}" y="{H-17}" text-anchor="middle" '
             f'font-family="Georgia, serif" font-size="14" font-weight="bold" '
             f'fill="#f6f1e7">{c["common"]}</text>')

    p.append("</svg>")
    return "\n".join(p)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    roster = {c["genus"]: c for c in parse_roster()}
    targets = sys.argv[1:] or list(roster)
    made = 0
    for genus in targets:
        c = roster.get(genus)
        if not c:
            print(f"unknown genus: {genus}")
            continue
        photo = PICS / f"{genus}.jpg"
        if not photo.exists():
            print(f"no photo for {genus}, skipping")
            continue
        palette, contour = analyze_photo(photo)
        if palette is None:
            print(f"could not extract foliage from {genus}, skipping")
            continue
        svg = build_svg(c, palette, contour)
        out = OUT_DIR / f"{genus}_v2.svg"
        out.write_text(svg)
        made += 1
        print(f"wrote {out.relative_to(ROOT)}  palette={palette[:3]}")
    print(f"done: {made} sprite(s)")


if __name__ == "__main__":
    main()
