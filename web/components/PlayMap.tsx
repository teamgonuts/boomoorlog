"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

import type { ViewportMarker } from "@/lib/trees-api";

// CARTO Voyager — light raster tiles, very close visual match to OSM Liberty
// (beige residential, soft greens for parks, yellow/orange roads, light blue
// water) but served as plain raster PNGs so Leaflet can render it directly
// without dragging in MapLibre GL. Free for non-commercial; attributed below.
const BASEMAP_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const BASEMAP_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

// Map opens centered on Amsterdam if no address has been searched.
const AMSTERDAM_CENTER: [number, number] = [52.3676, 4.9041];
const AMSTERDAM_ZOOM = 12;

// Today's calendar year. Used to compute ages. Fine to refresh on a 1-yr cadence.
const CURRENT_YEAR = new Date().getFullYear();

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

function tooltipForIndividual(t: Marker): string {
  const lines: string[] = [];
  const title = t.species ?? t.slug ?? "Unknown tree";
  lines.push(`<div class="ttl-h">${escapeHtml(title)}</div>`);

  const stats: string[] = [];
  if (t.height_m != null) stats.push(`${t.height_m} m`);
  if (t.diameter_cm != null) stats.push(`&Oslash; ${t.diameter_cm} cm`);
  if (t.planting_year != null) {
    const age = CURRENT_YEAR - t.planting_year;
    if (age >= 0 && age < 400) stats.push(`${age} yrs`);
  }
  if (stats.length > 0) {
    lines.push(`<div class="ttl-stats">${stats.join(" · ")}</div>`);
  }

  if (
    t.planting_year != null &&
    t.planting_year >= 1500 &&
    t.planting_year <= CURRENT_YEAR + 1
  ) {
    lines.push(`<div class="ttl-ctx">Planted in ${t.planting_year}</div>`);
  }

  if (t.protection_status) {
    lines.push(
      `<div class="ttl-protected">★ ${escapeHtml(
        en(PROTECTION_EN, t.protection_status),
      )}</div>`,
    );
  }

  return lines.join("");
}

function tooltipForCluster(m: Marker): string {
  const slug = m.slug ?? "mixed";
  return (
    `<div class="ttl-h">${escapeHtml(slug)}</div>` +
    `<div class="ttl-stats">${m.n.toLocaleString()} trees · click to zoom</div>`
  );
}

const SPRITE_ICON_CACHE = new Map<string, L.Icon>();

function iconForIndividual(slug: string | null): L.Icon | L.DivIcon {
  if (!slug) {
    return L.divIcon({
      className: "tree-dot",
      iconSize: [6, 6],
      iconAnchor: [3, 3],
    });
  }
  let icon = SPRITE_ICON_CACHE.get(slug);
  if (!icon) {
    icon = L.icon({
      iconUrl: `/sprites/${slug}.png`,
      iconSize: [22, 28],
      iconAnchor: [11, 26],
      tooltipAnchor: [0, -22],
      className: "tree-pin",
    });
    SPRITE_ICON_CACHE.set(slug, icon);
  }
  return icon;
}

function iconForCluster(slug: string | null, n: number): L.DivIcon {
  const sprite = slug
    ? `<img class="tree-cluster-sprite pixel" src="/sprites/${slug}.png" alt="" />`
    : `<span class="tree-cluster-dot"></span>`;
  // Compact number; >=1k → "1.2k" so the badge stays readable at city zoom.
  const label =
    n >= 1000 ? (n / 1000).toFixed(n >= 10_000 ? 0 : 1) + "k" : String(n);
  return L.divIcon({
    className: "tree-cluster",
    html: `${sprite}<span class="tree-cluster-count">${label}</span>`,
    iconSize: [36, 44],
    iconAnchor: [18, 40],
    tooltipAnchor: [0, -34],
  });
}

