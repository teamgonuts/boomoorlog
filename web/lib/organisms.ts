/**
 * Helpers for the unified `organisms` table (Creatures AMS C1 milestone).
 *
 * Today the web app reads from `genera` and `creatures` directly. This module
 * is the migration target: page-by-page refactors will replace `.from('genera')`
 * and `.from('creatures')` calls with the helpers below, all of which read
 * from `organisms`.
 *
 * Both old tables continue to exist alongside `organisms` during the
 * transition — see db/MIGRATING_TO_ORGANISMS.md.
 */
import type { Organism, OrganismCategory } from "@/types/supabase";

/**
 * Resolve a row's display photo to a public URL the browser can fetch.
 * Mirrors web/lib/creature.ts#creaturePhotoUrl but handles every photo_path
 * shape we have in the wild:
 *
 *   - "data/creature_pics/foo.jpg"        → "/creature_photos/foo.jpg"   (legacy curated creatures)
 *   - "data/organism_photos/<slug>.jpg"   → "/organism_photos/<slug>.jpg" (C3 downloads)
 *   - "web/public/creature_sprites/x.png" → "/creature_sprites/x.png"    (legacy populate)
 *   - "https://…"                         → unchanged
 *   - null                                → null
 */
export function organismPhotoUrl(photo_path: string | null): string | null {
  if (!photo_path) return null;
  if (/^https?:\/\//.test(photo_path)) return photo_path;
  return photo_path
    .replace(/^data\/creature_pics\//, "/creature_photos/")
    .replace(/^data\/organism_photos\//, "/organism_photos/")
    .replace(/^web\/public\//, "/");
}

/**
 * Sprite URL is deterministic from slug + category. Trees live under
 * /sprites/, creatures under /creature_sprites/. Returns null when sprite
 * hasn't been generated yet (sprite_pending) — callers filter on this.
 */
export function organismSpriteUrl(org: Pick<Organism, "slug" | "category" | "sprite_pending">): string | null {
  if (org.sprite_pending) return null;
  if (org.category === "tree") return `/sprites/${org.slug}.png`;
  return `/creature_sprites/${org.slug}.png`;
}

/** Dominant habitat / movement tag (index 0 of the multi-valued array). */
export function dominantHabitat(org: Pick<Organism, "habitat_classes">): string | null {
  return org.habitat_classes[0] ?? null;
}

export function dominantMovement(org: Pick<Organism, "movement_classes">): string | null {
  return org.movement_classes[0] ?? null;
}

/** True when the organism is renderable on the map (sprite available). */
export function hasSprite(org: Pick<Organism, "sprite_path" | "sprite_pending">): boolean {
  return !org.sprite_pending && org.sprite_path !== null;
}

/** Group label for the wiki / panel UIs. Single source of truth. */
export const CATEGORY_LABEL: Record<OrganismCategory, string> = {
  tree: "Tree",
  bird: "Bird",
  mammal: "Mammal",
  insect: "Insect",
  arachnid: "Arachnid",
  mollusc: "Mollusc",
  amphibian: "Amphibian",
  reptile: "Reptile",
  fish: "Fish",
  fungus: "Fungus",
  lichen: "Lichen",
  plant: "Plant",
  other: "Other",
};

export function categoryLabel(c: OrganismCategory): string {
  return CATEGORY_LABEL[c] ?? c;
}
