# Behavior Taxonomy — Locked C2

> The master vocabularies for `organisms.habitat_classes` and
> `organisms.movement_classes`, plus per-category defaults and override rules.
> Locked 2026-06-29 (Creatures AMS C2 milestone). Stress-tested against the
> top 60 most-observed species in Amsterdam (see
> [potential-creatures.md](potential-creatures.md)).
>
> The values are stable IDs. The wiki / UI can surface friendlier labels, but
> changing a value in the DB needs a follow-up migration.

---

## Habitat classes (12)

What polygon / surface the organism actually lives on. Drives the map
placement rule in milestone C5 (habitat-realistic placement). Multi-valued:
the dominant tag is at index 0; a coot is `['water-surface', 'ground-park']`
because it lives on water but sometimes wanders onto bank lawns.

| ID | Map placement rule | What it is | Example organisms |
|---|---|---|---|
| `tree-rooted` | At the actual tree coordinate from the trees dataset. | Physically a tree. | Tilia, Quercus, Platanus, every genus in the tree roster. |
| `tree-canopy` | Snap to the nearest tree sprite within ~30m of the raw observation; place inside its canopy area. | Lives in tree foliage. | Eurasian Blue Tit, Chiffchaff, Blackcap, Wren, aphids, oak processionary caterpillar. |
| `tree-bark` | Snap to the nearest tree sprite; place on the trunk/stem area. | Anchors to the bark surface. | Treecreeper, bracket fungi, foliose lichens, bark beetles, jumping spiders on trunks. |
| `ground-park` | Place inside the nearest OSM park / cemetery / green polygon within ~50m. | Needs vegetated ground / soil. | Hedgehog, rabbit, fox, ground beetles, slugs, most mushrooms, snowdrops. |
| `ground-urban` | Place on the nearest paved area (street / pavement / square). | Tolerates / prefers built-up ground. | Foraging pigeons, brown rat, urban dandelion, ants in pavement cracks. |
| `water-surface` | Snap to the nearest OSM water polygon; place on top of the water. | On or just above the water surface. | Coot, mallard, moorhen, swans, Egyptian goose, water boatman. |
| `water-edge` | Place along the boundary of the nearest OSM water polygon. | Banks, reedy edges, canal walls. | Grey heron, cormorant drying wings, kingfisher, common frog. |
| `water-body` | Place inside the nearest OSM water polygon; rendered "below" the surface. | In the water itself. | Wild carp, common rudd, chub, red swamp crayfish, mute swan when diving. |
| `sky-only` | Place over the centroid of an open polygon (water, square, park); never resolves to a perch. | Almost never lands in view; soars / glides through. | Common swift, swallow, sand martin, soaring gulls. |
| `flower-visitor` | Place near flowering trees / plants in season; falls back to `tree-canopy` / `ground-park` out of season. | Anchored to blooms when blooming, dormant otherwise. | Honey bee, common carder bumblebee, Red Admiral, Peacock butterfly, marmalade hoverfly. |
| `wall-and-roof` | Place on the boundary of the nearest OSM building polygon. | Vertical built surfaces. | House sparrow, swift colony entrance, jackdaw, peregrine, zebra spider, wall mosses. |
| `anywhere` | Place at the raw observation coordinate, falling back to any plausible polygon nearby. | True urban generalist, won't be wrong wherever you put it. | Magpie, carrion crow, herring gull. Use sparingly. |

### How to pick when several apply

Pick the **most specific** value as the dominant tag. `water-edge` beats
`anywhere` for a heron; `tree-canopy` beats `anywhere` for a tit. Add a
second tag only when the organism *genuinely* changes habitat (a coot
beds on the bank lawn; a mallard begs on pavements).

### Habitats NOT in the vocabulary, and why

