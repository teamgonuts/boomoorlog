# Project Vision — Boomoorlog ("Tree War")

> **Direction change (2026-06-28):** pivoted from "two ZIP codes battle, marching armies
> clash" to "defend your own ~250m neighborhood against waves of spawns, classic
> tower-defense." This reverses the *marching-armies* decision locked 2026-06-27. Delivery
> plan lives in [ROADMAP.md](ROADMAP.md).

## Concept

A web app where you defend **your own Amsterdam neighborhood** in a **classic
tower-defense** game built from real open data. You enter your address; the game generates
a board from the **real world within ~250m** — the actual roads, canals, buildings, and
**trees** around you. Waves of enemies spawn and march your streets toward the center; the
**real trees are your defensive towers**.

Every board is real and personal: a leafy old street defends very differently from a sparse
new one, because the towers *are* the trees that actually grow there.

## User flow

1. User opens the website.
2. User enters **their Amsterdam address**.
3. The app geocodes the address and pulls the real world within ~250m: the trees (from the
   open trees dataset) and the roads / buildings / canals (from OSM).
4. It generates a **tower-defense board** — a walkable grid (roads = lanes; buildings +
   canals = blocked) plus a pixel-art render.
5. The neighborhood's real trees become the **defensive towers**, placed where they grow.
6. **Waves of enemies spawn** at the map edges and pathfind down the roads toward the
   center (the thing you defend). Towers in range fire. Enemies that reach the center
   "leak". Survive the waves → win.

## Core principles

- **Real data only.** The trees come from the Amsterdam open trees dataset (`bomen` /
  `stamgegevens`); the streets, canals, and buildings come from OSM. The board is a real
  place, not a designed level.
- **Classic tower-defense.** Stationary defenders (the trees) vs. moving attackers (the
  spawns) that pathfind along the streets toward a goal. Not the old marching-armies model.
- **One personal board per player.** Your address defines the board, so everyone defends
  somewhere different. Boards are generated **on demand and cached** (Amsterdam is bounded,
  so the cache fills in as people play — no upfront batch pre-render).

## Characters = tree genera (your towers)

- One **stat block per genus** (~50 playable archetypes), NOT per individual tree.
- Rarity tiers from the real frequency distribution:
  - **Common** (~15 genera): the everyday roster. 30 genera cover 95% of all trees;
    6 cover 50%.
  - **Uncommon** (~20 genera): 1,000–4,000 trees each (Sorbus, Gleditsia, Aesculus,
    Fagus, Liquidambar, Pinus, Ginkgo, Magnolia, Taxus…).
  - **Rare / Legendary**: the long tail — especially physically **big** or **exotic**
    species (Sequoia, Araucaria, Ginkgo, Metasequoia, etc.).

## Stats

Core tower stats per genus: **Attack, Range, Attack speed, Health**. Full design and trait
mappings live in [STATS.md](STATS.md). In the TD model the trees are stationary towers, so
Attack / Range / Attack speed map cleanly to a tower; the **enemies** carry move speed.

**Open design questions still to resolve:**
- Numeric scale per stat.
- AoE/splash as a 5th stat vs. a per-genus special ability (leaning: special ability).
- **What the enemies are** — pests / disease / chainsaws / urbanization. (TD pivot makes
  this the key open question.)
- Whether towers can take damage (does `Health` still apply now that trees don't move?).
- Do players **place / upgrade** towers, or are they fixed by the real trees?

## Data status / dependencies

- **Trees:** Amsterdam DSO API, dataset `bomen`, table `stamgegevens` (~323k trees, 298,734
  "currently living" after filtering stumps + to-be-felled). Seeded into Supabase.
- **Spatial query:** the board needs "trees within ~250m of an address" → **PostGIS**
  (`ST_DWithin` on a geography column built from the existing lon/lat). This revives PostGIS,
  which was deferred during the ZIP-only phase.
- **Geocoding:** address → coordinates (Amsterdam-only) is needed to center the board.
- **Map geometry:** roads / buildings / canals come from **OSM**, ingested offline and
  rasterized into the walkability grid (M5 in the roadmap).

## Working name

`boomoorlog` = Dutch for "tree war".
