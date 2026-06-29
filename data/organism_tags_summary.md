# C3 Organism Labeling — Summary

> Produced by `pipeline/c3_aggregate.py` + `pipeline/c3_validate.py` after
> the parallel research pass against the 319 organisms in `creatures.csv`.
> Run date: 2026-06-29.

## Coverage

| Metric | Count |
|---|---:|
| Organisms in `data/creatures.csv` | 319 |
| Tagged with `habitat_classes` + `movement_classes` | 319 (100%) |
| Per-organism research markdown in `memory/organisms/<slug>.md` | 319 (100%) |
| Photos already on disk | 314 |
| Photos missing (need backfill) | 5 |

## Tag source mix

How many rows took the category default vs. the per-organism override:

| Source | Count |
|---|---:|
| `default` | 30 (~9%) |
| `override` | 289 (~91%) |

Most rows are overrides because the `creatures.csv` roster is heavy on
tree-feeding microorganisms (aphids, mites, scale insects, gall midges)
whose category-default (`flower-visitor` / `flower-bobber`) was almost
never right; they consistently override to `tree-canopy` or `tree-bark`
+ `idle-only`.

## Taxonomy enrichment (GBIF)

Produced by `pipeline/enrich_taxonomy.py`. 319 organisms → GBIF Species
Match API → `data/organisms_taxonomy.csv`:

| GBIF rank | Count | % |
|---|---:|---:|
| species | 181 | 57% |
| genus | 47 | 15% |
| family | 29 | 9% |
| compound* | 25 | 8% |
| unmatched | 12 | 4% |
| order | 10 | 3% |
| kingdom | 5 | 2% |
| class | 5 | 2% |
| phylum | 4 | 1% |
| unranked | 1 | <1% |

\* Compound = multi-species slug like `wood-pigeon-magpie-carrion-crow`
that doesn't resolve to a single GBIF taxon. Marked `rank=compound`,
taxonomy chain left blank.

The 12 unmatched rows are typically pest/disease groupings that don't
exist in GBIF (e.g. "Generalist sap-feeders", "Sooty mould grazers")
or have such loose Latin names that GBIF can't disambiguate. They keep
their habitat / movement tags but their taxonomy chain stays null.

## Validation pass

3 flags total across the 319 rows, all **false positives** on inspection:

| Slug | Rule | Why it flagged | Reality |
|---|---|---|---|
| `bradyrhizobium` | R1 | movement=none + category=other | Nitrogen-fixing bacteria. The tags are correct — bacteria are stationary and don't fit any other category. Rule R1 should permit `category=other` for stationary microbes. |
| `frankia-alni` | R1 | movement=none + category=other | Same: nitrogen-fixing actinobacteria. Tags correct. |
| `lutra-lutra` | R3 | water-body habitat + category=mammal | Eurasian otter actively swims under water in Amsterdam canals. Tags correct; rule R3 was too strict (mammals with `water-body` are legitimate). |

No labeling errors found. Detail in `data/organism_tags_review.csv`.

## What's next (post-C3)

Ready to ingest. Once the schema migrations (020 → 025) are applied on
Supabase + verified on localhost, a follow-up migration (026, not
written yet) backfills the `habitat_classes` + `movement_classes` +
`lore` columns from `data/organism_tags.csv` (plus the per-organism
markdown body into `organisms.lore`).

Then the alive-map renderer (C5+) reads from those columns.

## Files produced by C3

| Path | What |
|---|---|
| `data/c3_inventory.csv` | Working file: one row per creature, has_photo flag. |
| `data/c3_batches/batch_NN.csv` | Per-batch slices for parallel research (11 × 29). |
| `data/c3_batches/batch_NN_tagged.csv` | Per-batch tagged output. |
| `data/c3_batches/manifest.json` | Batch range index for reproducibility. |
| `data/organisms_taxonomy.csv` | GBIF chain per organism. |
| `data/.taxonomy_cache.json` | GBIF response cache. |
| `data/organism_tags.csv` | **Canonical merged output.** Tags + taxonomy + inventory metadata. |
| `data/organism_tags_review.csv` | Validation flags (3 false positives). |
| `data/organism_tags_summary.md` | This file. |
| `memory/organisms/<slug>.md` | Per-organism research notes (319 files). |
| `data/organism_photos_backfill.csv` | (After running c3_photo_backfill.py) photo-download report. |

## Reproducibility

The whole pipeline is runnable from scratch:

```
python3 pipeline/c3_inventory.py        # build inventory from creatures.csv
python3 pipeline/c3_batches.py          # split into research batches
# [parallel research agents fill each batch's tagged CSV + per-organism .md]
python3 pipeline/enrich_taxonomy.py     # GBIF taxonomy chain (cached)
python3 pipeline/c3_aggregate.py        # merge everything → organism_tags.csv
python3 pipeline/c3_validate.py         # sanity-check
python3 pipeline/c3_photo_backfill.py   # download CC photos for missing rows
```

Each step writes deterministic output, so re-runs only differ where the
inputs differ.
