# Creatures AMS — Roadmap to Production

> Living document. The source of truth for **what we ship** and **in what order** to get
> [Creatures AMS](CREATURES_VISION.md) production-ready.
>
> Last updated: 2026-07-01

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

### C3.D — Sprite production + admin QA tool *(post-photo-backfill, follow-up)*
Surfaced 2026-06-29 after the photo-backfill pass. We now have photos for
nearly every organism in the encyclopedia, but only ~360 have sprites
(curated creatures from the original pipeline + ~55 stat-blocked trees).
The other ~2,300 organisms are wiki-only — they don't render on the map.

**Scope:**
- **Bulk sprite generation.** For every organism with a photo but no sprite,
  run the matching pixel-art skill (`tree-pixel-art` for category=tree,
  `creature-pixel-art` for everything else). Output goes to
  `data/sprites_pixel/<slug>.png` and `data/creature_sprites_pixel/<slug>.png`,
  mirrored to `web/public/sprites/` and `web/public/creature_sprites/`.
- **Per-category sprite count targets.** Plants (0/767), insects with photos
  (~442 candidates), arachnids (~52 candidates), fungi (~15), molluscs (~10),
  amphibians/reptiles (small but symbolic) all need sprite coverage to make
  the encyclopedia feel comprehensive on the map.
- **Quality bar.** The sprite must be recognisable as the species — colour
  palette and silhouette match the photo. The pixel-art skill house style
  (chunky pixels, dark outline, left-lit shading) stays consistent.
- **Admin QA tool.** A new `/admin/sprites` page that lets you scroll
  through organisms side-by-side: real photo vs. generated sprite, with
  approve / reject / regenerate buttons. Rejected sprites queue for a
  second pass with a different prompt seed. The admin tool gates publish
  to `web/public/` until approved.
- **Approval persistence.** A `sprite_approved boolean` column on
  `organisms` (or a separate `sprite_reviews` table) records the QA state
  so re-runs of the pipeline don't re-show approved sprites.
- **Migration to set sprite_path.** Once approved, the sprite file lives
  on disk and the migration sets `organisms.sprite_path` so the map
  renderer picks it up.

**Why this matters:** the user's quality bar — "I want everything to be
recognizable" — means we can't just generate and ship blindly. The admin
QA tool turns the long-tail sprite work into a manageable review queue
rather than a "trust the AI" leap.

**Dependencies:**
- Photos must be backfilled first (C5 prerequisite — done in this round).
- The pixel-art skills already exist and work; the new piece is the
  orchestration + QA loop.

**Sub-steps (2026-06-30):**

