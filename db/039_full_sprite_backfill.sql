-- Creatures AMS schema, migration 039.
-- Full per-organism sprite backfill (2026-07-01).
--
-- Reads the pipeline's log (data/full_sprite_backfill/backfill.csv)
-- and, for every row with status='ok', sets the organism's sprite_path
-- to the repo-relative creature_sprites path. The web layer already
-- knows how to translate that to /creature_sprites/<slug>.png.
--
-- Method: pure Python auto-form-assignment from taxonomy → hue from
-- dominant photo colour → render via the creature-pixel-art skill.
-- Zero LLM tokens; ~5 minutes wall-clock on a laptop.
--
-- Idempotent. Apply via `psql -f db/039_full_sprite_backfill.sql` from
-- the repo root.

begin;

create temp table tmp_sprite_backfill (
    slug         text primary key,
    form         text,
    hue          text,
    aspect       text,
    sat          text,
    tail         text,
    head_stripe  text,
    status       text,
    note         text
);

\copy tmp_sprite_backfill from 'data/full_sprite_backfill/backfill.csv' with (format csv, header true);

-- Update sprite_path for every organism where the render succeeded.
-- Overwrites any pre-existing sprite_path so re-runs of the pipeline
-- (with tuned forms) always land the freshest asset.
update organisms o
   set sprite_path = 'data/creature_sprites/' || t.slug || '.png'
  from tmp_sprite_backfill t
 where o.slug = t.slug
   and t.status = 'ok';

commit;
