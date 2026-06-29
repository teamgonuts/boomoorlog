# Creatures AMS — Roadmap to Production

> Living document. The source of truth for **what we ship** and **in what order** to get
> [Creatures AMS](CREATURES_VISION.md) production-ready.
>
> Last updated: 2026-06-29

---

## North star

A **single-purpose website** where Amsterdam locals open a pixel-art map of their city
and find it already alive — real trees in their real places, real animals in their real
habitats, real sightings from this week — and click anything to learn its story. Grounded
entirely in open data; ambient and whimsical without being dishonest.

Full vision: [CREATURES_VISION.md](CREATURES_VISION.md).

---

## How this roadmap is organised

Milestones are grouped into four phases. Within a phase, milestones are listed in
intended delivery order, but most are independent enough to reorder if priorities shift.

Each milestone is a **gate** — a single coherent ship — not a sprint estimate.

The "house style" (chunky pixel art, soft basemap, limited palette) is preserved
throughout. Every "alive map" milestone is an **incremental enhancement** of that style,
not a replacement.

---

## Phase 1 — Foundation: one unified encyclopedia

Trees, creatures, fungi, lichens, and future categories collapse into one organism model.
This phase is the **organising layer** that everything else in the roadmap reads from:
the schema, the canonical behavior vocabularies, the per-organism tags, and the source-
agnostic ingest pipeline.

Nothing visible to the visitor ships in this phase. The payoff is that every subsequent
milestone reads from clean, tagged data instead of hard-coding per-creature rules.

### C1 — Unified organism model
- One canonical `organisms` table (or equivalent) supersedes `genera` + `creatures`.
- Columns the rest of the roadmap depends on:
  - `category` — `tree | bird | mammal | insect | fungus | lichen | …`
  - `habitat_class` — where this organism plausibly appears on the map (vocabulary in C2).
  - `movement_class` — how this organism moves, if at all (vocabulary in C2).
  - `sprite_path`, `latin_name`, `dutch_name`, `english_name`, `lore`, `sources[]`.
- One wiki route (`/wiki/<slug>`) renders any organism.
- Map markers carry an `organism_slug` regardless of which table the entity used to live
  in.
- `tree_genera` cross-link on creatures generalises into an organism-↔-organism
  relationship.
- Migration preserves all existing data, sprites, lore.
- Columns are `text` for now (cheap, flexible). CHECK constraints / enums can land later
  once the vocab is settled.

### C2 — Behavior taxonomy (master vocabularies)
The fixed, reviewable set of values that `habitat_class` and `movement_class` accept,
plus per-category defaults. This is a **design doc** milestone, not code.

- **Habitat classes** (draft starting set, to be refined):
  - `tree-canopy` — lives in tree foliage (most small birds, some insects).
  - `tree-bark` — lives on bark (some insects, lichens, some fungi).
  - `tree-rooted` — physically a tree (the trees themselves).
  - `ground-park` — needs park / green polygons (squirrels, hedgehogs, rabbits).
  - `ground-urban` — comfortable on streets / pavements (rats, urban birds).
  - `water-surface` — on or just above water (ducks, coots, swans).
  - `water-edge` — canal banks, reedy edges (herons, kingfishers).
  - `water-body` — in the water itself (fish).
  - `sky-only` — almost never lands in view (swifts, swallows).
  - `flower-visitor` — anchored to flowering plants in season (bees, butterflies).
  - `wall-and-roof` — buildings / walls (some birds, lizards).
  - `anywhere` — true urban generalists (magpies, crows, pigeons).
- **Movement classes** (draft starting set, to be refined):
  - `none` — stationary (trees, fungi, lichens).
  - `idle-only` — visible breathing / sway but no path (most stationary creatures).
  - `tree-flitter` — hops between nearby trees.
  - `water-edge-stalker` — slow walk along water polygon edges.
  - `sky-looper` — loops over open polygons; never lands in view.
  - `park-roamer` — wanders inside park polygons.
  - `water-drifter` — drifts along canal centerlines.
  - `flower-bobber` — bobs between flowering tree sprites in season.
  - `urban-walker` — short paths along ground / pavements.
