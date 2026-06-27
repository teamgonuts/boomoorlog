#!/usr/bin/env python3
"""Build the Boomoorlog character wiki: a static, Slay-the-Spire-style site.

Reads per-genus lore from memory/characters/*.md, normalized stats from
memory/CHARACTERS.md, and images from data/tree_pics + data/sprites_pixel,
then emits a self-contained static site into docs/ (GitHub Pages friendly).

Run:  python3 build_wiki.py
Then open docs/index.html in a browser, or deploy docs/ via GitHub Pages.
"""

import glob
import html
import os
import re
import shutil
from collections import defaultdict

CHARDIR = "memory/characters"
CHARTABLE = "memory/CHARACTERS.md"
PHOTODIR = "data/tree_pics"
SPRITEDIR = "data/sprites_pixel"
TREECSV = "data/amsterdam_trees_zip.csv"
OUT = "docs"

RARITY = {
    "common": ("Common", "common"),
    "notable": ("Uncommon", "notable"),
    "rare": ("Legendary", "rare"),
}
STAT_ORDER = [("atk", "Attack"), ("rng", "Range"), ("hp", "Health"),
              ("as", "Atk Speed"), ("mv", "Movement")]


# ---------------------------------------------------------------- inline md
def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    """Minimal markdown inline -> HTML: escape, then **bold** and *italic*."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


# ---------------------------------------------------------------- parse data
def parse_table():
    """Parse memory/CHARACTERS.md master table -> {genus: stat dict}."""
    stats = {}
    with open(CHARTABLE) as f:
        for line in f:
            m = re.match(r"\|\s*\*([A-Za-z]+)\*\s*\|", line)
            if not m:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 12:
                continue
            g = m.group(1)
            try:
                stats[g] = {
                    "common": cells[1], "nl": cells[2].split(" (")[0],
                    "count": int(cells[3]),
                    "atk": float(cells[4]), "rng": float(cells[5]),
                    "hp": float(cells[6]), "as": float(cells[7]),
                    "mv": float(cells[8]), "rarity": cells[9].lower(),
                    "power": float(cells[10]), "arch": cells[11],
                }
            except ValueError:
                continue
    return stats


def amsterdam_totals():
    """Read the municipal tree registry CSV -> (total_trees, distinct_genera).

    Genus is column 'soortnaamTop' (e.g. 'Iep (Ulmus)'); blanks are counted as
    trees but not as a named genus. Returns (None, None) if the CSV is absent.
    """
    if not os.path.exists(TREECSV):
        return None, None
    import csv
    with open(TREECSV) as f:
        r = csv.reader(f)
        header = next(r)
        gi = header.index("soortnaamTop")
        total, genera = 0, set()
        for row in r:
            total += 1
            g = row[gi].strip()
            if g:
                genera.add(g)
    return total, len(genera)


# Genera that get an embedded OpenStreetMap of real locations.
# A set limits the scope (prototyping); None maps every roster genus.
MAP_GENERA = None


def clean_height(h):
    """'a. tot 6 m.' -> '≤6 m'; 'b. 6 tot 9 m.' -> '6–9 m'."""
    h = re.sub(r"^[a-z]\.\s*", "", h.strip()).rstrip(".").strip()
    h = h.replace(" tot ", "–")
    h = re.sub(r"^tot\s*", "≤", h)
    return h


def collect_points(wanted):
    """One pass over TREECSV -> {genus: [tree dict, ...]} for wanted genera.

    `wanted` is a set of genus names (matched on 'soortnaamKort'), or None for
    all. Each tree dict carries la/lo (coords, 5 decimals ~1 m) plus any present
    per-tree fields: sp (species/cultivar), yr (year planted), h (height class),
    pc (postcode). Returns {} if the CSV is absent.
    """
    if not os.path.exists(TREECSV):
        return {}
    import csv
    trees = defaultdict(list)
    with open(TREECSV) as f:
        r = csv.DictReader(f)
        for row in r:
            g = row["soortnaamKort"].strip()
            if not g or (wanted is not None and g not in wanted):
                continue
            lo, la = row["longitude"].strip(), row["latitude"].strip()
            if not (lo and la):
                continue
            try:
                rec = {"la": round(float(la), 5), "lo": round(float(lo), 5)}
            except ValueError:
                continue
            sp = row.get("soortnaam", "").strip()
            yr = row.get("jaarVanAanleg", "").strip()
            ht = clean_height(row.get("boomhoogteklasseActueel", ""))
            pc = row.get("postcode6", "").strip()
            if sp:
                rec["sp"] = sp
            if yr:
                rec["yr"] = yr
            if ht:
                rec["h"] = ht
            if pc:
                rec["pc"] = pc
            trees[g].append(rec)
    return trees


def sections(text):
    """Split markdown into {heading: body} for '## ' headings."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        h = re.match(r"^##\s+(.*)", line)
        if h:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur, buf = h.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def parse_char(path):
    with open(path) as f:
        text = f.read()
    genus = os.path.splitext(os.path.basename(path))[0]
    title = re.search(r"^#\s+(.*)", text, re.M)
    title = title.group(1).strip() if title else genus
    m = re.match(r"(\S+)\s+—\s+(.+?)\s*\((.+?)\)\s*$", title)
    common, dutch = (m.group(2), m.group(3)) if m else (genus, "")
    sec = sections(text)
    inputs = {}
    for key in ("max_height_m", "lifespan_yr", "wood_density_kgm3",
                "growth_class", "world_rarity"):
        mm = re.search(rf"{key}:\s*([^\n]+)", text)
        inputs[key] = mm.group(1).strip() if mm else ""
    return {
        "genus": genus, "common": common, "dutch": dutch,
        "personality": sec.get("Personality", ""),
        "facts": sec.get("Real-world facts", ""),
        "flavor": sec.get("Combat flavor", ""),
        "inputs": inputs,
    }


