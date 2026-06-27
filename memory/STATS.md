# Genus Stats — Boomoorlog

One stat block **per genus** (~50 archetypes), NOT per individual tree. Decided so
far:

## The 4 core stats

| Stat | What it does | Tree trait it maps to | Examples |
|---|---|---|---|
| **Attack** | damage per hit | Wood hardness / density | Oak, Hornbeam = high; Willow, Poplar = low |
| **Range** | reach radius | Tree height | Tall canopy (Plane, Poplar) = long range |
| **Attack speed** | hits per second | Growth speed | Fast growers (Willow, Birch) = rapid; slow hardwoods = sluggish |
| **Health** | damage it can absorb before dying | Trunk girth / size (tankiness) | Big old trunks (Oak, Plane) = high HP |

Built-in tensions that make genera feel different without extra systems:
- Fast-but-weak (Willow) vs. slow-but-strong (Oak).
- Tall snipers (Poplar) vs. tough tanks (thick-trunked Oak/Plane).

## Decisions locked
- **4 stats**, Health included. (Confirmed by user 2026-06-27.)
- **Health implies tree-towers CAN be destroyed** — so the combat model is NOT pure
  classic TD; the enemy damages trees. Kept because it fits "tree war" thematically.
- **Rarity → overall power tier** (legendary/exotic trees get higher numbers across
  the board). No separate "cost" stat, since the user never places towers.

## Still open
- Exact numeric scale per stat (e.g. 1–10? raw values?) — not yet set.
- Whether to add **AoE/splash** for wide-canopy genera, or keep splash as a per-genus
  **special ability** instead of a universal 5th stat. (Leaning: special ability, to
  stay simple.)
- Per-genus special abilities (Yew=poison, Robinia=heal-aura, Plane=bark-shed,
  Ginkgo=fireproof) — flavor layer, not yet assigned.
- What the enemies are, and whether stats need damage/resist types.
- Does a ZIP's strength come mostly from tree **count** (volume) or **stats**? (Draft:
  army = all trees in the ZIP as towers; volume matters, species stats add flavor.)
