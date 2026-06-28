-- Boomoorlog schema, migration 002.
-- Indexes on the trees table for the hot-path queries.
-- Idempotent: safe to re-run.

-- Army composition: SELECT genus_slug, COUNT(*) FROM trees WHERE postcode4 = $1
create index if not exists idx_trees_postcode4 on trees (postcode4);

-- Finer-grained map view: SELECT ... FROM trees WHERE postcode6 = $1
create index if not exists idx_trees_postcode6 on trees (postcode6);

-- Wiki / per-genus queries: SELECT ... FROM trees WHERE genus_slug = $1
create index if not exists idx_trees_genus_slug on trees (genus_slug);
