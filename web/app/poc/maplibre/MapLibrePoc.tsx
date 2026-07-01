"use client";

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import {
  AMS_CENTER,
  AMS_ZOOM,
  generateSprites,
  SPRITE_FILES,
} from "../data";
import FpsMeter from "../FpsMeter";

// OpenFreeMap Liberty style — visual match for the current CARTO Voyager basemap
// (warm beige residential, soft green parks, yellow/orange roads, blue water).
// Free vector tiles, no key required. Rendering engine is identical to Mapbox GL JS.
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

export default function MapLibrePoc({ n }: { n: number }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const map = new maplibregl.Map({
      container: el,
      style: STYLE_URL,
      center: [AMS_CENTER[1], AMS_CENTER[0]], // MapLibre is [lng, lat]
      zoom: AMS_ZOOM,
      // Snap-off = smooth continuous zoom, the whole point of testing this.
      renderWorldCopies: false,
    });

    // Container may be 0-sized on first paint (parent uses absolute positioning
    // and layout races the map init). Keep it in sync.
    const ro = new ResizeObserver(() => map.resize());
    ro.observe(el);

    map.on("error", (e) => console.error("[maplibre error]", e.error));

    // Pre-load the raw sprite PNGs concurrently with the style download.
    const imagesReady = Promise.all(
      SPRITE_FILES.map(
        (f) =>
          new Promise<[string, HTMLImageElement]>((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve([f, img]);
            img.onerror = reject;
            img.src = "/creature_sprites/" + f;
          }),
      ),
    );

    // Set up source + layer once style is parsed AND images are ready.
    // `style.load` is emitted by MapLibre when the style JSON has been fully
    // parsed — safe point to call addImage / addSource / addLayer.
    const setup = async () => {
      const images = await imagesReady;
      for (const [f, img] of images) {
        if (!map.hasImage(f)) map.addImage(f, img, { pixelRatio: 1 });
      }
      const sprites = generateSprites(n);
      map.addSource("sprites", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: sprites.map((s) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [s.lng, s.lat] },
            properties: { file: s.file },
          })),
        },
      });
      map.addLayer({
        id: "sprites-layer",
        type: "symbol",
        source: "sprites",
        layout: {
          "icon-image": ["get", "file"],
          "icon-size": 0.75,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
      });
    };
    if (map.isStyleLoaded()) setup();
    else map.once("style.load", setup);

    return () => {
      ro.disconnect();
      map.remove();
    };
  }, [n]);

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      <FpsMeter engine="MapLibre GL + symbol layer" n={n} />
    </div>
  );
}
