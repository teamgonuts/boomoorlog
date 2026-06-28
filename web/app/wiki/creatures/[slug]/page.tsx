import Link from "next/link";
import { notFound } from "next/navigation";

import { creaturePhotoUrl, creatureSpriteUrl, formLabel } from "@/lib/creature";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }) {
  const { slug } = await params;
  return { title: `${slug} | Boomoorlog Wiki — Creatures` };
}

const STAT_LABELS: {
  key: "attack" | "range" | "health" | "attack_speed" | "move_speed";
  label: string;
}[] = [
  { key: "attack", label: "Attack" },
  { key: "range", label: "Range" },
  { key: "health", label: "Health" },
  { key: "attack_speed", label: "Atk Speed" },
  { key: "move_speed", label: "Movement" },
];

export default async function CreaturePage({ params }: { params: Params }) {
  const { slug } = await params;

  const { data: creature } = await supabase
    .from("creatures")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();

  if (!creature) {
    return notFound();
  }

  // Pull the host-tree genera so we can show "lives on" with display names.
  const { data: hostGenera } = await supabase
    .from("genera")
    .select("slug, latin_name, display_name, tree_count")
    .in("slug", creature.tree_genera);

  const sortedHosts = (hostGenera ?? [])
    .slice()
    .sort((a, b) => (b.tree_count ?? 0) - (a.tree_count ?? 0));

  const photoSrc = creaturePhotoUrl(creature.pic_file);
  const spriteSrc = creatureSpriteUrl(creature.slug);

  const hasStats = STAT_LABELS.some((s) => creature[s.key] != null);

  return (
    <main>
      <p style={{ marginBottom: 18 }}>
        <Link href="/wiki/creatures" style={{ fontSize: 13 }}>
          ← All creatures
        </Link>
      </p>

      <article className="char">
        <div className="char-body">
          <h1>
            {creature.common_name}
            {creature.latin_name ? (
              <span className="common" style={{ fontStyle: "italic" }}>
                {" "}
                — {creature.latin_name}
              </span>
            ) : null}
          </h1>

          <p className="lead">
            Found on {creature.tree_count} Amsterdam tree{" "}
            {creature.tree_count === 1 ? "genus" : "genera"}.
          </p>

          <h3>Lives on these trees</h3>
          {sortedHosts.length === 0 ? (
            <p style={{ opacity: 0.7 }}>No host trees recorded.</p>
          ) : (
            <ul style={{ lineHeight: 1.8 }}>
              {sortedHosts.map((g) => (
                <li key={g.slug}>
                  <Link href={`/wiki/trees/${g.slug}`}>
                    <strong>{g.latin_name}</strong>
                  </Link>
                  {g.display_name ? ` — ${g.display_name}` : ""}
                  <span style={{ opacity: 0.6, marginLeft: 8 }}>
                    ({(g.tree_count ?? 0).toLocaleString()} trees)
                  </span>
                </li>
              ))}
            </ul>
          )}

          <h3>Gallery</h3>
          <div className="gallery">
            {photoSrc && (
              <figure>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photoSrc} alt={`${creature.common_name} real photo`} />
                <figcaption>The real creature</figcaption>
              </figure>
            )}
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="pixel"
                src={spriteSrc}
                alt={`${creature.common_name} battle sprite`}
              />
              <figcaption>Battle sprite</figcaption>
            </figure>
          </div>
        </div>

        <aside className="infobox">
          <div className="ib-compare">
            {photoSrc && (
              <figure>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photoSrc} alt={`${creature.common_name} real photo`} />
                <figcaption>Real</figcaption>
              </figure>
            )}
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="pixel"
                src={spriteSrc}
                alt={`${creature.common_name} sprite`}
              />
              <figcaption>Sprite</figcaption>
            </figure>
          </div>
          <h2 className="ib-name">{creature.common_name}</h2>
          {creature.latin_name && (
            <div className="ib-sub" style={{ fontStyle: "italic" }}>
              {creature.latin_name}
            </div>
          )}
          <div className="ib-badges">
            {creature.form && (
              <span className="badge">{formLabel(creature.form)}</span>
            )}
          </div>

          {hasStats ? (
            <div className="ib-stats">
              {STAT_LABELS.map(({ key, label }) => {
                const v = creature[key] as number | null;
                const pct = v != null ? Math.round(v * 10) : 0;
                return (
                  <div className="stat" key={key}>
                    <span className="stat-l">{label}</span>
                    <span className="stat-track">
                      <span
                        className="stat-fill"
                        style={{ width: `${pct}%` }}
                      />
                    </span>
                    <span className="stat-n">{v ?? "—"}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="ib-stats unranked">
              No combat stats yet — coming with the engine.
            </div>
          )}

          <div className="ib-count">
            Found on {creature.tree_count} tree{" "}
            {creature.tree_count === 1 ? "genus" : "genera"}
          </div>
        </aside>
      </article>
    </main>
  );
}
