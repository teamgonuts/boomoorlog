"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

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

/**
 * Leaflet map for the /play page.
 *
 * Receives:
 *  - center: where the user's address geocoded to (map centre + radius circle)
 *  - radiusM: the search radius in meters (drawn as a translucent circle)
 *  - trees: array of trees within that radius, with lat/lng + (optional) genus
 *
 * Renders:
 *  - Dark CARTO basemap (matches the wiki's dark theme)
 *  - A radius circle so the player sees what 1km looks like
 *  - One marker per tree, sprite-icon if we know the genus, plain dot otherwise
 *  - Tooltip on hover: "Genus · height"
 *
 * Performance: ~3k markers is fine for Leaflet. If a board ever exceeds 10k
 * we'll bring in leaflet.markercluster — not worth the dependency now.
 */

type TreePoint = {
  id: number;
  lat: number;
  lng: number;
  slug: string | null;
  species: string | null;
  height_m: number | null;
  diameter_cm: number | null;
  planting_year: number | null;
  location: string | null;
  location_detail: string | null;
  protection_status: string | null;
};

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

function tooltipFor(t: TreePoint): string {
  const lines: string[] = [];

  // Title: full species if we have it, else genus, else "Unknown".
  const title = t.species ?? t.slug ?? "Unknown tree";
  lines.push(`<div class="ttl-h">${escapeHtml(title)}</div>`);

  // Numeric stats: height · diameter · age. Skip nulls.
  const stats: string[] = [];
  if (t.height_m != null) stats.push(`${t.height_m} m`);
  if (t.diameter_cm != null) stats.push(`&Oslash; ${t.diameter_cm} cm`);
  if (t.planting_year != null) {
    const age = CURRENT_YEAR - t.planting_year;
    if (age >= 0 && age < 400) {
      stats.push(`${age} yrs`);
    }
  }
  if (stats.length > 0) {
    lines.push(`<div class="ttl-stats">${stats.join(" · ")}</div>`);
  }

  // Planted year — explicit and historical. Only shown when known.
  if (t.planting_year != null && t.planting_year >= 1500 && t.planting_year <= CURRENT_YEAR + 1) {
    lines.push(`<div class="ttl-ctx">Planted in ${t.planting_year}</div>`);
  }

  // Protected status: rare (~1.6% of trees) so call it out.
  if (t.protection_status) {
    lines.push(
      `<div class="ttl-protected">★ ${escapeHtml(
        en(PROTECTION_EN, t.protection_status),
      )}</div>`,
    );
  }

  return lines.join("");
}

const SPRITE_ICON_CACHE = new Map<string, L.Icon>();

