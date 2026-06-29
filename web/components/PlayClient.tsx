"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AddressInput } from "@/components/AddressInput";
import { AdminPanel, useAdminSettings } from "@/components/AdminPanel";
import { AreaPanel, type AreaCreature, type AreaTree } from "@/components/AreaPanel";
import type { Bbox } from "@/components/PlayMap";
import type { ViewportTreesResponse } from "@/lib/trees-api";

// Leaflet touches `window` at module-load time, so the map component is
// client-only. Dynamic import with ssr:false skips it during SSR.
const PlayMap = dynamic(() => import("@/components/PlayMap"), { ssr: false });

/**
 * Static metadata about a genus the area panel needs (Dutch name + rarity).
 * We fetch this server-side once per page and pass it down — the same data
 * for every viewport, no point requerying.
 */
export type GenusMeta = {
  slug: string;
  dutch: string;
  rarity: "common" | "notable" | "rare";
};

/** Creature row needed to filter the area-panel list by current viewport. */
export type AllCreatureForFilter = {
  slug: string;
  common_name: string;
  latin_name: string | null;
  tree_genera: string[];
};

/** Creature row needed to render the in-map flying sprite + hover tooltip. */
export type CreatureForMap = {
  slug: string;
  common_name: string;
  latin_name: string | null;
  photo_url: string | null;
};

type Props = {
  address: string;
  resolvedAddress: string | null;
  geocodeError: string | null;
  center: { lat: number; lng: number } | null;
  initialRadiusM: number;
  generaMeta: GenusMeta[];
  allCreatures: AllCreatureForFilter[];
  creaturesForMap: CreatureForMap[];
};

// Wait this long after the last moveend/zoomend before firing a fetch. Long
// enough to coalesce a continuous drag into one request; short enough to feel
// instant after the user lets go.
const VIEWPORT_DEBOUNCE_MS = 180;

/**
 * Client-side state holder for /play. Owns:
 *   - the viewport-driven /api/trees fetch (debounced + abortable)
 *   - the derived AreaPanel data (top genera filtered by viewport, creatures
 *     filtered by tree-genera overlap with the viewport)
 *
 * page.tsx (server) just geocodes + fetches static metadata, then hands off
 * here. The Leaflet map lives in PlayMap; this component is the glue.
 */
