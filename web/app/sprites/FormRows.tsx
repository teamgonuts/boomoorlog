/**
 * FormRows.tsx — client component that renders every form row on
 * /sprites, keeps the visual layout the user liked (form template on
 * the left, meta in the middle, per-organism photo|sprite pairs on
 * the right) but extends each row to show ALL matching species with
 * per-row pagination, plus a sticky filter bar at the top with sprite
 * thumbnails so you can toggle which rows are visible.
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import type { GalleryItem } from "@/lib/sprite-gallery";

/** Row config passed from the server. Same shape as FormEntry but with
 *  a matcher spec instead of a hand-coded example list — the client
 *  applies the matcher to the gallery items to build the row's pairs. */
export type FormRowSpec = {
  id: string;                          // #anchor id
  label: string;                       // display label
  kind: "new" | "creature" | "tree";
  count: string;                       // human-readable count blurb (unchanged)
  desc: string;
  photoNote?: string;
  subModes?: string[];
  sprites: { src: string; caption?: string }[];   // form template thumbnails
  match: FormMatcher;                  // decides which gallery items belong here
};

/**
 * Which gallery items belong to this row. `form` is required; `aspectLt`
 * and `aspectGte` split sub-modes (e.g. reptile <1 = turtle, >=1 = lizard).
 */
export type FormMatcher = {
  form: string;
  aspectLt?: number;   // include only items with aspect < this
  aspectGte?: number;  // include only items with aspect >= this
};

type Props = {
  rows: FormRowSpec[];
  gallery: GalleryItem[];
};

const PAGE_SIZE = 12;

