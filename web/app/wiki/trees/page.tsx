import Link from "next/link";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Wiki — Boomoorlog",
  description: "Tree genus roster: stat blocks for every Amsterdam tree archetype.",
};

export default async function WikiIndexPage() {
  const { data: genera, error } = await supabase
    .from("genera")
    .select("*")
    .not("attack", "is", null)
    .order("tree_count", { ascending: false });

  if (error) {
    return <p className="p-12 text-red-600">Error: {error.message}</p>;
  }

  return (
    <main className="min-h-screen p-8 md:p-12 max-w-6xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Wiki — Genus Roster</h1>
        <p className="mt-2 text-sm text-gray-600">
          {genera?.length ?? 0} stat-blocked genera. Stats normalised 1–10
          from the Amsterdam tree dataset + per-genus research. Click a row
          for full details.
        </p>
      </header>

      <table className="w-full text-sm border-separate border-spacing-y-1">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="p-2">Genus</th>
            <th className="p-2">Dutch</th>
            <th className="p-2 text-right">Trees</th>
            <th className="p-2 text-right">Atk</th>
            <th className="p-2 text-right">Rng</th>
            <th className="p-2 text-right">HP</th>
            <th className="p-2 text-right">A.Spd</th>
            <th className="p-2 text-right">Move</th>
            <th className="p-2 text-right">Rarity</th>
          </tr>
        </thead>
        <tbody>
          {genera?.map((g) => (
            <tr key={g.slug} className="bg-white hover:bg-stone-50">
              <td className="p-2 font-medium">
                <Link
                  href={`/wiki/trees/${g.slug}`}
                  className="text-emerald-700 hover:underline"
                >
                  {g.slug}
                </Link>
              </td>
              <td className="p-2 text-gray-700">{g.dutch_name ?? "—"}</td>
              <td className="p-2 text-right tabular-nums">
                {g.tree_count.toLocaleString()}
              </td>
              <td className="p-2 text-right tabular-nums">{g.attack ?? "—"}</td>
              <td className="p-2 text-right tabular-nums">{g.range ?? "—"}</td>
              <td className="p-2 text-right tabular-nums">{g.health ?? "—"}</td>
              <td className="p-2 text-right tabular-nums">
                {g.attack_speed ?? "—"}
              </td>
              <td className="p-2 text-right tabular-nums">
                {g.move_speed ?? "—"}
              </td>
              <td className="p-2 text-right tabular-nums">
                {Number(g.world_rarity_multiplier).toFixed(2)}×
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
