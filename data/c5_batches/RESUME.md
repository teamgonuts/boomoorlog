# C5 — How to resume the photo backfill

Each batch (~25 organisms) is processed by a sonnet sub-agent that:
1. Looks up the iNaturalist taxon for each Latin name.
2. Downloads candidate photos via curl.
3. Reads each photo (vision QA) to verify: **clear, full-body, recognisable**.
4. If the first candidate is poor, tries 1–2 alternates.
5. Saves the chosen photo to `data/organism_photos/<slug>.jpg`.
6. Writes a row to `data/c5_batches/batch_NN_photos.csv` with the verdict.

## State files (the source of truth)

| File | What it tracks |
|---|---|
| `progress.json` | Per-batch `status: pending\|done`. |
| `batch_NN.csv` | Input slice for sub-agent N. |
| `batch_NN_photos.csv` | Sub-agent output — **existence = batch is done**. |
| `data/organism_photos/<slug>.jpg` | The chosen photo file (saved + committed). |

## To resume in a fresh conversation

Tell Claude:
> Continue C5 photo backfill. Read `data/c5_batches/progress.json`, pick the
> next 13 batches with status='pending', and spawn sonnet sub-agents to
> process them. Commit between waves so progress survives credit windows.

## Wave size

13 batches × 25 organisms = ~325 organisms per wave. With ~1,700 organisms
total in the long tail, expect 5–6 waves to cover everything. Track
remaining via:

```bash
jq '[.batches[] | select(.status != "done")] | length' \
   data/c5_batches/progress.json
```

## Aggregate + apply

After all waves are done (or whenever you want to publish what's been
collected so far):

```bash
python3 pipeline/c5_aggregate.py            # merges batch_NN_photos.csv → data/c5_photos.csv
psql "$SUPABASE_DB_URL" -f db/036_c5_photos_backfill.sql
```

## Sub-agent prompt template

Each launched agent receives this self-contained prompt (substituting NN):

```
You are a research agent for the Creatures AMS C5 photo backfill. Your batch:
`data/c5_batches/batch_NN.csv` (~25 organisms).

For each organism in the batch:

1. WebFetch:
   `https://api.inaturalist.org/v1/taxa?q=<latin_name>&per_page=1`
   Read the JSON; grab `results[0].id` and `results[0].default_photo.medium_url`
   plus `default_photo.attribution` and `default_photo.license_code`.
2. Download the default photo to /tmp/<slug>.jpg via curl:
   `curl -sL -o /tmp/<slug>.jpg "<medium_url>"`
3. Read /tmp/<slug>.jpg with your vision capability. Decide: is the
   organism shown clearly, ideally with the WHOLE body in frame and
   recognisable from this image alone?
4. If yes → cp /tmp/<slug>.jpg data/organism_photos/<slug>.jpg, record
   status=ok.
5. If no → WebFetch alternates. The `/v1/taxa/<id>/photos` endpoint
   returns 404 in practice; use the observations endpoint instead:
   `https://api.inaturalist.org/v1/observations?taxon_id=<id>&photos=true&per_page=5&order=desc&order_by=votes`
   Pick a photo from `results[*].photos[*].url` (replace `square` with
   `medium` in the URL if needed). Try at most 2 alternates. If none
   meet the bar, record status=no_good_photo.
   Also: reject default photos under ~30 KB on disk — they're often
   broken thumbnails.
   Also: when the initial `q=<latin>` returns a higher-rank taxon
   (e.g. "q=Buteo buteo" returning Buteoninae), search again with
   `q=<genus> <species>` and pick the species-rank result.

Output `data/c5_batches/batch_NN_photos.csv` with header:
slug,latin_name,taxon_id,photo_url,photo_license,attribution,status,note

`status` ∈ {ok, no_good_photo, taxon_not_found, error}.
`note` = brief sentence on the choice or rejection reason.

Reply "DONE. Wrote N rows to batch_NN_photos.csv. Saved M photos."
```

## Why batches of 25 (not 30)

Vision QA is heavier than text classification — each image costs tokens.
25 keeps a single sub-agent run comfortably under a per-call budget; if
you increase batch size, watch for sub-agent timeouts.

## Credit budgeting

Each batch is roughly: 25 organisms × (1 iNat lookup + 1 image inspection
+ optional 1 retry) = 25–50 model calls + a few WebFetches. With sonnet
that's a few thousand tokens per batch. A full pass of 1,700 organisms
in waves of 13 totals roughly 60 batches × ~10k tokens = a few hundred
thousand tokens of sub-agent time across all waves.
