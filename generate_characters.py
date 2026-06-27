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
from collections import defaultdict

CSV = "data/amsterdam_trees.csv"
OUT = "memory/CHARACTERS.md"
NOW = 2026
MIN_COUNT = 100  # genera below this are folded into the "long tail" note

HEIGHT = {'a. tot 6 m.': 4, 'b. 6 tot 9 m.': 7.5, 'c. 9 tot 12 m.': 10.5,
          'd. 12 tot 15 m.': 13.5, 'e. 15 tot 18 m.': 16.5, 'f. 18 tot 24 m.': 21,
          'g. 24 m. en hoger': 27}
DIA = {'tot 0,1 m.': 0.05, '0,1 tot 0,2 m.': 0.15, '0,2 tot 0,3 m.': 0.25,
       '0,3 tot 0,5 m.': 0.4, '0,5 tot 1 m.': 0.75, '1,0 tot 1,5 m.': 1.25,
       '1,5 m. en groter': 1.75}

# World-rarity multiplier: globally rare / exotic / iconic only. Default 1.0.
WORLD_RARITY = {
    'Ginkgo': 1.30, 'Metasequoia': 1.30, 'Parrotia': 1.20, 'Taxodium': 1.15,
    'Pterocarya': 1.15, 'Liriodendron': 1.10, 'Cercidiphyllum': 1.10,
    'Zelkova': 1.10, 'Liquidambar': 1.05, 'Catalpa': 1.05, 'Koelreuteria': 1.05,
    'Styphnolobium': 1.05, 'Magnolia': 1.05,
}

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


def archetype(size, vigor, smed, vmed, world):
    legend = " (Legendary)" if world >= 1.15 else ""
    if size >= smed and vigor < vmed:
        return "Juggernaut — Tank/Artillery" + legend
    if size >= smed and vigor >= vmed:
        return "Bruiser — Elite Carry" + legend
    if size < smed and vigor >= vmed:
        return "Skirmisher — Glass Cannon" + legend
    return ("Support — Chaff/Filler" + legend) if size < smed else "Balanced" + legend


def main():
    cnt, H, D, A, dutch = collect()
    genera = [g for g in cnt if cnt[g] >= MIN_COUNT]

    h = {g: avg(H[g]) for g in genera}
    d = {g: avg(D[g]) for g in genera}
    a = {g: avg(A[g]) for g in genera}
    mass = {g: (h[g] * d[g]) if (h[g] and d[g]) else None for g in genera}
    growth = {g: (h[g] / a[g]) if (h[g] and a[g]) else None for g in genera}

    nR, nA, nH = norm_map(h), norm_map(d), norm_map(mass)
    nS = norm_map(growth)  # attack speed
    nM = nS                # movement = vigor

    rows = []
    for g in genera:
        if None in (nR[g], nA[g], nH[g], nS[g]):
            continue
        world = WORLD_RARITY.get(g, 1.0)
        size = (nR[g] + nA[g] + nH[g]) / 3
        vigor = nS[g]
        power = round((nA[g] + nR[g] + nH[g] + nS[g] + nM[g]) / 5 * world, 1)
        nl = max(dutch[g], key=dutch[g].get)
        rows.append({
            'g': g, 'common': COMMON.get(g, g), 'nl': nl, 'count': cnt[g],
            'atk': nA[g], 'rng': nR[g], 'hp': nH[g], 'as': nS[g], 'mv': nM[g],
            'world': world, 'size': size, 'vigor': vigor, 'power': power,
        })

    sizes = sorted(r['size'] for r in rows)
    vigs = sorted(r['vigor'] for r in rows)
    smed = sizes[len(sizes) // 2]
    vmed = vigs[len(vigs) // 2]
    for r in rows:
        r['arch'] = archetype(r['size'], r['vigor'], smed, vmed, r['world'])

    # Group by base archetype name (strip legendary suffix) for the MD sections.
    order = ["Bruiser — Elite Carry", "Juggernaut — Tank/Artillery",
             "Skirmisher — Glass Cannon", "Balanced", "Support — Chaff/Filler"]
    groups = defaultdict(list)
    for r in rows:
        base = r['arch'].replace(" (Legendary)", "")
        groups[base].append(r)

    def fmt(x):
        return f"{x:.0f}"

    with open(OUT, 'w') as f:
        f.write("# Characters — Boomoorlog Genus Roster\n\n")
        f.write("Auto-generated by `generate_characters.py` from "
                "`data/amsterdam_trees.csv`. One row per genus (count >= "
                f"{MIN_COUNT}). Stats normalized 1-10; **Power** = mean stat x "
                "world-rarity multiplier.\n\n")
        f.write("Stat sources: Attack=trunk girth, Range=height, Health=height x "
                "girth, Atk speed & Move=growth vigor. See `STATS.md`.\n\n")
        f.write(f"Archetype split uses medians: size={smed:.1f}, vigor={vmed:.1f}.\n\n")

        # Master table sorted by power.
        f.write("## All characters (by Power)\n\n")
        f.write("| Genus | Common | NL | Trees | Atk | Rng | HP | A.Spd | Move | World× | Power | Archetype |\n")
        f.write("|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|\n")
        for r in sorted(rows, key=lambda x: -x['power']):
            f.write(f"| *{r['g']}* | {r['common']} | {r['nl'].split(' (')[0]} | "
                    f"{r['count']} | {fmt(r['atk'])} | {fmt(r['rng'])} | {fmt(r['hp'])} | "
                    f"{fmt(r['as'])} | {fmt(r['mv'])} | {r['world']:.2f} | "
                    f"{r['power']} | {r['arch']} |\n")

        # Archetype sections.
        f.write("\n## Archetypes (TD stat builds)\n\n")
        blurbs = {
            "Bruiser — Elite Carry": "Big AND vigorous: strong, durable, and fast. "
                "The carnage units — a fast-growing giant that hits hard and keeps up.",
            "Juggernaut — Tank/Artillery": "Big but slow: high Attack/Health/Range, "
                "low Attack speed & Movement. Lumbering heavy hitters / walls.",
            "Skirmisher — Glass Cannon": "Small but vigorous: fast move & attack, "
                "low Health/Range. Cheap swarmers that die fast.",
            "Balanced": "No extreme axis — flexible mid-tier all-rounders.",
            "Support — Chaff/Filler": "Low size and low vigor: weak filler that wins "
                "by sheer numbers in tree-dense ZIP codes.",
        }
        for name in order:
            grp = groups.get(name)
            if not grp:
                continue
            f.write(f"### {name}\n{blurbs[name]}\n\n")
            members = sorted(grp, key=lambda x: -x['power'])
            f.write(", ".join(f"*{r['g']}* ({r['common']})"
                    + ("★" if r['world'] >= 1.15 else "") for r in members))
            f.write("\n\n")

        f.write("★ = Legendary (world-rarity multiplier >= 1.15).\n\n")
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
