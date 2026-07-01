/**
 * Gallery.tsx — client-side filterable grid of every per-organism sprite.
 *
 * The server component hands us the full list once at build time; here
 * we handle the interactive bits — search box + form-filter chips + grid.
 */
"use client";

import { useMemo, useState } from "react";
import type { GalleryItem } from "@/lib/sprite-gallery";

type Props = {
  items: GalleryItem[];
  formCounts: { form: string; count: number }[];
};

export function Gallery({ items, formCounts }: Props) {
  const [query, setQuery] = useState("");
  const [selectedForms, setSelectedForms] = useState<Set<string>>(new Set());
  const [onlyWithPhoto, setOnlyWithPhoto] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((it) => {
      if (selectedForms.size > 0 && !selectedForms.has(it.form)) return false;
      if (onlyWithPhoto && !it.photoUrl) return false;
      if (q && !it.slug.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [items, query, selectedForms, onlyWithPhoto]);

  const toggleForm = (form: string) => {
    setSelectedForms((prev) => {
      const next = new Set(prev);
      if (next.has(form)) next.delete(form);
      else next.add(form);
      return next;
    });
  };

  const clearFilters = () => {
    setQuery("");
    setSelectedForms(new Set());
    setOnlyWithPhoto(false);
  };

  return (
    <div className="sl-gallery">
      <div className="sl-gallery-controls">
        <input
          className="sl-gallery-search"
          type="search"
          placeholder="Search by slug… (e.g. anas, buteo, cornu)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="sl-gallery-checkbox">
          <input
            type="checkbox"
            checked={onlyWithPhoto}
            onChange={(e) => setOnlyWithPhoto(e.target.checked)}
          />
          only show organisms with a photo
        </label>
        {(query || selectedForms.size > 0 || onlyWithPhoto) && (
          <button className="sl-gallery-clear" onClick={clearFilters}>
            clear filters
          </button>
        )}
      </div>

      <div className="sl-gallery-chips">
        {formCounts.map(({ form, count }) => {
          const active = selectedForms.has(form);
          return (
            <button
              key={form}
              type="button"
              className={`sl-chip${active ? " sl-chip-active" : ""}`}
              onClick={() => toggleForm(form)}
            >
              <code>{form}</code>
              <span className="sl-chip-count">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="sl-gallery-summary">
        Showing <b>{filtered.length.toLocaleString()}</b> of{" "}
        <b>{items.length.toLocaleString()}</b> sprites
      </div>

      <div className="sl-gallery-grid">
        {filtered.map((it) => (
          <figure key={it.slug} className="sl-gcard" id={`g-${it.slug}`}>
            <div className="sl-gcard-imgs">
              {it.photoUrl ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  className="sl-gcard-photo"
                  src={it.photoUrl}
                  alt={it.slug}
                  loading="lazy"
                />
              ) : (
                <div className="sl-gcard-photo sl-gcard-nophoto" title="no photo on disk">
                  no photo
                </div>
              )}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className="sl-gcard-sprite pixel"
                src={it.spriteUrl}
                alt={`${it.slug} sprite`}
                loading="lazy"
              />
            </div>
            <figcaption>
              <span className="sl-gcard-slug">{it.slug}</span>
              <span className="sl-gcard-form">{it.form}</span>
            </figcaption>
          </figure>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="sl-gallery-empty">
          No sprites match those filters. <button onClick={clearFilters}>reset</button>
        </div>
      )}
    </div>
  );
}
