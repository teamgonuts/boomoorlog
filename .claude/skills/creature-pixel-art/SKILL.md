---
name: creature-pixel-art
description: >-
  Turn a photo of an animal or insect into a clean, game-ready pixel-art sprite
  in the same house style as the tree sprites (chunky pixels, dark outline,
  left-lit shading, vibrant limited palette, transparent background, landscape
  32x24 grid). Use this whenever the user has a creature photo and wants it
  stylized as a pixel sprite, creature icon, or game asset -- e.g. "make a
  pixel art version of this bug", "turn these creature photos into sprites",
  "I need a pixel bat for my game", or batch-converting a folder of creature
  images into a consistent sprite set. Trigger even if the user just drops a
  creature image and asks for "a sprite" or "pixel art" without naming the
  style.
---

# Creature Pixel-Art Sprite

Sibling skill to `tree-pixel-art`. Same house style ("A1"): tiny native
resolution upscaled with hard nearest-neighbor pixels, a 4-step color ramp
(outline / dark / mid / light), left-side lighting, a 1px dark outline around
the silhouette, transparent background.

**Difference from trees:**
- **Landscape 32x24 grid** instead of trees' portrait 27x36. At-a-glance
  tells you "creature" vs "tree" in the asset folder.
- **Forms are body plans** (bug, beetle, caterpillar, moth, bee, spider,
  bird, mammal, bat) rather than tree silhouettes.
- **Accents paint stripes or spots** on the body instead of berries/blossom
  in a canopy.

**The whole point is still accuracy: a real photo drives the result.** Every
sprite should look like *that specific creature* — its body plan, its color,
its wing-or-no-wing, its stripes/spots. The single biggest failure mode is
making every aphid look like every other green oval. Use the knobs to keep
them distinct.

## Workflow

1. **View the photo.** Open the input image with the Read tool. Never guess
   from the filename or the latin name. Look at five things:
   - **Body plan** → picks the `--form`.
   - **Size / proportions** — long & thin, fat & round?
     → `--size`, `--aspect`.
   - **Color** — dominant body color. Use real hue.
     → `--hue` or `--base-color`.
   - **Markings** — stripes (bee/wasp/caterpillar), spots (ladybird/tit),
     wing patterns? → `--accent-hue`, `--accent`, `--accent-mode`.
   - **Wings / legs / tail** — bushy tail vs thin tail (squirrel vs mouse),
     spread wings vs none, legs visible? → `--tail`, `--no-legs`,
     `--no-antennae`.

2. **Pick the form** (`--form`) — the body plan a stranger would recognize
   fastest:

   | form          | use when the creature is…                                    | examples |
   |---------------|--------------------------------------------------------------|----------|
   | `bug`         | tiny oval body, no wings, maybe legs+antennae                | aphid, scale, mealybug, mite, generic small insect |
   | `beetle`      | hard oval shell with central elytra seam                     | ladybird, weevil, longhorn beetle, dor beetle |
   | `caterpillar` | horizontal segmented worm                                    | sycamore moth larva, hawk-moth caterpillar, processionary |
   | `moth`        | symmetric wings spread top-down (forewing + hindwing)        | codling moth, hawk moth, butterfly |
   | `bee`         | side-view fat body + wings arching up                        | honey bee, bumblebee, wasp, hoverfly, fly |
   | `spider`      | round body + 8 legs radiating                                | garden spider, theridiid, harvestman (close enough) |
   | `bird`        | passerine perched, body + head + tail + eye                  | blue tit, robin, finch, sparrow, blackbird, jay |
   | `mammal`      | side-view 4-legged body with head + tail                     | squirrel, dormouse, mouse, marten, hedgehog |
   | `bat`         | small body + wings arched up-and-out, scalloped membrane     | pipistrelle, noctule, barbastelle |

   When genuinely unsure: `bug` is the safe default for any small insect,
   `bird` for any small passerine. Prefer the more specific form when the
   photo clearly shows it — a bee with visible wings is `bee`, not `bug`.

   **Microbe / bacteria / fungi** (Bradyrhizobium, Frankia, Verticillium,
   etc.) → use `bug` with `--size 0.7` and `--accent 60 --accent-mode spots`
   for a cluster look.

3. **Pick the hue** (`--hue`, degrees 0–360) — the dominant color of the
   *body* (ignore background, flowers, leaves). Saturation is fixed punchy
   by default so even a dusky creature comes out clean.

   | body looks like…                | hue   |
   |---------------------------------|-------|
   | brown / tawny (mammal, moth)    | ~25   |
   | gold / yellow (bee, finch)      | ~45   |
   | orange / rust (squirrel, fox)   | ~18   |
   | red / cinnabar                  | ~5    |
   | pink / blossom                  | ~340  |
   | green (aphid, caterpillar)      | ~110  |
   | blue (blue tit, jay flash)      | ~210  |
   | slate / grey-blue               | ~220  |
   | black / dark                    | hue 0, `--sat 5`, low light  |
   | white / pale                    | any, `--sat 10`              |

   Prefer estimating yourself; to pull an exact color sample a body pixel
   and pass `--base-color "#rrggbb"`.

