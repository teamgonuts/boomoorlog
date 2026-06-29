import Link from "next/link";
import { notFound } from "next/navigation";

import {
  ARCHETYPE_FULL,
  RARITY_LABEL,
  classifyGenera,
} from "@/lib/archetype";
import { parseLore } from "@/lib/lore";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

type Params = Promise<{ slug: string }>;

const STAT_LABELS: { key: "attack" | "range" | "health" | "attack_speed" | "move_speed"; label: string }[] = [
  { key: "attack", label: "Attack" },
  { key: "range", label: "Range" },
  { key: "health", label: "Health" },
  { key: "attack_speed", label: "Atk Speed" },
  { key: "move_speed", label: "Movement" },
];

export async function generateMetadata({ params }: { params: Params }) {
  const { slug } = await params;
  return { title: `${slug} | Boomoorlog Wiki` };
}

export default async function GenusPage({ params }: { params: Params }) {
  const { slug } = await params;

  // Pull this genus + the full stat-blocked roster (we need the latter to
  // compute archetype medians the same way the home page does) + every
  // creature whose tree_genera contains this genus (for the cross-link).
  const [genusResp, allStatBlockedResp, creaturesResp] = await Promise.all([
    supabase
      .from("organisms")
      .select("*")
      .eq("category", "tree")
      .eq("slug", slug)
      .maybeSingle(),
    supabase
      .from("organisms")
      .select("*")
      .eq("category", "tree")
      .not("attack", "is", null),
    supabase
      .from("organisms")
      .select("slug, common_name, latin_name, form")
      .neq("category", "tree")
      .contains("tree_genera", [slug])
      .order("tree_count", { ascending: false })
      .limit(48),
  ]);

  const genus = genusResp.data;
  const allStatBlocked = allStatBlockedResp.data ?? [];
  // Renaming on the wire: the cross-link query returns Organism rows but
  // only the three fields we render here, all shared with Creature.
  const creatures = (creaturesResp.data ?? []).map((o) => ({
    slug: o.slug,
    common_name: o.common_name ?? o.latin_name,
    latin_name: o.latin_name,
    form: o.form,
  }));

  if (!genus) {
    return notFound();
  }

  const classified = classifyGenera(allStatBlocked);
  const me = classified.find((g) => g.slug === genus.slug);
  const rarityClass = me ? `rarity-${me.rarity}` : "rarity-common";
  const { combatFlavor, facts, commonName } = parseLore(genus.lore);

  const photoSrc = `/photos/${genus.slug}.jpg`;
  const spriteSrc = `/sprites/${genus.slug}.png`;

  return (
    <main>
      <p style={{ marginBottom: 18 }}>
        <Link href="/wiki/trees" style={{ fontSize: 13 }}>
          ← All trees
        </Link>
      </p>

      <article className={`char ${rarityClass}`}>
        <div className="char-body">
          <h1>
            <span style={{ fontStyle: "italic" }}>{genus.latin_name}</span>
            {commonName ? <span className="common"> — {commonName}</span> : null}
            {genus.dutch_name ? (
              <span className="nl"> ({genus.dutch_name})</span>
            ) : null}
          </h1>

          {genus.personality && <p className="lead">{genus.personality}</p>}

          {combatFlavor && (
            <>
              <h3>Combat flavor</h3>
              <p>{combatFlavor}</p>
            </>
          )}

          {facts.length > 0 && (
            <>
              <h3>Real-world facts</h3>
              <div className="facts">
                {facts.map((f) => (
                  <div className="fact" key={f.key}>
                    <span className="fact-k">{f.key}</span>
                    <span className="fact-v">{f.value}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {creatures.length > 0 && (
            <>
              <h3>
                Living creatures on this tree{" "}
                <span style={{ opacity: 0.5, fontSize: 13, fontWeight: 400 }}>
                  ({creatures.length})
                </span>
              </h3>
              <div
                className="grid"
                style={{
                  gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                  gap: 10,
                  marginBottom: 18,
                }}
              >
                {creatures.map((c) => (
                  <Link
                    key={c.slug}
                    href={`/wiki/creatures/${c.slug}`}
                    className="card"
                    style={{ padding: 8, textAlign: "center" }}
                  >
                    <div className="card-art" style={{ height: 72 }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="pixel"
                        src={`/creature_sprites/${c.slug}.png`}
                        alt=""
                        style={{ maxHeight: 72 }}
                      />
                    </div>
                    <div className="card-name" style={{ fontSize: 12 }}>
                      {c.common_name}
                    </div>
                    {c.latin_name && (
                      <div
                        className="card-common"
                        style={{
                          fontStyle: "italic",
                          fontSize: 10,
                          opacity: 0.7,
                        }}
                      >
                        {c.latin_name}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </>
          )}

          <h3>Gallery</h3>
          <div className="gallery">
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photoSrc} alt={`${genus.slug} real tree`} />
              <figcaption>The real tree</figcaption>
            </figure>
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="pixel"
                src={spriteSrc}
                alt={`${genus.slug} battle sprite`}
              />
              <figcaption>Battle sprite</figcaption>
            </figure>
          </div>
        </div>

        <aside className="infobox">
          <div className="ib-compare">
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photoSrc} alt={`${genus.slug} real tree`} />
              <figcaption>Real tree</figcaption>
            </figure>
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className="pixel" src={spriteSrc} alt={`${genus.slug} sprite`} />
              <figcaption>Sprite</figcaption>
            </figure>
          </div>
          <h2 className="ib-name">{genus.latin_name}</h2>
          {commonName && <div className="ib-sub">{commonName}</div>}
          <div className="ib-badges">
            {me && (
              <span className={`badge rarity-${me.rarity}`}>
                {me.isLegendary && "★ "}
                {RARITY_LABEL[me.rarity]}
              </span>
            )}
          </div>
          {me && <div className="ib-arch">{ARCHETYPE_FULL[me.archetype]}</div>}
          {me ? (
            <>
              <div className="ib-stats">
                {STAT_LABELS.map(({ key, label }) => {
                  const v = me[key] as number | null;
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
              <div className="ib-power">
                <span>Power</span>
                <b>{me.powerScore.toFixed(1)}</b>
              </div>
            </>
          ) : (
            <div className="ib-stats unranked">
              No stat block — research data missing for this genus.
            </div>
          )}
          <div className="ib-count">
            {genus.tree_count.toLocaleString()} trees in Amsterdam
          </div>
        </aside>
      </article>
    </main>
  );
}