/** Creature data needed to render + identify the marker on hover. */
type CreatureForMap = {
  slug: string;
  common_name: string;
  latin_name: string | null;
  photo_url: string | null;
};

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
  layer: L.LayerGroup,
  creature: CreatureForMap,
  pointsRef: { current: FlyPoint[] },
  onComplete: () => void,
): () => void {
  const points = pointsRef.current;
  if (points.length < 2) {
    onComplete();
    return () => {};
  }

  const SPEED_MPS = 6;
  const PERCH_MS = 500;
  const MIN_DURATION_MS = 800;

  const icon = L.divIcon({
    className: "creature-flying",
    html: `<img src="/creature_sprites/${creature.slug}.png" alt="" />`,
    iconSize: [56, 40],
    iconAnchor: [28, 20],
  });

  const fromIdx = Math.floor(Math.random() * points.length);
  let toIdx = Math.floor(Math.random() * points.length);
  if (toIdx === fromIdx) toIdx = (toIdx + 1) % points.length;
  const from = points[fromIdx];
  const to = points[toIdx];

  const marker = L.marker([from.lat, from.lng], {
    icon,
    interactive: true,
    keyboard: false,
    bubblingMouseEvents: false,
    zIndexOffset: 1000,
  }).addTo(layer);

  const photoBlock = creature.photo_url
    ? `<div class="creature-tip-photo"><img src="${escapeForAttr(creature.photo_url)}" alt="" loading="lazy" /></div>`
    : "";
  const latinLine = creature.latin_name
    ? `<div class="creature-tip-latin">${escapeForAttr(creature.latin_name)}</div>`
    : "";
  marker.bindTooltip(
    photoBlock +
      `<div class="creature-tip-name">${escapeForAttr(creature.common_name)}</div>` +
      latinLine,
    { direction: "top", className: "creature-tip", offset: [0, -8], sticky: true },
  );

  function metersBetween(a: FlyPoint, b: FlyPoint): number {
    const dLat = (b.lat - a.lat) * 111_320;
    const cosLat = Math.cos((a.lat * Math.PI) / 180);
    const dLng = (b.lng - a.lng) * 111_320 * cosLat;
    return Math.hypot(dLat, dLng);
  }

  function setSpriteRotation() {
    const el = marker.getElement()?.querySelector("img") as HTMLImageElement | null;
    if (!el) return;
    const dLat = to.lat - from.lat;
    const dLng = to.lng - from.lng;
    const angleDeg = (Math.atan2(-dLat, dLng) * 180) / Math.PI;
    el.style.transform =
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
      marker.setLatLng([
        from.lat + (to.lat - from.lat) * t,
        from.lng + (to.lng - from.lng) * t,
      ]);
      if (t >= 1) {
        mode = "perched";
        perchUntil = now + PERCH_MS;
      }
    } else if (now >= perchUntil) {
      // Journey done — disappear and let the parent spawn a replacement.
      running = false;
      marker.remove();
      onComplete();
      return;
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  return () => {
    running = false;
    marker.remove();
  };
}

export type Bbox = {
  lat_min: number;
  lng_min: number;
  lat_max: number;
  lng_max: number;
};

export default function PlayMap({
  center,
  initialRadiusM,
  markers,
  creatures,
  onViewportChange,
}: {
  center: { lat: number; lng: number } | null;
  /** Half-side of the initial fitBounds box, in meters. Only used the first
   *  time a new `center` arrives — after that, the user controls the view. */
  initialRadiusM: number;
  markers: Marker[];
  creatures?: CreatureForMap[];
  onViewportChange?: (bbox: Bbox, zoom: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const addressLayerRef = useRef<L.LayerGroup | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const creatureLayerRef = useRef<L.LayerGroup | null>(null);
  // Marker handles keyed by Marker.key for diff-update on marker prop change.
  const markerHandlesRef = useRef<Map<string, L.Marker>>(new Map());
  // Marker positions exposed to creature loops via ref so flights survive
  // marker-prop changes without restarting.
  const flyPointsRef = useRef<FlyPoint[]>([]);
  // Callback captured into the mount-effect via ref so identity churn from
  // the parent doesn't trigger a remap remount.
  const onViewportChangeRef = useRef(onViewportChange);
  onViewportChangeRef.current = onViewportChange;
  // First-fit guard: only auto-fit when a new center arrives. After that,
  // panning/zooming is the user's.
  const lastFitCenterRef = useRef<string | null>(null);

  // ---- Mount the map once ----
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: AMSTERDAM_CENTER,
      zoom: AMSTERDAM_ZOOM,
      scrollWheelZoom: true,
      zoomControl: false,
      // Perf: see bench results — disabling these avoids per-marker animation
      // costs and makes pan/zoom snap. Acceptable trade since markers are
      // capped at ~400 and zoom is the dominant cost (~50ms at the cap).
      fadeAnimation: false,
      zoomAnimation: false,
      markerZoomAnimation: false,
    });
    L.control.zoom({ position: "bottomleft" }).addTo(map);
    L.tileLayer(BASEMAP_URL, {
      subdomains: "abcd",
      maxZoom: 19,
      attribution: BASEMAP_ATTR,
      updateWhenZooming: false,
      updateWhenIdle: true,
      keepBuffer: 1,
    }).addTo(map);

    addressLayerRef.current = L.layerGroup().addTo(map);
    markerLayerRef.current = L.layerGroup().addTo(map);
    creatureLayerRef.current = L.layerGroup().addTo(map);
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

    return () => {
      map.off("moveend", emitViewport);
      map.remove();
      mapRef.current = null;
      addressLayerRef.current = null;
      markerLayerRef.current = null;
      creatureLayerRef.current = null;
      markerHandlesRef.current.clear();
    };
  }, []);

  // ---- Address pin + initial fit when center changes ----
  useEffect(() => {
    const map = mapRef.current;
    const layer = addressLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    if (!center) {
      map.setView(AMSTERDAM_CENTER, AMSTERDAM_ZOOM);
      lastFitCenterRef.current = null;
      return;
    }

    L.circleMarker([center.lat, center.lng], {
      radius: 6,
      color: "#c0463b",
      fillColor: "#c0463b",
      fillOpacity: 1,
      weight: 2,
    })
      .bindTooltip("Your address", { direction: "top" })
      .addTo(layer);

    const centerKey = `${center.lat},${center.lng}`;
    if (lastFitCenterRef.current !== centerKey) {
      // New address — auto-fit. `radius * 2.2` matches the prior look.
      const bounds = L.latLng(center.lat, center.lng).toBounds(
        initialRadiusM * 2.2,
      );
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18, animate: false });
      lastFitCenterRef.current = centerKey;
    }
  }, [center, initialRadiusM]);

  // ---- Markers: diff-update on prop change ----
  useEffect(() => {
    const layer = markerLayerRef.current;
    const map = mapRef.current;
    if (!layer || !map) return;

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
      const icon =
        m.mode === "cluster"
          ? iconForCluster(m.slug, m.n)
          : iconForIndividual(m.slug);
      const marker = L.marker([m.lat, m.lng], {
        icon,
        keyboard: false,
        bubblingMouseEvents: false,
      });
      const tip =
        m.mode === "cluster" ? tooltipForCluster(m) : tooltipForIndividual(m);
      marker.bindTooltip(tip, {
        direction: "top",
        className: "tree-tip",
        offset: [0, -4],
      });
      if (m.mode === "cluster") {
        // Click a cluster → drill in two zoom levels. Two levels usually
        // splits a dense cluster into finer ones (or unblocks individual mode
        // if total drops under max_pins).
        marker.on("click", () => {
          const target = Math.min(map.getZoom() + 2, 19);
          map.setView([m.lat, m.lng], target, { animate: false });
        });
      }
      marker.addTo(layer);
      handles.set(m.key, marker);
    }

    // Keep flyPointsRef in sync — creatures land on these on respawn. Using
    // marker centroids for both modes is fine; cluster centroids are still
    // "where trees are".
    flyPointsRef.current = markers.map((m) => ({ lat: m.lat, lng: m.lng }));
  }, [markers]);

  // ---- Creatures: spawn N slots, each respawns on completion ----
  useEffect(() => {
    const creatureLayer = creatureLayerRef.current;
    if (!creatureLayer) return;
    const pool = creatures ?? [];
    if (pool.length === 0) return;

    const NUM_CREATURE_SLOTS = 5;
    const slotStops: Array<(() => void) | null> = Array(NUM_CREATURE_SLOTS).fill(null);
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
      slotStops[slot] = startCreatureFlight(creatureLayer, c, flyPointsRef, () =>
        spawnSlot(slot),
      );
    };
    for (let i = 0; i < NUM_CREATURE_SLOTS; i++) spawnSlot(i);

    return () => {
      mounted = false;
      slotStops.forEach((stop) => stop?.());
      creatureLayer.clearLayers();
    };
  }, [creatures]);

  return <div ref={containerRef} className="play-map" />;
}
