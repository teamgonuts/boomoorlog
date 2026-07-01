"""Full per-organism sprite backfill.

For every slug that has a photo on disk but no sprite in
`web/public/creature_sprites/`, do:
  1. Look up taxonomy from the CSVs → decide which sprite form to use
     (via the same bucket() classifier we've been iterating on for the
     priority backfill).
  2. Extract dominant hue from the photo (PIL, ignoring near-white /
     near-black / near-grey backgrounds so foliage doesn't dominate).
  3. Call the creature-pixel-art render script → save PNG to
     `web/public/creature_sprites/<slug>.png`.

No LLM calls, no network — pure local Python. Runs in ~5 min for
~1,600 organisms on this laptop.

Usage:
    python3 pipeline/full_sprite_backfill.py [--dry-run] [--limit N]
"""
from __future__ import annotations
import argparse
import colorsys
import csv
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
PHOTO_DIRS = [
    REPO / "data" / "organism_photos",
    REPO / "web" / "public" / "creature_photos",
]
SPRITE_DIR = REPO / "web" / "public" / "creature_sprites"
RENDER_SCRIPT = (
    REPO / ".claude" / "skills" / "creature-pixel-art"
    / "scripts" / "render_creature_sprite.py"
)
TAX_FILES = [
    REPO / "data" / "organisms_taxonomy.csv",
    REPO / "data" / "c3a_taxonomy.csv",
    REPO / "data" / "c3c_taxonomy_trees.csv",
]
LOG_DIR = REPO / "data" / "full_sprite_backfill"


def load_taxonomy() -> dict[str, dict]:
    tax: dict[str, dict] = {}
    for path in TAX_FILES:
        if not path.exists():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                slug = (row.get("slug") or "").strip()
                if not slug or slug in tax:
                    continue
                tax[slug] = {
                    "latin":   (row.get("latin_name") or "").strip(),
                    "kingdom": (row.get("kingdom") or "").strip().lower(),
                    "phylum":  (row.get("phylum") or "").strip().lower(),
                    "class":   (row.get("class_name") or "").strip().lower(),
                    "order":   (row.get("order_name") or "").strip().lower(),
                    "family":  (row.get("family") or "").strip().lower(),
                    "genus":   (row.get("genus") or "").strip().lower(),
                }
    return tax


def find_photo(slug: str) -> Path | None:
    for d in PHOTO_DIRS:
        for ext in ("jpg", "jpeg", "png"):
            p = d / f"{slug}.{ext}"
            if p.exists():
                return p
    return None


