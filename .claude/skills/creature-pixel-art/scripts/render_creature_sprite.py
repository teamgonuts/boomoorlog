#!/usr/bin/env python3
"""Render an "A1-style" pixel-art creature sprite.

Sibling of render_tree_sprite.py. Same house style — tiny native grid upscaled
with NEAREST, 4-step ramp synthesized from a single hue, left-lit shading,
1px dark outline, transparent background — but for animals and insects on a
landscape (32x24) grid instead of the trees' portrait grid.

The form picks the body plan (bug / beetle / caterpillar / moth / bee /
spider / bird / mammal / bat). Per-creature knobs (size, aspect, legs/wings
toggles, accent for stripes-spots-wing-markings, seed) make every creature
read as DISTINCT rather than the same generic blob.

Usage:
  python render_creature_sprite.py --form bug --hue 120 --out aphid.png
  python render_creature_sprite.py --form bird --hue 210 --accent-hue 50 \\
      --accent 35 --out blue-tit.png
  python render_creature_sprite.py --form mammal --hue 25 --tail bushy \\
      --out squirrel.png

Forms: bug, beetle, caterpillar, moth, bee, spider, bird, mammal, bat
"""

import argparse
import colorsys
import math
from pathlib import Path

from PIL import Image

WP, HP = 32, 24          # native sprite grid (landscape — distinguishes from trees)
CX, CY = WP // 2, HP // 2


# --------------------------------------------------------------------------- #
# deterministic value noise
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
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return (round(r * 255), round(g * 255), round(b * 255))


def build_ramp(hue, sat):
    """Four body tones, matching A1's lightness steps (outline / dark / mid / light)."""
    return {
        "outline": hsl(hue, min(100, sat + 8), 12),
        "dark":    hsl(hue, sat, 26),
        "mid":     hsl(hue, sat, 42),
        "light":   hsl(hue - 10, sat, 62),
    }


def build_accent(hue, sat, light):
    return {
        "light": hsl(hue, sat, min(92, light + 14)),
        "dark":  hsl(hue, sat, light),
    }


def shade(x, cx, span, ramp):
    """Left-lit 3-tone shading by horizontal position."""
    rel = (x - cx) / max(1, span)
    if rel < -0.25:
        return ramp["light"]
    if rel > 0.45:
        return ramp["dark"]
    return ramp["mid"]


def hue_from_hex(s):
    s = s.lstrip("#")
    r, g, b = (int(s[i:i+2], 16) / 255 for i in (0, 2, 4))
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360


# --------------------------------------------------------------------------- #
# grid utilities
# --------------------------------------------------------------------------- #
def _blank():
    return [[None] * WP for _ in range(HP)]


def _neighbors4(x, y):
    return ((x+1, y), (x-1, y), (x, y+1), (x, y-1))


def _fill_ellipse(g, cx, cy, rx, ry, ramp, span=None, dark_only=False):
    span = span if span is not None else rx
    for y in range(HP):
        for x in range(WP):
            if ((x - cx) / max(0.5, rx)) ** 2 + ((y - cy) / max(0.5, ry)) ** 2 <= 1.0:
                g[y][x] = ramp["dark"] if dark_only else shade(x, cx, span, ramp)


