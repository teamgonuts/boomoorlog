# C3.A — How to resume the long-tail labeling pass

If a conversation got interrupted mid-pass (credit window, network blip, etc),
this is the protocol to pick up where it left off. The whole pipeline is
designed so neither state nor work is lost.

## Where state lives

| File | What it tracks |
|---|---|
| `data/c3a_batches/progress.json` | Per-batch `status: pending\|done`. Source of truth for which batches still need a sub-agent. |
| `data/c3a_batches/batch_NN.csv` | Input slice handed to a sub-agent (30 organisms each, sorted by `observations_count desc`). |
| `data/c3a_batches/batch_NN_tagged.csv` | Sub-agent output: per-organism tags + override reasons. **Existence = batch is done.** |
| `memory/organisms/<slug>.md` | Per-organism research markdown the sub-agents write. |

## To resume

1. Open a fresh conversation in this repo. Tell it:
   > Continue C3.A. Read `data/c3a_batches/progress.json` and process the
   > pending batches with sonnet sub-agents.
2. Claude reads `progress.json`, finds the `pending` entries, spawns one
   sub-agent per batch (sonnet model), waits for completion, then flips the
   `status` to `done` for each.
3. Commit after each wave finishes.
4. When all batches are `done`, run migration 029 (the override backfill).

## Sub-agent prompt template

Each sub-agent gets a self-contained prompt with:
- The full path to its batch CSV (`data/c3a_batches/batch_NN.csv`).
- The locked behaviour vocabulary (read `memory/BEHAVIOR_TAXONOMY.md`).
- Instructions to write `memory/organisms/<slug>.md` for each organism.
- Instructions to write `data/c3a_batches/batch_NN_tagged.csv` with the
  columns: `slug, category, habitat_classes, movement_classes, source,
  reason, photo_suggestion`.

The full template is at the bottom of this file.

## To kick off a fresh pass

If `progress.json` doesn't exist or you want to re-batch:

```bash
source .env
python3 pipeline/c3a_batches.py --top 300 --batch 30
```

## Re-applying overrides to the DB

After all sub-agents finish, aggregate into one CSV and run migration 029:

```bash
python3 pipeline/c3a_aggregate.py  # writes data/c3a_overrides.csv
psql "$SUPABASE_DB_URL" -f db/029_c3a_overrides_backfill.sql
```

This updates `organisms.habitat_classes` / `movement_classes` / `lore` only
for the slugs the sub-agents reviewed — defaults applied in migration 028
stay in place for the un-reviewed long tail.

## Cost note

- 10 batches × 30 organisms = 300 species in the first wave.
- Run with sonnet (cheaper than opus) — see `model: "sonnet"` in the Agent
  call.
- If you want broader coverage, re-run with `--top 1000` and the orchestrator
  will pick up additional pending batches in subsequent waves.

---

## Sub-agent prompt template (copy into Agent call)

```
You are a research agent for the Creatures AMS C3.A long-tail labeling pass.
Your batch is `data/c3a_batches/batch_NN.csv` — 30 organisms found in
Amsterdam observations. Tag each with behavior classes and write a research
markdown file. Mostly your job is to OVERRIDE category defaults when biology
warrants — defaults were applied in bulk in migration 028.

REPO ROOT: /Users/calvino/dev/boomoorlog

# Step 1: Read the locked behavior taxonomy
`/Users/calvino/dev/boomoorlog/memory/BEHAVIOR_TAXONOMY.md`.

CATEGORIES (pick exactly one):
  tree, bird, mammal, insect, arachnid, mollusc, amphibian, reptile, fish,
  fungus, lichen, plant, other

HABITAT_CLASSES (multi-valued; dominant first):
  tree-rooted, tree-canopy, tree-bark, ground-park, ground-urban,
  water-surface, water-edge, water-body, sky-only, flower-visitor,
  wall-and-roof, anywhere

MOVEMENT_CLASSES (multi-valued; dominant first):
  none, idle-only, tree-flitter, water-edge-stalker, sky-looper,
  park-roamer, water-drifter, flower-bobber, urban-walker

Multi-valued: use 2 values ONLY when the organism demonstrably alternates.
3+ is wrong.

# Step 2: Read your batch
`/Users/calvino/dev/boomoorlog/data/c3a_batches/batch_NN.csv`
Columns: slug, latin_name, common_name, category, family, genus,
         taxon_group, observations_count.

# Step 3: For each organism, write `memory/organisms/<slug>.md`
```
---
slug: <slug>
latin_name: <latin>
common_name: <common>
category: <category>
habitat_classes: [<v1>, <v2>]
movement_classes: [<v1>, <v2>]
tags_source: default | override
---

<3-5 sentences of plain prose: where it lives in Amsterdam, how it moves,
why these tags fit. NO markdown headers in body.>
```

# Step 4: Write `data/c3a_batches/batch_NN_tagged.csv`
Header: slug,category,habitat_classes,movement_classes,source,reason,photo_suggestion
Multi-value: semicolon-separated. source = "default" or "override".

# Notes
- The category default in the CSV is GBIF-derived. Keep unless biology
  disagrees (e.g. aquatic-only family but category=insect — rare).
- Aquatic insects (dragonflies, water beetles) → habitat=water-body or
  water-edge, movement=water-drifter or water-edge-stalker.
- Day-flying birds with strong urban presence (pigeons, crows, magpies) →
  habitat=anywhere, movement=[tree-flitter, urban-walker].
- Common plants in Amsterdam parks default to ground-park / none — fine.

Reply: "DONE. Wrote N organism files and batch_NN_tagged.csv".
```
