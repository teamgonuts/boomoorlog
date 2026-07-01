"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

// Rolling FPS meter — samples every rAF, averages over the last ~30 frames.
export default function FpsMeter({
  engine,
  n,
}: {
  engine: string;
  n: number;
}) {
  const [fps, setFps] = useState(0);
  const frames = useRef<number[]>([]);

  useEffect(() => {
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = now - last;
      last = now;
      const buf = frames.current;
      buf.push(dt);
      if (buf.length > 30) buf.shift();
      const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
      setFps(Math.round(1000 / avg));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div
      style={{
        position: "absolute",
        top: 10,
        left: 10,
        background: "rgba(0,0,0,0.75)",
        color: "#fff",
        padding: "8px 12px",
        borderRadius: 6,
        fontFamily: "ui-monospace, Menlo, monospace",
        fontSize: 13,
        lineHeight: 1.5,
        pointerEvents: "auto",
        zIndex: 1000,
      }}
    >
      <div style={{ fontWeight: 600 }}>{engine}</div>
      <div>sprites: {n.toLocaleString()}</div>
      <div>
        fps: <span style={{ color: fps < 30 ? "#ff8080" : "#8fff8f" }}>{fps}</span>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, opacity: 0.7 }}>
        <Link href="/poc" style={{ color: "#9fdfff" }}>
          ← back
        </Link>
      </div>
    </div>
  );
}
