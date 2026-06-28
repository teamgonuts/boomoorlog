-- Boomoorlog schema, migration 004.
-- Enable PostGIS and add a geography column on `trees` for radius queries
-- ("trees within 1km of an address"). Idempotent: safe to re-run.

begin;

-- Supabase ships PostGIS — just turn it on.
create extension if not exists postgis;

-- A `geography(Point, 4326)` column lets ST_DWithin take distance in meters.
-- Populated from the existing longitude/latitude pair; kept nullable so rows
-- missing coords just don't show up in spatial queries.
alter table trees
    add column if not exists geom geography(Point, 4326);

-- Backfill from the lon/lat columns the M2 seed already populated.
-- Note column order: ST_MakePoint(lng, lat), not (lat, lng).
update trees
   set geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
 where geom is null
   and longitude is not null
   and latitude is not null;

-- GiST index makes ST_DWithin queries fast (millisecond, even on 300k rows).
create index if not exists idx_trees_geom on trees using gist (geom);

commit;
