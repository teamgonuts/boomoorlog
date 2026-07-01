-- Boomoorlog schema, migration 039 (C5 — Slice 3a).
--
-- Server-side habitat point picker. Given a viewport bbox and a habitat
-- kind, returns N random points-on-surface from polygons intersecting the
-- bbox. Called by /api/trees to attach a `habitat_points_by_kind` map to
-- each viewport response, so the client can spawn creatures on the right
-- kind of terrain without shipping polygon geometry over the wire.
--
-- Kinds: 'water', 'park', 'tree'. 'tree' is a synthetic kind — it reads
-- from the `trees` table instead of `osm_habitats`, so tree-canopy /
-- tree-bark species get the same interface.
--
-- Perf note: uses geography bbox intersect (&&) so the GiST index on
-- osm_habitats.geom and trees.geom stays hot. Split into UNION ALL branches
-- rather than a CASE WHEN LEFT JOIN because Postgres can only pick one
-- index plan per join, and mixing water/tree paths in one join defeats
-- both. The final ORDER BY random() LIMIT n is O(intersecting rows), which
-- is tens/hundreds at Amsterdam scale.
--
-- Idempotent: `create or replace function`.

begin;

create or replace function habitat_points_in_bbox(
    min_lat  double precision,
    min_lng  double precision,
    max_lat  double precision,
    max_lng  double precision,
    h_kind   text,
    n        int
)
returns table (lat double precision, lng double precision)
language sql
stable
as $$
    with env as (
        select ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)::geography as g
    ),
    picks as (
        -- osm_habitats path (water / park / future).
        select ST_PointOnSurface(h.geom::geometry) as pt
        from osm_habitats h, env
        where h_kind <> 'tree'
          and h.kind = h_kind
          and h.geom && env.g
        union all
        -- Trees path — the geometry is already a point, no ST_PointOnSurface.
        select ST_SetSRID(ST_MakePoint(t.longitude, t.latitude), 4326) as pt
        from trees t, env
        where h_kind = 'tree'
          and t.geom && env.g
          and t.longitude is not null
          and t.latitude is not null
    )
    select ST_Y(pt)::double precision as lat,
           ST_X(pt)::double precision as lng
    from picks
    where pt is not null
    order by random()
    limit greatest(n, 0);
$$;

comment on function habitat_points_in_bbox(double precision, double precision,
    double precision, double precision, text, int)
is 'C5: return N random habitat-appropriate spawn points inside a viewport '
   'bbox for a given kind (water|park|tree). Reads osm_habitats for water/park '
   'and the trees table for tree. Server-side random sampling.';

commit;
