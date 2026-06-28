-- Boomoorlog schema, migration 008.
-- Viewport-aware tree fetch for /play. One RPC, two regimes:
--   * If the count of trees in the bbox is <= max_pins, return each tree as
--     an individual row (mode='individual').
--   * Otherwise bin trees into a cells_per_side² grid and return one row per
--     non-empty cell (mode='cluster'), with the cell centroid + count + the
--     dominant genus_slug. Caller renders these as cluster pins.
-- Idempotent: replaces the function on re-run.

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
    cell_key          text,            -- 't:<id>' or 'g:<gx>_<gy>'
    id                bigint,          -- null for clusters
    lat               double precision,
    lng               double precision,
    slug              text,             -- genus or dominant genus for cluster
    n                 integer,          -- 1 for individual, count for cluster
    species           text,
    height_m          smallint,
    diameter_cm       smallint,
    planting_year     smallint,
    location          text,
    location_detail   text,
    protection_status text
)
language plpgsql
stable
parallel safe
as $$
declare
    total_count integer;
    cw          double precision := (lng_max - lng_min) / nullif(cells_per_side, 0);
    ch          double precision := (lat_max - lat_min) / nullif(cells_per_side, 0);
begin
    select count(*)
      into total_count
      from trees
     where geom is not null
       and ST_Intersects(
             geom,
             ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
           );

    if total_count <= max_pins then
        return query
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
        where t.geom is not null
          and ST_Intersects(
                t.geom,
                ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
              );
    else
        return query
        with in_box as (
            select
                floor((t.longitude - lng_min) / cw)::int as gx,
                floor((t.latitude  - lat_min) / ch)::int as gy,
                t.genus_slug,
                t.longitude,
                t.latitude
            from trees t
            where t.geom is not null
              and ST_Intersects(
                    t.geom,
                    ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
                  )
        ),
        per_cell_genus as (
            select gx, gy, genus_slug, count(*) as gn
            from in_box
            where genus_slug is not null
            group by gx, gy, genus_slug
        ),
        top_per_cell as (
            select distinct on (gx, gy) gx, gy, genus_slug as top_slug
            from per_cell_genus
            order by gx, gy, gn desc
        ),
        cell_aggs as (
            select gx, gy,
                   count(*)::int as cn,
                   avg(longitude) as clng,
                   avg(latitude)  as clat
            from in_box
            group by gx, gy
        )
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
        left join top_per_cell t using (gx, gy);
    end if;
end;
$$;