def bullets(md):
    """Render a '- **key:** val' bullet block as <dl>-style rows."""
    rows = []
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        body = line[2:]
        km = re.match(r"\*\*(.+?):\*\*\s*(.*)", body)
        if km:
            rows.append(f'<div class="fact"><span class="fact-k">{inline(km.group(1))}</span>'
                        f'<span class="fact-v">{inline(km.group(2))}</span></div>')
        else:
            rows.append(f'<div class="fact"><span class="fact-v">{inline(body)}</span></div>')
    return "\n".join(rows)


# ---------------------------------------------------------------- rendering
def stat_bar(label, val):
    pct = max(0, min(100, val * 10))
    return (f'<div class="stat"><span class="stat-l">{label}</span>'
            f'<span class="stat-track"><span class="stat-fill" style="width:{pct:.0f}%"></span></span>'
            f'<span class="stat-n">{val:.0f}</span></div>')


def page_head(title, depth):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}assets/css/style.css">
</head>
<body>
<header class="site">
  <a class="brand" href="{up}index.html">🌳 Boomoorlog <span>Wiki</span></a>
  <span class="tagline">The trees of Amsterdam, ready for war</span>
</header>
<main>"""


PAGE_FOOT = """</main>
<footer class="site">
  <a href="../index.html">← Back to roster</a>
  <span>Boomoorlog — an Amsterdam tree-war simulation. Stats derived from real open-data trees.</span>
