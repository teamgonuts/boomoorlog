"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

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

  // Standplaats: where it stands. e.g. "Groenobject · Tegels".
  const context = [t.location, t.location_detail]
    .filter((s): s is string => Boolean(s))
    .map(escapeHtml)
    .join(" · ");
  if (context) lines.push(`<div class="ttl-ctx">${context}</div>`);

  // Protected status: rare (~1.6% of trees) so call it out.
  if (t.protection_status) {
    lines.push(
      `<div class="ttl-protected">★ ${escapeHtml(t.protection_status)}</div>`,
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

export default function PlayMap({
  center,
  radiusM,
  trees,
}: {
  center: { lat: number; lng: number };
  radiusM: number;
  trees: TreePoint[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Mount / unmount the Leaflet map once. Subsequent prop changes update layers.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [center.lat, center.lng],
      zoom: 15,
      scrollWheelZoom: false,
    });
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        subdomains: "abcd",
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      },
    ).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [center.lat, center.lng]);

  // Re-render markers + radius whenever inputs change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const layer = L.layerGroup().addTo(map);

    // Recenter (in case the address changed between renders).
    map.setView([center.lat, center.lng], 15);

    // Radius circle.
    L.circle([center.lat, center.lng], {
      radius: radiusM,
      color: "#e0a33a",
      weight: 2,
      fillColor: "#e0a33a",
      fillOpacity: 0.05,
    }).addTo(layer);

    // Center pin (the user's address).
    L.circleMarker([center.lat, center.lng], {
      radius: 6,
      color: "#c0463b",
      fillColor: "#c0463b",
      fillOpacity: 1,
      weight: 2,
    })
      .bindTooltip("Your address", { direction: "top" })
      .addTo(layer);

    // Tree markers.
    for (const t of trees) {
      const marker = L.marker([t.lat, t.lng], { icon: iconFor(t.slug) });
      marker.bindTooltip(tooltipFor(t), {
        direction: "top",
        className: "tree-tip",
        offset: [0, -4],
      });
      marker.addTo(layer);
    }

    return () => {
      layer.remove();
    };
  }, [center.lat, center.lng, radiusM, trees]);

  return <div ref={containerRef} className="play-map" />;
}
