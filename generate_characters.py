#!/usr/bin/env python3
"""Derive per-genus character stat blocks for boomoorlog from the Amsterdam data.

Reads data/amsterdam_trees.csv, computes per-genus size/vigor metrics, normalizes
to a 1-10 scale, applies a world-rarity multiplier, classifies each genus into a
tower-defense archetype, and writes memory/CHARACTERS.md.

Stat mapping (see memory/STATS.md):
  SIZE axis  -> Range  = height
                Attack = trunk diameter (girth)
                Health = height x diameter (mass)
  VIGOR axis -> Attack speed = growth rate (height / age)
                Movement     = growth rate (vigor)
"""

import csv
import glob
import math
import os
import re
from collections import defaultdict

CSV = "data/amsterdam_trees.csv"
OUT = "memory/CHARACTERS.md"
CHARDIR = "memory/characters"
NOW = 2026
MIN_COUNT = 100  # genera below this are folded into the "long tail" note
RARITY_MULT = {"common": 1.00, "notable": 1.10, "rare": 1.25}

HEIGHT = {'a. tot 6 m.': 4, 'b. 6 tot 9 m.': 7.5, 'c. 9 tot 12 m.': 10.5,
          'd. 12 tot 15 m.': 13.5, 'e. 15 tot 18 m.': 16.5, 'f. 18 tot 24 m.': 21,
          'g. 24 m. en hoger': 27}
DIA = {'tot 0,1 m.': 0.05, '0,1 tot 0,2 m.': 0.15, '0,2 tot 0,3 m.': 0.25,
       '0,3 tot 0,5 m.': 0.4, '0,5 tot 1 m.': 0.75, '1,0 tot 1,5 m.': 1.25,
       '1,5 m. en groter': 1.75}

def first_num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def load_research():
    """Parse per-genus research (Stat inputs block) from memory/characters/*.md."""
    res = {}
    for path in glob.glob(f"{CHARDIR}/*.md"):
        genus = os.path.splitext(os.path.basename(path))[0]
        if genus.startswith("_"):
            continue
        with open(path) as f:
            txt = f.read()
        d = {}
        for key in ("max_height_m", "lifespan_yr", "wood_density_kgm3"):
            m = re.search(rf"{key}:\s*([^\n]+)", txt)
            d[key] = first_num(m.group(1)) if m else None
        m = re.search(r"world_rarity:\s*(\w+)", txt)
        d["world_rarity"] = m.group(1).lower() if m else "common"
        m = re.search(r"^## Personality\s*\n+([^\n]+)", txt, re.M)
        d["personality"] = m.group(1).strip() if m else ""
        res[genus] = d
    return res


# English common names for readability (fallback: genus name).
COMMON = {
    'Ulmus': 'Elm', 'Tilia': 'Linden', 'Acer': 'Maple', 'Fraxinus': 'Ash',
    'Quercus': 'Oak', 'Platanus': 'Plane', 'Salix': 'Willow', 'Alnus': 'Alder',
    'Populus': 'Poplar', 'Prunus': 'Cherry', 'Betula': 'Birch', 'Carpinus': 'Hornbeam',
    'Crataegus': 'Hawthorn', 'Robinia': 'Locust', 'Malus': 'Apple', 'Sorbus': 'Rowan',
    'Gleditsia': 'Honey locust', 'Aesculus': 'Horse chestnut', 'Pyrus': 'Pear',
    'Fagus': 'Beech', 'Liquidambar': 'Sweetgum', 'Pinus': 'Pine',
    'Pterocarya': 'Wingnut', 'Metasequoia': 'Dawn redwood', 'Ilex': 'Holly',
    'Ginkgo': 'Ginkgo', 'Magnolia': 'Magnolia', 'Taxus': 'Yew',
    'Styphnolobium': 'Pagoda tree', 'Corylus': 'Hazel', 'Amelanchier': 'Serviceberry',
    'Ailanthus': 'Tree of heaven', 'Juglans': 'Walnut', 'Liriodendron': 'Tulip tree',
    'Taxodium': 'Bald cypress', 'Catalpa': 'Catalpa', 'Cornus': 'Dogwood',
    'Koelreuteria': 'Golden rain', 'Castanea': 'Sweet chestnut', 'Parrotia': 'Ironwood',
    'Cercidiphyllum': 'Katsura', 'Picea': 'Spruce', 'Chamaecyparis': 'False cypress',
    'Laburnum': 'Laburnum', 'Celtis': 'Hackberry', 'Zelkova': 'Zelkova',
    'Ostrya': 'Hop hornbeam', 'Thuja': 'Arborvitae', 'Morus': 'Mulberry',
    'Cercis': 'Redbud',
}


