-- Boomoorlog schema, migration 001.
-- Creates the two core tables: genera (archetypes) and trees (census).
-- Spec lives in memory/SCHEMA.md. Idempotent: safe to re-run.

begin;

-- genera: one stat block per archetype (~56 rows).
create table if not exists genera (
    slug                    text         primary key,
    latin_name              text         not null,
    dutch_name              text,
    display_name            text,

    -- Five combat stats, locked at 1-10 per memory/STATS.md.
    attack                  smallint     check (attack       between 1 and 10),
    range                   smallint     check (range        between 1 and 10),
    health                  smallint     check (health       between 1 and 10),
    attack_speed            smallint     check (attack_speed between 1 and 10),
    move_speed              smallint     check (move_speed   between 1 and 10),

    -- World-rarity power multiplier. Default 1.00; >1 only for globally rare species
    -- (Ginkgo, Metasequoia, Taxodium, Pterocarya, Parrotia, etc).
    world_rarity_multiplier numeric(3,2) not null default 1.00
                            check (world_rarity_multiplier >= 0),

    -- Baseline for individual-tree variance. A tree taller/thicker than its genus
    -- average is more powerful; smaller is weaker. Precomputed at seed time from
    -- trees.height_m / trees.diameter_cm; the per-tree modifier formula lives in
    -- pipeline/stats.py, not the DB.
    avg_height_m            numeric(4,1),
    avg_diameter_cm         numeric(5,1),

    personality             text,
    tree_count              integer      not null default 0,
    sprite_path             text,
    lore                    text,

    created_at              timestamptz  not null default now()
);

-- trees: the Amsterdam census (~298,734 rows).
-- All 24 source columns from data/amsterdam_trees_zip.csv preserved.
create table if not exists trees (
    id                          bigint  primary key,
    genus_slug                  text    references genera(slug),

    species_full                text,    -- "Tilia americana"
    species_top                 text,    -- "Linde (Tilia)"

    postcode6                   text,    -- "1079RL"
    postcode4                   text,    -- "1079"
    buurt_id                    text,    -- gbdBuurtId

    longitude                   double precision,
    latitude                    double precision,
    rd_x                        double precision,
    rd_y                        double precision,
    geometrie_raw               text,    -- "SRID=28992;POINT (122115.11 483653)"

    height_class                text,    -- raw: "e. 15 tot 18 m."
    diameter_class              text,    -- raw: "0,3 tot 0,5 m." (often null)

    -- Parsed numeric midpoints of the class strings, computed once at seed time
    -- so the army builder doesn't re-parse on every query. Drives per-tree power
    -- variance vs genus baseline (genera.avg_height_m / avg_diameter_cm).
    height_m                    smallint,  -- e.g. "e. 15 tot 18 m." → 17
    diameter_cm                 smallint,  -- e.g. "0,3 tot 0,5 m." → 40

    planting_year               smallint,

    owner                       text,    -- typeEigenaarPlus
    manager                     text,    -- typeBeheerderPlus
    location                    text,    -- standplaats
    location_detail             text,    -- standplaatsGedetailleerd
    object_type                 text,    -- typeObject
    species_type                text,    -- typeSoortnaam
    growing_location_id         text,    -- groeiplaatsBoomId

    protection_status           text,
    protection_status_detail    text,

    valid_from                  date,
    mutated_at                  timestamptz
);

commit;
