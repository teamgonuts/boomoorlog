import { NextResponse } from "next/server";
import { geocodeAmsterdam, isGeocodeHit } from "@/lib/geocode";

/**
 * REST endpoint mirroring the geocodeAmsterdam() helper.
 *
 * Not currently used by /play (it calls the helper directly server-side),
 * but kept around for future client-side debouncing / autocomplete.
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  const result = await geocodeAmsterdam(q);
  if (isGeocodeHit(result)) {
    return NextResponse.json(result);
  }
  return NextResponse.json({ error: result.error }, { status: result.status });
}
