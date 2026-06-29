# Creatures AMS — Vision

> Living document. The source of truth for **what we're building and why**.
> Delivery plan lives in [CREATURES_ROADMAP.md](CREATURES_ROADMAP.md).
>
> Last updated: 2026-06-29

---

## Concept

A **single-purpose website that makes Amsterdam locals fall in love with the wildlife on
their own street.** You open the page and a pixel-art map of the city is already alive —
trees in their real places, animals in their real habitats, observations from this week —
and clicking anything you notice opens a beautiful little dossier about it.

Not a game. Not a tower defense. An ambient, whimsical, *truthful* window into the living
city, grounded entirely in real open data (Amsterdam open trees, iNaturalist,
Waarneming.nl, OSM, KNMI, xeno-canto, and more as we add them).

## Audience

**Amsterdam locals.** People who walk past these trees and birds every day but have never
stopped to know what they are. The site exists to nudge them outside to look. Desktop is
the v1 surface; mobile follows in a dedicated polish milestone, but no design decision
should lock phones out later.

## North star

You land on `creatures-ams.io` and the map is already *doing things*. A heron stalks a
canal edge. A swift loops over a square. A bumblebee bobs around a Linde. You think
*"wait — what's that?"* — click — and an opinionated, well-sourced dossier opens. The
clock, the season, and the weather on the map are all real. The creatures you see are
the species being reported *right now* by iNaturalist and Waarneming users in Amsterdam.

You close the tab. A few hours later, walking down your street, you look up.

## Core principles

- **Real data, always.** Every tree, every creature, every observation is from open data.
  Nothing invented. Fiction lives only in *how* we render it (pixel art, behavior
  animation, voice in the copy).
- **Single purpose.** One site, one job: make the visitor want to go outside and look.
- **Honest whimsy.** The pixel art and animation should charm without misrepresenting the
  animal. A heron behaves like a heron. A swift never lands. A fish stays in the water.
- **Encyclopedia, not zoo.** Trees, creatures, fungi, lichens — all the same kind of
  *thing* on this site: an organism with a sprite, a wiki page, and a place on the map.
- **One unified roster.** The current split between "trees" and "creatures" is an artefact
  of how we built it, not how the world is. The data model and UI should treat them as one
  family of organisms, with category as a tag.
- **Source-extensible.** Today: Amsterdam open trees + iNaturalist + Waarneming. Tomorrow:
  whatever new dataset adds another layer of life. Adding a source should be a Tuesday
  task, not a refactor.
- **Desktop-first, mobile-aware.** Build for big screens but never make a decision that's
  hard to bring to phones later.
- **Keep it simple** (project-wide rule). Lightest option that delivers the vibe.
- **Respect the sources.** Every dataset and every photographer gets credit. The site
  routes value back to local conservation.

## User flow

1. Visitor opens `creatures-ams.io`. The map is already showing Amsterdam — atmospheric,
   alive, with real recent sightings.
2. The browser prompts for location (opt-in). Allowed → map centers on the visitor.
   Denied → the page gently nudges them to enter their address. Either path → the visitor
   ends up with their own neighborhood at the centre.
3. They notice something — a heron, a bumblebee, an old Linde — and click. A dossier
   opens: photo, recent local sightings, a one-line story, how to identify it, where it
   lives, when it's most visible.
4. They poke around. Maybe they enable bird sound. Maybe they hit "surprise me." Maybe
   they bookmark their own block. Maybe they tap "donate to conservation."
5. They close the tab. The city outside has changed for them, even a little.

## The unified organism encyclopedia

Trees, creatures, fungi, lichens, and whatever else we add will share **one data model
and one wiki**:

- One canonical `organisms` table (or equivalent) replaces today's `genera` + `creatures`
  split.
- Three columns drive everything that follows: `category` (tree, bird, mammal, insect,
  fungus, lichen, …), `habitat_class` (where it appears on the map), `movement_class`
  (how it moves, if at all — `none` for fungi and trees, plus a small set of behavior
  archetypes for everything else).
- Each organism also has: sprite, real photo(s), Latin + Dutch + English names, lore,
  source attributions.
- Every map marker points at one organism in the encyclopedia.
- Every observation (iNat, Waarneming, future sources) hits the map and resolves — best
  effort — to one organism row.
- New source feeds add rows + observations, not schemas.

