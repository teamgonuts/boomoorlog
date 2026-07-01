"use client";

// Tiny client wrapper so the MapLibre GL import (which touches `window` at
// module load) never reaches the SSR pass. The actual map lives in
// components/ObservationsMap.tsx.
import dynamic from "next/dynamic";

const ObservationsMap = dynamic(() => import("@/components/ObservationsMap"), {
  ssr: false,
  loading: () => <div className="play-map" />,
});

export default ObservationsMap;