export default function PlayClient(props: Props) {
  const [data, setData] = useState<ViewportTreesResponse | null>(null);
  // True from the moment the user starts moving the map until the matching
  // /api/trees response lands. Drives the floating "Loading…" pill so the
  // user knows pan/zoom is being honored even before pins refresh.
  const [loading, setLoading] = useState(false);

  // Admin/dev sliders — see AdminPanel.tsx. Hydrates from localStorage so a
  // tester's tuning survives a refresh. Read by the /api/trees fetch (treeCap)
  // and forwarded to PlayMap (creatureSlots, creatureSpeedMps).
  const [adminSettings, setAdminSettings] = useAdminSettings();
  const treeCapRef = useRef(adminSettings.treeCap);

  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Remember the last viewport we fetched for so we can re-fire when the
  // tree-cap slider moves (otherwise nothing happens until the user pans).
  const lastBboxRef = useRef<Bbox | null>(null);

  const handleViewportChange = useCallback((bbox: Bbox) => {
    lastBboxRef.current = bbox;
    setLoading(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (abortRef.current) abortRef.current.abort();
      const ac = new AbortController();
      abortRef.current = ac;

      const bboxStr = [bbox.lat_min, bbox.lng_min, bbox.lat_max, bbox.lng_max]
        .map((n) => n.toFixed(6))
        .join(",");
      // Read the live cap from ref so slider changes take effect on the next
      // viewport fetch without remounting the map or rebuilding the callback.
      // cells_per_side scales with cap — the RPC produces one winner per grid
      // cell, so a 10x10 grid (default) hard-caps the result at 100 regardless
      // of max_pins. Use ceil(sqrt(cap)) to make the grid match.
      const cap = treeCapRef.current;
      const cellsPerSide = Math.min(40, Math.max(4, Math.ceil(Math.sqrt(cap))));
      const url =
        `/api/trees?bbox=${encodeURIComponent(bboxStr)}` +
        `&max_pins=${cap}` +
        `&cells_per_side=${cellsPerSide}`;
      fetch(url, { signal: ac.signal })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json() as Promise<ViewportTreesResponse>;
        })
        .then((json) => {
          if (ac.signal.aborted) return;
          setData(json);
          setLoading(false);
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          console.error("/api/trees", err);
          setLoading(false);
        });
    }, VIEWPORT_DEBOUNCE_MS);
  }, []);

  // Cancel any pending request when this component unmounts.
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  // When the tree-cap slider moves, push the new value into the ref AND
  // immediately re-fire the viewport fetch using the last-seen bbox. Without
  // this, the change only takes effect on the next pan/zoom, which makes the
  // slider feel broken.
  useEffect(() => {
    treeCapRef.current = adminSettings.treeCap;
    if (lastBboxRef.current) {
      handleViewportChange(lastBboxRef.current);
    }
  }, [adminSettings.treeCap, handleViewportChange]);

  // ---- Derive AreaPanel data ----
  const generaMetaBySlug = useMemo(
    () => new Map(props.generaMeta.map((g) => [g.slug, g])),
    [props.generaMeta],
  );

  const areaTrees: AreaTree[] = useMemo(() => {
    const top = data?.topGenera ?? [];
    return top.map((g) => {
      const meta = generaMetaBySlug.get(g.slug);
      return {
        slug: g.slug,
        n: g.n,
        pct: g.pct,
        dutch: meta?.dutch ?? g.slug,
        rarity: meta?.rarity ?? "common",
      };
    });
  }, [data, generaMetaBySlug]);

  const areaCreatures: AreaCreature[] = useMemo(() => {
    const genusSet = new Set((data?.topGenera ?? []).map((g) => g.slug));
    const observedSlugs = new Set(data?.creatureSlugs ?? []);
    // Union: include a creature if its tree_genera overlap the viewport
    // (curated path) OR if it has at least one observation inside the viewport
    // bbox (auto-promoted path — those rows have empty tree_genera).
    if (genusSet.size === 0 && observedSlugs.size === 0) return [];
    return props.allCreatures
      .filter(
        (c) =>
          c.tree_genera.some((g) => genusSet.has(g)) ||
          observedSlugs.has(c.slug),
      )
      .map((c) => ({
        slug: c.slug,
        common_name: c.common_name,
        latin_name: c.latin_name,
      }))
      .sort((a, b) => a.common_name.localeCompare(b.common_name));
  }, [data, props.allCreatures]);

  const markers = data?.markers ?? [];

  return (
    <main className="play-page">
      <div className="play-map-stage">
        <PlayMap
          center={props.center}
          initialRadiusM={props.initialRadiusM}
          creatures={props.creaturesForMap}
          markers={markers}
          onViewportChange={handleViewportChange}
          creatureSlots={adminSettings.creatureSlots}
          creatureSpeedMps={adminSettings.creatureSpeedMps}
        />

        {/* Floating search panel, top-left of the map. */}
        <div className="play-search-overlay">
          <AddressInput defaultValue={props.address} />
          {props.geocodeError && (
            <p className="play-error-mini">{props.geocodeError}</p>
          )}
        </div>

        {/* Admin/dev controls — closed by default, sits to the left of the
            area-panel collapsed handle. */}
        <AdminPanel settings={adminSettings} onChange={setAdminSettings} />

        {/* Floating loading indicator, top-center. Visible whenever a new
            /api/trees request is in flight after pan/zoom. */}
        {loading && (
          <div className="play-loading" role="status" aria-live="polite">
            <span className="play-loading-spinner" aria-hidden="true" />
            <span>Loading…</span>
          </div>
        )}

        {/* Area panel — hides cleanly until the first viewport response lands. */}
        {(areaTrees.length > 0 || areaCreatures.length > 0) && (
          <AreaPanel trees={areaTrees} creatures={areaCreatures} />
        )}
      </div>
    </main>
  );
}
