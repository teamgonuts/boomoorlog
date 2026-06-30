#!/usr/bin/env python3
"""Pixel-art sprite experiments for Boomoorlog (test character).

Produces several distinct pixel-art renditions of one tree so we can pick a
direction before building the full pipeline:

  A1  hand-authored layered conifer  (vibrant palette)
  A2  hand-authored layered conifer  (muted/earthy palette)
  A3  hand-authored round deciduous tree
  B   photo-derived: knock out sky, downscale hard, quantize colors

All output as upscaled PNGs (nearest-neighbor) into data/sprites_pixel/.
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PICS = ROOT / "data" / "tree_pics"
OUT = ROOT / "data" / "sprites_pixel"

SCALE = 10  # nearest-neighbor upscale for the hand-authored grids


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def render_grid(grid, scale, path):
    """grid: 2D list of (r,g,b) or None (transparent). Upscale + save PNG."""
    h = len(grid)
    w = len(grid[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            if c is not None:
                px[x, y] = (c[0], c[1], c[2], 255)
    img = img.resize((w * scale, h * scale), Image.NEAREST)
    img.save(path)
    print(f"wrote {path.relative_to(ROOT)}  ({w}x{h} -> {w*scale}x{h*scale})")


def outline_pass(grid, color):
    """Replace each filled pixel that touches transparency with outline color."""
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] is None:
                continue
            edge = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or grid[ny][nx] is None:
                    edge = True
                    break
            if edge:
                out[y][x] = color
    return out


def shade(x, cx, span, dark, mid, light):
    rel = (x - cx) / span
    if rel < -0.25:
        return light
    if rel > 0.45:
        return dark
    return mid


# ----------------------------------------------------------------------------
# A: hand-authored conifer (matches the real Dawn Redwood cone)
# ----------------------------------------------------------------------------
def conifer(palette):
    outl, dark, mid, light, trunk_d, trunk_l = palette
    Wp, Hp = 25, 33
    cx = 12
    grid = [[None] * Wp for _ in range(Hp)]

    tiers = [(0, 12, 5), (7, 21, 8), (15, 28, 11)]
    span = 11
    for ay, by, mhw in tiers:
        for y in range(ay, by + 1):
            frac = (y - ay) / (by - ay)
            hw = max(1, round(mhw * frac))
            for x in range(cx - hw, cx + hw + 1):
                grid[y][x] = shade(x, cx, span, dark, mid, light)

    # trunk
    for y in range(28, 33):
        for x in range(cx - 1, cx + 2):
            grid[y][x] = trunk_l if x == cx - 1 else trunk_d

    return outline_pass(grid, outl)


# ----------------------------------------------------------------------------
# A3: hand-authored round deciduous tree
# ----------------------------------------------------------------------------
def deciduous(palette):
    outl, dark, mid, light, trunk_d, trunk_l = palette
    Wp, Hp = 25, 30
    cx, cy, r = 12, 11, 10
    grid = [[None] * Wp for _ in range(Hp)]

    for y in range(Hp):
        for x in range(Wp):
            dx, dy = x - cx, y - cy
            # slightly squashed canopy
            if dx * dx + (dy * 1.05) ** 2 <= r * r:
                grid[y][x] = shade(x, cx, r, dark, mid, light)

    for y in range(20, 30):
        for x in range(cx - 1, cx + 2):
            grid[y][x] = trunk_l if x == cx - 1 else trunk_d

    return outline_pass(grid, outl)


# ----------------------------------------------------------------------------
# B: photo-derived pixel art
# ----------------------------------------------------------------------------
def photo_pixel(genus, target_w=44, colors=14, scale=6):
    img = Image.open(PICS / f"{genus}.jpg").convert("RGB")
    w, h = img.size
    # crop to the upper-center where the crown lives (drop most lawn/building)
    img = img.crop((int(w * 0.12), 0, int(w * 0.88), int(h * 0.82)))
    w, h = img.size
    px = img.load()
    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rp = rgba.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            sky = b > g and b > r and b > 110
            white = r > 200 and g > 200 and b > 200
            if not (sky or white):
                rp[x, y] = (r, g, b, 255)

    # downscale hard
    th = max(1, int(target_w * h / w))
    small = rgba.resize((target_w, th), Image.NEAREST)

    # quantize the colors (only the opaque pixels)
    rgb = Image.new("RGB", small.size, (0, 0, 0))
    rgb.paste(small, mask=small.split()[3])
    q = rgb.convert("P", palette=Image.ADAPTIVE, colors=colors).convert("RGB")
    out = q.convert("RGBA")
    # reapply transparency from the alpha mask
    out.putalpha(small.split()[3])

    big = out.resize((target_w * scale, th * scale), Image.NEAREST)
    return big


VIBRANT = [(20, 45, 28), (34, 92, 52), (60, 140, 70), (120, 200, 110),
           (74, 48, 30), (110, 74, 44)]
EARTHY = [(38, 40, 22), (74, 86, 40), (110, 124, 58), (160, 170, 90),
          (70, 50, 32), (104, 78, 46)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render_grid(conifer(VIBRANT), SCALE, OUT / "Metasequoia_A1_conifer_vibrant.png")
    render_grid(conifer(EARTHY), SCALE, OUT / "Metasequoia_A2_conifer_earthy.png")
    render_grid(deciduous(VIBRANT), SCALE, OUT / "Metasequoia_A3_round.png")
    b = photo_pixel("Metasequoia")
    bp = OUT / "Metasequoia_B_photo.png"
    b.save(bp)
    print(f"wrote {bp.relative_to(ROOT)}")
    print("done")


if __name__ == "__main__":
    main()
