-- Boomoorlog schema, migration 012.
-- Single-scan rewrite of trees_for_view. The original (010) ran the spatial
-- scan twice: once for the count(*) decision, once for the grid CTE. At
-- citywide zoom (~70k+ trees in bbox) that doubled the work and put us over
-- Supabase's 3s anon-role statement_timeout.
--
-- This version materializes the bbox-filtered rows in a single CTE and then
-- branches via WHERE-clauses against the count — only one branch produces
-- rows. WITH ... AS MATERIALIZED tells PG to compute in_box once and reuse.
-- Idempotent: CREATE OR REPLACE.

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
as $$
    with in_box as materialized (
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
            t.protection_status,
            floor((t.longitude - lng_min) / nullif((lng_max - lng_min) / cells_per_side, 0))::int as gx,
            floor((t.latitude  - lat_min) / nullif((lat_max - lat_min) / cells_per_side, 0))::int as gy
        from trees t
        where t.geom is not null
          and ST_Intersects(
                t.geom,
                ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
              )
    ),
    cnt as (
        select count(*)::int as n from in_box
    ),
    -- Individual branch: only emits when count ≤ max_pins.
    ind as (
        select
            'individual'::text                          as mode,
            't:' || i.id::text                          as cell_key,
            i.id                                        as id,
            i.latitude                                  as lat,
            i.longitude                                 as lng,
            i.genus_slug                                as slug,
            1                                           as n,
            i.species_full                              as species,
            i.height_m                                  as height_m,
            i.diameter_cm                               as diameter_cm,
            i.planting_year                             as planting_year,
            i.location                                  as location,
            i.location_detail                           as location_detail,
            i.protection_status                         as protection_status
        from in_box i, cnt
        where cnt.n <= max_pins
    ),
    -- Cluster branch: only emits when count > max_pins.
    per_cell_genus as (
        select i.gx, i.gy, i.genus_slug, count(*) as gn
        from in_box i, cnt
        where cnt.n > max_pins
          and i.genus_slug is not null
        group by i.gx, i.gy, i.genus_slug
    ),
    top_per_cell as (
        select distinct on (gx, gy) gx, gy, genus_slug as top_slug
        from per_cell_genus
        order by gx, gy, gn desc
    ),
    cell_aggs as (
        select i.gx, i.gy,
               count(*)::int as cn,
               avg(i.longitude) as clng,
               avg(i.latitude)  as clat
        from in_box i, cnt
        where cnt.n > max_pins
        group by i.gx, i.gy
    ),
    clu as (
        select
            'cluster'::text                              as mode,
            'g:' || c.gx::text || '_' || c.gy::text     as cell_key,
            null::bigint                                 as id,
            c.clat                                       as lat,
            c.clng                                       as lng,
            t.top_slug                                   as slug,
            c.cn                                         as n,
            null::text                                   as species,
            null::smallint                               as height_m,
            null::smallint                               as diameter_cm,
            null::smallint                               as planting_year,
            null::text                                   as location,
            null::text                                   as location_detail,
            null::text                                   as protection_status
        from cell_aggs c
        left join top_per_cell t using (gx, gy)
    )
    select * from ind
    union all
    select * from clu;
$$;
