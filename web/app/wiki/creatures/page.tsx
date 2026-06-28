import Link from "next/link";

import { FORM_LABEL, toCard } from "@/lib/creature";
import { supabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Creatures — Boomoorlog Wiki",
  description:
    "Every animal, insect, fungus and lichen that lives in the Amsterdam trees, deduped across the tree roster.",
};

type SearchParams = Promise<{ sort?: string }>;

// 7-day window for the "Recently spotted" badge.
const RECENT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

function isRecent(promoted_at: string | null): boolean {
  if (!promoted_at) return false;
  const t = Date.parse(promoted_at);
  if (Number.isNaN(t)) return false;
  return Date.now() - t < RECENT_WINDOW_MS;
}

export default async function CreaturesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { sort } = await searchParams;
  const sortMode: "abundant" | "recent" = sort === "recent" ? "recent" : "abundant";

  const query = supabase.from("creatures").select("*");
  const ordered =
    sortMode === "recent"
      ? query
          .order("promoted_at", { ascending: false, nullsFirst: false })
          .order("common_name", { ascending: true })
      : query
          .order("tree_count", { ascending: false })
          .order("common_name", { ascending: true });

  const { data: rows, error } = await ordered;

  if (error) {
    return <p style={{ padding: 48, color: "#ff6b6b" }}>Error: {error.message}</p>;
  }

  const cards = (rows ?? []).map(toCard);

  // Counts per form for the filter chips (only show forms that exist).
  const formCounts = new Map<string, number>();
  for (const c of cards) {
    if (!c.form) continue;
    formCounts.set(c.form, (formCounts.get(c.form) ?? 0) + 1);
  }
  const formsWithData = Array.from(formCounts.entries()).sort(
    (a, b) => b[1] - a[1],
  );

  return (
    <main>
      <section className="hero">
        <h1>The Creature Roster</h1>
        <p>
          {cards.length} animals, insects, fungi and lichens that live in the
          Amsterdam trees, deduped across the 55-genus tree roster. Click any
          card to see which trees host it.
        </p>
        <div className="hero-stats">
          <div className="hstat">
            <b>{cards.length}</b>
            <span>unique creatures</span>
          </div>
          <div className="hstat">
            <b>{Object.keys(FORM_LABEL).length}</b>
            <span>body plans</span>
          </div>
          <div className="hstat">
            <b>{cards.filter((c) => c.tree_count >= 5).length}</b>
            <span>found on 5+ trees</span>
          </div>
        </div>
      </section>

      <div className="toolbar" style={{ marginBottom: 16 }}>
        <div className="tb-group">
          <label>Sort</label>
          <Link
            href="/wiki/creatures"
            className="chip"
            style={{
              fontWeight: sortMode === "abundant" ? 700 : 400,
              textDecoration: sortMode === "abundant" ? "underline" : "none",
            }}
          >
            Most common
          </Link>
          <Link
            href="/wiki/creatures?sort=recent"
            className="chip"
            style={{
              fontWeight: sortMode === "recent" ? 700 : 400,
              textDecoration: sortMode === "recent" ? "underline" : "none",
            }}
          >
            Recently spotted
          </Link>
        </div>

        {formsWithData.length > 0 && (
          <div className="tb-group">
            <label>Form</label>
            {formsWithData.map(([form, count]) => (
              <span
                key={form}
                className="chip"
                style={{ pointerEvents: "none" }}
              >
                {FORM_LABEL[form] ?? form}{" "}
                <small style={{ opacity: 0.6 }}>({count})</small>
              </span>
            ))}
            {cards.some((c) => !c.form) && (
              <span
                className="chip"
                style={{ pointerEvents: "none", opacity: 0.6 }}
              >
                Unclassified ({cards.filter((c) => !c.form).length})
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid">
        {cards.map((c) => {
          const recent = isRecent(c.promoted_at);
          return (
            <Link
              key={c.slug}
              className="card"
              href={`/wiki/creatures/${c.slug}`}
              data-name={c.common_name}
            >
              <div className="card-art">
                {c.sprite_pending ? (
                  <div className="pixel pixel-pending">sprite pending</div>
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img className="pixel" src={c.spriteUrl} alt="" />
                )}
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
                {recent && (
                  <span className="badge star" style={{ marginLeft: 8 }}>
                    Recently spotted
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
