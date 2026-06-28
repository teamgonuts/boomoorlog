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
  // compute archetype medians the same way the home page does).
  const [{ data: genus }, { data: allStatBlocked }] = await Promise.all([
    supabase.from("genera").select("*").eq("slug", slug).maybeSingle(),
    supabase.from("genera").select("*").not("attack", "is", null),
  ]);

  if (!genus) notFound();

  const classified = classifyGenera(allStatBlocked ?? []);
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
