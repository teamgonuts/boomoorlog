import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AddressInput } from "@/components/AddressInput";
import PlayMap from "@/components/PlayMap";
import { classifyGenera } from "@/lib/archetype";
import { geocodeAmsterdam, isGeocodeHit } from "@/lib/geocode";
import { supabase } from "@/lib/supabase";
import type { Genus, Tree } from "@/types/supabase";

// Spatial query + Nominatim → never cache the page.
export const dynamic = "force-dynamic";

// "Your block" radius. We render every marker as a DOM element (sprite img),
// and ~1k markers on screen at once choked low-end devices at 250m. 100m
// gives ~80–250 trees in dense Amsterdam, ~30–100 in quieter areas — small
// enough to stay snappy on pan/zoom, big enough to feel like a neighborhood.
const RADIUS_M = 100;
// Bbox the map will show — fitBounds uses `radius * 2.2` as the edge length;
// we query `radius * 2.4` total to add a thin buffer for screen corners.
const VIEW_BBOX_HALF_SIDE_M = RADIUS_M * 1.2;
const PAGE_SIZE = 1000;
const COOKIE_NAME = "lastAddress";

// Convert meters to lat/lng deltas at the given latitude. Good enough for
// Amsterdam-sized bboxes — we're not crossing a pole.
const METERS_PER_DEG_LAT = 111_320;
function bboxAround(lat: number, lng: number, halfSideM: number) {
  const dLat = halfSideM / METERS_PER_DEG_LAT;
  const dLng = halfSideM / (METERS_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180));
  return {
    lat_min: lat - dLat,
    lng_min: lng - dLng,
    lat_max: lat + dLat,
    lng_max: lng + dLng,
  };
}

// Fisher-Yates picker — used for the creature-of-the-moment selection.
function pickRandom<T>(arr: T[], n: number): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out.slice(0, n);
}

async function fetchTreesInBbox(args: {
  lat_min: number;
  lng_min: number;
  lat_max: number;
  lng_max: number;
}): Promise<Tree[]> {
  const out: Tree[] = [];
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .rpc("trees_in_bbox", args)
      .range(from, from + PAGE_SIZE - 1);
    if (error) throw new Error(`trees_in_bbox: ${error.message}`);
    if (!data || data.length === 0) break;
    out.push(...(data as unknown as Tree[]));
    if (data.length < PAGE_SIZE) break;
    if (from > 50_000) break;
  }
  return out;
}

export const metadata = {
  title: "Play — Boomoorlog",
  description:
    "Enter an Amsterdam address and see the real trees that defend your neighborhood.",
};

type SearchParams = Promise<{ q?: string }>;

