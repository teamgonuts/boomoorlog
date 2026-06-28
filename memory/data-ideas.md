# Data Ideas — open nature & living-things datasets to maybe fold in later

> Research scratchpad, not a commitment. A running list of **open** datasets about living
> things and nature that could enrich Boomoorlog beyond what we already use. Grouped by the
> role each could play in the game. Keep-it-simple rule applies: most of these are "nice
> someday," not roadmap. ⭐ = strongest fit / lowest friction.

**Legend for each entry:**
- **API:** free public API? key required? bulk-only?
- **Geo:** ✅ point/polygon coords (drop straight on the map) · ⚠️ aggregated to a region
  (country / province / 10km grid — not for fine placement) · ❌ not geotagged
  (per-species trait/taxonomy only)

## Already in use (baseline)

- **Amsterdam trees** — DSO API (`bomen`/`stamgegevens`, ~298k living trees) · **API:** free,
  no key (Amsterdam Dataservices) · **Geo:** ✅ per-tree lat/lon.
- **OSM** — roads / canals / buildings for the board · **API:** free (Overpass API, Nominatim;
  fair-use limits — for heavy use, self-host or use a planet extract) · **Geo:** ✅.
- **CBS Postcode-6 boundaries** — PC6/PC4 polygons · **API:** free download (CBS / PDOK WFS) ·
  **Geo:** ✅ polygons.

---

## 1. Enemies — what attacks the trees

The TD pivot left "what are the enemies" wide open. Real tree pests/diseases are a perfect,
thematically-honest answer, and several have real spatial/abundance data for NL.

- ⭐ **Oak processionary moth (eikenprocessierups)** — a genuine, well-tracked Amsterdam pest.
  Targets *Quercus* towers specifically. · **API:** no single national API; data fragmented
  across municipal open-data portals (Amsterdam publishes nest/treatment locations via
  data.amsterdam.nl) and citizen-science via Observation.org / iNaturalist. Easiest path is
  GBIF/iNaturalist filtered to *Thaumetopoea processionea*. · **Geo:** ✅ point observations;
  ⚠️ municipal aggregates where published as polygons.
- ⭐ **Dutch elm disease (iepziekte)** — Amsterdam is famously an elm city and actively fights
  this. Spreads tree-to-tree among *Ulmus*. · **API:** no dedicated public API; the city
  inspects/removes infected elms but the dataset isn't openly streamed. Workaround: pull
  *Ophiostoma* observations from GBIF, or just simulate spread on actual Ulmus locations
  from our own tree DB. · **Geo:** ✅ via GBIF; otherwise simulated on our tree coords.
- **Ash dieback (essentaksterfte, _Hymenoscyphus fraxineus_)** — hits *Fraxinus*. · **API:**
  GBIF (`Hymenoscyphus fraxineus`), EPPO Global Database (free, light registration), NVWA
  reports (PDF/region-level). · **Geo:** ✅ GBIF points; ⚠️ NVWA/EPPO at country/province.
- **GBIF / iNaturalist pest occurrences** — beetles, aphids, scale insects, moths actually
  observed near an address. · **API:** both free, REST, no key for read (rate-limited).
  GBIF: `api.gbif.org/v1`. iNaturalist: `api.inaturalist.org/v1`. · **Geo:** ✅ per-record
  lat/lon (some sensitive species are obscured to ~10km).
- **Generic "human" enemies** — chainsaws / urbanization / construction. · **API:** OSM
  Overpass for `landuse=construction` etc. (free); Amsterdam open data for building permits
  (`omgevingsvergunningen`, free via DSO). · **Geo:** ✅ points/polygons.

## 2. Creatures — enemies, allies, or flavor (drive the creature sprite pipeline)

We already extract creatures + make pixel sprites. Open occurrence data could decide *which*
creatures appear on a given board (real local fauna), and supply source photos.