| Considered | Decision | Why |
|---|---|---|
| `garden`, `hedge` | Folded into `tree-canopy`. | Visually identical for placement; no organism in our roster needs the distinction. |
| `meadow`, `grassland` | Folded into `ground-park`. | Amsterdam doesn't have meaningful meadow polygons distinct from parks. |
| `cavity-nester` | Folded into `tree-canopy` / `wall-and-roof`. | Nesting cavity = inside the tree / wall; placement-equivalent to its surface tag. |
| `sand`, `dune`, `farmland` | Out of scope. | Not present in central Amsterdam. |
| `under-leaf-litter` | Folded into `ground-park`. | Visible placement is the same. |

---

## Movement classes (9)

How the organism is animated on the map. Drives milestones C6 (idle motion)
and C9 (smart per-species movement). Multi-valued: an organism can switch
between behaviors. The dominant tag at index 0 is what the animator picks
most often; secondaries fire on a low-probability tick or under specific
context (time of day, season). The animator implementation is one function
per class.

| ID | Animation | What it does | Example organisms |
|---|---|---|---|
| `none` | Static sprite. | Doesn't move at all. | Every tree, every fungus, every lichen. |
| `idle-only` | 1–2 alternate frames swapped slowly (bob / sway / blink); no positional change. | Stays put but visibly alive. | Heron when stalking (stands frozen), web-anchored spiders, sleeping bats, dragonfly perched. |
| `tree-flitter` | Hops to a nearby tree sprite every ~5–10s with a short arc; idle in between. | Songbirds flitting between branches. | Blue tit, chiffchaff, blackcap, wren, common chaffinch. |
| `water-edge-stalker` | Walks slowly along the boundary of its water polygon at ~1 sprite-width / sec. | Wading birds patrolling banks. | Grey heron, cormorant, white stork. |
| `sky-looper` | Long curved paths over open polygons; never lands in view. | Aerial-only birds and bats. | Common swift, swallow, common pipistrelle, gulls when soaring. |
| `park-roamer` | Random walk inside its park polygon; pauses every few steps. | Mammals wandering through green. | Hedgehog, rabbit, hare, fox (at dusk). |
| `water-drifter` | Drifts along the canal centerline at slow constant speed; rotates with the canal direction. | On / in the water, going with the flow. | Mallard, mute swan, wild carp, coot when not bank-stalking. |
| `flower-bobber` | Short bobs (~0.5 sprite-width) between nearby flowering tree sprites in season; dormant out of season. | Pollinators moving flower to flower. | Honey bee, bumblebees, hoverflies, butterflies, day-flying moths. |
| `urban-walker` | Short walks along pavements / streets, with frequent pauses. | Ground-foragers on built surfaces. | Foraging pigeon, foraging gull, brown rat (at night), foraging magpie. |

### Movements NOT in the vocabulary, and why

| Considered | Decision | Why |
|---|---|---|
| `slow-creep` (snails, slugs) | Folded into `idle-only`. | Their movement is below the renderer's frame-rate threshold. |
| `web-anchored` (web spiders) | Folded into `idle-only`. | Animation-identical; they sit there. |
| `dive` (kingfisher, cormorant) | Folded into `water-edge-stalker` with an idle-only secondary. | The dive itself is a one-frame burst we'll add later if it pays off. |
| `swim-under-water` | Folded into `water-drifter`. | Same path generator; only the z-order differs, and that's an `habitat_classes` job (`water-body` renders below the surface). |

---

## Per-category defaults

When the C3 labeling pass runs, every organism starts with these defaults.
Most fit; the rest get per-species overrides. The defaults are tuned so a
default placement is *visually plausible*, not necessarily biologically
precise — overrides handle the precision.

