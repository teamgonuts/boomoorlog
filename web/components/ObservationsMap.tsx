"use client";

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

// OpenFreeMap Liberty — visual match for the previous CARTO Voyager basemap
// (warm beige residential, soft greens, yellow/orange roads, blue water),
// served as vector tiles for buttery zoom. Free, no key.
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

const AMSTERDAM_CENTER: [number, number] = [4.9041, 52.3676]; // [lng, lat]
const AMSTERDAM_ZOOM = 12;

// Source colour palette. Picked to be high-contrast on the Liberty basemap
// and friendly to red/green colourblindness: blue vs. orange, not green.
const INAT_COLOR = "#1f6feb"; // GitHub-blue
const WN_COLOR = "#e8590c"; // warm orange

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

function toGeoJSON(observations: ObservationPin[]) {
  return {
    type: "FeatureCollection" as const,
    features: observations.map((p) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [p.lng, p.lat] as [number, number],
      },
      properties: {
        id: p.id,
        source: p.source,
        observed_on: p.observed_on,
        scientific_name: p.scientific_name,
        common_name: p.common_name,
        photo_url: p.photo_url,
        permalink: p.permalink,
      },
    })),
  };
}

export default function ObservationsMap({
  observations,
}: {
  observations: ObservationPin[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  // Mount the map once.
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

  // (Re-)populate clustered observations whenever the data changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const SRC = "obs";
    const CLUSTER_LAYER = "obs-clusters";
    const CLUSTER_COUNT_LAYER = "obs-cluster-count";
    const POINT_LAYER = "obs-points";

    const install = () => {
      // Idempotent tear-down (in case the effect re-runs on data change).
      if (map.getLayer(CLUSTER_COUNT_LAYER)) map.removeLayer(CLUSTER_COUNT_LAYER);
      if (map.getLayer(CLUSTER_LAYER)) map.removeLayer(CLUSTER_LAYER);
      if (map.getLayer(POINT_LAYER)) map.removeLayer(POINT_LAYER);
      if (map.getSource(SRC)) map.removeSource(SRC);

      map.addSource(SRC, {
        type: "geojson",
        data: toGeoJSON(observations),
        cluster: true,
        clusterMaxZoom: 15,
        clusterRadius: 40,
      });

      // Unclustered pins — GPU-drawn circles, coloured by source.
      map.addLayer({
        id: POINT_LAYER,
        type: "circle",
        source: SRC,
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "source"],
            "inat", INAT_COLOR,
            "waarneming", WN_COLOR,
            /* other */ "#888",
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
        },
      });

      // Cluster bubbles — neutral grey; grow with count.
      map.addLayer({
        id: CLUSTER_LAYER,
        type: "circle",
        source: SRC,
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#14161b",
          "circle-stroke-color": "rgba(255,255,255,0.6)",
          "circle-stroke-width": 1,
          "circle-radius": [
            "step",
            ["get", "point_count"],
            14, // <10
            10, 18,
            50, 22,
            200, 28,
          ],
          "circle-opacity": 0.85,
        },
      });
      map.addLayer({
        id: CLUSTER_COUNT_LAYER,
        type: "symbol",
        source: SRC,
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Noto Sans Bold"],
          "text-size": 11,
        },
        paint: {
          "text-color": "#fff",
        },
      });

      // Cluster click → zoom into it.
      map.on("click", CLUSTER_LAYER, async (e) => {
        const feat = e.features?.[0];
        if (!feat) return;
        const clusterId = feat.properties?.cluster_id as number | undefined;
        const src = map.getSource(SRC) as
          | (maplibregl.GeoJSONSource & {
              getClusterExpansionZoom: (id: number) => Promise<number>;
            })
          | undefined;
        if (clusterId == null || !src) return;
        try {
          const zoom = await src.getClusterExpansionZoom(clusterId);
          const geom = feat.geometry as unknown as {
            coordinates: [number, number];
          };
          map.easeTo({ center: geom.coordinates, zoom });
        } catch {
          /* cluster gone (data changed mid-request) — ignore */
        }
      });
      map.on("mouseenter", CLUSTER_LAYER, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", CLUSTER_LAYER, () => {
        map.getCanvas().style.cursor = "";
      });

      // Hover tooltip on individual points.
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: "obs-tip",
        offset: 8,
        maxWidth: "260px",
      });
      map.on("mousemove", POINT_LAYER, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const p = f.properties as unknown as ObservationPin;
        const geom = f.geometry as unknown as {
          coordinates: [number, number];
        };
        popup.setLngLat(geom.coordinates).setHTML(tooltipFor(p)).addTo(map);
      });
      map.on("mouseleave", POINT_LAYER, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
    };

    if (map.isStyleLoaded()) install();
    else map.once("style.load", install);

    return () => {
      // Best-effort cleanup — map may already be torn down by the mount effect.
      const m = mapRef.current;
      if (!m) return;
      try {
        if (m.getLayer(CLUSTER_COUNT_LAYER)) m.removeLayer(CLUSTER_COUNT_LAYER);
        if (m.getLayer(CLUSTER_LAYER)) m.removeLayer(CLUSTER_LAYER);
        if (m.getLayer(POINT_LAYER)) m.removeLayer(POINT_LAYER);
        if (m.getSource(SRC)) m.removeSource(SRC);
      } catch {
        /* map already gone */
      }
    };
  }, [observations]);

  return <div ref={containerRef} className="play-map" />;
}
