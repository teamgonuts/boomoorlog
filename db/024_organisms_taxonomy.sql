-- Creatures AMS schema, migration 024.
-- Adds the full taxonomy chain to `organisms` so every row records the
-- biological hierarchy (kingdom → phylum → class → order → family → genus
-- → species). Also records the rank of the row itself, so the renderer
-- knows whether it's looking at a species, a genus, or a compound entry.
--
-- The narrow `category` column (tree | bird | mammal | …) is preserved
-- for UX bucketing; it doesn't always match taxonomy 1:1 (we lump spiders
-- and mites under "arachnid"; we separate "tree" from "plant"). Taxonomy
-- is the scientific truth; category is the display label.
--
-- Also adds `rank` to `observations` so we know what level each sighting
-- was reported at (species when ID'd, genus when not, etc.). This is what
-- lets the renderer "match observations to organisms at the finest level
-- they share, falling back up the chain when needed."
--
-- Idempotent: safe to re-run.

begin;

alter table organisms
    add column if not exists rank        text,
    add column if not exists kingdom     text,
    add column if not exists phylum      text,
    add column if not exists class_name  text,   -- `class` is reserved in SQL
    add column if not exists order_name  text,   -- `order` is reserved in SQL
    add column if not exists family      text,
    add column if not exists genus       text,
    add column if not exists species     text;   -- species epithet only ('vulpes', not 'Vulpes vulpes')

-- Optional CHECK to keep `rank` consistent. Don't enforce yet — the
-- enrichment script may leave rank null for unresolved rows, and
-- 'compound' rows (multi-species slugs like wood-pigeon-magpie-carrion-
-- crow) are an intentional escape hatch.

-- Indexes for the most common "aggregate up the tree" queries.
create index if not exists organisms_genus_idx      on organisms (genus);
create index if not exists organisms_family_idx     on organisms (family);
create index if not exists organisms_order_name_idx on organisms (order_name);
create index if not exists organisms_class_name_idx on organisms (class_name);
create index if not exists organisms_rank_idx       on organisms (rank);

-- Observations also carry their reported rank, so we can resolve them to
-- the finest-matching organism (species first, then genus, then family).
alter table observations
    add column if not exists rank text;

create index if not exists observations_rank_idx on observations (rank);

commit;
