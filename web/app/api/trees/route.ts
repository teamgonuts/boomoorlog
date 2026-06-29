import { NextResponse } from "next/server";

import { supabase } from "@/lib/supabase";
import type {
  ViewportMarker,
  ViewportTreesResponse,
} from "@/lib/trees-api";

// Viewport-aware tree fetch for /play. Calls the combined `viewport_for_map`
// RPC (migration 027) which intersects the bbox ONCE and returns markers +
// top-genera breakdown + creature slugs in a single JSONB blob — replaces
// the older two-RPC fan-out that did the spatial intersect twice.
//
// Query params:
//   bbox  = "lat_min,lng_min,lat_max,lng_max" (required)
// Optional:
//   max_pins        = cap before clustering (default 100)
//   cells_per_side  = grid resolution (default 10)
//   top_n           = top genera count (default 100)

export const dynamic = "force-dynamic";

const DEFAULT_MAX_PINS = 100;
const DEFAULT_CELLS_PER_SIDE = 10;
const DEFAULT_TOP_N = 100;

// Cache the JSON for short windows — repeated pans to the same viewport
// (Leaflet rounds to integers, so this hits often) bypass Postgres entirely.
// Vercel honours s-maxage on the edge; browsers honour max-age. stale-while-
// revalidate keeps perceived latency low even when the upstream is recomputing.
const CACHE_HEADERS = {
  "Cache-Control": "public, max-age=30, s-maxage=120, stale-while-revalidate=300",
};

function parseBbox(s: string | null) {
  if (!s) return null;
  const parts = s.split(",").map((x) => Number(x.trim()));
  if (parts.length !== 4 || parts.some((x) => !Number.isFinite(x))) return null;
  const [lat_min, lng_min, lat_max, lng_max] = parts;
  if (lat_min >= lat_max || lng_min >= lng_max) return null;
  return { lat_min, lng_min, lat_max, lng_max };
}

function clampInt(value: string | null, def: number, min: number, max: number) {
  if (!value) return def;
  const n = Number(value);
  if (!Number.isFinite(n)) return def;
  return Math.max(min, Math.min(max, Math.floor(n)));
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const bbox = parseBbox(url.searchParams.get("bbox"));
  if (!bbox) {
    return NextResponse.json({ error: "invalid bbox" }, { status: 400 });
  }
  // Lower bound matches the AdminPanel slider min (20) so a tester moving the
  // slider to its lowest setting actually gets 20 markers back, not 50.
  const maxPins = clampInt(url.searchParams.get("max_pins"), DEFAULT_MAX_PINS, 20, 2000);
  const cellsPerSide = clampInt(
    url.searchParams.get("cells_per_side"),
    DEFAULT_CELLS_PER_SIDE,
    4,
    40,
  );
  const topN = clampInt(url.searchParams.get("top_n"), DEFAULT_TOP_N, 1, 50);

  const { data, error } = await supabase.rpc("viewport_for_map", {
    ...bbox,
    max_pins: maxPins,
    cells_per_side: cellsPerSide,
    top_n: topN,
  });

  if (error) {
    // Most likely cause is the 10s statement_timeout on a citywide bbox.
    // Log it server-side but degrade gracefully — return an empty viewport
    // (200) so the client doesn't surface a dev-overlay error and the map
    // just shows no markers until the user pans/zooms to a smaller area.
    console.warn("viewport_for_map:", error.message, "bbox:", bbox);
    const empty: ViewportTreesResponse = {
      mode: "individual",
      total: 0,
      markers: [],
      topGenera: [],
      creatureSlugs: [],
    };
    return NextResponse.json(empty, { headers: CACHE_HEADERS });
  }

  // RPC returns JSONB which supabase-js parses to a plain object. Narrow
  // the type from `unknown` and translate to the wire shape this route
  // has historically produced.
  const blob = (data ?? {
    mode: "individual",
    total: 0,
    markers: [],
    topGenera: [],
    creatureSlugs: [],
  }) as {
    mode: "individual" | "cluster";
    total: number;
    markers: Array<{
      id: number;
      lat: number;
      lng: number;
      slug: string | null;
      species: string | null;
      height_m: number | null;
      diameter_cm: number | null;
      planting_year: number | null;
      location: string | null;
      location_detail: string | null;
      protection_status: string | null;
    }>;
    topGenera: Array<{ slug: string; n: number }>;
    creatureSlugs: string[];
  };

  const markers: ViewportMarker[] = blob.markers.map((m) => ({
    mode: "individual",
    key: `t:${m.id}`,
    lat: m.lat,
    lng: m.lng,
    slug: m.slug,
    n: 1,
    id: m.id,
    species: m.species,
    height_m: m.height_m,
    diameter_cm: m.diameter_cm,
    planting_year: m.planting_year,
    location: m.location,
    location_detail: m.location_detail,
    protection_status: m.protection_status,
  }));

  const total = blob.total;
  const topGenera = blob.topGenera.map((g) => ({
    slug: g.slug,
    n: Number(g.n),
    pct: total === 0 ? 0 : (Number(g.n) / total) * 100,
  }));

  const body: ViewportTreesResponse = {
    mode: "individual",
    total,
    markers,
    topGenera,
    creatureSlugs: blob.creatureSlugs ?? [],
  };
  return NextResponse.json(body, { headers: CACHE_HEADERS });
}
