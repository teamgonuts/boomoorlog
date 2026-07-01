"use client";

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import type { ViewportMarker } from "@/lib/trees-api";

// OpenFreeMap Liberty — vector tiles, buttery zoom, warm palette that mirrors
// the previous CARTO Voyager (beige residential, soft greens, yellow/orange
// roads, blue water). Free, no key.
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

// Map opens centered on Amsterdam if no address has been searched. Zoom 15
// is neighborhood-scale (a few hundred meters across) — wide enough to feel
// like "you can see your area" without triggering the citywide-bbox slow
// path on /api/trees.
const AMSTERDAM_CENTER: [number, number] = [4.9041, 52.3676]; // [lng, lat] for MapLibre
const AMSTERDAM_ZOOM = 15;

// Today's calendar year. Used to compute ages. Fine to refresh on a 1-yr cadence.
const CURRENT_YEAR = new Date().getFullYear();

// Creature density. Slot count scales with √(viewport km²): zoom out → more
// creatures, zoom in → fewer. Square-root keeps city view from clumping while
// still feeling more alive than a 1km neighborhood. Tune by eye.
const CREATURE_K = 3;
const CREATURE_MIN_SLOTS = 4;
const CREATURE_MAX_SLOTS = 14;

function slotsForBounds(bounds: maplibregl.LngLatBounds): number {
  const south = bounds.getSouth();
  const north = bounds.getNorth();
  const latKm = (north - south) * 111.32;
  const cosLat = Math.cos((((south + north) / 2) * Math.PI) / 180);
  const lngKm = (bounds.getEast() - bounds.getWest()) * 111.32 * cosLat;
  const areaKm2 = Math.max(0, latKm * lngKm);
  const raw = Math.round(CREATURE_K * Math.sqrt(areaKm2));
  return Math.max(CREATURE_MIN_SLOTS, Math.min(CREATURE_MAX_SLOTS, raw));
}

// Translations for the Dutch open-data protection field. Anything not listed
// falls back to the original Dutch (better than dropping it).
const PROTECTION_EN: Record<string, string> = {
  "Monumentale boom": "Monumental tree",
  "Bijzondere boom": "Special tree",
};

function en(map: Record<string, string>, value: string): string {
  return map[value] ?? value;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Re-export so callers can `import type { Marker } from "@/components/PlayMap"`.
// Single source of truth lives in lib/trees-api.ts (also used by /api/trees).
export type Marker = ViewportMarker;

function treePhotoBlock(slug: string | null, photoSlugs: Set<string>): string {
  if (!slug || !photoSlugs.has(slug)) return "";
  return `<div class="ttl-photo"><img src="/photos/${encodeURIComponent(slug)}.jpg" alt="" loading="lazy" /></div>`;
}

function tooltipForIndividual(t: Marker, photoSlugs: Set<string>): string {
  const body: string[] = [];
  const title = t.species ?? t.slug ?? "Unknown tree";
  body.push(`<div class="ttl-h">${escapeHtml(title)}</div>`);

  const stats: string[] = [];
  if (t.height_m != null) stats.push(`${t.height_m} m`);
  if (t.diameter_cm != null) stats.push(`&Oslash; ${t.diameter_cm} cm`);
  if (t.planting_year != null) {
    const age = CURRENT_YEAR - t.planting_year;
    if (age >= 0 && age < 400) stats.push(`${age} yrs`);
  }
  if (stats.length > 0) {
    body.push(`<div class="ttl-stats">${stats.join(" · ")}</div>`);
  }

  if (
    t.planting_year != null &&
    t.planting_year >= 1500 &&
    t.planting_year <= CURRENT_YEAR + 1
  ) {
    body.push(`<div class="ttl-ctx">Planted in ${t.planting_year}</div>`);
  }

  if (t.protection_status) {
    body.push(
      `<div class="ttl-protected">★ ${escapeHtml(
        en(PROTECTION_EN, t.protection_status),
      )}</div>`,
    );
  }

  return treePhotoBlock(t.slug, photoSlugs) + `<div class="ttl-body">${body.join("")}</div>`;
}

function tooltipForCluster(m: Marker, photoSlugs: Set<string>): string {
  const slug = m.slug ?? "mixed";
  const body =
    `<div class="ttl-h">${escapeHtml(slug)}</div>` +
    `<div class="ttl-stats">${m.n.toLocaleString()} trees · click to zoom</div>`;
  return treePhotoBlock(m.slug, photoSlugs) + `<div class="ttl-body">${body}</div>`;
}

const EMPTY_SLUG_SET: Set<string> = new Set();

// Build an HTML element for an individual tree marker. Returns anchor `bottom`
// so the sprite foot sits on the coordinate (matches previous L.icon anchor).
function elementForIndividual(slug: string | null): {
  el: HTMLElement;
  anchor: maplibregl.PositionAnchor;
} {
  if (!slug) {
    const dot = document.createElement("div");
    dot.className = "tree-dot";
    dot.style.width = "6px";
    dot.style.height = "6px";
    return { el: dot, anchor: "center" };
  }
  const img = document.createElement("img");
  img.className = "tree-pin";
  img.src = `/sprites/${slug}.png`;
  img.alt = "";
  img.width = 22;
  img.height = 28;
  img.style.display = "block";
  return { el: img, anchor: "bottom" };
}

function elementForCluster(
  slug: string | null,
  n: number,
): { el: HTMLElement; anchor: maplibregl.PositionAnchor } {
  const wrap = document.createElement("div");
  wrap.className = "tree-cluster";
  const sprite = slug
    ? `<img class="tree-cluster-sprite pixel" src="/sprites/${slug}.png" alt="" />`
    : `<span class="tree-cluster-dot"></span>`;
  const label =
    n >= 1000 ? (n / 1000).toFixed(n >= 10_000 ? 0 : 1) + "k" : String(n);
  wrap.innerHTML = `${sprite}<span class="tree-cluster-count">${label}</span>`;
  return { el: wrap, anchor: "bottom" };
}

// Attach a hover-triggered popup to a MapLibre marker. Uses one popup per
// marker (cheap enough at ~400 markers cap) and toggles on mouseenter/leave.
function attachHoverTooltip(
  marker: maplibregl.Marker,
  html: string,
  className: string,
  map: maplibregl.Map,
) {
  const popup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: false,
    className,
    offset: 12,
    anchor: "bottom",
    maxWidth: "260px",
  }).setHTML(html);
  const el = marker.getElement();
  el.addEventListener("mouseenter", () => {
    popup.setLngLat(marker.getLngLat()).addTo(map);
  });
  el.addEventListener("mouseleave", () => {
    popup.remove();
  });
  // If the marker moves (creature flights), keep popup pinned to it.
  return { popup };
}

