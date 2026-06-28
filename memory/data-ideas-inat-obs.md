# Deep-dive — iNaturalist & Observation.org/Waarneming.nl APIs

Companion to [data-ideas.md](data-ideas.md). These two are the strongest free, ✅-geotagged
sources for "what lives near a player's address" — driving local fauna spawns and feeding
the creature sprite pipeline with real photos.

**TL;DR:**
- Both have free public REST APIs that return per-observation lat/lon.
- **iNaturalist** is the global heavyweight, English-first, richer per-observation metadata
  (taxonomy ancestry, quality grade, CC-license per photo, vernacular names).
- **Observation.org / Waarneming.nl** is the Dutch heavyweight — denser NL coverage and a
  cleaner spatial endpoint (`/observations/around-point/`), but observation photos are
  served from a media server without a stable per-photo license field in the API response.
- For Amsterdam we'd query both, dedupe on `species`, prefer iNat for photos (clear license)
  and Observation.org for density.

---

## Quick comparison

| Aspect | iNaturalist | Observation.org / Waarneming.nl |
|---|---|---|
| Base URL | `https://api.inaturalist.org/v1` | `https://observation.org/api/v1` |
| Auth for read | None (rate-limited ~60 req/min) | None for most read endpoints (some require OAuth2) |
| Spatial query | `?lat=&lng=&radius=` (km), or `?nelat=&nelng=&swlat=&swlng=` bbox | `/observations/around-point/?lat=&lng=&radius=` (meters) |
| Per-record coords | ✅ `geojson.coordinates` + `location` string | ✅ `point.coordinates` (GeoJSON) |
| Obscured for sensitive taxa | Yes (`taxon_geoprivacy`, `obscured`) | Yes (`obscurity` field, `embargo_date`) |
| Quality grade | ✅ `quality_grade` (`research` / `needs_id` / `casual`) | ✅ `validation_status` (`J`/`O`/etc.) + `is_certain` |
| Photos | URLs returned, per-photo `license_code` | URLs returned, no per-photo license in API payload |
| Taxonomy | Full ancestry chain returned per obs | Just `species_detail` (id, sci name, common name) |
| Coverage in Amsterdam (sample 1km² near Dam) | Thousands of obs | ~1,029 obs within 2km of Dam (single query) |
| Total records | ~200M globally | ~16.4M (NL/BE-centric, growing) |
| Docs | https://api.inaturalist.org/v1/docs/ | https://observation.org/api/v1/docs/ |

---

## iNaturalist

### Endpoint that worked

```
GET https://api.inaturalist.org/v1/observations
    ?lat=52.3702&lng=4.8952&radius=2
    &taxon_name=Quercus
    &quality_grade=research
    &per_page=1&photos=true
```

`radius` is in **kilometres**. No API key required for reads. Friendly to set a
`User-Agent` per their docs.

### Real sample — `Quercus robur` (English oak) in Amsterdam

Pruned to the fields that matter for the game:

```json
{
  "id": 309415411,
  "uri": "https://www.inaturalist.org/observations/309415411",
  "observed_on": "2025-08-26",
  "place_guess": "Dr D M Sluyspad, Amsterdam, North Holland, NL",
  "location": "52.3679721949,4.9082082493",
  "geojson": {
    "type": "Point",
    "coordinates": [4.9082082493, 52.3679721949]
  },
  "positional_accuracy": 30,
  "quality_grade": "research",
  "license_code": null,
  "taxon": {
    "id": 56133,
    "name": "Quercus robur",
    "rank": "species",
    "preferred_common_name": "English oak",
    "wikipedia_url": "http://en.wikipedia.org/wiki/Quercus_robur",
    "observations_count": 105016
  },
  "photos": [{
    "id": 558345437,
    "license_code": null,
    "url": "https://static.inaturalist.org/photos/558345437/square.jpg",
    "attribution": "(c) Gia-Uyen Tran, all rights reserved"
  }],
  "user": { "login": "gutran", "name": "Gia-Uyen Tran" }
}
```

### Real sample — a casual creature obs near Dam Square (today)

```
GET /observations?lat=52.3702&lng=4.8952&radius=1&per_page=1
```

Top hit was a **Common Rough Woodlouse** (*Porcellio scaber*) observed at Dam Square
today, license `cc-by-nc`, with full taxonomy ancestry (Animalia → Arthropoda →
Crustacea → Isopoda → … → *Porcellio scaber*) and a default photo URL pointing at
`inaturalist-open-data.s3.amazonaws.com`. The ancestry chain is what lets you say
"this is an insect/crustacean/bird" without a second lookup.

