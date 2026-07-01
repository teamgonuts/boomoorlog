"""Render sample per-organism sprites for the /sprites QA page.

For each (slug, form, aspect) in SAMPLES:
  1. Load data/organism_photos/<slug>.jpg
  2. Extract the dominant hue (skipping near-white/black + near-grey pixels)
  3. Call the creature-pixel-art skill with form + hue + aspect
  4. Save to web/public/creature_sprites/<slug>.png

Not a full backfill — this generates ~35 samples so the reviewer can eyeball
form-vs-photo fit before we commit to the full render pass.

Usage:
    python3 pipeline/sample_sprite_batch.py
"""
from __future__ import annotations
import colorsys
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
# Search order: C5-backfilled first, then the older curated set.
PHOTO_DIRS = [
    REPO / "data" / "organism_photos",
    REPO / "web" / "public" / "creature_photos",
]
SPRITES_OUT = REPO / "web" / "public" / "creature_sprites"
RENDER_SCRIPT = (
    REPO / ".claude" / "skills" / "creature-pixel-art"
    / "scripts" / "render_creature_sprite.py"
)


class Sample(NamedTuple):
    slug: str
    form: str
    aspect: float = 1.0
    # Optional overrides (rarely needed once hue is auto-derived)
    hue_override: float | None = None
    sat: float = 55.0
    size: float = 1.0
    seed: int = 1
    # Per-organism styling flags — expose the render script's rarely-used
    # CLI toggles so a per-species Sample can request e.g. a bushy tail
    # (fox) or a head stripe (badger).
    tail: str = "thin"          # "none" | "thin" | "bushy"
    head_stripe: bool = False


# Curated samples covering every row on the /sprites page, so no "dash" gaps.
# Order = /sprites row order.
SAMPLES: list[Sample] = [
    # --- reptile: turtle mode ---
    Sample("trachemys-scripta-scripta", "reptile", aspect=0.85, sat=50),
    Sample("trachemys-scripta",         "reptile", aspect=0.85, sat=50),
    Sample("pseudemys-concinna",        "reptile", aspect=0.85, sat=50),
    # --- fish ---
    Sample("cyprinus-carpio",              "fish", aspect=1.2, sat=45),
    Sample("scardinius-erythrophthalmus",  "fish", aspect=1.2, sat=50),
    Sample("leucaspius-delineatus",        "fish", aspect=1.2, sat=35),
    Sample("cypriniformes",                "fish", aspect=1.2, sat=45),
    # --- amphibian (aspect controls fat toad vs. medium frog vs. slim newt) ---
    Sample("bufo-bufo",             "amphibian", aspect=0.75, sat=45),  # toad — fat
    Sample("rana-temporaria",       "amphibian", aspect=1.0, sat=50),   # frog — medium
    Sample("pelophylax",            "amphibian", aspect=0.95, sat=55),
    Sample("pelophylax-esculentus", "amphibian", aspect=0.9, sat=55),
    Sample("lissotriton-vulgaris",  "amphibian", aspect=1.25, sat=45),  # newt — slim + tail
    # --- large-mammal — 3 sub-modes via aspect ---
    # aspect >= 1.15 → TALL (deer, boar). Boar gets bigger size for thicker body.
    Sample("capreolus-capreolus", "large-mammal", aspect=1.25, sat=45),  # roe deer, tall
    Sample("sus-scrofa",          "large-mammal", aspect=1.30, size=1.15, sat=25),  # boar, thicker
    # aspect ~1.0 → MID (fox) — smaller legs + bushy tail
    Sample("vulpes-vulpes",       "large-mammal", aspect=0.95, sat=55, tail="bushy"),
    # aspect <= 0.75 → LOW/COMPACT (badger) — short legs, thick, head stripe
    Sample("meles-meles",         "large-mammal", aspect=0.55, sat=8, tail="none", head_stripe=True),
    # --- aquatic-mammal ---
    Sample("lutra-lutra",         "aquatic-mammal", sat=40),
    Sample("ondatra-zibethicus",  "aquatic-mammal", sat=35),
    Sample("myocastor-coypus",    "aquatic-mammal", sat=35),
    # --- water-bird (duck / coot / grebe) ---
    Sample("anas-platyrhynchos",  "water-bird", sat=40),
    Sample("fulica-atra",         "water-bird", sat=15),
    Sample("podiceps-cristatus",  "water-bird", sat=30),
    Sample("gallinula-chloropus", "water-bird", sat=30),
    Sample("branta-canadensis",   "water-bird", sat=25),
    Sample("alopochen-aegyptiaca","water-bird", sat=40),
    Sample("aythya-ferina",       "water-bird", sat=35),
    # --- wading-bird (heron / stork / spoonbill / lapwing) ---
    Sample("ardea-cinerea",      "wading-bird", sat=15),  # grey heron
    Sample("ciconia-ciconia",    "wading-bird", sat=5),   # white stork
    Sample("platalea-leucorodia","wading-bird", sat=5),   # spoonbill
    Sample("vanellus-vanellus",  "wading-bird", sat=35),  # lapwing
    # --- raptor ---
    Sample("buteo-buteo",         "raptor", sat=45),  # common buzzard
    Sample("accipiter-nisus",     "raptor", sat=40),  # sparrowhawk
    Sample("circus-aeruginosus",  "raptor", sat=35),  # marsh harrier
    Sample("falco-tinnunculus",   "raptor", sat=55),  # kestrel
    Sample("asio-otus",           "raptor", sat=35),  # long-eared owl
    # --- gull ---
    Sample("larus-fuscus",           "gull", sat=15),
    Sample("larus-argentatus",       "gull", sat=15),
    Sample("chroicocephalus-ridibundus","gull", sat=15),
    Sample("sterna-hirundo",         "gull", sat=15),
    # --- mollusc: snail ---
    Sample("cornu-aspersum",   "mollusc", aspect=0.9, sat=55),
    Sample("cepaea-nemoralis", "mollusc", aspect=0.9, sat=60),
    Sample("helix-pomatia",    "mollusc", aspect=0.9, sat=50),
    # --- mollusc: slug ---
    Sample("arion-rufus-vulgaris", "mollusc", aspect=1.2, sat=60),
    Sample("limax-maximus",        "mollusc", aspect=1.2, sat=40),
    # --- mushroom ---
    Sample("agaricus-bitorquis",  "mushroom", sat=35),
    Sample("coprinus-comatus",    "mushroom", sat=25),
    Sample("agrocybe-praecox",    "mushroom", sat=45),
    # --- lagomorph ---
    Sample("oryctolagus-cuniculus", "lagomorph", sat=35),
    Sample("lepus",                 "lagomorph", sat=35),
    # --- grasshopper ---
    Sample("tettigonia-viridissima",   "grasshopper", sat=55),
    Sample("chorthippus-brunneus",     "grasshopper", sat=40),
    Sample("leptophyes-punctatissima", "grasshopper", sat=55),
    # --- rodent ---
    Sample("muscardinus-avellanarius", "rodent", sat=45),
    Sample("clethrionomys-glareolus",  "rodent", sat=45),
    # --- dragonfly ---
    Sample("orthetrum-cancellatum", "dragonfly", sat=55),
    Sample("ischnura-elegans",      "dragonfly", sat=60),
    Sample("coenagrion-puella",     "dragonfly", sat=60),
    # --- spider (top-observed) ---
    Sample("araneus-diadematus",   "spider", sat=45),
    Sample("salticus-scenicus",    "spider", sat=35),
    Sample("marpissa-muscosa",     "spider", sat=45),
    Sample("opilio-canestrinii",   "spider", sat=45),
    # --- fungus / lichen ---
    Sample("xanthoria-parietina",    "fungus", aspect=0.85, sat=60),
    Sample("physcia-adscendens",     "fungus", aspect=0.85, sat=25),
    Sample("flavoparmelia-soredians","fungus", aspect=0.85, sat=45),
    # --- existing forms — refresh sample renders for the QA page ---
    Sample("apis-mellifera",       "bee", sat=55),
    Sample("cyanistes-caeruleus",  "bird", sat=55),
]


