#!/usr/bin/env python3
"""Render an "A1-style" pixel-art tree sprite.

The A1 look (the one this skill is built around) has four defining traits:
  1. a tiny native resolution (~27x36) upscaled with NEAREST so pixels stay chunky
  2. a 4-step color ramp (outline / shadow / base / highlight) -- limited palette
  3. left-side lighting: the left of the canopy is lighter, the right darker
  4. a 1px dark outline traced around the whole silhouette

Colors are synthesized from a single base HUE so the sprite can adapt to any
tree (green foliage, autumn gold, blue-green conifer) while keeping the punchy,
consistent, game-ready feel -- the ramp's saturation and lightness steps are
fixed to match A1; only the hue moves.

The silhouette is chosen by --form so the sprite matches the real tree's growth
habit instead of every tree looking identical.

Usage:
  python render_tree_sprite.py --form conifer --hue 125 --out sprite.png
  python render_tree_sprite.py --form round --base-color "#4f8a3b" --out oak.png

Forms: conifer, round, columnar, spreading, weeping, vase
"""

import argparse
import colorsys
from pathlib import Path

from PIL import Image

WP, HP = 27, 36          # native sprite grid
GROUND = HP - 2          # baseline row for the trunk
CX = WP // 2             # horizontal center


# --------------------------------------------------------------------------- #
# color
# --------------------------------------------------------------------------- #
def hsl(h, s, l):
    """h in degrees, s/l in 0..100 -> (r,g,b) 0..255."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return (round(r * 255), round(g * 255), round(b * 255))


def build_ramp(hue, sat, trunk_hue):
    """Four foliage tones + two trunk tones, matching A1's lightness steps.

    Highlight nudges its hue slightly toward yellow (-12 deg) because that is
    what reads as 'sunlit leaves' and is what the original A1 palette did.
    """
    foliage = {
        "outline": hsl(hue, min(100, sat + 8), 13),
        "dark": hsl(hue, sat, 25),
        "mid": hsl(hue, sat, 40),
        "light": hsl(hue - 12, sat, 60),
    }
    trunk = {
        "dark": hsl(trunk_hue, 46, 22),
        "light": hsl(trunk_hue, 42, 34),
    }
    return foliage, trunk


def shade(x, cx, span, ramp):
    """Left-lit 3-tone shading by horizontal position within the canopy."""
    rel = (x - cx) / max(1, span)
    if rel < -0.25:
        return ramp["light"]
    if rel > 0.45:
        return ramp["dark"]
    return ramp["mid"]


# --------------------------------------------------------------------------- #
# silhouette builders -- each returns a 2D grid of (r,g,b)|None
# --------------------------------------------------------------------------- #
def _blank():
    return [[None] * WP for _ in range(HP)]


def _trunk(grid, top, ramp_t, width=3):
    half = width // 2
    for y in range(top, GROUND + 1):
        for x in range(CX - half, CX - half + width):
            grid[y][x] = ramp_t["light"] if x == CX - half else ramp_t["dark"]


def _outline(grid, color):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] is None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or grid[ny][nx] is None:
                    out[y][x] = color
                    break
    return out


def form_conifer(ramp, ramp_t):
    g = _blank()
    span = 11
    tiers = [(0, 13, 5), (8, 23, 8), (16, 30, 11)]  # apex, base, half-width
    for ay, by, mhw in tiers:
        for y in range(ay, by + 1):
            frac = (y - ay) / (by - ay)
            hw = max(1, round(mhw * frac))
            for x in range(CX - hw, CX + hw + 1):
                g[y][x] = shade(x, CX, span, ramp)
    _trunk(g, 30, ramp_t)
    return g


def _ellipse(g, cy, rx, ry, ramp):
    for y in range(HP):
        for x in range(WP):
            if ((x - CX) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                g[y][x] = shade(x, CX, rx, ramp)


def form_round(ramp, ramp_t):
    g = _blank()
    _ellipse(g, 12, 11, 12, ramp)
    _trunk(g, 23, ramp_t)
    return g


def form_columnar(ramp, ramp_t):
    g = _blank()
    _ellipse(g, 15, 6, 16, ramp)
    _trunk(g, 30, ramp_t)
    return g


def form_spreading(ramp, ramp_t):
    g = _blank()
    # wide, shallow, slightly domed crown sitting high on a taller trunk
    _ellipse(g, 11, 13, 8, ramp)
    _trunk(g, 18, ramp_t)
    return g


def form_vase(ramp, ramp_t):
    g = _blank()
    # narrow at the base, fanning outward toward a rounded top (elm/zelkova)
    top, bot = 2, 22
    for y in range(top, bot + 1):
        frac = (y - top) / (bot - top)
        hw = round(3 + 9 * frac)
        for x in range(CX - hw, CX + hw + 1):
            g[y][x] = shade(x, CX, 12, ramp)
    # round off the top corners
    for y in range(top, top + 4):
        for x in range(WP):
            if g[y][x] is not None and abs(x - CX) > 3 + (y - top) * 2:
                g[y][x] = None
    _trunk(g, 22, ramp_t)
    return g


def form_weeping(ramp, ramp_t):
    g = _blank()
    # domed crown
    _ellipse(g, 10, 11, 8, ramp)
    # drooping strands hanging from the crown edge
    for x in range(CX - 11, CX + 12):
        # find lowest filled canopy pixel in this column
        low = None
        for y in range(HP):
            if g[y][x] is not None:
                low = y
        if low is None:
            continue
        edge = abs(x - CX)
        drop = max(0, int((edge - 2) * 1.4)) if edge > 3 else 2
        for y in range(low + 1, min(GROUND - 1, low + 1 + drop)):
            if (x + y) % 2 == 0 or edge > 7:   # broken, stringy look
                g[y][x] = shade(x, CX, 11, ramp)
    _trunk(g, 17, ramp_t)
    return g


FORMS = {
    "conifer": form_conifer,
    "round": form_round,
    "columnar": form_columnar,
    "spreading": form_spreading,
    "vase": form_vase,
    "weeping": form_weeping,
}


# --------------------------------------------------------------------------- #
def hue_from_hex(s):
    s = s.lstrip("#")
    r, g, b = (int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360


def render(form, hue, sat, trunk_hue, scale):
    ramp, ramp_t = build_ramp(hue, sat, trunk_hue)
    grid = FORMS[form](ramp, ramp_t)
    grid = _outline(grid, ramp["outline"])
    img = Image.new("RGBA", (WP, HP), (0, 0, 0, 0))
    px = img.load()
    for y in range(HP):
        for x in range(WP):
            c = grid[y][x]
            if c is not None:
                px[x, y] = (c[0], c[1], c[2], 255)
    return img.resize((WP * scale, HP * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--form", required=True, choices=sorted(FORMS),
                    help="tree silhouette matching the real growth habit")
    ap.add_argument("--hue", type=float,
                    help="foliage base hue 0-360 (green~120, yellow-green~80, "
                         "autumn gold~45, orange~28, blue-green conifer~150)")
    ap.add_argument("--base-color", help="hex like #4f8a3b; hue is derived from it")
    ap.add_argument("--sat", type=float, default=50,
                    help="foliage saturation 0-100 (default 50 = punchy/A1)")
    ap.add_argument("--trunk-hue", type=float, default=28, help="bark hue (default 28)")
    ap.add_argument("--scale", type=int, default=10, help="nearest-neighbor upscale")
    ap.add_argument("--out", required=True, help="output PNG path")
    a = ap.parse_args()

    if a.hue is None and not a.base_color:
        ap.error("provide --hue or --base-color")
    hue = a.hue if a.hue is not None else hue_from_hex(a.base_color)

    img = render(a.form, hue, a.sat, a.trunk_hue, a.scale)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}  form={a.form} hue={hue:.0f} sat={a.sat:.0f} "
          f"({WP}x{HP} -> {img.width}x{img.height})")


if __name__ == "__main__":
    main()
