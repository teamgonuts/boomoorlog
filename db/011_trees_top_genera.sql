-- Boomoorlog schema, migration 009.
-- Top-N genera by count inside a bbox. Used by /play to drive the
-- viewport-aware area panel (the panel shows the genera in the area the user
-- is currently looking at, refreshing on pan/zoom). `total` is the same value
-- across every returned row — a one-roundtrip way to get the global count
-- alongside the breakdown. Idempotent: replaces the function on re-run.

create or replace function trees_top_genera_in_bbox(
    lat_min  double precision,
    lng_min  double precision,
    lat_max  double precision,
    lng_max  double precision,
    limit_n  integer
)
returns table (
    slug  text,
    n     bigint,
    total bigint
)
language sql
stable
parallel safe
as $$
    with in_box as (
        select genus_slug
        from trees
        where geom is not null
          and ST_Intersects(
                geom,
                ST_MakeEnvelope(lng_min, lat_min, lng_max, lat_max, 4326)::geography
              )
    ),
    counts as (
        select genus_slug, count(*) as n
        from in_box
        where genus_slug is not null
        group by genus_slug
    ),
    tot as (select count(*)::bigint as total from in_box)
    select c.genus_slug, c.n, tot.total
    from counts c, tot
    order by c.n desc
    limit limit_n;
$$;
