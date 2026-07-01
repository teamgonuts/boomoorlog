// Shared POC data — same sprite set + same deterministic positions on both maps,
// so what you're comparing is the map engine, not the inputs.

export const AMS_CENTER: [number, number] = [52.3676, 4.9041]; // [lat, lng]
export const AMS_ZOOM = 14;
export const DEFAULT_SPRITE_COUNT = 1000;

// Box around Amsterdam center to scatter sprites in (roughly ~4km wide).
const HALF_LAT = 0.02;
const HALF_LNG = 0.03;

// Random-but-consistent sprite set from /public/creature_sprites/.
export const SPRITE_FILES = [
  "alopochen-aegyptiaca.png",
  "adalia-bipunctata.png",
  "pieris-brassicae.png",
  "nymphalis-antiopa.png",
  "sitta-europaea-dendrocopos-major.png",
  "harmonia-axyridis.png",
  "phylloscopus-collybita.png",
  "turdus-iliacus-pilaris.png",
];

// mulberry32 PRNG — deterministic so both maps get the exact same layout.
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type Sprite = {
  lat: number;
  lng: number;
  file: string; // filename in /creature_sprites/
};

export function generateSprites(n: number, seed = 1): Sprite[] {
  const rand = mulberry32(seed);
  const out: Sprite[] = new Array(n);
  for (let i = 0; i < n; i++) {
    out[i] = {
      lat: AMS_CENTER[0] + (rand() * 2 - 1) * HALF_LAT,
      lng: AMS_CENTER[1] + (rand() * 2 - 1) * HALF_LNG,
      file: SPRITE_FILES[Math.floor(rand() * SPRITE_FILES.length)],
    };
  }
  return out;
}
