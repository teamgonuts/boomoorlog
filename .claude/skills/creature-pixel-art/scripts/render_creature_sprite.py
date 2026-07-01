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
    body_cy = CY + 3

    # ---- abdomen (LEFT) — chunky but NOT huge; roughly matched to thorax ----
    # Earlier version had rx=7, ry=4 which made the abdomen 14 wide vs the
    # 6-wide thorax — read as a bat wing/torso. Trimmed here for balance.
    ab_rx = max(3, int(round(4 * s * P["aspect"])))
    ab_ry = max(2, int(round(3 * s / max(0.6, P["aspect"]))))
    ab_cx = CX - 3
    _fill_ellipse(g, ab_cx, body_cy, ab_rx, ab_ry, ramp, span=ab_rx)
    # horizontal stripes — 2 dark bands across the abdomen
    for stripe_dy in (-1, 1):
        y = body_cy + stripe_dy
        for x in range(WP):
            if 0 <= y < HP and g[y][x] in (ramp["mid"], ramp["dark"], ramp["light"]):
                g[y][x] = ramp["outline"]

    # ---- thorax (MIDDLE — same size as abdomen for a bee proportion) ----
    th_r = max(3, int(round(3 * s)))
    th_cx = ab_cx + ab_rx + 1
    th_cy = body_cy - 1
    _fill_ellipse(g, th_cx, th_cy, th_r, th_r, ramp, span=th_r)

    # ---- head (RIGHT — smaller than thorax) ----
    hd_r = max(2, int(round(2 * s)))
    hd_cx = th_cx + th_r + 1
    hd_cy = th_cy
    _fill_ellipse(g, hd_cx, hd_cy, hd_r, hd_r, ramp, span=hd_r)

    # ---- big black compound eye (2x2 block on the front of the head) ----
    eye_x0 = hd_cx + hd_r - 2
    for dy in range(2):
        for dx in range(2):
            xx, yy = eye_x0 + dx, hd_cy - 1 + dy
            if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is not None:
                g[yy][xx] = ramp["outline"]

    # ---- WING — small pale arched ellipse, only over the THORAX (not the
    # abdomen), so it reads as a bee wing not a bat membrane ----
    wing_rx = max(4, int(round(5 * s)))
    wing_ry = max(2, int(round(3 * s)))
    wing_cx = th_cx - 1
    wing_cy = th_cy - th_r - wing_ry + 3
    for y in range(HP):
        for x in range(WP):
            d = ((x - wing_cx) / wing_rx) ** 2 + ((y - wing_cy) / wing_ry) ** 2
            if d <= 1.0 and y < th_cy - th_r + 1:
                if d >= 0.72:
                    g[y][x] = ramp["dark"]    # wing edge / veins
                else:
                    g[y][x] = ramp["light"]   # pale membrane

    # ---- legs underneath the thorax + abdomen ----
    if P["legs"]:
        for k in (-3, -1, 2):
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
    return g, ab_rx + th_r + hd_r


