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
import type { Genus, Organism } from "@/types/supabase";

// Same shim pattern as the wiki pages — drops in step 9.
function organismToGenus(o: Organism): Genus {
  return {
    slug: o.slug,
    latin_name: o.latin_name,
    dutch_name: o.dutch_name,
    display_name: o.display_name,
    attack: o.attack,
    range: o.range,
    health: o.health,
    attack_speed: o.attack_speed,
    move_speed: o.move_speed,
    world_rarity_multiplier: o.world_rarity_multiplier,
    avg_height_m: o.avg_height_m,
    avg_diameter_cm: o.avg_diameter_cm,
    personality: o.personality,
    tree_count: o.tree_count,
    sprite_path: o.sprite_path,
    lore: o.lore,
    created_at: o.created_at,
  };
}

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
  // the client. Two filtered queries against organisms (was: genera +
  // creatures tables). Cheap: ~167 trees + ~360 creatures.
  const [treesResp, creaturesResp] = await Promise.all([
    supabase.from("organisms").select("*").eq("category", "tree"),
    supabase
      .from("organisms")
      .select(
        "slug, common_name, latin_name, photo_path, tree_genera, sprite_pending",
      )
      .neq("category", "tree")
      .range(0, 1999),
  ]);
  const allGenera = (treesResp.data ?? []).map(organismToGenus);
  const allCreaturesRaw = creaturesResp.data ?? [];

  // dutch + rarity per slug for the area panel.
  const generaBySlug = new Map(allGenera.map((g) => [g.slug, g]));
  const classified = classifyGenera(allGenera);
  const generaMeta: GenusMeta[] = classified.map((c) => ({
    slug: c.slug,
    dutch: generaBySlug.get(c.slug)?.dutch_name ?? c.slug,
    rarity: c.rarity,
  }));

  // `photo_path` is the canonical photo location (legacy creatures.pic_file
  // values were copied across in migration 021 unchanged). We mirror the
  // pipeline tree at `web/public/creature_photos/`, so swap the prefix
  // (preserving the original extension — most are .jpg, a few .png, one .jpeg).
  //
  // Skip rows with `sprite_pending` (auto-promoted creatures whose pixel-art
  // sprite hasn't been generated yet — rendering them would yield a broken
  // <img>). Also require a non-null photo_path so we never queue a flier with
  // no photo to show.
  const creaturesForMap: CreatureForMap[] = allCreaturesRaw
    .filter((c) => c.photo_path && !c.sprite_pending)
    .map((c) => ({
      slug: c.slug,
      common_name: c.common_name ?? c.latin_name,
      latin_name: c.latin_name,
      photo_url: "/creature_photos/" + c.photo_path!.split("/").pop(),
    }));

  // Light shape for the area-panel filter (tree_genera overlap).
  const allCreatures: AllCreatureForFilter[] = allCreaturesRaw.map((c) => ({
    slug: c.slug,
    common_name: c.common_name ?? c.latin_name,
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
