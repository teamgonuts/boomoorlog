-- Boomoorlog schema, migration 007.
-- Adds `observations`: wildlife sightings pulled from iNaturalist and
-- Observation.org / Waarneming.nl, stored together in one table with a
-- discriminator column. Drives the "what lives near this address" feature
-- and the future live creature map.
--
-- Source of truth: live APIs, refreshed by seed_observations.py.
-- Natural key: (source, source_obs_id) — what each API returns. Re-running
-- the seed UPSERTs cleanly without duplicates.
-- Idempotent: safe to re-run.

begin;

create table if not exists observations (
    source          text         not null check (source in ('inat', 'waarneming')),
    source_obs_id   bigint       not null,
    primary key (source, source_obs_id),

    -- when + where
    observed_on     date         not null,
    point           geography(Point, 4326),     -- ST_MakePoint(lng, lat); nullable so no-coord obs still land
    accuracy_m      integer,

    -- taxonomy as reported by the source
    scientific_name text         not null,
    common_name     text,
    taxon_group     text,                       -- inat: "Animalia"/"Insecta"/...; waarneming: group id

    -- source-specific quality / rarity signal (kept as text so both fit)
    quality         text,                       -- inat: research|needs_id|casual · waarneming: rarity 1-4

    -- first photo (if any) — display + sprite-pipeline source
    photo_url       text,
    photo_license   text,                       -- iNat per-photo license; empty for waarneming

    permalink       text,

    -- link to our game roster. Populated by a separate matching step
    -- (see 008_observations_match_creatures.sql), nullable until then.
    creature_slug   text         references creatures(slug),

    fetched_at      timestamptz  not null default now()
);

-- Spatial index: powers ST_DWithin("show creatures within 1km of address").
create index if not exists observations_point_gix
    on observations using gist (point);

-- "Last N days" filters and ordering.
create index if not exists observations_observed_on_idx
    on observations (observed_on desc);

-- "Which observations belong to creature X" lookups.
create index if not exists observations_creature_slug_idx
    on observations (creature_slug);

-- Name-based search and the creature-matching step.
create index if not exists observations_scientific_name_idx
    on observations (scientific_name);

commit;