def form_spider(ramp, P):
    """Top-down spider — small central body + 8 LONG, JOINTED legs. The
    identity is the legs, so the body is deliberately small and the legs
    are drawn with a clear knee bend (out-and-up, then down-and-out to
    a foot dot) so it reads as a spider at a glance and not as a bug.

    Layout per side (4 legs each side):
      leg 1 — steep-up forward   (front pair, splayed forward)
      leg 2 — mid-up forward
      leg 3 — mid-up back
      leg 4 — steep-up back      (back pair, splayed backward)
    """
    g = _blank()
    s = P["size"]
    # Small round body — cephalothorax + abdomen suggested as one blob
    body_r = max(2, int(round(3 * s)))
    _fill_ellipse(g, CX, CY, body_r, body_r, ramp, span=body_r)
    # tiny darker abdomen suggestion in the back half
    for dx in range(-1, 2):
        yy = CY + 1
        xx = CX + dx
        if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is not None:
            g[yy][xx] = ramp["dark"]

    # Eight jointed legs. Each leg has:
    #   shoulder attachment at body edge
    #   femur: 3 pixels going OUT and UP (up = smaller y) to the knee
    #   tibia: 3 pixels going OUT and DOWN back to foot level
    #   foot: dot at the end
    #
    # This makes each leg 6 pixels of visible stroke — much longer than
    # the earlier single-diagonal — with a clear knee bend that reads
    # unambiguously as a spider leg.
    def _draw_leg(shoulder_x, shoulder_y, dx_dir, dy_shoulder,
                  femur_up_steps, knee_dx_offset, tibia_down_steps):
        # Femur: from shoulder, out (dx_dir) and up
        x, y = shoulder_x, shoulder_y + dy_shoulder
        for k in range(1, femur_up_steps + 1):
            x = shoulder_x + dx_dir * k
            # subtle upward angle: y decreases every 2 steps
            y = shoulder_y + dy_shoulder - (k // 2 if femur_up_steps >= 3 else k // 2)
            if 0 <= x < WP and 0 <= y < HP and g[y][x] is None:
                g[y][x] = ramp["dark"] if k == 1 else ramp["outline"]
        knee_x, knee_y = x + dx_dir * knee_dx_offset, y
        # Tibia: from knee, out further and back down
        for k in range(1, tibia_down_steps + 1):
            tx = knee_x + dx_dir * k
            ty = knee_y + k // 2
            if 0 <= tx < WP and 0 <= ty < HP and g[ty][tx] is None:
                g[ty][tx] = ramp["outline"]
            # foot dot at the end
            if k == tibia_down_steps and 0 <= tx < WP and 0 <= ty + 1 < HP:
                g[ty + 1][tx] = ramp["outline"]

    # 4 legs per side. Vary shoulder y and femur length so the legs fan
    # out at different angles and don't overlap.
    left_shoulder = CX - body_r
    right_shoulder = CX + body_r
    # Params tuned for 32x24 grid at size=1.0
    # (shoulder_dy, femur_len, knee_offset, tibia_len)
    leg_specs = [
        (-1, 3, 1, 3),   # front-most (most forward-up)
        (0,  3, 1, 3),   # mid-front
        (0,  3, 1, 3),   # mid-back
        (1,  3, 1, 3),   # back-most
    ]
    # LEFT legs (dx_dir = -1)
    for i, (dy_sh, femur, knee_off, tibia) in enumerate(leg_specs):
        # slight y-offset per leg so they don't stack
        y_off = dy_sh + (i - 1)
        _draw_leg(left_shoulder, CY, -1, y_off, femur, knee_off, tibia)
    # RIGHT legs (dx_dir = +1)
    for i, (dy_sh, femur, knee_off, tibia) in enumerate(leg_specs):
        y_off = dy_sh + (i - 1)
        _draw_leg(right_shoulder, CY, +1, y_off, femur, knee_off, tibia)
    return g, body_r + 8


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
    """Right-side-up top-down view of a lichen / crust / bracket-cluster patch.
    Both modes read as an irregular lobed growth seen from above (as it will
    appear on the map) — no sideways trunk anchor.

    Two modes via --aspect:
      aspect >= 1.0 → BRACKET / SHELF cluster (thicker, more solid dome
                       with a subtle "growth ring" arc across the middle).
      aspect <  1.0 → LICHEN / CRUST (thin lobed patch with speckled
                       texture and small holes to suggest crustose growth).
    """
    g = _blank()
    s = P["size"]
    seed = P["seed"]
    rx = max(7, int(round(10 * s)))
    ry = max(5, int(round(7 * s)))
    if P["aspect"] >= 1.0:
        # BRACKET / SHELF cluster — right-side-up, thicker, more lobed at
        # edges. Drawn as a lobed dome oval centred vertically.
        for y in range(HP):
            for x in range(WP):
                dx, dy = x - CX, y - CY
                ang = math.atan2(dy, dx)
                wobble = 0.85 + 0.14 * math.sin(ang * 3 + seed)
                if (dx / rx) ** 2 + (dy / ry) ** 2 <= wobble:
                    g[y][x] = shade(x, CX, rx, ramp)
        # subtle growth-ring arc across the middle (a slightly darker
        # concentric line)
        ring_r = max(3, int(round(5 * s)))
        for y in range(HP):
            for x in range(WP):
                dx, dy = x - CX, y - CY
                if g[y][x] is None:
                    continue
                d = math.hypot(dx, dy)
                if abs(d - ring_r) < 0.6:
                    g[y][x] = ramp["dark"]
        # a few darker speckles
        for y in range(HP):
            for x in range(WP):
                if g[y][x] in (ramp["mid"], ramp["dark"]):
                    if _hash(x, y, seed + 23) < 0.05:
                        g[y][x] = ramp["light"]
    else:
        # LICHEN / CRUST — right-side-up irregular lobed patch, more
        # wobble around the edge, plus internal texture holes/spots.
        for y in range(HP):
            for x in range(WP):
                dx, dy = x - CX, y - CY
                ang = math.atan2(dy, dx)
                wobble = 0.78 + 0.30 * math.sin(ang * 4 + seed)
                if (dx / rx) ** 2 + (dy / ry) ** 2 <= wobble:
                    g[y][x] = shade(x, CX, rx, ramp)
        # crusty texture — darker specks + small holes
        for y in range(HP):
            for x in range(WP):
                if g[y][x] is None:
                    continue
                if _hash(x, y, seed + 91) < 0.10:
                    g[y][x] = ramp["dark"]
                elif _hash(x, y, seed + 137) < 0.04:
                    g[y][x] = None  # tiny holes suggesting crustose lichen
    return g, rx


def form_reptile(ramp, P):
    """Reptile view. Two modes via --aspect:
        aspect >= 1.0 → LIZARD (top-down: elongated body, 4 splayed legs, long tail).
        aspect <  1.0 → TURTLE (top-down: shell dome in contrasting shell colour,
                                 tiny head + 4 legs poking out from under the shell)."""
    g = _blank()
    s = P["size"]
    if P["aspect"] >= 1.0:
        # TOP-DOWN LIZARD — reads as a lizard with 4 splayed legs.
        # Slim body running left→right, head right, tail tapering left.
        body_rx = max(5, int(round(7 * s)))
        body_ry = max(1, int(round(2 * s)))    # slim body
        body_cx = CX - 2
        body_cy = CY + 2
        _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
        # head — pointed oval on the right
        head_rx = max(2, int(round(3 * s)))
        head_ry = max(2, int(round(2 * s)))
        head_cx = body_cx + body_rx + 1
        head_cy = body_cy
        _fill_ellipse(g, head_cx, head_cy, head_rx, head_ry, ramp, span=head_rx)
        # eyes — 2 small dots (top-down)
        for dx in (-1, +1):
            if 0 <= head_cx + dx < WP and 0 <= head_cy - 1 < HP:
                g[head_cy - 1][head_cx + dx] = ramp["outline"]
        # LONG tail — thin taper off the LEFT
        for k in range(1, max(7, int(round(10 * s))) + 1):
            xx = body_cx - body_rx - k + 1
            yy = body_cy + (k // 6)   # slight downward curve
            if 0 <= xx < WP and 0 <= yy < HP:
                if k < 3:
                    g[yy][xx] = ramp["dark"]
                elif k < 6:
                    g[yy][xx] = ramp["outline"]
                else:
                    # taper to a single pixel
                    g[yy][xx] = ramp["outline"]
        # 4 SPLAYED LEGS — front pair (near head) angled forward-out,
        # back pair (near tail) angled backward-out. Each leg is 3px:
        # a shoulder (dark) + 2px limb (outline) that goes diagonally
        # away from the body.
        # Front pair shoulders sit at body_cx + body_rx // 2
        # Back pair shoulders sit at body_cx - body_rx // 2
        shoulder_dx = body_rx // 2
        for (sh_dx, dx_dir) in ((+shoulder_dx, +1), (-shoulder_dx, -1)):
            sh_x = body_cx + sh_dx
            # upper leg (above body midline)
            for k in range(1, 3):
                lx = sh_x + dx_dir * k
                ly = body_cy - body_ry - k
                if 0 <= lx < WP and 0 <= ly < HP:
                    g[ly][lx] = ramp["outline"] if k == 2 else ramp["dark"]
            # foot dot (upper)
            fx = sh_x + dx_dir * 3
            fy = body_cy - body_ry - 3
            if 0 <= fx < WP and 0 <= fy < HP:
                g[fy][fx] = ramp["outline"]
            # lower leg (below body midline)
            for k in range(1, 3):
                lx = sh_x + dx_dir * k
                ly = body_cy + body_ry + k
                if 0 <= lx < WP and 0 <= ly < HP:
                    g[ly][lx] = ramp["outline"] if k == 2 else ramp["dark"]
            # foot dot (lower)
            fx = sh_x + dx_dir * 3
            fy = body_cy + body_ry + 3
            if 0 <= fx < WP and 0 <= fy < HP:
                g[fy][fx] = ramp["outline"]
        return g, body_rx + 4
    else:
        # TOP-DOWN TURTLE — round shell dome in a CONTRASTING colour so the
        # shell reads as distinct from the body. Head + 4 legs peek out.
        shell_r = max(6, int(round(8 * s)))
        cx = CX - 1
        cy = CY + 1
        # Build a shell ramp: shift the hue significantly for contrast
        # (body hue → shell hue). Turtle bodies are usually greenish/olive
        # with a browner shell, so offset hue by +40° (toward orange/brown)
        # and desaturate a bit.
        hue = P.get("hue", 90)
        sat = P.get("sat", 55)
        shell_ramp = build_ramp((hue + 40) % 360, max(35, sat - 10))
        # BODY (visible under the shell) — small oval underneath
        body_rx = shell_r + 1
        body_ry = shell_r // 2
        _fill_ellipse(g, cx, cy + 1, body_rx, body_ry, ramp, span=body_rx)
        # 4 legs poking out at the diagonals — drawn as 2x2 blocks so they
        # visibly stick out from under the shell (was: 1-pixel nubs, too subtle)
        for (dx_off, dy_off) in ((-shell_r, +1), (+shell_r, +1),
                                  (-shell_r + 1, -2), (+shell_r - 1, -2)):
            lx = cx + dx_off
            ly = cy + dy_off
            sign = 1 if dx_off > 0 else -1
            # 2-pixel-wide leg extending out
            for k in range(0, 3):
                xx = lx + sign * k
                for dy in (0, 1):
                    yy = ly + dy
                    if 0 <= xx < WP and 0 <= yy < HP:
                        if k == 2 or dy == 1:
                            g[yy][xx] = ramp["outline"]
                        else:
                            g[yy][xx] = ramp["dark"]
        # HEAD — poking out on the right
        head_cx = cx + shell_r
        head_cy = cy
        for dx in (0, 1, 2):
            xx = head_cx + dx
            if 0 <= xx < WP and 0 <= head_cy < HP:
                g[head_cy][xx] = ramp["mid"] if dx == 0 else ramp["dark"]
        # eye
        if 0 <= head_cx + 2 < WP and 0 <= head_cy - 1 < HP:
            g[head_cy - 1][head_cx + 2] = ramp["outline"]
        # TAIL nub on the left
        if 0 <= cx - shell_r - 1 < WP and 0 <= cy < HP:
            g[cy][cx - shell_r - 1] = ramp["outline"]
        # SHELL — round dome in shell_ramp colours, overwrites body top
        for y in range(HP):
            for x in range(WP):
                dist2 = ((x - cx) / shell_r) ** 2 + ((y - cy) / shell_r) ** 2
                if dist2 <= 1.0:
                    if dist2 > 0.75:
                        g[y][x] = shell_ramp["outline"]
                    else:
                        g[y][x] = shade(x, cx, shell_r, shell_ramp)
        # SCUTE PATTERN — hexagonal-ish plates on the shell
        # Draw 5-6 dark spots to suggest scutes
        seed = P.get("seed", 0)
        scute_positions = [
            (0, -1), (-2, 0), (+2, 0), (0, +1), (-3, -2), (+3, -2),
        ]
        for (sdx, sdy) in scute_positions:
            sx = cx + sdx
            sy = cy + sdy
            if 0 <= sx < WP and 0 <= sy < HP and g[sy][sx] is not None:
                g[sy][sx] = shell_ramp["outline"]
        # highlight on the shell's upper-left (left-lit consistency)
        hi_x = cx - shell_r // 2
        hi_y = cy - shell_r // 2
        if 0 <= hi_x < WP and 0 <= hi_y < HP and g[hi_y][hi_x] is not None:
            g[hi_y][hi_x] = shell_ramp["light"]
        return g, shell_r + 2


def form_fish(ramp, P):
    """Side-view fusiform fish — body ellipse, tail fin left, dorsal fin top, eye + gill."""
    g = _blank()
    s = P["size"]
    # Cap body width so the tail fin doesn't get clipped off the left edge.
    # Was: body_rx = 10 * s * aspect  → with aspect=1.2 → 12, then tail_len=5,
    # meaning left tail tip lands at x=-2 (off frame). Now:
    body_rx = max(6, min(9, int(round(8 * s * P["aspect"]))))
    body_ry = max(3, int(round(4 * s / max(0.7, P["aspect"]))))
    tail_len = max(3, int(round(5 * s)))
    # Center body so BOTH the tail (left) and the head+eye (right) fit.
    # Left edge = body_cx - body_rx - tail_len must be >= 1.
    body_cx = max(body_rx + tail_len + 1, CX + 1)
    body_cy = CY + 1
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # tail fin — triangle on the left, closed with an outline at the tip
    tail_root_x = body_cx - body_rx
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
    # CLOSE THE TAIL — draw a hard dark outline along the leftmost tail
    # column so the fin ends in a distinct closing edge, not a fade-out.
    tail_tip_x = tail_root_x - tail_len
    tip_height = tail_len * 2 - (tail_len - 1)   # ≈ tail_len + 1
    for dy in range(-tip_height, tip_height + 1):
        yy = body_cy + dy
        if 0 <= tail_tip_x < WP and 0 <= yy < HP and g[yy][tail_tip_x] is not None:
            g[yy][tail_tip_x] = ramp["outline"]
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
    """Frog / toad / newt side-view. Body proportions vary by --aspect
    so a single form covers the whole class:
      aspect >= 1.15 → newt / salamander (elongated body + visible tail)
      0.85 < aspect < 1.15 → regular frog (medium round body, no tail)
      aspect <= 0.85 → toad / bufo (FAT round body — chunky and squat)
    """
    g = _blank()
    s = P["size"]
    a = P["aspect"]
    is_newt = a >= 1.15
    is_toad = a <= 0.85
    # Toad: fatter body. Newt: slimmer, longer body. Frog: medium.
    if is_toad:
        body_rx = max(7, int(round(9 * s)))
        body_ry = max(5, int(round(6 * s)))     # extra vertical bulk
    elif is_newt:
        body_rx = max(8, int(round(10 * s)))    # elongated
        body_ry = max(2, int(round(3 * s)))
    else:
        body_rx = max(6, int(round(8 * s)))
        body_ry = max(4, int(round(5 * s)))
    body_cx = CX
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # NEWT tail — thin taper off the LEFT (only for aspect >= 1.15)
    if is_newt:
        for k in range(1, max(5, int(round(7 * s))) + 1):
            xx = body_cx - body_rx - k + 1
            yy = body_cy + (k // 4)
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["dark"] if k < 3 else ramp["outline"]
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
    """Side-view large mammal — deer / boar / fox / badger. Three sub-modes
    keyed off --aspect so a single form covers the whole family without
    every species looking identical:

      aspect >= 1.15 → TALL (deer, boar, roe). Body high off ground, long
                       legs. Boar can bulk up further via --size.
      0.75 < aspect < 1.15 → MID (fox / canid). Medium legs, BUSHY
                       trailing tail (tail=bushy triggers), pointier snout.
      aspect <= 0.75 → LOW (badger / mustelid). Body sits LOW to the
                       ground, short legs, thick body. `--tail=none` +
                       head-stripe is drawn if P["head_stripe"] is set.
    """
    g = _blank()
    s = P["size"]
    a = P["aspect"]

    # Pick proportion tuning per sub-mode
    if a >= 1.15:
        mode = "tall"
        body_rx = max(7, int(round(9 * s)))
        body_ry = max(2, int(round(3 * s)))
        body_cy = CY - 2
        leg_style = "long"           # from body underside to HP-1
    elif a <= 0.75:
        mode = "low"
        body_rx = max(7, int(round(9 * s)))
        body_ry = max(3, int(round(4 * s)))   # thicker
        body_cy = CY + 2                       # body sits LOW
        leg_style = "short"
    else:
        mode = "mid"
        body_rx = max(6, int(round(8 * s)))
        body_ry = max(2, int(round(3 * s)))
        body_cy = CY
        leg_style = "medium"

    body_cx = CX - 3
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)

    # Neck rising up-right from the shoulder
    neck_base_x = body_cx + body_rx - 2
    neck_len = 4 if mode == "tall" else (3 if mode == "mid" else 2)
    for k in range(0, neck_len):
        xx = neck_base_x + (k // 2)
        yy = body_cy - body_ry - k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"] if k < neck_len - 1 else ramp["outline"]
        if k >= 1 and 0 <= xx + 1 < WP and 0 <= yy < HP:
            g[yy][xx + 1] = ramp["mid"]

    # Head — oval at top of neck
    head_r = max(2, int(round(2 * s)))
    head_cx = neck_base_x + (neck_len // 2) + head_r
    head_cy = body_cy - body_ry - neck_len + 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)

    # Upright ears (2 nubs on top of head)
    for sign in (-1, 1):
        xx = head_cx + sign
        yy = head_cy - head_r - 1
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
        if 0 <= xx < WP and 0 <= yy + 1 < HP and g[yy + 1][xx] is None:
            g[yy + 1][xx] = ramp["dark"]

    # Snout — for fox (mid) draw longer/pointier; for badger (low) short
    snout_len = 2 if mode == "mid" else 1
    for k in range(1, snout_len + 1):
        snout_x = head_cx + head_r + k
        if 0 <= snout_x < WP and 0 <= head_cy + 1 < HP:
            g[head_cy + 1][snout_x] = ramp["outline"]

    # Eye
    if 0 <= head_cx + 1 < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + 1] = ramp["outline"]

    # BADGER HEAD STRIPE — one dark vertical line from crown down through
    # snout, drawn if P.get("head_stripe") is truthy. Uses shell-ramp-style
    # dark accent (build a stripe ramp with same hue but very dark + very light).
    if P.get("head_stripe"):
        stripe_ramp = build_ramp(P.get("hue", 25), 5)  # near-grey ramp
        # Draw a white/light stripe down the forehead + a dark stripe on
        # each side. This is the signature badger face.
        for dy in (-1, 0, 1):
            sy = head_cy + dy
            sx = head_cx + 1
            if 0 <= sx < WP and 0 <= sy < HP:
                g[sy][sx] = stripe_ramp["light"]
        # dark side stripes
        for dy in (0, 1):
            sy = head_cy + dy
            for sx in (head_cx, head_cx + 2):
                if 0 <= sx < WP and 0 <= sy < HP:
                    g[sy][sx] = stripe_ramp["outline"]

    # LEGS — number, height, spread depend on sub-mode
    if leg_style == "long":
        leg_top_y = body_cy + body_ry
        leg_bot_y = HP - 1
    elif leg_style == "medium":
        leg_top_y = body_cy + body_ry
        leg_bot_y = HP - 2
    else:  # short (badger)
        leg_top_y = body_cy + body_ry
        leg_bot_y = min(HP - 1, leg_top_y + 3)

    leg_positions = [
        body_cx - body_rx + 2,   # back-left
        body_cx - body_rx + 4,   # back-right
        body_cx + body_rx - 4,   # front-left
        body_cx + body_rx - 2,   # front-right
    ]
    for xx in leg_positions:
        for yy in range(leg_top_y, leg_bot_y + 1):
            if 0 <= xx < WP and 0 <= yy < HP:
                if yy == leg_bot_y:
                    g[yy][xx] = ramp["outline"]
                elif yy == leg_top_y:
                    g[yy][xx] = ramp["dark"]
                else:
                    g[yy][xx] = ramp["outline"]

    # TAIL — style depends on P["tail"]
    tail_style = P.get("tail", "thin")
    tail_root_x = body_cx - body_rx
    tail_root_y = body_cy
    if tail_style == "bushy":
        # Big drooping bushy tail — fox style. Sits behind and hangs low.
        for k in range(0, 6):
            for dy in range(-1, 2):
                xx = tail_root_x - k - (1 if k > 2 else 0)
                yy = tail_root_y + k + dy
                if 0 <= xx < WP and 0 <= yy < HP and g[yy][xx] is None:
                    if dy == -1 or dy == 1 or k == 5:
                        g[yy][xx] = ramp["outline"]
                    else:
                        g[yy][xx] = ramp["dark"]
    elif tail_style == "none":
        pass  # badger — no tail nub
    else:
        # Thin short nub — deer / boar
        if 0 <= tail_root_x < WP and 0 <= tail_root_y < HP:
            g[tail_root_y][tail_root_x] = ramp["outline"]
        if 0 <= tail_root_x - 1 < WP and 0 <= tail_root_y + 1 < HP:
            g[tail_root_y + 1][tail_root_x - 1] = ramp["outline"]

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
    # head — round oval that clears the body's right edge with a short neck.
    # Otter head has a very readable rounded silhouette lifted above the water.
    head_r = max(3, int(round(3 * s)))
    head_cx = body_cx + body_rx + 1     # sits just past body's right edge
    head_cy = body_cy - 2                # lifted above the waterline
    _fill_ellipse(g, head_cx, head_cy, head_r, head_r, ramp, span=head_r)
    # neck bridge — 1px diagonal joining body shoulder to head
    for k in range(1, 3):
        xx = body_cx + body_rx - k
        yy = body_cy - k
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["dark"]
    # tiny round ears on top of head
    for sign in (-1, 1):
        xx = head_cx + sign
        yy = head_cy - head_r
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # snout / nose — dark 2px poking to the right
    for k in range(1, 3):
        xx = head_cx + head_r + k - 1
        if 0 <= xx < WP and 0 <= head_cy + 1 < HP:
            g[head_cy + 1][xx] = ramp["outline"]
    # eye
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
    # NOTE: no waterline is drawn — the map basemap already renders water.
    # This keeps the sprite transparent below the belly so it composites
    # onto real canals cleanly.
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
    # NOTE: no waterline is drawn — the map basemap already renders water
    # under the duck. The bottom of the body is the natural waterline.
    return g, body_rx + 2


def form_wading_bird(ramp, P):
    """Long-legged wader — heron / stork / spoonbill / egret / lapwing.
    The identity is TALL STILT LEGS + high S-curve neck. Body is deliberately
    small and sits high up so ~half the total silhouette height is leg.
    """
    g = _blank()
    s = P["size"]
    # SMALL body, sitting HIGH so tall legs read
    body_rx = max(3, int(round(4 * s)))
    body_ry = max(2, int(round(2 * s)))
    body_cx = CX - 3
    body_cy = CY - 3                    # body lifted high (was CY-1)
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)

    # S-CURVE NECK rising up-and-forward from the shoulder
    neck_base_x = body_cx + body_rx - 1
    for i, (dx, dy) in enumerate(((0, -1), (1, -2), (2, -3), (2, -4), (3, -5))):
        xx, yy = neck_base_x + dx, body_cy + dy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"] if i >= 3 else ramp["dark"]

    # Small round HEAD at top of neck
    head_cx = neck_base_x + 4
    head_cy = body_cy - 5
    for dy, dx_range in ((0, range(-1, 2)), (-1, range(0, 2))):
        for dx in dx_range:
            xx, yy = head_cx + dx, head_cy + dy
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["dark"]
    # DAGGER BILL — long pointy horizontal off the head
    bill_len = max(3, int(round(4 * s)))
    for k in range(1, bill_len + 1):
        xx, yy = head_cx + 2 + k, head_cy
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"]
    # Eye
    if 0 <= head_cx < WP and 0 <= head_cy - 1 < HP:
        g[head_cy - 1][head_cx] = ramp["outline"]

    # TALL STILT LEGS — go from body underside all the way to the bottom.
    # With body_cy=CY-3=9 and body_ry=2, body underside is y=11. Legs
    # extend to y=23, so ~12 px of visible leg — well over half the total
    # silhouette. 5px gap so they read as two distinct stilts.
    for dx_off in (-2, 3):
        xx = body_cx + dx_off
        for yy in range(body_cy + body_ry, HP):
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    # Small feet — 3 pixels wide at the bottom
    for dx_off in (-2, 3):
        for foot_dx in (-1, 0, 1):
            xx = body_cx + dx_off + foot_dx
            if 0 <= xx < WP and 0 <= HP - 1 < HP:
                g[HP - 1][xx] = ramp["outline"]
    # Optional visible "knee" halfway down the leg — a small mid-tone
    # pixel that makes the leg read as jointed rather than a plain stroke
    knee_y = body_cy + body_ry + (HP - 1 - body_cy - body_ry) // 2
    for dx_off in (-2, 3):
        xx = body_cx + dx_off
        if 0 <= xx < WP and 0 <= knee_y < HP:
            g[knee_y][xx] = ramp["dark"]

    # Short tail nub off the back
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
    """Iconic gull silhouette in flight — the classic "M-shape" spread wings
    seen from below/front. Drawn as: two upward-angled wing arms sweeping
    out from a small central body, with dark wingtip primaries.

    This reads as a gull at a glance in a way that a side profile does not
    — the M-shape is the universal shorthand.
    """
    g = _blank()
    s = P["size"]

    # Central body — short horizontal oval
    body_rx = max(2, int(round(2 * s)))
    body_ry = max(1, int(round(2 * s)))
    body_cx = CX
    body_cy = CY + 2
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)

    # HEAD — small oval above the body, slightly forward
    head_r = max(1, int(round(2 * s)))
    head_cx = body_cx
    head_cy = body_cy - body_ry - 1
    _fill_ellipse(g, head_cx, head_cy, head_r, head_r, ramp, span=head_r)
    # small bill
    if 0 <= head_cx + head_r < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + head_r] = ramp["outline"]

    # WINGS — two arms sweeping OUT and UP from the shoulders, forming an
    # M. Each wing is a 2-row thick stroke going out-and-up, then bending
    # back-and-down near the tip so the silhouette droops a bit at the
    # wingtip (classic soaring gull).
    wing_span = max(10, int(round(12 * s)))
    shoulder_y = body_cy - body_ry + 1
    for sign in (-1, +1):
        for k in range(wing_span):
            # sweep out from shoulder
            t = k / max(1, wing_span - 1)
            xx = body_cx + sign * (body_rx + k)
            # up then back down — parabolic
            yy_offset = int(round(2.5 * s * (4 * t * (1 - t)) - 3 * s * t))
            yy = shoulder_y + yy_offset
            for dy in (0, 1):
                yy2 = yy + dy
                if 0 <= xx < WP and 0 <= yy2 < HP:
                    if dy == 0:
                        g[yy2][xx] = ramp["outline"]
                    else:
                        if g[yy2][xx] is None:
                            g[yy2][xx] = ramp["dark"]
        # dark wingtip — final 2 pixels of the wing
        for k in range(wing_span - 2, wing_span):
            t = k / max(1, wing_span - 1)
            xx = body_cx + sign * (body_rx + k)
            yy_offset = int(round(2.5 * s * (4 * t * (1 - t)) - 3 * s * t))
            yy = shoulder_y + yy_offset
            for dy in (0, 1):
                yy2 = yy + dy
                if 0 <= xx < WP and 0 <= yy2 < HP:
                    g[yy2][xx] = ramp["outline"]

    # short tail nub below the body
    if 0 <= body_cx < WP and 0 <= body_cy + body_ry + 1 < HP:
        g[body_cy + body_ry + 1][body_cx] = ramp["outline"]
    return g, wing_span + body_rx


