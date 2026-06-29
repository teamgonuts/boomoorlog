# Migrating to the unified `organisms` table (C1)

This file documents the C1 milestone of the Creatures AMS roadmap
(see [`memory/CREATURES_ROADMAP.md`](../memory/CREATURES_ROADMAP.md)).

## What's in this checkpoint

Three new migrations and the TypeScript types that go with them. **None of
them are applied to Supabase yet** — they're proposed changes for you to
review locally before anything destructive happens.

| File | Effect |
|---|---|
| `db/020_organisms.sql` | Creates the `organisms` table + indexes + an `updated_at` trigger. No data movement. |
| `db/021_organisms_populate.sql` | Copies `genera`, `creatures`, and observation-only species into `organisms`. Three idempotent `INSERT … ON CONFLICT` steps. |
| `db/022_observations_organism_slug.sql` | Adds `observations.organism_slug` + index, back-fills from `creature_slug` + scientific-name slug derivation. |
| `db/023_observations_open_source.sql` | Drops the narrow `source` CHECK constraint on `observations` and adds a generic `metadata jsonb` column so new location feeds (eBird, GBIF fungi, gemeente datasets, etc.) can be onboarded without schema changes. |
| `db/024_organisms_taxonomy.sql` | Adds taxonomy columns to `organisms` (`rank`, `kingdom`, `phylum`, `class_name`, `order_name`, `family`, `genus`, `species`) and `observations.rank`. `class_name` / `order_name` instead of `class` / `order` because those are reserved SQL words. |
| `db/025_organisms_taxonomy_backfill.sql` | Backfills taxonomy from `data/organisms_taxonomy.csv` (produced by `pipeline/enrich_taxonomy.py` from GBIF). Uses `\copy`; must run via `psql -f` from the repo root. |
| `db/026_organisms_tags_backfill.sql` | Backfills `habitat_classes` + `movement_classes` + `lore` from the C3 outputs (`data/organism_tags.csv` and `data/organism_lore.csv`). Also tags the 167 tree genera with `{tree-rooted}` / `{none}` defaults. Uses `\copy`. |
| `web/types/supabase.ts` | Adds `Organism` + `OrganismCategory` types; adds `observations.organism_slug` field. |
| `web/lib/organisms.ts` | Helper module (photo URL, sprite URL, dominant tag, category label). |

**Old `genera` and `creatures` tables are not touched.** They keep working
exactly as before. The page-by-page refactor to read from `organisms`
happens after you verify the migration on localhost.

## How to apply

The repo has no migration runner — apply by hand with `psql` (or via the
Supabase SQL editor). The DB URL is in `.env` / `web/.env.local`.

```bash
# from repo root, with $DATABASE_URL set to your Supabase Postgres URL:
psql "$DATABASE_URL" -f db/020_organisms.sql
psql "$DATABASE_URL" -f db/021_organisms_populate.sql
psql "$DATABASE_URL" -f db/022_observations_organism_slug.sql
psql "$DATABASE_URL" -f db/023_observations_open_source.sql
psql "$DATABASE_URL" -f db/024_organisms_taxonomy.sql
psql "$DATABASE_URL" -f db/025_organisms_taxonomy_backfill.sql
psql "$DATABASE_URL" -f db/026_organisms_tags_backfill.sql
```

Each migration is wrapped in a transaction and is idempotent (re-runs are
safe).

## How to verify

```sql
-- 1. Did organisms populate?
select category, count(*) from organisms group by category order by 2 desc;
-- Expected (rough): tree ~167, bird ~120, insect ~600, fungus/lichen/plant
-- ~500, etc. Total depends on observation feed at apply time.

-- 2. Did every existing creature land?
select count(*) from creatures
 where not exists (select 1 from organisms o where o.slug = creatures.slug);
-- Expected: 0.

-- 3. Did every existing genus land as a tree organism?
select count(*) from genera
 where not exists (
     select 1 from organisms o
      where o.slug = genera.slug and o.category = 'tree'
 );
-- Expected: 0.

-- 4. Did observation backfill catch most rows?
select
    sum(case when organism_slug is not null then 1 else 0 end) as linked,
    sum(case when organism_slug is null     then 1 else 0 end) as unlinked,
    count(*) as total
from observations;
-- Expected: linked >> unlinked. Unlinked rows are observations whose
-- scientific_name didn't slug-match any organisms row — typically rare
-- one-offs. The C3 labeling pass cleans these up.

-- 5. Spot-check a few rows.
select slug, category, latin_name, common_name, sprite_path is not null as has_sprite,
       observations_count, tree_count
from organisms
where slug in ('Tilia', 'eurasian-coot', 'grey-heron')
order by category;
```

If anything looks off, the migrations can be reversed:

```sql
-- only if you need to start over:
alter table observations drop column if exists organism_slug;
drop table if exists organisms cascade;
```

(`cascade` removes the trigger + indexes; the underlying `genera`,
`creatures`, and `observations` tables are untouched.)

## What's next after applying

Once you've applied + verified, ping me and the next chunk lands:

1. **Pipeline updates** — the Python seed scripts (`seed_genera.py`,
   `seed_creatures.py`, `seed_observations.py`) start writing to `organisms`
   in addition to the old tables.
2. **Web page refactors** — homepage, `/play`, `/wiki/trees`, `/wiki/creatures`,
   `/api/trees`, `/observations`. One commit per page.
3. **Cut over** — once every reader is on `organisms`, the old tables get
   demoted to views over `organisms`, or dropped entirely.

The C2 (behavior taxonomy) and C3 (labeling pass) milestones can run **in
parallel** with the application of this migration — their output is a CSV
that gets imported once you're satisfied with the schema.
