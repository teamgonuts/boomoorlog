"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AddressInput } from "@/components/AddressInput";
import { AreaPanel, type AreaCreature, type AreaTree } from "@/components/AreaPanel";
import PlayMap, { type Bbox } from "@/components/PlayMap";
import type { ViewportTreesResponse } from "@/lib/trees-api";

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
  const [loading, setLoading] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleViewportChange = useCallback((bbox: Bbox) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (abortRef.current) abortRef.current.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setLoading(true);

      const bboxStr = [bbox.lat_min, bbox.lng_min, bbox.lat_max, bbox.lng_max]
        .map((n) => n.toFixed(6))
        .join(",");
      fetch(`/api/trees?bbox=${encodeURIComponent(bboxStr)}`, { signal: ac.signal })
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
          // eslint-disable-next-line no-console
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
    if (genusSet.size === 0) return [];
    return props.allCreatures
      .filter((c) => c.tree_genera.some((g) => genusSet.has(g)))
      .map((c) => ({
        slug: c.slug,
        common_name: c.common_name,
        latin_name: c.latin_name,
      }))
      .sort((a, b) => a.common_name.localeCompare(b.common_name));
  }, [data, props.allCreatures]);

  const markers = data?.markers ?? [];
  const total = data?.total ?? 0;
  const generaCount = data?.topGenera.length ?? 0;

  return (
    <main className="play-page">
      <div className="play-map-stage">
        <PlayMap
          center={props.center}
          initialRadiusM={props.initialRadiusM}
          creatures={props.creaturesForMap}
          markers={markers}
          onViewportChange={handleViewportChange}
        />

        {/* Floating search panel, top-left of the map. */}
        <div className="play-search-overlay">
          <AddressInput defaultValue={props.address} />
          {props.geocodeError && (
            <p className="play-error-mini">{props.geocodeError}</p>
          )}
          {props.resolvedAddress && (
            <p className="play-meta-mini">
              <span>{props.resolvedAddress}</span>
              <span className="play-meta-counts">
                {loading && data === null ? (
                  <span className="play-meta-loading">loading…</span>
                ) : (
                  <>
                    <b>{total.toLocaleString()}</b> trees · <b>{generaCount}</b>{" "}
                    genera
                  </>
                )}
              </span>
            </p>
          )}
        </div>

        {/* Area panel — hides cleanly until the first viewport response lands. */}
        {(areaTrees.length > 0 || areaCreatures.length > 0) && (
          <AreaPanel trees={areaTrees} creatures={areaCreatures} />
        )}
      </div>
    </main>
  );
}
