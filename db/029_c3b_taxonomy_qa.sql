-- Creatures AMS schema, migration 029.
-- C3.B: cleanup pass on the taxonomy results.
--
-- Two fixes:
--   1. Ingest data/c3b_taxonomy_retry.csv — GBIF retry hits for organisms
--      that were rank='unmatched'. 44 of 91 resolved this time (kingdom /
--      class hints disambiguated genera like "Acanthus", "Salix", etc.).
--   2. Mark the misranked compound slugs as rank='compound' — these are
--      multi-Latin-name strings like "Pica / Corvus" or "Apodemus, Myodes,
--      Sciurus" that GBIF resolved to an oddly-high level (phylum / kingdom /
--      class) because they're not a single taxon. 'compound' is the
--      appropriate label per memory/BEHAVIOR_TAXONOMY.md.
--
-- Apply via psql -f from the repo root. Idempotent.

begin;

-- ----------------------------------------------------------------------------
-- 1. C3.B retry ingest (44 newly resolved)
-- ----------------------------------------------------------------------------
create temp table tmp_c3b_retry (
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

\copy tmp_c3b_retry from 'data/c3b_taxonomy_retry.csv' with (format csv, header true);

update organisms o
   set rank        = nullif(t.rank, ''),
       kingdom     = coalesce(nullif(t.kingdom, ''),     o.kingdom),
       phylum      = coalesce(nullif(t.phylum, ''),      o.phylum),
       class_name  = coalesce(nullif(t.class_name, ''),  o.class_name),
       order_name  = coalesce(nullif(t.order_name, ''),  o.order_name),
       family      = coalesce(nullif(t.family, ''),      o.family),
       genus       = coalesce(nullif(t.genus, ''),       o.genus),
       species     = coalesce(nullif(t.species, ''),     o.species)
  from tmp_c3b_retry t
 where o.slug = t.slug
   and t.rank <> 'unmatched'
   and t.rank <> '';

-- ----------------------------------------------------------------------------
-- 2. Re-derive category for the freshly-resolved rows
--    (same CASE as migration 028; only rewrites 'other' rows that just
--    got a real class_name.)
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
       when phylum   = 'Arthropoda'                                      then 'insect'
       else category
   end
 where category = 'other'
   and class_name is not null;

-- Apply habitat / movement defaults for any of the newly-categorised rows
-- that are still tagged as 'other' or untagged. Mirrors migration 028.
update organisms
   set habitat_classes  = case category
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
 where category != 'tree'
   and habitat_classes = '{}'::text[];

-- ----------------------------------------------------------------------------
-- 3. Misranked compound slugs
--    These rows have multi-Latin-name latin_name strings ("Pica / Corvus",
--    "Apodemus, Myodes, Sciurus", "Collembola, Oribatida"…). GBIF was forced
--    to take the union ancestor, which landed at phylum / kingdom / class.
--    That's misleading — mark them rank='compound' so the renderer / wiki
--    knows they're aggregate entries.
-- ----------------------------------------------------------------------------
update organisms
   set rank = 'compound'
 where rank in ('phylum', 'kingdom', 'class')
   and category != 'tree'
   and (latin_name ~ '[/,]'        -- has a separator
        or latin_name ~ '\s+and\s+'
        or latin_name ~ '\s+&\s+'
        or latin_name ~ ';');

commit;

-- Sanity:
--   select rank, count(*) from organisms group by rank order by 2 desc;
--   select count(*) from organisms where rank = 'unmatched';   -- should drop ~44
--   select count(*) from organisms where rank = 'compound';    -- should be original + 14