</footer>
</body>
</html>"""


def char_page(c, st, rel_photo, rel_sprite, has_map=False):
    rarity_key = (st["rarity"] if st else c["inputs"].get("world_rarity", "common")).lower()
    rar_label, rar_cls = RARITY.get(rarity_key, ("Common", "common"))
    arch = st["arch"].replace(" (Legendary)", "") if st else "Long-tail / Unranked"
    legendary = bool(st and "Legendary" in st["arch"]) or rarity_key == "rare"

    dutch = f' <span class="nl">({esc(c["dutch"])})</span>' if c["dutch"] else ""
    out = [page_head(f'{c["genus"]} — {c["common"]} | Boomoorlog Wiki', 1)]
    out.append(f'<article class="char rarity-{rar_cls}">')

    # ---- body (left, scrollable)
    out.append('<div class="char-body">')
    out.append(f'<h1>{esc(c["genus"])} <span class="common">— {esc(c["common"])}</span>{dutch}</h1>')
    if c["personality"]:
        out.append(f'<p class="lead">{inline(c["personality"])}</p>')
    if c["flavor"]:
        out.append('<h3>Combat flavor</h3>')
        out.append(f'<p>{inline(c["flavor"])}</p>')
    if c["facts"]:
        out.append('<h3>Real-world facts</h3>')
        out.append(f'<div class="facts">{bullets(c["facts"])}</div>')

    if has_map:
        out.append('<h3>Where they grow in Amsterdam</h3>')
        out.append(f'<div id="treemap" class="treemap" data-genus="{esc(c["genus"])}"></div>')
        out.append('<p class="map-note">Every pin is a real registered tree in the municipal '
                   'open-data registry. Clusters show how many trees they hold — zoom in and '
                   'they split apart down to individual trees.</p>')

    out.append('<h3>Gallery</h3>')
    out.append('<div class="gallery">')
    out.append(f'<figure><img src="{rel_photo}" alt="{esc(c["genus"])} real tree"><figcaption>The real tree</figcaption></figure>')
    out.append(f'<figure><img class="pixel" src="{rel_sprite}" alt="{esc(c["genus"])} sprite"><figcaption>Battle sprite</figcaption></figure>')
    out.append('</div>')
    out.append('</div>')  # char-body

    # ---- infobox (right, sticky/static)
    out.append('<aside class="infobox">')
    out.append('<div class="ib-compare">')
    out.append(f'<figure><img src="{rel_photo}" alt="{esc(c["genus"])} real tree"><figcaption>Real tree</figcaption></figure>')
    out.append(f'<figure><img class="pixel" src="{rel_sprite}" alt="{esc(c["genus"])} sprite"><figcaption>Sprite</figcaption></figure>')
    out.append('</div>')
    out.append(f'<h2 class="ib-name">{esc(c["genus"])}</h2>')
    out.append(f'<div class="ib-sub">{esc(c["common"])}</div>')
    out.append('<div class="ib-badges">')
    out.append(f'<span class="badge rarity-{rar_cls}">{rar_label}</span>')
    if legendary:
        out.append('<span class="badge star">★ Legendary</span>')
    out.append('</div>')
    out.append(f'<div class="ib-arch">{esc(arch)}</div>')
    if st:
        out.append('<div class="ib-stats">')
        for key, label in STAT_ORDER:
            out.append(stat_bar(label, st[key]))
        out.append('</div>')
        out.append(f'<div class="ib-power"><span>Power</span><b>{st["power"]:.1f}</b></div>')
        out.append(f'<div class="ib-count">{st["count"]:,} trees in Amsterdam</div>')
    else:
        out.append('<div class="ib-stats unranked">Below the roster cutoff — a rare '
                   'long-tail card with no fixed stat block yet.</div>')
        if c["inputs"].get("max_height_m"):
            out.append(f'<div class="ib-count">Max height ~{esc(c["inputs"]["max_height_m"])} m</div>')
    out.append('</aside>')

    out.append('</article>')
    if has_map:
        out.append(MAP_ASSETS)
        out.append('<script>\n' + MAP_JS + '\n</script>')
    out.append(PAGE_FOOT)
    return "\n".join(out)


MAP_ASSETS = """<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>"""

MAP_JS = r"""
(function(){
  var el = document.getElementById('treemap');
  if(!el || !window.L) return;
  var genus = el.dataset.genus;
  var map = L.map('treemap', {scrollWheelZoom:false}).setView([52.3676, 4.9041], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    subdomains:'abcd', maxZoom:19,
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
  }).addTo(map);

  var icon = L.icon({
    iconUrl: '../assets/sprites/' + genus + '.png',
    iconSize: [30, 40], iconAnchor: [15, 38], tooltipAnchor: [0, -34],
    className: 'tree-pin'
  });
  var thisYear = new Date().getFullYear();
  function tip(t){
    var rows = [];
    if(t.sp) rows.push('<em>' + t.sp + '</em>');
    if(t.yr){ var age = thisYear - parseInt(t.yr, 10);
      rows.push('Planted ' + t.yr + (age > 0 ? ' &middot; ~' + age + ' yr old' : '')); }
    if(t.h) rows.push('Height ' + t.h);
    if(t.pc) rows.push('📍 ' + t.pc);
    return rows.join('<br>');
  }

  var cluster = L.markerClusterGroup({
    chunkedLoading:true, showCoverageOnHover:false,
    maxClusterRadius:45,
    disableClusteringAtZoom:14,   // zoom >= 14 -> every tree shows as its own sprite
    spiderfyOnMaxZoom:false
  });
  fetch('../assets/maps/' + genus + '.json')
    .then(function(r){ return r.json(); })
    .then(function(d){
      var arr = d.trees, ms = [];
      for(var i=0; i<arr.length; i++){
        var t = arr[i];
        var m = L.marker([t.la, t.lo], {icon: icon, riseOnHover: true});
        m.bindTooltip(tip(t), {direction:'top', opacity:0.97, className:'tree-tip'});
        ms.push(m);
      }
      cluster.addLayers(ms);
      map.addLayer(cluster);
      if(ms.length) map.fitBounds(cluster.getBounds().pad(0.05));
    });
})();
"""


def index_page(chars, totals=(None, None)):
    """chars: list of (c, st). Rendered as one grid sorted by Amsterdam tree count."""
    total_trees, total_genera = totals
    out = [page_head("Boomoorlog Wiki — The Tree Roster", 0)]
    out.append('<section class="hero">')
    out.append('<h1>The Tree Roster</h1>')
    out.append('<div class="hero-stats">')
    if total_trees:
        out.append(f'<div class="hstat"><b>{total_trees:,}</b><span>trees in Amsterdam</span></div>')
    if total_genera:
        out.append(f'<div class="hstat"><b>{total_genera}</b><span>genera in the city</span></div>')
    out.append(f'<div class="hstat"><b>{len(chars)}</b><span>playable archetypes</span></div>')
    out.append('</div>')
    out.append('</section>')

    # ---- toolbar: sort + filters
    out.append('<div class="toolbar">')
    out.append('<div class="tb-group"><label>Sort</label>'
               '<select id="sortby">'
               '<option value="count">Trees in Amsterdam</option>'
               '<option value="rarity">Rarity</option>'
               '<option value="atk">Attack</option>'
               '<option value="rng">Range</option>'
               '<option value="hp">Health</option>'
               '<option value="as">Attack speed</option>'
               '<option value="mv">Movement</option>'
               '<option value="power">Power</option>'
               '<option value="name">Name (A–Z)</option>'
               '</select>'
               '<button id="dir" class="dir" title="Toggle ascending / descending">▼ Desc</button></div>')
    out.append('<div class="tb-group"><label>Rarity</label>'
               '<button class="chip rarity-common" data-rf="common">Common</button>'
               '<button class="chip rarity-notable" data-rf="notable">Uncommon</button>'
               '<button class="chip rarity-rare" data-rf="rare">Legendary</button></div>')
    out.append('<div class="tb-group"><label>Archetype</label>'
               '<button class="chip" data-af="bruiser">Bruiser</button>'
               '<button class="chip" data-af="juggernaut">Juggernaut</button>'
               '<button class="chip" data-af="skirmisher">Skirmisher</button>'
               '<button class="chip" data-af="support">Support</button></div>')
    out.append('<div class="tb-count"><span id="shown">0</span> trees shown</div>')
    out.append('</div>')

    rrank = {"common": 1, "notable": 2, "rare": 3}

    def csrow(label, v):
        pct = max(0, min(100, v * 10))
        return (f'<div class="cs-row"><span class="cs-l">{label}</span>'
                f'<span class="cs-t"><span class="cs-f" style="width:{pct:.0f}%"></span></span>'
                f'<b>{v:.0f}</b></div>')

    ordered = sorted(chars, key=lambda x: -(x[1]["count"] if x[1] else 0))
    out.append('<div class="grid">')
    for c, st in ordered:
        rarity_key = (st["rarity"] if st else c["inputs"].get("world_rarity", "common")).lower()
        _, rar_cls = RARITY.get(rarity_key, ("Common", "common"))
        arch_key = (st["arch"].split(" ")[0].lower() if st else "longtail")
        count_fmt = f'{st["count"]:,}' if st else "—"
        d = (f'data-name="{esc(c["genus"])}" data-rarity="{rarity_key}" '
             f'data-rrank="{rrank.get(rarity_key, 0)}" data-arch="{arch_key}" '
             f'data-count="{st["count"] if st else 0}" data-atk="{st["atk"]:.1f}" '
             f'data-rng="{st["rng"]:.1f}" data-hp="{st["hp"]:.1f}" data-as="{st["as"]:.1f}" '
             f'data-mv="{st["mv"]:.1f}" data-power="{st["power"]:.1f}"') if st else \
            (f'data-name="{esc(c["genus"])}" data-rarity="{rarity_key}" data-rrank="0" '
             f'data-arch="longtail" data-count="0" data-power="0"')
        out.append(f'<a class="card rarity-{rar_cls}" href="trees/{c["genus"]}.html" {d}>')
        out.append(f'<div class="card-art"><img class="pixel" src="assets/sprites/{c["genus"]}.png" alt=""></div>')
        out.append(f'<div class="card-name">{esc(c["genus"])}</div>')
        out.append(f'<div class="card-common">{esc(c["common"])}</div>')
        out.append(f'<div class="card-foot"><span class="cnt">🌳 {count_fmt}</span></div>')
        if st:
            out.append('<div class="card-stats">')
            out.append(f'<div class="cs-name">{esc(c["genus"])}</div>')
            for lbl, key in [("ATK", "atk"), ("RNG", "rng"), ("HP", "hp"),
                             ("SPD", "as"), ("MOV", "mv")]:
                out.append(csrow(lbl, st[key]))
            out.append(f'<div class="cs-power"><span>POWER</span><b>{st["power"]:.1f}</b></div>')
            out.append('</div>')
        out.append('</a>')
    out.append('</div>')

    out.append("</main>\n<script>\n" + INDEX_JS + "\n</script>")
    out.append("""<footer class="site">
  <span>Boomoorlog — an Amsterdam tree-war simulation. Stats derived from real open-data trees.</span>
