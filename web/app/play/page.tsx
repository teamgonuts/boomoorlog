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

const RADIUS_M = 250;
// Supabase's PostgREST caps every request at 1000 rows. Page through it.
const PAGE_SIZE = 1000;
// Same key the AddressInput writes on the client.
const COOKIE_NAME = "lastAddress";

async function fetchAllTreesWithin(
  lat: number,
  lng: number,
  radius_m: number,
): Promise<Tree[]> {
  const out: Tree[] = [];
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .rpc("trees_within_radius", { lat, lng, radius_m })
      .range(from, from + PAGE_SIZE - 1);
    if (error) throw new Error(`trees_within_radius: ${error.message}`);
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

  if (address) {
    const geo = await geocodeAmsterdam(address);
    if (isGeocodeHit(geo)) {
      center = { lat: geo.lat, lng: geo.lng };
      resolvedAddress = geo.display_name;
      const [treeList, gResp] = await Promise.all([
        fetchAllTreesWithin(geo.lat, geo.lng, RADIUS_M),
        supabase.from("genera").select("*"),
      ]);
      trees = treeList;
      allGenera = gResp.data ?? [];
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
