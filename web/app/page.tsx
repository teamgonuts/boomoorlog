import Link from "next/link";

import { classifyGenera, type Classified } from "@/lib/archetype";
import { toCard } from "@/lib/creature";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const STAT_BARS: { key: keyof Classified; label: string }[] = [
  { key: "attack", label: "ATK" },
  { key: "range", label: "RNG" },
  { key: "health", label: "HP" },
  { key: "attack_speed", label: "SPD" },
  { key: "move_speed", label: "MOV" },
];

export default async function HomePage() {
  const [
    { data: allGenera, error },
    { count: totalTrees },
    { data: creaturesRaw, count: totalCreatures },
  ] = await Promise.all([
    supabase.from("genera").select("*"),
    supabase.from("trees").select("*", { count: "exact", head: true }),
    supabase
      .from("creatures")
      .select("*", { count: "exact" })
      .order("tree_count", { ascending: false })
      .limit(24),
  ]);

  if (error) {
    return <p style={{ padding: 48, color: "#ff6b6b" }}>Error: {error.message}</p>;
  }

  const totalGenera = (allGenera ?? []).length;

  const cards = classifyGenera(allGenera ?? []).sort(
    (a, b) => b.tree_count - a.tree_count,
  );

  const creatureCards = (creaturesRaw ?? []).map(toCard);

  return (
    <main>
      <section className="hero">
        <h1>The Tree Roster</h1>
        <p>
          Every fully stat-blocked genus in Amsterdam, ready to march. Hover any
          card to see the stat bars. Click for the full dossier.
        </p>
        <div className="hero-stats">
          <div className="hstat">
            <b>{(totalTrees ?? 0).toLocaleString()}</b>
            <span>trees in Amsterdam</span>
          </div>
          <div className="hstat">
            <b>{totalGenera}</b>
            <span>genera in the city</span>
          </div>
          <div className="hstat">
            <b>{cards.length}</b>
            <span>playable archetypes</span>
          </div>
        </div>
      </section>

      <div className="grid">
        {cards.map((g) => (
          <GenusCard key={g.slug} g={g} />
        ))}
      </div>

      <section className="hero" style={{ marginTop: 48 }}>
        <h1>The Creature Roster</h1>
        <p>
          Every animal, insect, fungus, and lichen that lives in the Amsterdam
          trees — deduped across the tree roster. Top {creatureCards.length}{" "}
          most widespread shown below.{" "}
          <Link href="/wiki/creatures">See all {totalCreatures ?? 0} →</Link>
        </p>
      </section>

      <div className="grid">
        {creatureCards.map((c) => (
          <Link
            key={c.slug}
            href={`/wiki/creatures/${c.slug}`}
            className="card"
          >
            <div className="card-art">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="pixel"
                src={c.spriteUrl}
                alt=""
              />
            </div>
            <div className="card-name">{c.common_name}</div>
            <div className="card-common" style={{ fontStyle: "italic" }}>
              {c.latin_name ?? ""}
            </div>
            <div className="card-foot">
              <span className="cnt">🌳 {c.tree_count}</span>
              {c.form && (
                <span style={{ marginLeft: 8, opacity: 0.7, fontSize: 12 }}>
                  {c.formLabel}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}

function GenusCard({ g }: { g: Classified }) {
  return (
    <Link href={`/wiki/trees/${g.slug}`} className={`card rarity-${g.rarity}`}>
      <div className="card-art">
        {/* Plain <img>: pixel sprites bypass next/image optimization anyway */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className="pixel"
          src={`/sprites/${g.slug}.png`}
          alt={`${g.slug} sprite`}
        />
      </div>
      <div className="card-name">
        {g.slug}
        {g.isLegendary && (
          <span style={{ color: "var(--rare)", marginLeft: 4 }}>★</span>
        )}
      </div>
      <div className="card-common">{g.dutch_name ?? g.slug}</div>
      <div className="card-foot">
        <span className="cnt">🌳 {g.tree_count.toLocaleString()}</span>
      </div>

      <div className="card-stats">
        <div className="cs-name">{g.slug}</div>
        {STAT_BARS.map(({ key, label }) => {
          const v = g[key] as number | null;
          const pct = v != null ? Math.round(v * 10) : 0;
          return (
            <div className="cs-row" key={key as string}>
              <span className="cs-l">{label}</span>
              <span className="cs-t">
                <span className="cs-f" style={{ width: `${pct}%` }} />
              </span>
              <b>{v ?? "—"}</b>
            </div>
          );
        })}
        <div className="cs-power">
          <span>POWER</span>
          <b>{g.powerScore.toFixed(1)}</b>
        </div>
      </div>
    </Link>
  );
}