### What's useful for Boomoorlog

- **Spawn enemies that actually live there** — `radius=1` (≈500m, matches our board) →
  hundreds of obs. Filter to pest taxa (`taxon_name=Thaumetopoea` for oak processionary;
  `iconic_taxa=Insecta`, etc.).
- **License-safe source photos for sprites** — filter `license=cc-by-nc,cc-by,cc0` and
  only the photos with a non-null `license_code` → safe to pipe into `creature-pixel-art`.
- **Quality filter** — `quality_grade=research` gives community-verified IDs only.

### Caveats

- **Rate limit** ~60 req/min, ~10k req/day. Cache aggressively per address.
- **`license_code: null`** = all-rights-reserved. The sprite pipeline must skip those photos.
- **Geoprivacy obscuration** for ~conservation-sensitive species → blurred to ~10–20km box.
- **iNaturalist also publishes to GBIF** — if you'd rather do everything via one API,
  GBIF mirrors it (with ~24h lag). Not as photo-rich.

### Resources

- API explorer (try queries in-browser): https://api.inaturalist.org/v1/docs/
- Observation search params reference: https://www.inaturalist.org/pages/api+reference
- Photo & data licensing: https://www.inaturalist.org/pages/help#cc
- Bulk export (GBIF Darwin Core archive): https://www.gbif.org/dataset/50c9509d-22c7-4a22-a47d-8c48425ef4a7

---

## Observation.org / Waarneming.nl

Same backend, different country-skinned frontends:
- `observation.org` — international portal (English)
- `waarneming.nl` — Dutch portal (NL focus, much higher domestic density)
- `waarnemingen.be` — Belgian portal

The API at `observation.org/api/v1` covers all of them; the `permalink` per record points
to the originating site. **Note:** the docs URL `/api/v1/docs/` requires login to render.

### Endpoint that worked (no auth needed)

```
GET https://observation.org/api/v1/observations/around-point/
    ?lat=52.3702&lng=4.8952&radius=2000&limit=1
```

`radius` is in **metres** (not km). Returned 1,029 observations within 2km of Dam Square.

**What does NOT work without auth / silently fails:**
- `?bbox=...` on the base `/observations/` list → param is *silently ignored*, returns
  global feed.
- `?point=POINT(lon lat)&radius=...` → silently ignored.
- `/api/v1/locations/` → 401 Unauthorized.
- `/api/v1/schema/` → 403, requires login.

So the practical public surface is: `/observations/around-point/`, `/observations/?limit=N`
(global feed), and `/regions/` (full country list).

### Real sample — most-recent observation near Dam Square (today)

```json
{
  "id": 407901777,
  "permalink": "https://waarneming.nl/observation/407901777/",
  "date": "2026-06-28",
  "time": "17:18",
  "species_detail": {
    "id": 25151,
    "scientific_name": "Pinalitus cervinus",
    "name": "",
    "group": 15,
    "type": "S"
  },
  "number": 1, "sex": "U", "activity": 98, "life_stage": 1028, "method": 447,
  "has_photo": true, "has_sound": false,
  "point": {
    "type": "Point",
    "coordinates": [4.8672885, 52.3681878]
  },
  "location_detail": {
    "id": 16344,
    "name": "Amsterdam - Oud-West",
    "country_code": "NL",
    "permalink": "https://waarneming.nl/locations/16344/"
  },
  "rarity": 1,
  "is_certain": true,
  "is_escape": false,
  "validation_status": "O",
  "user": 1021256
}
```

A plant bug (*Pinalitus cervinus*) seen in Oud-West today. Note the named neighbourhood
location ("Oud-West") — that's an actual on-brand bonus we don't get from iNat. Photos
arrive as URLs under `photos: [...]` (when the `/observations/{id}/` detail endpoint is
hit; the list view returns `has_photo: true` and you fetch the URLs from the detail call).

### What's useful for Boomoorlog

- **Density in NL** — Observation.org is where Dutch nature recorders log everything. For
  an Amsterdam address, this will be the richer of the two for "what insects/birds were
  seen here this week."
- **Named neighbourhood location** (`location_detail.name`) — could double as flavour text
  on the board ("a *Bombus pascuorum* spotted in your Oud-West last week joined the wave").
- **`rarity`** field (1–4) is a built-in rarity tier we can map straight onto our common /
  uncommon / rare / legendary tower-defense rarity ladder for enemies.
- **`life_stage`, `activity`, `method`, `substrate`** — coded vocabularies (small integer
  IDs) for behavioural state, useful as flavour or balance modifiers.

