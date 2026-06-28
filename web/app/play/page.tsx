import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import PlayClient, {
  type AllCreatureForFilter,
  type CreatureForMap,
  type GenusMeta,
} from "@/components/PlayClient";
import { classifyGenera } from "@/lib/archetype";
import { geocodeAmsterdam, isGeocodeHit } from "@/lib/geocode";
import { supabase } from "@/lib/supabase";

// Geocode call → never cache the page.
export const dynamic = "force-dynamic";

// Half-side of the initial fitBounds box around a geocoded address, in meters.
// The map is viewport-driven now, so this only sets the FIRST view; afterwards
// the user controls zoom/pan and /api/trees refetches on every moveend.
const INITIAL_RADIUS_M = 100;
const COOKIE_NAME = "lastAddress";

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

  // Geocode when we have an address; the bbox query and rendering happen
  // client-side in PlayClient now (viewport-driven).
  let center: { lat: number; lng: number } | null = null;
  let resolvedAddress: string | null = null;
  let geocodeError: string | null = null;

  if (address) {
    const geo = await geocodeAmsterdam(address);
    if (isGeocodeHit(geo)) {
      center = { lat: geo.lat, lng: geo.lng };
      resolvedAddress = geo.display_name;
    } else {
      geocodeError = geo.error;
    }
  }

  // Static metadata — same for every viewport, fetched once and handed to
  // the client. Cheap (genera ≈ 167 rows, creatures ≈ 50 rows).
  const [gResp, creaturesResp] = await Promise.all([
    supabase.from("genera").select("*"),
    supabase
      .from("creatures")
      .select(
        "slug, common_name, latin_name, pic_file, tree_genera, sprite_pending",
      ),
  ]);
  const allGenera = gResp.data ?? [];
  const allCreaturesRaw = creaturesResp.data ?? [];

  // dutch + rarity per slug for the area panel.
  const generaBySlug = new Map(allGenera.map((g) => [g.slug, g]));
  const classified = classifyGenera(allGenera);
  const generaMeta: GenusMeta[] = classified.map((c) => ({
    slug: c.slug,
    dutch: generaBySlug.get(c.slug)?.dutch_name ?? c.slug,
    rarity: c.rarity,
  }));

  // `pic_file` is the original pipeline path (e.g. `data/creature_pics/foo.jpg`);
  // we mirror those files at `web/public/creature_photos/`, so swap the prefix
  // (preserving the original extension — most are .jpg, a few .png, one .jpeg).
  //
  // Skip rows with `sprite_pending` (auto-promoted creatures whose pixel-art
  // sprite hasn't been generated yet — rendering them would yield a broken
  // <img>). Also require a non-null pic_file so we never queue a flier with no
  // photo to show.
  const creaturesForMap: CreatureForMap[] = allCreaturesRaw
    .filter((c) => c.pic_file && !c.sprite_pending)
    .map((c) => ({
      slug: c.slug,
      common_name: c.common_name,
      latin_name: c.latin_name,
      photo_url: "/creature_photos/" + c.pic_file!.split("/").pop(),
    }));

  // Light shape for the area-panel filter (tree_genera overlap).
  const allCreatures: AllCreatureForFilter[] = allCreaturesRaw.map((c) => ({
    slug: c.slug,
    common_name: c.common_name,
    latin_name: c.latin_name,
    tree_genera: c.tree_genera,
  }));

  return (
    <PlayClient
      address={address}
      resolvedAddress={resolvedAddress}
      geocodeError={geocodeError}
      center={center}
      initialRadiusM={INITIAL_RADIUS_M}
      generaMeta={generaMeta}
      allCreatures={allCreatures}
      creaturesForMap={creaturesForMap}
    />
  );
}
