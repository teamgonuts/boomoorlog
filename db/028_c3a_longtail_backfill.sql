-- Creatures AMS schema, migration 028.
-- C3.A: backfill the ~2,236 long-tail observation organisms with:
--   1. GBIF taxonomy (from data/c3a_taxonomy.csv)
--   2. A proper `category` derived from GBIF's class_name (was 'other')
--   3. Habitat + movement defaults per category (per memory/BEHAVIOR_TAXONOMY.md)
--
-- Sub-agents will override the defaults for the top-N most-observed species
-- in a follow-up step; this migration covers the long tail in one shot so the
-- encyclopedia goes from "2,236 rows tagged 'other' with no behavior" to
-- "every row has a class-derived category and a plausible default behavior".
--
-- Run via `psql -f` from the repo root (\copy is repo-relative).
-- Idempotent: re-running overwrites the same rows.

begin;

-- ----------------------------------------------------------------------------
-- 1. Taxonomy ingest
-- ----------------------------------------------------------------------------
create temp table tmp_c3a_taxonomy (
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

\copy tmp_c3a_taxonomy from 'data/c3a_taxonomy.csv' with (format csv, header true);

update organisms o
   set rank        = coalesce(nullif(t.rank, ''),        o.rank),
       kingdom     = coalesce(nullif(t.kingdom, ''),     o.kingdom),
       phylum      = coalesce(nullif(t.phylum, ''),      o.phylum),
       class_name  = coalesce(nullif(t.class_name, ''),  o.class_name),
       order_name  = coalesce(nullif(t.order_name, ''),  o.order_name),
       family      = coalesce(nullif(t.family, ''),      o.family),
       genus       = coalesce(nullif(t.genus, ''),       o.genus),
       species     = coalesce(nullif(t.species, ''),     o.species)
  from tmp_c3a_taxonomy t
 where o.slug = t.slug;

-- ----------------------------------------------------------------------------
-- 2. Re-map category from the new class_name + kingdom info
--    Only rewrites organisms that ended up as 'other' from 021 — never
--    overrides the curated rows that already got proper categories.
-- ----------------------------------------------------------------------------
update organisms
   set category = case
       when kingdom = 'Plantae'                                          then 'plant'
       when kingdom = 'Fungi' and class_name = 'Lecanoromycetes'         then 'lichen'
       when kingdom = 'Fungi'                                            then 'fungus'
       when class_name = 'Aves'                                          then 'bird'
       when class_name = 'Mammalia'                                      then 'mammal'
       when class_name = 'Insecta'                                       then 'insect'
       when class_name = 'Arachnida'                                     then 'arachnid'
       when class_name in ('Gastropoda', 'Bivalvia', 'Cephalopoda')      then 'mollusc'
       when class_name = 'Amphibia'                                      then 'amphibian'
       when class_name in ('Reptilia', 'Squamata', 'Testudines')         then 'reptile'
       when class_name in ('Actinopterygii', 'Chondrichthyes', 'Cephalaspidomorphi') then 'fish'
       when phylum   in ('Bryophyta', 'Marchantiophyta', 'Anthocerotophyta') then 'plant'
       when phylum   = 'Arthropoda'                                      then 'insect'   -- catch-all for arthropod observations we couldn't class
       else category
   end
 where category = 'other'
   and class_name is not null;

-- ----------------------------------------------------------------------------
-- 3. Habitat + movement defaults per category
--    Locked vocabulary in memory/BEHAVIOR_TAXONOMY.md.
--    Only writes to rows whose tags are still empty — sub-agent overrides
--    in the follow-up step will take precedence.
-- ----------------------------------------------------------------------------
update organisms
   set habitat_classes  = case category
           when 'tree'      then array['tree-rooted']
           when 'bird'      then array['tree-canopy']
           when 'mammal'    then array['ground-park']
           when 'insect'    then array['flower-visitor']
           when 'arachnid'  then array['anywhere']
           when 'mollusc'   then array['ground-park']
           when 'amphibian' then array['water-edge']
           when 'reptile'   then array['wall-and-roof']
           when 'fish'      then array['water-body']
           when 'fungus'    then array['tree-bark']
           when 'lichen'    then array['tree-bark']
           when 'plant'     then array['ground-park']
           else                  array['anywhere']
       end,
       movement_classes = case category
           when 'tree'      then array['none']
           when 'bird'      then array['tree-flitter']
           when 'mammal'    then array['park-roamer']
           when 'insect'    then array['flower-bobber']
           when 'arachnid'  then array['idle-only']
           when 'mollusc'   then array['idle-only']
           when 'amphibian' then array['water-edge-stalker']
           when 'reptile'   then array['idle-only']
           when 'fish'      then array['water-drifter']
           when 'fungus'    then array['none']
           when 'lichen'    then array['none']
           when 'plant'     then array['none']
           else                  array['idle-only']
       end
 where habitat_classes = '{}'::text[]
   and movement_classes = '{}'::text[]
   and category != 'tree';     -- trees got their defaults in 026

commit;

-- Sanity checks:
--   select category, count(*) from organisms group by category order by 2 desc;
--   select count(*) filter (where habitat_classes <> '{}') as tagged,
--          count(*) filter (where habitat_classes  = '{}') as untagged,
--          count(*) as total from organisms;