### Caveats

- **No per-photo license** in the API payload. The site terms apply, and many Dutch
  observers retain rights. For sprite-generation use, **iNat is the safer photo source**.
- **Coded fields** (`activity: 98`, `method: 447`) are opaque without the lookup tables.
  Lookup tables exist behind some endpoints — needs more digging, or just ignore for v1.
- **Spatial filter is `/around-point/`, not `?bbox=`** — easy gotcha; bbox params silently
  return the global feed.
- **OAuth required for writes and for richer `/locations/` data.** Read-only spatial
  queries work fine without it for our use case.

### Resources

- API docs (requires login to view in-browser, but endpoints work without auth):
  https://observation.org/api/v1/docs/
- API root: https://observation.org/api/v1/
- Regions list (countries / continents, no auth): https://observation.org/api/v1/regions/
- About the platform: https://observation.org/about/
- Dutch portal: https://waarneming.nl/
- Their data is also published to GBIF as datasets — Observation.org "8a863029-…" series.

---

## Data volume — how many species/day in Amsterdam?

Measured 2026-06-28 by querying both APIs for **2026-06-27** (a fully-posted day):

| Source | Observations | Unique species |
|---|---:|---:|
| iNaturalist (bbox 4.728–5.079, 52.278–52.431) | 57 | **46** |
| Observation.org (7km radius around Dam) | 887 | **517** |
| Overlap (species reported on both) | — | 22 |
| **Union (either source)** | — | **541** |

**Across the last week (Observation.org):** 253–517 unique species/day, mean ~400.
**iNat:** 38–57/day. Combined union typically lands in the **450–600 species/day** band.

**Why the asymmetry:** Observation.org's NL cohort logs *everything* (moths, beetles, true
bugs, micro-Lepidoptera). The iNat-only sample skews gardener-friendly
(*Acanthus mollis*, *Fuchsia*); the Obs.org-only sample is moth-specialist
(`Acleris forsskaleana`, `Acrobasis repandana`). **Overlap is small (~22 species)** —
mostly the conspicuous baseline (geese, herons, mallards, cabbage white). The two
sources are **highly complementary, not redundant**.

**Implication for Boomoorlog:** even one Amsterdam day yields ~10× more candidate enemy
species than the game could ever use. The constraint is **curation, not data volume**.

### Live-map angle 🗺️

The volume + per-record coords mean we could trivially render a **live "what's around you
right now" creature map** as a sidebar/teaser to the main game — refresh every few
minutes from `/observations/around-point/` and drop pixel sprites on a Leaflet/Mapbox
layer at the real obs coordinates. Could double as:
- A pre-game "scout your neighbourhood" mode that previews the wave roster.
- A standalone Amsterdam wildlife ticker (zero gameplay dependency, ships before M9).
- A way to seed the sprite-generation pipeline opportunistically — when a new species
  shows up nearby and we don't have a sprite for it, queue one.

Caching: ~500–600 fresh observations/day across all of Amsterdam means we can refresh
the whole city in **2–3 API calls** (Obs.org page size 500). Trivial to do every 10
minutes without hitting rate limits.

---

## How they'd fit together in Boomoorlog

```
                player address
                       │
                       ▼
         ┌─────────────────────────┐
         │ Supabase (cached board) │   ← if we have a recent fetch, reuse
         └─────────────────────────┘
                       │ miss
        ┌──────────────┴───────────────┐
        ▼                              ▼
  iNaturalist API              Observation.org API
  (research-grade,             (NL-dense, around-point,
   licensed photos)             rarity + neighbourhood)
        │                              │
        └──────────────┬───────────────┘
                       ▼
        Dedupe by species → enemy roster
        Merge photos (prefer iNat CC-licensed)
        Persist into Supabase keyed by address+date
```

**Concretely for a first pass:**
1. For sprites / asset generation: query **iNat** offline once per chosen pest species,
   filter `license_code in (cc0, cc-by, cc-by-nc)`, feed top photo into the sprite skill.
2. For per-board enemy variety: query **Observation.org `/around-point/`** at game start
   with `lat/lng` from the player's address and `radius=500`. Sort by `rarity` to pick a
   mix of common (rarity=1) and uncommon (rarity=2+) attackers.
3. Cache the per-address response in Supabase for ≥30 days — the wildlife near an address
   doesn't churn fast and we want to respect rate limits.

This keeps the game online-first but light on the third-party APIs, and means every player's
wave roster is built from real sightings on (or near) their own street.
