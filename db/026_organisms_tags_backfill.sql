-- Creatures AMS schema, migration 026.
-- Backfills organisms.habitat_classes, movement_classes, category, and
-- lore from the C3 labeling outputs:
--   - data/organism_tags.csv   (per-slug tags + reason + category)
--   - data/organism_lore.csv   (per-slug prose body from memory/organisms/<slug>.md)
--
-- After this migration runs, the 319 curated creatures in `organisms`
-- have populated behavior tags and wiki-ready prose. The long-tail
-- observation species (the 2,197 'other'-categorised rows) remain
-- unlabeled — they get a second C3 pass after C1's web refactor lands.
--
-- Run via `psql -f` from the repo root (the \copy paths are repo-relative).
-- Idempotent: re-running overwrites the same rows.

begin;

-- ----------------------------------------------------------------------------
-- Tags + category override (from the research agents)
-- ----------------------------------------------------------------------------
create temp table tmp_organism_tags (
    slug              text primary key,
    common_name       text,
    latin_name        text,
    category          text,
    habitat_classes   text,     -- semicolon-separated; converted on UPDATE
    movement_classes  text,     -- semicolon-separated; converted on UPDATE
    source            text,
    reason            text,
    rank              text,
    kingdom           text,
    phylum            text,
    class_name        text,
    order_name        text,
    family            text,
    genus             text,
    species           text,
    has_photo         text,
    tree_genera       text,
    tree_count        text,
    photo_suggestion  text
);

\copy tmp_organism_tags from 'data/organism_tags.csv' with (format csv, header true);

update organisms o
   set habitat_classes  = string_to_array(t.habitat_classes,  ';'),
       movement_classes = string_to_array(t.movement_classes, ';'),
       category         = nullif(t.category, '')
  from tmp_organism_tags t
 where o.slug = t.slug
   and t.habitat_classes <> ''
   and t.movement_classes <> '';

-- ----------------------------------------------------------------------------
-- Lore (prose body from memory/organisms/<slug>.md)
-- ----------------------------------------------------------------------------
create temp table tmp_organism_lore (
    slug text primary key,
    lore text
);

\copy tmp_organism_lore from 'data/organism_lore.csv' with (format csv, header true);

update organisms o
   set lore = t.lore
  from tmp_organism_lore t
 where o.slug = t.slug
   and t.lore <> ''
   -- Don't overwrite existing curated lore unless we're improving it.
   and (o.lore is null or length(t.lore) > length(o.lore));

-- ----------------------------------------------------------------------------
-- Tree defaults (the 167 tree genera weren't in the C3 research pass —
-- they trivially take the category default per BEHAVIOR_TAXONOMY.md)
-- ----------------------------------------------------------------------------
update organisms
   set habitat_classes  = array['tree-rooted'],
       movement_classes = array['none']
 where category = 'tree'
   and (habitat_classes  = '{}'::text[] or habitat_classes  is null);

commit;

-- Sanity checks (run interactively after apply):
--   select count(*) filter (where habitat_classes <> '{}') as tagged,
--          count(*) filter (where habitat_classes  = '{}') as untagged,
--          count(*) as total
--     from organisms;
--   select rank, count(*) from organisms
--    where habitat_classes <> '{}' group by rank order by 2 desc;
