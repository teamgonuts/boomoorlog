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

**The whole point is accuracy: a real photo drives the result.** Every sprite
should look like *that specific tree* — its shape, its proportions, how dense or
airy its canopy is, how much trunk shows, and its real color. The single biggest
failure mode is making every tree the same green lollipop. Avoid it: two trees
should only come out looking alike if they actually look alike in the photos.

The rendering is deterministic and lives in a bundled script. Your job is to
*look at the photo* and translate what you see into the script's knobs.

## Workflow

1. **View the photo.** Open the input image with the Read tool. Never guess from
   the filename. Look at five things and say them to yourself:
   - **Overall shape** → picks the `--form`.
   - **Proportions** — is the crown wide or narrow, tall or squat?
     → `--crown-aspect`, `--crown-scale`.
   - **Trunk** — long bare trunk, or crown coming down low? thick or thin?
     → `--trunk-h`, `--trunk-w`.
   - **Canopy character** — dense solid mass, or open and airy/see-through?
     ragged/lumpy edge or smooth? → `--density`, `--texture`.
   - **Color** — dominant *foliage* hue; any blossom / berries / autumn tint?
     → `--hue` / `--base-color`, and `--accent`.

2. **Pick the form** (`--form`) — the silhouette a stranger would recognize
   fastest:

   | form        | use when the tree is…                                          | examples |
   |-------------|-----------------------------------------------------------------|----------|
   | `conifer`   | a pointed, triangular evergreen cone                            | pine, spruce, fir, dawn redwood, larch |
   | `round`     | a rounded, dome / lollipop deciduous crown                     | oak, maple, linden, beech, magnolia |
   | `egg`       | an upright oval/teardrop — taller than round but not a column   | young plane, hornbeam, ornamental pear, sweetgum |
   | `columnar`  | tall and narrow, much taller than wide                          | Lombardy poplar, Italian cypress, fastigiate trees |
   | `spreading` | a wide crown on a clear trunk, broader than tall                | mature plane, acacia, honey locust |
   | `umbrella`  | a very flat, wide, table-top crown high on a long trunk         | old cedar, old Scots pine, stone pine |
   | `vase`      | NARROW at the base, fanning OUT and UP to a broad rounded top    | elm, zelkova |
   | `weeping`   | a broad crown whose foliage drapes DOWN toward the ground       | weeping willow, weeping birch |

   When genuinely unsure: `round` is the safe default for broadleaf trees,
   `conifer` for needled evergreens. But prefer the more specific form when the
   photo clearly shows it — a tall narrow birch is `egg`/`columnar`, not `round`.

3. **Pick the hue** (`--hue`, degrees 0–360) — the dominant color of the
   *foliage* (ignore sky, trunk, grass). Saturation/lightness are fixed so even
   an autumn tree comes out clean rather than muddy.

   | foliage looks like…           | hue  |
   |-------------------------------|------|
   | deep / typical green          | ~120 |
   | fresh yellow-green spring      | ~90  |
   | blue-green conifer (spruce)    | ~150 |
   | golden / yellow autumn         | ~50  |
   | orange autumn                  | ~30  |
   | red / copper (e.g. red maple)  | ~12  |
   | purple / copper beech          | ~345 |

   Prefer estimating the hue yourself. To pull an exact color, sample a foliage
   pixel and pass `--base-color "#rrggbb"` instead. For a muted/dusky tree
   (copper beech, olive conifer) also lower `--sat` toward 38.