def form_mollusc(ramp, P):
    """Mollusc side view. Two modes via --aspect:
        aspect >= 1.0 → SLUG (elongated fleshy body, no shell, two tall eyestalks
                              with eye-dot tips).
        aspect <  1.0 → SNAIL (small foot + big spiral shell in a CONTRASTING
                                colour, two tall eyestalks with eye-dot tips)."""
    g = _blank()
    s = P["size"]
    seed = P.get("seed", 0)
    # Signature snail/slug feature: tall eyestalks with dark eye-dot tips.
    # Draw as 4-pixel-tall thin verticals with a "bulb" on top so they read
    # as antennae/eyestalks and not just noise.
    def _draw_eyestalks(head_x, head_y, count=2, gap=3, height=4):
        for i in range(count):
            sx = head_x - i * gap
            # stalk
            for k in range(1, height):
                yy = head_y - k
                if 0 <= sx < WP and 0 <= yy < HP:
                    g[yy][sx] = ramp["dark"]
            # eye-dot (bulb tip)
            tip_y = head_y - height
            if 0 <= sx < WP and 0 <= tip_y < HP:
                g[tip_y][sx] = ramp["outline"]
            # left and right of the tip to make it a small bulb
            if 0 <= sx - 1 < WP and 0 <= tip_y < HP:
                g[tip_y][sx - 1] = ramp["outline"]
            if 0 <= sx + 1 < WP and 0 <= tip_y < HP:
                g[tip_y][sx + 1] = ramp["outline"]

    if P["aspect"] >= 1.0:
        # SLUG — long fleshy body, no shell. Head is to the RIGHT with the
        # eyestalks rising off it.
        body_rx = max(8, int(round(10 * s)))
        body_ry = max(2, int(round(3 * s)))
        body_cx = CX - 2
        body_cy = CY + 3
        _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
        # foot / underside — dark line
        for x in range(body_cx - body_rx, body_cx + body_rx + 1):
            yy = body_cy + body_ry
            if 0 <= x < WP and 0 <= yy < HP:
                g[yy][x] = ramp["outline"]
        # head end (right) — 2 tall eyestalks
        head_x = body_cx + body_rx - 1
        head_y = body_cy - body_ry
        _draw_eyestalks(head_x, head_y, count=2, gap=3, height=4)
        # mantle groove — subtle dark stripe on top of body
        for x in range(body_cx - body_rx + 2, body_cx + body_rx - 2):
            yy = body_cy - body_ry + 1
            if 0 <= x < WP and 0 <= yy < HP and g[yy][x] == ramp["mid"]:
                g[yy][x] = ramp["dark"]
        return g, body_rx
    else:
        # SNAIL — small foot below + big spiral shell above in CONTRASTING
        # colour so the shell reads as a distinct object.
        hue = P.get("hue", 25)
        sat = P.get("sat", 55)
        # Shell hue offset by +30° for contrast (browner shell vs body).
        shell_ramp = build_ramp((hue + 35) % 360, min(80, sat + 15))

        # Foot (body) — small, sits under the shell, projects forward-right
        foot_rx = max(6, int(round(8 * s)))
        foot_ry = max(2, int(round(2 * s)))
        foot_cx = CX
        foot_cy = CY + 5
        _fill_ellipse(g, foot_cx, foot_cy, foot_rx, foot_ry, ramp, span=foot_rx)
        # foot underline
        for x in range(foot_cx - foot_rx, foot_cx + foot_rx + 1):
            yy = foot_cy + foot_ry
            if 0 <= x < WP and 0 <= yy < HP:
                g[yy][x] = ramp["outline"]

        # SHELL — round dome above the foot, in shell_ramp colour. Spiral
        # swirl pattern inside.
        shell_r = max(5, int(round(6 * s)))
        shell_cx = foot_cx - 2
        shell_cy = foot_cy - foot_ry - shell_r + 2
        for y in range(HP):
            for x in range(WP):
                dist2 = ((x - shell_cx) / shell_r) ** 2 + ((y - shell_cy) / shell_r) ** 2
                if dist2 <= 1.0:
                    if dist2 > 0.75:
                        g[y][x] = shell_ramp["outline"]
                    else:
                        # spiral rings
                        dx = x - shell_cx
                        dy = y - shell_cy
                        d = int(round(math.hypot(dx, dy)))
                        ang = math.atan2(dy, dx)
                        band = (d + int(ang * 2)) % 3
                        if band == 0:
                            g[y][x] = shell_ramp["dark"]
                        else:
                            g[y][x] = shade(x, shell_cx, shell_r, shell_ramp)
        # Central swirl highlight — a small light-colored dot at the shell
        # center to sell the spiral read
        if 0 <= shell_cx < WP and 0 <= shell_cy < HP:
            g[shell_cy][shell_cx] = shell_ramp["light"]

        # Head end (right of the foot) — 2 tall eyestalks projecting forward-up
        head_x = foot_cx + foot_rx - 1
        head_y = foot_cy - foot_ry - 1
        _draw_eyestalks(head_x, head_y, count=2, gap=3, height=4)
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


