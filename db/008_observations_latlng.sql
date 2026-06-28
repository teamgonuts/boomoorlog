-- Boomoorlog schema, migration 008.
-- Add plain lat/lng columns to `observations` alongside the PostGIS `point`.
-- Why: supabase-js returns geography as hex EWKB, which is annoying to decode
-- on the client. Plain floats make the /observations Leaflet page trivial.
-- The PostGIS `point` column stays for future spatial (ST_DWithin) queries.
-- Idempotent.

begin;

alter table observations
    add column if not exists lat double precision,
    add column if not exists lng double precision;

-- Backfill from existing point geometries.
update observations
   set lat = ST_Y(point::geometry),
       lng = ST_X(point::geometry)
 where lat is null and point is not null;

commit;