export default async function PlayPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { q } = await searchParams;
  const address = (q ?? "").trim();

  // No address in URL? Auto-load the last successful search if we have one.
  if (!address) {
    const cookieStore = await cookies();
    const last = cookieStore.get(COOKIE_NAME)?.value;
    if (last) {
      redirect(`/play?q=${encodeURIComponent(last)}`);
    }
  }

  // Geocode + spatial query when we have an address; otherwise just show the
  // bare map with the search overlay.
  let center: { lat: number; lng: number } | null = null;
  let resolvedAddress: string | null = null;
  let trees: Tree[] = [];
  let allGenera: Genus[] = [];
  let geocodeError: string | null = null;

  // M4.5: pick 5 random creatures from the wiki on each page load. Each one
  // flies tree-to-tree on the map for visual life. Uniform random across the
  // full pool. Pull common + latin name now so the hover popup can show them
  // without an extra round-trip.
  let creaturesForMap: Array<{
    slug: string;
    common_name: string;
    latin_name: string | null;
    photo_url: string | null;
  }> = [];

  if (address) {
    const geo = await geocodeAmsterdam(address);
    if (isGeocodeHit(geo)) {
      center = { lat: geo.lat, lng: geo.lng };
      resolvedAddress = geo.display_name;
      const bbox = bboxAround(geo.lat, geo.lng, VIEW_BBOX_HALF_SIDE_M);
      const [treeList, gResp, creaturesResp] = await Promise.all([
        fetchTreesInBbox(bbox),
        supabase.from("genera").select("*"),
        supabase
          .from("creatures")
          .select("slug, common_name, latin_name, pic_file"),
      ]);
      trees = treeList;
      allGenera = gResp.data ?? [];
      // `pic_file` is the original pipeline path (e.g. `data/creature_pics/foo.jpg`);
      // we mirror those files at `web/public/creature_photos/`, so swap the prefix
      // (preserving the original extension — most are .jpg, a few .png, one .jpeg).
      const picked = pickRandom(creaturesResp.data ?? [], 5);
      creaturesForMap = picked.map((c) => ({
        slug: c.slug,
        common_name: c.common_name,
        latin_name: c.latin_name,
        photo_url: c.pic_file
          ? "/creature_photos/" + c.pic_file.split("/").pop()
          : null,
      }));
    } else {
      geocodeError = geo.error;
    }
  }

  // Top genera ranking for the overlay panel.
  const counts = new Map<string, number>();
  for (const t of trees) {
    if (t.genus_slug)
      counts.set(t.genus_slug, (counts.get(t.genus_slug) ?? 0) + 1);
  }
  const generaBySlug = new Map(allGenera.map((g) => [g.slug, g]));
  const classified = classifyGenera(allGenera);
  const classifiedBySlug = new Map(classified.map((c) => [c.slug, c]));
  const top = [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([slug, n]) => {
      const g = generaBySlug.get(slug);
      const c = classifiedBySlug.get(slug);
      return {
        slug,
        n,
        pct: trees.length === 0 ? 0 : (n / trees.length) * 100,
        dutch: g?.dutch_name ?? slug,
        rarity: c?.rarity ?? "common",
      };
    });

  return (
    <main className="play-page">
      <div className="play-map-stage">
        <PlayMap
          center={center}
          radiusM={RADIUS_M}
          creatures={creaturesForMap}
          trees={trees
            .filter((t) => t.latitude != null && t.longitude != null)
            .map((t) => ({
              id: t.id,
              lat: t.latitude!,
              lng: t.longitude!,
              slug: t.genus_slug ?? null,
              species: t.species_full ?? null,
              height_m: t.height_m ?? null,
              diameter_cm: t.diameter_cm ?? null,
              planting_year: t.planting_year ?? null,
              location: t.location ?? null,
              location_detail: t.location_detail ?? null,
              protection_status: t.protection_status ?? null,
            }))}
        />

        {/* Floating search panel, top-left of the map. */}
        <div className="play-search-overlay">
          <AddressInput defaultValue={address} />
          {geocodeError && (
            <p className="play-error-mini">{geocodeError}</p>
          )}
          {resolvedAddress && (
            <p className="play-meta-mini">
              <span>{resolvedAddress}</span>
              <span className="play-meta-counts">
                <b>{trees.length.toLocaleString()}</b> trees · <b>{counts.size}</b>{" "}
                genera
              </span>
            </p>
          )}
        </div>

        {/* Top genera overlay, top-right. Each row links to its wiki page. */}
        {top.length > 0 && (
          <aside className="play-overlay">
            <h2 className="play-overlay-h">Top genera</h2>
            <ol className="play-top">
              {top.map((row) => (
                <li key={row.slug} className={`rarity-${row.rarity}`}>
                  <Link
                    href={`/wiki/trees/${row.slug}`}
                    className="play-top-link"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      className="pixel"
                      src={`/sprites/${row.slug}.png`}
                      alt=""
                      width={32}
                      height={32}
                    />
                    <div className="play-top-body">
                      <div className="play-top-name">
                        <em>{row.slug}</em>{" "}
                        <span className="play-top-dutch">{row.dutch}</span>
                      </div>
                      <div className="play-top-meta">
                        {row.n.toLocaleString()} · {row.pct.toFixed(1)}%
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ol>
          </aside>
        )}
      </div>
    </main>
  );
}