def form_rodent(ramp, P):
    """Side-view small rodent — mouse / rat / vole. Distinct from `mammal`
    (squirrel-style) because the tail is LONG, THIN, and NON-BUSHY — the
    classic rat/mouse tail is the identity. Also has visibly big ears
    (mice + rats have prominent round ears vs. squirrel's tufted ones).
    """
    g = _blank()
    s = P["size"]
    # SMALL body — smaller than the squirrel-style `mammal` form
    body_rx = max(4, int(round(5 * s)))
    body_ry = max(2, int(round(3 * s)))
    body_cx = CX - 3
    body_cy = CY + 3
    _fill_ellipse(g, body_cx, body_cy, body_rx, body_ry, ramp, span=body_rx)
    # head — small oval on the right, slightly lifted
    head_r = max(2, int(round(2 * s)))
    head_cx = body_cx + body_rx
    head_cy = body_cy - 1
    _fill_ellipse(g, head_cx, head_cy, head_r + 1, head_r, ramp, span=head_r)
    # BIG ROUND EARS — mice + rats have very visible round ears
    for sign in (-1, +1):
        ear_x = head_cx + sign
        ear_y = head_cy - head_r
        if 0 <= ear_x < WP and 0 <= ear_y < HP:
            g[ear_y][ear_x] = ramp["outline"]
        # ear top pixel
        if 0 <= ear_x < WP and 0 <= ear_y - 1 < HP:
            g[ear_y - 1][ear_x] = ramp["dark"]
    # eye
    if 0 <= head_cx + 1 < WP and 0 <= head_cy < HP:
        g[head_cy][head_cx + 1] = ramp["outline"]
    # nose (small dot forward of head)
    if 0 <= head_cx + head_r + 1 < WP and 0 <= head_cy + 1 < HP:
        g[head_cy + 1][head_cx + head_r + 1] = ramp["outline"]
    # 2 short legs underneath
    foot_y = body_cy + body_ry
    for dx_off in (-body_rx + 2, body_rx - 3):
        for k in range(1, 2):
            xx, yy = body_cx + dx_off, foot_y + k - 1
            if 0 <= xx < WP and 0 <= yy < HP:
                g[yy][xx] = ramp["outline"]
    # LONG THIN NON-BUSHY TAIL — the identity. Trails off the back-left,
    # curves slightly, drawn as a single-pixel stroke to convey "thin".
    tail_len = max(9, int(round(12 * s)))
    for k in range(1, tail_len + 1):
        # subtle curl: goes back-left, drooping down slightly, then curving up
        xx = body_cx - body_rx - k + 1
        # parabolic droop
        t = k / tail_len
        yy = body_cy + int(round(3 * s * (2 * t - t * t))) - 1
        if 0 <= xx < WP and 0 <= yy < HP:
            g[yy][xx] = ramp["outline"] if k > 2 else ramp["dark"]
    return g, body_rx + 3


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
    # New forms (2026-07-01) — C3.D.1 feedback batch 2
    "rodent": form_rodent,
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
    # Expose hue/sat so form functions can build a secondary ramp
    # (e.g. turtle shell, snail shell) with a contrasting hue.
    P = {**P, "hue": hue, "sat": sat}
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
    ap.add_argument("--head-stripe", action="store_true", default=False,
                    help="badger-style black+white head stripe (large-mammal low mode)")
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
        "size":        a.size,
        "aspect":      a.aspect,
        "legs":        a.legs,
        "antennae":    a.antennae,
        "bristles":    a.bristles,
        "tail":        a.tail,
        "head_stripe": a.head_stripe,
        "seed":        a.seed,
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
