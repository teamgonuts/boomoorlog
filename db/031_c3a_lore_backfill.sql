-- Creatures AMS schema, migration 031.
-- Backfills organisms.lore from data/organism_lore.csv, which is produced
-- by pipeline/c3_extract_lore.py from the per-organism markdown files in
-- memory/organisms/<slug>.md (the prose-only body, frontmatter stripped).
--
-- After C3.A's sub-agent wave, the lore CSV grew from 319 → 619 rows.
-- Apply via psql -f from the repo root. Idempotent.

begin;

create temp table tmp_lore (slug text primary key, lore text);
\copy tmp_lore from 'data/organism_lore.csv' with (format csv, header true);

update organisms o
   set lore = t.lore
  from tmp_lore t
 where o.slug = t.slug
   and t.lore <> ''
   and (o.lore is null or length(t.lore) > length(o.lore));

commit;

-- Sanity:
--   select count(*) filter (where lore is not null) as has_lore, count(*) as total from organisms;
