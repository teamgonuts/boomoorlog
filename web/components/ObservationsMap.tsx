"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import { useEffect, useRef } from "react";

// Same CARTO Voyager basemap as /play for visual consistency.
const BASEMAP_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const BASEMAP_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

const AMSTERDAM_CENTER: [number, number] = [52.3676, 4.9041];
const AMSTERDAM_ZOOM = 12;

// Source colour palette. Picked to be high-contrast on the Voyager basemap
// and friendly to red/green colourblindness: blue vs. orange, not green.
const SOURCE_COLOR: Record<"inat" | "waarneming", string> = {
  inat: "#1f6feb", // GitHub-blue
  waarneming: "#e8590c", // warm orange
};

// leaflet.markercluster is a legacy IIFE-style plugin: it grabs L off the
// global window at evaluation time and registers `L.MarkerClusterGroup` on it.
// In Next.js / Turbopack ESM land we need to (a) put our imported L on window,
// (b) defer loading the plugin until after that's done. A dynamic import inside
// the effect gives us both, and it ducks the SSR pass cleanly.
let markerClusterReady: Promise<void> | null = null;
function ensureMarkerCluster(): Promise<void> {
  if (markerClusterReady) return markerClusterReady;
  markerClusterReady = (async () => {
    if (typeof window !== "undefined") {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).L = L;
    }
    await import("leaflet.markercluster");
  })();
  return markerClusterReady;
}

export type ObservationPin = {
  id: string;
  source: "inat" | "waarneming";
  lat: number;
  lng: number;
  observed_on: string;
  scientific_name: string;
  common_name: string | null;
  photo_url: string | null;
  permalink: string | null;
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function tooltipFor(p: ObservationPin): string {
  const title = p.common_name
    ? `${escapeHtml(p.common_name)} <em>(${escapeHtml(p.scientific_name)})</em>`
    : `<em>${escapeHtml(p.scientific_name)}</em>`;
  const dateLine = `<div class="obs-tip-date">${escapeHtml(p.observed_on)} · ${p.source === "inat" ? "iNaturalist" : "Waarneming.nl"}</div>`;
  const photo = p.photo_url
    ? `<div class="obs-tip-photo"><img src="${escapeHtml(p.photo_url)}" alt="" loading="lazy" /></div>`
    : "";
  return (
    `${photo}` +
    `<div class="obs-tip-title">${title}</div>` +
    `${dateLine}`
  );
}

// Default Leaflet circleMarker as the pin: cheap to render at 12k count and
// matches the user's "no custom pins" ask. Colour discriminates source.
function makeMarker(p: ObservationPin): L.CircleMarker {
  const color = SOURCE_COLOR[p.source];
  const m = L.circleMarker([p.lat, p.lng], {
    radius: 5,
    color: "#ffffff",
    weight: 1,
    fillColor: color,
    fillOpacity: 0.9,
    bubblingMouseEvents: false,
  });
  m.bindTooltip(tooltipFor(p), {
    direction: "top",
    className: "obs-tip",
    offset: [0, -4],
    sticky: true,
  });
  return m;
}

export default function ObservationsMap({
  observations,
}: {
  observations: ObservationPin[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Mount the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: AMSTERDAM_CENTER,
      zoom: AMSTERDAM_ZOOM,
      scrollWheelZoom: true,
      zoomControl: false,
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
    mapRef.current = map;
    if (typeof window !== "undefined") {
      // Dev-only handle so we can pan/zoom from the browser console.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__obsMap = map;
    }
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // (Re-)populate clustered markers whenever the data changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    let cancelled = false;
    let attachedCluster: L.LayerGroup | null = null;

    (async () => {
      await ensureMarkerCluster();
      if (cancelled || !mapRef.current) return;

      // Default cluster behaviour — Leaflet.markercluster's stock algorithm
      // (greedy distance-based clustering at each zoom level). Default radius
      // 80px, default spiderfy on zoom-max. `animateAddingMarkers: false`
      // keeps `addLayers` fully synchronous so a strict-mode unmount can't
      // race a pending animation frame.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cluster = (L as any).markerClusterGroup({
        animateAddingMarkers: false,
      }) as L.LayerGroup;
      map.addLayer(cluster);
      attachedCluster = cluster;

      const markers: L.CircleMarker[] = [];
      for (const p of observations) markers.push(makeMarker(p));
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (cluster as any).addLayers(markers);
      } catch {
        // Strict-mode double-mount left this cluster orphaned; the remounted
        // effect will draw on the live one.
      }
    })();

    return () => {
      cancelled = true;
      if (attachedCluster && mapRef.current) {
        mapRef.current.removeLayer(attachedCluster);
      }
    };
  }, [observations]);

  return <div ref={containerRef} className="play-map" />;
}
