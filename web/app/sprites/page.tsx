/**
 * /sprites — Sprite library QA page (admin-only, NOT linked from nav).
 *
 * Purpose: show one sample sprite per existing form so a reviewer can
 * judge whether the form library is fit for the bulk-render pass. Also
 * lists the 12 proposed new forms that don't yet have implementations,
 * so the reviewer can see the coverage gap at a glance.
 *
 * Use: send feedback by form-id (every section has a stable anchor —
 * #tree-conifer, #creature-bird, #new-mushroom, etc.) so individual
 * form notes are unambiguous.
 *
 * Hidden from nav by design — this is internal QA tooling. Will be
 * gated behind an env flag (or removed) before public launch.
 */

export const metadata = {
  title: "Sprite library (admin) — Creatures AMS",
  description: "QA page for the pixel-art sprite forms.",
  robots: "noindex,nofollow",
};

type TreeForm = {
  id: string;
  label: string;
  slug: string;
  desc: string;
};

type CreatureForm = {
  id: string;
  label: string;
  slug: string;
  ext?: "jpg" | "jpeg" | "png";
  desc: string;
};

type NewForm = {
  id: string;
  label: string;
  unlocks: string;
  desc: string;
  subModes?: string[];
};

const TREE_FORMS: TreeForm[] = [
  { id: "tree-conifer",   label: "conifer",   slug: "Pinus",        desc: "Triangular evergreen cone (pine, spruce, fir, larch, dawn redwood)." },
  { id: "tree-round",     label: "round",     slug: "Quercus",      desc: "Rounded dome / lollipop (oak, maple, linden, beech, magnolia)." },
  { id: "tree-egg",       label: "egg",       slug: "Liquidambar",  desc: "Upright oval / teardrop (young plane, hornbeam, sweetgum)." },
  { id: "tree-columnar",  label: "columnar",  slug: "Populus",      desc: "Tall and narrow column (Lombardy poplar, fastigiate trees, Italian cypress)." },
  { id: "tree-spreading", label: "spreading", slug: "Platanus",     desc: "Broad crown on a clear trunk (mature plane, acacia, honey locust)." },
  { id: "tree-umbrella",  label: "umbrella",  slug: "Cedrus",       desc: "Flat tabletop high on a long trunk (old cedar, old Scots pine, stone pine)." },
  { id: "tree-vase",      label: "vase",      slug: "Ulmus",        desc: "Narrow at the base, fanning out and up (elm, zelkova)." },
  { id: "tree-weeping",   label: "weeping",   slug: "Salix",        desc: "Foliage drapes down toward the ground (weeping willow, weeping birch)." },
];

const CREATURE_FORMS: CreatureForm[] = [
  { id: "creature-bug",         label: "bug",         slug: "aphidoidea",                desc: "Tiny oval body, no wings, maybe legs + antennae (aphid, scale, mealybug, mite)." },
  { id: "creature-beetle",      label: "beetle",      slug: "coccinella-septempunctata", desc: "Hard oval shell with a central elytra seam (ladybird, weevil, longhorn, dor beetle)." },
  { id: "creature-caterpillar", label: "caterpillar", slug: "cossus-cossus",             desc: "Horizontal segmented worm (sycamore moth larva, hawk-moth caterpillar, processionary)." },
  { id: "creature-moth",        label: "moth",        slug: "noctua-pronuba",            desc: "Symmetric spread wings, top-down (codling moth, hawk moth, butterfly)." },
  { id: "creature-bee",         label: "bee",         slug: "apis-mellifera",            desc: "Side-view fat body, wings arching up (honey bee, bumblebee, wasp, hoverfly, fly)." },
  { id: "creature-spider",      label: "spider",      slug: "araneidae",                 desc: "Round body with 8 legs radiating (garden spider, harvestman)." },
  { id: "creature-bird",        label: "bird",        slug: "cyanistes-caeruleus",       desc: "Passerine perched — body, head, tail, eye (tit, robin, finch, sparrow, blackbird)." },
  { id: "creature-mammal",      label: "mammal",      slug: "sciurus-vulgaris",          desc: "Side-view 4-legged body with head + tail (squirrel, dormouse, mouse, marten, hedgehog)." },
  { id: "creature-bat",         label: "bat",         slug: "pipistrellus-pipistrellus", desc: "Small body, wings arched up-and-out, scalloped membrane (pipistrelle, noctule, barbastelle)." },
  { id: "creature-fungus",      label: "fungus",      slug: "fomitopsis-betulina",       desc: "Bracket / lichen / mycorrhizal cluster (Fomitopsis, Lobarion, Bradyrhizobium). Two modes via --aspect: ≥1 = bracket, <1 = crust/lichen." },
];

