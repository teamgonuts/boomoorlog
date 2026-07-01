/**
 * sprite-gallery.ts — server-side helper for /sprites page gallery.
 *
 * Enumerates every organism sprite on disk, figures out which form each
 * one used (from the full-backfill CSV log + the priority-backfill CSV +
 * the hand-curated SAMPLES table), and pairs each with its photo URL.
 *
 * All disk I/O runs once at build time in the sprites server component.
 */
import fs from "node:fs";
import path from "node:path";

const REPO_ROOT = path.join(process.cwd(), "..");
const SPRITE_DIR = path.join(process.cwd(), "public", "creature_sprites");
const CREATURE_PHOTOS_DIR = path.join(process.cwd(), "public", "creature_photos");
const ORGANISM_PHOTOS_DIR = path.join(REPO_ROOT, "data", "organism_photos");
const BACKFILL_CSV = path.join(REPO_ROOT, "data", "full_sprite_backfill", "backfill.csv");

export type GalleryItem = {
  slug: string;
  form: string;                       // "fish" | "bird" | "moth" | ...
  aspect: number | null;              // sub-mode key (e.g. reptile <1 → turtle, >=1 → lizard)
  spriteUrl: string;                  // /creature_sprites/<slug>.png
  photoUrl: string | null;            // /organism_photos/<slug>.jpg or /creature_photos/...
};

function photoUrlFor(slug: string): string | null {
  for (const ext of ["jpg", "jpeg", "png"] as const) {
    if (fs.existsSync(path.join(CREATURE_PHOTOS_DIR, `${slug}.${ext}`))) {
      return `/creature_photos/${slug}.${ext}`;
    }
    if (fs.existsSync(path.join(ORGANISM_PHOTOS_DIR, `${slug}.${ext}`))) {
      return `/organism_photos/${slug}.${ext}`;
    }
  }
  return null;
}

type BackfillRow = { form: string; aspect: number | null };

/** Parse the backfill.csv → { slug → {form, aspect} } map. */
function loadBackfillMap(): Map<string, BackfillRow> {
  const map = new Map<string, BackfillRow>();
  if (!fs.existsSync(BACKFILL_CSV)) return map;
  const text = fs.readFileSync(BACKFILL_CSV, "utf8");
  const lines = text.split(/\r?\n/);
  const header = lines[0].split(",");
  const slugIdx = header.indexOf("slug");
  const formIdx = header.indexOf("form");
  const aspectIdx = header.indexOf("aspect");
  if (slugIdx < 0 || formIdx < 0) return map;
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i]) continue;
    const cols = lines[i].split(",");
    const slug = cols[slugIdx]?.trim();
    const form = cols[formIdx]?.trim();
    if (!slug || !form) continue;
    const rawAspect = aspectIdx >= 0 ? cols[aspectIdx]?.trim() : "";
    const aspect = rawAspect ? Number(rawAspect) : NaN;
    map.set(slug, { form, aspect: Number.isFinite(aspect) ? aspect : null });
  }
  return map;
}

/** Enumerate every sprite PNG in /creature_sprites/ and build gallery items. */
export function loadGallery(): GalleryItem[] {
  const backfillMap = loadBackfillMap();
  if (!fs.existsSync(SPRITE_DIR)) return [];
  const files = fs.readdirSync(SPRITE_DIR).filter((f) => f.endsWith(".png"));
  const items: GalleryItem[] = files.map((f) => {
    const slug = f.replace(/\.png$/, "");
    const b = backfillMap.get(slug);
    return {
      slug,
      form: b?.form ?? "other",
      aspect: b?.aspect ?? null,
      spriteUrl: `/creature_sprites/${slug}.png`,
      photoUrl: photoUrlFor(slug),
    };
  });
  items.sort((a, b) => {
    if (a.form !== b.form) return a.form.localeCompare(b.form);
    return a.slug.localeCompare(b.slug);
  });
  return items;
}

export type FormChipInfo = {
  form: string;
  count: number;
  thumbSrc: string;   // sprite thumbnail for this form
};

/**
 * Count items per form and pick a representative sprite thumbnail for each.
 * Priority for the thumbnail:
 *   1. A hand-curated form template if one is supplied (via `templates`)
 *   2. Otherwise the first gallery item that uses this form
 */
export function galleryFormCounts(
  items: GalleryItem[],
  templates: Record<string, string> = {},
): FormChipInfo[] {
  const c = new Map<string, number>();
  const firstForForm = new Map<string, string>();
  for (const it of items) {
    c.set(it.form, (c.get(it.form) ?? 0) + 1);
    if (!firstForForm.has(it.form)) firstForForm.set(it.form, it.spriteUrl);
  }
  return Array.from(c.entries())
    .map(([form, count]) => ({
      form,
      count,
      thumbSrc: templates[form] ?? firstForForm.get(form) ?? "",
    }))
    .sort((a, b) => b.count - a.count || a.form.localeCompare(b.form));
}
