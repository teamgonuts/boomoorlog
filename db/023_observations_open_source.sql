-- Creatures AMS schema, migration 023.
-- Generalises the `observations` table so it can absorb arbitrary new
-- location-bearing feeds (eBird, GBIF fungi, gemeente datasets, etc.)
-- without future schema changes. This is the "source-extensible ingest"
-- half of C4 — the rest is the Python pipeline side, which lands later.
--
-- Two changes:
--   1) Drop the CHECK constraint that limits `source` to ('inat',
--      'waarneming'). New feeds are now a config change, not a migration.
--   2) Add a generic `metadata jsonb` column for source-specific extras
--      (audio URLs, capture methods, ringing IDs, ...). Optional; default
--      empty.
--
-- Idempotent: safe to re-run.

begin;

-- 1. Drop the narrow check constraint.
--    The constraint name follows Postgres's default convention for table
--    CHECKs declared inline (observations_source_check). We try both that
--    and a safer pattern-match in case it was named differently.
do $$
declare
    cname text;
begin
    select conname into cname
    from pg_constraint
    where conrelid = 'observations'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%source%in%';
    if cname is not null then
        execute format('alter table observations drop constraint %I', cname);
    end if;
end $$;

-- 2. Generic metadata bag for source-specific fields. Default '{}' so
--    existing rows have a well-formed empty object rather than NULL.
alter table observations
    add column if not exists metadata jsonb not null default '{}'::jsonb;

-- Index for JSONB lookups (cheap, useful once feeds use it).
create index if not exists observations_metadata_gin
    on observations using gin (metadata);

commit;
