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
    """Side-view bee/wasp/fly. Layout (left→right): fat striped abdomen, fuzzy
    thorax, round head with big compound eye. A pale wing arches up over the
    back. Stripes are classic pixel-art HORIZONTAL bands on the abdomen for
    instant readability (anatomically each band wraps the body but flat-shaded
    horizontal stripes are the convention that reads as "bee")."""
    g = _blank()
    s = P["size"]
    # body lives in the LOWER half so the wing has room above
    body_cy = CY + 4

    # ---- abdomen ----
    ab_rx = max(5, int(round(7 * s * P["aspect"])))
    ab_ry = max(3, int(round(4 * s / max(0.6, P["aspect"]))))
    ab_cx = CX - 4
    _fill_ellipse(g, ab_cx, body_cy, ab_rx, ab_ry, ramp, span=ab_rx)
    # horizontal stripes — paint 2 dark bands across the abdomen.
    # bands are 1 row tall and span only abdomen-shaped pixels.
    for stripe_dy in (-1, 1):
        y = body_cy + stripe_dy
        for x in range(WP):
            if 0 <= y < HP and g[y][x] in (ramp["mid"], ramp["dark"], ramp["light"]):
                g[y][x] = ramp["outline"]

    # ---- thorax (middle — slightly higher) ----
    th_r = max(2, int(round(3 * s)))
    th_cx = ab_cx + ab_rx
    th_cy = body_cy - 1
    _fill_ellipse(g, th_cx, th_cy, th_r, th_r, ramp, span=th_r)

    # ---- head (right) ----
    hd_r = max(2, int(round(3 * s)))
    hd_cx = th_cx + th_r + 1
    hd_cy = th_cy + 1
    _fill_ellipse(g, hd_cx, hd_cy, hd_r, hd_r, ramp, span=hd_r)

    # ---- big black compound eye (2x2 block on the front of the head) ----
    eye_x0 = hd_cx + hd_r - 2
    for dy in range(2):
        for dx in range(2):
            xx, yy = eye_x0 + dx, hd_cy - 1 + dy
            if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is not None:
                g[yy][xx] = ramp["outline"]

    # ---- WING — pale arched ellipse, drawn LAST so visible on top ----
    wing_rx = max(7, int(round(9 * s)))
    wing_ry = max(3, int(round(5 * s)))
    wing_cx = ab_cx + 2
    wing_cy = body_cy - ab_ry - wing_ry + 3
    for y in range(HP):
        for x in range(WP):
            d = ((x - wing_cx) / wing_rx) ** 2 + ((y - wing_cy) / wing_ry) ** 2
            if d <= 1.0 and y < body_cy - ab_ry + 1:
                if d >= 0.78:
                    g[y][x] = ramp["dark"]    # wing edge / veins
                else:
                    g[y][x] = ramp["light"]   # pale membrane

    # ---- legs underneath ----
    if P["legs"]:
        for k in (-3, 0, 3):
            xx, yy = ab_cx + k, body_cy + ab_ry
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
            if 0 <= xx < WP and 0 <= yy + 1 < HP:
                g[yy + 1][xx] = ramp["outline"]

    # ---- antennae (curl forward off the head) ----
    if P["antennae"]:
        for k in (1, 2):
            xx, yy = hd_cx + k, hd_cy - hd_r - k + 1
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