1. **C3.D.1 — Sprite form library expansion. ✅ DONE (2026-07-01).**
   Landed 14 new creature body-plans on top of the existing 10:

   | New form | Covers | Status |
   |---|---|---|
   | `reptile` (lizard / turtle sub-modes via `--aspect`) | wall lizard, pond slider (~3) | ✅ |
   | `fish` | carp, perch, rudd (~5+) | ✅ |
   | `amphibian` | toads, frogs, newts (~7) | ✅ |
   | `large-mammal` | roe deer, wild boar, fox, badger (~5–7) | ✅ |
   | `aquatic-mammal` | otter, water vole, muskrat, coypu (~5) | ✅ |
   | `water-bird` | ducks, coots, geese, swans, grebes (~25–30) | ✅ |
   | `wading-bird` | herons, storks, spoonbill, cormorant, lapwing (~8–10) | ✅ |
   | `raptor` | falcons, buzzards, sparrowhawks, owls (~10–12) | ✅ |
   | `gull` | gulls + terns (~6–8) | ✅ |
   | `mollusc` (snail / slug sub-modes via `--aspect`) | ~25 | ✅ |
   | `dragonfly` | Odonata (~19) | ✅ |
   | `mushroom` (cap on stipe) | Agaricus, Boletus, Coprinus, Leccinum (~25) | ✅ Distinct from existing `fungus` (brackets/lichens only) |
   | `grasshopper` | Orthoptera (~14) | ✅ |
   | `lagomorph` | rabbits, hares (~3) | ✅ |

   **Deferred: `plant` form.** ~656 plant organisms is the single biggest
   gap, but needs 7+ sub-modes (flower / grass / rosette / umbel / spike /
   shrub / vine) to be honest — a whole batch on its own. Prioritized the
   iconic-species forms above per user direction (2026-07-01). Plants land
   in a later C3.D.1 continuation batch.

   **Feedback batch 2 (2026-07-01) — additional forms + form fixes:**
   - `rodent` form added — small body + big round ears + LONG THIN
     non-bushy tail. Covers Mus, Rattus, Apodemus, Microtus, Myodes,
     Muscardinus. Split off from `mammal` (which stays squirrel-shaped
     with a bushy tail).
   - `spider` legs redrawn as long jointed strokes with a clear knee
     bend + foot dot, so spider reads as spider not as a bug.
   - `fungus` form redrawn RIGHT-SIDE UP (top-down lobed patch) instead
     of the sideways bracket-on-trunk view. Both sub-modes now read as
     lichen / crust / shelf clusters seen from above.
   - Turtle and snail shells now use a CONTRASTING accent-hue ramp
     (`build_ramp(hue + offset, ...)`) so the shell visually separates
     from the body.
   - Reptile switched from side-view to TOP-DOWN with 4 splayed legs.
   - Gull switched to the iconic M-shape spread-wings silhouette so it
     reads at any saturation.
   - Bee proportions tightened (abdomen shrunk to match thorax).

   **Follow-up — priority photo backfill (2026-07-01, in progress).**
   The pipeline-C5 photo backfill (name conflict with roadmap C5 — the
   pipeline's `c5_*` files are unrelated to the alive-map milestone)
   ordered by `observations_count DESC NULLS LAST`, so the low-count
   tail of the roster was skipped. Firing a targeted 51-organism
   allowlist backfill for the user's priority categories: fish,
   amphibian, turtle, mollusc, mushroom, lagomorph, grasshopper,
   rodent, dragonfly, fungus/lichen, plus the top-10 spiders by obs
   count. Deprioritized: insects (~450 organisms) + plants (~656).

   **Follow-up — lizard / snake DB add (2026-07-01, later).** Zero
   Squamata species in the current taxonomy CSVs — they're missing
   from the DB entirely, not just missing photos. Constraint per user:
   only add species that have Amsterdam-geotagged observations on iNat
   / Waarneming. Candidate list to verify: `podarcis-muralis` (wall
   lizard), `natrix-helvetica` (barred grass snake), `anguis-fragilis`
   (slow worm), `zootoca-vivipara` (viviparous lizard), `lacerta-agilis`
   (sand lizard). Small GBIF-taxonomy fetch + insert once the
   Amsterdam-geotag filter is applied. Photos then follow via a
   second targeted backfill pass.

   Each new form is a ~30–80-line Python function in
   `.claude/skills/creature-pixel-art/scripts/render_creature_sprite.py`.
   Registered in the `FORMS` dict; argparse auto-picks up new names.

2. **C3.D.2 — `/sprites` library QA page. ✅ DONE (2026-07-01).** Hidden
   `/sprites` route (unlinked from nav, `robots: noindex,nofollow`).
   Layout: **sprite on the left, form metadata in the middle, real-organism
   photos on the right** — so a reviewer sees at a glance which species get
   grouped into each sprite form. Photos come from
   `web/public/creature_photos/` (older curated set) plus a
   `/organism_photos/[slug]` route handler that streams from
   `data/organism_photos/` (kept outside `web/public/` so Turbopack doesn't
   try to bundle 1.5k photos). Every form has a stable anchor id
   (`#new-reptile`, `#creature-bee`) for precise feedback.

3. **C3.D.3 — Bulk render pass.** Once C3.D.1 is fully complete
   (including plants) and QA'd on the /sprites page, run the matching
   skill against every organism with a photo but no sprite.

4. **C3.D.4 — Per-organism admin QA tool** (the original C3.D scope).
   `/admin/sprites` paged review queue; approve / reject / regenerate
   per organism; `organisms.sprite_approved` persists state.

**Not blocking:** can run in parallel with the alive-map work (C5–C11).
Each newly-approved sprite immediately starts appearing on the map for
its organism's category.

### C1.A — Unified wiki URL & layout *(post-Phase-B, follow-up)*
Surfaced 2026-06-29 after Phase B (web refactor to `organisms`). The DB and the
web data layer are unified, but the URL structure and page contents still split
by `/wiki/trees/*` vs `/wiki/creatures/*` — an artefact of the pre-unification
era. This follow-up brings the UX in line with the data model.

**Scope:**
- **URL collapse.** One route handles every organism: `/wiki/<slug>` (currently
  `/wiki/trees/<slug>` and `/wiki/creatures/<slug>`). Old routes 301 to the new
  shape so external links keep working.
- **Listing pages.** `/wiki` becomes the encyclopedia landing page with
  category-filter chips (trees, birds, mammals, insects, fungi, …); the
  existing `/wiki/trees` and `/wiki/creatures` become category-filter shortcuts.
- **Consistent page contents.** Tree wiki pages have "Combat flavor",
  "Real-world facts", "Living creatures on this tree". Creature pages have
  different sections. Pick one layout — hero, identification, where you'll find
  it, taxonomy, related organisms, gallery, sources — that gracefully handles
  every category. Move category-specific sections to opt-in blocks.
- **Cross-links.** Tree → creature lists become organism → organism via the
  `tree_genera` array (which is already there). Same for creature → tree.
- **Navigation.** Top nav's "TREES" / "CREATURES" links become one
  "Encyclopedia" entry (or stay as filter shortcuts). The encyclopedia,
  map (`/play`), and observations are the three primary surfaces.

**Why it's not blocking C5+:** the alive-map work doesn't touch the wiki
surface. But this should happen **before** C14 (Living dossier) so the dossier
redesign builds on the unified URL/layout instead of papering over the split.

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

**Open question — flocks / groups (dig into during this milestone):** many species
are almost never solo in reality. Parakeets in Vondelpark fly in flocks; sparrows,
starlings, long-tailed tits, coots with chicks, ducklings, etc. all travel in groups.
A single parakeet sprite drifting alone reads wrong. Things to figure out here:
- Add a `social_class` (or similar) tag on the organism — e.g. `solitary`, `pair`,
  `small-group` (3–5), `flock` (6–15), `large-flock` (20+). Default per category,
  override per species (parakeet → flock, robin → solitary, mallard → pair-or-family).
- One observation → render N sprites clustered around the obs point, all sharing the
  same `movement_class` path with small per-sprite offsets so the group moves
  *together* but not in lockstep (V-formation, loose cloud, line of ducklings).
- Performance budget: flocks multiply sprite count fast. Cap group size by zoom level
  and viewport density; degrade large flocks to a single "flock" sprite when zoomed
  out.
- Keep the "honest whimsy" rule — group size should be representative, not inflated
  for spectacle.

Decide the lightest version of this that still makes parakeets feel like parakeets
before locking the C9 path generators.

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
