-- Creatures AMS schema, migration 022.
-- Adds `organism_slug` to `observations` so future map queries can resolve
-- every observation to a single organism row in the unified encyclopedia.
-- The existing `creature_slug` column is kept for back-compat — it continues
-- to point at `creatures(slug)` and will be removed in a follow-up after the
-- web refactor is fully cut over.
--
-- Idempotent: safe to re-run.

begin;

alter table observations
    add column if not exists organism_slug text references organisms(slug);

-- Backfill organism_slug:
--   1) Where creature_slug already matches an organism row, copy it across.
--   2) For unmatched observations whose scientific_name resolves to an
--      organism via the same slug-derivation rule used in 021, set that.
update observations
   set organism_slug = creature_slug
 where creature_slug is not null
   and organism_slug is null
   and exists (select 1 from organisms o where o.slug = observations.creature_slug);

update observations
   set organism_slug = derived.slug
  from (
      select
          regexp_replace(
              regexp_replace(lower(o.scientific_name), '[^a-z0-9]+', '-', 'g'),
              '(^-+|-+$)', '', 'g'
          ) as slug,
          o.scientific_name
      from observations o
      where o.organism_slug is null
        and o.creature_slug is null
  ) derived
 where observations.scientific_name = derived.scientific_name
   and observations.organism_slug is null
   and exists (select 1 from organisms o where o.slug = derived.slug);

-- "Which observations belong to organism X" — same access pattern as the
-- existing creature_slug index, so we mirror it.
create index if not exists observations_organism_slug_idx
    on observations (organism_slug);

commit;
