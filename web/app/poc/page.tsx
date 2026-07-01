import Link from "next/link";

export const metadata = {
  title: "Map POC — Leaflet vs MapLibre",
};

export default function PocIndex() {
  return (
    <main
      style={{
        fontFamily: "system-ui, sans-serif",
        maxWidth: 640,
        margin: "40px auto",
        padding: "0 20px",
        lineHeight: 1.5,
      }}
    >
      <h1>Map engine comparison</h1>
      <p>
        Same 1,000 pixel-art sprites at the same random positions around
        Amsterdam. Same starting view, same interactions. Only the map engine
        differs. Zoom in / out, pan, watch the FPS counter top-left.
      </p>

      <ul style={{ marginTop: 24, fontSize: 18 }}>
        <li>
          <Link href="/poc/leaflet">/poc/leaflet</Link> — Leaflet + CARTO raster
          tiles + canvas sprite overlay
        </li>
        <li style={{ marginTop: 8 }}>
          <Link href="/poc/maplibre">/poc/maplibre</Link> — MapLibre GL +
          OpenFreeMap Liberty (Voyager-like) vector tiles + WebGL symbol layer
        </li>
      </ul>

      <p style={{ marginTop: 24, color: "#666", fontSize: 14 }}>
        Tune the sprite count via <code>?n=2000</code>. Try{" "}
        <code>?n=500</code> to see baseline feel.
      </p>
    </main>
  );
}
