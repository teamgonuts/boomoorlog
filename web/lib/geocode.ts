/**
 * Server-side OpenStreetMap Nominatim helper.
 *
 * Used by:
 *  - /api/geocode  (REST endpoint for future client-side use)
 *  - /play page    (called directly from the server component)
 *
 * Nominatim requires a unique User-Agent (their usage policy) and has a
 * 1 req/sec rate limit. We stay way under that — solo project.
 *
 * Restricts results to the Netherlands and an Amsterdam bounding box so
 * "Hoofdstraat 10" doesn't match Hoofdstraat in some other city.
 */

// Amsterdam bbox: NW corner first, then SE corner.
// lng_west, lat_north, lng_east, lat_south
const AMSTERDAM_VIEWBOX = "4.7287,52.4429,5.0790,52.2783";

export type GeocodeHit = {
  lat: number;
  lng: number;
  display_name: string;
};

export type GeocodeError = {
  error: string;
  status: number;
};

export type GeocodeResult = GeocodeHit | GeocodeError;

export function isGeocodeHit(r: GeocodeResult): r is GeocodeHit {
  return "lat" in r;
}

type NominatimHit = {
  lat: string;
  lon: string;
  display_name: string;
};

export async function geocodeAmsterdam(q: string): Promise<GeocodeResult> {
  const cleaned = q.trim();
  if (!cleaned) {
    return { error: "Empty address.", status: 400 };
  }

  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("q", cleaned);
  url.searchParams.set("format", "json");
  url.searchParams.set("countrycodes", "nl");
  url.searchParams.set("viewbox", AMSTERDAM_VIEWBOX);
  url.searchParams.set("bounded", "1");
  url.searchParams.set("limit", "1");
  url.searchParams.set("addressdetails", "0");

  let hits: NominatimHit[];
  try {
    const r = await fetch(url, {
      headers: {
        "User-Agent":
          "boomoorlog/0.1 (+https://github.com/teamgonuts/boomoorlog)",
        "Accept-Language": "nl,en;q=0.8",
      },
      cache: "no-store",
    });
    if (!r.ok) {
      return { error: `Geocoder returned ${r.status}.`, status: 502 };
    }
    hits = (await r.json()) as NominatimHit[];
  } catch (e) {
    return {
      error: `Geocoder unreachable: ${(e as Error).message}`,
      status: 502,
    };
  }

  if (hits.length === 0) {
    return { error: "No match in Amsterdam for that address.", status: 404 };
  }

  const hit = hits[0];
  return {
    lat: parseFloat(hit.lat),
    lng: parseFloat(hit.lon),
    display_name: hit.display_name,
  };
}