def avg(xs):
    return sum(xs) / len(xs) if xs else None


def collect():
    cnt = defaultdict(int)
    H, D, A = defaultdict(list), defaultdict(list), defaultdict(list)
    dutch = defaultdict(lambda: defaultdict(int))
    with open(CSV) as f:
        for r in csv.DictReader(f):
            g = r['soortnaamKort'].strip()
            if not g or g == 'Onbekend':
                continue
            cnt[g] += 1
            dutch[g][r['soortnaamTop']] += 1
            if r['boomhoogteklasseActueel'] in HEIGHT:
                H[g].append(HEIGHT[r['boomhoogteklasseActueel']])
            if r['stamdiameterklasse'] in DIA:
                D[g].append(DIA[r['stamdiameterklasse']])
            y = r['jaarVanAanleg']
            if y and y.isdigit():
                age = NOW - int(y)
                if 0 < age < 400:
                    A[g].append(age)
    return cnt, H, D, A, dutch


def norm_map(raw):
    """Min-max normalize a {genus: value} dict to a 1-10 scale."""
    vals = [v for v in raw.values() if v is not None]
    lo, hi = min(vals), max(vals)
    out = {}
    for k, v in raw.items():
        if v is None:
            out[k] = None
        else:
            out[k] = 1 + 9 * (v - lo) / (hi - lo) if hi > lo else 5.5
    return out


def archetype(power, agility, pmed, amed, world):
    legend = " (Legendary)" if world >= 1.25 else ""
    if power >= pmed and agility < amed:
        return "Juggernaut — Tank/Artillery" + legend
    if power >= pmed and agility >= amed:
        return "Bruiser — Elite Carry" + legend
    if power < pmed and agility >= amed:
        return "Skirmisher — Glass Cannon" + legend
    return "Support — Chaff/Filler" + legend


