-- Boomoorlog schema, migration 005.
-- RPC function for the M4 "trees within radius" query, called from the
-- Next.js app via supabase.rpc("trees_within_radius", …).
-- Idempotent: replaces the function on re-run.

create or replace function trees_within_radius(
    lat double precision,
    lng double precision,
    radius_m double precision default 100
)
returns setof trees
language sql
stable
parallel safe
as $$
    select *
    from trees
    where geom is not null
      and ST_DWithin(
              geom,
              ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
              radius_m
          )
$$;
