-- Creatures AMS schema, migration 036.
-- C5: ingest the sub-agent photo backfill.
--
-- For every slug whose data/organism_photos/<slug>.jpg exists and whose
-- status was 'ok' in the sub-agent batch output, set photo_path to the
-- repo-relative path. web/lib/organisms.ts (organismPhotoUrl) already
-- knows how to translate `data/organism_photos/...` to the web URL.
--
-- Idempotent. Apply via psql -f from the repo root.

begin;

create temp table tmp_c5 (
    slug            text primary key,
    latin_name      text,
    taxon_id        text,
    photo_url       text,
    photo_license   text,
    attribution     text,
    status          text,
    note            text
);

\copy tmp_c5 from 'data/c5_photos.csv' with (format csv, header true);

update organisms o
   set photo_path    = 'data/organism_photos/' || t.slug || '.jpg',
       photo_license = nullif(t.photo_license, ''),
       photo_source  = 'inat'
  from tmp_c5 t
 where o.slug = t.slug
   and t.status = 'ok'
   and (o.photo_path is null or o.photo_path = '');

commit;