- ⭐ **GBIF (Global Biodiversity Information Facility)** — gbif.org. The backbone for "what
  lives near this address." · **API:** free, no key, `api.gbif.org/v1`; bounding-box query
  is one call. Bulk downloads also free (registration). · **Geo:** ✅ per-occurrence lat/lon.
- ⭐ **iNaturalist** — inaturalist.org. Citizen-science observations with CC-licensed photos
  (per-photo license varies). · **API:** free public REST (`api.inaturalist.org/v1`), no key
  for read; OAuth for writes. · **Geo:** ✅ per-observation coords (obscured for ~conservation-
  sensitive species). Photos could feed `creature-pixel-art`.
  → **deep-dive + real sample response:** [data-ideas-inat-obs.md](data-ideas-inat-obs.md).
- ⭐ **Observation.org / Waarneming.nl** — the Dutch powerhouse for local sightings; far
  denser NL coverage than global sources. · **API:** free public REST
  (`observation.org/api/v1`); spatial reads via `/observations/around-point/` need no auth
  (correction — bbox/point on the base list silently ignored). · **Geo:** ✅ point coords
  (obscured for some species).
  → **deep-dive + real sample response:** [data-ideas-inat-obs.md](data-ideas-inat-obs.md).
- **eBird / SOVON** — bird distributions & abundance. · **API:** eBird has a free API key
  (`api.ebird.org/v2`); SOVON has limited public access (mostly atlas downloads). · **Geo:**
  ✅ eBird (point checklists); ⚠️ SOVON atlases (5×5km or 10×10km grids).
- **De Vlinderstichting** — butterflies & moths (NL). · **API:** no clean public API;
  downloadable atlases. Practical path: pull Lepidoptera from Observation.org / GBIF. ·
  **Geo:** ✅ via those proxies; ⚠️ atlas grids direct from Vlinderstichting.
- **NDFF (Nationale Databank Flora en Fauna)** — national species DB. · **API:** mostly
  restricted/paid; some open layers via PDOK (`Verspreidingsatlas`). · **Geo:** ⚠️ public
  view tends to be 1×1km / 5×5km blurred grids.
- **xeno-canto** — xeno-canto.org. CC-licensed bird/insect *sounds*. · **API:** free public
  REST (`xeno-canto.org/api/2`), no key. · **Geo:** ✅ per-recording coords (some blurred).

## 3. Tower stats & traits — make genera differ on real biology

Right now stats (Attack/Range/Speed/Health) are hand-designed. Real plant-trait data could
ground them.

- **Plant trait databases (TRY, LEDA, BIEN)** — leaf size, growth rate, max height, wood
  density, longevity per species. Natural mappings: max height → Range, wood density →
  Health, growth rate → Attack speed. · **API:** TRY = proposal-based bulk download (free for
  research, no API); LEDA = bulk download; BIEN = R/Python packages over a Postgres backend
  (free). · **Geo:** ❌ for traits (per-species). BIEN also exposes occurrences (✅).
- ⭐ **AHN (Actueel Hoogtebestand Nederland)** — national LiDAR; gives per-tree height /
  canopy for the *actual* trees on the board. Big real tree → strong tower. · **API:** free
  via PDOK (WMS/WCS for the rasters; AHN4 point cloud as bulk tiles). No key. · **Geo:** ✅
  it *is* spatial — raster pixels at 0.5m / per-point xyz.
- **IUCN Red List** — iucnredlist.org. Conservation status → rarity / legendary tiers. ·
  **API:** free REST API (`apiv3.iucnredlist.org`); free token via signup. · **Geo:** ⚠️
  range maps are coarse country/region polygons; status itself is per-species (❌).