// Two existing forms get the photo+sprite comparison treatment.
const TREE_COMPARISONS = ["Quercus"];                    // round form
const CREATURE_COMPARISONS = ["cyanistes-caeruleus", "pipistrellus-pipistrellus"]; // bird, bat

const NEW_FORMS: NewForm[] = [
  { id: "new-plant",          label: "plant",          unlocks: "~656 organisms (biggest gap)", desc: "Non-tree vascular plants. Three sub-modes recommended.", subModes: ["flower (visible bloom — daisy, poppy, mallow)", "grass (vertical blade-clump)", "rosette (ground-hugging — plantain, dandelion)"] },
  { id: "new-mushroom",       label: "mushroom",       unlocks: "~25 organisms",                desc: "Iconic cap-on-stipe — gilled mushrooms and boletes (Agaricus, Coprinus, Chlorophyllum, Boletus, Leccinum, Volvariella). Distinct from the existing `fungus` form, which only does brackets and lichen-crusts." },
  { id: "new-water-bird",     label: "water-bird",     unlocks: "~30 organisms",                desc: "Side view on waterline (ducks, coots, geese, swans)." },
  { id: "new-wading-bird",    label: "wading-bird",    unlocks: "~10 organisms",                desc: "Long legs + long neck + dagger bill (grey heron, white stork, kingfisher variant)." },
  { id: "new-mollusc",        label: "mollusc",        unlocks: "~26 organisms",                desc: "Snail or slug. Two sub-modes.", subModes: ["snail (visible shell — Cornu, Cepaea, Helix)", "slug (no shell — Arion, Limax)"] },
  { id: "new-fish",           label: "fish",           unlocks: "~5+ organisms",                desc: "Side-view fusiform body + fin (carp, perch, rudd)." },
  { id: "new-amphibian",      label: "amphibian",      unlocks: "7 organisms",                  desc: "Squat side view, frog or toad posture; newt variant with tail (Bufo, Pelophylax, Lissotriton)." },
  { id: "new-reptile",        label: "reptile",        unlocks: "3 today, will grow",           desc: "Two sub-modes.", subModes: ["lizard (4 short legs + tail — wall lizard)", "turtle (shell + head + flippers — pond slider)"] },
  { id: "new-raptor",         label: "raptor",         unlocks: "~5 organisms",                 desc: "Broad wings spread, sky view (peregrine, buzzard, kestrel). Visually distinct from the perched-passerine `bird` form." },
  { id: "new-gull",           label: "gull",           unlocks: "~5 organisms",                 desc: "Long-winged side-glide (lesser black-backed, herring, common tern)." },
  { id: "new-large-mammal",   label: "large-mammal",   unlocks: "~5 organisms",                 desc: "Tall side view — deer/boar proportions (Capreolus, Sus scrofa)." },
  { id: "new-aquatic-mammal", label: "aquatic-mammal", unlocks: "~5 organisms",                 desc: "Otter / water-vole side view, waterline visible (Lutra, Arvicola)." },
];

