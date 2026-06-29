-- Creatures AMS schema, migration 030.
-- C3.A: ingest the sub-agent override tags into organisms.
--
-- pipeline/c3a_aggregate.py merges every batch_NN_tagged.csv into
-- data/c3a_overrides.csv. This migration:
--   1. \copies the CSV into a temp table
--   2. UPDATEs organisms.habitat_classes / movement_classes / category for
--      every row the sub-agents touched
--   3. UPDATEs organisms.lore for any slug whose memory/organisms/<slug>.md
--      exists (handled separately by a re-run of pipeline/c3_extract_lore.py
--      + an UPDATE; not in this migration to keep the lore pipeline self-
--      contained)
--
-- Idempotent — re-running just re-applies the same overrides.

begin;

create temp table tmp_c3a_overrides (
    slug              text primary key,
    category          text,
    habitat_classes   text,    -- semicolon-separated; converted on update
    movement_classes  text,    -- semicolon-separated; converted on update
    source            text,
    reason            text,
    photo_suggestion  text
);

\copy tmp_c3a_overrides from 'data/c3a_overrides.csv' with (format csv, header true);

-- Only apply rows whose habitat/movement values are actually present
-- (skip any empty defaults that slipped into a sub-agent output).
update organisms o
   set habitat_classes  = string_to_array(t.habitat_classes,  ';'),
       movement_classes = string_to_array(t.movement_classes, ';'),
       category         = coalesce(nullif(t.category, ''), o.category)
  from tmp_c3a_overrides t
 where o.slug = t.slug
   and t.habitat_classes <> ''
   and t.movement_classes <> '';

commit;

-- Sanity:
--   select count(*) from organisms o
--     join (select slug from organisms where slug in (select slug from tmp_c3a_overrides)) using (slug);
