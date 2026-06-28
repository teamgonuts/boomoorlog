import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";

import { Sprite } from "@/components/Sprite";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const STAT_LABELS: { key: StatKey; label: string; help: string }[] = [
  { key: "attack", label: "Attack", help: "wood hardness" },
  { key: "range", label: "Range", help: "average height" },
  { key: "health", label: "Health", help: "mass + longevity" },
  { key: "attack_speed", label: "Attack speed", help: "inverse hardness" },
  { key: "move_speed", label: "Move", help: "growth vigor" },
] as const;

type StatKey =
  | "attack"
  | "range"
  | "health"
  | "attack_speed"
  | "move_speed";

export default async function GenusPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const { data: genus, error } = await supabase
    .from("genera")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();

  if (error) {
    return <p className="p-12 text-red-600">Error: {error.message}</p>;
  }
  if (!genus) notFound();

  return (
    <main className="min-h-screen p-8 md:p-12 max-w-4xl mx-auto">
      <Link
        href="/wiki"
        className="text-sm text-emerald-700 hover:underline"
      >
        ← Wiki
      </Link>

      <header className="mt-4 flex flex-row items-end gap-6">
        <Sprite slug={genus.slug} size={128} />
        <div>
          <h1 className="text-4xl font-bold italic">{genus.latin_name}</h1>
          <p className="mt-1 text-lg text-gray-700">
            {genus.dutch_name ?? "—"} &middot;{" "}
            {genus.tree_count.toLocaleString()} trees in Amsterdam
          </p>
          {Number(genus.world_rarity_multiplier) > 1 && (
            <p className="mt-1 text-sm text-amber-700">
              ★ Legendary &middot; world-rarity multiplier{" "}
              {Number(genus.world_rarity_multiplier).toFixed(2)}×
            </p>
          )}
        </div>
      </header>

      {genus.personality && (
        <section className="mt-8">
          <p className="italic text-lg text-gray-800 border-l-4 border-emerald-300 pl-4">
            {genus.personality}
          </p>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-sm uppercase tracking-wide text-gray-500 mb-3">
          Stats
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {STAT_LABELS.map(({ key, label, help }) => {
            const v = genus[key];
            return (
              <div
                key={key}
                className="bg-white border border-stone-200 rounded p-3"
              >
                <div className="text-xs uppercase text-gray-500">{label}</div>
                <div className="mt-1 text-2xl font-bold tabular-nums">
                  {v ?? "—"}
                  <span className="text-sm font-normal text-gray-400">
                    /10
                  </span>
                </div>
                <div className="mt-1 text-xs text-gray-400">{help}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm uppercase tracking-wide text-gray-500 mb-3">
          Data
        </h2>
        <dl className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          <DataCell label="Trees in Amsterdam" value={genus.tree_count.toLocaleString()} />
          <DataCell
            label="Avg height"
            value={genus.avg_height_m ? `${genus.avg_height_m} m` : "—"}
          />
          <DataCell
            label="Avg trunk diameter"
            value={genus.avg_diameter_cm ? `${genus.avg_diameter_cm} cm` : "—"}
          />
        </dl>
      </section>

      {genus.lore && (
        <section className="mt-8 prose prose-stone max-w-none">
          <h2 className="text-sm uppercase tracking-wide text-gray-500 mb-3 not-prose">
            Lore
          </h2>
          <ReactMarkdown>{genus.lore}</ReactMarkdown>
        </section>
      )}
    </main>
  );
}

function DataCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-stone-200 rounded p-3">
      <dt className="text-xs uppercase text-gray-500">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}
