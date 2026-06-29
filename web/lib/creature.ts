/**
 * Small helpers for the creature wiki.
 *
 * organisms.photo_path stores the same path the legacy creatures.pic_file
 * column did ("data/creature_pics/foo.jpg"); web assets live under
 * web/public/ as /creature_photos/foo.jpg and /creature_sprites/foo.png.
 * These helpers translate between the two and provide friendly form labels.
 */
import type { Organism } from "@/types/supabase";

/** Translate organisms.photo_path ("data/creature_pics/foo.jpg") to web URL.
 *  Returns null if the row has no photo (truly photoless organism). */
export function creaturePhotoUrl(photo_path: string | null): string | null {
  if (!photo_path) return null;
  return photo_path.replace(/^data\/creature_pics\//, "/creature_photos/");
}

/** Sprite URL is deterministic from slug — always PNG in /creature_sprites/. */
export function creatureSpriteUrl(slug: string): string {
  return `/creature_sprites/${slug}.png`;
}

/** Form display labels for the 10 body plans the pixel-art skill supports.
 *  Unknown / null forms show as "—". */
export const FORM_LABEL: Record<string, string> = {
  bug: "Bug",
  beetle: "Beetle",
  caterpillar: "Caterpillar",
  moth: "Moth",
  bee: "Bee",
  spider: "Spider",
  bird: "Bird",
  mammal: "Mammal",
  bat: "Bat",
  fungus: "Fungus / Lichen",
};

export function formLabel(form: string | null): string {
  if (!form) return "—";
  return FORM_LABEL[form] ?? form;
}

/** Quick sortable shape used by the landing grid.
 *  Organism.common_name is nullable in the DB; CreatureCard normalises
 *  it to a non-null string (falling back to latin_name) so the UI never
 *  has to think about it. */
export type CreatureCard = Omit<Organism, "common_name"> & {
  common_name: string;
  photoUrl: string | null;
  spriteUrl: string;
  formLabel: string;
};

export function toCard(o: Organism): CreatureCard {
  return {
    ...o,
    common_name: o.common_name ?? o.latin_name,
    photoUrl: creaturePhotoUrl(o.photo_path),
    spriteUrl: creatureSpriteUrl(o.slug),
    formLabel: formLabel(o.form),
  };
}
