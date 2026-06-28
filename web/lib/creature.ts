/**
 * Small helpers for the creature wiki.
 *
 * The creatures table stores pic_file as a SOURCE path
 * ("data/creature_pics/foo.jpg"); web assets live under web/public/ as
 * /creature_photos/foo.jpg and /creature_sprites/foo.png. These helpers
 * translate between the two and provide friendly form labels.
 */
import type { Creature } from "@/types/supabase";

/** Translate creatures.pic_file ("data/creature_pics/foo.jpg") to web URL.
 *  Returns null if the row has no pic_file (truly photoless creature). */
export function creaturePhotoUrl(pic_file: string | null): string | null {
  if (!pic_file) return null;
  return pic_file.replace(/^data\/creature_pics\//, "/creature_photos/");
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

/** Quick sortable shape used by the landing grid. */
export type CreatureCard = Creature & {
  photoUrl: string | null;
  spriteUrl: string;
  formLabel: string;
};

export function toCard(c: Creature): CreatureCard {
  return {
    ...c,
    photoUrl: creaturePhotoUrl(c.pic_file),
    spriteUrl: creatureSpriteUrl(c.slug),
    formLabel: formLabel(c.form),
  };
}
