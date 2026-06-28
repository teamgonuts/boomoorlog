/**
 * Server-side OpenStreetMap Nominatim helpers.
 *
 * Used by:
 *  - /play  page  — single best hit (geocodeAmsterdam, internally calls search)
 *  - /api/geocode — array, used by the AddressInput autocomplete
 *
 * Nominatim requires a unique User-Agent and has a 1 req/sec rate limit. Both
 * helpers stay well under that — solo project.
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

/**
 * Returns up to `limit` matches in Amsterdam. Used for autocomplete.
 * Returns [] on errors (autocomplete should fail silently).
 */
export async function searchAmsterdam(
  q: string,
  limit = 5,
): Promise<GeocodeHit[]> {
  const cleaned = q.trim();
  if (cleaned.length < 3) return [];

  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("q", cleaned);
  url.searchParams.set("format", "json");
  url.searchParams.set("countrycodes", "nl");
  url.searchParams.set("viewbox", AMSTERDAM_VIEWBOX);
  url.searchParams.set("bounded", "1");
  url.searchParams.set("limit", String(limit));
  url.searchParams.set("addressdetails", "0");

  try {
    const r = await fetch(url, {
      headers: {
        "User-Agent":
          "boomoorlog/0.1 (+https://github.com/teamgonuts/boomoorlog)",
        "Accept-Language": "nl,en;q=0.8",
      },
      cache: "no-store",
    });
    if (!r.ok) return [];
    const hits = (await r.json()) as NominatimHit[];
    return hits.map((h) => ({
      lat: parseFloat(h.lat),
      lng: parseFloat(h.lon),
      display_name: h.display_name,
    }));
  } catch {
    return [];
  }
}

/**
 * Returns the single best match or an error object. Used by /play server-side
 * when the user actually submits the form.
 */
export async function geocodeAmsterdam(q: string): Promise<GeocodeResult> {
  const cleaned = q.trim();
  if (!cleaned) return { error: "Empty address.", status: 400 };

  const hits = await searchAmsterdam(cleaned, 1);
  if (hits.length === 0) {
    return { error: "No match in Amsterdam for that address.", status: 404 };
  }
  return hits[0];
}
