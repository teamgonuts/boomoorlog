"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

import {
  AMS_CENTER,
  AMS_ZOOM,
  generateSprites,
  SPRITE_FILES,
  type Sprite,
} from "../data";
import FpsMeter from "../FpsMeter";

const BASEMAP_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const BASEMAP_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

const SPRITE_SIZE = 24; // px on screen (matches Sprite.tsx in the real app)

type SpriteImages = Record<string, HTMLImageElement>;

function loadSpriteImages(): Promise<SpriteImages> {
  const entries = SPRITE_FILES.map(
    (f) =>
      new Promise<[string, HTMLImageElement]>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve([f, img]);
        img.onerror = reject;
        img.src = "/creature_sprites/" + f;
      }),
  );
  return Promise.all(entries).then((pairs) => Object.fromEntries(pairs));
}

// Custom canvas layer: one <canvas> the size of the map pane, sprites drawn
// each frame in map-projected pixel coords. The animated-zoom trick: on
// `zoomanim`, project the canvas origin into the target zoom's pixel space and
// CSS-transform it so it moves with the tile pane. Redraws crisp on `zoomend`.
function createSpriteLayer(sprites: Sprite[], images: SpriteImages) {
  const CanvasLayer = L.Layer.extend({
    onAdd(this: L.Layer & { _map: L.Map }, map: L.Map) {
      const canvas = document.createElement("canvas");
      canvas.style.position = "absolute";
      canvas.style.pointerEvents = "none";
      canvas.style.imageRendering = "pixelated";
      (this as unknown as { _canvas: HTMLCanvasElement })._canvas = canvas;
      map.getPane("overlayPane")!.appendChild(canvas);

      map.on("moveend", this._reset, this);
      map.on("resize", this._reset, this);
      map.on("zoomanim", this._animateZoom, this);

      this._reset();
      return this;
    },
    onRemove(this: L.Layer & { _map: L.Map }, map: L.Map) {
      const c = (this as unknown as { _canvas: HTMLCanvasElement })._canvas;
      c.parentNode?.removeChild(c);
      map.off("moveend", this._reset, this);
      map.off("resize", this._reset, this);
      map.off("zoomanim", this._animateZoom, this);
      return this;
    },
    _reset(this: L.Layer & { _map: L.Map }) {
      const map = this._map;
      const canvas = (this as unknown as { _canvas: HTMLCanvasElement })
        ._canvas;
      const size = map.getSize();
      const topLeft = map.containerPointToLayerPoint([0, 0]);
      L.DomUtil.setPosition(canvas, topLeft);
      const dpr = window.devicePixelRatio || 1;
      canvas.width = size.x * dpr;
      canvas.height = size.y * dpr;
      canvas.style.width = size.x + "px";
      canvas.style.height = size.y + "px";
      canvas.style.transformOrigin = "0 0";
      canvas.style.transform = "";
      this._draw();
    },
    _animateZoom(
      this: L.Layer & { _map: L.Map },
      e: { zoom: number; center: L.LatLng },
    ) {
      const map = this._map;
      const canvas = (this as unknown as { _canvas: HTMLCanvasElement })
        ._canvas;
      const scale = map.getZoomScale(e.zoom, map.getZoom());
      const offset = map
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ._latLngBoundsToNewLayerBounds(
          map.getBounds(),
          e.zoom,
          e.center,
        )
        .min;
      const topLeft = map.containerPointToLayerPoint([0, 0]);
      L.DomUtil.setTransform(
        canvas,
        offset.subtract(topLeft),
        scale,
      );
    },
    _draw(this: L.Layer & { _map: L.Map }) {
      const map = this._map;
      const canvas = (this as unknown as { _canvas: HTMLCanvasElement })
        ._canvas;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.imageSmoothingEnabled = false;
      const dpr = window.devicePixelRatio || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const half = SPRITE_SIZE / 2;
      // Culling: only draw sprites inside the current viewport (padded).
      const bounds = map.getBounds().pad(0.1);
      for (const s of sprites) {
        if (
          s.lat < bounds.getSouth() ||
          s.lat > bounds.getNorth() ||
          s.lng < bounds.getWest() ||
          s.lng > bounds.getEast()
        )
          continue;
        const p = map.latLngToContainerPoint([s.lat, s.lng]);
        const img = images[s.file];
        if (!img) continue;
        ctx.drawImage(img, p.x - half, p.y - half, SPRITE_SIZE, SPRITE_SIZE);
      }
    },
  });
  return new (CanvasLayer as unknown as new () => L.Layer)();
}

export default function LeafletPoc({ n }: { n: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const spriteCountRef = useRef(n);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = L.map(containerRef.current, {
      preferCanvas: true,
      zoomAnimation: true,
      fadeAnimation: true,
    }).setView(AMS_CENTER, AMS_ZOOM);
    L.tileLayer(BASEMAP_URL, {
      attribution: BASEMAP_ATTR,
      maxZoom: 19,
    }).addTo(map);

    const sprites = generateSprites(spriteCountRef.current);
    let layer: L.Layer | null = null;
    loadSpriteImages().then((imgs) => {
      layer = createSpriteLayer(sprites, imgs);
      layer.addTo(map);
    });

    return () => {
      if (layer) map.removeLayer(layer);
      map.remove();
    };
  }, []);

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1 }}>
      <div
        ref={containerRef}
        style={{ position: "absolute", inset: 0 }}
      />
      <FpsMeter engine="Leaflet + canvas overlay" n={n} />
    </div>
  );
}
