-- Creatures AMS schema, migration 035.
-- C4 step 2: ingest the sub-agent common-name research.
--
-- 13 sonnet sub-agents covered the 376 organisms still missing a
-- common_name after the iNat pass in migration 034. They produced
-- data/c4_names_resolved.csv via pipeline/c4_aggregate.py.
--
-- Idempotent. Apply via psql -f from the repo root.

begin;

create temp table tmp_c4_resolved (
    slug         text primary key,
    latin_name   text,
    common_name  text,
    source       text
);

\copy tmp_c4_resolved from 'data/c4_names_resolved.csv' with (format csv, header true);

update organisms o
   set common_name = t.common_name
  from tmp_c4_resolved t
 where o.slug = t.slug
   and t.common_name <> ''
   and (o.common_name is null or o.common_name = '');

commit;

-- Sanity:
--   select count(*) filter (where common_name is null or common_name = '') as still_missing
--     from organisms;
