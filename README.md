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
| `data/` | Raw datasets — **offline pipeline inputs only** (see note below). |
| `db/` | SQL migrations (`001_schema.sql`, `002_indexes.sql`, `003_backfill_genera.sql`). |
| `pipeline/` | Shared pipeline modules (`stats.py` — single source of truth for per-genus stat derivation). |
| `docs/` | Generated static character wiki (M1 output). |
| `*.py` | Offline data pipeline — extract trees, derive ZIP codes, generate characters & sprites, seed the DB. |

## Data pipeline (Python scripts)

These are offline tools that prep data, derive stats, and seed the database — they
are **not** part of the runtime app.

| Script | Purpose |
|---|---|
| `extract_trees.py` | Pull living trees out of the raw Amsterdam dataset. |
| `generate_characters.py` | Render `memory/CHARACTERS.md` from `pipeline/stats.py`. |
| `generate_sprites.py` / `_v2.py` / `generate_pixel_sprites.py` | Produce genus sprites. |
| `build_wiki.py` | Render the static character wiki into `docs/`. |
| `seed_genera.py` | Load `genera` table in Supabase (uses `pipeline/stats.py`). |
| `seed_trees.py` | Bulk-load `trees` table via `COPY` (298k rows). |

## Data status (as of M2)

The CSVs and GeoJSON in `data/` are **raw pipeline inputs** — fed into Postgres via
the seed scripts. The runtime app reads only from the Supabase database; nothing in
the app touches `data/*.csv` directly. If the source data changes, re-run the seed
scripts.

## Architecture (planned)

- **Database:** Postgres + PostGIS on Supabase as the source of truth (not CSVs).
- **Engine:** a pure, headless, framework-agnostic TypeScript module — armies + seed
  in, battle log out. Deterministic seeded RNG. No UI, no DOM, no DB inside it.
- **Frontend:** deferred until the app skeleton milestone.

Full delivery plan and rationale live in [`memory/ROADMAP.md`](memory/ROADMAP.md).

## Status

M1 (character wiki) is done. Next up is the database foundation. Track progress in
[`memory/ROADMAP.md`](memory/ROADMAP.md).
