# Creatures AMS 🌳🐦🍄

A single-purpose website that makes **Amsterdam locals fall in love with the wildlife on
their own street.** Open the page and a pixel-art map of the city is already alive —
real trees in their real places, real animals in their real habitats, real sightings
from this week — and clicking anything opens a beautiful little dossier about it.

Not a game. Not a tower defense. An ambient, whimsical, *truthful* window into the
living city, grounded entirely in real open data.

See [`memory/CREATURES_VISION.md`](memory/CREATURES_VISION.md) for the full concept and
[`memory/CREATURES_ROADMAP.md`](memory/CREATURES_ROADMAP.md) for the delivery plan
(phases C1–C19).

## Data sources

- **Amsterdam open trees** — DSO `bomen` / `stamgegevens` (~298k living trees).
- **iNaturalist** + **Waarneming.nl** — live creature observations (refreshed regularly).
- **OSM** — roads, canals, parks, buildings (habitat polygons for realistic placement).
- **KNMI** — live weather (Phase 1 weather mirror).
- **xeno-canto** — bird & creature sounds (Phase 1 sound layer).
- More to come as the unified encyclopedia takes shape (Phase 2).

## Repo layout

| Path | What it is |
|---|---|
| `memory/` | Design source of truth — vision, roadmap, stats, per-genus research. |
| `data/` | Raw datasets — **offline pipeline inputs only** (see note below). |
| `db/` | SQL migrations. |
| `pipeline/` | All offline Python — extract / fetch / generate / promote / seed scripts, plus the C3/C4/C5 milestone pipelines. |
| `web/` | Next.js app (the runtime — wiki + `/play` live map). Reads from Supabase. |

## Data pipeline (Python scripts in `pipeline/`)

Offline tools that prep data, derive metadata, and seed the database — they are **not**
part of the runtime app. Run from the repo root, e.g. `python3 pipeline/extract_trees.py`.

| Script | Purpose |
|---|---|
| `pipeline/extract_trees.py` | Pull living trees out of the raw Amsterdam dataset. |
| `pipeline/extract_creatures.py` | Build the curated creature roster. |
| `pipeline/fetch_observations.py` / `pipeline/seed_observations.py` | Pull iNat + Waarneming observations into Supabase. |
| `pipeline/generate_pixel_sprites.py` | Produce pixel-art sprites for trees and creatures. |
| `pipeline/promote_creatures.py` / `pipeline/backfill_creature_matches.py` | Curate observations into the creature roster. |
| `pipeline/seed_genera.py` / `pipeline/seed_trees.py` / `pipeline/seed_creatures.py` | Load Supabase tables. |
| `pipeline/c3*_*.py` / `pipeline/c4_*.py` / `pipeline/c5_*.py` | Milestone-specific batch builders, GBIF/iNat enrichment, aggregators (C3 labeling, C3.A long-tail, C3.B GBIF QA, C3.C trees, C4 common names, C5 photo backfill). |

## Architecture (current)

- **Database** — Postgres + PostGIS on Supabase. Source of truth (not CSVs).
- **Runtime** — Next.js (`web/`), client-side viewport-driven map (Leaflet + CARTO
  Voyager basemap), Supabase as backend.
- **Pipelines** — Python scripts produce data + sprites offline; the runtime never reads
  raw CSVs.

The original repo direction was a tower-defense game; large parts of the infra
(Supabase, geocoding, sprite pipeline, `/play` map code) were built for that and are
reused by Creatures AMS. Tower Defense is now parked — see
[`memory/TOWER_DEFENSE_VISION.md`](memory/TOWER_DEFENSE_VISION.md) and
[`memory/TOWER_DEFENSE_ROADMAP.md`](memory/TOWER_DEFENSE_ROADMAP.md).

## Live app

Currently deployed at **https://boomoorlog.vercel.app** (custom `creatures-ams.io`
domain coming in C14).

## Status

Foundation work done (database, app skeleton, address → neighborhood map, sprite
pipeline for trees + creatures, live iNat/Waarneming feed). Phase 1 of the Creatures
roadmap — "the map comes alive" — is the active workstream. Track in
[`memory/CREATURES_ROADMAP.md`](memory/CREATURES_ROADMAP.md).
