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
};
