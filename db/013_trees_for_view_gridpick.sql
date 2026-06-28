-- Boomoorlog schema, migration 013.
-- Two changes that together fix the /play map UX at all zooms:
--
-- 1. Grid-pick trees_for_view. The 010/012 versions had two regimes (return
--    every tree if ≤ max_pins, else cluster pins). At mid-zoom the "individual"
--    branch returned every real tree, which clumped along streets (because
--    that's where Amsterdam plants them) and made the map feel uneven. This
--    rewrite is one regime: always grid the bbox into cells_per_side² cells,
--    return one representative tree per non-empty cell (lowest id, so the
--    selection is deterministic per viewport). At neighborhood zoom cells are
--    tiny → most trees are alone in a cell → you still see most of them. At
--    city zoom cells are big → one sample per cell → even spacing across the
--    whole viewport. Cluster mode and its count-badge UI are retired (the
--    `mode` field still exists for back-compat, always set to 'individual').
--
-- 2. Per-function statement_timeout = 10s on both viewport RPCs. The anon
--    role's default 3s wasn't enough for citywide bboxes (~209k trees) — the
--    sort step spills to disk under anon's small work_mem and runs ~3–7s.
--    10s gives plenty of headroom while still protecting against runaway
--    queries. We explored bumping work_mem at the function level instead;
--    it interacted poorly with SQL-function plan caching and made things
--    worse, so we went with the simpler timeout-bump approach.
--
-- Idempotent: CREATE OR REPLACE / ALTER FUNCTION SET.

create or replace function trees_for_view(
    lat_min        double precision,
    lng_min        double precision,
    lat_max        double precision,
    lng_max        double precision,
    max_pins       integer,
    cells_per_side integer
)
returns table (
    mode              text,
    cell_key          text,
    id                bigint,
    lat               double precision,
    lng               double precision,
    slug              text,
    n                 integer,
    species           text,
    height_m          smallint,
    diameter_cm       smallint,
    planting_year     smallint,
    location          text,
    location_detail   text,
    protection_status text
)
language sql
stable
parallel safe
set statement_timeout = '10s'
as $$
    with winning_ids as (
        -- For each cell pick the lowest tree id. Single narrow scan (id + lat
        -- + lng), grouped by (gx, gy) — much cheaper than DISTINCT ON sort
        -- over wide rows.
        select min(s.id) as id
        from (
            select
                t.id,
                floor((t.longitude - lng_min) / nullif((lng_max - lng_min) / cells_per_side, 0))::int as gx,
                floor((t.latitude  - lat_min) / nullif((lat_max - lat_min) / cells_per_side, 0))::int as gy
            from trees t
            where t.geom is not null
              and ST_Intersects(
                    t.geom,
                    ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
                  )
        ) s
        group by s.gx, s.gy
    )
    select
        'individual'::text                          as mode,
        't:' || t.id::text                          as cell_key,
        t.id                                        as id,
        t.latitude                                  as lat,
        t.longitude                                 as lng,
        t.genus_slug                                as slug,
        1                                           as n,
        t.species_full                              as species,
        t.height_m                                  as height_m,
        t.diameter_cm                               as diameter_cm,
        t.planting_year                             as planting_year,
        t.location                                  as location,
        t.location_detail                           as location_detail,
        t.protection_status                         as protection_status
    from trees t
    join winning_ids w using (id)
    limit max_pins;
$$;

-- Match the bump on the companion top-genera RPC (same citywide-bbox cost).
alter function trees_top_genera_in_bbox(
    double precision, double precision, double precision, double precision,
    integer
) set statement_timeout = '10s';
