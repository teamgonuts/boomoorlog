-- Creatures AMS schema, migration 021.
-- Populates `organisms` from the existing `genera`, `creatures`, and
-- `observations` tables. The C1 unification — every organism we know about
-- ends up here, whether or not it has a sprite or a curated entry.
--
-- Run after 020 (which creates the table). Idempotent: uses ON CONFLICT to
-- support re-running after partial completion or upstream backfills.
--
-- Three populate steps, intentionally separate so output is auditable:
--   1) trees: one row per genus (167 rows expected)
--   2) creatures: one row per curated creature (~330 rows expected)
--   3) observation long-tail: one row per unique scientific_name in
--      observations that didn't already get covered by step 2
--
-- habitat_classes and movement_classes are LEFT EMPTY here — the C3 labeling
-- pass writes them.

begin;

-- ----------------------------------------------------------------------------
-- Step 1: trees (from genera)
-- ----------------------------------------------------------------------------
insert into organisms (
    slug, latin_name, dutch_name, display_name,
    category,
    sprite_path, lore, personality,
    sources, tree_count,
    attack, range, health, attack_speed, move_speed,
    world_rarity_multiplier, avg_height_m, avg_diameter_cm,
    created_at
)
select
    g.slug,
    g.latin_name,
    g.dutch_name,
    g.display_name,
    'tree'                                          as category,
    g.sprite_path,
    g.lore,
    g.personality,
    array['amsterdam_trees']::text[]                as sources,
    g.tree_count,
    g.attack, g.range, g.health, g.attack_speed, g.move_speed,
    g.world_rarity_multiplier, g.avg_height_m, g.avg_diameter_cm,
    coalesce(g.created_at, now())
from genera g
on conflict (slug) do update set
    latin_name              = excluded.latin_name,
    dutch_name              = excluded.dutch_name,
    display_name            = excluded.display_name,
    sprite_path             = excluded.sprite_path,
    lore                    = excluded.lore,
    personality             = excluded.personality,
    tree_count              = excluded.tree_count,
    attack                  = excluded.attack,
    range                   = excluded.range,
    health                  = excluded.health,
    attack_speed            = excluded.attack_speed,
    move_speed              = excluded.move_speed,
    world_rarity_multiplier = excluded.world_rarity_multiplier,
    avg_height_m            = excluded.avg_height_m,
    avg_diameter_cm         = excluded.avg_diameter_cm;

-- ----------------------------------------------------------------------------
-- Step 2: creatures (from curated + auto-observed creatures)
-- ----------------------------------------------------------------------------
-- Maps creatures.taxon_group -> organisms.category. The taxon_group column
-- on creatures is sometimes null (older curated rows) — we fall back to
-- 'other' so the NOT NULL constraint is satisfied.
insert into organisms (
    slug, latin_name, common_name,
    category,
    sprite_path, sprite_pending, form,
    photo_path,
    lore,
    sources, tree_genera, tree_count, observations_count,
    taxon_group, promoted_source, promoted_at,
    attack, range, health, attack_speed, move_speed,
    created_at
)
select
    c.slug,
    coalesce(c.latin_name, c.common_name)           as latin_name,
    c.common_name,
    case
        when c.taxon_group is null                                    then 'other'
        when c.taxon_group ilike '%bird%'                             then 'bird'
        when c.taxon_group ilike '%mammal%'                           then 'mammal'
        when c.taxon_group ilike '%amphib%'
          or c.taxon_group ilike '%reptile%'                          then 'amphibian'
        when c.taxon_group ilike '%fish%'                             then 'fish'
        when c.taxon_group ilike '%mollusc%'                          then 'mollusc'
        when c.taxon_group ilike '%arachnid%'
          or c.taxon_group ilike '%spider%'                           then 'arachnid'
        when c.taxon_group ilike '%fung%'                             then 'fungus'
        when c.taxon_group ilike '%lichen%'                           then 'lichen'
        when c.taxon_group ilike '%moss%'
          or c.taxon_group ilike '%plant%'                            then 'plant'
        when c.taxon_group ilike '%moth%'
          or c.taxon_group ilike '%butterfl%'
          or c.taxon_group ilike '%insect%'
          or c.taxon_group ilike '%bee%'
          or c.taxon_group ilike '%wasp%'
          or c.taxon_group ilike '%ant%'
          or c.taxon_group ilike '%beetle%'
          or c.taxon_group ilike '%fl%'        -- flies
          or c.taxon_group ilike '%bug%'
          or c.taxon_group ilike '%cicada%'
          or c.taxon_group ilike '%dragonfl%'
          or c.taxon_group ilike '%cricket%'
          or c.taxon_group ilike '%locust%'
          or c.taxon_group ilike '%arthropod%'                        then 'insect'
        else 'other'
    end                                              as category,
    -- sprite_path: derived from slug under /creature_sprites/ (matches web/lib/creature.ts)
    case
        when c.sprite_pending then null
        else 'web/public/creature_sprites/' || c.slug || '.png'
    end                                              as sprite_path,
    c.sprite_pending,
    c.form,
    c.pic_file                                       as photo_path,
    c.wikipedia_summary                              as lore,
    case
        when c.source = 'curated'       then array['curated']::text[]
        when c.source = 'auto_observed' then array['inat', 'waarneming']::text[]
        else array['curated']::text[]
    end                                              as sources,
    c.tree_genera,
    c.tree_count,
    c.observations_count,
    c.taxon_group,
    c.source                                         as promoted_source,
    c.promoted_at,
    c.attack, c.range, c.health, c.attack_speed, c.move_speed,
    coalesce(c.created_at, now())
