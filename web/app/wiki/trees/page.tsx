import Link from "next/link";

import { classifyGenera } from "@/lib/archetype";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Trees — Boomoorlog Wiki",
  description:
    "All Amsterdam tree genera, ranked by power. Quick sortable table view.",
};

export default async function TreesListPage() {
  const { data: organisms, error } = await supabase
    .from("organisms")
    .select("*")
    .eq("category", "tree")
    .not("attack", "is", null);

  if (error) {
    return <p style={{ padding: 48, color: "#ff6b6b" }}>Error: {error.message}</p>;
  }

  const rows = classifyGenera(organisms ?? []).sort(
    (a, b) => b.powerScore - a.powerScore,
  );

  return (
    <main>
      <section className="hero">
        <h1>Trees — by Power</h1>
        <p>
          The full roster as a sortable table. Prefer cards?{" "}
          <Link href="/">Go back to the gallery</Link>.
        </p>
      </section>

      <table className="trees-table">
        <thead>
          <tr>
            <th>Genus</th>
            <th>Common</th>
            <th>Dutch</th>
            <th>Archetype</th>
            <th className="num">Trees</th>
            <th className="num">Atk</th>
            <th className="num">Rng</th>
            <th className="num">HP</th>
            <th className="num">A.Spd</th>
            <th className="num">Move</th>
            <th className="num">Power</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((g) => (
            <tr key={g.slug} className={`rarity-${g.rarity}`}>
              <td>
                <Link href={`/wiki/trees/${g.slug}`}>
                  <em>{g.slug}</em>
                  {g.isLegendary && (
                    <span style={{ color: "var(--rare)", marginLeft: 4 }}>★</span>
                  )}
                </Link>
              </td>
              <td>{(g as { common_name?: string }).common_name ?? "—"}</td>
              <td>{g.dutch_name ?? "—"}</td>
              <td>{g.archetype}</td>
              <td className="num">{g.tree_count.toLocaleString()}</td>
              <td className="num">{g.attack ?? "—"}</td>
              <td className="num">{g.range ?? "—"}</td>
              <td className="num">{g.health ?? "—"}</td>
              <td className="num">{g.attack_speed ?? "—"}</td>
              <td className="num">{g.move_speed ?? "—"}</td>
              <td className="num" style={{ color: "var(--gold)", fontWeight: 700 }}>
                {g.powerScore.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
