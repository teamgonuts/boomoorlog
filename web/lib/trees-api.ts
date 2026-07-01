/**
 * Shape of the /api/trees response. Lives outside the route file so client
 * components can import the type without pulling Next.js server-only imports
 * into the client bundle.
 */
export type ViewportMarker = {
  mode: "individual" | "cluster";
  key: string;
  lat: number;
  lng: number;
  slug: string | null;
  n: number;
  // Individual-only enrichment (omitted on cluster pins).
  id?: number;
  species?: string | null;
  height_m?: number | null;
  diameter_cm?: number | null;
  planting_year?: number | null;
  location?: string | null;
  location_detail?: string | null;
  protection_status?: string | null;
};

/** A single (lat, lng) — used for C5 habitat-appropriate creature spawn points. */
export type HabitatPoint = { lat: number; lng: number };

/** Kinds of habitat we serve pre-picked spawn points for. `tree` reads from
 *  the trees table; the others read from `osm_habitats`. Kept as a string
 *  union so callers can extend it (e.g. `building` later) without changing
 *  the API shape. */
export type HabitatKind = "water" | "park" | "tree";

export type ViewportTreesResponse = {
  mode: "individual" | "cluster";
  total: number;
  markers: ViewportMarker[];
  topGenera: Array<{ slug: string; n: number; pct: number }>;
  // Distinct creature_slug values from observations whose lat/lng fall inside
  // the current viewport bbox. Used by the AreaPanel to surface auto-promoted
  // creatures (whose tree_genera array is empty, so the genus-overlap filter
  // alone would miss them).
  creatureSlugs: string[];
  /** C5: server-picked spawn points for the current viewport, keyed by
   *  habitat kind. `tree` is always present (falls back to the tree markers
   *  themselves). `water` / `park` are present when osm_habitats has been
   *  seeded and the viewport intersects any polygons; otherwise empty. */
  habitatPointsByKind: Partial<Record<HabitatKind, HabitatPoint[]>>;
};