- **Per-category defaults** (so most rows are tagged without per-organism research):
  - `tree → habitat=tree-rooted, movement=none`
  - `fungus → habitat=tree-bark (most) or ground-park, movement=none`
  - `lichen → habitat=tree-bark, movement=none`
  - `bird → habitat=anywhere, movement=tree-flitter` (override per species)
  - `insect → habitat=anywhere, movement=flower-bobber` (override per species)
  - `mammal → habitat=ground-park, movement=park-roamer` (override per species)
- The vocabularies are deliberately small — easier to label, easier to animate, easier
  to extend. Each value maps to one behavior implementation in code.

### C3 — Organism labeling pass
Apply tags to every row in the encyclopedia. Defaults from C2 land first via bulk
SQL; then a per-organism research pass overrides where biology warrants.

- Step 1: bulk-apply category defaults to every organism.
- Step 2: per-organism research pass — for each row, check whether the default fits.
  Override `habitat_class` / `movement_class` where the species is atypical.
  - *Example overrides:* heron → `water-edge` / `water-edge-stalker`; swift →
    `sky-only` / `sky-looper`; mallard → `water-surface` / `water-drifter`; fish →
    `water-body` / `water-drifter`; hedgehog → `ground-park` / `park-roamer`
    (default already fits); honeybee → `flower-visitor` / `flower-bobber`.
- Output: every organism in the encyclopedia has both columns populated, with a small
  audit log of which rows were overridden vs. left as default.
- For organisms added in the future (via C4 new sources), defaults are applied
  automatically; a manual override pass is triggered only for high-volume or
  obviously-atypical species.

### C4 — Extensible observation pipeline
- Generalise the `observations` ingest so adding a new source is a config change, not a
  new table.
- Document the recipe for adding a new feed.
- Onboard 1–2 new sources as proof — candidates: eBird (richer bird data), GBIF fungi
  for Amsterdam, a citizen-science fungi feed, NDFF where licensing allows.

### C3.A — Long-tail labeling pass *(post-C1, follow-up)*
Surfaced 2026-06-29 after applying the first migration round. The C3 labeling pass
covered the 319 curated organisms in `data/creatures.csv`. After migration 021 ran,
**2,197 long-tail observation-only species** landed in `organisms` with empty
`habitat_classes` / `movement_classes` and a fallback `category='other'`. They need:
- A second C3-style labeling pass (same parallel-batch shape, sonnet agents) to
  assign habitat + movement tags + per-organism markdown.
- A category cleanup so `'other'` becomes a proper biological category from GBIF.
- These rows have no sprite yet — they remain hidden from the map, but they're in
  the encyclopedia and need wiki-ready prose.
Tagged in roadmap so it's not forgotten; not a hard blocker for the alive map (the
2,197 species aren't sprite-rendered today anyway).

### C3.B — GBIF taxonomy QA pass *(post-C1, follow-up)*
The GBIF auto-match in `pipeline/enrich_taxonomy.py` produced a small number of
false hits where the Latin name collides with a higher-rank taxon. Example caught:
`pica` matched to `rank='phylum'` because Pica is also a phylum name. A short QA
pass needs to:
- Walk every `organisms` row with `rank IN ('phylum','kingdom','class')` and verify.
- Fix mismatches by re-querying GBIF with a more specific name (e.g. "Pica pica").
- 12 organisms are `rank='unmatched'`; these need manual matching (or are genuinely
  unresolvable — like "Generalist sap-feeders").

---

## Phase 2 — The map comes alive

With organisms tagged, the map can read each row's `habitat_class` and `movement_class`
and render the right behavior. Today the map shows static markers; after this phase, the
map *breathes* — real geography, motion, time of day, season, sound, weather.

Most visitors will spend most of their time looking at the output of this phase.