export function FormRows({ rows, gallery }: Props) {
  const [activeForms, setActiveForms] = useState<Set<string>>(new Set());
  const [onlyWithPhoto, setOnlyWithPhoto] = useState(false);
  const [query, setQuery] = useState("");

  // Build the item list for each row once, keyed by row.id.
  const itemsByRow = useMemo(() => {
    const map = new Map<string, GalleryItem[]>();
    for (const r of rows) {
      const matched = gallery.filter((it) => matchesRow(it, r.match));
      map.set(r.id, matched);
    }
    return map;
  }, [rows, gallery]);

  // Apply filter chips / search / photo-only to a row's items.
  const filteredByRow = useMemo(() => {
    const q = query.trim().toLowerCase();
    const map = new Map<string, GalleryItem[]>();
    for (const r of rows) {
      const base = itemsByRow.get(r.id) ?? [];
      const filtered = base.filter((it) => {
        if (onlyWithPhoto && !it.photoUrl) return false;
        if (q && !it.slug.toLowerCase().includes(q)) return false;
        return true;
      });
      map.set(r.id, filtered);
    }
    return map;
  }, [rows, itemsByRow, query, onlyWithPhoto]);

  // Total counts per row for the filter-chip thumbnails
  const chipRows = useMemo(() => {
    return rows.map((r) => ({
      row: r,
      count: (itemsByRow.get(r.id) ?? []).length,
      filteredCount: (filteredByRow.get(r.id) ?? []).length,
    })).filter((r) => r.count > 0);
  }, [rows, itemsByRow, filteredByRow]);

  // Which rows to display: if any chip is active, only those rows;
  // otherwise all rows that have at least one filtered item.
  const visibleRows = rows.filter((r) => {
    if (activeForms.size > 0) return activeForms.has(r.id);
    // Hide rows that end up empty under current filters (e.g. photo-only
    // + a form with no photos on disk).
    return (filteredByRow.get(r.id) ?? []).length > 0
        || (itemsByRow.get(r.id) ?? []).length === 0;    // keep "no items" rows for photoNote
  });

  const toggleForm = (id: string) => {
    setActiveForms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const clearFilters = () => {
    setActiveForms(new Set());
    setQuery("");
    setOnlyWithPhoto(false);
  };

  const anyFilterActive = query.length > 0 || activeForms.size > 0 || onlyWithPhoto;

  return (
    <div className="sl-formrows">
      <div className="sl-controls">
        <input
          className="sl-controls-search"
          type="search"
          placeholder="Search species by slug…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="sl-controls-checkbox">
          <input
            type="checkbox"
            checked={onlyWithPhoto}
            onChange={(e) => setOnlyWithPhoto(e.target.checked)}
          />
          only species with a photo
        </label>
        {anyFilterActive && (
          <button className="sl-controls-clear" onClick={clearFilters}>
            clear filters
          </button>
        )}
      </div>

      <div className="sl-chip-label">
        Filter by sprite form — click a thumbnail to toggle:
      </div>
      <div className="sl-chips">
        {chipRows.map(({ row, count, filteredCount }) => {
          const active = activeForms.has(row.id);
          return (
            <button
              key={row.id}
              type="button"
              className={`sl-fchip${active ? " sl-fchip-active" : ""}`}
              onClick={() => toggleForm(row.id)}
              title={`${filteredCount} of ${count} ${row.label}`}
            >
              <div className="sl-fchip-thumb">
                {row.sprites.map((s) => (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    key={s.src}
                    className="pixel"
                    src={s.src}
                    alt=""
                    loading="lazy"
                  />
                ))}
              </div>
              <div className="sl-fchip-label">
                <code>{row.label}</code>
                <span className="sl-fchip-count">
                  {filteredCount === count ? count : `${filteredCount}/${count}`}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="sl-rows">
        {visibleRows.map((r) => (
          <FormRowClient
            key={r.id}
            row={r}
            items={filteredByRow.get(r.id) ?? []}
            totalCount={(itemsByRow.get(r.id) ?? []).length}
          />
        ))}
      </div>

      {visibleRows.length === 0 && (
        <div className="sl-empty">
          No rows match those filters.{" "}
          <button onClick={clearFilters}>reset</button>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ //
// Row + pagination                                                   //
// ------------------------------------------------------------------ //
function FormRowClient({
  row,
  items,
  totalCount,
}: {
  row: FormRowSpec;
  items: GalleryItem[];
  totalCount: number;
}) {
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [items.length]);

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages);
  const startIdx = (clampedPage - 1) * PAGE_SIZE;
  const endIdx = Math.min(items.length, startIdx + PAGE_SIZE);
  const pageItems = items.slice(startIdx, endIdx);
  const multi = row.sprites.length > 1;

  return (
    <article id={row.id} className={`sl-row sl-row-${row.kind}`}>
      <div className={`sl-row-sprite${multi ? " sl-row-sprite-multi" : ""}`}>
        {row.sprites.map((s) => (
          <figure key={s.src} className="sl-sprite-tile">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="pixel" src={s.src} alt={`${row.label} sprite`} />
            {s.caption && <figcaption>{s.caption}</figcaption>}
          </figure>
        ))}
      </div>
      <div className="sl-row-meta">
        <div className="sl-row-head">
          <code className="sl-form-name">{row.label}</code>
          <span className="sl-form-count">{row.count}</span>
        </div>
        <p className="sl-form-desc">{row.desc}</p>
        {row.subModes && (
          <ul className="sl-submodes">
            {row.subModes.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        <div className="sl-form-anchor">
          <code>#{row.id}</code> · <b>{items.length.toLocaleString()}</b> species{items.length !== totalCount && ` (of ${totalCount.toLocaleString()})`}
        </div>
      </div>
      <div className="sl-row-photos">
        {items.length === 0 && !row.photoNote && (
          <div className="sl-no-photos">no species match current filters</div>
        )}
        {row.photoNote && (
          <div className="sl-photo-note">{row.photoNote}</div>
        )}
        {pageItems.map((it) => (
          <figure key={it.slug} id={`g-${it.slug}`} className="sl-pair">
            <div className="sl-pair-imgs">
              {it.photoUrl ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  className="sl-pair-photo"
                  src={it.photoUrl}
                  alt={it.slug}
                  loading="lazy"
                />
              ) : (
                <div className="sl-pair-photo sl-pair-nophoto">–</div>
              )}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="sl-pair-sprite pixel"
                src={it.spriteUrl}
                alt={`${it.slug} sprite`}
                loading="lazy"
              />
            </div>
            <figcaption>{it.slug}</figcaption>
          </figure>
        ))}
      </div>
      {items.length > PAGE_SIZE && (
        <div className="sl-row-pagination">
          <button
            type="button"
            className="sl-pgbtn"
            onClick={() => setPage(Math.max(1, clampedPage - 1))}
            disabled={clampedPage === 1}
          >
            ← prev
          </button>
          <span className="sl-pgstate">
            {startIdx + 1}–{endIdx} of {items.length.toLocaleString()}
          </span>
          <button
            type="button"
            className="sl-pgbtn"
            onClick={() => setPage(Math.min(totalPages, clampedPage + 1))}
            disabled={clampedPage >= totalPages}
          >
            next →
          </button>
        </div>
      )}
    </article>
  );
}

function matchesRow(item: GalleryItem, m: FormMatcher): boolean {
  if (item.form !== m.form) return false;
  if (m.aspectLt !== undefined) {
    if (item.aspect === null) return false;
    if (!(item.aspect < m.aspectLt)) return false;
  }
  if (m.aspectGte !== undefined) {
    if (item.aspect === null) return false;
    if (!(item.aspect >= m.aspectGte)) return false;
  }
  return true;
}
