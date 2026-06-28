# Boomoorlog — Roadmap & Plan of Attack

> Living document. This is the source of truth for **what we're building and in what
> order**. Update it as milestones complete or decisions change. Game-design decisions
> still live in `memory/` (VISION.md, STATS.md, CHARACTERS.md); this file is about
> **delivery and architecture**.
>
> Last updated: 2026-06-28

---

## North star

You enter **your Amsterdam address** → the game builds a board from the **real world
within ~1km**: the actual roads, canals, buildings, and **trees** around you. Waves of
enemies spawn and march your streets toward the center of your neighborhood; the real
trees are your **defensive towers**. Classic tower-defense, generated from open data.
Built on a real **database source of truth** (not CSVs, not baked into HTML), structured
to scale toward real users over time.

See `memory/VISION.md` for the full game concept.

> **Direction change (2026-06-28):** pivoted from "two ZIP codes battle, marching armies
> clash" to "defend your 1km neighborhood against spawns, classic TD." This reverses the
> *marching-armies* decision locked in VISION.md on 2026-06-27 and revives PostGIS + adds
> OSM geometry (see below). VISION.md still describes the old model and needs a follow-up
> rewrite.

---

## Locked architecture decisions

These are settled. Change them only deliberately, and note the change here.

1. **Database = Postgres + PostGIS, hosted on Supabase.**
   Reason: the whole app is geospatial (every tree has coordinates; we query trees by
   postcode / radius). PostGIS does this natively. Supabase = hosted Postgres + free
   tier + auth-for-later, so it grows into real users without a rewrite.
   *Free at our scale* (~298k tree rows ≈ 30–60 MB, well under the 500 MB free tier).
   We do **not** load the raw 315 MB PC6 GeoJSON — trees already carry a postcode, so
   "trees in ZIP X" is a `WHERE` clause. Add (simplified) boundary geometry only if/when
   needed.

   **Direction change (2026-06-28):** the address-based pivot revives PostGIS *now* (M4) —
   "trees within 1km of an address" is `ST_DWithin`, not a postcode `WHERE`. We also now
   ingest OSM road/building/canal geometry for board generation (M5), which the M2 "don't
   load big geometry" stance had deferred. Still no PC6 boundary GeoJSON.

2. **The game engine is a pure, headless, framework-agnostic TypeScript module.**
   It takes plain data in (two armies + a random seed) and returns a battle log out.
   It imports **no** UI framework, touches **no** DOM, talks to **no** database.
   - Protects the engine from every frontend/DB decision.
   - Runs in plain Node → battle fairness is unit-testable with zero UI.

3. **Data contract between data layer and engine.**
   A stable TypeScript shape (`Unit`, `Army`) is the only thing the engine speaks.
   Stats and balance can change freely; the contract stays stable so DB and engine
   evolve independently.

4. **Deterministic, seeded RNG in the engine.**
   Same inputs → same battle. Enables replays, shareable results, and reproducible
   tests. Cheap now, painful to retrofit.

5. **Python scripts become an offline data pipeline**, not part of the app. They seed
   the database; the app never reads CSVs at runtime.

### Open / deferred decisions

- **Frontend / app stack** — *deferred until M3.* Candidates: Next.js (React+TS),
  SvelteKit (+TS), or a lighter Vite SPA + thin API. Safe to defer because M2 needs no
  frontend and the engine is headless. Decide right before M3.
- App hosting (Vercel/Netlify/GitHub Pages) — decide with the stack.
- Combat rules / numeric balance — firms up in M5–M6 (see `memory/STATS.md`).

---

## Milestones

Status keys: ✅ done · 🔲 not started · 🚧 in progress

### M1 — Character wiki ✅
Static genus wiki: stats, sprites, lore, per-genus maps.
- *Originally* generated into `docs/` by `build_wiki.py`. Both removed in M3 step 13
  (2026-06-28) once the Next.js `/wiki` route reached parity.

### M2 — Data foundation (the "source of truth") ✅
Stand up the database and make it the single source for trees and genera.

