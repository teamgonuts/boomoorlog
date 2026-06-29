-- Creatures AMS schema, migration 032.
-- C3.C: backfill the full taxonomy chain (phylum / class / order / family)
-- for the 167 tree genera.
--
-- These rows took the coarse default in migration 025 (kingdom=Plantae,
-- genus=slug, rank=genus) because they live in `genera`, not in
-- data/creatures.csv, and so were skipped by the original GBIF enrichment
-- script. pipeline/c3c_enrich_trees.py hits GBIF for each tree latin_name
-- with a `kingdom=Plantae` hint (disambiguates Acer / etc. homonyms).
--
-- 167 / 167 matched. Apply via psql -f from the repo root. Idempotent.

begin;

create temp table tmp_c3c_trees (
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

\copy tmp_c3c_trees from 'data/c3c_taxonomy_trees.csv' with (format csv, header true);

update organisms o
   set rank        = nullif(t.rank, ''),
       kingdom     = coalesce(nullif(t.kingdom, ''),     o.kingdom),
       phylum      = coalesce(nullif(t.phylum, ''),      o.phylum),
       class_name  = coalesce(nullif(t.class_name, ''),  o.class_name),
       order_name  = coalesce(nullif(t.order_name, ''),  o.order_name),
       family      = coalesce(nullif(t.family, ''),      o.family),
       genus       = coalesce(nullif(t.genus, ''),       o.genus)
       -- species deliberately not set — tree organisms are genus-level
  from tmp_c3c_trees t
 where o.slug = t.slug
   and t.rank <> 'unmatched'
   and t.rank <> '';

commit;

-- Sanity:
--   select count(*) filter (where phylum is not null) as has_phylum,
--          count(*) as total from organisms where category = 'tree';
--   -- should now be 167 / 167.
