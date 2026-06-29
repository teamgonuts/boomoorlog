import Link from "next/link";

import { classifyGenera, type Classified } from "@/lib/archetype";
import { toCard } from "@/lib/creature";
import { supabase } from "@/lib/supabase";
import type { Creature, Genus, Organism } from "@/types/supabase";

export const dynamic = "force-dynamic";

const STAT_BARS: { key: keyof Classified; label: string }[] = [
  { key: "attack", label: "ATK" },
  { key: "range", label: "RNG" },
  { key: "health", label: "HP" },
  { key: "attack_speed", label: "SPD" },
  { key: "move_speed", label: "MOV" },
];

// Adapter: Organism rows have every Genus column plus more (taxonomy,
// behavior, etc.). For the tree-roster homepage we only need the legacy
// Genus shape; we pluck the matching columns and pass them through the
// archetype classifier untouched. When the lib helpers themselves move
// to the Organism type (Phase B step 9), this adapter goes away.
function organismToGenus(o: Organism): Genus {
  return {
    slug: o.slug,
    latin_name: o.latin_name,
    dutch_name: o.dutch_name,
    display_name: o.display_name,
    attack: o.attack,
    range: o.range,
    health: o.health,
    attack_speed: o.attack_speed,
    move_speed: o.move_speed,
    world_rarity_multiplier: o.world_rarity_multiplier,
    avg_height_m: o.avg_height_m,
    avg_diameter_cm: o.avg_diameter_cm,
    personality: o.personality,
    tree_count: o.tree_count,
    sprite_path: o.sprite_path,
    lore: o.lore,
    created_at: o.created_at,
  };
}

// The creature card helper expects the legacy Creature shape with
// pic_file. Organism rows store the same value as photo_path; this
// adapter bridges until creature.ts moves over in step 9.
function organismToCreature(o: Organism): Creature {
  return {
    slug: o.slug,
    common_name: o.common_name ?? o.latin_name,
    latin_name: o.latin_name,
    pic_file: o.photo_path,
    tree_count: o.tree_count,
    tree_genera: o.tree_genera,
    form: o.form,
    attack: o.attack,
    range: o.range,
    health: o.health,
    attack_speed: o.attack_speed,
    move_speed: o.move_speed,
    created_at: o.created_at,
    source: o.promoted_source ?? "curated",
    promoted_at: o.promoted_at,
    taxon_group: o.taxon_group,
    wikipedia_summary: o.lore,
    observations_count: o.observations_count,
    sprite_pending: o.sprite_pending,
  };
}

export default async function HomePage() {
  // Two filtered queries — supabase-js caps each .select at 1000 rows by
  // default, and the master organisms table now has 2.7k rows. Filtering
  // by category server-side both fits comfortably under the cap and pushes
  // the work onto Postgres indexes (organisms_category_idx).
  const [
    treesResp,
    creaturesResp,
    treesCount,
    creatureTotal,
  ] = await Promise.all([
    supabase.from("organisms").select("*").eq("category", "tree"),
    supabase
      .from("organisms")
      .select("*")
      .neq("category", "tree")
      .not("sprite_path", "is", null)
      .eq("sprite_pending", false)
      .order("tree_count", { ascending: false })
      .limit(24),
    supabase.from("trees").select("*", { count: "exact", head: true }),
    supabase
      .from("organisms")
      .select("*", { count: "exact", head: true })
      .neq("category", "tree"),
  ]);

  if (treesResp.error) {
    return <p style={{ padding: 48, color: "#ff6b6b" }}>Error: {treesResp.error.message}</p>;
  }
  if (creaturesResp.error) {
    return <p style={{ padding: 48, color: "#ff6b6b" }}>Error: {creaturesResp.error.message}</p>;
  }

  const treeOrganisms = treesResp.data ?? [];
  const creatureOrganisms = creaturesResp.data ?? [];
  const totalTrees = treesCount.count ?? 0;
  const totalCreatures = creatureTotal.count ?? 0;

  const totalGenera = treeOrganisms.length;

  const cards = classifyGenera(treeOrganisms.map(organismToGenus)).sort(
    (a, b) => b.tree_count - a.tree_count,
  );

  const creatureCards = creatureOrganisms.map(organismToCreature).map(toCard);

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
            <b>{totalTrees.toLocaleString()}</b>
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
          <Link href="/wiki/creatures">See all {totalCreatures} →</Link>
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