from creatures c
on conflict (slug) do update set
    latin_name         = excluded.latin_name,
    common_name        = coalesce(excluded.common_name, organisms.common_name),
    sprite_path        = excluded.sprite_path,
    sprite_pending     = excluded.sprite_pending,
    form               = excluded.form,
    photo_path         = excluded.photo_path,
    lore               = coalesce(excluded.lore, organisms.lore),
    sources            = excluded.sources,
    tree_genera        = excluded.tree_genera,
    tree_count         = excluded.tree_count,
    observations_count = excluded.observations_count,
    taxon_group        = excluded.taxon_group,
    promoted_source    = excluded.promoted_source,
    promoted_at        = excluded.promoted_at;

-- ----------------------------------------------------------------------------
-- Step 3: observation long-tail
-- ----------------------------------------------------------------------------
-- Species observed in Amsterdam (via iNat/Waarneming) that don't yet have a
-- creature row become unsprited organisms. Sprite generation can happen later.
-- We derive a slug from the scientific name; if it collides with an existing
-- organism slug we leave the existing row untouched (ON CONFLICT DO NOTHING).
with new_species as (
    select
        -- slug: lowercased latin name with non-alphanumerics squashed to '-'
        regexp_replace(
            regexp_replace(lower(o.scientific_name), '[^a-z0-9]+', '-', 'g'),
            '(^-+|-+$)', '', 'g'
        )                                            as slug,
        o.scientific_name                            as latin_name,
        -- prefer the most-common common_name across observations
        mode() within group (order by o.common_name) as common_name,
        -- ditto taxon_group
        mode() within group (order by o.taxon_group) as taxon_group,
        count(*)                                     as observations_count,
        max(o.photo_url)                             as photo_url
    from observations o
    where o.creature_slug is null
    group by o.scientific_name
)
insert into organisms (
    slug, latin_name, common_name,
    category,
    photo_path, photo_source,
    sources, observations_count,
    taxon_group,
    created_at
)
select
    ns.slug,
    ns.latin_name,
    nullif(ns.common_name, ''),
    case
        when ns.taxon_group is null                                    then 'other'
        when ns.taxon_group ilike '%bird%'                             then 'bird'
        when ns.taxon_group ilike '%mammal%'                           then 'mammal'
        when ns.taxon_group ilike '%amphib%'
          or ns.taxon_group ilike '%reptile%'                          then 'amphibian'
        when ns.taxon_group ilike '%fish%'                             then 'fish'
        when ns.taxon_group ilike '%mollusc%'                          then 'mollusc'
        when ns.taxon_group ilike '%arachnid%'
          or ns.taxon_group ilike '%spider%'                           then 'arachnid'
        when ns.taxon_group ilike '%fung%'                             then 'fungus'
        when ns.taxon_group ilike '%lichen%'                           then 'lichen'
        when ns.taxon_group ilike '%moss%'
          or ns.taxon_group ilike '%plant%'                            then 'plant'
        when ns.taxon_group ilike '%moth%'
          or ns.taxon_group ilike '%butterfl%'
          or ns.taxon_group ilike '%insect%'
          or ns.taxon_group ilike '%bee%'
          or ns.taxon_group ilike '%wasp%'
          or ns.taxon_group ilike '%ant%'
          or ns.taxon_group ilike '%beetle%'
          or ns.taxon_group ilike '%fl%'
          or ns.taxon_group ilike '%bug%'
          or ns.taxon_group ilike '%cicada%'
          or ns.taxon_group ilike '%dragonfl%'
          or ns.taxon_group ilike '%cricket%'
          or ns.taxon_group ilike '%locust%'
          or ns.taxon_group ilike '%arthropod%'                        then 'insect'
        else 'other'
    end,
    ns.photo_url,
    case when ns.photo_url is not null then 'inat' else null end,
    array['inat', 'waarneming']::text[],
    ns.observations_count,
    ns.taxon_group,
    now()
from new_species ns
where ns.slug <> ''
on conflict (slug) do nothing;

-- ----------------------------------------------------------------------------
-- Sanity summary (run interactively after the migration to verify counts)
-- ----------------------------------------------------------------------------
-- select category, count(*) from organisms group by category order by 2 desc;
-- select source, count(*) from observations group by source;

commit;
