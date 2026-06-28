# Creatures — Roadmap to Production

> Living document. Source of truth for **what we ship** on the Creatures spin-off and
> **in what order** to get it production-ready.
>
> Last updated: 2026-06-28

---

## North star

A **live simulation of Amsterdam's creatures on a map**, rendered with pixel art. Not a
game, not tower defense — an ambient, living view of what's actually moving through the
city. Address-aware where useful (your neighborhood's creatures), but the core experience
is the map + the creatures + their behavior, presented honestly and beautifully.

Sister project to Boomoorlog, sharing the same Supabase/PostGIS backend and creature/tree
datasets. The TD roadmap (`TD_ROADMAP.md`) continues independently.

---

## Why a separate roadmap

Boomoorlog's roadmap (M1–M10+) is about the tower-defense game loop. Creatures is a
different product with a different shape: no waves, no win/lose, no battle engine. The
shared infra (Supabase, creature data, pixel sprites, `/play` map) means there's no need
for a separate repo — just a separate plan.

---

## Milestones to production

In intended order. Each is a gate, not a sprint estimate.

### C1 — Finalize creature behavior algorithms
What governs movement, clustering, idle vs active states, day/night activity, interactions
between species. Goal: behaviors that *read as alive*, not random walks, and that don't
misrepresent the real animal (a heron shouldn't behave like a swift). Lock the algorithm
set before tuning scheduling or UI on top of them.

### C2 — Finalize scheduling
When creatures appear, how density changes through the day/season, how the simulation
clock relates to real time. Decide: real-time mirror, accelerated loop, or scheduled
windows. Drives perceived liveliness and server load.

### C3 — Finalize trees/creatures page content
The wiki/info pages (`/wiki/creatures/[slug]`, tree pages). Lock copy, fields shown,
photo/sprite quality bar, sources/credits per entry. These are the "press the creature,
learn about it" surfaces.

### C4 — Custom domain (creatures-ams.io)
Register, point DNS, set up on hosting. Decide on subdomain split vs single site. After
this the project has its own identity, separable from boomoorlog dev URLs.

### C5 — Finalize mobile display
Mobile is the primary surface for an "Amsterdam creatures live map." Map controls, panel
sizing, sprite legibility at phone DPRs, perf on mid-range Android. Verify in real
browsers, not just dev-tools emulation.

### C6 — Business case (donation / €€)
Decide the model: donations only, optional Patreon/Ko-fi, paid tier for extras, sponsored
by a nature org, or nothing. Define what "production-viable" means financially (covers
Supabase + domain, or more). No code work — a decision doc.

### C7 — Distribution strategy
How people find this. Candidates: Amsterdam subreddits, nature/bird communities, local
press, gemeente partnerships, Instagram/TikTok of the pixel-art map, school/education
angle. Pick 2–3 channels and a launch sequence.

### C8 — Credits
Attribution page: data sources (Amsterdam open data, iNaturalist, OSM), photo sources
(per creature), pixel art credits, contributors, libraries. Required by most data licenses
and just the right thing to do.

### C9 — Performance
Final perf pass before launch. Clustering at low zoom, sprite atlasing, tile/marker
budgets on mobile, cold-load TTI, server cost under realistic traffic. Builds on M4's
viewport-driven `/play` work but holds it to a public-launch bar.

---

## Decisions still open

- Real-time vs accelerated simulation clock (C2)
- Donations vs paid vs sponsored (C6)
- Single domain vs subdomain split with boomoorlog (C4)
- Whether C1 behaviors are deterministic (seeded, replayable) or live-random

Defer these until their milestone — don't pre-decide.

---

## Relationship to Boomoorlog TD

- **Shared:** Supabase DB, creature data, tree data, pixel-art pipeline, `/play` map code.
- **Separate:** the TD game loop (`memory/TD_ROADMAP.md` M5–M10) does not block Creatures, and
  Creatures does not block TD.
- **Keep it simple:** if a feature only serves one product, build it in that product's
  surface, not in shared code.