export default function SpriteLibraryPage() {
  return (
    <main className="sprite-library">
      <header className="sl-hero">
        <h1>Sprite library</h1>
        <p className="sl-sub">
          Hidden admin page (unlinked from nav). One sample per form so you
          can judge whether the existing sprite forms cover the encyclopedia
          well enough to start the bulk render. Each form has a stable
          anchor — leave feedback per form id (e.g. <code>#creature-bee</code>,{" "}
          <code>#new-plant</code>).
        </p>
        <p className="sl-counts">
          <b>{TREE_FORMS.length}</b> existing tree forms ·{" "}
          <b>{CREATURE_FORMS.length}</b> existing creature forms ·{" "}
          <b>{NEW_FORMS.length}</b> proposed new forms (pending implementation)
        </p>
      </header>

      <section>
        <h2>Existing tree forms ({TREE_FORMS.length})</h2>
        <p className="sl-note">
          Examples below pull from <code>data/sprites_pixel/&lt;genus&gt;.png</code>{" "}
          (served at <code>/sprites/&lt;genus&gt;.png</code>).
        </p>
        <div className="sl-grid">
          {TREE_FORMS.map((f) => (
            <article key={f.id} id={f.id} className="sl-card">
              <div className="sl-card-art">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="pixel" src={`/sprites/${f.slug}.png`} alt={`${f.label} example: ${f.slug}`} />
              </div>
              <div className="sl-card-meta">
                <span className="sl-id">{f.id}</span>
                <h3>
                  <code>{f.label}</code>{" "}
                  <span className="sl-eg">→ {f.slug}</span>
                </h3>
                <p>{f.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2>Tree comparison: photo ↔ sprite</h2>
        {TREE_COMPARISONS.map((slug) => {
          const f = TREE_FORMS.find((t) => t.slug === slug);
          return (
            <div key={slug} id={`compare-tree-${slug}`} className="sl-compare">
              <div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/photos/${slug}.jpg`} alt={`${slug} photo`} />
                <div className="sl-caption">Photo: {slug}</div>
              </div>
              <div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="pixel" src={`/sprites/${slug}.png`} alt={`${slug} sprite`} />
                <div className="sl-caption">
                  Sprite: <code>{f?.label}</code> form
                </div>
              </div>
            </div>
          );
        })}
      </section>

      <section>
        <h2>Existing creature forms ({CREATURE_FORMS.length})</h2>
        <p className="sl-note">
          Examples below pull from <code>data/creature_sprites_pixel/&lt;slug&gt;.png</code>{" "}
          (served at <code>/creature_sprites/&lt;slug&gt;.png</code>).
        </p>
        <div className="sl-grid">
          {CREATURE_FORMS.map((f) => (
            <article key={f.id} id={f.id} className="sl-card">
              <div className="sl-card-art">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="pixel" src={`/creature_sprites/${f.slug}.png`} alt={`${f.label} example: ${f.slug}`} />
              </div>
              <div className="sl-card-meta">
                <span className="sl-id">{f.id}</span>
                <h3>
                  <code>{f.label}</code>{" "}
                  <span className="sl-eg">→ {f.slug}</span>
                </h3>
                <p>{f.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2>Creature comparisons: photo ↔ sprite</h2>
        {CREATURE_COMPARISONS.map((slug) => {
          const f = CREATURE_FORMS.find((c) => c.slug === slug);
          const ext = f?.ext ?? "jpg";
          return (
            <div key={slug} id={`compare-creature-${slug}`} className="sl-compare">
              <div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/creature_photos/${slug}.${ext}`} alt={`${slug} photo`} />
                <div className="sl-caption">Photo: {slug}</div>
              </div>
              <div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="pixel" src={`/creature_sprites/${slug}.png`} alt={`${slug} sprite`} />
                <div className="sl-caption">
                  Sprite: <code>{f?.label}</code> form
                </div>
              </div>
            </div>
          );
        })}
      </section>

      <section>
        <h2>
          Proposed new forms ({NEW_FORMS.length})
          <span className="sl-tag-pending">pending implementation</span>
        </h2>
        <p className="sl-note">
          These would close the coverage gap for plants, mushrooms (cap-on-stipe),
          water-birds, waders, raptors, gulls, molluscs, fish, amphibians,
          reptiles, large mammals, aquatic mammals. Each is roughly a 30-line
          Python function in the relevant sprite skill. No sprite rendered yet —
          this is the QA gate before implementation.
        </p>
        <div className="sl-grid">
          {NEW_FORMS.map((f) => (
            <article key={f.id} id={f.id} className="sl-card sl-card-pending">
              <div className="sl-card-art sl-card-art-placeholder">
                <span>not yet implemented</span>
              </div>
              <div className="sl-card-meta">
                <span className="sl-id">{f.id}</span>
                <h3>
                  <code>{f.label}</code>{" "}
                  <span className="sl-eg">— {f.unlocks}</span>
                </h3>
                <p>{f.desc}</p>
                {f.subModes && (
                  <ul className="sl-submodes">
                    {f.subModes.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <footer className="sl-footer">
        <p>
          Feedback protocol: reference forms by their <code>#id</code> anchors
          (e.g. <code>#creature-bee</code>, <code>#new-mushroom</code>). When
          satisfied with the existing-form set, the bulk render (C3.D.3) can
          start against the ~2,300 photo-having organisms without a sprite.
          The 12 new forms (C3.D.1) need implementation before they can
          contribute.
        </p>
      </footer>
    </main>
  );
}