4. **Pick the shape + marking knobs from the photo:**

   | knob              | range / default          | read from the photo |
   |-------------------|--------------------------|---------------------|
   | `--size`          | 0.6 tiny … 1.2 big (1.0) | tiny aphid → 0.7; large beetle → 1.1 |
   | `--aspect`        | 0.7 round … 1.4 elongated (1.0) | round/compact → <1; long thin (caterpillar, wasp) → >1 |
   | `--tail`          | none / thin / bushy (thin) | bushy: squirrel, marten; thin: mouse, rat; none: dormouse, hedgehog |
   | `--bristles`      | flag (off)               | caterpillar with visible hairs (sycamore moth larva, vapourer) |
   | `--no-legs`       | flag                     | suppress legs when they aren't visible (aphid hidden under wing, microbe) |
   | `--no-antennae`   | flag                     | suppress antennae for non-insects or smooth-fronted bugs |
   | `--accent-hue`    | 0–360                    | the stripe / spot / wing-marking color in the photo |
   | `--accent`        | 0–100 (0)                | how prominent the marking is — 50 = visible, 25 = subtle |
   | `--accent-mode`   | spots / stripes (spots)  | stripes for bee/wasp/caterpillar; spots for ladybird/tit/spotted moth |
   | `--seed`          | any int (0)              | give every creature a DIFFERENT seed so accent-spot placement varies |

5. **Render:**

   ```bash
   python3 scripts/render_creature_sprite.py --form <form> --hue <hue> \
       --size <s> --aspect <a> --tail <t> \
       --accent-hue <ah> --accent <amt> --accent-mode <m> \
       --seed <n> --out <path.png>
   ```

6. **Look at the output** next to the photo and ask "would someone match
   these?" Iterate — the script is instant. Common fixes:
   - Wings invisible (bee/moth) → make sure you've actually picked `bee` or
     `moth` form, not `bug`.
   - Stripes too dominant → lower `--accent` toward 30, or switch to spots.
   - Mammal looks like a hot-dog → set `--tail bushy` for squirrel-likes.
   - Bird looks generic → use `--accent` with the right colored belly hue.

## Worked examples (photo → call)

- **Sycamore aphid** — small pale-green sap-feeder:
  `--form bug --hue 110 --sat 50 --size 0.85 --aspect 1.1 --seed 1`
- **Honey bee** — golden body with dark stripes:
  `--form bee --hue 38 --sat 75 --aspect 1.3 --accent-hue 25 --accent 50 --accent-mode stripes --seed 2`
- **Sycamore moth caterpillar** — yellow-orange "punk" larva with bristles:
  `--form caterpillar --hue 45 --sat 65 --bristles --seed 3`
- **Codling moth** — small brown moth:
  `--form moth --hue 28 --sat 45 --seed 4`
- **Blue Tit** — slate-blue back, yellow belly:
  `--form bird --hue 210 --sat 55 --accent-hue 50 --accent 40 --seed 5`
- **Eurasian Red Squirrel** — rusty orange with huge bushy tail:
  `--form mammal --hue 18 --sat 70 --tail bushy --seed 6`
- **Common Pipistrelle** — dark brown bat with spread wings:
  `--form bat --hue 25 --sat 40 --seed 7`
- **Theridiid spider** — small dark spider, 8 legs:
  `--form spider --hue 25 --sat 35 --seed 8`
- **Ladybird (7-spot)** — red beetle with black spots:
  `--form beetle --hue 5 --sat 80 --accent-hue 0 --accent 30 --accent-mode spots --seed 9`

## Batch conversion

When given a folder of creature pics (or the `creatures` table / `data/creatures.csv`):
view each photo, choose form + hue + accent, and render once per creature into
a shared output dir (`data/creature_sprites_pixel/{slug}.png`).

- **Give every creature a distinct `--seed`** so accent placements never line
  up identically.
- Keep `--scale` (and usually `--sat`) constant across the batch so the set
  stays cohesive — let form, hue, size, accent carry the differences.
- After rendering, spot-check several sprites against their photos. If two
  unrelated species came out looking the same, you under-used the knobs — go
  back and differentiate them.

## Notes / known limits

- Output is always a transparent-background PNG, true pixel art (a 32x24 grid
  scaled with NEAREST), so it stays crisp at any integer zoom.
- The sprite is a plain creature (no face beyond an eye dot for bird/mammal).
- Form library is intentionally small. If you find a creature that needs a
  new body plan (fish, snail, slug), add a `form_<name>` function to
  `scripts/render_creature_sprite.py` modeled on the existing ones — they're
  all ~30 lines.
- `scripts/render_creature_sprite.py --help` lists every flag.