/** Creature data needed to render + identify the marker on hover. */
type CreatureForMap = {
  slug: string;
  common_name: string;
  latin_name: string | null;
  photo_url: string | null;
  /** ISO date (YYYY-MM-DD) of the most recent observation of this species,
   *  or null if we have no observations on file. Drives the "Last spotted X
   *  ago" line in the hover tooltip. */
  last_observed_on: string | null;
};

/**
 * Format an ISO observation date as a human-friendly "X ago" line. Returns
 * null when the date is missing or invalid so callers can skip the line.
 * Granularity is day-level because observations only store `observed_on date`.
 */
function formatLastSeen(observedOn: string | null): string | null {
  if (!observedOn) return null;
  const obs = new Date(observedOn + "T00:00:00Z").getTime();
  if (!Number.isFinite(obs)) return null;
  const now = Date.now();
  const days = Math.floor((now - obs) / 86_400_000);
  if (days < 0) return "Spotted today";
  if (days === 0) return "Last spotted today";
  if (days === 1) return "Last spotted yesterday";
  if (days < 30) return `Last spotted ${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 9) return `Last spotted ${weeks} weeks ago`;
  const months = Math.floor(days / 30);
  if (months < 24) return `Last spotted ${months} ${months === 1 ? "month" : "months"} ago`;
  const years = Math.floor(days / 365);
  return `Last spotted ${years} ${years === 1 ? "year" : "years"} ago`;
}

function escapeForAttr(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

type FlyPoint = { lat: number; lng: number };

/**
 * Animate a creature sprite making ONE flight between two points, then perch
 * and disappear. Reads the "where can I land" point list from a ref so the
 * creature loop survives marker prop changes (parent updates the ref when
 * new /api/trees responses land). Calls `onComplete` when the flight finishes
 * — the parent uses that to respawn a fresh pick in the same slot.
 */
function startCreatureFlight(
  map: maplibregl.Map,
  activeMarkers: Set<maplibregl.Marker>,
  creature: CreatureForMap,
  pointsRef: { current: FlyPoint[] },
  speedMps: number,
  onComplete: () => void,
): () => void {
  const points = pointsRef.current;
  if (points.length < 2) {
    onComplete();
    return () => {};
  }

  const SPEED_MPS = speedMps;
  const PERCH_MS = 500;
  const MIN_DURATION_MS = 800;

  const el = document.createElement("div");
  el.className = "creature-flying";
  el.style.width = "56px";
  el.style.height = "40px";
  el.innerHTML = `<img src="/creature_sprites/${creature.slug}.png" alt="" />`;

  const fromIdx = Math.floor(Math.random() * points.length);
  let toIdx = Math.floor(Math.random() * points.length);
  if (toIdx === fromIdx) toIdx = (toIdx + 1) % points.length;
  const from = points[fromIdx];
  const to = points[toIdx];

  const marker = new maplibregl.Marker({ element: el, anchor: "center" })
    .setLngLat([from.lng, from.lat])
    .addTo(map);
  activeMarkers.add(marker);

  const photoBlock = creature.photo_url
    ? `<div class="creature-tip-photo"><img src="${escapeForAttr(creature.photo_url)}" alt="" loading="lazy" /></div>`
    : "";
  const latinLine = creature.latin_name
    ? `<div class="creature-tip-latin">${escapeForAttr(creature.latin_name)}</div>`
    : "";
  const lastSeen = formatLastSeen(creature.last_observed_on);
  const lastSeenLine = lastSeen
    ? `<div class="creature-tip-lastseen">${escapeForAttr(lastSeen)}</div>`
    : "";
  const tipHTML =
    photoBlock +
    `<div class="creature-tip-name">${escapeForAttr(creature.common_name)}</div>` +
    latinLine +
    lastSeenLine;
  const popup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: false,
    className: "creature-tip",
    offset: 20,
    anchor: "bottom",
    maxWidth: "240px",
  }).setHTML(tipHTML);
  el.addEventListener("mouseenter", () => {
    popup.setLngLat(marker.getLngLat()).addTo(map);
  });
  el.addEventListener("mouseleave", () => {
    popup.remove();
  });

  // Click → open this creature's wiki page in a new tab. Note: the creature is
  // a moving target while in flight; the click hit-area is the sprite itself
  // so the user has to chase it. The brief perch at the end of each flight
  // makes it easier (the marker is stationary for PERCH_MS).
  el.addEventListener("click", (e) => {
    e.stopPropagation();
    window.open(`/wiki/creatures/${creature.slug}`, "_blank", "noopener");
  });

  function metersBetween(a: FlyPoint, b: FlyPoint): number {
    const dLat = (b.lat - a.lat) * 111_320;
    const cosLat = Math.cos((a.lat * Math.PI) / 180);
    const dLng = (b.lng - a.lng) * 111_320 * cosLat;
    return Math.hypot(dLat, dLng);
  }

  function setSpriteRotation() {
    const img = el.querySelector("img") as HTMLImageElement | null;
    if (!img) return;
    const dLat = to.lat - from.lat;
    const dLng = to.lng - from.lng;
    const angleDeg = (Math.atan2(-dLat, dLng) * 180) / Math.PI;
    img.style.transform =
      Math.abs(angleDeg) > 90 ? "scaleX(-1)" : `rotate(${angleDeg}deg)`;
  }

  const segmentStart = performance.now();
  const segmentDurMs = Math.max(
    MIN_DURATION_MS,
    (metersBetween(from, to) / SPEED_MPS) * 1000,
  );
  setSpriteRotation();

  let mode: "flying" | "perched" = "flying";
  let perchUntil = 0;
  let running = true;

  function tick(now: number) {
    if (!running) return;
    if (mode === "flying") {
      const t = Math.min(1, (now - segmentStart) / segmentDurMs);
      const lat = from.lat + (to.lat - from.lat) * t;
      const lng = from.lng + (to.lng - from.lng) * t;
      marker.setLngLat([lng, lat]);
      // Keep popup pinned if it's currently visible.
      if (popup.isOpen()) popup.setLngLat([lng, lat]);
      if (t >= 1) {
        mode = "perched";
        perchUntil = now + PERCH_MS;
      }
    } else if (now >= perchUntil) {
      // Journey done — disappear and let the parent spawn a replacement.
      running = false;
      popup.remove();
      marker.remove();
      activeMarkers.delete(marker);
      onComplete();
      return;
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  return () => {
    running = false;
    popup.remove();
    marker.remove();
    activeMarkers.delete(marker);
  };
}

export type Bbox = {
  lat_min: number;
  lng_min: number;
  lat_max: number;
  lng_max: number;
};

// Compute a bounding box that is roughly a 2*radiusM square around a point,
// used for the initial fit-bounds when a new address is geocoded. Matches
// what Leaflet's `L.latLng(...).toBounds(N)` produced.
function boundsAround(
  lat: number,
  lng: number,
  radiusM: number,
): maplibregl.LngLatBoundsLike {
  const dLat = radiusM / 111_320;
  const dLng = radiusM / (111_320 * Math.cos((lat * Math.PI) / 180));
  return [
    [lng - dLng, lat - dLat],
    [lng + dLng, lat + dLat],
  ];
}

export default function PlayMap({
  center,
  initialRadiusM,
  markers,
  creatures,
  treePhotoSlugs,
  onViewportChange,
  creatureSlots,
  creatureSpeedMps,
}: {
  center: { lat: number; lng: number } | null;
  /** Half-side of the initial fitBounds box, in meters. Only used the first
   *  time a new `center` arrives — after that, the user controls the view. */
  initialRadiusM: number;
  markers: Marker[];
  creatures?: CreatureForMap[];
  /** Genus slugs that have a photo on disk at /photos/<slug>.jpg. Used to
   *  decide whether to include a photo block in the tree hover tooltip — we
   *  only have ~55 of these, so most clusters/markers gracefully render
   *  text-only. */
  treePhotoSlugs?: Set<string>;
  onViewportChange?: (bbox: Bbox, zoom: number) => void;
  /** Admin-panel override: force a specific creature-slot count instead of
   *  scaling with viewport area. Undefined keeps the viewport-area heuristic. */
  creatureSlots?: number;
  /** Admin-panel override: creature flight speed in m/s. */
  creatureSpeedMps?: number;
}) {
  const photoSlugSet = treePhotoSlugs ?? EMPTY_SLUG_SET;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  // A single address marker; we keep the handle to remove on center change.
  const addressMarkerRef = useRef<maplibregl.Marker | null>(null);
  // Marker handles keyed by Marker.key for diff-update on marker prop change.
  const markerHandlesRef = useRef<Map<string, maplibregl.Marker>>(new Map());
  // Active creature markers so cleanup can tear them all down.
  const creatureMarkersRef = useRef<Set<maplibregl.Marker>>(new Set());
  // Marker positions exposed to creature loops via ref so flights survive
  // marker-prop changes without restarting.
  const flyPointsRef = useRef<FlyPoint[]>([]);
  // Callback captured into the mount-effect via ref so identity churn from
  // the parent doesn't trigger a remap remount.
  const onViewportChangeRef = useRef(onViewportChange);
  useEffect(() => {
    onViewportChangeRef.current = onViewportChange;
  }, [onViewportChange]);
  // First-fit guard: only auto-fit when a new center arrives. After that,
  // panning/zooming is the user's.
  const lastFitCenterRef = useRef<string | null>(null);
  // Style-loaded gate — moveend can fire before style.load in some flows.
  const styleReadyRef = useRef(false);

  // ---- Mount the map once ----
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: AMSTERDAM_CENTER,
      zoom: AMSTERDAM_ZOOM,
      attributionControl: { compact: true },
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "bottom-left",
    );
    mapRef.current = map;

    const emitViewport = () => {
      const b = map.getBounds();
      onViewportChangeRef.current?.(
        {
          lat_min: b.getSouth(),
          lng_min: b.getWest(),
          lat_max: b.getNorth(),
          lng_max: b.getEast(),
        },
        map.getZoom(),
      );
    };
    map.on("moveend", emitViewport);
    // Emit once the style has finished loading, so the parent picks up the
    // initial viewport (Leaflet fired moveend implicitly on mount; MapLibre
    // doesn't).
    const onStyleLoad = () => {
      styleReadyRef.current = true;
      emitViewport();
    };
    map.once("style.load", onStyleLoad);

    // Capture the marker-handles + creature-set up front so cleanup uses the
    // same instances the effect set up with.
    const handlesAtMount = markerHandlesRef.current;
    const creaturesAtMount = creatureMarkersRef.current;
    return () => {
      map.off("moveend", emitViewport);
      map.remove();
      mapRef.current = null;
      addressMarkerRef.current = null;
      styleReadyRef.current = false;
      handlesAtMount.clear();
      creaturesAtMount.clear();
    };
  }, []);

  // ---- Address pin + initial fit when center changes ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear any existing address marker.
    if (addressMarkerRef.current) {
      addressMarkerRef.current.remove();
      addressMarkerRef.current = null;
    }

    if (!center) {
      map.jumpTo({ center: AMSTERDAM_CENTER, zoom: AMSTERDAM_ZOOM });
      lastFitCenterRef.current = null;
      return;
    }

    // Small red dot, mirroring the previous L.circleMarker styling.
    const dot = document.createElement("div");
    dot.style.width = "12px";
    dot.style.height = "12px";
    dot.style.borderRadius = "50%";
    dot.style.background = "#c0463b";
    dot.style.border = "2px solid #c0463b";
    dot.style.boxShadow = "0 0 0 1px rgba(255,255,255,0.8)";
    dot.title = "Your address";
    const marker = new maplibregl.Marker({ element: dot, anchor: "center" })
      .setLngLat([center.lng, center.lat])
      .addTo(map);
    addressMarkerRef.current = marker;

    const centerKey = `${center.lat},${center.lng}`;
    if (lastFitCenterRef.current !== centerKey) {
      map.fitBounds(boundsAround(center.lat, center.lng, initialRadiusM), {
        padding: 40,
        maxZoom: 18,
        animate: false,
      });
      lastFitCenterRef.current = centerKey;
    }
  }, [center, initialRadiusM]);

  // ---- Markers: diff-update on prop change ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const handles = markerHandlesRef.current;
    const incoming = new Set(markers.map((m) => m.key));

    // Remove markers that fell out of the new set.
    for (const [key, handle] of handles) {
      if (!incoming.has(key)) {
        handle.remove();
        handles.delete(key);
      }
    }

    // Add markers that are new (kept-same markers are skipped, no churn).
    for (const m of markers) {
      if (handles.has(m.key)) continue;
      const { el, anchor } =
        m.mode === "cluster"
          ? elementForCluster(m.slug, m.n)
          : elementForIndividual(m.slug);
      const marker = new maplibregl.Marker({ element: el, anchor })
        .setLngLat([m.lng, m.lat])
        .addTo(map);
      const tip =
        m.mode === "cluster"
          ? tooltipForCluster(m, photoSlugSet)
          : tooltipForIndividual(m, photoSlugSet);
      attachHoverTooltip(marker, tip, "tree-tip", map);
      if (m.mode === "cluster") {
        // Click a cluster → drill in two zoom levels. Two levels usually
        // splits a dense cluster into finer ones (or unblocks individual mode
        // if total drops under max_pins).
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          const target = Math.min(map.getZoom() + 2, 19);
          map.jumpTo({ center: [m.lng, m.lat], zoom: target });
        });
      } else if (m.slug) {
        // Click an individual tree → open its genus wiki page in a new tab.
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          window.open(`/wiki/trees/${m.slug}`, "_blank", "noopener");
        });
      }
      handles.set(m.key, marker);
    }

    // Keep flyPointsRef in sync — creatures land on these on respawn. Using
    // marker centroids for both modes is fine; cluster centroids are still
    // "where trees are".
    flyPointsRef.current = markers.map((m) => ({ lat: m.lat, lng: m.lng }));
  }, [markers, photoSlugSet]);

  // ---- Creatures: spawn N slots, each respawns on completion ----
  // Depends on `markers` so the loop fully resets on every map change (pan or
  // zoom triggers a /api/trees refetch → new markers → cleanup tears every
  // creature down, then N fresh picks spawn against the new viewport's perches).
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const pool = creatures ?? [];
    if (pool.length === 0) return;

    // Admin override wins if provided (including 0 to disable creatures
    // entirely). Falls back to the viewport-area heuristic otherwise.
    const NUM_CREATURE_SLOTS =
      typeof creatureSlots === "number"
        ? creatureSlots
        : slotsForBounds(map.getBounds());
    if (NUM_CREATURE_SLOTS <= 0) return;
    const speed =
      typeof creatureSpeedMps === "number" && creatureSpeedMps > 0
        ? creatureSpeedMps
        : 6;
    const slotStops: Array<(() => void) | null> = Array(NUM_CREATURE_SLOTS).fill(null);
    const activeMarkers = creatureMarkersRef.current;
    let mounted = true;

    const spawnSlot = (slot: number) => {
      if (!mounted) return;
      if (flyPointsRef.current.length < 2) {
        // No perches yet — the first /api/trees response will populate
        // flyPointsRef. Try again shortly.
        setTimeout(() => spawnSlot(slot), 600);
        return;
      }
      const c = pool[Math.floor(Math.random() * pool.length)];
      slotStops[slot] = startCreatureFlight(
        map,
        activeMarkers,
        c,
        flyPointsRef,
        speed,
        () => spawnSlot(slot),
      );
    };
    for (let i = 0; i < NUM_CREATURE_SLOTS; i++) spawnSlot(i);

    return () => {
      mounted = false;
      slotStops.forEach((stop) => stop?.());
      // Safety net — should already be empty via slotStops teardown.
      for (const m of activeMarkers) m.remove();
      activeMarkers.clear();
    };
  }, [creatures, markers, creatureSlots, creatureSpeedMps]);

  return <div ref={containerRef} className="play-map" />;
}
