"""Per-genus stat derivation for boomoorlog.

Single source of truth for transforming raw Amsterdam tree data + per-genus
research into the 1-10 stat blocks used by:
  - generate_characters.py  (writes memory/CHARACTERS.md)
  - seed_genera.py          (loads genera into Postgres)

Editing this file changes the game balance for all consumers. Re-run both
generate_characters.py and seed_genera.py after a change to keep the MD wiki
and DB in sync.

Pipeline:
  1. collect_genus_data(csv_path) → per-genus raw inputs (counts, heights,
     diameters, ages) from the Amsterdam dataset.
  2. load_research(char_dir)      → per-genus research facts (max height,
     lifespan, wood density, world-rarity, personality) from MD files.
  3. compute_genus_rows()         → joins (1)+(2), normalizes to 1-10 stats,
     applies world-rarity multiplier, assigns an archetype.
"""

import csv
import glob
import math
import os
import re
from collections import defaultdict

# ---- Constants ----------------------------------------------------------

CSV_DEFAULT = "data/amsterdam_trees.csv"
CHARDIR_DEFAULT = "memory/characters"
NOW = 2026
MIN_COUNT = 100  # genera below this aren't stat-blocked (long tail)
RARITY_MULT = {"common": 1.00, "notable": 1.10, "rare": 1.25}

# Midpoints of the Amsterdam dataset's height/diameter class strings. Used both
# to drive per-genus averages (here) AND to assign each individual tree a
# parsed numeric height in trees.height_m / trees.diameter_cm (see seed_trees.py).
HEIGHT_MIDPOINTS = {
    'a. tot 6 m.':    4,
    'b. 6 tot 9 m.':  7.5,
    'c. 9 tot 12 m.': 10.5,
    'd. 12 tot 15 m.': 13.5,
    'e. 15 tot 18 m.': 16.5,
    'f. 18 tot 24 m.': 21,
    'g. 24 m. en hoger': 27,
}
DIA_MIDPOINTS = {
    'tot 0,1 m.':       0.05,
    '0,1 tot 0,2 m.':   0.15,
    '0,2 tot 0,3 m.':   0.25,
    '0,3 tot 0,5 m.':   0.4,
    '0,5 tot 1 m.':     0.75,
    '1,0 tot 1,5 m.':   1.25,
    '1,5 m. en groter': 1.75,
}

# English common names for readability (fallback: latin genus name).
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


# ---- Class-string parsers (also used by seed_trees.py) ------------------

def parse_height_m(height_class):
    """Class string -> integer meters (midpoint). Returns None if unparseable."""
    v = HEIGHT_MIDPOINTS.get(height_class)
    return int(round(v)) if v is not None else None


def parse_diameter_cm(diameter_class):
    """Class string -> integer cm (midpoint). Returns None if unparseable."""
    v = DIA_MIDPOINTS.get(diameter_class)
    return int(round(v * 100)) if v is not None else None


# ---- Helpers ------------------------------------------------------------

def _first_num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _avg(xs):
    return sum(xs) / len(xs) if xs else None


def _norm_map(raw):
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


def _archetype_label(power_axis, agility_axis, p_med, a_med, world_mult):
    legend = " (Legendary)" if world_mult >= 1.25 else ""
    if power_axis >= p_med and agility_axis < a_med:
        return "Juggernaut — Tank/Artillery" + legend
    if power_axis >= p_med and agility_axis >= a_med:
        return "Bruiser — Elite Carry" + legend
    if power_axis < p_med and agility_axis >= a_med:
        return "Skirmisher — Glass Cannon" + legend
    return "Support — Chaff/Filler" + legend


# ---- Data loaders -------------------------------------------------------

def load_research(char_dir=CHARDIR_DEFAULT):
    """Parse per-genus research from memory/characters/*.md."""
    res = {}
    for path in glob.glob(f"{char_dir}/*.md"):
        genus = os.path.splitext(os.path.basename(path))[0]
        if genus.startswith("_"):
            continue
        with open(path) as f:
            txt = f.read()
        d = {}
        for key in ("max_height_m", "lifespan_yr", "wood_density_kgm3"):
            m = re.search(rf"{key}:\s*([^\n]+)", txt)
            d[key] = _first_num(m.group(1)) if m else None
        m = re.search(r"world_rarity:\s*(\w+)", txt)
        d["world_rarity"] = m.group(1).lower() if m else "common"
        m = re.search(r"^## Personality\s*\n+([^\n]+)", txt, re.M)
        d["personality"] = m.group(1).strip() if m else ""
        d["raw_md"] = txt  # full file content, used as `lore` in the DB
        res[genus] = d
    return res


def collect_genus_data(csv_path=CSV_DEFAULT):
    """Walk the trees CSV and aggregate per-genus inputs.

    Returns (cnt, heights, diameters, ages, dutch_names) where each is a
    {genus: ...} dict.
    """
    cnt = defaultdict(int)
    H, D, A = defaultdict(list), defaultdict(list), defaultdict(list)
    dutch = defaultdict(lambda: defaultdict(int))
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            g = r['soortnaamKort'].strip()
            if not g or g == 'Onbekend':
                continue
            cnt[g] += 1
            dutch[g][r['soortnaamTop']] += 1
            if r['boomhoogteklasseActueel'] in HEIGHT_MIDPOINTS:
                H[g].append(HEIGHT_MIDPOINTS[r['boomhoogteklasseActueel']])
            if r['stamdiameterklasse'] in DIA_MIDPOINTS:
                D[g].append(DIA_MIDPOINTS[r['stamdiameterklasse']])
            y = r['jaarVanAanleg']
            if y and y.isdigit():
                age = NOW - int(y)
                if 0 < age < 400:
                    A[g].append(age)
    return cnt, H, D, A, dutch


