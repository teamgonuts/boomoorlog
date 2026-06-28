-- Boomoorlog schema, migration 003.
-- Backfill genera aggregates from the now-populated trees table.
-- Idempotent: safe to re-run any time `trees` changes.
--
--   tree_count      = how many rows in trees have this genus_slug
--   avg_height_m    = mean of trees.height_m   for this genus (where not null)
--   avg_diameter_cm = mean of trees.diameter_cm for this genus (where not null)
--
-- Note: a tree's avg_*_class strings are class-bucket midpoints, so these
-- averages are coarse, but consistent for ranking individual trees against the
-- genus baseline (the per-tree variance mechanic in memory/SCHEMA.md).

begin;

with stats as (
    select
        genus_slug,
        count(*)               as cnt,
        avg(height_m)::numeric(4,1)    as avg_h,
        avg(diameter_cm)::numeric(5,1) as avg_d
    from trees
    where genus_slug is not null
    group by genus_slug
)
update genera g
   set tree_count      = coalesce(stats.cnt, 0),
       avg_height_m    = stats.avg_h,
       avg_diameter_cm = stats.avg_d
  from stats
 where stats.genus_slug = g.slug;

-- Genera that exist but have zero trees in the table get tree_count = 0
-- (their default), avg_* stay NULL. Nothing to do — they're already correct.

commit;