# --------------------------------------------------------------------------- #
# Form assignment
#
# Assigns (form, aspect, sat, tail, head_stripe) tuple from taxonomy.
# Coverage priority mirrors the /sprites row order the user has been curating.
# Returns None if we don't have a form for this taxon yet — those get
# skipped and reported so we know what still needs a form.
# --------------------------------------------------------------------------- #
def assign_form(t: dict) -> tuple[str, dict] | None:
    """Return (form_name, {aspect, sat, tail, head_stripe}) or None if we
    have no matching form for this taxon.
    """
    o = t.get("order", "")
    c = t.get("class", "")
    fam = t.get("family", "")
    g = t.get("genus", "")
    ph = t.get("phylum", "")
    kd = t.get("kingdom", "")

    # Reptiles / amphibians / fish
    if c == "testudines" or o == "testudines":
        return "reptile", {"aspect": 0.85, "sat": 50}
    if o == "squamata" or c == "reptilia":
        return "reptile", {"aspect": 1.30, "sat": 45}  # lizard mode
    if c == "amphibia" or o in ("anura", "caudata", "urodela"):
        aspect = 0.75 if fam in ("bufonidae",) else (
            1.25 if o in ("caudata", "urodela") or fam in ("salamandridae",) else 0.95
        )
        return "amphibian", {"aspect": aspect, "sat": 50}
    if c == "actinopterygii" or o in (
        "cypriniformes", "perciformes", "esociformes", "anguilliformes",
        "salmoniformes", "siluriformes", "cyprinodontiformes",
        "gasterosteiformes",
    ):
        return "fish", {"aspect": 1.2, "sat": 45}

    # Molluscs
    if c == "gastropoda" or o in ("stylommatophora", "systellommatophora", "pulmonata"):
        # slug families vs. snail families
        slug_families = {"arionidae", "limacidae", "milacidae", "agriolimacidae"}
        aspect = 1.2 if fam in slug_families else 0.9
        return "mollusc", {"aspect": aspect, "sat": 55}

    # Mammals — split by order + family for the sub-modes we built
    if o == "lagomorpha":
        return "lagomorph", {"aspect": 1.0, "sat": 35}
    if o == "rodentia":
        # Squirrels get the mammal (bushy-tail) form; other rodents get rodent
        if fam == "sciuridae":
            return "mammal", {"aspect": 1.0, "sat": 45}
        return "rodent", {"aspect": 1.0, "sat": 40}
    if o == "chiroptera":
        return "bat", {"aspect": 1.0, "sat": 30}
    if o in ("eulipotyphla", "erinaceomorpha", "soricomorpha"):
        return "mammal", {"aspect": 1.0, "sat": 30}
    if o == "carnivora":
        # Foxes/canids: mid mode + bushy tail
        if fam == "canidae":
            return "large-mammal", {
                "aspect": 0.95, "sat": 55, "tail": "bushy",
            }
        # Mustelids (badger/marten/weasel/mink/otter): low mode
        if fam == "mustelidae":
            # Lutra (otter) → aquatic-mammal (has waterline behaviour)
            if g == "lutra":
                return "aquatic-mammal", {"aspect": 1.0, "sat": 30}
            head_stripe = (g == "meles")
            return "large-mammal", {
                "aspect": 0.55, "sat": 15, "tail": "none",
                "head_stripe": head_stripe,
            }
        # Cats & anything else carnivora: mid mode default
        return "large-mammal", {"aspect": 0.95, "sat": 40, "tail": "thin"}
    if o == "artiodactyla" or o == "cetartiodactyla":
        return "large-mammal", {"aspect": 1.25, "sat": 30}
    if o == "perissodactyla":
        return "large-mammal", {"aspect": 1.30, "sat": 25}
    # Aquatic mammals fallback: castor, ondatra, myocastor, arvicola
    if g in ("castor", "ondatra", "myocastor", "arvicola", "neogale"):
        return "aquatic-mammal", {"aspect": 1.0, "sat": 30}

    # Birds — split by order
    if c == "aves":
        if o == "anseriformes":  # ducks, geese, swans
            return "water-bird", {"aspect": 1.0, "sat": 30}
        if o == "podicipediformes":  # grebes
            return "water-bird", {"aspect": 1.0, "sat": 30}
        if o == "gruiformes":  # coots, rails
            return "water-bird", {"aspect": 1.0, "sat": 20}
        if o == "pelecaniformes" or o == "ciconiiformes":  # herons, storks
            return "wading-bird", {"aspect": 1.0, "sat": 15}
        if o == "suliformes":  # cormorants
            return "wading-bird", {"aspect": 1.0, "sat": 10}
        if o == "charadriiformes":  # gulls, waders, terns, lapwings
            gull_fams = {"laridae", "sternidae", "stercorariidae"}
            wader_fams = {"charadriidae", "scolopacidae", "recurvirostridae"}
            if fam in gull_fams:
                return "gull", {"aspect": 1.0, "sat": 12}
            if fam in wader_fams:
                return "wading-bird", {"aspect": 1.0, "sat": 30}
            return "gull", {"aspect": 1.0, "sat": 15}  # default seabird
        if o in ("accipitriformes", "falconiformes"):
            return "raptor", {"aspect": 1.0, "sat": 40}
        if o == "strigiformes":  # owls
            return "raptor", {"aspect": 1.0, "sat": 30}
        # Default all other orders (passerines, doves, kingfishers, etc.) → bird
        return "bird", {"aspect": 1.0, "sat": 55}

    # Insects — deprioritized per user, but assign forms so we cover the
    # long tail with something rather than skip entirely
    if c == "insecta":
        if o == "odonata":
            return "dragonfly", {"aspect": 1.0, "sat": 55}
        if o == "orthoptera":
            return "grasshopper", {"aspect": 1.0, "sat": 50}
        if o == "coleoptera":
            return "beetle", {"aspect": 1.0, "sat": 55}
        if o == "lepidoptera":
            # Adults use moth form (butterfly/moth similar top-down); larvae
            # would use caterpillar but we can't tell from taxonomy alone.
            return "moth", {"aspect": 1.0, "sat": 55}
        if o == "hymenoptera" or o == "diptera":
            return "bee", {"aspect": 1.0, "sat": 55}
        if o == "hemiptera":
            return "bug", {"aspect": 1.0, "sat": 45}
        return "bug", {"aspect": 1.0, "sat": 40}

    # Arachnids (spiders, mites, harvestmen)
    if c == "arachnida" or o == "araneae":
        return "spider", {"aspect": 1.0, "sat": 35}

    # Fungi + lichens
    if kd == "fungi" or c == "lichenes":
        # Mushroom-forming orders (cap on stipe)
        if o in ("agaricales", "boletales", "russulales", "pluteales",
                 "tremellales", "geastrales"):
            return "mushroom", {"aspect": 1.0, "sat": 35}
        # Everything else fungal → fungus form (right-side-up lobed patch)
        # Aspect < 1 = lichen/crust; >= 1 = bracket cluster.
        aspect = 0.85 if o in ("lecanorales", "peltigerales", "arthoniales",
                                "teloschistales", "baeomycetales", "ostropales",
                                "pertusariales", "umbilicariales") else 1.0
        return "fungus", {"aspect": aspect, "sat": 35}

    # Plants — deprioritized per user, don't render for now
    if kd == "plantae":
        return None

    return None


