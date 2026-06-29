-- Creatures AMS schema, migration 025.
-- Backfills the taxonomy columns added in 024 from the CSV produced by
-- pipeline/enrich_taxonomy.py (which hits the GBIF Species API for every
-- row in data/creatures.csv and records the full chain).
--
-- Re-run pipeline/enrich_taxonomy.py before this migration to refresh the
-- CSV from the latest creatures.csv. The script is idempotent and caches
-- successful matches.
--
-- This migration must be run with psql's `\copy` available (i.e. via
-- `psql -f` from the repo root), since `\copy` is a client-side meta
-- command. The CSV path is repo-relative.
--
-- Idempotent: re-running overwrites the same rows.

begin;

create temp table tmp_organisms_taxonomy (
    slug             text primary key,
    latin_name       text,
    query_name       text,
    rank             text,
    kingdom          text,
    phylum           text,
    class_name       text,
    order_name       text,
    family           text,
    genus            text,
    species          text,
    scientific_name  text,
    match_type       text,
    confidence       text
);

-- Pull the CSV in. Path is relative to where psql is invoked (the repo
-- root, per db/MIGRATING_TO_ORGANISMS.md).
\copy tmp_organisms_taxonomy from 'data/organisms_taxonomy.csv' with (format csv, header true);

-- Update only existing organism rows (we don't insert new ones here —
-- that's 021's job). Empty CSV cells become NULLs.
update organisms o
   set rank        = nullif(t.rank, ''),
       kingdom     = nullif(t.kingdom, ''),
       phylum      = nullif(t.phylum, ''),
       class_name  = nullif(t.class_name, ''),
       order_name  = nullif(t.order_name, ''),
       family      = nullif(t.family, ''),
       genus       = nullif(t.genus, ''),
       species     = nullif(t.species, '')
  from tmp_organisms_taxonomy t
 where o.slug = t.slug;

-- Tree organisms (rows imported from `genera`) don't appear in
-- data/organisms_taxonomy.csv because they come from a different source.
-- Apply a coarse default for any tree row that still has null taxonomy:
-- kingdom=Plantae, genus=slug, rank=genus. The GBIF enrichment can be
-- extended to cover genera later (see pipeline/enrich_taxonomy.py TODO).
update organisms
   set kingdom = coalesce(kingdom, 'Plantae'),
       genus   = coalesce(genus, slug),
       rank    = coalesce(rank, 'genus')
 where category = 'tree';

commit;

-- Sanity check: how many rows of each rank do we now have?
-- Run this interactively after applying:
--   select rank, count(*) from organisms group by rank order by 2 desc;
