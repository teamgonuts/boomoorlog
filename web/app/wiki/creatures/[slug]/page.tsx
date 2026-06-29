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

const RECENT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

function isRecent(promoted_at: string | null): boolean {
  if (!promoted_at) return false;
  const t = Date.parse(promoted_at);
  if (Number.isNaN(t)) return false;
  return Date.now() - t < RECENT_WINDOW_MS;
}

export default async function CreaturePage({ params }: { params: Params }) {
  const { slug } = await params;

  const { data: organism } = await supabase
    .from("organisms")
    .select("*")
    .neq("category", "tree")
    .eq("slug", slug)
    .maybeSingle();

  if (!organism) {
    return notFound();
  }

  // Project to the legacy `creature` shape for the rest of the template.
  // Drops in step 9 along with the lib/creature.ts conversion.
  const creature = {
    slug: organism.slug,
    common_name: organism.common_name ?? organism.latin_name,
    latin_name: organism.latin_name,
    pic_file: organism.photo_path,
    tree_count: organism.tree_count,
    tree_genera: organism.tree_genera,
    form: organism.form,
    attack: organism.attack,
    range: organism.range,
    health: organism.health,
    attack_speed: organism.attack_speed,
    move_speed: organism.move_speed,
    source: organism.promoted_source ?? "curated",
    promoted_at: organism.promoted_at,
    taxon_group: organism.taxon_group,
    wikipedia_summary: organism.lore,
    observations_count: organism.observations_count,
    sprite_pending: organism.sprite_pending,
  };

  const isAuto = creature.source === "auto_observed";
  const recent = isRecent(creature.promoted_at);

  // Pull host-tree organisms only when we have any — auto-promoted creatures
  // have an empty tree_genera array and we'd otherwise issue a useless query.
  const { data: hostGenera } =
    creature.tree_genera && creature.tree_genera.length > 0
      ? await supabase
          .from("organisms")
          .select("slug, latin_name, display_name, tree_count")
          .eq("category", "tree")
          .in("slug", creature.tree_genera)
      : { data: [] as Array<{
          slug: string;
          latin_name: string;
          display_name: string | null;
          tree_count: number | null;
        }> };

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

          {isAuto ? (
            <>
              <p className="lead">
                Spotted in Amsterdam in the last 30 days.
                {creature.taxon_group ? ` ${creature.taxon_group}.` : ""}
              </p>

              <h3>From recent sightings</h3>
              {creature.wikipedia_summary ? (
                <p style={{ lineHeight: 1.6 }}>{creature.wikipedia_summary}</p>
              ) : (
                <p style={{ opacity: 0.7 }}>
                  No Wikipedia summary available yet.
                </p>
              )}
              <p style={{ marginTop: 12, fontSize: 14, opacity: 0.8 }}>
                Seen {creature.observations_count} time
                {creature.observations_count === 1 ? "" : "s"} in Amsterdam in
                the last 30 days.{" "}
                <Link href="/observations">See on map →</Link>
              </p>
            </>
          ) : (
            <>
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
            </>
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
              {creature.sprite_pending ? (
                <div className="pixel pixel-pending">sprite pending</div>
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  className="pixel"
                  src={spriteSrc}
                  alt={`${creature.common_name} battle sprite`}
                />
              )}
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
              {creature.sprite_pending ? (
                <div className="pixel pixel-pending">sprite pending</div>
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  className="pixel"
                  src={spriteSrc}
                  alt={`${creature.common_name} sprite`}
                />
              )}
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
            {isAuto
              ? creature.taxon_group && (
                  <span className="badge">{creature.taxon_group}</span>
                )
              : creature.form && (
                  <span className="badge">{formLabel(creature.form)}</span>
                )}
            {recent && <span className="badge star">Recently spotted</span>}
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

          {isAuto ? (
            <div className="ib-count">
              {creature.observations_count} sighting
              {creature.observations_count === 1 ? "" : "s"} in last 30 days
            </div>
          ) : (
            <div className="ib-count">
              Found on {creature.tree_count} tree{" "}
              {creature.tree_count === 1 ? "genus" : "genera"}
            </div>
          )}
        </aside>
      </article>
    </main>
  );
}