# --------------------------------------------------------------------------- #
# Hue extraction
# --------------------------------------------------------------------------- #
def dominant_hue(img_path: Path) -> float:
    im = Image.open(img_path).convert("RGB")
    im.thumbnail((160, 160))
    pal = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT).convert("RGB")
    counts: Counter[tuple[int, int, int]] = Counter()
    w, h = pal.size
    px = pal.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 235 and g > 235 and b > 235:
                continue
            if r < 20 and g < 20 and b < 20:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx == 0:
                continue
            chroma = (mx - mn) / mx
            if chroma < 0.18:
                continue
            counts[(r, g, b)] += 1
    if not counts:
        # Fall back to whatever the palette said
        colors = pal.getcolors() or [(1, (128, 128, 128))]
        _, (r, g, b) = max(colors, key=lambda c: c[0])
    else:
        (r, g, b), _ = counts.most_common(1)[0]
    h_val, _, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h_val * 360


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't actually render")
    ap.add_argument("--limit", type=int, default=0, help="stop after N")
    ap.add_argument("--force", action="store_true",
                    help="re-render even if sprite already exists")
    args = ap.parse_args()

    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    tax = load_taxonomy()

    # Enumerate every slug with a photo
    photo_slugs: set[str] = set()
    for d in PHOTO_DIRS:
        for f in os.listdir(d):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                photo_slugs.add(os.path.splitext(f)[0])

    already_have = {os.path.splitext(f)[0] for f in os.listdir(SPRITE_DIR)
                    if f.lower().endswith(".png")}
    todo = sorted(photo_slugs if args.force else (photo_slugs - already_have))
    if args.limit:
        todo = todo[: args.limit]

    print(f"Photos on disk:  {len(photo_slugs)}")
    print(f"Sprites on disk: {len(already_have)}")
    print(f"To render:       {len(todo)}")
    print(f"Dry run:         {args.dry_run}\n")

    ok = 0
    no_form: dict[str, int] = defaultdict(int)   # bucket → count of skips
    no_tax = 0
    fail: list[tuple[str, str]] = []

    csv_out = LOG_DIR / "backfill.csv"
    csv_f = csv_out.open("w", newline="")
    csv_w = csv.writer(csv_f)
    csv_w.writerow(["slug", "form", "hue", "aspect", "sat", "tail",
                    "head_stripe", "status", "note"])

    t_start = time.time()
    for i, slug in enumerate(todo, 1):
        t = tax.get(slug)
        if t is None:
            no_tax += 1
            csv_w.writerow([slug, "", "", "", "", "", "", "no_taxonomy", ""])
            continue
        assigned = assign_form(t)
        if assigned is None:
            key = (t.get("kingdom") or "-") + "/" + (t.get("class") or "-") + "/" + (t.get("order") or "-")
            no_form[key] += 1
            csv_w.writerow([slug, "", "", "", "", "", "", "no_form", key])
            continue
        form, cfg = assigned

        photo = find_photo(slug)
        if photo is None:
            fail.append((slug, "photo file vanished"))
            csv_w.writerow([slug, form, "", "", "", "", "", "fail", "photo missing"])
            continue

        try:
            hue = dominant_hue(photo)
        except Exception as e:
            fail.append((slug, f"hue extraction: {e}"))
            csv_w.writerow([slug, form, "", "", "", "", "", "fail", f"hue: {e}"])
            continue

        aspect = cfg.get("aspect", 1.0)
        sat = cfg.get("sat", 55)
        tail = cfg.get("tail", "thin")
        head_stripe = cfg.get("head_stripe", False)

        if args.dry_run:
            csv_w.writerow([slug, form, f"{hue:.1f}", f"{aspect:.2f}",
                            f"{sat:.0f}", tail, head_stripe, "dry_run", ""])
            ok += 1
            continue

        out = SPRITE_DIR / f"{slug}.png"
        cmd = [
            "python3", str(RENDER_SCRIPT),
            "--form", form,
            "--hue", f"{hue:.1f}",
            "--sat", f"{sat:.0f}",
            "--size", "1.0",
            "--aspect", f"{aspect:.2f}",
            "--seed", "1",
            "--tail", tail,
            "--out", str(out),
        ]
        if head_stripe:
            cmd.append("--head-stripe")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail.append((slug, r.stderr.strip()[:120]))
            csv_w.writerow([slug, form, f"{hue:.1f}", f"{aspect:.2f}",
                            f"{sat:.0f}", tail, head_stripe, "fail",
                            r.stderr.strip()[:120]])
            continue
        csv_w.writerow([slug, form, f"{hue:.1f}", f"{aspect:.2f}",
                        f"{sat:.0f}", tail, head_stripe, "ok", ""])
        ok += 1
        if i % 100 == 0:
            elapsed = time.time() - t_start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(todo) - i) / rate if rate > 0 else 0
            print(f"  [{i}/{len(todo)}] ok={ok} no_form={sum(no_form.values())} "
                  f"no_tax={no_tax} fail={len(fail)} "
                  f"({rate:.1f}/sec, eta {eta/60:.1f} min)")

    csv_f.close()
    total_time = time.time() - t_start
    print(f"\n=== Done in {total_time/60:.1f} min ===")
    print(f"  ok:       {ok}")
    print(f"  no_form:  {sum(no_form.values())}  (no rule for these taxons)")
    print(f"  no_tax:   {no_tax}  (slug not in taxonomy CSVs)")
    print(f"  fail:     {len(fail)}")

    if no_form:
        print("\nTop no_form buckets (kingdom/class/order → count):")
        for k, v in sorted(no_form.items(), key=lambda x: -x[1])[:15]:
            print(f"  {v:5d}  {k}")

    if fail:
        print("\nFirst 10 failures:")
        for slug, msg in fail[:10]:
            print(f"  {slug}: {msg}")

    print(f"\nDetailed log: {csv_out}")


if __name__ == "__main__":
    main()
