-- Boomoorlog schema, migration 038 (C5 — habitat-realistic placement).
--
-- Stores OSM polygons that constrain creature placement on /play. Populated
-- offline by pipeline/seed_osm_habitats.py from the Overpass API. Small enough
-- to fit comfortably in one Supabase row-count budget (Amsterdam is ~200 km²;
-- water + park polygons are on the order of a few thousand rows).
--
-- Design shape (kept minimal per the "keep it simple" project rule):
--   * one polymorphic table, one `kind` column — new habitat types plug in
--     without adding new tables. Slice 1 seeds only 'water'; parks and other
--     kinds land in follow-up commits.
--   * geography(MultiPolygon, 4326) so we can ST_DWithin in meters and cheaply
--     union canal segments that Overpass returns as separate ways.
--   * osm_id + osm_type retained so re-imports are idempotent — the seed
--     script upserts on (osm_type, osm_id).
--   * GiST index for the viewport ST_Intersects query the /api/habitats route
--     will run per pan/zoom.
--
-- Idempotent — safe to re-run.

begin;

create extension if not exists postgis;

create table if not exists osm_habitats (
    id            bigserial primary key,
    osm_type      text        not null,     -- 'way' | 'relation'
    osm_id        bigint      not null,
    kind          text        not null,     -- 'water' | future: 'park' | 'canopy' | ...
    tags          jsonb,                    -- raw OSM tag bag, useful for debugging + future filtering
    geom          geography(MultiPolygon, 4326) not null,
    imported_at   timestamptz not null default now(),
    constraint osm_habitats_unique_osm unique (osm_type, osm_id)
);

create index if not exists idx_osm_habitats_geom on osm_habitats using gist (geom);
create index if not exists idx_osm_habitats_kind on osm_habitats (kind);

commit;
