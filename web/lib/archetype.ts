/**
 * Archetype classification: split the 55 stat-blocked genera into four
 * tower-defense roles based on their stats. Derived live from the DB so
 * formula changes only require updating this file (no re-seed).
 *
 * Power axis    = (attack + range + health) / 3      // hard-hitting / tanky
 * Agility axis  = (attack_speed + move_speed) / 2    // mobile / fast strikes
 *
 * The 4-way split uses the medians of each axis across all stat-blocked
 * genera. Genera with `world_rarity_multiplier >= 1.25` get marked Legendary.
 *
 * Mirrors the assignment logic in pipeline/stats.py — keep in sync.
 */

import type { Genus } from "@/types/supabase";

export type ArchetypeBase =
  | "Bruiser"
  | "Juggernaut"
  | "Skirmisher"
  | "Support";

export type Classified = Genus & {
  archetype: ArchetypeBase;
  isLegendary: boolean;
  powerAxis: number;
  agilityAxis: number;
  powerScore: number; // mean of the 5 stats × world-rarity multiplier, 1-10
  rarity: RarityTier;
};

export type RarityTier = "common" | "notable" | "rare";

export function rarityFor(mult: number): RarityTier {
  if (mult >= 1.25) return "rare";
  if (mult > 1.0) return "notable";
  return "common";
}

export const RARITY_LABEL: Record<RarityTier, string> = {
  common: "Common",
  notable: "Uncommon",
  rare: "Legendary",
};

export const ARCHETYPE_ORDER: ArchetypeBase[] = [
  "Bruiser",
  "Juggernaut",
  "Skirmisher",
  "Support",
];

export const ARCHETYPE_BLURBS: Record<ArchetypeBase, string> = {
  Bruiser:
    "High power AND high agility: strong, durable, and quick. The carnage units.",
  Juggernaut:
    "High power, low agility: hard-hitting, tanky, long-range, but slow to move and strike. Walls and artillery.",
  Skirmisher:
    "Low power, high agility: fast strikes and movement, fragile and short-range. Swarmers.",
  Support:
    "Low power and low agility: weak filler that wins by sheer numbers in tree-dense ZIP codes.",
};

function median(xs: number[]): number {
  const sorted = [...xs].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

export function classifyGenera(genera: Genus[]): Classified[] {
  const usable = genera.filter(
    (g) =>
      g.attack != null &&
      g.range != null &&
      g.health != null &&
      g.attack_speed != null &&
      g.move_speed != null,
  );

  const withAxes = usable.map((g) => ({
    ...g,
    powerAxis: ((g.attack! + g.range! + g.health!) / 3),
    agilityAxis: ((g.attack_speed! + g.move_speed!) / 2),
  }));

  const pMed = median(withAxes.map((g) => g.powerAxis));
  const aMed = median(withAxes.map((g) => g.agilityAxis));

  return withAxes.map((g) => {
    let archetype: ArchetypeBase;
    if (g.powerAxis >= pMed && g.agilityAxis < aMed) archetype = "Juggernaut";
    else if (g.powerAxis >= pMed && g.agilityAxis >= aMed) archetype = "Bruiser";
    else if (g.powerAxis < pMed && g.agilityAxis >= aMed) archetype = "Skirmisher";
    else archetype = "Support";

    const mult = Number(g.world_rarity_multiplier);
    const meanStat =
      (g.attack! + g.range! + g.health! + g.attack_speed! + g.move_speed!) / 5;
    const powerScore = Math.round(meanStat * mult * 10) / 10;
    return {
      ...g,
      archetype,
      isLegendary: mult >= 1.25,
      powerScore,
      rarity: rarityFor(mult),
    };
  });
}
