"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

export type AreaTree = {
  slug: string;
  n: number;
  pct: number;
  dutch: string;
  rarity: "common" | "notable" | "rare";
};

export type AreaCreature = {
  slug: string;
  common_name: string;
  latin_name: string | null;
};

/**
 * Right-side overlay on /play. Lists trees-in-area (by genus, with counts)
 * and creatures-in-area (filtered server-side by tree_genera overlap), with
 * a single search input that filters both lists inline.
 *
 * Each row is a Link to the corresponding wiki page.
 */
export function AreaPanel({
  trees,
  creatures,
}: {
  trees: AreaTree[];
  creatures: AreaCreature[];
}) {
  const [q, setQ] = useState("");
  const [tab, setTab] = useState<"trees" | "creatures">("trees");
  const needle = q.trim().toLowerCase();

  const { filteredTrees, filteredCreatures } = useMemo(() => {
    if (!needle) return { filteredTrees: trees, filteredCreatures: creatures };
    return {
      filteredTrees: trees.filter(
        (t) =>
          t.slug.toLowerCase().includes(needle) ||
          t.dutch.toLowerCase().includes(needle),
      ),
      filteredCreatures: creatures.filter(
        (c) =>
          c.common_name.toLowerCase().includes(needle) ||
          (c.latin_name?.toLowerCase().includes(needle) ?? false) ||
          c.slug.toLowerCase().includes(needle),
      ),
    };
  }, [needle, trees, creatures]);

  const activeList = tab === "trees" ? filteredTrees : filteredCreatures;
  const otherCount =
    tab === "trees" ? filteredCreatures.length : filteredTrees.length;
  const otherTabLabel = tab === "trees" ? "Creatures" : "Trees";

  return (
    <aside className="area-panel">
      <div className="area-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "trees"}
          className={`area-tab ${tab === "trees" ? "active" : ""}`}
          onClick={() => setTab("trees")}
        >
          Trees <span className="area-tab-count">{filteredTrees.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "creatures"}
          className={`area-tab ${tab === "creatures" ? "active" : ""}`}
          onClick={() => setTab("creatures")}
        >
          Creatures{" "}
          <span className="area-tab-count">{filteredCreatures.length}</span>
        </button>
      </div>

      <div className="area-search">
        <svg
          aria-hidden="true"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={`Search ${tab}`}
          spellCheck={false}
          autoCorrect="off"
          autoComplete="off"
        />
        {q && (
          <button
            type="button"
            className="area-clear"
            aria-label="Clear search"
            onClick={() => setQ("")}
          >
            ×
          </button>
        )}
      </div>

      <div className="area-scroll" role="tabpanel">
        {tab === "trees" && filteredTrees.length > 0 && (
          <ol className="area-list">
            {filteredTrees.map((t) => (
              <li key={t.slug} className={`area-row rarity-${t.rarity}`}>
                <Link href={`/wiki/trees/${t.slug}`} className="area-link">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    className="pixel area-icon"
                    src={`/sprites/${t.slug}.png`}
                    alt=""
                    width={32}
                    height={32}
                  />
                  <div className="area-body">
                    <div className="area-name">
                      <em>{t.slug}</em>{" "}
                      <span className="area-dutch">{t.dutch}</span>
                    </div>
                    <div className="area-meta">
                      {t.n.toLocaleString()} · {t.pct.toFixed(1)}%
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}

        {tab === "creatures" && filteredCreatures.length > 0 && (
          <ol className="area-list">
            {filteredCreatures.map((c) => (
              <li key={c.slug} className="area-row">
                <Link href={`/wiki/creatures/${c.slug}`} className="area-link">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    className="pixel area-icon"
                    src={`/creature_sprites/${c.slug}.png`}
                    alt=""
                    width={32}
                    height={32}
                  />
                  <div className="area-body">
                    <div className="area-name area-name-creature">
                      {c.common_name}
                    </div>
                    {c.latin_name && (
                      <div className="area-meta area-latin">
                        {c.latin_name}
                      </div>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}

        {activeList.length === 0 && (
          <p className="area-empty">
            {q ? (
              <>
                No {tab} match <em>&ldquo;{q}&rdquo;</em>.
                {otherCount > 0 && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="area-empty-jump"
                      onClick={() =>
                        setTab(tab === "trees" ? "creatures" : "trees")
                      }
                    >
                      {otherCount} in {otherTabLabel} →
                    </button>
                  </>
                )}
              </>
            ) : (
              <>No {tab} in this neighborhood.</>
            )}
          </p>
        )}
      </div>
    </aside>
  );
}
