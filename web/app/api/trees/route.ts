import { NextResponse } from "next/server";

import { supabase } from "@/lib/supabase";
import type {
  ViewportMarker,
  ViewportTreesResponse,
} from "@/lib/trees-api";

// Viewport-aware tree fetch for /play. Single GET endpoint that returns the
// markers to render (individual trees OR cluster pins, chosen server-side
// based on how many trees fall in the bbox) plus the top-genera breakdown
// for the current viewport. Both come from PostGIS RPCs called in parallel.
//
// Query params:
//   bbox  = "lat_min,lng_min,lat_max,lng_max" (required)
// Optional (rarely overridden):
//   max_pins        = cap before we switch to cluster mode (default 100 — the
//                     bench supports much higher, but visually anything past
//                     ~100 in one viewport feels cluttered, especially with
//                     cluster pins where each one is sprite+number)
//   cells_per_side  = grid resolution in cluster mode (default 10 → max 100 cells,
//                     matches max_pins so the two regimes feel consistent)
//   top_n           = how many top genera to return (default 100, large enough
//                     that the area panel sees every genus in the viewport)

export const dynamic = "force-dynamic";

const DEFAULT_MAX_PINS = 100;
const DEFAULT_CELLS_PER_SIDE = 10;
const DEFAULT_TOP_N = 100;

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
  const maxPins = clampInt(url.searchParams.get("max_pins"), DEFAULT_MAX_PINS, 50, 2000);
  const cellsPerSide = clampInt(
    url.searchParams.get("cells_per_side"),
    DEFAULT_CELLS_PER_SIDE,
    4,
    40,
  );
  const topN = clampInt(url.searchParams.get("top_n"), DEFAULT_TOP_N, 1, 50);

  const [markersResp, topResp, obsResp] = await Promise.all([
    supabase.rpc("trees_for_view", {
      ...bbox,
      max_pins: maxPins,
      cells_per_side: cellsPerSide,
    }),
    supabase.rpc("trees_top_genera_in_bbox", {
      ...bbox,
      limit_n: topN,
    }),
    // Pull creature_slug for any observation inside the viewport. Used by the
    // AreaPanel to surface auto-promoted creatures (empty tree_genera). 10k cap
    // is well above the densest Amsterdam viewport we expect at default zoom.
    supabase
      .from("observations")
      .select("creature_slug")
      .gte("lat", bbox.lat_min)
      .lte("lat", bbox.lat_max)
      .gte("lng", bbox.lng_min)
      .lte("lng", bbox.lng_max)
      .not("creature_slug", "is", null)
      .range(0, 9999),
  ]);

  if (markersResp.error) {
    return NextResponse.json(
      { error: `trees_for_view: ${markersResp.error.message}` },
      { status: 500 },
    );
  }
  if (topResp.error) {
    return NextResponse.json(
      { error: `trees_top_genera_in_bbox: ${topResp.error.message}` },
      { status: 500 },
    );
  }
  // Observation lookup is best-effort: if it errors (e.g. table missing during
  // an in-progress migration), we'd rather render the panel without auto-promoted
  // creatures than 500 the whole viewport fetch. Log and continue.
  if (obsResp.error) {
    console.error("observations bbox lookup:", obsResp.error.message);
  }

  const rows = markersResp.data ?? [];
  // Mode is uniform across rows (the RPC picks one branch). If no rows, treat
  // as individual mode with zero markers — clean default for the empty view.
  const mode: "individual" | "cluster" =
    rows.length > 0 ? (rows[0].mode as "individual" | "cluster") : "individual";

  const markers: ViewportMarker[] = rows.map((r) => ({
    mode: r.mode as "individual" | "cluster",
    key: r.cell_key,
    lat: r.lat,
    lng: r.lng,
    slug: r.slug,
    n: r.n,
    id: r.id ?? undefined,
    species: r.species,
    height_m: r.height_m,
    diameter_cm: r.diameter_cm,
    planting_year: r.planting_year,
    location: r.location,
    location_detail: r.location_detail,
    protection_status: r.protection_status,
  }));

  // `total` is repeated on every row of trees_top_genera_in_bbox; pull from
  // the first row, fall back to 0 when the viewport is empty.
  const total = topResp.data && topResp.data.length > 0 ? Number(topResp.data[0].total) : 0;
  const topGenera = (topResp.data ?? []).map((g) => ({
    slug: g.slug,
    n: Number(g.n),
    pct: total === 0 ? 0 : (Number(g.n) / total) * 100,
  }));

  const creatureSlugs = Array.from(
    new Set(
      (obsResp.data ?? [])
        .map((o) => o.creature_slug)
        .filter((s): s is string => typeof s === "string" && s.length > 0),
    ),
  );

  const body: ViewportTreesResponse = {
    mode,
    total,
    markers,
    topGenera,
    creatureSlugs,
  };
  return NextResponse.json(body);
}
