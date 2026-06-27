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
habit. On top of that, a handful of per-tree shape knobs (crown size/aspect,
trunk height/width, canopy texture + density, and an optional accent color for
blossom/berry/autumn tips) let every species read as a DISTINCT tree instead of
the same green lollipop. All of these are deterministic given --seed.

Usage:
  python render_tree_sprite.py --form conifer --hue 125 --out sprite.png
  python render_tree_sprite.py --form round --base-color "#4f8a3b" --out oak.png
  python render_tree_sprite.py --form round --hue 120 --texture 55 --density 80 \\
      --crown-aspect 1.15 --trunk-h 6 --seed 7 --out linden.png

Forms: conifer, round, egg, columnar, spreading, umbrella, vase, weeping
"""

import argparse
import colorsys
from pathlib import Path

from PIL import Image

WP, HP = 27, 36          # native sprite grid
GROUND = HP - 2          # baseline row for the trunk
CX = WP // 2             # horizontal center


# --------------------------------------------------------------------------- #
# deterministic value noise (so texture/density are reproducible per --seed)
# --------------------------------------------------------------------------- #
def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 0xFFFF


# --------------------------------------------------------------------------- #
# color
# --------------------------------------------------------------------------- #
def hsl(h, s, l):
    """h in degrees, s/l in 0..100 -> (r,g,b) 0..255."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return (round(r * 255), round(g * 255), round(b * 255))


def build_ramp(hue, sat, trunk_hue):
    """Four foliage tones + two trunk tones, matching A1's lightness steps."""
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


def build_accent(hue, sat, light):
    """A 2-tone accent (blossom / berry / bright autumn tip) sprinkled on top."""
    return {
        "light": hsl(hue, sat, min(92, light + 14)),
        "dark": hsl(hue, sat, light),
    }


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
    top = max(0, min(GROUND, int(round(top))))
    half = width // 2
    for y in range(top, GROUND + 1):
        for x in range(CX - half, CX - half + width):
            if 0 <= x < WP:
                grid[y][x] = ramp_t["light"] if x == CX - half else ramp_t["dark"]