def form_fungus(ramp, P):
    """Organic blob with lobed edges — covers bracket fungi, lichens, mycorrhizae,
    bacterial-nodule clusters. Two modes via --aspect:
      aspect >= 1.0 → BRACKET fungus (half-dome jutting from a "trunk" on the
        right edge, classic Fomitopsis silhouette)
      aspect <  1.0 → LICHEN/cluster (irregular crusty patch, lobed everywhere)"""
    g = _blank()
    s = P["size"]
    seed = P["seed"]
    if P["aspect"] >= 1.0:
        # Bracket fungus: half-circle attached to trunk on the right edge.
        # Trunk = ramp["outline"] vertical bar at the right side.
        rx = max(8, int(round(11 * s)))
        ry = max(5, int(round(7 * s)))
        cy = CY + 1
        anchor_x = WP - 4  # anchor on right side (the "trunk")
        for y in range(HP):
            for x in range(WP):
                if x > anchor_x:
                    continue   # trunk side, stays empty/becomes trunk
                if ((x - anchor_x) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    g[y][x] = shade(x, anchor_x - rx // 2, rx, ramp)
        # carve a curved underside lip (subtle dark band on the lower edge)
        for x in range(WP):
            for y in range(HP - 1, -1, -1):
                if g[y][x] is not None:
                    if y + 1 < HP and g[y + 1][x] is None:
                        # bottom edge: paint with a brighter "lip"
                        g[y][x] = ramp["light"]
                    break
        # trunk strip
        for y in range(HP):
            for tx in range(anchor_x + 1, min(WP, anchor_x + 4)):
                g[y][tx] = ramp["outline"] if tx == anchor_x + 1 else ramp["dark"]
        # speckled texture across the cap
        for y in range(HP):
            for x in range(WP):
                if g[y][x] in (ramp["mid"], ramp["dark"]):
                    if _hash(x, y, seed + 23) < 0.06:
                        g[y][x] = ramp["light"]
        span = rx
    else:
        # Lichen / cluster: irregular lobed patch centered, no trunk
        rx = max(7, int(round(10 * s)))
        ry = max(5, int(round(7 * s)))
        for y in range(HP):
            for x in range(WP):
                # lobed ellipse: radius wobbles with angle
                dx, dy = x - CX, y - CY
                ang = math.atan2(dy, dx)
                wobble = 0.78 + 0.30 * math.sin(ang * 4 + seed)
                if (dx / rx) ** 2 + (dy / ry) ** 2 <= wobble:
                    g[y][x] = shade(x, CX, rx, ramp)
        # carve a few internal gaps for crusty texture
        for y in range(HP):
            for x in range(WP):
                if g[y][x] is None:
                    continue
                if _hash(x, y, seed + 91) < 0.10:
                    g[y][x] = ramp["dark"]
                elif _hash(x, y, seed + 137) < 0.04:
                    g[y][x] = None  # tiny holes
        span = rx
    return g, span


def form_reptile(ramp, P):
    """Reptile side view. Two modes via --aspect:
        aspect >= 1.0 → LIZARD (elongated body low to ground, 4 short legs, long tail).
        aspect <  1.0 → TURTLE (dome shell centre, tiny head + stumpy legs poking out)."""
    g = _blank()
    s = P["size"]
    if P["aspect"] >= 1.0:
        # LIZARD — body low, elongated, tail longer than body
        body_rx = max(6, int(round(8 * s)))
        body_ry = max(2, int(round(3 * s)))
        body_cx = CX - 3
        body_cy = CY + 3
        _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
        # head — small oval on the right
        head_r = max(2, int(round(2 * s)))
        head_cx = body_cx + body_rx
        head_cy = body_cy - 1
        _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
        # eye
        if 0 <= head_cx + head_r < WP and 0 <= head_cy - 1 < HP:
            g[head_cy - 1][head_cx + head_r] = ramp["outline"]
        # tail — thin taper off the LEFT going down-left
        for k in range(1, max(6, int(round(11 * s))) + 1):
            xx = body_cx - body_rx - k
            yy = body_cy + k // 3
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["dark"] if k < 3 else ramp["outline"]
        # 4 short legs sticking down
        foot_y = body_cy + body_ry
        for dx_off in (-body_rx + 2, body_rx - 3):
            for k in range(1, 3):
                xx, yy = body_cx + dx_off, foot_y + k - 1
                if 0 <= xx < WP and 0 <= yy < HP:
                    g[yy][xx] = ramp["outline"]
        return g, body_rx + 2
    else:
        # TURTLE — dome shell dominates, tiny head + legs poke out
        shell_rx = max(7, int(round(10 * s)))
        shell_ry = max(4, int(round(6 * s)))
        cx = CX - 1
        cy = CY + 1
        # shell as half-ellipse (top half only)
        for y in range(HP):
            for x in range(WP):
                if y > cy:
                    continue
                if ((x - cx) / shell_rx) ** 2 + ((y - cy) / shell_ry) ** 2 <= 1.0:
                    g[y][x] = shade(x, cx, shell_rx, ramp)
        # shell rim (dark under-line)
        for x in range(cx - shell_rx, cx + shell_rx + 1):
            if 0 <= x < WP and 0 <= cy < HP and g[cy][x] is not None:
                g[cy][x] = ramp["outline"]
        # scute pattern — 3 dark spots on the shell top
        seed = P.get("seed", 0)
        for k in range(4):
            sx = cx - shell_rx + (k + 1) * (shell_rx // 2) + int(_hash(k, 0, seed) * 2) - 1
            sy = cy - int(shell_ry * 0.55)
            if 0 <= sx < WP and 0 <= sy < HP and g[sy][sx] is not None:
                g[sy][sx] = ramp["dark"]
        # head — small oval poking out right
        head_cx = cx + shell_rx
        head_cy = cy
        if 0 <= head_cx < WP and 0 <= head_cy < HP:
            g[head_cy][head_cx] = ramp["mid"]
        if 0 <= head_cx + 1 < WP and 0 <= head_cy < HP:
            g[head_cy][head_cx + 1] = ramp["dark"]
        if 0 <= head_cx + 1 < WP and 0 <= head_cy - 1 < HP:
            g[head_cy - 1][head_cx + 1] = ramp["outline"]  # eye
        # 4 stumpy leg nubs
        for dx_off, sign in ((-shell_rx + 2, -1), (shell_rx - 3, 1)):
            xx = cx + dx_off
            yy = cy + 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
        # tail nub off the left
        if 0 <= cx - shell_rx - 1 < WP and 0 <= cy < HP:
            g[cy][cx - shell_rx - 1] = ramp["outline"]
        return g, shell_rx


def form_fish(ramp, P):
    """Side-view fusiform fish — body ellipse, tail fin left, dorsal fin top, eye + gill."""
    g = _blank()
    s = P["size"]
    body_rx = max(7, int(round(10 * s * P["aspect"])))
    body_ry = max(3, int(round(4 * s / max(0.7, P["aspect"]))))
    body_cx = CX - 1
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # tail fin — triangle on the left
    tail_root_x = body_cx - body_rx
    tail_len = max(3, int(round(5 * s)))
    for k in range(1, tail_len + 1):
        h = k * 2
        for dy in range(-h, h + 1):
            xx = tail_root_x - k
            yy = body_cy + dy
            if 0 <= xx < WP and 0 <= yy < HP and abs(dy) <= h - (k - 1):
                if abs(dy) == h - (k - 1) or k == tail_len:
                    g[yy][xx] = ramp["outline"]
                elif g[yy][xx] is None:
                    g[yy][xx] = shade(xx, body_cx, body_rx + tail_len, ramp)
    # dorsal fin — triangle up on top-middle
    dorsal_h = max(2, int(round(3 * s)))
    for k in range(1, dorsal_h + 1):
        for dx in range(-2 - k // 2, 3 + k // 2):
            xx = body_cx + dx
            yy = body_cy - body_ry - k
            if 0 <= xx < WP and 0 <= yy < HP:
                is_edge = (k == dorsal_h or dx == -2 - k // 2 or dx == 2 + k // 2)
                g[yy][xx] = ramp["outline"] if is_edge else ramp["dark"]
    # eye dot near front (right side)
    eye_x = body_cx + body_rx - 2
    eye_y = body_cy - 1
    if 0 <= eye_x < WP and 0 <= eye_y < HP:
        g[eye_y][eye_x] = ramp["outline"]
    # gill line — vertical dark line behind the head
    gill_x = body_cx + body_rx - 4
    for dy in range(-body_ry + 1, body_ry):
        yy = body_cy + dy
        if 0 <= gill_x < WP and 0 <= yy < HP and g[yy][gill_x] is not None:
            g[yy][gill_x] = ramp["dark"]
    # small mouth dot at front
    mouth_x = body_cx + body_rx - 1
    if 0 <= mouth_x < WP and 0 <= body_cy + 1 < HP:
        g[body_cy + 1][mouth_x] = ramp["outline"]
    return g, body_rx + tail_len // 2


def form_amphibian(ramp, P):
    """Squat frog/toad — round body, tucked bent-jump legs, small head, big eye, no tail."""
    g = _blank()
    s = P["size"]
    body_rx = max(6, int(round(8 * s)))
    body_ry = max(4, int(round(5 * s)))
    body_cx = CX
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head bump — a smaller ellipse tucked on the top of the body
    head_r = max(2, int(round(3 * s)))
    head_cx = body_cx + body_rx - head_r - 1
    head_cy = body_cy - body_ry + 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # big eye on top of head — bulging eye is the signature
    eye_cx = head_cx + 1
    eye_cy = head_cy - 1
    for dx, dy in ((0, 0), (1, 0), (0, -1), (1, -1)):
        xx, yy = eye_cx + dx, eye_cy + dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"] if (dx + dy) % 2 == 0 else ramp["dark"]
    # bent hind leg (folded, ready to jump) — showing as a Z-shape on the back-left
    knee_x = body_cx - body_rx + 1
    knee_y = body_cy + body_ry - 1
    # thigh
    for k in range(1, 4):
        xx = knee_x + k - 1
        yy = knee_y - k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # shin going down-left
    for k in range(1, 3):
        xx = knee_x - k + 1
        yy = knee_y + k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # front leg — small dab under the head
    front_x = head_cx - 1
    front_y = body_cy + body_ry
    for k in range(2):
        xx = front_x + k
        yy = front_y + k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # nostrils / spot on the crown
    if 0 <= head_cx + head_r < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + head_r] = ramp["dark"]
    return g, body_rx


def form_large_mammal(ramp, P):
    """Larger side-view mammal — deer / boar proportions. Longer body + longer legs +
    longer neck lifting head high. No bushy tail (thin or absent)."""
    g = _blank()
    s = P["size"]
    body_rx = max(7, int(round(10 * s)))
    body_ry = max(3, int(round(4 * s)))
    body_cx = CX - 3
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # neck rising up-right from the shoulder
    neck_base_x = body_cx + body_rx - 2
    neck_top_x = neck_base_x + 2
    neck_top_y = body_cy - body_ry - 2
    for k in range(0, 4):
        xx = neck_base_x + (k // 2)
        yy = body_cy - body_ry - k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"] if k in (0, 1) else ramp["outline"]
        if k >= 1 and 0 <= xx + 1 < WP and 0 <= yy < HP:
            g[yy][xx + 1] = ramp["mid"]
    # head — small oval at the top of the neck
    head_r = max(2, int(round(2 * s)))
    head_cx = neck_top_x + head_r
    head_cy = neck_top_y
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # ears (2 upright)
    for sign in (-1, 1):
        xx, yy = head_cx + sign, head_cy - head_r - 1
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # eye
    if 0 <= head_cx + 1 < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + 1] = ramp["outline"]
    # 4 long legs (front pair + back pair, each 4 px tall)
    leg_top_y = body_cy + body_ry - 1
    leg_bot_y = HP - 1
    for dx_off in (-body_rx + 2, -body_rx + 4, body_rx - 4, body_rx - 2):
        xx = body_cx + dx_off
        for yy in range(leg_top_y, leg_bot_y + 1):
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"] if yy == leg_bot_y else ramp["dark"]
    # short tail nub off the back
    tail_x = body_cx - body_rx
    if 0 <= tail_x < WP and 0 <= body_cy < HP:
        g[body_cy][tail_x] = ramp["outline"]
    return g, body_rx + 2


def form_aquatic_mammal(ramp, P):
    """Sleek elongated otter / water-vole with visible waterline below.
    Body low and long, head right, small ears, thick tail extending back-left."""
    g = _blank()
    s = P["size"]
    body_rx = max(8, int(round(11 * s)))
    body_ry = max(2, int(round(3 * s)))
    body_cx = CX - 2
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head — small oval on the right, slightly raised
    head_r = max(2, int(round(3 * s)))
    head_cx = body_cx + body_rx - 1
    head_cy = body_cy - 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # ears — small round nubs
    for sign in (-1, 1):
        xx, yy = head_cx + sign, head_cy - head_r
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # eye + nose
    if 0 <= head_cx + head_r < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + head_r] = ramp["outline"]
    if 0 <= head_cx + 1 < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx + 1] = ramp["outline"]
    # thick tapered tail off the LEFT
    tail_len = max(5, int(round(8 * s)))
    for k in range(1, tail_len + 1):
        xx = body_cx - body_rx - k + 1
        yy = body_cy + (k // 4)
        thickness = max(0, body_ry - k // 3)
        for dy in range(-thickness, thickness + 1):
            yy2 = yy + dy
            if 0 <= xx < WP and 0 <= yy2 < HP:
                if abs(dy) == thickness or k == tail_len:
                    g[yy2][xx] = ramp["outline"]
                elif g[yy2][xx] is None:
                    g[yy2][xx] = shade(xx, body_cx, body_rx + tail_len, ramp)
    # waterline: dashed horizontal line under the body
    waterline_y = min(HP - 1, body_cy + body_ry + 1)
    for x in range(WP):
        if 0 <= waterline_y < HP and g[waterline_y][x] is None:
            if x % 3 != 2:
                g[waterline_y][x] = ramp["dark"]
    return g, body_rx + 2


def form_water_bird(ramp, P):
    """Side-view duck / coot / goose sitting on the water.
    Round body, arched neck up to head, bill. No visible legs (underwater).
    Waterline dashes cross the body's underside."""
    g = _blank()
    s = P["size"]
    body_rx = max(7, int(round(9 * s * P["aspect"])))
    body_ry = max(3, int(round(4 * s)))
    body_cx = CX - 2
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # neck rising up-right from shoulder to the head (clear vertical/diag stack)
    neck_base_x = body_cx + body_rx - 2
    neck_h = max(3, int(round(3 * s)))
    for k in range(0, neck_h):
        xx = neck_base_x + k // 2 + 1
        yy = body_cy - body_ry - k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
        if 0 <= xx + 1 < WP and 0 <= yy < HP:
            g[yy][xx + 1] = ramp["mid"]
    # head — clearly raised above body
    head_r = max(2, int(round(2 * s)))
    head_cx = neck_base_x + neck_h // 2 + 2
    head_cy = body_cy - body_ry - neck_h + 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # bill — long dark rectangle sticking forward-right (unmistakable duck bill)
    bill_len = max(3, int(round(4 * s)))
    for k in range(1, bill_len + 1):
        xx = head_cx + head_r + k
        # upper edge of bill
        if 0 <= xx < WP and 0 <= head_cy < HP:
            g[head_cy][xx] = ramp["outline"]
        # lower edge of bill (thicker at base, tapers)
        if k <= bill_len - 1 and 0 <= xx < WP and 0 <= head_cy + 1 < HP:
            g[head_cy + 1][xx] = ramp["dark"]
    # eye
    if 0 <= head_cx < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx] = ramp["outline"]
    # tail nub off the left-back
    tail_x = body_cx - body_rx
    if 0 <= tail_x < WP and 0 <= body_cy < HP:
        g[body_cy][tail_x] = ramp["dark"]
    # waterline: dashed line at the middle of the body
    waterline_y = body_cy + body_ry - 1
    for x in range(WP):
        if 0 <= waterline_y < HP:
            if x % 3 != 2:
                cur = g[waterline_y][x]
                if cur is None:
                    g[waterline_y][x] = ramp["dark"]
                elif cur in (ramp["mid"], ramp["light"]):
                    g[waterline_y][x] = ramp["outline"]
    return g, body_rx + 2


def form_wading_bird(ramp, P):
    """Long-legged wader — heron / stork / kingfisher-tall variant. Small body high up
    on tall legs, S-curve neck, dagger bill."""
    g = _blank()
    s = P["size"]
    body_rx = max(4, int(round(5 * s)))
    body_ry = max(2, int(round(3 * s)))
    body_cx = CX - 3
    body_cy = CY - 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # neck — S curve rising up from the shoulder
    neck_base_x = body_cx + body_rx - 1
    for i, (dx, dy) in enumerate(((0, -1), (1, -2), (1, -3), (2, -4))):
        xx, yy = neck_base_x + dx, body_cy + dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"] if i == 3 else ramp["dark"]
    # head — small oval at top of neck
    head_cx = neck_base_x + 3
    head_cy = body_cy - 4
    for dy, dx_range in ((0, range(0, 3)), (-1, range(1, 3))):
        for dx in dx_range:
            xx, yy = head_cx + dx, head_cy + dy
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["dark"]
    # dagger bill — long pointy horizontal
    bill_len = max(3, int(round(5 * s)))
    for k in range(1, bill_len + 1):
        xx, yy = head_cx + 3 + k - 1, head_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # eye
    if 0 <= head_cx + 1 < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx + 1] = ramp["outline"]
    # long legs going down to the bottom of the frame
    for dx_off in (-1, 2):
        xx = body_cx + dx_off
        for yy in range(body_cy + body_ry, HP):
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    # tail — short triangle off the back
    for k in range(1, 3):
        xx, yy = body_cx - body_rx - k + 1, body_cy + k - 1
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    return g, body_rx + 3


def form_raptor(ramp, P):
    """Top-down / sky view raptor with broad spread wings. Similar to bat but
    larger, no ears, tail fan visible, no wing-finger struts."""
    g = _blank()
    s = P["size"]
    body_rx = max(2, int(round(2 * s)))
    body_ry = max(4, int(round(6 * s)))
    body_cy = CY
    _fill_ellipse(g, CX, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # broad wings — V-shape / M-shape from the shoulder
    wing_span = max(11, int(round(14 * s)))
    shoulder_y = body_cy - body_ry + 2
    for sign in (-1, 1):
        for step in range(1, wing_span + 1):
            frac = step / wing_span
            xx = CX + sign * (body_rx + step - 1)
            # leading edge tilts back slightly
            upper = int(round(shoulder_y - 3 * (frac ** 0.6)))
            # trailing edge falls behind
            lower = int(round(shoulder_y + 3 - 4 * (frac ** 1.2)))
            for yy in range(upper, lower + 1):
                if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                    if yy == upper or yy == lower:
                        g[yy][xx] = ramp["dark"]
                    else:
                        g[yy][xx] = shade(xx, CX, wing_span + body_rx, ramp)
        # wingtip primaries — 2-3 splayed pixels at the tip
        for k in range(2):
            xx = CX + sign * (body_rx + wing_span + k)
            yy = int(round(shoulder_y - 3 * ((wing_span / wing_span) ** 0.6))) + k
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    # tail fan — trapezoid off the bottom of the body
    tail_top = body_cy + body_ry - 1
    for k in range(1, 4):
        for dx in range(-1 - k // 2, 2 + k // 2):
            xx = CX + dx
            yy = tail_top + k
            if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                is_edge = (dx == -1 - k // 2 or dx == 1 + k // 2 or k == 3)
                g[yy][xx] = ramp["outline"] if is_edge else ramp["dark"]
    # head — small circle above body (leading end)
    head_cy = body_cy - body_ry - 1
    for dx in (-1, 0, 1):
        xx = CX + dx
        if 0 <= xx < WP and 0 <= head_cy < HP:
            g[head_cy][xx] = ramp["outline"] if abs(dx) == 1 else ramp["dark"]
    return g, body_rx + wing_span // 2


def form_gull(ramp, P):
    """Long-winged side-glide gull. Streamlined side-view body + long slender
    wings extended horizontally back-and-sideways. Distinct from raptor (which
    is top-down). Wings taper to a thin sharp tip."""
    g = _blank()
    s = P["size"]
    body_rx = max(5, int(round(7 * s)))
    body_ry = max(2, int(round(3 * s)))
    body_cx = CX - 2
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # wing — long thin ellipse arching up-and-back from the mid-body
    wing_rx = max(9, int(round(12 * s)))
    wing_ry = max(1, int(round(2 * s)))
    wing_cx = body_cx - wing_rx // 3
    wing_cy = body_cy - body_ry
    for y in range(HP):
        for x in range(WP):
            if ((x - wing_cx) / wing_rx) ** 2 + ((y - wing_cy) / wing_ry) ** 2 <= 1.0:
                if g[y][x] is None:
                    dist = ((x - wing_cx) / wing_rx) ** 2 + ((y - wing_cy) / wing_ry) ** 2
                    if dist > 0.75:
                        g[y][x] = ramp["outline"]
                    else:
                        g[y][x] = shade(x, wing_cx, wing_rx, ramp)
    # dark wingtip (primaries) — end of the wing
    tip_x = wing_cx - wing_rx
    for k in range(3):
        xx, yy = tip_x + k, wing_cy
        if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is not None:
            g[yy][xx] = ramp["outline"]
    # head — small circle on the right of the body
    head_r = max(2, int(round(2 * s)))
    head_cx = body_cx + body_rx - 1
    head_cy = body_cy - 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # bill — short dagger
    for k in range(1, 3):
        xx, yy = head_cx + head_r + k, head_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # eye
    if 0 <= head_cx + 1 < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx + 1] = ramp["outline"]
    # tail — thin fork off the back-left
    for k in range(1, 3):
        xx = body_cx - body_rx - k + 1
        yy = body_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    return g, body_rx + wing_rx // 2


def form_mollusc(ramp, P):
    """Mollusc side view. Two modes via --aspect:
        aspect >= 1.0 → SLUG (elongated fleshy body, no shell, two eyestalks up-front)
        aspect <  1.0 → SNAIL (body low + spiral shell visible on the back)"""
    g = _blank()
    s = P["size"]
    seed = P.get("seed", 0)
    if P["aspect"] >= 1.0:
        # SLUG — long fleshy body, tapering back
        body_rx = max(8, int(round(11 * s)))
        body_ry = max(2, int(round(3 * s)))
        body_cx = CX - 1
        body_cy = CY + 2
        _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
        # foot / underside — dark line
        for x in range(body_cx - body_rx, body_cx + body_rx + 1):
            yy = body_cy + body_ry
            if 0 <= x < WP and 0 <= yy < HP:
                g[yy][x] = ramp["outline"]
        # two eyestalks — thin verticals rising up from the head end
        for stalk_dx in (-2, 0):
            xx = body_cx + body_rx - 1 + stalk_dx
            for k in range(1, 4):
                yy = body_cy - body_ry - k
                if 0 <= xx < WP and 0 <= yy < HP:
                    g[yy][xx] = ramp["outline"] if k == 3 else ramp["dark"]
        # mantle groove — small horizontal dark stripe on top
        for x in range(body_cx - body_rx + 2, body_cx + body_rx // 2 + 1):
            yy = body_cy - body_ry + 1
            if 0 <= x < WP and 0 <= yy < HP and g[yy][x] is not None:
                g[yy][x] = ramp["dark"]
        return g, body_rx
    else:
        # SNAIL — foot below + spiral shell above
        foot_rx = max(6, int(round(9 * s)))
        foot_ry = max(2, int(round(2 * s)))
        foot_cx = CX - 1
        foot_cy = CY + 4
        _fill_ellipse(g, foot_cx, foot_cy, foot_rx, foot_ry, ramp, span=foot_rx)
        # foot underline
        for x in range(foot_cx - foot_rx, foot_cx + foot_rx + 1):
            yy = foot_cy + foot_ry
            if 0 <= x < WP and 0 <= yy < HP:
                g[yy][x] = ramp["outline"]
        # spiral shell on top — dome ellipse
        shell_rx = max(5, int(round(7 * s)))
        shell_ry = max(4, int(round(5 * s)))
        shell_cx = foot_cx - 1
        shell_cy = foot_cy - foot_ry - shell_ry + 1
        # draw shell with a spiral swirl inside
        for y in range(HP):
            for x in range(WP):
                if ((x - shell_cx) / shell_rx) ** 2 + ((y - shell_cy) / shell_ry) ** 2 <= 1.0:
                    if g[y][x] is None:
                        # spiral rings — distance-mod-3 gives the swirl look
                        dx = x - shell_cx
                        dy = y - shell_cy
                        d = int(round(math.hypot(dx, dy)))
                        ang = math.atan2(dy, dx)
                        band = (d + int(ang * 2)) % 3
                        if band == 0:
                            g[y][x] = ramp["outline"]
                        else:
                            g[y][x] = shade(x, shell_cx, shell_rx, ramp)
        # eyestalks poking forward off the foot's head end
        head_x = foot_cx + foot_rx - 1
        for stalk_dx in (0, 1):
            xx = head_x + stalk_dx
            for k in range(1, 3):
                yy = foot_cy - k
                if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                    g[yy][xx] = ramp["outline"] if k == 2 else ramp["dark"]
        return g, foot_rx + 2


def form_dragonfly(ramp, P):
    """Top-down dragonfly / damselfly. Long thin abdomen horizontal, 4 wings out
    to the sides (2 forward + 2 back), pair of large compound eyes at the head."""
    g = _blank()
    s = P["size"]
    body_len = max(14, int(round(18 * s)))
    body_x0 = CX - body_len // 2
    body_x1 = body_x0 + body_len
    # abdomen — thin horizontal bar down the middle
    for x in range(body_x0, body_x1 + 1):
        if 0 <= x < WP:
            for dy in (-1, 0, 1):
                yy = CY + dy
                if 0 <= yy < HP:
                    if dy == 0:
                        g[yy][x] = ramp["mid"]
                    else:
                        g[yy][x] = ramp["dark"]
    # abdominal segmentation — small dark ticks every 2 pixels
    for x in range(body_x0 + 3, body_x1 - 2, 2):
        if 0 <= x < WP and 0 <= CY < HP:
            g[CY][x] = ramp["outline"]
    # 2 forewings top-left of centre, 2 forewings top-right — actually 2 wings
    # per side (fore + hind), stacked. Fore is bigger.
    wing_cx = CX + 2
    for wing_sign_x in (-1, 1):
        wc_x = CX + wing_sign_x * 3
        # forewing (upper)
        fw_rx = max(5, int(round(8 * s)))
        fw_ry = max(1, int(round(2 * s)))
        fw_cy = CY - 4
        for y in range(HP):
            for x in range(WP):
                if ((x - wc_x) / fw_rx) ** 2 + ((y - fw_cy) / fw_ry) ** 2 <= 1.0 and g[y][x] is None:
                    d = ((x - wc_x) / fw_rx) ** 2 + ((y - fw_cy) / fw_ry) ** 2
                    g[y][x] = ramp["outline"] if d > 0.75 else ramp["light"]
        # hindwing (lower — slightly narrower)
        hw_rx = max(4, int(round(6 * s)))
        hw_ry = max(1, int(round(2 * s)))
        hw_cx = wc_x + wing_sign_x
        hw_cy = CY + 4
        for y in range(HP):
            for x in range(WP):
                if ((x - hw_cx) / hw_rx) ** 2 + ((y - hw_cy) / hw_ry) ** 2 <= 1.0 and g[y][x] is None:
                    d = ((x - hw_cx) / hw_rx) ** 2 + ((y - hw_cy) / hw_ry) ** 2
                    g[y][x] = ramp["outline"] if d > 0.75 else ramp["light"]
    # head — small block at right end with 2 big eyes
    head_x = body_x1
    for dy in (-1, 0, 1):
        xx, yy = head_x + 1, CY + dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # compound eyes: 2x2 dark blocks either side of the head
    for eye_dy in (-1, 1):
        xx, yy = head_x + 2, CY + eye_dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    return g, body_len // 2


def form_mushroom(ramp, P):
    """Iconic cap-on-stipe mushroom / toadstool. Dome cap on top, straight stipe
    below, dark gill-line under the cap. --accent-hue paints cap spots (amanita
    style) at --accent > 0."""
    g = _blank()
    s = P["size"]
    seed = P.get("seed", 0)
    # cap
    cap_rx = max(6, int(round(9 * s)))
    cap_ry = max(3, int(round(5 * s)))
    cap_cx = CX
    cap_cy = CY - 2
    # draw only the top half (dome)
    for y in range(HP):
        for x in range(WP):
            if y > cap_cy:
                continue
            if ((x - cap_cx) / cap_rx) ** 2 + ((y - cap_cy) / cap_ry) ** 2 <= 1.0:
                g[y][x] = shade(x, cap_cx, cap_rx, ramp)
    # cap rim — dark line along the bottom of the dome
    for x in range(cap_cx - cap_rx, cap_cx + cap_rx + 1):
        if 0 <= x < WP and 0 <= cap_cy < HP and g[cap_cy][x] is not None:
            g[cap_cy][x] = ramp["outline"]
    # gill line — a slightly darker horizontal beneath the cap
    gill_y = cap_cy + 1
    for x in range(cap_cx - cap_rx + 1, cap_cx + cap_rx):
        if 0 <= x < WP and 0 <= gill_y < HP and g[gill_y][x] is None:
            g[gill_y][x] = ramp["dark"]
    # stipe (stem) — vertical column below cap
    stipe_w = max(2, int(round(3 * s)))
    stipe_top = cap_cy + 2
    stipe_bot = HP - 1
    stipe_cx = cap_cx
    for y in range(stipe_top, stipe_bot + 1):
        for dx in range(-stipe_w // 2, stipe_w - stipe_w // 2):
            xx = stipe_cx + dx
            if 0 <= xx < WP and 0 <= y < HP:
                is_edge = (dx == -stipe_w // 2 or dx == stipe_w - stipe_w // 2 - 1)
                g[y][xx] = ramp["outline"] if is_edge else shade(xx, stipe_cx, stipe_w, ramp)
    return g, cap_rx


def form_grasshopper(ramp, P):
    """Side view grasshopper / cricket. Compact torpedo body + huge angled hind
    leg (jumping-ready) — the hind leg is the identity. Long antennae, small head."""
    g = _blank()
    s = P["size"]
    # SMALL body — grasshopper reads via hind leg, not body mass
    body_rx = max(4, int(round(5 * s)))
    body_ry = max(2, int(round(2 * s)))
    body_cx = CX
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head — small oval on the right
    head_r = max(2, int(round(2 * s)))
    head_cx = body_cx + body_rx + 1
    head_cy = body_cy - 1
    _fill_ellipse(g, head_cx, head_cy, head_r, head_r, ramp, span=head_r)
    # big eye
    if 0 <= head_cx + head_r - 1 < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx + head_r - 1] = ramp["outline"]
    # antennae — two long thin lines curving up-forward from the head
    for stalk_dx in (0, 1):
        for k in range(1, max(5, int(round(6 * s))) + 1):
            yy = head_cy - k
            xx = head_cx + head_r - 1 + stalk_dx + k // 3
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    # HIND LEG — dominant Z-shape on the back-left. Thick angled thigh (femur)
    # rising from body's rear.
    femur_len = max(6, int(round(7 * s)))
    fx0 = body_cx - body_rx + 1     # base at back of body
    fy0 = body_cy                    # attaches at body midline
    for k in range(femur_len):
        # goes up-and-back: dx = -k, dy = -k*2//3
        xx = fx0 - k
        yy = fy0 - (k * 2) // 3
        # thick 2-pixel femur
        for dy in (0, 1):
            if 0 <= xx < WP and 0 <= yy + dy < HP:
                g[yy + dy][xx] = ramp["outline"] if dy == 0 else ramp["dark"]
    # knee position
    knee_x = fx0 - (femur_len - 1)
    knee_y = fy0 - ((femur_len - 1) * 2) // 3
    # tibia (shin) — goes down-and-back from knee at steep angle
    tibia_len = max(5, int(round(6 * s)))
    for k in range(1, tibia_len + 1):
        xx = knee_x + k // 2 - 1
        yy = knee_y + k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # 2 small front legs under the body
    foot_y = body_cy + body_ry
    for dx_off in (0, 2):
        xx = body_cx + dx_off
        for k in range(1, 3):
            yy = foot_y + k - 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    return g, body_rx + 3


def form_lagomorph(ramp, P):
    """Rabbit / hare — like the mammal form but with two tall upright ears that
    are the whole identity. Slightly rounder body, upright posture."""
    g = _blank()
    s = P["size"]
    body_rx = max(5, int(round(7 * s)))
    body_ry = max(4, int(round(5 * s)))
    body_cx = CX - 1
    body_cy = CY + 3
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head — smaller oval on top-right
    head_r = max(2, int(round(3 * s)))
    head_cx = body_cx + body_rx - head_r
    head_cy = body_cy - body_ry - 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # TALL EARS — the signature. Two clearly separated upright ears with a
    # gap between them so they don't fuse into a "chef hat".
    ear_h = max(5, int(round(6 * s)))
    # Two ear columns with a 2-pixel gap between their inside edges
    ear_left_x = head_cx - 1
    ear_right_x = head_cx + head_r + 1
    for (ear_x, sign) in ((ear_left_x, -1), (ear_right_x, +1)):
        for k in range(1, ear_h + 1):
            yy = head_cy - head_r - k + 1
            if not (0 <= yy < HP):
                continue
            # 2-column ear: outline column and inner mid column
            outer_x = ear_x
            inner_x = ear_x - sign  # inner column faces the other ear (with gap)
            # tip cap and base cap use outline; middle uses mid inside, outline outer
            if k == 1 or k == ear_h:
                # cap: both cols outline
                if 0 <= outer_x < WP:
                    g[yy][outer_x] = ramp["outline"]
                if 0 <= inner_x < WP:
                    g[yy][inner_x] = ramp["outline"]
            else:
                if 0 <= outer_x < WP:
                    g[yy][outer_x] = ramp["outline"]
                if 0 <= inner_x < WP:
                    g[yy][inner_x] = ramp["mid"]
    # eye + nose
    if 0 <= head_cx + 1 < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + 1] = ramp["outline"]
    if 0 <= head_cx + head_r < WP and 0 <= head_cy + 1 < HP:
        g[head_cy + 1][head_cx + head_r] = ramp["outline"]
    # small legs
    foot_y = body_cy + body_ry
    for dx_off in (-body_rx + 2, body_rx - 3):
        for k in range(1, 3):
            xx, yy = body_cx + dx_off, foot_y + k - 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"] if k == 2 else ramp["dark"]
    # tiny puff tail
    for xx in (body_cx - body_rx, body_cx - body_rx + 1):
        yy = body_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["light"]
    return g, body_rx + 2


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
    "fungus": form_fungus,
    # New forms (2026-06-30) — C3.D.1 sprite library expansion.
    "reptile": form_reptile,
    "fish": form_fish,
    "amphibian": form_amphibian,
    "large-mammal": form_large_mammal,
    "aquatic-mammal": form_aquatic_mammal,
    "water-bird": form_water_bird,
    "wading-bird": form_wading_bird,
    "raptor": form_raptor,
    "gull": form_gull,
    "mollusc": form_mollusc,
    "dragonfly": form_dragonfly,
    "mushroom": form_mushroom,
    "grasshopper": form_grasshopper,
    "lagomorph": form_lagomorph,
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