function iconFor(slug: string | null): L.Icon | L.DivIcon {
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

/**
 * Animate a creature sprite hopping tree-to-tree, ignoring streets and
 * physics. Used for the M4.5 "Living map" demo. Returns a stop() function
 * that cancels the loop and removes the marker.
 */
function startCreatureFlight(
  layer: L.LayerGroup,
  slug: string,
  trees: TreePoint[],
): () => void {
  if (trees.length < 2) return () => {};

  const SPEED_MPS = 6;
  const PAUSE_MS = 600;
  const MIN_DURATION_MS = 800;

  const icon = L.divIcon({
    className: "creature-flying",
    html: `<img src="/creature_sprites/${slug}.png" alt="" />`,
    iconSize: [28, 20],
    iconAnchor: [14, 10],
  });

  const pickIndex = (exclude: number): number => {
    if (trees.length <= 1) return 0;
    let i = Math.floor(Math.random() * trees.length);
    if (i === exclude) i = (i + 1) % trees.length;
    return i;
  };

  let fromIdx = Math.floor(Math.random() * trees.length);
  let toIdx = pickIndex(fromIdx);

  const marker = L.marker([trees[fromIdx].lat, trees[fromIdx].lng], {
    icon,
    interactive: false,
    keyboard: false,
    zIndexOffset: 1000,
  }).addTo(layer);

  function metersBetween(a: TreePoint, b: TreePoint): number {
    const dLat = (b.lat - a.lat) * 111_320;
    const cosLat = Math.cos((a.lat * Math.PI) / 180);
    const dLng = (b.lng - a.lng) * 111_320 * cosLat;
    return Math.hypot(dLat, dLng);
  }

  function setSpriteRotation(from: TreePoint, to: TreePoint) {
    const el = marker.getElement()?.querySelector("img") as HTMLImageElement | null;
    if (!el) return;
    const dLat = to.lat - from.lat;
    const dLng = to.lng - from.lng;
    // Screen y goes down (decreasing lat = increasing screen y).
    // Original sprite faces east → 0° rotation = unchanged.
    const angleDeg = (Math.atan2(-dLat, dLng) * 180) / Math.PI;
    // For mostly-westward moves, mirror horizontally so the bird never looks
    // upside-down. Accept a tiny tilt mismatch on diagonals; simpler than a
    // full rotation-matrix-aware sprite atlas.
    el.style.transform =
      Math.abs(angleDeg) > 90 ? "scaleX(-1)" : `rotate(${angleDeg}deg)`;
  }

  let segmentStart = performance.now();
  let segmentDurMs =
    Math.max(MIN_DURATION_MS, (metersBetween(trees[fromIdx], trees[toIdx]) / SPEED_MPS) * 1000);
  setSpriteRotation(trees[fromIdx], trees[toIdx]);

  let mode: "flying" | "paused" = "flying";
  let pauseUntil = 0;
  let running = true;

  function tick(now: number) {
    if (!running) return;
    if (mode === "flying") {
      const t = Math.min(1, (now - segmentStart) / segmentDurMs);
      const from = trees[fromIdx];
      const to = trees[toIdx];
      marker.setLatLng([
        from.lat + (to.lat - from.lat) * t,
        from.lng + (to.lng - from.lng) * t,
      ]);
      if (t >= 1) {
        mode = "paused";
        pauseUntil = now + PAUSE_MS;
      }
    } else if (now >= pauseUntil) {
      fromIdx = toIdx;
      toIdx = pickIndex(fromIdx);
      segmentStart = now;
      segmentDurMs = Math.max(
        MIN_DURATION_MS,
        (metersBetween(trees[fromIdx], trees[toIdx]) / SPEED_MPS) * 1000,
      );
      setSpriteRotation(trees[fromIdx], trees[toIdx]);
      mode = "flying";
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  return () => {
    running = false;
    marker.remove();
  };
}

export default function PlayMap({
  center,
  radiusM,
  trees,
  creatureSlugs,
}: {
  center: { lat: number; lng: number } | null;
  radiusM: number;
  trees: TreePoint[];
  creatureSlugs?: string[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Mount the Leaflet map once. Subsequent prop changes update layers.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: AMSTERDAM_CENTER,
      zoom: AMSTERDAM_ZOOM,
      scrollWheelZoom: true,
      zoomControl: false,
      // Perf: with up to ~250 sprite-icon markers in view, Leaflet's
      // per-marker reposition during zoom/fade animations is the dominant
      // cost. Disabling these makes pan and zoom snap immediately.
      fadeAnimation: false,
      zoomAnimation: false,
      markerZoomAnimation: false,
    });
    L.control.zoom({ position: "bottomleft" }).addTo(map);
    L.tileLayer(BASEMAP_URL, {
      subdomains: "abcd",
      maxZoom: 19,
      attribution: BASEMAP_ATTR,
      // Defer tile requests until the user stops zooming/panning.
      updateWhenZooming: false,
      updateWhenIdle: true,
      keepBuffer: 1,
    }).addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Re-render markers + radius whenever inputs change; fit zoom to the data.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const layer = L.layerGroup().addTo(map);

    if (!center) {
      // No search yet — keep the default Amsterdam-wide view.
      map.setView(AMSTERDAM_CENTER, AMSTERDAM_ZOOM);
      return () => {
        layer.remove();
      };
    }

    // Center pin (the user's address). No radius ring — the visible map IS
    // the play area now.
    L.circleMarker([center.lat, center.lng], {
      radius: 6,
      color: "#c0463b",
      fillColor: "#c0463b",
      fillOpacity: 1,
      weight: 2,
    })
      .bindTooltip("Your address", { direction: "top" })
      .addTo(layer);

    // Tree markers. `keyboard: false` + `bubblingMouseEvents: false` skip a
    // per-marker listener install that adds up at 200+ markers.
    for (const t of trees) {
      const marker = L.marker([t.lat, t.lng], {
        icon: iconFor(t.slug),
        keyboard: false,
        bubblingMouseEvents: false,
      });
      marker.bindTooltip(tooltipFor(t), {
        direction: "top",
        className: "tree-tip",
        offset: [0, -4],
      });
      marker.addTo(layer);
    }

    // Auto-zoom to roughly cover the radius area. With the ring gone, the
    // visible viewport is the play area; bbox is queried 1.2× wider for buffer.
    const bounds = L.latLng(center.lat, center.lng).toBounds(radiusM * 2.2);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18, animate: false });

    // M4.5: animate the creatures-of-the-moment between random trees in view.
    const creatureStops: Array<() => void> = [];
    for (const slug of creatureSlugs ?? []) {
      creatureStops.push(startCreatureFlight(layer, slug, trees));
    }

    return () => {
      creatureStops.forEach((stop) => stop());
      layer.remove();
    };
  }, [center, radiusM, trees, creatureSlugs]);

  return <div ref={containerRef} className="play-map" />;
}