The schema is **the organising layer** the entire alive map reads from. The habitat and
movement vocabularies are small, fixed sets — each value maps to one behavior
implementation in code, and a per-category default keeps most rows tagged without
hand-research. A dedicated labeling pass tags the long tail.

Re-shaping the schema is the first foundational phase; the map and wiki sit on top of it
afterwards.

## The living map (layered atmosphere)

The map's aliveness is **layered** — each layer ships independently, in roughly visible-
impact order, *after* the encyclopedia is in place. The full ladder is in the roadmap;
the visible deliverables are:

1. **Habitat-realistic placement** — birds in trees, fish in water, squirrels in parks,
   herons stalking canal edges. Reads `habitat_class` from each organism row.
2. **Idle motion** — sprites bob, sway, blink. Signs of life, no pathing yet.
3. **Day / night cycle** — keyed to real Amsterdam local time; nocturnal species appear
   after dark.
4. **Seasonal skin** — palette + pixel particles per season (blossom, leaves, snow).
5. **Smart per-species movement** — one behaviour per `movement_class` value
   (tree-flitter, water-edge-stalker, sky-looper, park-roamer, water-drifter, flower-
   bobber, urban-walker, …). Plausible biology, still readable as pixel art.
6. **Sound** — click → real species call (xeno-canto). Off by default; one-time prompt;
   choice persists.
7. **Weather mirror** — KNMI live conditions drive subtle effects (drizzle, wind shake).

After this ladder, the map's atmosphere is essentially done. The "house style" stays
pixel-art and minimalistic throughout — we incrementally enhance, never abandon, the
visual language.

## Rewards for clicking around

- **Living dossier.** Every organism page surfaces real recent observations near the
  visitor ("seen N times this week within 1km").
- **Real-sighting trail.** Click a creature → photo gallery from actual iNat / Waarneming
  observations nearby.
- **My block.** A permanent personalised URL for the visitor's address (`/b/<hash>` or
  similar). Bookmark-able. Shareable.
- **Surprise me.** A button that pans/zooms to a delightful spot in Amsterdam right now.
- **Hotspots & rarity radar.** Soft heatmap of recent biodiversity; rare-species flags.
- **Cross-links.** A Linde page lists creatures observed *on* Tilia trees. A bird page
  lists the genera it's been seen in.

## Launch, distribution, and good citizenship

The project isn't done at "feature complete." It ships in a way that respects its data
sources and finds its audience:

- **Custom domain** — `creatures-ams.io`.
- **Credits & attribution.** Required by most data licenses, and just right: Amsterdam
  open data, iNaturalist, Waarneming.nl, OSM, KNMI, xeno-canto, every photo contributor,
  every library, every human contributor.
- **Conservation donation flow.** A clean, gentle way for visitors to donate to a named
  local Amsterdam conservation organisation. Not pushy, not blocking. We are a
  passthrough; the money goes to the org.
- **Distribution strategy.** Pick 2–3 channels (local subreddits, NL birding/nature
  communities, IG / TikTok of the pixel-art map, gemeente partnerships, local press,
  schools) and a launch sequence.
- **Mobile polish.** Even though desktop is v1, most locals will eventually open this on
  a phone.
- **Performance pass.** Final perf bar before public launch.

## Relationship to Tower Defense

Tower Defense is **parked**. See [TOWER_DEFENSE_VISION.md](TOWER_DEFENSE_VISION.md) and
[TOWER_DEFENSE_ROADMAP.md](TOWER_DEFENSE_ROADMAP.md). The two products share
infrastructure (Supabase, sprite pipeline, geocoding, `/play` map code) but only Creatures
AMS is shipping. If TD ever revives, it can sit on top of the unified encyclopedia and
existing infra without rewriting.

## Open questions

- **Geolocation denial fallback** — full Amsterdam ambient view, or block until an
  address is typed? *(Lean: ambient.)*
- **Day/night cycle: real-time mirror vs accelerated loop.** *(Lean: real-time mirror;
  accelerated loops feel game-y.)*
- **Where does the unification milestone slot?** Strictly speaking the map ladder doesn't
  need it, but the wiki and click-anything UX do. *(Lean: between the visual map work and
  the rewards-for-clicking work.)*
- **Conservation partner** for the donation flow.
- **Distribution channel mix.**
- **Sub-domain vs single domain** for wiki vs map vs root.

Defer until the milestone surfaces them. Don't pre-decide.

## Working name & identity

**Creatures AMS** — `creatures-ams.io`.