**M2 locked decisions (2026-06-28):**
- Plain Postgres on Supabase — **PostGIS deferred** (trees already carry postcodes, so
  spatial queries aren't needed yet).
- **No separate `postcodes` table** — no boundary geometry until a milestone needs it.
- **No backend framework** — Supabase's auto-generated REST API is the backend for now.
  Decision revisited at M3 only if Supabase's built-in API can't do the job.
- **Seed pipeline in Python** (matches existing scripts).
- **Import all CSV columns** into `trees`; flag game-relevant ones, ignore the rest at
  query time.
- **`Unit`/`Army` TypeScript contract deferred** to M6 — not part of M2.

**Schema (two tables, one relationship):**
- `genera` (~56 rows) — archetype stat blocks: `slug PK`, latin/dutch/display names,
  5 stats (attack, range, health, attack_speed, move_speed), `world_rarity_multiplier`,
  `personality`, `tree_count`, `sprite_path`, `lore`.
- `trees` (~298,734 rows) — census: `id PK`, `genus_slug FK→genera.slug`, all 24
  source columns from `amsterdam_trees_zip.csv` (postcode6, postcode4, lon/lat, rd_x/y,
  height_class, diameter_class, planting_year, owner, manager, location, …).
- Indexes: `(postcode4)`, `(postcode6)`, `(genus_slug)`.

**Step-by-step deliverables (do in order, check off as completed):**
- [x] **1. Supabase project** — free-tier project in `eu-central-1` (Frankfurt).
      Running Postgres 17.6.
- [x] **2. Credentials wired locally** — `.env` at repo root (gitignored) holding
      `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`. `.env.example`
      committed as template. `psql` connection verified.
- [x] **3. Schema SQL** — `db/001_schema.sql` creates `genera` and `trees` tables with
      `genus_slug` FK. Includes individual-tree variance support: `trees.height_m` /
      `diameter_cm` (parsed midpoints) + `genera.avg_height_m` / `avg_diameter_cm`
      (baselines). Applied to Supabase 2026-06-28.
- [x] **4. Indexes SQL** — `db/002_indexes.sql` adds the three indexes on `trees`
      (`postcode4`, `postcode6`, `genus_slug`). Applied to Supabase 2026-06-28.
- [x] **5. Genera seed** — `seed_genera.py` loads 167 genera (55 fully stat-blocked
      + 112 sparse for FK coverage). Shared derivation logic extracted into
      `pipeline/stats.py` — used by both `seed_genera.py` and `generate_characters.py`.
- [x] **6. Trees seed** — `seed_trees.py` bulk-loads all 298,734 rows via `COPY`.
      Parses height/diameter class strings into `height_m` / `diameter_cm` at seed
      time. Two corrupt `planting_year` values dropped to NULL (20141990, 19921).
- [x] **7. Backfill genera aggregates** — `db/003_backfill_genera.sql` populates
      `tree_count`, `avg_height_m`, `avg_diameter_cm` from `trees`. Re-runnable.
- [x] **8. Verification queries** — all pass:
        Tilia stats present; 1079 has Tilia=801, Ulmus=631, Acer=347 (top 3); 86%
        of trees have parsed height, 29% have parsed diameter (matches STATS.md
        coverage notes); 103 distinct postcode4 values; individual-variance demo:
        tallest Tilias in 1079 are 21m vs genus avg 12.9m → ~1.6× modifier.
- [x] **9. Demote CSVs** — note added in repo root `README.md`: CSVs are raw
      pipeline inputs only; app reads from Supabase.

### M3 — App skeleton & code-quality reset 🔲
Replace the Python static-site generator with a proper app reading from Supabase.

**M3 locked decisions (2026-06-28):**
- **Frontend stack: Next.js (App Router).** Chosen because user knows React already
  — Next.js is React + file-based routing + server components, so almost zero new
  concepts. Server components fetch from Supabase directly (no separate API layer).
- **Hosting: Vercel.** Zero-config deploys from the GitHub repo on push to `main`,
  free tier covers our scale, native Next.js integration.
- **CSS: Tailwind.** Faster iteration than CSS modules; massive Next.js+Tailwind
  ecosystem; low commitment (easy to rip out if user hates it after first page).
- **TypeScript types: auto-generated** from Supabase schema via
  `supabase gen types typescript --linked > web/types/supabase.ts`. Editor knows
  every column; types stay in sync with DB.
- **Test framework: Vitest.** Fast, Vite-native, minimal ceremony.
- **Linter/formatter: ESLint + Prettier** (Next.js built-in defaults — no plugins
  beyond what `create-next-app` ships).
- **App location: `web/` subfolder in this repo.** Monorepo-light. Pipeline /
  data / db live at repo root; the app lives under `web/`.
- **Old `docs/` static wiki stays online until new app reaches parity**, then
  deleted (and `build_wiki.py` removed from the pipeline).

**Step-by-step deliverables (do in order, check off as completed):**
- [x] **1. Vercel account** — created via GitHub OAuth, hooked to `teamgonuts/boomoorlog`.
- [x] **2. Scaffold Next.js app** — `create-next-app` in `web/` with TS + Tailwind
      + App Router + ESLint. Booted on `localhost:3000`. Node upgraded to v26.
- [x] **3. Supabase client wired** — `@supabase/supabase-js` installed.
      `web/.env.local` (gitignored) holds `NEXT_PUBLIC_SUPABASE_URL` +
      `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Client wrapper at `web/lib/supabase.ts`.
- [x] **4. Hello-world DB page** — `/test` route reads `select count(*) from
      genera` and renders 167. Verified live in the browser preview.
- [x] **5. TS types** — `web/types/supabase.ts` hand-written (not auto-gen).
      Supabase CLI's `gen types` needs Docker/Podman which is denied territory;
      for a 2-table schema it's faster to maintain by hand. Wired into the client
      as `createClient<Database>`.
- [x] **6. Dev experience** — ESLint from create-next-app passes clean. Vitest +
      Prettier deferred until a real need arises (keep-it-simple).
- [x] **7. Genus list page** — `/wiki` lists all 55 stat-blocked genera in a
      table sorted by tree count. Each row links to the detail page.
- [x] **8. Genus detail page** — `/wiki/[slug]` renders sprite + 5-stat grid +
      personality + avg height/diameter + full lore (via react-markdown).
      `data/sprites_pixel/` and `data/tree_pics/` copied into
      `web/public/sprites/` + `web/public/photos/` (Vercel needs them
      inside the app root). Source-of-truth copy remains in `data/`.
- [x] **9. Wiki home / index** — `/` groups all 55 genera into archetype
      sections (Bruiser / Juggernaut / Skirmisher / Support) with sprite cards
      and legendary stars. Archetype computed live in `web/lib/archetype.ts`
      from current DB stats (no precomputed column = no re-seed when formula
      changes).
- [x] **10. Reusable components** — `<Sprite>` extracted into
      `web/components/Sprite.tsx` (used in home cards and detail header). Other
      patterns left inline — repetition wasn't strong enough to justify more
      extraction yet.
- [x] **11. Visual pass** — light leafy theme (`stone-50` bg, `stone-900` fg,
      `emerald-700` accents), Geist sans, top nav with Boomoorlog logo + Wiki
      link, pixelated sprite rendering, stat cards with help text. Adequate as
      a baseline; iterate when there's a feature reason to.
- [x] **12. Deploy to Vercel** — live at https://boomoorlog.vercel.app. Root
      Directory set to `web/`. `NEXT_PUBLIC_SUPABASE_URL` + `_ANON_KEY` set in
      Vercel env. Auto-deploys on push to `main`.
- [x] **13. Deprecate old `docs/`** — `docs/` removed, `build_wiki.py` deleted
      (its sole purpose was generating `docs/`), README pipeline + repo-layout tables
      updated, "Live app" section added pointing at https://boomoorlog.vercel.app.

### M4 — Address → neighborhood map ✅  *(was: zipcode → neighborhood map)*
User types their Amsterdam address → sees the real trees around them on a map. The first
demoable "your neighborhood" moment, before any board or combat exists.

**Pivot note:** address-based (~1km radius), not zipcode. This needs real spatial queries,
so **PostGIS is back on** (the M2 deferral assumed zip-membership `WHERE` clauses; "trees
within 1km of an arbitrary point" is `ST_DWithin`).

**M4 locked decisions (2026-06-28):**
- **Geocoder: OpenStreetMap Nominatim.** Free, no API key, open-data theme, well within
  the 1 req/sec rate limit at our scale. Proxied through a Next.js API route so the User-
  Agent header (required by Nominatim) is set server-side.
- **Radius: 100 m, hard-coded.** Started at 1 km, came down to 250 m, then 100 m
  for performance — Leaflet DOM markers (one `<img>` per tree) get sluggish past
  a few hundred. 100 m gives ~80–250 trees in dense Amsterdam, ~30–100 elsewhere,
  with a "your block" zoom level. Becomes user-tunable when M5 needs it.
- **Map library: Leaflet** + the dark CARTO basemap (matches the wiki's dark theme).
  Loaded client-side only (Leaflet touches `window`).
- **Route: `/play`** (linked from `/`'s top nav). The wiki at `/` stays as the browse view.
- **Server vs client.** Address input + geocode = server action / route. Map + markers =
  client component. Trees fetched server-side and passed as props.
- **No board / wave logic in M4.** Map + summary only. M5 starts board generation.

**Step-by-step deliverables (do in order, check off as completed):**
- [x] **1. PostGIS extension + geom column** — `db/004_postgis.sql` enables
      PostGIS, adds `trees.geom geography(Point, 4326)`, backfills 298,710 rows
      from lon/lat, GiST index. Idempotent.
- [x] **2. Spatial RPC function** — `db/005_trees_within.sql` defines
      `trees_within_radius(lat, lng, radius_m default 250)` using ST_DWithin.
- [x] **3. Verify spatial query** — Dam Square (52.3731/4.8926) returns 3,256
      trees within 1km; top genera Ulmus (2513), Tilia (157), Platanus (123).
- [x] **4. Nominatim proxy** — `web/lib/geocode.ts` (shared helper) +
      `web/app/api/geocode/route.ts` (REST). User-Agent set, NL-only,
      Amsterdam-bbox bounded.
- [x] **5. `/play` route** — server component with address form + result panel.
      Pages through Supabase's 1000-row cap to get the full result set.
- [x] **6. Leaflet map** — `web/components/PlayMap.tsx` (`"use client"`), dark
      CARTO basemap, gold radius circle, red center pin, sprite icons per tree.
- [x] **7. Summary panel** — top-5 genera with sprite, Dutch name, count, %,
      archetype. Rarity-tinted left border.
- [x] **8. Home → /play link** — top nav now has "Play" + "All trees".
- [x] **9. Deploy + verify on prod** — live at
      https://boomoorlog.vercel.app/play; verified Dam 1 returns 3,161 trees
      across 37 genera.

### M4.5 — Living map ✅
"Make the map *feel alive* before we build the real game." Two random creature
sprites fly tree-to-tree on `/play`, ignoring streets and physics. Pure visual
demo, no game logic, no pathfinding. Cheap, demoable, validates the animation
tech path (Leaflet marker + requestAnimationFrame + CSS transform).

**Locked decisions (2026-06-28):**
- 2 creatures at a time, picked uniformly at random from the `creatures` table
  on each page load. Variety per visit.
- Straight-line tree → tree, linear lat/lng interpolation. No pathfinding.
- ~6 m/s, scaled by hop distance (min 800ms per leg).
- 600 ms pause on each tree before next hop.
- Sprite faces direction of travel: rotate for east-ish moves, mirror
  (`scaleX(-1)`) for west-ish moves so birds never look upside-down.
- Single Leaflet `divIcon` per creature, animated with `requestAnimationFrame`
  + `marker.setLatLng()`. No new dependencies.

**Done:**
- `pickRandom()` picks 2 creature slugs server-side at /play render.
- `startCreatureFlight()` in `web/components/PlayMap.tsx` runs the RAF loop,
  swaps from/to on arrival, manages rotation. Returns a stop() for cleanup.
- `.creature-flying` styles in globals.css (transparent divIcon shell, inner
  `<img>` constrained + smoothed transform transitions on rotation).

### M5 — Board generation (OSM → playable grid) 🔲  *(new — the map-translation milestone)*
Turn the real world inside the 1km box into a tower-defense board. Two **separate layers
on one grid**: a *walkability/collision* layer (data) and a *pixel-art* layer (cosmetic).
Build & test the grid headless; treat the art as a swappable skin (same discipline as the
engine/renderer split below).

**Locked decisions (2026-06-28):**
- **On-demand + cache, not batch pre-render.** Generate a board the first time an address
  is requested, then cache it. Amsterdam is bounded, so the cache fills in as people play
  — we get the pre-render payoff without building a batch pipeline we might throw away.
  (Simplify call, confirmed with user.)
- **Collision layer:** roads = walkable lanes; buildings + canals = blocked. Pathfinding
  reads *only* this layer.
- **Pixel-art layer:** cosmetic 8bitcity-style render on top (see `memory/INSPIRATION.md`).
  Can lag the collision layer — it's a skin, not a dependency.

**Deliverables**
- [ ] OSM ingest for Amsterdam: roads (lines), buildings (polygons), water/canals
      (polygons). Offline pipeline step, like the tree seed.
- [ ] Rasterize the 1km box into a tile grid → per-tile walkable/blocked from OSM geometry.
- [ ] Spawn points + goal: enemies enter from map edges along roads and march toward the
      address center (the thing you defend). [open: exact spawn/goal placement rules]
- [ ] Board cache keyed by address/box so repeat plays don't re-generate.
- [ ] Pixel-art tile render of the board (cosmetic layer).

### M6 — Tower roster (neighborhood trees → towers) 🔲  *(was: army builder)*
Turn the trees the M4 query returned into placeable defensive **towers**: aggregate /
attach stats, position them where they actually grow on the board.
**Deliverables**
- [ ] Pure function `neighborhood trees → Tower[]` (emits the data contract).
- [ ] Towers sit at their real coordinates on the M5 grid.
- [ ] Tower-preview reusing wiki components.
- [ ] [open: do players place/upgrade towers, or are they fixed by the real trees?]

### M7 — TD wave engine (headless, no graphics) 🔲  *(was: battle engine)*
Deterministic tower-defense simulation. No rendering — logic + event log only. Enemies
spawn in waves, **pathfind along roads** toward the goal; towers in range fire; enemies
that reach the goal "leak". Seeded RNG → same inputs, same run.
**Deliverables**
- [ ] Pathfinding over the M5 walkability grid (e.g. A* / flow field along roads).
- [ ] Simulation module (pure TS, seeded RNG): waves, enemy movement, tower targeting +
      firing, damage, leaks, win/lose.
- [ ] Unit tests for fairness/balance — run many boards headless in Node.
- [ ] Given a board + roster + seed → reproducible tick-by-tick event log + result.
- [ ] [open: what are the enemies? pests / disease / chainsaws / urbanization — STATS.md
      follow-up.]

### M8 — Board & battle visualization (Pixi.js) 🔲  *(was: battle visualization)*
Render the M7 event log on the M5 pixel board — enemies marching the streets, tree-towers
firing, hits, leaks, win/lose banner.
**Deliverables**
- [ ] Canvas renderer driven by the event log, on top of the board render.
- [ ] Playback / speed controls.

### Engine ↔ Renderer contract (spans M7–M8)
Same split, retuned for TD: the **engine** (M7) decides *what happens*, the **renderer**
(M8) decides *how it looks*, joined by an event log. The engine records *facts only*
(spawn / move / fire / hit / death / leak / result with `tick` + positions); it never
draws. All the juice (sprite tweens, muzzle flashes, leak flashes, win banner) lives in
the renderer. Design the event shape with M8 in mind so there's enough detail to animate.

```ts
type Tower = { id; genus; atk; range; atkSpeed; x; y };   // a real tree, placed
type Enemy = { id; kind; hp; speed };                     // a spawn
type SimEvent =
  | { tick; type: "spawn";  id; kind; x; y }
  | { tick; type: "move";   id; x; y }
  | { tick; type: "fire";   from; to }
  | { tick; type: "hit";    id; hp }
  | { tick; type: "death";  id }
  | { tick; type: "leak";   id }                           // reached the goal
  | { tick: -1; type: "result"; outcome: "win" | "lose"; leaked: number };
```

Payoffs unchanged: deterministic & replayable (share link = `address + seed`), balance
testable headless in Node, and the frontend stays swappable.

### M9 — Full playable loop (v1 playable) 🔲  *(was M8)*
Enter your address → board generates → waves attack → you defend → win/lose. First version
that's "the game."

### M11 — Living creature roster (auto-discover from observations) 🔲

**Goal:** every species sighted enough to matter gets promoted from a raw row in
`observations` to a real `creatures` entry, with a Wikipedia blurb, a photo, and a
generated pixel sprite — appearing on the wiki the next time the page is rendered.
Builds directly on the /observations data pipe (already live with ~12k obs).

**Promotion rule (locked):** a species becomes a creature when it has **≥3 sightings
in the last 30 days** AND isn't already a creature (by exact Latin or genus-token match
to existing `creatures.latin_name`). Genus-rollup means `Bombus pascuorum` resolves to
the existing `Bombus` creature without creating a new row.

**Steps:**

1. **Schema bump** — add to `creatures`:
   - `source text not null default 'curated' check (source in ('curated','auto_observed'))`
   - `promoted_at timestamptz` (null for curated, set at promotion time)
   - `taxon_group text` (so we can show "Beetle"/"Moth"/"Bird" without a join)
   - `wikipedia_summary text` (the M12-pending lore; Wikipedia REST API fills it now)
   - `observations_count int` (denormalised 30-day count for "recently spotted" sort)

2. **Match backfill** — one-shot SQL/script: link every existing observation to an
   existing creature where the genus-token or exact-name match hits. Drops the
   ~330 curated creatures into use immediately; everything else stays unmatched and
   feeds the promotion queue.

3. **Promotion job** (`promote_creatures.py`, runnable on demand): finds species
   ≥3 obs / no creature yet, then per candidate:
   - Pick best common_name (most-common across its observations).
   - Find a usable photo: search iNat for a CC-BY/CC-BY-NC/CC0 photo of the species
     (across ALL obs, not just our 30-day window) → fall back to iNat taxon default →
     fall back to Wikipedia image → otherwise flag `sprite_pending: true` and skip
     sprite for this run.
   - Fetch Wikipedia summary (`/api/rest_v1/page/summary/{title}`, free, no key).
   - Generate slug from Latin name; insert creature row with `source='auto_observed'`,
     `promoted_at=now()`, taxon_group from the source obs.
   - Generate sprite via the `creature-pixel-art` skill from the chosen photo.
   - Update all matching observations to point at the new `creature_slug`.
   - **Hard cap: 20 sprites per run** to bound cost/time.

4. **Wiki updates** — on `/wiki/creatures`:
   - "Recently spotted" badge on cards whose `promoted_at` is within 7 days.
   - New sort option "Recently spotted" alongside the current alphabetical default.
   - Auto-observed creatures get a lean detail page template: photo, taxonomy,
     Wikipedia blurb, observations count + link to the /observations map filtered to
     that species. Curated detail pages stay as-is (the M12 milestone unifies later).

5. **Map & AreaPanel integration on `/play`** — without this, auto-promoted creatures
   exist in the DB but never show up in-game:
   - **Sprite/photo file placement** — promotion job must drop the generated sprite to
     `web/public/creature_sprites/{slug}.png` AND a copy of the source photo to
     `web/public/creature_photos/{slug}.{ext}` (the paths the existing
     `PlayMap.tsx` + `AreaPanel.tsx` already expect). No frontend changes needed for
     file references — only the file-write side.
   - **AreaPanel filter widening** — currently `PlayClient.tsx:131` filters creatures
     by `tree_genera` overlap with neighborhood trees. Auto-promoted creatures have
     empty `tree_genera`, so they'd never appear. New rule (union):
     a creature shows in the widget if **either** (a) its `tree_genera` overlap the
     neighborhood (existing curated path), **or** (b) it has at least one observation
     within the current map bounds. (b) needs a small spatial query — easy with the
     `observations` GiST index already in place. Net result: curated creatures keep
     their tree-based association; auto-promoted ones surface in any neighborhood
     where they were actually seen, and nowhere else.
   - **Flying-creature pool** — `creaturesForMap` in `/play/page.tsx` passes ALL
     creatures to `PlayMap`, which randomly picks 5 to animate. Add a "has a usable
     sprite + photo" guard at server-render time (skip creatures still in
     `sprite_pending`) so we never animate a creature with a broken `<img>`.
   - **The /observations live map already includes auto-promoted creatures by
     definition** (they were promoted *from* observations), so no change needed there.

**Out of scope (deferred):**
- Daily cadence + cron → **M13**.
- Defining what creature/tree page content *should* look like long-term → **M12**.
- Stats (Attack/Range/Health) for auto-promoted creatures → wait on enemy mechanics.

**Acceptance:** schema migration applied · backfill linked all matchable existing
obs · `python promote_creatures.py` runs end-to-end on the current 12k obs and the
new creatures show up on `/wiki/creatures` with badges and lean detail pages · the
sprite cap is respected · no API rate-limit errors · **on `/play` a newly-promoted
creature whose observations fall inside the visible map appears in the AreaPanel
"Creatures" tab AND can be picked for the flying-creature animation** (with its
sprite + photo rendering correctly from `/creature_sprites/` + `/creature_photos/`).

### M12 — Finalise trees/creatures page content 🔲

**Goal:** decide what a tree page and a creature page *should* contain end-to-end.
The current curated creature pages have rich lore from `memory/characters/*.md`;
auto-promoted creatures from M11 land with just a Wikipedia blurb. This milestone
pins down the content spec so both tiers eventually converge (or stay deliberately
different).

**Open questions to resolve here:** what lore is required vs. optional · how rich
should taxonomy/identification info be · do we show conservation status / native
vs introduced · what relationship to trees do we surface (which trees they live on,
which they damage) · how do auto-promoted and curated entries visually differ ·
do creatures need stat blocks for the wiki even if the game doesn't show them yet.

**Deliverable:** a content spec doc in `memory/` + a layout pass on the existing
templates. No new auto-data pipelines.

### M13 — Finalise scheduling 🔲

**Goal:** the M11 promotion job runs automatically without me typing a command.

**Scope:**
- Daily 03:00 Europe/Amsterdam cron (using the `schedule` skill or a Supabase
  scheduled function) that:
  1. Incrementally fetches the last 24h of observations (`seed_observations.py --days 1`).
  2. Runs the promotion job (`promote_creatures.py`).
  3. Surfaces a summary on next session (new species count, new sprites generated,
     any failures).
- Manual `--run-now` flag preserved for ad-hoc invocation.
- Failure handling: a single failed sprite or Wikipedia lookup shouldn't kill the
  whole run; failures are logged and re-tried next day.

**Out of scope:** anything beyond once-a-day cadence (no event-driven triggers, no
realtime ingest).

**Acceptance:** the daily run has succeeded autonomously for at least 3 consecutive
days, with new creatures appearing on the wiki the morning after they cross the
3-sighting threshold.

### M10+ — Later (the DB makes these cheap) 🔲  *(was M9+)*
Neighborhood-vs-neighborhood competitive mode (the old zip-vs-zip North star, now an
optional mode) · shareable results · user accounts · leaderboards / neighborhood rankings.

---

## Why this order
- **Map (M4) early** → a satisfying, demoable thing (your own neighborhood's trees) well
  before the board or combat exists.
- **Board generation (M5) before combat** → the walkability grid is the foundation
  everything pathfinds on; get it right before towers and waves depend on it.
- **Engine logic (M7) before graphics (M8)** → test that defending is fair/fun without
  spending effort on art-driven rendering.
- **Headless engine + data contract** → no early decision boxes in the eventual game.