</footer>
</body>
</html>""")
    return "\n".join(out)


INDEX_JS = r"""
(function(){
  const grid = document.querySelector('.grid');
  const cards = Array.from(grid.children);
  const sortSel = document.getElementById('sortby');
  const dirBtn = document.getElementById('dir');
  const shown = document.getElementById('shown');
  const rarityF = new Set(), archF = new Set();
  let dir = -1;  // -1 = descending, 1 = ascending

  function keyVal(card, key){
    if(key === 'rarity') return +card.dataset.rrank;
    if(key === 'name')   return card.dataset.name.toLowerCase();
    return parseFloat(card.dataset[key] || '0');
  }
  function apply(){
    let n = 0;
    cards.forEach(c => {
      const rOk = rarityF.size === 0 || rarityF.has(c.dataset.rarity);
      const aOk = archF.size === 0 || archF.has(c.dataset.arch);
      const vis = rOk && aOk;
      c.classList.toggle('hidden', !vis);
      if(vis) n++;
    });
    shown.textContent = n;
    const key = sortSel.value;
    const sorted = cards.slice().sort((a,b) => {
      let va = keyVal(a,key), vb = keyVal(b,key);
      if(typeof va === 'string') return dir * va.localeCompare(vb);
      if(va === vb) return (+b.dataset.count) - (+a.dataset.count);  // tiebreak: most common first
      return dir * (va - vb);
    });
    sorted.forEach(c => grid.appendChild(c));
  }
  sortSel.addEventListener('change', apply);
  dirBtn.addEventListener('click', () => {
    dir *= -1;
    dirBtn.textContent = dir < 0 ? '▼ Desc' : '▲ Asc';
    apply();
  });
  document.querySelectorAll('[data-rf]').forEach(b => b.addEventListener('click', () => {
    b.classList.toggle('on');
    const v = b.dataset.rf;
    rarityF.has(v) ? rarityF.delete(v) : rarityF.add(v);
    apply();
  }));
  document.querySelectorAll('[data-af]').forEach(b => b.addEventListener('click', () => {
    b.classList.toggle('on');
    const v = b.dataset.af;
    archF.has(v) ? archF.delete(v) : archF.add(v);
    apply();
  }));
  apply();
})();
"""


# ---------------------------------------------------------------- main
def build():
    stats = parse_table()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(f"{OUT}/trees", exist_ok=True)
    os.makedirs(f"{OUT}/assets/css", exist_ok=True)
    os.makedirs(f"{OUT}/assets/photos", exist_ok=True)
    os.makedirs(f"{OUT}/assets/sprites", exist_ok=True)
    os.makedirs(f"{OUT}/assets/maps", exist_ok=True)
    open(f"{OUT}/.nojekyll", "w").close()

    import json
    map_pts = collect_points(MAP_GENERA)

    chars = []
    for path in sorted(glob.glob(f"{CHARDIR}/*.md")):
        if os.path.basename(path).startswith("_"):
            continue
        c = parse_char(path)
        g = c["genus"]
        photo = f"{PHOTODIR}/{g}.jpg"
        sprite = f"{SPRITEDIR}/{g}.png"
        if not (os.path.exists(photo) and os.path.exists(sprite)):
            continue  # need both photo + sprite to get a page
        shutil.copy(photo, f"{OUT}/assets/photos/{g}.jpg")
        shutil.copy(sprite, f"{OUT}/assets/sprites/{g}.png")
        st = stats.get(g)
        has_map = g in map_pts and len(map_pts[g]) > 0
        if has_map:
            with open(f"{OUT}/assets/maps/{g}.json", "w") as mf:
                json.dump({"n": len(map_pts[g]), "trees": map_pts[g]},
                          mf, separators=(",", ":"))
        html_out = char_page(c, st, f"../assets/photos/{g}.jpg",
                             f"../assets/sprites/{g}.png", has_map=has_map)
        with open(f"{OUT}/trees/{g}.html", "w") as f:
            f.write(html_out)
        chars.append((c, st))

    with open(f"{OUT}/index.html", "w") as f:
        f.write(index_page(chars, amsterdam_totals()))
    write_css()

    ranked = sum(1 for _, st in chars if st)
    print(f"Built {len(chars)} character pages ({ranked} stat-ranked, "
          f"{len(chars) - ranked} long-tail) -> {OUT}/index.html")


def write_css():
    with open(f"{OUT}/assets/css/style.css", "w") as f:
        f.write(CSS)


CSS = r"""
:root{
  --bg:#0c0d10; --bg2:#14161b; --panel:#191c23; --panel2:#1f232c;
  --ink:#e7e3da; --dim:#9aa0ac; --line:#2a2f3a;
  --common:#7f8a99; --notable:#4a9fd4; --rare:#e0a33a;
  --accent:#c0463b;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}
img{max-width:100%;display:block}
.pixel{image-rendering:pixelated;image-rendering:crisp-edges}
a{color:#e6b566;text-decoration:none}
a:hover{text-decoration:underline}

/* ---- header / footer ---- */
header.site{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
  padding:14px 28px;background:linear-gradient(#181b22,#0f1115);
  border-bottom:2px solid var(--accent)}
.brand{font-size:22px;font-weight:700;color:var(--ink);letter-spacing:.5px}
.brand span{color:var(--accent)}
.tagline{color:var(--dim);font-style:italic;font-size:14px}
footer.site{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;
  margin-top:48px;padding:22px 28px;border-top:1px solid var(--line);
  color:var(--dim);font-size:13px}
main{max-width:1040px;margin:0 auto;padding:28px}

/* ---- index hero + groups ---- */
.hero{padding:18px 0 8px;border-bottom:1px solid var(--line);margin-bottom:26px}
.hero h1{font-size:40px;margin:0 0 8px}
.hero p{color:var(--dim);max-width:70ch;margin:0}
.hero-stats{display:flex;flex-wrap:wrap;gap:14px;margin-top:4px}
.hero-stats .hstat{display:flex;flex-direction:column;gap:2px;
  padding:10px 18px 10px 0;border-right:1px solid var(--line)}
.hero-stats .hstat:last-child{border-right:none}
.hero-stats .hstat b{font-size:30px;line-height:1;color:var(--ink);
  font-family:Georgia,'Times New Roman',serif}
.hero-stats .hstat span{font-size:12px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--dim)}
.legend{display:flex;gap:10px;margin-top:16px}
.legend .lg{font-size:12px;text-transform:uppercase;letter-spacing:.05em;
  padding:3px 12px;border-radius:20px;border:1px solid var(--line);font-weight:700}
.legend .lg.rarity-common{background:#1b2029;color:#c3cad6;border-color:#2f3742}
.legend .lg.rarity-notable{background:rgba(74,159,212,.14);color:#8fcbf0;border-color:rgba(74,159,212,.4)}
.legend .lg.rarity-rare{background:rgba(224,163,58,.14);color:#f0cd84;border-color:rgba(224,163,58,.5)}
/* toolbar */
.toolbar{display:flex;flex-wrap:wrap;gap:14px 26px;align-items:center;
  padding:14px 16px;margin-bottom:22px;background:var(--panel);
  border:1px solid var(--line);border-radius:10px}
.tb-group{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.tb-group>label{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim)}
#sortby,.dir{background:var(--bg2);color:var(--ink);border:1px solid var(--line);
  border-radius:6px;padding:6px 10px;font:inherit;font-size:14px;cursor:pointer}
.dir:hover,#sortby:hover{border-color:#e6b566}
.chip{background:var(--bg2);color:#aab2bf;border:1px solid var(--line);border-radius:20px;
  padding:5px 13px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.chip:hover{color:var(--ink)}
.chip.on{color:#fff;background:var(--panel2);border-color:#e6b566}
.chip.rarity-notable{color:#8fcbf0;border-color:rgba(74,159,212,.4)}
.chip.rarity-notable.on{background:rgba(74,159,212,.22);color:#cfeaf9;border-color:var(--notable)}
.chip.rarity-rare{color:#e0b25a;border-color:rgba(224,163,58,.45)}
.chip.rarity-rare.on{background:rgba(224,163,58,.22);color:#f4d791;border-color:var(--rare)}
.tb-count{margin-left:auto;color:var(--dim);font-size:13px}
.tb-count #shown{color:var(--ink);font-weight:700}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
.card{position:relative;overflow:hidden;background:var(--panel);border:1px solid var(--line);
  border-top:3px solid var(--common);border-radius:8px;padding:12px 10px 10px;
  text-align:center;color:var(--ink);transition:transform .08s ease,filter .08s ease}
.card:hover{transform:translateY(-3px);filter:brightness(1.18);text-decoration:none}
.card.hidden{display:none}

/* hover stat overlay */
.card-stats{position:absolute;inset:0;padding:13px 14px;
  background:linear-gradient(rgba(9,11,15,.94),rgba(9,11,15,.98));
  display:flex;flex-direction:column;justify-content:center;gap:6px;
  opacity:0;transform:translateY(6px);transition:opacity .12s ease,transform .12s ease;
  pointer-events:none}
.card:hover .card-stats{opacity:1;transform:none}
.cs-name{text-align:center;font-weight:700;font-size:14px;margin-bottom:3px}
.cs-row{display:grid;grid-template-columns:30px 1fr 16px;align-items:center;gap:7px}
.cs-l{font-size:11px;color:var(--dim);letter-spacing:.03em;text-align:left}
.cs-t{height:7px;background:#0b0d11;border:1px solid #000;border-radius:5px;overflow:hidden}
.cs-f{display:block;height:100%;background:linear-gradient(90deg,#b8412f,#e6b566)}
.cs-row b{font-size:12px;text-align:right}
.cs-power{display:flex;justify-content:space-between;align-items:center;margin-top:4px;
  padding-top:7px;border-top:1px solid var(--line)}
.cs-power span{font-size:11px;color:var(--dim);letter-spacing:.05em}
.cs-power b{color:#e6b566;font-size:18px}
.card-art{height:104px;display:flex;align-items:flex-end;justify-content:center}
.card-art img{max-height:104px;width:auto}
.card-name{font-weight:700;margin-top:6px}
.card-common{color:var(--dim);font-size:13px}
.card-foot{margin-top:6px;font-size:13px;color:var(--dim)}
.card .cnt{color:#9fd6a0;font-weight:600}

/* rarity-tinted cards */
.card.rarity-common{background:#161a21;border-top-color:var(--common)}
.card.rarity-notable{background:#141d27;border-top-color:var(--notable);
  border-color:rgba(74,159,212,.28)}
.card.rarity-notable .cnt{color:#8fcbf0}
.card.rarity-rare{background:#221c12;border-top-color:var(--rare);
  border-color:rgba(224,163,58,.4);box-shadow:0 0 14px rgba(224,163,58,.12)}
.card.rarity-rare .cnt{color:#f0cd84}

/* rarity accents (non-card, e.g. char page) */
.rarity-notable{border-top-color:var(--notable)}
.rarity-rare{border-top-color:var(--rare)}

/* ---- character page ---- */
.char{display:grid;grid-template-columns:1fr 360px;gap:30px;align-items:start}
.char-body h1{font-size:38px;margin:0 0 6px;line-height:1.15}
.char-body h1 .common{color:var(--dim);font-weight:400;font-size:24px}
.char-body h1 .nl{color:var(--dim);font-size:18px;font-style:italic}
.char-body h3{font-size:18px;margin:26px 0 8px;color:#e6b566;
  border-bottom:1px solid var(--line);padding-bottom:4px}
.lead{font-size:19px;line-height:1.6;color:#d8d3c8;font-style:italic;
  border-left:3px solid var(--accent);padding-left:14px;margin:14px 0 0}
.facts{display:flex;flex-direction:column;gap:8px}
.fact{background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:8px 12px}
.fact-k{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.06em;
  color:#e6b566;margin-bottom:2px}
.fact-v{color:var(--ink)}
.gallery{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.gallery figure{margin:0;background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:10px;text-align:center}
.gallery img{border-radius:5px;margin:0 auto;max-height:340px;width:auto}
.gallery .pixel{max-height:300px}
.gallery figcaption{color:var(--dim);font-size:13px;margin-top:8px}
.treemap{height:400px;border-radius:10px;border:1px solid var(--line);
  margin-top:8px;background:#0c0e12;z-index:0}
.leaflet-container{background:#0c0e12;font-family:inherit}
.map-note{color:var(--dim);font-size:13px;font-style:italic;margin-top:10px}
.tree-pin{image-rendering:pixelated;image-rendering:crisp-edges;
  filter:drop-shadow(0 2px 2px rgba(0,0,0,.6))}
.leaflet-tooltip.tree-tip{background:#14161b;color:var(--ink);border:1px solid var(--line);
  border-radius:6px;font-family:inherit;font-size:12px;line-height:1.5;
  box-shadow:0 4px 14px rgba(0,0,0,.5);padding:7px 10px}
.leaflet-tooltip.tree-tip em{color:#e6b566;font-style:italic;font-weight:600}
.leaflet-tooltip-top.tree-tip:before{border-top-color:var(--line)}

/* ---- infobox ---- */
.infobox{background:linear-gradient(#1b1f27,#15181e);border:1px solid var(--line);
  border-radius:10px;padding:16px;position:sticky;top:18px}
.rarity-rare .infobox{border-color:rgba(224,163,58,.5)}
.rarity-notable .infobox{border-color:rgba(74,159,212,.4)}
.ib-compare{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:end;
  background:radial-gradient(ellipse at 50% 95%,rgba(255,255,255,.05),transparent 70%);
  padding:6px 2px 4px}
.ib-compare figure{margin:0;text-align:center;display:flex;flex-direction:column;
  align-items:center;justify-content:flex-end}
.ib-compare img{max-height:170px;width:auto;border-radius:4px;
  border:1px solid var(--line)}
.ib-compare .pixel{image-rendering:pixelated;border-color:transparent}
.ib-compare figcaption{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--dim);margin-top:6px}
.ib-name{text-align:center;font-size:26px;margin:6px 0 0}
.ib-sub{text-align:center;color:var(--dim);margin-bottom:10px}
.ib-badges{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:10px}
.badge{font-size:12px;padding:3px 10px;border-radius:20px;font-weight:700;
  text-transform:uppercase;letter-spacing:.04em;background:var(--panel2);color:var(--ink)}
.badge.rarity-common{background:#2a2f39;color:#c3cad6}
.badge.rarity-notable{background:rgba(74,159,212,.18);color:#8fcbf0}
.badge.rarity-rare{background:rgba(224,163,58,.18);color:#f0cd84}
.badge.star{background:rgba(224,163,58,.14);color:#f0cd84}
.ib-arch{text-align:center;color:var(--dim);font-size:13px;font-style:italic;
  padding-bottom:12px;margin-bottom:12px;border-bottom:1px solid var(--line)}
.ib-stats{display:flex;flex-direction:column;gap:9px}
.ib-stats.unranked{color:var(--dim);font-size:13px;font-style:italic;text-align:center}
.stat{display:grid;grid-template-columns:78px 1fr 22px;align-items:center;gap:8px}
.stat-l{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--dim)}
.stat-track{height:9px;background:#0c0e12;border-radius:5px;overflow:hidden;
  border:1px solid #000}
.stat-fill{display:block;height:100%;background:linear-gradient(90deg,#b8412f,#e6b566)}
.stat-n{text-align:right;font-weight:700;font-size:13px}
.ib-power{display:flex;justify-content:space-between;align-items:center;
  margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
.ib-power span{text-transform:uppercase;letter-spacing:.06em;font-size:12px;color:var(--dim)}
.ib-power b{font-size:26px;color:#e6b566}
.ib-count{text-align:center;color:var(--dim);font-size:12px;margin-top:10px}

@media(max-width:820px){
  .char{grid-template-columns:1fr}
  .infobox{position:static;order:-1}
  .gallery{grid-template-columns:1fr}
}
"""


if __name__ == "__main__":
    build()
