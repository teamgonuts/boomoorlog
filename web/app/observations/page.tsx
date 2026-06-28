import { supabase } from "@/lib/supabase";
import ObservationsMapClient from "./ObservationsMapClient";

// Live data; never cache.
export const dynamic = "force-dynamic";

const DAYS = 90;
const PAGE_SIZE = 1000;

// Trimmed projection — the client only needs map + tooltip fields.
type ObsPin = {
  id: string; // "source:obs_id" — stable React key
  source: "inat" | "waarneming";
  lat: number;
  lng: number;
  observed_on: string;
  scientific_name: string;
  common_name: string | null;
  photo_url: string | null;
  permalink: string | null;
};

async function fetchObservations(): Promise<ObsPin[]> {
  const since = new Date(Date.now() - DAYS * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);
  const out: ObsPin[] = [];
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .from("observations")
      .select(
        "source, source_obs_id, lat, lng, observed_on, scientific_name, common_name, photo_url, permalink",
      )
      .gte("observed_on", since)
      .not("lat", "is", null)
      .not("lng", "is", null)
      .order("observed_on", { ascending: false })
      .range(from, from + PAGE_SIZE - 1);
    if (error) throw new Error(`observations: ${error.message}`);
    if (!data || data.length === 0) break;
    for (const r of data) {
      if (r.lat == null || r.lng == null) continue;
      out.push({
        id: `${r.source}:${r.source_obs_id}`,
        source: r.source,
        lat: r.lat,
        lng: r.lng,
        observed_on: r.observed_on,
        scientific_name: r.scientific_name,
        common_name: r.common_name,
        photo_url: r.photo_url,
        permalink: r.permalink,
      });
    }
    if (data.length < PAGE_SIZE) break;
    if (from > 200_000) break; // hard safety stop
  }
  return out;
}

export const metadata = {
  title: "Observations — Boomoorlog",
  description:
    "Live map of wildlife observations in Amsterdam from iNaturalist and Waarneming.nl.",
};

export default async function ObservationsPage() {
  const obs = await fetchObservations();

  const inatCount = obs.filter((o) => o.source === "inat").length;
  const wnCount = obs.length - inatCount;
  const uniqSpecies = new Set(obs.map((o) => o.scientific_name)).size;

  return (
    <main className="play-page">
      <div className="play-map-stage">
        <ObservationsMapClient observations={obs} />

        <div className="play-search-overlay">
          <h1 className="obs-h">Recent Amsterdam wildlife</h1>
          <p className="play-meta-mini">
            <span>Last {DAYS} days</span>
            <span className="play-meta-counts">
              <b>{obs.length.toLocaleString()}</b> sightings ·{" "}
              <b>{uniqSpecies.toLocaleString()}</b> species
            </span>
          </p>
          <ul className="obs-legend">
            <li>
              <span className="obs-dot obs-dot-inat" /> iNaturalist (
              {inatCount.toLocaleString()})
            </li>
            <li>
              <span className="obs-dot obs-dot-wn" /> Waarneming.nl (
              {wnCount.toLocaleString()})
            </li>
          </ul>
        </div>
      </div>
    </main>
  );
}
