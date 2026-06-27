# Project Vision — Boomoorlog ("Tree War")

## Concept

A web app where two Amsterdam ZIP codes battle each other **tower-defense style**,
using the **real trees** that grow in each ZIP code as the combatants.

The whole experience is data-driven and runs as an **automated simulation** — the
only user input is the two ZIP codes. There is **no in-match interaction**.

## User flow

1. User opens the website.
2. User enters **their ZIP code** (an Amsterdam postcode).
3. User enters an **opponent ZIP code** (another Amsterdam postcode).
4. The app looks up every real tree in each ZIP code from the dataset.
5. A tower-defense battle simulation runs automatically, the trees fight, and a
   winner is shown.
6. That's it — no clicking towers, no upgrades mid-match. Watch the simulation.

## Core principles

- **Real data only.** Every combatant comes from the Amsterdam open trees dataset
  (`bomen` / `stamgegevens`). The number, species mix, age, and size of trees in a
  ZIP code directly determine that side's army. A leafy, old neighborhood should
  feel different to a sparse new one.
- **Simulation, not a game you play.** Output is a deterministic-ish battle replay
  driven by the data, not a skill-based game.
- **Marching armies.** Trees are the OFFENSIVE units: each ZIP code fields an army of
  its trees that **advances and clashes** with the opponent's. Not stationary tower
  defense — trees move, so movement speed matters. (Locked 2026-06-27.)

## Characters = tree genera

- One **stat block per genus** (~50 playable archetypes), NOT per individual tree.
- Rarity tiers from the real frequency distribution:
  - **Common** (~15 genera): the everyday roster. 30 genera cover 95% of all trees;
    6 cover 50%.
  - **Uncommon** (~20 genera): 1,000–4,000 trees each (Sorbus, Gleditsia, Aesculus,
    Fagus, Liquidambar, Pinus, Ginkgo, Magnolia, Taxus…).
  - **Rare / Legendary**: the long tail — especially physically **big** or **exotic**
    species (Sequoia, Araucaria, Ginkgo, Metasequoia, etc.).

## Stats

4 core stats per genus: **Attack, Range, Attack speed, Health**. Full design and
trait mappings live in [STATS.md](STATS.md). Health is included, which means
tree-towers can be destroyed (the combat model is not pure classic TD).

**Open design questions still to resolve:**
- Numeric scale per stat.
- AoE/splash as a 5th stat vs. a per-genus special ability (leaning: special ability).
- What the enemies are; whether stats need damage/resist types.
- ZIP strength from tree count (volume) vs. species stats.

## Data status / dependencies

- Source: Amsterdam DSO API, dataset `bomen`, table `stamgegevens` (~323k trees,
  298,734 "currently living" after filtering stumps + to-be-felled).
- Current export `data/amsterdam_trees.csv` has coordinates (RD + WGS84) but
  **no ZIP code** — the dataset has no postcode field.
- **Dependency:** the ZIP-code battle requires assigning each tree to a postcode,
  derived from its coordinates (e.g. spatial join to PC4/PC6 polygons, or reverse
  geocoding). This is not yet built.

## Working name

`boomoorlog` = Dutch for "tree war".