| Category | Habitat default | Movement default | Notes |
|---|---|---|---|
| `tree` | `['tree-rooted']` | `['none']` | Always fits. No overrides expected. |
| `bird` | `['tree-canopy']` | `['tree-flitter']` | Small songbirds dominate the roster. Big urban birds (magpies, pigeons, gulls, swifts, herons) need overrides. |
| `mammal` | `['ground-park']` | `['park-roamer']` | Hedgehog/rabbit/fox fit. Bats, squirrels, water voles override. |
| `insect` | `['flower-visitor']` | `['flower-bobber']` | Bees / butterflies / hoverflies fit. Ground beetles, moths-at-rest, dragonflies override. |
| `arachnid` | `['anywhere']` | `['idle-only']` | Spiders are too varied for a useful default beyond "sits there." |
| `mollusc` | `['ground-park']` | `['idle-only']` | Most slugs / snails fit. Aquatic snails / mussels override to `water-body`. |
| `amphibian` | `['water-edge']` | `['water-edge-stalker']` | Toads / frogs fit; salamanders override to `ground-park`. |
| `reptile` | `['wall-and-roof']` | `['idle-only']` | Wall lizard fits if Amsterdam has it; turtles override to `water-surface`. |
| `fish` | `['water-body']` | `['water-drifter']` | Always fits. No overrides expected. |
| `fungus` | `['tree-bark']` | `['none']` | Bracket / shelf fungi fit. Ground / soil mushrooms (most of them) override to `ground-park`. |
| `lichen` | `['tree-bark']` | `['none']` | Most fit; some are `wall-and-roof`. |
| `plant` | `['ground-park']` | `['none']` | Non-tree vascular plants. Aquatic plants override. |
| `other` | `['anywhere']` | `['idle-only']` | Catch-all. Every `other` row should get a manual override during C3 review. |

---

## How overrides work in C3

For each row in the master inventory:

1. **Apply category default.** Every row gets the dominant habitat + movement
   values from the table above.
2. **Per-organism research.** For each row, decide:
   - Does the default fit? → leave as-is, mark `source = 'default'`.
   - Doesn't fit? → override `habitat_classes` and/or `movement_classes`,
     mark `source = 'override'`, write a one-sentence `reason`.
   - Genuinely multi-class? → set arrays with dominant at index 0, others
     after, mark `source = 'override'`.
3. **Write per-organism markdown.** `memory/organisms/<slug>.md` with the
   final tags + research notes (eventually rendered on the wiki page).

The override file (`data/organism_tags.csv`) is what eventually feeds into
an `UPDATE` against `organisms`.

---

## Multi-valued behavior (when to use it)

Most organisms get a single dominant value in each array. Use a second
value only when the organism *demonstrably* alternates behaviors that need
different animations or placements:

| Organism | `habitat_classes` | `movement_classes` | Why multi |
|---|---|---|---|
| Coot | `['water-surface', 'ground-park']` | `['water-drifter', 'park-roamer']` | Lives on water; routinely bank-grazes. |
| Mallard | `['water-surface', 'ground-urban']` | `['water-drifter', 'urban-walker']` | Begs on pavements. |
| Mute Swan | `['water-surface']` | `['water-drifter', 'idle-only']` | Spends real time grooming statically. |
| Bumblebee | `['flower-visitor']` | `['flower-bobber', 'sky-looper']` | Long transit flights between flower patches. |
| Magpie | `['anywhere']` | `['tree-flitter', 'urban-walker']` | Genuinely both — tree perches AND pavement foraging. |
| Grey Heron | `['water-edge']` | `['water-edge-stalker', 'idle-only']` | Stalks slowly, then stands rock-still for minutes. |

Three or more values is almost always wrong — collapse to the two most
distinct.

---

## Open extensions (not in scope for C2)

Documented here so we don't re-litigate during C3; these become later
milestones if they earn it.

- **`activity_window`** — `diurnal | nocturnal | crepuscular`. Needed for
  C7 (day / night cycle) but doesn't belong in habitat or movement. Will be
  added as a separate column when C7 lands.
- **`seasonal_habitat`** — most flower-visitors are seasonal. C8 (seasonal
  skin) can handle this by simply hiding `flower-visitor` organisms in
  winter rather than adding a new field.
- **Sub-classes** (e.g. `tree-canopy:upper` vs `tree-canopy:lower`,
  `water-edge:reedy` vs `water-edge:bare`) — defer until placement looks
  monotonous and we have evidence we need finer granularity.

---

## Changelog

- **2026-06-29** — Locked v1 of the vocabulary. 12 habitats, 9 movements,
  13 categories, per-category defaults defined. (C2 milestone.)
