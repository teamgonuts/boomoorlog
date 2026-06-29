-- Creatures AMS schema, migration 020.
-- Adds the unified `organisms` table — the C1 milestone of the Creatures AMS
-- roadmap (memory/CREATURES_ROADMAP.md). Supersedes the split between `genera`
-- (trees) and `creatures` (animals/fungi/etc), and becomes the master list
-- every map marker and every wiki page points at.
--
-- This migration ONLY creates the table + indexes. Data population is in 021.
-- Old `genera` and `creatures` tables continue to exist alongside until the
-- web refactor is verified on localhost; see db/MIGRATING_TO_ORGANISMS.md.
--
-- Idempotent: safe to re-run.

begin;

create table if not exists organisms (
    slug              text         primary key,

    -- names (latin is the canonical pivot; the rest are display variants)
    latin_name        text         not null,
    common_name       text,
    dutch_name        text,
    display_name      text,

    -- categorization (vocab locked in memory/BEHAVIOR_TAXONOMY.md, C2 milestone)
    category          text         not null check (category in (
        'tree', 'bird', 'mammal', 'insect', 'arachnid',
        'mollusc', 'amphibian', 'reptile', 'fish',
        'fungus', 'lichen', 'plant', 'other'
    )),

    -- behavior tags (multi-valued; dominant is index 0). Empty array = unlabeled
    -- (e.g. observation-only long tail before C3's research pass tags it).
    habitat_classes   text[]       not null default '{}',
    movement_classes  text[]       not null default '{}',

    -- visual assets. sprite_path nullable so the master list can hold
    -- organisms we know about but haven't drawn yet; the map filters on
    -- non-null sprite_path at display time.
    sprite_path       text,
    sprite_pending    boolean      not null default false,
    form              text,           -- body plan for sprite generation (bug/beetle/bird/...)
    photo_path        text,           -- repo-relative or web path; web/lib/organisms.ts resolves
    photo_license     text,
    photo_source      text,           -- 'inat' | 'wikimedia' | 'curated' | ...

    -- written content
    lore              text,           -- 1-2 paragraph blurb (renders on wiki page)
    personality       text,           -- short one-liner flavor
    sources           text[]       not null default '{}',
                                       -- 'amsterdam_trees' | 'inat' | 'waarneming' | 'curated' | ...

    -- denormalised counts (kept current by the seed pipelines)
    observations_count integer     not null default 0,
    tree_count         integer     not null default 0,    -- only meaningful for category='tree'
    tree_genera        text[]      not null default '{}',  -- creatures: which tree genera they live on

    -- legacy creature metadata
    taxon_group        text,           -- the iNat/Waarneming taxon label that fed our category mapping
    promoted_source    text         check (promoted_source in ('curated', 'auto_observed')),
    promoted_at        timestamptz,

    -- TD combat stats (legacy from genera + creatures). Tower Defense is parked
    -- but the wiki homepage still surfaces these bars; keeping them inline rather
    -- than in a sidecar table for simplicity at ~500 rows.
    attack                     smallint     check (attack       between 1 and 10),
    range                      smallint     check (range        between 1 and 10),
    health                     smallint     check (health       between 1 and 10),
    attack_speed               smallint     check (attack_speed between 1 and 10),
    move_speed                 smallint     check (move_speed   between 1 and 10),
    world_rarity_multiplier    numeric(3,2) not null default 1.00
                                            check (world_rarity_multiplier >= 0),
    avg_height_m               numeric(4,1),
    avg_diameter_cm            numeric(5,1),

    created_at        timestamptz  not null default now(),
    updated_at        timestamptz  not null default now()
);

-- Filter-by-category for the map and the wiki.
create index if not exists organisms_category_idx on organisms (category);

-- "Which tree genera does this creature live on?" -> reverse lookup.
create index if not exists organisms_tree_genera_gin on organisms using gin (tree_genera);

-- Behavior-tag lookups for the alive-map renderer.
create index if not exists organisms_habitat_classes_gin  on organisms using gin (habitat_classes);
create index if not exists organisms_movement_classes_gin on organisms using gin (movement_classes);

-- Common filter: "which organisms have we drawn yet" (sprite filter for map display).
create index if not exists organisms_has_sprite_idx
    on organisms (slug) where sprite_path is not null;

-- Auto-promoted sort for the wiki "recently spotted" view.
create index if not exists organisms_promoted_at_idx
    on organisms (promoted_at desc nulls last);

-- Keep updated_at fresh on every write.
create or replace function organisms_set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists organisms_updated_at on organisms;
create trigger organisms_updated_at
    before update on organisms
    for each row execute function organisms_set_updated_at();

commit;