def _dutch_display(dutch_counter):
    """Pick the most common Dutch name string (e.g. 'Linde (Tilia)')."""
    if not dutch_counter:
        return None
    return max(dutch_counter, key=dutch_counter.get)


# ---- Main entry points --------------------------------------------------

def collect_all_genera(csv_path=CSV_DEFAULT):
    """Every genus seen in the CSV with minimal info.

    Used by seed_genera.py so trees can FK to a genus row even when that
    genus isn't stat-blocked (count below MIN_COUNT or no research MD).

    Returns a list of dicts:
        {slug, latin_name, dutch_name, display_name, common_name, tree_count}
    """
    cnt, H, D, A, dutch = collect_genus_data(csv_path)
    out = []
    for g in sorted(cnt, key=lambda x: -cnt[x]):
        nl_full = _dutch_display(dutch[g])  # "Linde (Tilia)"
        nl_short = nl_full.split(' (')[0] if nl_full else None
        out.append({
            'slug': g,
            'latin_name': g,
            'dutch_name': nl_short,
            'display_name': f"{nl_short} ({g})" if nl_short else g,
            'common_name': COMMON.get(g, g),
            'tree_count': cnt[g],
        })
    return out


def compute_genus_rows(csv_path=CSV_DEFAULT, char_dir=CHARDIR_DEFAULT):
    """Fully stat-blocked genera (count >= MIN_COUNT AND has research MD).

    Returns a list of dicts with all stat fields populated, in stable order
    by power descending. Each row contains everything both consumers need:

      slug, latin_name, common_name, dutch_name, display_name, tree_count,
      attack, range, health, attack_speed, move_speed,    # 1-10 ints
      world_rarity_multiplier, world_rarity_label, personality, lore,
      archetype, power_score,                             # power_score = float
      power_axis, agility_axis, archetype_median_power, archetype_median_agility
    """
    cnt, H, D, A, dutch = collect_genus_data(csv_path)
    research = load_research(char_dir)
    genera = [g for g in cnt if cnt[g] >= MIN_COUNT and g in research]

    h = {g: _avg(H[g]) for g in genera}
    d = {g: _avg(D[g]) for g in genera}
    a = {g: _avg(A[g]) for g in genera}
    mass = {g: (h[g] * d[g]) if (h[g] and d[g]) else None for g in genera}
    growth = {g: (h[g] / a[g]) if (h[g] and a[g]) else None for g in genera}

    dens = {g: research[g]["wood_density_kgm3"] for g in genera}
    life = {g: research[g]["lifespan_yr"] for g in genera}
    loglife = {g: (math.log(life[g]) if life[g] else None) for g in genera}
    invdens = {g: (-dens[g] if dens[g] else None) for g in genera}

    nRange = _norm_map(h)        # Range  <- local height
    nMass = _norm_map(mass)      # mass component of Health
    nLife = _norm_map(loglife)   # longevity component of Health
    nAtk = _norm_map(dens)       # Attack <- wood hardness
    nSpd = _norm_map(invdens)    # Attack speed <- inverse hardness
    nMove = _norm_map(growth)    # Movement <- growth vigor

    rows = []
    for g in genera:
        if None in (nRange[g], nMass[g], nLife[g], nAtk[g], nSpd[g], nMove[g]):
            continue
        hp_f = 0.6 * nMass[g] + 0.4 * nLife[g]
        world = RARITY_MULT.get(research[g]["world_rarity"], 1.0)
        power_axis = (nAtk[g] + nRange[g] + hp_f) / 3
        agility_axis = (nSpd[g] + nMove[g]) / 2
        power = round((nAtk[g] + nRange[g] + hp_f + nSpd[g] + nMove[g]) / 5 * world, 1)
        nl_full = _dutch_display(dutch[g])
        nl_short = nl_full.split(' (')[0] if nl_full else None
        rows.append({
            'slug': g,
            'latin_name': g,
            'common_name': COMMON.get(g, g),
            'dutch_name': nl_short,
            'display_name': f"{nl_short} ({g})" if nl_short else g,
            'tree_count': cnt[g],
            # 1-10 stats (rounded ints for DB; floats kept for power calc above)
            'attack': int(round(nAtk[g])),
            'range': int(round(nRange[g])),
            'health': int(round(hp_f)),
            'attack_speed': int(round(nSpd[g])),
            'move_speed': int(round(nMove[g])),
            # Rarity + personality + raw lore
            'world_rarity_multiplier': world,
            'world_rarity_label': research[g]["world_rarity"],
            'personality': research[g]["personality"],
            'lore': research[g]["raw_md"],
            # Axes & power (for archetype assignment + MD output)
            'power_axis': power_axis,
            'agility_axis': agility_axis,
            'power_score': power,
        })

    p_med = sorted(r['power_axis'] for r in rows)[len(rows) // 2]
    a_med = sorted(r['agility_axis'] for r in rows)[len(rows) // 2]
    for r in rows:
        r['archetype'] = _archetype_label(
            r['power_axis'], r['agility_axis'], p_med, a_med,
            r['world_rarity_multiplier'],
        )
        r['archetype_median_power'] = p_med
        r['archetype_median_agility'] = a_med

    rows.sort(key=lambda r: -r['power_score'])
    return rows
