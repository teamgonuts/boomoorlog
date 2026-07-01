-- Creatures AMS schema, migration 037.
-- Priority photo backfill (2026-07-01).
--
-- Second targeted photo backfill pass. The C5 pipeline (migration 036)
-- ordered organisms by observations_count DESC, so the low-count tail
-- was skipped. This ingest covers 51 organisms across the user's
-- priority categories for the "iconic map creatures":
--   fish, amphibian, turtle, mollusc, mushroom, lagomorph, grasshopper,
--   rodent, dragonfly, fungus/lichen, plus the top-10 spiders by
--   observations_count.
--
-- Same format as 036; idempotent; apply via `psql -f` from repo root.

begin;

create temp table tmp_priority (
    slug               text primary key,
    latin_name         text,
    taxon_id           text,
    photo_url          text,
    photo_license      text,
    attribution        text,
    status             text,
    note               text
);

\copy tmp_priority from 'data/priority_backfill/all_photos.csv' with (format csv, header true);

-- These 51 slugs may already have a REMOTE iNat URL in photo_path from an
-- earlier ingest, but we now have the actual JPEG on disk, so overwrite
-- with the repo-relative path (which is what web/lib/organisms.ts expects).
update organisms o
   set photo_path    = 'data/organism_photos/' || t.slug || '.jpg',
       photo_license = nullif(t.photo_license, ''),
       photo_source  = 'inat'
  from tmp_priority t
 where o.slug = t.slug
   and t.status like 'ok%';

commit;
