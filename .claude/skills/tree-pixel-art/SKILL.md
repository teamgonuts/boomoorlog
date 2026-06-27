---
name: tree-pixel-art
description: >-
  Turn a photo of a tree into a clean, game-ready pixel-art sprite (chunky
  pixels, dark outline, left-lit shading, vibrant limited palette, transparent
  background). Use this whenever the user has a tree photo and wants it
  stylized as a pixel sprite, tree icon, or game asset -- e.g. "make a pixel
  art version of this tree", "turn these tree photos into sprites", "I need a
  pixel tree for my game", or batch-converting a folder of tree images into a
  consistent sprite set. Trigger even if the user just drops a tree image and
  asks for "a sprite" or "pixel art" without naming the style.
---

# Tree Pixel-Art Sprite

Convert a tree photo into a pixel-art sprite in a single consistent house style
("A1"): a tiny native resolution upscaled with hard nearest-neighbor pixels, a
4-step color ramp (outline / shadow / base / highlight), left-side lighting, a
1px dark outline around the silhouette, and a transparent background.

The whole point is that **a real photo drives the result** — the tree's growth
habit picks the silhouette and its color picks the hue — while the rendering
stays punchy and uniform so a whole set of sprites looks like it belongs
together. The rendering itself is deterministic and lives in a bundled script;
your job is to *look at the photo* and choose two things: the **form** and the
**hue**.

## Workflow

1. **View the photo.** Open the input image with the Read tool so you can
   actually see the tree's shape and color. Do not guess from the filename.

2. **Pick the form** — the silhouette that matches the tree's real growth habit.
   Choosing the right one is what makes each sprite distinct:

   | form        | use when the tree is…                                         | examples |
   |-------------|----------------------------------------------------------------|----------|
   | `conifer`   | a pointed, triangular evergreen / Christmas-tree cone          | pine, spruce, fir, dawn redwood, larch |
   | `round`     | a rounded, dome / lollipop deciduous crown                     | oak, maple, linden, beech, magnolia |
   | `columnar`  | tall and narrow, much taller than wide                         | Lombardy poplar, fastigiate hornbeam, Italian cypress |
   | `spreading` | a wide, flat-topped umbrella crown on a clear trunk            | plane, acacia, honey locust, old cedar |
   | `vase`      | narrow at the base, fanning outward and upward                 | elm, zelkova |
   | `weeping`   | a domed crown with long drooping branches                      | weeping willow, weeping birch |

   If a tree sits between two forms, pick the one whose *outline* a stranger
   would recognize fastest. When genuinely unsure, `round` is the safe default
   for broadleaf trees and `conifer` for needled evergreens.

3. **Pick the hue** — the dominant color of the *foliage* (ignore sky, trunk,
   and grass). Pass it as `--hue` (degrees, 0–360). The ramp's saturation and
   lightness are fixed to keep things vibrant; only the hue moves, so even an
   autumn tree comes out clean rather than muddy.

   | foliage looks like…           | hue  |
   |-------------------------------|------|
   | deep / typical green          | ~120 |
   | fresh yellow-green spring      | ~85  |
   | blue-green conifer (spruce)    | ~150 |
   | golden / yellow autumn         | ~50  |
   | orange autumn                  | ~30  |
   | red / copper (e.g. red maple)  | ~12  |
   | purple / copper beech          | ~330 |

   Prefer estimating the hue yourself from what you see. If you'd rather pull an
   exact color, sample a representative foliage pixel and pass `--base-color
   "#rrggbb"` instead of `--hue`; the script derives the hue from it.

4. **Render.** Run the bundled script:

   ```bash
   python3 scripts/render_tree_sprite.py --form <form> --hue <hue> --out <path.png>
   ```

   Optional flags: `--sat` (foliage saturation, default 50 — raise toward 65 for
   extra-punchy, lower toward 35 for a softer look), `--trunk-hue` (bark hue,
   default 28), `--scale` (nearest-neighbor upscale, default 10 → a 270×360 PNG).

5. **Show the user the result** and offer to adjust form, hue, or saturation.
   These are cheap to re-run, so iterate freely rather than agonizing over the
   first call.

## Batch conversion

When given several photos (e.g. a folder of species), view each one, decide its
form + hue, and call the script once per image, writing to a shared output
directory. Keep `--scale`, `--sat`, and `--trunk-hue` constant across the batch
so the set stays visually consistent — only form and hue should vary per tree.

## Notes

- Output is always a transparent-background PNG. It is true pixel art: a small
  grid scaled with NEAREST, so it stays crisp at any integer zoom.
- The sprite is a plain tree (no face/character). If the user later wants
  characters, that is a separate styling pass, not this skill.
- `scripts/render_tree_sprite.py --help` lists every flag and the form list.