### C5 — Habitat-realistic placement
Each organism appears where its `habitat_class` says it lives, not at the raw
observation point (which is often a human's apartment).
- Pull OSM water / park / landuse polygons + our tree dataset for the viewport.
- At placement time: snap each sprite to the nearest valid habitat polygon / tree
  within a tolerance of its raw observation point. Discard if no plausible spot.
- Class → placement rule is a small lookup table; new classes plug in trivially.

This is the single biggest visual change. Most "wait, that's cool" reactions come from
here.

### C6 — Idle motion
Sprites bob, sway, blink, twitch. No pathing — just signs of life. Driven off
`movement_class != none` for any organism (and `idle-only` for the ones that don't path).
- 1–2 alternate frames per sprite, swapped on a slow interval.
- Slightly different phase per sprite so the city doesn't pulse in sync.
- Trees, fungi, lichens (`movement_class = none`) stay perfectly still.

### C7 — Day / night cycle
Map time follows the visitor's real Amsterdam local time.
- Basemap palette shift (light → dusk → night).
- Nocturnal species (bats, owls, hedgehogs) appear at night; daytime species hide.
  Driven by an `activity_window` tag we may add to organisms here or in C2.
- Dawn / dusk transitions on a smooth curve.
- A small clock indicator somewhere unobtrusive.

### C8 — Seasonal skin
Palette + pixel particles per season.
- **Spring** — Prunus blossom particles drifting near cherry trees, lighter palette.
- **Summer** — lush canopy, longer daylight.
- **Autumn** — falling leaves, oranges in the basemap.
- **Winter** — bare branches, occasional pixel snowflakes.
- Driven by real calendar date.

### C9 — Smart per-species movement
Per-`movement_class` behaviour. Each class is a small deterministic path generator,
seeded by the observation coordinate; sprites stay readable.
- `tree-flitter` — hop between nearby trees.
- `water-edge-stalker` — walk slowly along water polygon edges.
- `sky-looper` — loop over open squares and water; never land.
- `park-roamer` — wander inside park polygons.
- `water-drifter` — drift along canal centerlines.
- `flower-bobber` — bob between flowering tree sprites in season.
- `urban-walker` — short paths along ground / pavements.
- `none` / `idle-only` — handled in C6.

### C10 — Sound layer
Click any creature → hear its real species call (xeno-canto; free; attribution
required).
- **Off by default.**
- On first click of a creature, a one-time prompt: *"Want bird & creature sounds?"*
- Choice persists across sessions (localStorage).
- Visible toggle in the UI for changing later.
- Graceful fallback when xeno-canto has no recording for that species.

### C11 — Weather mirror
Live KNMI conditions drive subtle map effects.
- Rain → faint pixel droplets across the canvas.
- Wind → leaves shake on tree sprites.
- Cloud cover → softens the basemap.
- Refresh every ~15 minutes. Map continues to function if KNMI is down.

---

## Phase 3 — Make exploration rewarding

Once the map is alive and the encyclopedia is organised, the click-experience must
match. Every click should pay off.

### C12 — First-visit experience
- Beautiful Amsterdam-wide ambient default state when no address is set.
- Browser geolocation prompt (opt-in).
- Address-entry nudge if geolocation is denied.
- The map should be visibly *doing things* within 1 second of page load.

### C13 — "My block" personalised page
- A permanent URL per address (`/b/<hash>` or similar).
- Centered on the visitor's address, framed as their home patch.
- Headline at top: today's most interesting recent sighting in the visitor's block.
- Bookmark-able, shareable.

### C14 — Living dossier
Every organism wiki page shows:
- Recent observations within 1km of the visitor.
- "Seen N times this week / month" counters.
- A small gallery of real recent photos from iNat / Waarneming.
- Cross-links: tree pages list creatures seen on that genus; creature pages list the
  trees they prefer.

### C15 — Discovery features
- **Surprise me** button → pans/zooms to a delightful spot in Amsterdam right now (rare
  recent sighting, the oldest tree in the city, a goose family camping somewhere).
- **Hotspots** overlay → soft heatmap of recent biodiversity density.
- **Rarity radar** → subtle glow on locally-uncommon species (first dragonfly of the
  year, a rare moth, etc.).

---

## Phase 4 — Launch readiness

After Phase 3 the site is feature-complete. Phase 4 is about shipping it respectfully
into the world and finding its audience.

### C16 — Custom domain
- Register `creatures-ams.io`.
- Configure DNS, point to host.
- Decide subdomain vs single-domain split for wiki / map / root.

### C17 — Credits & attribution
A single, well-designed page listing every data source, every photo contributor (per
iNat license), every library, every human contributor. Linked prominently from the
footer. Includes:
- Amsterdam open data (trees, BAG, BGT…).
- iNaturalist, Waarneming.nl, OSM, KNMI, xeno-canto, AHN, PDOK.
- Open-source libraries (Leaflet, Next.js, Supabase libs, etc.).
- Per-photo attribution where licenses require.

### C18 — Conservation donation flow
A clean, gentle way for visitors to donate to a named local Amsterdam conservation
organisation. Not pushy, not blocking — just present.
- Choose the partner organisation (open decision).
- Wire the donation link / widget — straight passthrough; we don't take a cut.
- Decide framing and placement (footer, dossier sidebar, a one-off "thank you for
  caring" page after a few minutes on site).

### C19 — Distribution & marketing strategy
- Pick 2–3 channels: Amsterdam subreddits, local nature / birding communities,
  IG / TikTok of the pixel-art map, gemeente partnerships, local press, schools.
- Sequence the launch: soft-launch → community channels → press.
- Build a launch-day artefact per channel (a thread, a short video, a postcard image).
- Decide cadence for ongoing content (weekly "what's new in the city" post, etc.).

### C20 — Mobile polish
Even though v1 is desktop-first, the site has to feel right on a phone before public
launch — that's where the locals will actually open it.
- Map controls re-sized for touch.
- Panels re-sized.
- Sprite legibility at phone DPRs.
- Touch ergonomics for click-to-wiki.
- Real-device test on mid-range Android + iOS, not dev-tools emulation.

### C21 — Performance pass
- Clustering at low zoom.
- Sprite atlasing.
- Tile and marker budgets.
- Cold-load TTI under realistic traffic.
- Server cost projection at projected launch traffic.

---

## Decisions still open

- Real-time vs accelerated simulation clock (C7 — leaning real-time mirror).
- Whether to add an `activity_window` column in C2 or defer until C7 needs it
  (leaning: defer; C7 can read from a small per-organism override list).
- Conservation partner (C18).
- Distribution channel set (C19).
- Subdomain vs single domain (C16).
- Whether to keep Tower Defense surfaces discoverable from this site, or hide entirely.

Defer until the milestone surfaces them. Don't pre-decide.

---

## Relationship to Tower Defense

TD is **parked**. See [TOWER_DEFENSE_VISION.md](TOWER_DEFENSE_VISION.md) and
[TOWER_DEFENSE_ROADMAP.md](TOWER_DEFENSE_ROADMAP.md). The two products share
infrastructure (Supabase, sprite pipeline, geocoding, `/play` map code) but only
Creatures AMS is shipping. If TD ever revives, it can sit on top of the unified
encyclopedia and existing infra without rewriting.

---

## What we are not doing (and why)

| Not doing | Why |
|---|---|
| Realistic animal physics / pathfinding sim | "Honest whimsy" → behavior classes that *read* as alive are enough. A real sim is heavier, slower, and easier to get wrong. |
| Accounts, profiles, login | Visitor-anonymous by design. "My block" via URL hash, not auth. |
| User-generated content / submitted sightings | We surface iNat & Waarneming; visitors who want to log a sighting go there. We don't compete. |
| Native apps | Web first, mobile polish in C20. Native is a future possibility, not part of v1. |
| Gamification (points, badges, levels) | Single-purpose discovery site, not a game. TD is the parked sibling for that itch. |
| Per-organism custom behaviour code | Behavior lives in the `movement_class` lookup, not per-organism. Adding a new species = picking a class, not writing code. |
