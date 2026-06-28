# Boomoorlog 🌳⚔️

**"Tree War"** — a web app where two Amsterdam ZIP codes battle each other
auto-battler style, using the **real trees** that grow in each postcode as the
combatants.

You enter your ZIP code and an opponent's ZIP code. The app pulls every real tree
in each area from the Amsterdam open-data trees dataset, builds an army from them,
and runs an automated marching-army battle. ZIPs in → watch the fight → winner out.
No in-match clicking.

## How it works

- **Real data only.** The count, species mix, age, and size of trees in a ZIP code
  determine that side's army. A leafy old neighborhood feels different from a sparse
  new one.
- **Characters = tree genera.** One stat block per genus (~50 archetypes), not per
  individual tree. Rarity comes from real frequency — common street trees vs.
  long-tail exotics (Sequoia, Ginkgo, Araucaria).
- **Stats from the data.** Size axis (height, trunk diameter) drives Range, Attack,
  and Health; vigor (growth rate) drives Movement; researched wood density drives
  Attack speed.

See [`memory/VISION.md`](memory/VISION.md) and [`memory/STATS.md`](memory/STATS.md)
for the full game design.

## Repo layout

| Path | What it is |
|---|---|
| `memory/` | Game-design source of truth + delivery plan — VISION, STATS, CHARACTERS, ROADMAP, per-genus notes. |
| `data/` | Datasets: `amsterdam_trees.csv` (298k living trees), ZIP-matched trees, PC6 boundaries, sprites, tree photos. |
| `docs/` | Generated static character wiki (M1 output). |
| `*.py` | Offline data pipeline — extract trees, derive ZIP codes, generate characters & sprites, build the wiki. |

## Data pipeline (Python scripts)

These are offline tools that prep data and generate the wiki — they are **not** part
of the runtime app.

| Script | Purpose |
|---|---|
| `extract_trees.py` | Pull living trees out of the raw Amsterdam dataset. |
| `generate_characters.py` | Build per-genus character/stat blocks. |
| `generate_sprites.py` / `_v2.py` / `generate_pixel_sprites.py` | Produce genus sprites. |
| `build_wiki.py` | Render the static character wiki into `docs/`. |

## Architecture (planned)

- **Database:** Postgres + PostGIS on Supabase as the source of truth (not CSVs).
- **Engine:** a pure, headless, framework-agnostic TypeScript module — armies + seed
  in, battle log out. Deterministic seeded RNG. No UI, no DOM, no DB inside it.
- **Frontend:** deferred until the app skeleton milestone.

Full delivery plan and rationale live in [`memory/ROADMAP.md`](memory/ROADMAP.md).

## Status

M1 (character wiki) is done. Next up is the database foundation. Track progress in
[`memory/ROADMAP.md`](memory/ROADMAP.md).
