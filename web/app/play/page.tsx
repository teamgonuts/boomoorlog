import { readdirSync } from "node:fs";
import { join } from "node:path";

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

// Initial-fit radius around a geocoded address, in meters. PlayMap multiplies
// by 2 to derive a bounds side, so the rendered view is roughly a 2*R square
// around the address. 250 keeps the neighborhood readable without falling
// into the citywide-bbox slow path.
const INITIAL_RADIUS_M = 250;

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

  // Geocode when we have an address; the bbox query and rendering happen
  // client-side in PlayClient now (viewport-driven). With no address, the
  // map opens at the Amsterdam-center default (PlayMap.AMSTERDAM_CENTER /
  // AMSTERDAM_ZOOM) and /api/trees fetches markers for THAT viewport.
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
  // creatures tables). Cheap: ~167 trees + ~360 displayable creatures.
  const [treesResp, creaturesResp] = await Promise.all([
    supabase.from("organisms").select("*").eq("category", "tree"),
    // Only organisms that actually have a sprite on disk go to the map —
    // the long-tail observation organisms (~2.2k rows) have photo_path set
    // to a remote iNat URL but no local sprite, and including them produced
    // a flood of /creature_sprites/<slug>.png 404s.
    supabase
      .from("organisms")
      .select(
        "slug, common_name, latin_name, photo_path, tree_genera, sprite_pending, habitat_classes",
      )
      .neq("category", "tree")
      .not("sprite_path", "is", null)
      .eq("sprite_pending", false)
      .range(0, 1999),
  ]);
  const allGenera = treesResp.data ?? [];
  const allCreaturesRaw = creaturesResp.data ?? [];

  // Fetch latest observation date per organism from the migration-033 view.
  // Supabase caps a single request at 1000 rows, so we page through until we
  // see a short response. ~2.3k rows today → 3 round trips. The view is also
  // queried for organisms we don't render (the ~2k observation-only long tail);
  // filtering server-side would save bytes but the payload is already tiny.
  const latestByOrganism = new Map<string, string>();
  const PAGE_SIZE = 1000;
  type SightingRow = { organism_slug: string | null; last_observed_on: string | null };
  const sightingClient = supabase as unknown as {
    from: (t: string) => {
      select: (cols: string) => {
        range: (a: number, b: number) => Promise<{ data: SightingRow[] | null }>;
      };
    };
  };
  for (let offset = 0; offset < 10_000; offset += PAGE_SIZE) {
    const page = await sightingClient
      .from("organism_latest_sighting")
      .select("organism_slug, last_observed_on")
      .range(offset, offset + PAGE_SIZE - 1);
    const rows = page.data ?? [];
    for (const row of rows) {
      if (row.organism_slug && row.last_observed_on) {
        latestByOrganism.set(row.organism_slug, row.last_observed_on);
      }
    }
    if (rows.length < PAGE_SIZE) break;
  }

  // Static list of tree genera whose hero photo lives in web/public/photos/.
  // Read at request time (force-dynamic) — the folder has ~55 .jpg files and
  // readdirSync against the local filesystem is sub-millisecond. The hover
  // tooltip only shows the photo block for slugs in this set, so the ~110
  // genera without a curated photo render text-only instead of broken-image.
  let treePhotoSlugs: string[] = [];
  try {
    treePhotoSlugs = readdirSync(join(process.cwd(), "public", "photos"))
      .filter((name) => name.toLowerCase().endsWith(".jpg"))
      .map((name) => name.replace(/\.jpg$/i, ""));
  } catch {
    // Folder missing in some deploy targets — fall back to empty list, which
    // just means no photo block in tooltips. Not fatal.
  }

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
  // The sprite_path / sprite_pending filters already happened server-side;
  // we still skip rows with no photo_path so the hover tooltip has something
  // to show (rare — curated creatures almost always have one).
  const creaturesForMap: CreatureForMap[] = allCreaturesRaw
    .filter((c) => c.photo_path)
    .map((c) => ({
      slug: c.slug,
      common_name: c.common_name ?? c.latin_name,
      latin_name: c.latin_name,
      photo_url: "/creature_photos/" + c.photo_path!.split("/").pop(),
      last_observed_on: latestByOrganism.get(c.slug) ?? null,
      habitat_classes: c.habitat_classes ?? [],
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
      treePhotoSlugs={treePhotoSlugs}
    />
  );
}
