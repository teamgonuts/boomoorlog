-- Creatures AMS schema, migration 034.
-- C4 step 1: ingest the common names resolved by pipeline/c4_common_names.py
-- (iNaturalist /v1/taxa lookup with preferred_common_name).
--
-- 498 of 885 missing common_names resolved this pass. The rest (~387) go
-- through a sonnet sub-agent pass next.
--
-- Idempotent. Apply via psql -f from the repo root.

begin;

create temp table tmp_c4_names (
    slug           text primary key,
    latin_name     text,
    common_name    text,
    source         text,
    inat_taxon_id  text
);

\copy tmp_c4_names from 'data/c4_common_names.csv' with (format csv, header true);

-- Only update rows where (a) iNat returned a usable name and (b) the
-- organism is still missing a common_name (don't clobber curated values).
update organisms o
   set common_name = t.common_name
  from tmp_c4_names t
 where o.slug = t.slug
   and t.source = 'inat'
   and t.common_name <> ''
   and (o.common_name is null or o.common_name = '');

commit;
