import { AddressInput } from "@/components/AddressInput";
import PlayMap from "@/components/PlayMap";
import { classifyGenera } from "@/lib/archetype";
import { geocodeAmsterdam, isGeocodeHit } from "@/lib/geocode";
import { supabase } from "@/lib/supabase";
import type { Genus, Tree } from "@/types/supabase";

// Spatial query + Nominatim → never cache the page.
export const dynamic = "force-dynamic";

const RADIUS_M = 500;
// Supabase's PostgREST caps every request at 1000 rows. Page through it.
const PAGE_SIZE = 1000;

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
    if (from > 50_000) break; // safety stop
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

  return (
    <main className="play-page">
      <section className="play-search">
        <AddressInput defaultValue={address} />
      </section>

      {address ? (
        <PlayResults address={address} />
      ) : (
        <p className="play-empty">
          Type an address above to see the trees that defend your neighborhood.
        </p>
      )}
    </main>
  );
}

async function PlayResults({ address }: { address: string }) {
  const geo = await geocodeAmsterdam(address);
  if (!isGeocodeHit(geo)) {
    return (
      <section className="play-error">
        <p>
          <strong>{geo.error}</strong>
        </p>
        <p>
          Try a more specific address — e.g. <em>Dam 1, Amsterdam</em> or{" "}
          <em>Vondelpark 5</em>.
        </p>
      </section>
    );
  }

  const [treeList, { data: allGenera }] = await Promise.all([
    fetchAllTreesWithin(geo.lat, geo.lng, RADIUS_M),
    supabase.from("genera").select("*"),
  ]);

  const generaList: Genus[] = allGenera ?? [];
  const generaBySlug = new Map(generaList.map((g) => [g.slug, g]));

  const counts = new Map<string, number>();
  for (const t of treeList) {
    if (t.genus_slug)
      counts.set(t.genus_slug, (counts.get(t.genus_slug) ?? 0) + 1);
  }
  const classified = classifyGenera(generaList);
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
        pct: treeList.length === 0 ? 0 : (n / treeList.length) * 100,
        dutch: g?.dutch_name ?? slug,
        archetype: c?.archetype ?? null,
        rarity: c?.rarity ?? "common",
      };
    });

  return (
    <section className="play-result-v2">
      <div className="play-where-bar">
        <strong className="play-where-addr">{geo.display_name}</strong>
        <span className="play-where-meta">
          <b>{treeList.length.toLocaleString()}</b> trees ·{" "}
          <b>{counts.size}</b> genera within {RADIUS_M}&nbsp;m
        </span>
      </div>

      <div className="play-map-wrapper">
        <PlayMap
          center={{ lat: geo.lat, lng: geo.lng }}
          radiusM={RADIUS_M}
          trees={treeList
            .filter((t) => t.latitude != null && t.longitude != null)
            .map((t) => ({
              id: t.id,
              lat: t.latitude!,
              lng: t.longitude!,
              slug: t.genus_slug ?? null,
              height_m: t.height_m ?? null,
            }))}
        />
        <aside className="play-overlay">
          <h2 className="play-overlay-h">Top genera</h2>
          <ol className="play-top">
            {top.map((row) => (
              <li key={row.slug} className={`rarity-${row.rarity}`}>
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
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </section>
  );
}
