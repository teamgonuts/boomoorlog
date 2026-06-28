-- Boomoorlog schema, migration 006.
-- Bounding-box variant of the spatial query, used by /play to load every
-- tree visible in the current map viewport (not just inside the radius
-- circle). The radius function (005) stays around for ad-hoc psql work.
-- Idempotent: replaces the function on re-run.

create or replace function trees_in_bbox(
    lat_min double precision,
    lng_min double precision,
    lat_max double precision,
    lng_max double precision
)
returns setof trees
language sql
stable
parallel safe
as $$
    select *
    from trees
    where geom is not null
      and ST_Intersects(
              geom,
              ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
          )
$$;