def main():
    cnt, H, D, A, dutch = collect()
    research = load_research()
    genera = [g for g in cnt if cnt[g] >= MIN_COUNT and g in research]

    # Amsterdam-data metrics
    h = {g: avg(H[g]) for g in genera}
    d = {g: avg(D[g]) for g in genera}
    a = {g: avg(A[g]) for g in genera}
    mass = {g: (h[g] * d[g]) if (h[g] and d[g]) else None for g in genera}
    growth = {g: (h[g] / a[g]) if (h[g] and a[g]) else None for g in genera}

    # Research metrics
    dens = {g: research[g]["wood_density_kgm3"] for g in genera}
    life = {g: research[g]["lifespan_yr"] for g in genera}
    loglife = {g: (math.log(life[g]) if life[g] else None) for g in genera}
    invdens = {g: (-dens[g] if dens[g] else None) for g in genera}

    nRange = norm_map(h)            # Range  <- local height
    nMass = norm_map(mass)          # mass component of Health
    nLife = norm_map(loglife)       # longevity component of Health
    nAtk = norm_map(dens)           # Attack <- wood hardness
    nSpd = norm_map(invdens)        # Attack speed <- inverse hardness
    nMove = norm_map(growth)        # Movement <- growth vigor

    rows = []
    for g in genera:
        if None in (nRange[g], nMass[g], nLife[g], nAtk[g], nSpd[g], nMove[g]):
            continue
        hp = 0.6 * nMass[g] + 0.4 * nLife[g]   # tankiness = mass + longevity
        world = RARITY_MULT.get(research[g]["world_rarity"], 1.0)
        power_axis = (nAtk[g] + nRange[g] + hp) / 3
        agility_axis = (nSpd[g] + nMove[g]) / 2
        power = round((nAtk[g] + nRange[g] + hp + nSpd[g] + nMove[g]) / 5 * world, 1)
        nl = max(dutch[g], key=dutch[g].get)
        rows.append({
            'g': g, 'common': COMMON.get(g, g), 'nl': nl, 'count': cnt[g],
            'atk': nAtk[g], 'rng': nRange[g], 'hp': hp, 'as': nSpd[g], 'mv': nMove[g],
            'world': world, 'rarity': research[g]["world_rarity"],
            'pa': power_axis, 'aa': agility_axis, 'power': power,
            'persona': research[g]["personality"],
        })

    pas = sorted(r['pa'] for r in rows)
    aas = sorted(r['aa'] for r in rows)
    pmed = pas[len(pas) // 2]
    amed = aas[len(aas) // 2]
    for r in rows:
        r['arch'] = archetype(r['pa'], r['aa'], pmed, amed, r['world'])

    # Group by base archetype name (strip legendary suffix) for the MD sections.
    order = ["Bruiser — Elite Carry", "Juggernaut — Tank/Artillery",
             "Skirmisher — Glass Cannon", "Support — Chaff/Filler"]
    groups = defaultdict(list)
    for r in rows:
        base = r['arch'].replace(" (Legendary)", "")
        groups[base].append(r)

    def fmt(x):
        return f"{x:.0f}"

    with open(OUT, 'w') as f:
        f.write("# Characters — Boomoorlog Genus Roster\n\n")
        f.write("Auto-generated by `generate_characters.py`. One row per genus "
                f"(count >= {MIN_COUNT}). Stats normalized 1-10; **Power** = mean "
                "stat x world-rarity multiplier.\n\n")
        f.write("Stat sources (see `STATS.md`): **Attack**=wood hardness (research), "
                "**Range**=local height (data), **HP**=mass (data) + longevity "
                "(research), **A.Spd**=inverse wood hardness (research), "
                "**Move**=growth vigor (data). Per-genus research in "
                "`memory/characters/`.\n\n")
        f.write(f"Archetype split uses medians: power-axis={pmed:.1f}, "
                f"agility-axis={amed:.1f}.\n\n")

        # Master table sorted by power.
        f.write("## All characters (by Power)\n\n")
        f.write("| Genus | Common | NL | Trees | Atk | Rng | HP | A.Spd | Move | Rarity | Power | Archetype |\n")
        f.write("|---|---|---|--:|--:|--:|--:|--:|--:|:--|--:|---|\n")
        for r in sorted(rows, key=lambda x: -x['power']):
            f.write(f"| *{r['g']}* | {r['common']} | {r['nl'].split(' (')[0]} | "
                    f"{r['count']} | {fmt(r['atk'])} | {fmt(r['rng'])} | {fmt(r['hp'])} | "
                    f"{fmt(r['as'])} | {fmt(r['mv'])} | {r['rarity']} | "
                    f"{r['power']} | {r['arch']} |\n")

        # Archetype sections with personalities.
        f.write("\n## Archetypes (TD stat builds)\n\n")
        blurbs = {
            "Bruiser — Elite Carry": "High power AND high agility: strong, durable, "
                "and quick. The carnage units.",
            "Juggernaut — Tank/Artillery": "High power, low agility: hard-hitting, "
                "tanky, long-range, but slow to move and strike. Walls & artillery.",
            "Skirmisher — Glass Cannon": "Low power, high agility: fast strikes and "
                "movement, fragile and short-range. Swarmers.",
            "Support — Chaff/Filler": "Low power and low agility: weak filler that "
                "wins by sheer numbers in tree-dense ZIP codes.",
        }
        for name in order:
            grp = groups.get(name)
            if not grp:
                continue
            f.write(f"### {name}\n{blurbs[name]}\n\n")
            for r in sorted(grp, key=lambda x: -x['power']):
                star = "★" if r['world'] >= 1.25 else ""
                f.write(f"- **{r['g']}** ({r['common']}){star} — {r['persona']}\n")
            f.write("\n")

        f.write("★ = Legendary (world rarity = rare, multiplier 1.25).\n\n")
        f.write("## Long tail\n\n")
        tail = sorted((g for g in cnt if cnt[g] < MIN_COUNT), key=lambda g: -cnt[g])
        f.write(f"{len(tail)} more genera have <{MIN_COUNT} Amsterdam trees and are "
                "not stat-blocked here. Globally-rare giants among them (e.g. "
                "Sequoiadendron, Sequoia, Araucaria, Davidia) are prime **Legendary** "
                "cards when they appear in a ZIP code.\n")

    print(f"Wrote {OUT} with {len(rows)} genera.")
    print(f"Archetype counts: " +
          ", ".join(f"{k.split(' ')[0]}={len(v)}" for k, v in groups.items()))


if __name__ == "__main__":
    main()
