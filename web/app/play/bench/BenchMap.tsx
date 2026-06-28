"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";

// Mirrors PlayMap's marker/basemap setup so the benchmark reflects production cost.
// Self-contained on purpose — keeps PlayMap.tsx untouched.

const BASEMAP_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const BASEMAP_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

const AMSTERDAM_CENTER: [number, number] = [52.3676, 4.9041];
const SPRITE_SLUGS = [
  "Acer", "Tilia", "Quercus", "Fraxinus", "Ulmus", "Platanus",
  "Prunus", "Populus", "Salix", "Betula", "Fagus", "Carpinus",
];

const SPRITE_ICON_CACHE = new Map<string, L.Icon>();
function iconFor(slug: string): L.Icon {
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

// Deterministic PRNG so re-runs are comparable.
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type FakeTree = { id: number; lat: number; lng: number; slug: string };

function generateTrees(n: number, center: [number, number], radiusM: number): FakeTree[] {
  const rand = mulberry32(12345);
  const out: FakeTree[] = [];
  const metersPerDegLat = 111_320;
  const metersPerDegLng = 111_320 * Math.cos((center[0] * Math.PI) / 180);
  for (let i = 0; i < n; i++) {
    // Uniform in disk via sqrt for radial density.
    const r = Math.sqrt(rand()) * radiusM;
    const theta = rand() * 2 * Math.PI;
    const dx = r * Math.cos(theta);
    const dy = r * Math.sin(theta);
    out.push({
      id: i,
      lat: center[0] + dy / metersPerDegLat,
      lng: center[1] + dx / metersPerDegLng,
      slug: SPRITE_SLUGS[i % SPRITE_SLUGS.length],
    });
  }
  return out;
}

type BenchResult = {
  n: number;
  mountMs: number;
  zoomInMs: number;
  zoomOutMs: number;
  panMeanMs: number;
};

export default function BenchMap({ count }: { count: number }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const [result, setResult] = useState<BenchResult | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: AMSTERDAM_CENTER,
      zoom: 17,
      scrollWheelZoom: true,
      zoomControl: false,
      fadeAnimation: false,
      zoomAnimation: false,
      markerZoomAnimation: false,
    });
    L.tileLayer(BASEMAP_URL, {
      subdomains: "abcd",
      maxZoom: 19,
      attribution: BASEMAP_ATTR,
      updateWhenZooming: false,
      updateWhenIdle: true,
      keepBuffer: 1,
    }).addTo(map);
    mapRef.current = map;

    const trees = generateTrees(count, AMSTERDAM_CENTER, 300);
    const layer = L.layerGroup().addTo(map);
    for (const t of trees) {
      L.marker([t.lat, t.lng], {
        icon: iconFor(t.slug),
        keyboard: false,
        bubblingMouseEvents: false,
      })
        .bindTooltip(`${t.slug} #${t.id}`, {
          direction: "top",
          className: "tree-tip",
          offset: [0, -4],
        })
        .addTo(layer);
    }
    (window as unknown as { __benchTrees?: FakeTree[] }).__benchTrees = trees;
    (window as unknown as { __benchLayer?: L.LayerGroup }).__benchLayer = layer;

    map.fitBounds(
      L.latLng(AMSTERDAM_CENTER[0], AMSTERDAM_CENTER[1]).toBounds(600),
      { padding: [20, 20], maxZoom: 18, animate: false },
    );

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [count]);

  function runBench(): BenchResult {
    const map = mapRef.current!;
    const container = containerRef.current!;
    const trees = (window as unknown as { __benchTrees?: FakeTree[] }).__benchTrees ?? [];
    const flush = () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      container.offsetTop;
    };

    const layer = (window as unknown as { __benchLayer?: L.LayerGroup }).__benchLayer!;
    layer.clearLayers();
    flush();
    const t0 = performance.now();
    for (const t of trees) {
      L.marker([t.lat, t.lng], {
        icon: iconFor(t.slug),
        keyboard: false,
        bubblingMouseEvents: false,
      })
        .bindTooltip(`${t.slug} #${t.id}`, {
          direction: "top",
          className: "tree-tip",
          offset: [0, -4],
        })
        .addTo(layer);
    }
    flush();
    const mountMs = performance.now() - t0;

    const startZoom = map.getZoom();
    const t1 = performance.now();
    map.setZoom(startZoom + 1, { animate: false });
    flush();
    const zoomInMs = performance.now() - t1;

    const t2 = performance.now();
    map.setZoom(startZoom, { animate: false });
    flush();
    const zoomOutMs = performance.now() - t2;

    const PAN_ITERS = 40;
    const panSamples: number[] = [];
    let dir = 1;
    for (let i = 0; i < PAN_ITERS; i++) {
      if (i === PAN_ITERS / 2) dir = -1;
      const ts = performance.now();
      map.panBy([4 * dir, 0], { animate: false });
      flush();
      panSamples.push(performance.now() - ts);
    }
    const panMean =
      panSamples.slice(5).reduce((a, b) => a + b, 0) / (panSamples.length - 5);

    return {
      n: count,
      mountMs: +mountMs.toFixed(1),
      zoomInMs: +zoomInMs.toFixed(1),
      zoomOutMs: +zoomOutMs.toFixed(1),
      panMeanMs: +panMean.toFixed(2),
    };
  }

  async function handleRun() {
    if (!mapRef.current) return;
    setRunning(true);
    setResult(null);
    await new Promise((r) => setTimeout(r, 20));
    const r = runBench();
    setResult(r);
    setRunning(false);
    (window as unknown as { __benchResult?: BenchResult }).__benchResult = r;
  }

  useEffect(() => {
    (window as unknown as { __runBench?: () => BenchResult }).__runBench = runBench;
  });

  return (
    <main style={{ position: "relative", height: "100vh" }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          zIndex: 1000,
          background: "rgba(255,255,255,0.95)",
          padding: "10px 14px",
          borderRadius: 8,
          fontFamily: "system-ui, sans-serif",
          fontSize: 13,
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          minWidth: 260,
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 6 }}>
          Map bench — N = {count.toLocaleString()}
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          style={{
            padding: "6px 10px",
            cursor: running ? "wait" : "pointer",
            marginBottom: 8,
          }}
        >
          {running ? "Running…" : "Run pan benchmark"}
        </button>
        {result && (
          <pre style={{ margin: 0, fontSize: 12, lineHeight: 1.4 }}>
{`mount (N markers): ${result.mountMs}ms
zoom in:           ${result.zoomInMs}ms
zoom out:          ${result.zoomOutMs}ms
pan (mean):        ${result.panMeanMs}ms`}
          </pre>
        )}
      </div>
    </main>
  );
}
