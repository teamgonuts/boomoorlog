import { NextResponse } from "next/server";
import { searchAmsterdam } from "@/lib/geocode";

/**
 * GET /api/geocode?q=<address>&limit=<n>  →  GeocodeHit[]
 *
 * Used by the AddressInput autocomplete on /play. Returns an empty array on
 * any error so the client can fail silently.
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  const limitParam = parseInt(searchParams.get("limit") ?? "5", 10);
  const limit = Math.min(Math.max(limitParam, 1), 10);
  const hits = await searchAmsterdam(q, limit);
  return NextResponse.json(hits);
}