def _ellipse(g, cy, rx, ry, ramp):
    for y in range(HP):
        for x in range(WP):
            if ((x - CX) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                g[y][x] = shade(x, CX, rx, ramp)


def _ellipse_params(base_cy, base_rx, base_ry, P):
    import math
    a = math.sqrt(max(0.2, P["aspect"]))
    rx = max(2.0, base_rx * P["scale"] * a)
    ry = max(2.0, base_ry * P["scale"] / a)
    return base_cy, rx, ry


# Each builder reads P for scale/aspect/trunk and returns (grid, span, crown_top)
def form_conifer(ramp, ramp_t, P):
    g = _blank()
    s = P["scale"]
    span = 11 * s
    lift = P["lift"]
    tiers = [(0, 13, 5), (8, 23, 8), (16, 30, 11)]
    bottom = 0
    for ay, by, mhw in tiers:
        ay2, by2 = ay * s - lift, by * s - lift
        for y in range(int(ay2), int(by2) + 1):
            if y < 0:
                continue
            frac = (y - ay2) / max(1, (by2 - ay2))
            hw = max(1, round(mhw * s * P["aspect"] * frac))
            for x in range(CX - hw, CX + hw + 1):
                if 0 <= x < WP and y < HP:
                    g[y][x] = shade(x, CX, span, ramp)
            bottom = max(bottom, int(by2))
    _trunk(g, bottom, ramp_t, P["trunk_w"])
    return g, span, 0


def _seated_ellipse(base_cy, base_rx, base_ry, ramp, ramp_t, P, trunk_gap):
    g = _blank()
    cy, rx, ry = _ellipse_params(base_cy, base_rx, base_ry, P)
    cy = max(ry + 1, cy - P["lift"])
    _ellipse(g, cy, rx, ry, ramp)
    tt = P["trunk_top"] if P["trunk_top"] is not None else cy + ry - trunk_gap
    _trunk(g, tt, ramp_t, P["trunk_w"])
    return g, rx, cy - ry


def form_round(ramp, ramp_t, P):
    return _seated_ellipse(12, 11, 12, ramp, ramp_t, P, 1)


def form_egg(ramp, ramp_t, P):
    return _seated_ellipse(14, 8, 14, ramp, ramp_t, P, 1)


def form_columnar(ramp, ramp_t, P):
    return _seated_ellipse(15, 6, 16, ramp, ramp_t, P, 1)


def form_spreading(ramp, ramp_t, P):
    return _seated_ellipse(11, 13, 8, ramp, ramp_t, P, 0)


def form_umbrella(ramp, ramp_t, P):
    return _seated_ellipse(9, 13, 5, ramp, ramp_t, P, 0)


def form_vase(ramp, ramp_t, P):
    """Elm / zelkova vase: narrow at the base where it meets a short trunk,
    fanning outward and upward to a broad, rounded crown that is widest in the
    upper third."""
    g = _blank()
    top, bot = max(0, 2 - P["lift"]), 24 - P["lift"]
    maxw = 12 * P["scale"] * P["aspect"]
    basew = 2 * P["scale"]
    shoulder = top + max(3, int(round((bot - top) * 0.32)))
    for y in range(top, bot + 1):
        if y <= shoulder:                       # rounded crown top
            f = (y - top) / max(1, (shoulder - top))
            hw = basew + (maxw - basew) * (f ** 0.7)
        else:                                   # fan narrowing down to the base
            f = (y - shoulder) / max(1, (bot - shoulder))
            hw = maxw - (maxw - basew) * f
        hw = int(round(hw))
        for x in range(CX - hw, CX + hw + 1):
            if 0 <= x < WP:
                g[y][x] = shade(x, CX, maxw, ramp)
    tt = P["trunk_top"] if P["trunk_top"] is not None else bot
    _trunk(g, tt, ramp_t, P["trunk_w"])
    return g, maxw, top


def form_weeping(ramp, ramp_t, P):
    """A weeping willow: a broad shallow crown whose foliage drapes down in a
    near-continuous curtain almost to the ground, deepest in the middle and
    tapering at the edges, with the trunk mostly hidden behind the curtain."""
    import math
    g = _blank()
    a = math.sqrt(max(0.2, P["aspect"]))
    rx = max(6, int(round(12 * P["scale"] * a)))
    ry = max(3, int(round(5 * P["scale"])))
    cy = max(ry + 1, 6 - P["lift"])
    _ellipse(g, cy, rx, ry, ramp)         # broad shallow top
    dome_bottom = cy + ry
    for x in range(max(0, CX - rx), min(WP, CX + rx + 1)):
        edge = abs(x - CX)
        start = None
        for y in range(HP):
            if g[y][x] is not None:
                start = y
        if start is None:
            start = dome_bottom
        # curtain bottom: a wide arc that hangs near the ground in the middle
        frac = edge / rx
        bottom = GROUND - 1 - int(round((frac ** 1.8) * (rx * 0.9)))
        bottom = min(GROUND - 1, max(start + 1, bottom))
        for y in range(start + 1, bottom + 1):
            seam = (x % 4 == 0)               # vertical strand separation
            if y >= bottom - 1 and (x + y) % 2 == 0 and edge > 1:
                continue                      # broken, stringy tips
            g[y][x] = ramp["dark"] if seam else shade(x, CX, rx, ramp)
    tt = P["trunk_top"] if P["trunk_top"] is not None else GROUND - 4
    _trunk(g, tt, ramp_t, P["trunk_w"])
    return g, rx, cy - ry


FORMS = {
    "conifer": form_conifer,
    "round": form_round,
    "egg": form_egg,
    "columnar": form_columnar,
    "spreading": form_spreading,
    "umbrella": form_umbrella,
    "vase": form_vase,
    "weeping": form_weeping,
}


# --------------------------------------------------------------------------- #
# canopy modifiers: texture (lumpy edge), density (airy gaps), accent dots
# --------------------------------------------------------------------------- #
def _is_canopy(c, trunk):
    return c is not None and c != trunk["dark"] and c != trunk["light"]


def _neighbors4(x, y):
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def apply_texture(grid, ramp, ramp_t, span, amount, seed):
    """Roughen the canopy silhouette into chunky lumps + notches."""
    if amount <= 0:
        return grid
    amp = amount / 100.0
    snap = [row[:] for row in grid]
    # notch: carve away edge foliage pixels
    for y in range(HP):
        for x in range(WP):
            c = snap[y][x]
            if not _is_canopy(c, ramp_t):
                continue
            up = y > 0 and _is_canopy(snap[y - 1][x], ramp_t)
            left = x > 0 and _is_canopy(snap[y][x - 1], ramp_t)
            right = x < WP - 1 and _is_canopy(snap[y][x + 1], ramp_t)
            # dangling vertical strand (weeping): preserve it
            if up and not left and not right:
                continue
            on_edge = any(
                not (0 <= nx < WP and 0 <= ny < HP) or snap[ny][nx] is None
                for nx, ny in _neighbors4(x, y))
            if on_edge and _hash(x // 2, y // 2, seed) < amp * 0.45:
                grid[y][x] = None
    # bump: grow chunky tufts outward from the (already-notched) edge
    snap = [row[:] for row in grid]
    for y in range(HP):
        for x in range(WP):
            if snap[y][x] is not None:
                continue
            adj = [(nx, ny) for nx, ny in _neighbors4(x, y)
                   if 0 <= nx < WP and 0 <= ny < HP and _is_canopy(snap[ny][nx], ramp_t)]
            if not adj:
                continue
            # don't grow tufts below the canopy (would dangle past the trunk)
            if all(ny > y for _, ny in adj):
                continue
            if _hash(x // 2 + 53, y // 2 + 17, seed) < amp * 0.45:
                grid[y][x] = shade(x, CX, span, ramp)
    return grid


def apply_density(grid, ramp, ramp_t, density, seed):
    """Carve the interior into chunky light/shadow clumps so the crown reads as
    distinct masses of leaves instead of a flat fill. Lower density -> more and
    deeper shadow pockets (airy/open crown); higher -> solid. Gaps are SHADOW
    tones, never transparent holes, so the canopy never looks like static."""
    if density >= 100:
        return grid
    d = density / 100.0
    snap = [row[:] for row in grid]
    for y in range(HP):
        for x in range(WP):
            if not _is_canopy(snap[y][x], ramp_t):
                continue
            # interior only: keep the silhouette edge intact
            if any(not (0 <= nx < WP and 0 <= ny < HP) or snap[ny][nx] is None
                   for nx, ny in _neighbors4(x, y)):
                continue
            # coarse 2x2 noise -> chunky clumps rather than 1px speckle
            n = _hash(x // 2, y // 2, seed + 7)
            if n > d:
                grid[y][x] = ramp["dark"]
    return grid


def apply_accent(grid, ramp_t, accent, acc_ramp, seed):
    """Sprinkle blossom/berry/autumn-tip dots over the foliage."""
    if accent <= 0 or acc_ramp is None:
        return grid
    a = accent / 100.0
    for y in range(HP):
        for x in range(WP):
            if not _is_canopy(grid[y][x], ramp_t):
                continue
            n = _hash(x * 2 + 3, y * 2 + 5, seed + 91)
            if n < a:
                grid[y][x] = acc_ramp["light"] if (x + y) % 2 == 0 else acc_ramp["dark"]
    return grid


# --------------------------------------------------------------------------- #
def _outline_exterior(grid, color):
    """Trace a 1px outline against EXTERIOR background only (interior gaps in
    airy crowns stay open as see-through sky rather than getting outlined)."""
    h, w = len(grid), len(grid[0])
    # flood fill exterior emptiness from the border
    ext = [[False] * w for _ in range(h)]
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if grid[y][x] is None and not ext[y][x]:
                ext[y][x] = True
                stack.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if grid[y][x] is None and not ext[y][x]:
                ext[y][x] = True
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for nx, ny in _neighbors4(x, y):
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] is None and not ext[ny][nx]:
                ext[ny][nx] = True
                stack.append((nx, ny))
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] is not None:
                continue
            if not ext[y][x]:
                continue
            for nx, ny in _neighbors4(x, y):
                if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] is not None:
                    out[y][x] = color
                    break
    return out


def hue_from_hex(s):
    s = s.lstrip("#")
    r, g, b = (int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360


def render(form, hue, sat, trunk_hue, scale, P, acc_ramp):
    ramp, ramp_t = build_ramp(hue, sat, trunk_hue)
    grid, span, _crown_top = FORMS[form](ramp, ramp_t, P)
    grid = apply_texture(grid, ramp, ramp_t, span, P["texture"], P["seed"])
    grid = apply_density(grid, ramp, ramp_t, P["density"], P["seed"])
    grid = apply_accent(grid, ramp_t, P["accent"], acc_ramp, P["seed"])
    grid = _outline_exterior(grid, ramp["outline"])
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
    ap.add_argument("--trunk-w", type=int, default=3, help="trunk width in px (default 3)")
    ap.add_argument("--trunk-h", type=float, default=0,
                    help="extra clear-trunk length: lifts the crown up by N px so "
                         "more bare trunk shows (default 0)")
    ap.add_argument("--crown-scale", type=float, default=1.0,
                    help="overall crown size multiplier (default 1.0)")
    ap.add_argument("--crown-aspect", type=float, default=1.0,
                    help=">1 wider crown, <1 taller/narrower crown (default 1.0)")
    ap.add_argument("--texture", type=float, default=0,
                    help="0-100 canopy edge roughness: 0 smooth dome, ~50 lumpy/"
                         "leafy, ~80 ragged (default 0)")
    ap.add_argument("--density", type=float, default=100,
                    help="0-100 canopy fill: 100 solid, ~75 dappled, ~55 airy/"
                         "see-through (birch, honey locust) (default 100)")
    ap.add_argument("--accent-hue", type=float,
                    help="hue for blossom/berry/autumn-tip dots (e.g. 330 pink "
                         "blossom, 5 red berry, 45 gold tips)")
    ap.add_argument("--accent", type=float, default=0,
                    help="0-100 amount of accent dots (needs --accent-hue)")
    ap.add_argument("--accent-light", type=float, default=62,
                    help="lightness of accent dots 0-100 (default 62)")
    ap.add_argument("--seed", type=int, default=0,
                    help="deterministic variation seed for texture/density/accent")
    ap.add_argument("--scale", type=int, default=10, help="nearest-neighbor upscale")
    ap.add_argument("--out", required=True, help="output PNG path")
    a = ap.parse_args()

    if a.hue is None and not a.base_color:
        ap.error("provide --hue or --base-color")
    hue = a.hue if a.hue is not None else hue_from_hex(a.base_color)

    P = {
        "scale": a.crown_scale,
        "aspect": a.crown_aspect,
        "trunk_w": a.trunk_w,
        "trunk_top": None,
        "lift": int(round(a.trunk_h)),
        "texture": a.texture,
        "density": a.density,
        "accent": a.accent,
        "seed": a.seed,
    }
    acc_ramp = None
    if a.accent and a.accent_hue is not None:
        acc_ramp = build_accent(a.accent_hue, 62, a.accent_light)

    img = render(a.form, hue, a.sat, a.trunk_hue, a.scale, P, acc_ramp)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}  form={a.form} hue={hue:.0f} sat={a.sat:.0f} "
          f"tex={a.texture:.0f} dens={a.density:.0f} acc={a.accent:.0f} "
          f"seed={a.seed} ({WP}x{HP} -> {img.width}x{img.height})")


if __name__ == "__main__":
    main()
