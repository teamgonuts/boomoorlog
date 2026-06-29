-- Creatures AMS schema, migration 027.
-- Phase A perf sprint, step 1: collapse the two viewport RPCs into one.
--
-- The `/api/trees` endpoint currently fans out:
--   - trees_for_view             (intersects 266k trees on citywide bbox)
--   - trees_top_genera_in_bbox   (intersects 266k trees again)
--   - observations bbox query    (lat/lng range filter)
--
-- The two RPCs share the same expensive spatial intersect. This migration
-- introduces `viewport_for_map(...)` which does the intersect ONCE in a
-- NARROW materialized CTE (just id + lat + lng + genus_slug), then enriches
-- marker rows via a btree pkey join. Saves the second intersect and avoids
-- the wide-row sort spill that killed the naive single-RPC attempt.
--
-- Also bumps work_mem to 32MB at the function level — the old version was
-- spilling its 266k-row sort to disk because the anon role's default
-- work_mem is 2 MB.
--
-- The old RPCs (trees_for_view, trees_top_genera_in_bbox) stay around for
-- back-compat until /api/trees is rewritten in the next commit.
--
-- Idempotent.

begin;

create or replace function viewport_for_map(
    lat_min        double precision,
    lng_min        double precision,
    lat_max        double precision,
    lng_max        double precision,
    max_pins       integer default 100,
    cells_per_side integer default 10,
    top_n          integer default 100
)
returns jsonb
language sql
stable
parallel safe
set statement_timeout = '10s'
set work_mem = '64MB'
as $$
    with envelope as (
        select ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography as g
    ),
    -- NARROW intersect — read only the bare minimum columns from the GiST
    -- result so the materialised CTE stays in memory.
    in_box as materialized (
        select
            t.id,
            t.longitude,
            t.latitude,
            t.genus_slug,
            floor((t.longitude - lng_min) / nullif((lng_max - lng_min) / cells_per_side, 0))::int as gx,
            floor((t.latitude  - lat_min) / nullif((lat_max - lat_min) / cells_per_side, 0))::int as gy
        from trees t, envelope e
        where t.geom is not null
          and ST_Intersects(t.geom, e.g)
    ),
    cell_winners as (
        select min(id) as id
        from in_box
        group by gx, gy
    ),
    -- Enrich just the winning rows via pkey index — wide columns only read for
    -- the ~100 markers we actually return.
    markers as (
        select
            t.id,
            t.latitude,
            t.longitude,
            t.genus_slug,
            t.species_full,
            t.height_m,
            t.diameter_cm,
            t.planting_year,
            t.location,
            t.location_detail,
            t.protection_status
        from trees t
        join cell_winners w on t.id = w.id
        limit max_pins
    ),
    top_genera as (
        select genus_slug, count(*)::bigint as n
        from in_box
        where genus_slug is not null
        group by genus_slug
        order by n desc
        limit top_n
    ),
    creature_links as (
        select distinct o.organism_slug as slug
        from observations o, envelope e
        where o.organism_slug is not null
          and o.point is not null
          and ST_Intersects(o.point, e.g)
        limit 10000
    ),
    counts as (
        select count(*)::bigint as total from in_box
    )
    select jsonb_build_object(
        'mode', 'individual',
        'total', (select total from counts),
        'markers', coalesce(
            (select jsonb_agg(jsonb_build_object(
                'id',                m.id,
                'lat',               m.latitude,
                'lng',               m.longitude,
                'slug',              m.genus_slug,
                'species',           m.species_full,
                'height_m',          m.height_m,
                'diameter_cm',       m.diameter_cm,
                'planting_year',     m.planting_year,
                'location',          m.location,
                'location_detail',   m.location_detail,
                'protection_status', m.protection_status
            )) from markers m),
            '[]'::jsonb
        ),
        'topGenera', coalesce(
            (select jsonb_agg(jsonb_build_object('slug', genus_slug, 'n', n))
             from top_genera),
            '[]'::jsonb
        ),
        'creatureSlugs', coalesce(
            (select jsonb_agg(slug) from creature_links),
            '[]'::jsonb
        )
    );
$$;

commit;
