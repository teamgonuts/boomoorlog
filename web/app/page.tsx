import Link from "next/link";

import { Sprite } from "@/components/Sprite";
import {
  ARCHETYPE_BLURBS,
  ARCHETYPE_ORDER,
  classifyGenera,
  type ArchetypeBase,
  type Classified,
} from "@/lib/archetype";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const { data: genera, error } = await supabase
    .from("genera")
    .select("*")
    .not("attack", "is", null);

  if (error) {
    return <p className="p-12 text-red-600">Error: {error.message}</p>;
  }

  const classified = classifyGenera(genera ?? []);
  const byArchetype: Record<ArchetypeBase, Classified[]> = {
    Bruiser: [],
    Juggernaut: [],
    Skirmisher: [],
    Support: [],
  };
  for (const g of classified) byArchetype[g.archetype].push(g);
  for (const list of Object.values(byArchetype)) {
    list.sort((a, b) => b.tree_count - a.tree_count);
  }

  return (
    <main className="min-h-screen p-8 md:p-12 max-w-6xl mx-auto">
      <header className="mb-12">
        <h1 className="text-5xl font-bold tracking-tight">🌳 Boomoorlog</h1>
        <p className="mt-3 text-lg text-gray-700 max-w-2xl">
          &ldquo;Tree war.&rdquo; Two Amsterdam ZIP codes battle tower-defense
          style using the <em>real</em> trees that grow in each postcode as
          combatants. {classified.length} genera fight in four archetypes.
        </p>
        <p className="mt-3">
          <Link href="/wiki" className="text-emerald-700 hover:underline">
            Browse the full roster →
          </Link>
        </p>
      </header>

      {ARCHETYPE_ORDER.map((archetype) => {
        const list = byArchetype[archetype];
        if (list.length === 0) return null;
        return (
          <section key={archetype} className="mb-12">
            <h2 className="text-2xl font-bold">{archetype}</h2>
            <p className="mt-1 text-sm text-gray-600 max-w-2xl">
              {ARCHETYPE_BLURBS[archetype]}
            </p>
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {list.map((g) => (
                <GenusCard key={g.slug} g={g} />
              ))}
            </div>
          </section>
        );
      })}
    </main>
  );
}

function GenusCard({ g }: { g: Classified }) {
  return (
    <Link
      href={`/wiki/${g.slug}`}
      className="block bg-white border border-stone-200 rounded p-3 hover:border-emerald-400 hover:shadow-sm transition"
    >
      <div className="flex items-start gap-3">
        <Sprite slug={g.slug} size={48} />
        <div className="min-w-0">
          <div className="font-semibold italic truncate">
            {g.latin_name}
            {g.isLegendary && (
              <span className="ml-1 text-amber-600" title="Legendary">
                ★
              </span>
            )}
          </div>
          <div className="text-xs text-gray-600 truncate">
            {g.dutch_name ?? "—"}
          </div>
          <div className="mt-1 text-xs text-gray-500 tabular-nums">
            {g.tree_count.toLocaleString()} trees
          </div>
        </div>
      </div>
    </Link>
  );
}
