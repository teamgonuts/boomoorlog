-- Boomoorlog schema, migration 004.
-- Adds the `creatures` table: the master list of animals/insects that live in
-- the trees, deduped from the per-genus Living-creatures research.
-- Source of truth: data/creatures.csv (built by extract_creatures.py).
-- Idempotent: safe to re-run.

begin;

create table if not exists creatures (
    slug          text         primary key,
    common_name   text         not null,
    latin_name    text,
    pic_file      text,         -- repo-relative, e.g. "data/creature_pics/foo.jpg"
    tree_count    integer      not null default 0,
    tree_genera   text[]       not null default '{}',  -- references genera.slug values
    created_at    timestamptz  not null default now()
);

-- Quick "which creatures live on this genus?" lookup.
create index if not exists creatures_tree_genera_gin
    on creatures using gin (tree_genera);

commit;