def _line(g, x0, y0, x1, y1, color):
    """Bresenham for short body legs / antennae / wings struts."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        if 0 <= x < WP and 0 <= y < HP:
            g[y][x] = color
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x += sx
        if e2 <= dx:
            err += dx; y += sy


# --------------------------------------------------------------------------- #
# form builders — each returns (grid, span) where span is used for left-lit
# shading width and the accent overlay extent
# --------------------------------------------------------------------------- #
def form_bug(ramp, P):
    """Tiny oval body — aphid, scale, mealybug, mite, generic small insect."""
    g = _blank()
    s = P["size"]
    rx = max(3, int(round(5 * s * P["aspect"])))
    ry = max(2, int(round(4 * s / max(0.6, P["aspect"]))))
    _fill_ellipse(g, CX, CY, rx, ry, ramp, span=rx)
    # tiny legs
    if P["legs"]:
        for dy_off in (-1, 0, 1):
            for dx_off in (-rx - 1, rx + 1):
                xx, yy = CX + dx_off, CY + dy_off
                if 0 <= xx < WP and 0 <= yy < HP:
                    g[yy][xx] = ramp["outline"]
    # antennae (two short whiskers up-front)
    if P["antennae"]:
        ax = CX + rx - 1
        for k in (1, 2):
            yy = CY - ry - k
            if 0 <= yy < HP:
                g[yy][ax + k - 1] = ramp["outline"]
    return g, rx


def form_beetle(ramp, P):
    """Oval beetle with central elytra split."""
    g = _blank()
    s = P["size"]
    rx = max(5, int(round(8 * s * P["aspect"])))
    ry = max(3, int(round(5 * s / max(0.6, P["aspect"]))))
    _fill_ellipse(g, CX, CY, rx, ry, ramp, span=rx)
    # head (small dark cap on the right / "front" of the bug)
    for y in range(CY - 1, CY + 2):
        for x in range(CX + rx - 2, CX + rx):
            if 0 <= x < WP and 0 <= y < HP and g[y][x] is not None:
                g[y][x] = ramp["dark"]
    # central elytra seam
    for y in range(CY - ry + 1, CY + ry):
        if 0 <= y < HP and g[y][CX] is not None:
            g[y][CX] = ramp["outline"]
    # legs (3 each side)
    if P["legs"]:
        for k, dy_off in enumerate((-2, 0, 2)):
            for sign in (-1, 1):
                xx, yy = CX + sign * (rx + 1), CY + dy_off
                if 0 <= xx < WP and 0 <= yy < HP:
                    g[yy][xx] = ramp["outline"]
                xx2 = xx + sign  # second segment for longer legs
                if 0 <= xx2 < WP and 0 <= yy < HP:
                    g[yy][xx2] = ramp["outline"]
    return g, rx


def form_caterpillar(ramp, P):
    """Horizontal segmented worm."""
    g = _blank()
    s = P["size"]
    length = max(8, int(round(18 * s)))
    thickness = max(2, int(round(3 * s)))
    x0 = CX - length // 2
    y0 = CY - thickness // 2
    for i in range(length):
        for t in range(thickness):
            xx, yy = x0 + i, y0 + t
            if 0 <= xx < WP and 0 <= yy < HP:
                # alternating segment shading for that "ringed" look
                seg = (i // 2) % 2
                col = ramp["dark"] if seg else ramp["mid"]
                if t == 0:
                    col = ramp["light"]   # left-lit top
                if t == thickness - 1:
                    col = ramp["dark"]     # under-shadow
                g[yy][xx] = col
    # head cap
    head_x = x0 + length - 1
    if 0 <= head_x < WP and 0 <= y0 < HP and 0 <= y0 + thickness - 1 < HP:
        for t in range(thickness):
            yy = y0 + t
            if 0 <= head_x + 1 < WP:
                g[yy][head_x + 1] = ramp["dark"]
    # optional bristles
    if P["bristles"]:
        for i in range(2, length, 3):
            xx = x0 + i
            if 0 <= xx < WP and 0 <= y0 - 1 < HP:
                g[y0 - 1][xx] = ramp["outline"]
    return g, length // 2


def form_moth(ramp, P):
    """Symmetric wings spread top-down view — forewing (upper, larger) + hindwing
    (lower, smaller) on each side, with a clear notch where they meet."""
    g = _blank()
    s = P["size"]
    body_w = max(1, int(round(1.4 * s)))
    body_top = max(1, int(round(CY - 8 * s)))
    body_bot = min(HP - 2, int(round(CY + 8 * s)))
    fore_rx = max(6, int(round(9 * s)))
    fore_ry = max(4, int(round(5 * s)))
    hind_rx = max(4, int(round(6 * s)))
    hind_ry = max(3, int(round(4 * s)))
    fore_cy = body_top + 3
    hind_cy = body_bot - 2
    for sign in (-1, 1):
        fore_cx = CX + sign * (fore_rx - 2)
        hind_cx = CX + sign * (hind_rx - 1)
        # forewing
        for y in range(HP):
            for x in range(WP):
                if sign * (x - CX) < body_w:   # stay outside the body strip
                    continue
                if ((x - fore_cx) / fore_rx) ** 2 + ((y - fore_cy) / fore_ry) ** 2 <= 1.0:
                    g[y][x] = shade(x, CX, fore_rx + abs(CX - fore_cx), ramp)
        # hindwing
        for y in range(HP):
            for x in range(WP):
                if sign * (x - CX) < body_w:
                    continue
                if ((x - hind_cx) / hind_rx) ** 2 + ((y - hind_cy) / hind_ry) ** 2 <= 1.0:
                    if g[y][x] is None:        # leave the forewing-hindwing notch open
                        g[y][x] = shade(x, CX, hind_rx + abs(CX - hind_cx), ramp)
    # body strip down the middle (drawn last so it sits on top)
    for y in range(body_top, body_bot + 1):
        for x in range(CX - body_w, CX + body_w + 1):
            if 0 <= x < WP and 0 <= y < HP:
                edge = (x == CX - body_w or x == CX + body_w)
                g[y][x] = ramp["outline"] if edge else ramp["dark"]
    # antennae (curl outwards)
    if P["antennae"]:
        for sign in (-1, 1):
            for k in (1, 2, 3):
                xx, yy = CX + sign * k, body_top - k
                if 0 <= xx < WP and 0 <= yy < HP:
                    g[yy][xx] = ramp["outline"]
    return g, fore_rx + 4


def form_bee(ramp, P):
    """Side-view bee/wasp/fly: head right + striped abdomen left + wing arching
    UP over the back. Body sits low in the canvas so the wing has room above."""
    g = _blank()
    s = P["size"]
    # body lives in the LOWER half of the canvas so the wing sticks UP clearly
    body_cy = CY + 4
    ab_rx = max(5, int(round(7 * s * P["aspect"])))
    ab_ry = max(2, int(round(3 * s / max(0.6, P["aspect"]))))
    ab_cx = CX - 2
    _fill_ellipse(g, ab_cx, body_cy, ab_rx, ab_ry, ramp, span=ab_rx)
    # head/thorax (right side)
    th_r = max(2, int(round(3 * s)))
    th_cx = ab_cx + ab_rx
    th_cy = body_cy - 1
    _fill_ellipse(g, th_cx, th_cy, th_r, th_r, ramp, span=th_r)
    # eye
    for dy in (-1, 0):
        xx, yy = th_cx + th_r - 1, th_cy + dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # WING — one big pale arched ellipse going up and back, drawn LAST so visible.
    # Pale fill + dark outline so it reads even on a saturated body.
    wing_rx = max(7, int(round(9 * s)))
    wing_ry = max(3, int(round(5 * s)))
    wing_cx = ab_cx + 1
    wing_cy = body_cy - ab_ry - wing_ry + 2
    for y in range(HP):
        for x in range(WP):
            d = ((x - wing_cx) / wing_rx) ** 2 + ((y - wing_cy) / wing_ry) ** 2
            if d <= 1.0 and y <= body_cy - ab_ry:
                # edge → dark, interior → very pale wing-membrane color
                if d >= 0.7:
                    g[y][x] = ramp["dark"]
                else:
                    g[y][x] = ramp["light"]
    # legs underneath
    if P["legs"]:
        for k in (-3, 0, 3):
            xx, yy = ab_cx + k, body_cy + ab_ry
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
            if 0 <= xx < WP and 0 <= yy + 1 < HP:
                g[yy + 1][xx] = ramp["outline"]
    # antennae
    if P["antennae"]:
        for k in (1, 2):
            xx, yy = th_cx + th_r - 2 + k, th_cy - th_r - k + 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    return g, ab_rx


def form_spider(ramp, P):
    """Round body + 8 legs radiating."""
    g = _blank()
    s = P["size"]
    r = max(3, int(round(4 * s)))
    _fill_ellipse(g, CX, CY, r, r, ramp, span=r)
    # 8 angled legs, 4 each side, going diagonally
    leg_len = max(4, int(round(7 * s)))
    angles_left = (-150, -170, 170, 150)
    angles_right = (-30, -10, 10, 30)
    for deg in (*angles_left, *angles_right):
        rad = math.radians(deg)
        for step in range(1, leg_len + 1):
            xx = int(round(CX + math.cos(rad) * (r + step)))
            yy = int(round(CY + math.sin(rad) * (r + step)))
            if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                g[yy][xx] = ramp["outline"] if step > 1 else ramp["dark"]
    return g, r + leg_len // 2


def form_bird(ramp, P):
    """Small passerine perched, facing right. Round body + smaller head + tail + eye."""
    g = _blank()
    s = P["size"]
    body_rx = max(4, int(round(6 * s)))
    body_ry = max(4, int(round(5 * s)))
    body_cx = CX - 2
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head (smaller circle up-right)
    head_r = max(2, int(round(3 * s)))
    head_cx = body_cx + body_rx - 1
    head_cy = body_cy - body_ry + 1
    _fill_ellipse(g, head_cx, head_cy, head_r, head_r, ramp, span=head_r)
    # beak (2-3 px point)
    for k in range(1, 3):
        xx, yy = head_cx + head_r + k - 1, head_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # eye dot
    eye_x, eye_y = head_cx + 1, head_cy - 1
    if 0 <= eye_x < WP and 0 <= eye_y < HP:
        g[eye_y][eye_x] = ramp["outline"]
    # tail (short triangle off the back)
    for k in range(1, max(3, int(round(4 * s))) + 1):
        xx, yy = body_cx - body_rx - k + 1, body_cy + k - 2
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # legs (two short sticks down)
    foot_y = body_cy + body_ry
    for dx_off in (-1, 1):
        for k in range(1, 3):
            xx, yy = body_cx + dx_off, foot_y + k - 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    return g, body_rx + 2


def form_mammal(ramp, P):
    """Side-view small mammal — squirrel/mouse/dormouse. Body + head + legs + tail."""
    g = _blank()
    s = P["size"]
    body_rx = max(5, int(round(8 * s)))
    body_ry = max(3, int(round(4 * s)))
    body_cx = CX - 1
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head (right side)
    head_r = max(2, int(round(3 * s)))
    head_cx = body_cx + body_rx - 1
    head_cy = body_cy - 1
    _fill_ellipse(g, head_cx, head_cy, head_r, head_r, ramp, span=head_r)
    # ears (2 little tufts on top of head)
    for sign in (-1, 1):
        xx, yy = head_cx + sign, head_cy - head_r
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # nose / eye
    if 0 <= head_cx + head_r < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + head_r] = ramp["outline"]
    if 0 <= head_cx + 1 < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx + 1] = ramp["outline"]
    # 4 legs (front + back, each 2 px)
    foot_y = body_cy + body_ry
    for dx_off in (-body_rx + 2, body_rx - 2):
        for k in range(1, 3):
            xx, yy = body_cx + dx_off, foot_y + k - 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"] if k == 2 else ramp["dark"]
    # tail (bushy or thin) — drawn behind the body (back end, left side)
    tail_x0 = body_cx - body_rx
    if P["tail"] == "bushy":
        # squirrel-style: big fluffy column rising UP from the back end
        tail_cx = tail_x0 - 1
        tail_top = body_cy - body_ry - 7
        # ellipse-ish mass: 3px wide at base, fanning to 5px at the curl
        for y in range(max(0, tail_top), body_cy + 1):
            band = (body_cy - y)
            width = 2 + (band // 2)
            for dx in range(-width, width + 1):
                xx = tail_cx + dx
                if not (0 <= xx < WP and 0 <= y < HP):
                    continue
                if g[y][xx] is not None:
                    continue
                # left-lit shading + dark outline pixels at the leftmost edge
                if dx == -width or dx == width:
                    g[y][xx] = ramp["dark"]
                else:
                    g[y][xx] = ramp["light"] if dx < 0 else ramp["mid"]
        # the curl tip (top-left of the tail)
        for k in range(2):
            xx, yy = tail_cx - 2 - k, tail_top + k
            if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                g[yy][xx] = ramp["dark"]
    elif P["tail"] == "thin":
        for k in range(0, 6):
            xx = tail_x0 - k
            yy = body_cy + 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    return g, body_rx + 1


def form_bat(ramp, P):
    """Wings spread up-and-out, body small in middle, ear nubs.
    Classic bat silhouette: small central body, each wing is a scalloped
    triangle that goes from the body's shoulder UP and OUT to the wingtip,
    then drapes back DOWN to a lower trailing edge — leaving open arches
    underneath the wings."""
    g = _blank()
    s = P["size"]
    body_rx = max(2, int(round(2 * s)))
    body_ry = max(3, int(round(4 * s)))
    body_cy = CY + 1
    _fill_ellipse(g, CX, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # wing membranes
    wing_span = max(9, int(round(13 * s)))
    shoulder_y = body_cy - body_ry + 1
    for sign in (-1, 1):
        # tip is up and out from the shoulder
        tip_x = CX + sign * wing_span
        tip_y = max(1, shoulder_y - 4)
        # trailing-edge end (drapes lower at the tip than shoulder)
        trail_y = body_cy + body_ry - 1
        for step in range(1, wing_span + 1):
            frac = step / wing_span
            xx = CX + sign * (body_rx + step - 1)
            # upper leading edge: from shoulder up to tip
            upper = int(round(shoulder_y - (shoulder_y - tip_y) * (frac ** 0.7)))
            # lower trailing edge: scalloped arch — high near tip
            arch = int(round((trail_y - tip_y - 1) * (1 - (2 * frac - 1) ** 2)))
            lower = tip_y + arch
            # scallop notch every 3 steps along the lower edge
            if step % 3 == 0 and step < wing_span - 1:
                lower -= 1
            for yy in range(upper, lower + 1):
                if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                    if yy == upper or yy == lower:
                        g[yy][xx] = ramp["dark"]
                    else:
                        g[yy][xx] = shade(xx, CX, wing_span + body_rx, ramp)
        # finger struts: faint dark verticals at 1/3 and 2/3 of the span
        for frac in (0.35, 0.7):
            sx = CX + sign * int(round(wing_span * frac)) + (sign * body_rx)
            sy_top = int(round(shoulder_y - (shoulder_y - tip_y) * (frac ** 0.7)))
            for yy in range(sy_top, min(HP, sy_top + 3)):
                if 0 <= sx < WP and 0 <= yy < HP and g[yy][sx] is not None:
                    g[yy][sx] = ramp["dark"]
    # ears (two nubs on top of body)
    for sign in (-1, 1):
        xx, yy = CX + sign, body_cy - body_ry - 1
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    return g, body_rx + wing_span // 2


FORMS = {
    "bug": form_bug,
    "beetle": form_beetle,
    "caterpillar": form_caterpillar,
    "moth": form_moth,
    "bee": form_bee,
    "spider": form_spider,
    "bird": form_bird,
    "mammal": form_mammal,
    "bat": form_bat,
}


# --------------------------------------------------------------------------- #
# overlays
# --------------------------------------------------------------------------- #
def _is_body(c, ramp):
    """True for body fill pixels (dark/mid only) — skip outlines AND wing-light
    pixels so accent never overwrites wings or silhouette."""
    return c == ramp["dark"] or c == ramp["mid"]


def apply_accent(grid, ramp, accent_amt, acc_ramp, mode, seed):
    """Sprinkle accent (stripes / spots / wing markings) over body pixels.

    mode = 'spots' → scattered dots
    mode = 'stripes' → narrow horizontal bands across the body (bees/wasps)
    """
    if accent_amt <= 0 or acc_ramp is None:
        return grid
    a = accent_amt / 100.0
    if mode == "stripes":
        # paint single-row stripes every 3rd row, dark accent only (cleaner read)
        for y in range(HP):
            if (y % 3) != 1:
                continue
            for x in range(WP):
                if _is_body(grid[y][x], ramp):
                    grid[y][x] = acc_ramp["dark"]
    else:
        for y in range(HP):
            for x in range(WP):
                if not _is_body(grid[y][x], ramp):
                    continue
                if _hash(x * 2 + 3, y * 2 + 5, seed + 91) < a:
                    grid[y][x] = acc_ramp["light"] if (x + y) % 2 == 0 else acc_ramp["dark"]
    return grid


def _outline_exterior(grid, color):
    h, w = len(grid), len(grid[0])
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


def render(form, hue, sat, scale, P, acc_ramp, accent_amt, accent_mode):
    ramp = build_ramp(hue, sat)
    grid, _span = FORMS[form](ramp, P)
    grid = apply_accent(grid, ramp, accent_amt, acc_ramp, accent_mode, P["seed"])
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
                    help="creature body plan")
    ap.add_argument("--hue", type=float,
                    help="body base hue 0-360 (green~120, brown~25, "
                         "blue~210, yellow~50, red~5, grey-purple~280)")
    ap.add_argument("--base-color", help="hex #rrggbb; hue is derived from it")
    ap.add_argument("--sat", type=float, default=55,
                    help="body saturation 0-100 (default 55 = punchy/A1)")
    ap.add_argument("--size", type=float, default=1.0,
                    help="overall size multiplier 0.6 small bug -> 1.2 large (default 1.0)")
    ap.add_argument("--aspect", type=float, default=1.0,
                    help=">1 elongated/wide body, <1 compact/round (default 1.0)")
    ap.add_argument("--legs", action="store_true", default=True,
                    help="draw legs (default on; --no-legs to disable)")
    ap.add_argument("--no-legs", dest="legs", action="store_false")
    ap.add_argument("--antennae", action="store_true", default=True,
                    help="draw antennae for bug/moth (default on; --no-antennae)")
    ap.add_argument("--no-antennae", dest="antennae", action="store_false")
    ap.add_argument("--bristles", action="store_true", default=False,
                    help="caterpillar bristles/hairs (default off)")
    ap.add_argument("--tail", choices=("none", "thin", "bushy"), default="thin",
                    help="mammal tail style (default thin)")
    ap.add_argument("--accent-hue", type=float,
                    help="hue for stripes/spots/wing-markings (e.g. 50 yellow bee stripes, "
                         "10 red ladybird spots)")
    ap.add_argument("--accent", type=float, default=0,
                    help="0-100 amount of accent (needs --accent-hue)")
    ap.add_argument("--accent-mode", choices=("spots", "stripes"), default="spots",
                    help="how accent paints onto the body (default spots)")
    ap.add_argument("--accent-light", type=float, default=62,
                    help="lightness of accent 0-100 (default 62)")
    ap.add_argument("--seed", type=int, default=0,
                    help="deterministic variation seed for accent placement")
    ap.add_argument("--scale", type=int, default=10, help="nearest-neighbor upscale")
    ap.add_argument("--out", required=True, help="output PNG path")
    a = ap.parse_args()

    if a.hue is None and not a.base_color:
        ap.error("provide --hue or --base-color")
    hue = a.hue if a.hue is not None else hue_from_hex(a.base_color)

    P = {
        "size":     a.size,
        "aspect":   a.aspect,
        "legs":     a.legs,
        "antennae": a.antennae,
        "bristles": a.bristles,
        "tail":     a.tail,
        "seed":     a.seed,
    }
    acc_ramp = None
    if a.accent and a.accent_hue is not None:
        acc_ramp = build_accent(a.accent_hue, 70, a.accent_light)

    img = render(a.form, hue, a.sat, a.scale, P, acc_ramp, a.accent, a.accent_mode)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}  form={a.form} hue={hue:.0f} sat={a.sat:.0f} "
          f"size={a.size:.2f} acc={a.accent:.0f} seed={a.seed} "
          f"({WP}x{HP} -> {img.width}x{img.height})")


if __name__ == "__main__":
    main()
