-- Boomoorlog schema, migration 012.
-- Adds the columns needed for M11: auto-discover creatures from observations.
-- Existing curated creatures default to source='curated' and keep working
-- unchanged. New rows promoted by the M11 job will have source='auto_observed'
-- with promoted_at, taxon_group, wikipedia_summary, and a denormalised
-- observations_count for the "recently spotted" sort.
-- Idempotent.

begin;

alter table creatures
    add column if not exists source              text         not null default 'curated'
        check (source in ('curated', 'auto_observed')),
    add column if not exists promoted_at         timestamptz,
    add column if not exists taxon_group         text,
    add column if not exists wikipedia_summary   text,
    add column if not exists observations_count  integer      not null default 0,
    add column if not exists sprite_pending      boolean      not null default false;

-- Common filters: "sort by recently spotted", "auto-observed only", and
-- "which still need a sprite".
create index if not exists creatures_promoted_at_idx
    on creatures (promoted_at desc nulls last);

create index if not exists creatures_source_idx
    on creatures (source);

create index if not exists creatures_sprite_pending_idx
    on creatures (sprite_pending)
    where sprite_pending = true;

commit;
