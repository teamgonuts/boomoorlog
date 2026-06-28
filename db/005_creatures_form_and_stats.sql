-- Boomoorlog schema, migration 005.
-- Adds future-proof columns to creatures: form (body plan picked by the
-- pixel-art skill) + 5 nullable game stats so we can backfill stats later
-- without another schema change. Idempotent.

begin;

alter table creatures
    add column if not exists form text,                                   -- bug/beetle/.../fungus
    add column if not exists attack       smallint check (attack       between 1 and 10),
    add column if not exists range        smallint check (range        between 1 and 10),
    add column if not exists health       smallint check (health       between 1 and 10),
    add column if not exists attack_speed smallint check (attack_speed between 1 and 10),
    add column if not exists move_speed   smallint check (move_speed   between 1 and 10);

-- index on form for "filter by body plan" wiki queries
create index if not exists creatures_form_idx on creatures (form);

commit;