4. **Pick the shape + canopy knobs from the photo.** This is what makes each
   tree distinct — do not leave them all at default:

   | knob             | range / default        | read it from the photo |
   |------------------|------------------------|------------------------|
   | `--crown-aspect` | ~0.7 narrow … 1.3 wide (1.0) | tall-narrow crown → <1; broad crown → >1 |
   | `--crown-scale`  | ~0.85 … 1.15 (1.0)     | small/young tree → <1; big old tree → >1 |
   | `--trunk-h`      | 0 … 5 (0)              | long bare lower trunk (pine, mature tree) → raise it; crown coming down low → 0 |
   | `--trunk-w`      | 1 … 5 (3)              | slim sapling/birch → 1; massive old trunk (oak, poplar) → 4–5 |
   | `--texture`      | 0 smooth … 80 ragged (0) | smooth dome → ~20; leafy/lumpy → ~50; rough conifer/old tree → ~60 |
   | `--density`      | 55 airy … 100 solid (100) | open see-through crown (birch, honey locust, pine) → ~65; full dense mass (beech, holly, oak) → ~88 |
   | `--accent` + `--accent-hue` | 0 … ~65, hue 0–360 | blossom/berry/bright-tip color visibly covering the crown |
   | `--seed`         | any int (0)            | give every tree a DIFFERENT seed so their texture/clumping varies |

   **Accent** sprinkles a second color over the foliage — use it only when the
   photo actually shows it: pink/white spring blossom (`--accent-hue 335`,
   `--accent 45–65`), red berries (`--accent-hue 5`, `--accent 25`), bright
   golden autumn tips (`--accent-hue 45`, `--accent 30`). A plain green summer
   cherry gets NO accent.

5. **Render:**

   ```bash
   python3 scripts/render_tree_sprite.py --form <form> --hue <hue> \
       --crown-aspect <a> --crown-scale <s> --trunk-h <th> --trunk-w <tw> \
       --texture <tx> --density <d> --seed <n> --out <path.png>
   ```

6. **Look at the output** next to the photo and ask "would someone match these?"
   Iterate — the script is instant. Common fixes: crown too round for a narrow
   tree (lower `--crown-aspect`), looks flat/samey (raise `--texture` and vary
   `--seed`), too solid for an airy tree (lower `--density`), trunk wrong
   (`--trunk-h` / `--trunk-w`).

## Worked examples (photo → call)

- **Weeping willow** — broad curtain of foliage hanging near the ground, trunk
  hidden: `--form weeping --hue 100 --texture 15 --density 80 --seed 4`
- **Big old oak** — broad lumpy dome, thick trunk, dense:
  `--form round --hue 120 --crown-aspect 1.2 --crown-scale 1.1 --texture 62 --density 82 --trunk-w 5 --seed 1`
- **Tall slender birch** — narrow airy crown, slim trunk, fresh green:
  `--form egg --hue 92 --crown-aspect 0.78 --texture 45 --density 60 --trunk-w 1 --trunk-h 2 --seed 2`
- **Pine with bare lower trunk** — irregular blue-green conifer up high:
  `--form conifer --hue 148 --crown-aspect 0.82 --texture 55 --density 72 --trunk-h 3 --trunk-w 2 --seed 3`
- **Elm** — narrow base fanning to a broad rounded top:
  `--form vase --hue 125 --crown-scale 1.1 --texture 55 --density 82 --trunk-w 4 --seed 9`
- **Crabapple in flower** — crown smothered in magenta blossom:
  `--form round --hue 120 --crown-aspect 1.15 --texture 55 --density 85 --accent-hue 335 --accent 65 --seed 5`

## Batch conversion

When given a folder of species: view each photo, choose form + hue + the shape
and canopy knobs above, and render once per image into a shared output dir.

- **Give every tree a distinct `--seed`** so their texture/clumping never lines
  up identically.
- Keep `--scale` (and usually `--sat`) constant across the batch so the set
  stays cohesive — let form, hue, proportion, density, texture, and accent carry
  the differences.
- After rendering, spot-check several sprites against their photos. If two
  unrelated species came out looking the same, you under-used the knobs — go
  back and differentiate them.

## Notes

- Output is always a transparent-background PNG, true pixel art (a small grid
  scaled with NEAREST), so it stays crisp at any integer zoom.
- The sprite is a plain tree (no face/character). Characters are a separate pass.
- `--density` carves chunky shadow clumps into the canopy (never see-through
  speckle); `--texture` roughens the silhouette edge. Use both, not just hue.
- `scripts/render_tree_sprite.py --help` lists every flag.