- **GBIF taxonomy backbone / World Flora Online** — canonical genus/species, native vs.
  exotic. · **API:** both free, no key (`api.gbif.org/v1/species`, `list.worldfloraonline.org`).
  · **Geo:** ❌ taxonomy only (GBIF *occurrences* are ✅, but that's covered above).

## 4. Board & terrain — beyond flat roads

- ⭐ **PDOK (publieke geodata NL)** — pdok.nl. The Dutch open-geo hub. · **API:** free,
  no key, WMS/WMTS/WFS + REST (`api.pdok.nl`). · **Geo:** ✅ it *is* a geo platform. Two
  standouts inside:
  - **BAG** (addresses + building footprints) — official, free. **Geocoding without a paid
    API** via PDOK Locatieserver (`api.pdok.nl/bzk/locatieserver/search/v3_1`), plus crisp
    building polygons. Directly answers the open geocoding question in VISION.
  - **BGT** — large-scale base map (roads, water, green) at high detail. WMS/WFS.
- **AHN elevation** — already covered (§3). Free via PDOK. ✅ ✅.
- **Amsterdam open data (data.amsterdam.nl)** — parks/green (`groen`), ecological zones,
  water quality, bee/insect hotels, etc. · **API:** free, no key, DSO `dataservices` REST +
  WFS. · **Geo:** ✅ most datasets are point/polygon.
- **Natura 2000 / land cover** — protected-nature overlays. · **API:** PDOK WFS for Natura
  2000 NL (free, no key); Copernicus Land Monitoring Service (free, registration) for
  CORINE / HRL land cover, plus Sentinel imagery. · **Geo:** ✅ polygons / raster tiles.

## 5. Wiki / flavor / media

- **Wikidata + Wikipedia** — species descriptions, images, fun facts for the genus wiki. ·
  **API:** Wikidata SPARQL (`query.wikidata.org/sparql`) + MediaWiki REST, both free, no key.
  · **Geo:** ❌ for species pages; ✅ for items with coords (museums, type localities, etc.).
- **Encyclopedia of Life (EOL)** — traits + media per species. · **API:** free REST
  (`eol.org/api`), no key. · **Geo:** ❌ trait/media only.
- **xeno-canto** — sounds (already covered §2). Free, ✅.

## 6. Seasonal / dynamic mechanics (probably later)

- **KNMI open weather/climate** — knmi.nl. Seasons, storms, drought → weather modifiers. ·
  **API:** free KNMI Data Platform API (`api.dataplatform.knmi.nl`); free token via signup. ·
  **Geo:** ✅ per-station coords + gridded radar/forecast rasters.
- **Phenology (leaf-out / flowering timing)** — seasonal tower strength. · **API:** PEP725
  (European phenology DB) — free with registration, bulk download (no live API). USA-NPN has
  a free REST API (`data.usanpn.org/observations`) — US-only but good model. · **Geo:** ✅
  per-observation site coords; ⚠️ aggregated phenology indices at country level.

---

## Top picks if/when we extend

1. ⭐ **PDOK BAG** — solves geocoding + building blockers, free, no key, fully geotagged.
   Highest leverage.
2. ⭐ **GBIF + iNaturalist + Observation.org** — free APIs, ✅ point-level coords; drop real
   local fauna (and pest species) straight on the map. **Measured 2026-06-28:** Amsterdam
   produces **~450–600 unique species/day** across the two sources combined (~22 species
   overlap — they're highly complementary). Volume is enough for a **live creature map**
   sidebar refreshed every few minutes in 2–3 API calls. Full breakdown in
   [data-ideas-inat-obs.md](data-ideas-inat-obs.md#data-volume--how-many-speciesday-in-amsterdam).
3. ⭐ **Oak processionary moth + Dutch elm disease** — ready-made, genus-targeting,
   authentically-Amsterdam enemies. Get the spatial signal via GBIF/iNaturalist + Amsterdam
   open data.
4. ⭐ **AHN per-tree height** — real tall trees become stronger towers. Free PDOK raster, ✅.

**Pattern:** the strongest fits are all (a) free with no key or minimal signup, and (b)
return point-level coordinates we can place on the board. Trait/taxonomy sources are useful
but ❌ geo — they enrich per-genus stat blocks, not the map. All independent of each other
and none blocks M3–M9.
