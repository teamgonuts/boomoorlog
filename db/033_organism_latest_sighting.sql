-- Creatures AMS schema, migration 033.
-- Adds the `organism_latest_sighting` view: one row per organism with the
-- most recent observation date. Powers the "Last spotted X ago" line on the
-- creature hover tooltip in /play.
--
-- Cheap to query (uses the existing observations_organism_slug_idx +
-- observations_observed_on_idx); rebuilt on the fly per request — observations
-- is small enough (~5-figure rows) that materialisation is overkill.
--
-- Idempotent: safe to re-run.

begin;

create or replace view organism_latest_sighting as
select
    organism_slug,
    max(observed_on) as last_observed_on,
    count(*)         as obs_count
from observations
where organism_slug is not null
group by organism_slug;

commit;