def dominant_hue(img_path: Path) -> float:
    """Return the dominant hue (0–360) of the photo. Skips near-white,
    near-black, and near-grey pixels so vegetation/background doesn't
    drown out the subject.
    """
    im = Image.open(img_path).convert("RGB")
    # Downscale for speed
    im.thumbnail((160, 160))
    # Quantize to a modest palette
    pal = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT).convert("RGB")

    counts: Counter[tuple[int, int, int]] = Counter()
    w, h = pal.size
    px = pal.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # skip near-white
            if r > 235 and g > 235 and b > 235:
                continue
            # skip near-black
            if r < 20 and g < 20 and b < 20:
                continue
            # skip near-grey (low chroma) — HSL saturation < ~0.18
            mx, mn = max(r, g, b), min(r, g, b)
            if mx == 0:
                continue
            chroma = (mx - mn) / mx
            if chroma < 0.18:
                continue
            counts[(r, g, b)] += 1
    if not counts:
        # fall back to overall dominant
        (r, g, b), _ = pal.getcolors()[0][1], pal.getcolors()[0][0]
    else:
        (r, g, b), _ = counts.most_common(1)[0]
    h_val, _, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h_val * 360


def find_photo(slug: str) -> Path | None:
    for d in PHOTO_DIRS:
        for ext in ("jpg", "jpeg", "png"):
            p = d / f"{slug}.{ext}"
            if p.exists():
                return p
    return None


def render(sample: Sample) -> tuple[bool, str]:
    photo = find_photo(sample.slug)
    if photo is None:
        return False, f"photo missing for {sample.slug}"
    hue = sample.hue_override if sample.hue_override is not None else dominant_hue(photo)
    out = SPRITES_OUT / f"{sample.slug}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3", str(RENDER_SCRIPT),
        "--form", sample.form,
        "--hue", f"{hue:.1f}",
        "--sat", f"{sample.sat:.0f}",
        "--size", f"{sample.size:.2f}",
        "--aspect", f"{sample.aspect:.2f}",
        "--seed", str(sample.seed),
        "--tail", sample.tail,
        "--out", str(out),
    ]
    if sample.head_stripe:
        cmd.append("--head-stripe")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"render failed for {sample.slug}: {r.stderr.strip()[:200]}"
    return True, f"{sample.slug:38s} form={sample.form:11s} hue={hue:5.1f} aspect={sample.aspect}"


def main() -> None:
    ok = 0
    fail = 0
    for s in SAMPLES:
        good, msg = render(s)
        print(("[ok]  " if good else "[FAIL]") + " " + msg)
        if good:
            ok += 1
        else:
            fail += 1
    print(f"\nDone: {ok}/{len(SAMPLES)} rendered  ({fail} failed)")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
