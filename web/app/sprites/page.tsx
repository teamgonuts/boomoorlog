/**
 * /sprites — Sprite library QA page (admin-only, NOT linked from nav).
 *
 * Layout: SPRITE on the LEFT, real-photo examples on the RIGHT. Purpose:
 * quickly see which organisms get grouped into each sprite form so the
 * reviewer can judge whether the form is a good visual match for the
 * range of species it will represent.
 *
 * Sections:
 *   1. New forms (14) — priority QA section (2026-06-30 C3.D.1 batch).
 *   2. Existing creature forms (10).
 *   3. Existing tree forms (8).
 *
 * Every form has a stable anchor id (e.g. #new-reptile, #creature-bird)
 * so feedback can be referenced unambiguously.
 *
 * Hidden from nav by design.
 */
import fs from "node:fs";
import path from "node:path";

export const metadata = {
  title: "Sprite library (admin) — Creatures AMS",
  description: "QA page for the pixel-art sprite forms.",
  robots: "noindex,nofollow",
};

type FormEntry = {
  id: string;
  label: string;
  /** One image = single form; two = sub-modes rendered side-by-side. */
  sprites: { src: string; caption?: string }[];
  count: string;
  desc: string;
  examples: string[];
  subModes?: string[];
  /** Optional note shown under photos (e.g. photo-vs-tag mismatches). */
  photoNote?: string;
};

// --------------------------------------------------------------------------- //
// Photo resolver: server-side lookup at render time.
//   - /creature_photos/*  → static files in web/public/creature_photos/
//   - /organism_photos/*  → dynamic route handler (app/organism_photos/[slug])
//     that streams from data/organism_photos/ (kept outside web/ so Turbopack
//     doesn't try to bundle 1.5k photos).
// --------------------------------------------------------------------------- //
const CREATURE_PHOTOS_DIR = path.join(process.cwd(), "public", "creature_photos");
const ORGANISM_PHOTOS_DIR = path.join(process.cwd(), "..", "data", "organism_photos");

function photoUrl(slug: string): string | null {
  for (const ext of ["jpg", "jpeg", "png"] as const) {
    if (fs.existsSync(path.join(CREATURE_PHOTOS_DIR, `${slug}.${ext}`))) {
      return `/creature_photos/${slug}.${ext}`;
    }
    if (fs.existsSync(path.join(ORGANISM_PHOTOS_DIR, `${slug}.${ext}`))) {
      return `/organism_photos/${slug}.${ext}`;
    }
  }
  return null;
}

// --------------------------------------------------------------------------- //
// New forms (C3.D.1) — the priority QA section
// --------------------------------------------------------------------------- //
const NEW_FORMS: FormEntry[] = [
  {
    id: "new-lizard",
    label: "lizard",
    sprites: [{ src: "/sprites/library/new/reptile-lizard.png" }],
    count: "0 organisms in DB today",
    desc: "Top-down elongated body, 4 splayed legs, long tail. Rendered via form=reptile with --aspect ≥ 1.",
    examples: [],
    photoNote: "Zero Squamata species in the current taxonomy — lizards need to be ADDED to the DB first (constrained to Amsterdam-geotagged observations per user direction). Candidate list: podarcis-muralis, natrix-helvetica, anguis-fragilis, zootoca-vivipara. Tracked in roadmap follow-up.",
  },
  {
    id: "new-turtle",
    label: "turtle",
    sprites: [{ src: "/sprites/library/new/reptile-turtle.png" }],
    count: "3 organisms (all photos landed)",
    desc: "Top-down shell dome in a contrasting accent colour + 4 leg nubs. Rendered via form=reptile with --aspect < 1.",
    examples: ["trachemys-scripta-scripta", "trachemys-scripta", "pseudemys-concinna"],
  },
  {
    id: "new-fish",
    label: "fish",
    sprites: [{ src: "/sprites/library/new/fish.png" }],
    count: "6 organisms (all photos landed 2026-07-01)",
    desc: "Side-view fusiform body + fin (Cyprinus, Scardinius, Squalius, Leucaspius, Oncorhynchus, plus Cypriniformes at order rank).",
    examples: ["cyprinus-carpio", "scardinius-erythrophthalmus", "leucaspius-delineatus", "cypriniformes"],
  },
  {
    id: "new-amphibian",
    label: "amphibian",
    sprites: [{ src: "/sprites/library/new/amphibian.png" }],
    count: "7 organisms (all photos landed)",
    desc: "Squat side view, frog / toad / newt posture (Bufo, Pelophylax, Lissotriton, Triturus).",
    examples: ["bufo-bufo", "rana-temporaria", "lissotriton-vulgaris", "pelophylax", "pelophylax-esculentus"],
  },
  {
    id: "new-large-mammal",
    label: "large-mammal",
    sprites: [{ src: "/sprites/library/new/large-mammal.png" }],
    count: "~5–7 organisms",
    desc: "Tall 4-legged side view — deer / boar / fox / badger proportions (Capreolus, Sus, Vulpes, Meles, Cervus).",
    examples: ["capreolus-capreolus", "sus-scrofa", "vulpes-vulpes", "meles-meles"],
  },
  {
    id: "new-aquatic-mammal",
    label: "aquatic-mammal",
    sprites: [{ src: "/sprites/library/new/aquatic-mammal.png" }],
    count: "~5 organisms",
    desc: "Otter / muskrat / coypu / water-vole side view — elongated waterline mammal (Lutra, Ondatra, Myocastor, Arvicola, Castor).",
    examples: ["lutra-lutra", "ondatra-zibethicus", "myocastor-coypus"],
  },
  {
    id: "new-water-bird",
    label: "water-bird",
    sprites: [{ src: "/sprites/library/new/water-bird.png" }],
    count: "~25–30 organisms",
    desc: "Duck / coot / goose / grebe on waterline (Anas, Fulica, Cygnus, Aythya, Podiceps, Anser, Gallinula, Aix).",
    examples: ["anas-platyrhynchos", "fulica-atra", "podiceps-cristatus", "gallinula-chloropus", "branta-canadensis", "alopochen-aegyptiaca", "aythya-ferina"],
  },
  {
    id: "new-wading-bird",
    label: "wading-bird",
    sprites: [{ src: "/sprites/library/new/wading-bird.png" }],
    count: "~8–10 organisms",
    desc: "Long-legged wader: heron / stork / spoonbill / cormorant / lapwing (Ardea, Ciconia, Platalea, Egretta, Phalacrocorax).",
    examples: ["ardea-cinerea", "ciconia-ciconia", "platalea-leucorodia", "vanellus-vanellus"],
  },
  {
    id: "new-raptor",
    label: "raptor",
    sprites: [{ src: "/sprites/library/new/raptor.png" }],
    count: "~10–12 organisms",
    desc: "Broad wings spread, top-down or side (Buteo, Falco, Accipiter, Circus, Milvus, plus owls Strix / Asio / Tyto).",
    examples: ["buteo-buteo", "accipiter-nisus", "circus-aeruginosus", "falco-tinnunculus", "asio-otus"],
  },
  {
    id: "new-gull",
    label: "gull",
    sprites: [{ src: "/sprites/library/new/gull.png" }],
    count: "~6–8 organisms",
    desc: "Long-winged side-glide (Larus, Chroicocephalus, Sterna, Hydrocoloeus).",
    examples: ["larus-fuscus", "larus-argentatus", "chroicocephalus-ridibundus", "sterna-hirundo"],
  },
  {
    id: "new-snail",
    label: "snail",
    sprites: [{ src: "/sprites/library/new/mollusc-snail.png" }],
    count: "~15 organisms (all photos landed)",
    desc: "Small foot below + big spiral shell in an accent colour above + 2 tall eyestalks with eye-dot tips. Rendered via form=mollusc with --aspect < 1.",
    examples: ["cornu-aspersum", "cepaea-nemoralis", "cepaea-hortensis", "helix-pomatia", "succinea-putris", "xeroplexa-intersecta", "oxychilus-draparnaudi", "trochulus-hispidus"],
  },
  {
    id: "new-slug",
    label: "slug",
    sprites: [{ src: "/sprites/library/new/mollusc-slug.png" }],
    count: "~10 organisms (all photos landed)",
    desc: "Elongated fleshy body, no shell, 2 tall eyestalks with eye-dot tips. Rendered via form=mollusc with --aspect ≥ 1.",
    examples: ["arion-rufus-vulgaris", "arion-vulgaris", "limax-maximus", "ambigolimax-valentianus", "deroceras-reticulatum"],
  },
  {
    id: "new-dragonfly",
    label: "dragonfly",
    sprites: [{ src: "/sprites/library/new/dragonfly.png" }],
    count: "~19 organisms (all photos landed)",
    desc: "Four spread wings, long slender abdomen — dragonflies + damselflies (Aeshna, Anax, Sympetrum, Calopteryx, Libellula, Ischnura, Coenagrion).",
    examples: ["orthetrum-cancellatum", "aeshna-cyanea", "anax-imperator", "sympetrum-striolatum", "calopteryx-splendens", "ischnura-elegans", "coenagrion-puella", "erythromma-najas"],
  },
  {
    id: "new-mushroom",
    label: "mushroom",
    sprites: [{ src: "/sprites/library/new/mushroom.png" }],
    count: "~25 organisms (all photos landed)",
    desc: "Cap-on-stipe agarics + boletes (Agaricus, Coprinus, Boletus, Leccinum, Chlorophyllum, Macrolepiota). Distinct from the existing `fungus` form (brackets / lichen crusts only).",
    examples: ["agaricus-bitorquis", "agaricus-augustus", "coprinus-comatus", "agrocybe-praecox", "candolleomyces-candolleanus", "boletus-erythropus", "chlorophyllum-rhacodes"],
  },
  {
    id: "new-grasshopper",
    label: "grasshopper",
    sprites: [{ src: "/sprites/library/new/grasshopper.png" }],
    count: "~14 organisms (all photos landed)",
    desc: "Side view with prominent bent hind leg (femur + tibia Z-shape) — grasshoppers, crickets, katydids (Chorthippus, Tettigonia, Pholidoptera, Roeseliana, Metrioptera).",
    examples: ["tettigonia-viridissima", "chorthippus-brunneus", "chorthippus-biguttulus", "chorthippus-albomarginatus", "leptophyes-punctatissima", "meconema-meridionale", "conocephalus-fuscus"],
  },
  {
    id: "new-lagomorph",
    label: "lagomorph",
    sprites: [{ src: "/sprites/library/new/lagomorph.png" }],
    count: "3 organisms (all photos landed)",
    desc: "Rabbit / hare — mammal body plus two tall separated ears (Oryctolagus, Lepus).",
    examples: ["oryctolagus-cuniculus", "lepus"],
  },
  {
    id: "new-rodent",
    label: "rodent",
    sprites: [{ src: "/sprites/library/new/rodent.png" }],
    count: "~13 organisms (all photos landed)",
    desc: "Side-view small rodent — the identity is the LONG THIN NON-BUSHY tail plus prominent round ears. Distinct from the existing `mammal` form which is squirrel-shaped (bushy tail).",
    examples: ["muscardinus-avellanarius", "clethrionomys-glareolus", "rodentia"],
  },
];

// --------------------------------------------------------------------------- //
// Existing creature forms (already tagged in DB / rendered against roster)
// --------------------------------------------------------------------------- //
const CREATURE_FORMS: FormEntry[] = [
  {
    id: "creature-bug",
    label: "bug",
    sprites: [{ src: "/creature_sprites/aphidoidea.png" }],
    count: "many (default for hemiptera / mites)",
    desc: "Tiny oval body, no wings (aphid, scale, mealybug, mite).",
    examples: ["aphidoidea", "aphididae", "acari"],
  },
  {
    id: "creature-beetle",
    label: "beetle",
    sprites: [{ src: "/creature_sprites/coccinella-septempunctata.png" }],
    count: "many (default for coleoptera)",
    desc: "Hard oval shell with elytra seam (ladybirds, weevils, longhorns).",
    examples: ["coccinella-septempunctata", "adalia-bipunctata", "agelastica-alni"],
  },
  {
    id: "creature-caterpillar",
    label: "caterpillar",
    sprites: [{ src: "/creature_sprites/cossus-cossus.png" }],
    count: "many (lepidoptera larvae)",
    desc: "Horizontal segmented worm — represents the LARVAL stage of moth/butterfly species tagged with this form.",
    examples: [],
    photoNote: "No larva photos on disk — iNat captures are almost always the adult moth (see the `moth` row below). The sprite still applies to the larval stage of these species.",
  },
  {
    id: "creature-moth",
    label: "moth",
    sprites: [{ src: "/creature_sprites/noctua-pronuba.png" }],
    count: "many (default for lepidoptera adults)",
    desc: "Symmetric spread wings, top-down (moths, butterflies).",
    examples: ["noctua-pronuba", "apatura-iris", "abraxas-grossulariata", "acronicta-psi"],
  },
  {
    id: "creature-bee",
    label: "bee",
    sprites: [{ src: "/creature_sprites/apis-mellifera.png" }],
    count: "many (hymenoptera + diptera)",
    desc: "Side-view fat body with arched wings (bees, wasps, flies, hoverflies).",
    examples: ["apis-mellifera", "andrena", "anthophora"],
  },
  {
    id: "creature-spider",
    label: "spider",
    sprites: [{ src: "/creature_sprites/araneidae.png" }],
    count: "77 organisms (67 had photos + 10 top-observed backfilled 2026-07-01)",
    desc: "Round body with 8 long jointed legs (knee-bend + foot dot).",
    examples: ["araneidae", "araneus-diadematus", "salticus-scenicus", "marpissa-muscosa", "opilio-canestrinii", "pholcus-phalangioides", "textrix-denticulata", "nuctenea-umbratica"],
  },
  {
    id: "creature-bird",
    label: "bird",
    sprites: [{ src: "/creature_sprites/cyanistes-caeruleus.png" }],
    count: "many (default for passerines)",
    desc: "Perched passerine — body, head, tail, eye (tits, robins, finches, blackbirds).",
    examples: ["cyanistes-caeruleus", "acanthis-cabaret", "acrocephalus-scirpaceus"],
  },
  {
    id: "creature-mammal",
    label: "mammal",
    sprites: [{ src: "/creature_sprites/sciurus-vulgaris.png" }],
    count: "many (default for small mammals)",
    desc: "Side-view 4-legged small mammal (squirrel, mouse, marten, hedgehog).",
    examples: ["sciurus-vulgaris"],
  },
  {
    id: "creature-bat",
    label: "bat",
    sprites: [{ src: "/creature_sprites/pipistrellus-pipistrellus.png" }],
    count: "~10 organisms (chiroptera)",
    desc: "Small body with scalloped wing membrane arched up.",
    examples: ["pipistrellus-pipistrellus"],
  },
  {
    id: "creature-fungus",
    label: "fungus",
    sprites: [{ src: "/sprites/library/new/fungus-lichen.png" }],
    count: "20 organisms (all photos landed)",
    desc: "Right-side-up (top-down) lobed patch — represents lichens, crusts, and shelf/bracket clusters as they appear on the map. Two modes via --aspect: ≥1 bracket cluster (with growth ring), <1 crust/lichen (lobed + speckled + tiny holes). Distinct from the `mushroom` form (cap-on-stipe agarics/boletes).",
    examples: ["xanthoria-parietina", "xanthoria-calcicola", "xanthoria", "physcia-adscendens", "physcia-caesia", "flavoparmelia-soredians", "flavoparmelia-caperata", "ramalina-farinacea", "cladonia-coniocraea", "candelariella-vitellina", "lepraria-incana", "inonotus-hispidus"],
  },
];

// --------------------------------------------------------------------------- //
// Existing tree forms
// --------------------------------------------------------------------------- //
const TREE_FORMS: FormEntry[] = [
  { id: "tree-conifer",   label: "conifer",   sprites: [{ src: "/sprites/Pinus.png"       }], count: "~30 genera", desc: "Triangular evergreen cone (pine, spruce, fir, larch).", examples: ["Pinus", "Picea", "Larix"] },
  { id: "tree-round",     label: "round",     sprites: [{ src: "/sprites/Quercus.png"     }], count: "many",       desc: "Rounded dome (oak, maple, linden, beech).", examples: ["Quercus", "Acer", "Tilia"] },
  { id: "tree-egg",       label: "egg",       sprites: [{ src: "/sprites/Liquidambar.png" }], count: "~15",        desc: "Upright oval (young plane, hornbeam, sweetgum).", examples: ["Liquidambar", "Carpinus"] },
  { id: "tree-columnar",  label: "columnar",  sprites: [{ src: "/sprites/Populus.png"     }], count: "~10",        desc: "Tall narrow column (Lombardy poplar, Italian cypress).", examples: ["Populus"] },
  { id: "tree-spreading", label: "spreading", sprites: [{ src: "/sprites/Platanus.png"    }], count: "~10",        desc: "Broad crown on clear trunk (mature plane, acacia).", examples: ["Platanus", "Robinia"] },
  { id: "tree-umbrella",  label: "umbrella",  sprites: [{ src: "/sprites/Cedrus.png"      }], count: "~5",         desc: "Flat tabletop high on long trunk (old cedar).", examples: ["Cedrus"] },
  { id: "tree-vase",      label: "vase",      sprites: [{ src: "/sprites/Ulmus.png"       }], count: "~5",         desc: "Narrow at base, fanning out (elm, zelkova).", examples: ["Ulmus"] },
  { id: "tree-weeping",   label: "weeping",   sprites: [{ src: "/sprites/Salix.png"       }], count: "~3",         desc: "Foliage drapes down (weeping willow, weeping birch).", examples: ["Salix"] },
];

// --------------------------------------------------------------------------- //
// Row component
// --------------------------------------------------------------------------- //
// Given an organism slug, does a rendered per-organism sprite exist on disk?
const CREATURE_SPRITES_DIR = path.join(process.cwd(), "public", "creature_sprites");
function creatureSpriteUrl(slug: string): string | null {
  const p = path.join(CREATURE_SPRITES_DIR, `${slug}.png`);
  return fs.existsSync(p) ? `/creature_sprites/${slug}.png` : null;
}

function FormRow({ form, kind }: { form: FormEntry; kind: "new" | "creature" | "tree" }) {
  // For tree examples, use tree sprites as thumbnails (no photos available).
  const isTree = kind === "tree";
  const pairs = form.examples
    .map((slug) => {
      const photoU = isTree ? `/sprites/${slug}.png` : photoUrl(slug);
      // For creature/new forms, we may also have a per-organism sprite
      // rendered by pipeline/sample_sprite_batch.py — show it beside the photo
      // so the reviewer can compare form-vs-real.
      const spriteU = isTree ? null : creatureSpriteUrl(slug);
      return { slug, photoU, spriteU };
    })
    .filter((p): p is { slug: string; photoU: string; spriteU: string | null } =>
      p.photoU !== null
    );
  const multi = form.sprites.length > 1;

  return (
    <article id={form.id} className={`sl-row sl-row-${kind}`}>
      <div className={`sl-row-sprite${multi ? " sl-row-sprite-multi" : ""}`}>
        {form.sprites.map((s) => (
          <figure key={s.src} className="sl-sprite-tile">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="pixel" src={s.src} alt={`${form.label} sprite`} />
            {s.caption && <figcaption>{s.caption}</figcaption>}
          </figure>
        ))}
      </div>
      <div className="sl-row-meta">
        <div className="sl-row-head">
          <code className="sl-form-name">{form.label}</code>
          <span className="sl-form-count">{form.count}</span>
        </div>
        <p className="sl-form-desc">{form.desc}</p>
        {form.subModes && (
          <ul className="sl-submodes">
            {form.subModes.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        <div className="sl-form-anchor">
          <code>#{form.id}</code>
        </div>
      </div>
      <div className="sl-row-photos">
        {pairs.length === 0 && !form.photoNote && (
          <div className="sl-no-photos">no photos on disk yet — pending backfill for this category</div>
        )}
        {form.photoNote && (
          <div className="sl-photo-note">{form.photoNote}</div>
        )}
        {pairs.map((p) => (
          <figure key={p.slug} className={`sl-pair${isTree ? " sl-pair-tree" : ""}`}>
            <div className="sl-pair-imgs">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className={"sl-pair-photo" + (isTree ? " pixel" : "")}
                src={p.photoU}
                alt={p.slug}
                loading="lazy"
              />
              {p.spriteU ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  className="sl-pair-sprite pixel"
                  src={p.spriteU}
                  alt={`${p.slug} sprite`}
                  loading="lazy"
                />
              ) : (
                !isTree && (
                  <div className="sl-pair-sprite sl-pair-nospr" title="no per-organism sprite rendered yet">
                    –
                  </div>
                )
              )}
            </div>
            <figcaption>{p.slug}</figcaption>
          </figure>
        ))}
      </div>
    </article>
  );
}

// --------------------------------------------------------------------------- //
// Page
// --------------------------------------------------------------------------- //
export default function SpriteLibraryPage() {
  return (
    <main className="sprite-library">
      <header className="sl-hero">
        <h1>Sprite library</h1>
        <p className="sl-sub">
          Hidden admin QA page. Each row: <b>sprite on the left</b> — the pixel
          form we render. Middle: form name, expected count, description.
          <b> Real photos on the right</b> — examples of the organisms that will
          use this sprite, so you can see the grouping. Reference forms by
          anchor: <code>#new-reptile</code>, <code>#creature-bee</code>.
        </p>
        <p className="sl-counts">
          <b>{NEW_FORMS.length}</b> new forms (C3.D.1 batch) ·{" "}
          <b>{CREATURE_FORMS.length}</b> existing creature forms ·{" "}
          <b>{TREE_FORMS.length}</b> existing tree forms
        </p>
      </header>

      <section>
        <h2>
          New forms ({NEW_FORMS.length})
          <span className="sl-tag-new">2026-06-30 batch — QA gate</span>
        </h2>
        <p className="sl-note">
          14 new forms just landed. Photos are drawn from{" "}
          <code>/creature_photos/</code> (older curated set) and{" "}
          <code>/organism_photos/</code> (C5 backfill). Some categories don&apos;t
          have photos on disk yet — those are called out per row.
        </p>
        <div className="sl-rows">
          {NEW_FORMS.map((f) => (
            <FormRow key={f.id} form={f} kind="new" />
          ))}
        </div>
      </section>

      <section>
        <h2>Existing creature forms ({CREATURE_FORMS.length})</h2>
        <p className="sl-note">
          Already tagged on the current roster and rendered against ~2,300+
          organisms.
        </p>
        <div className="sl-rows">
          {CREATURE_FORMS.map((f) => (
            <FormRow key={f.id} form={f} kind="creature" />
          ))}
        </div>
      </section>

      <section>
        <h2>Existing tree forms ({TREE_FORMS.length})</h2>
        <p className="sl-note">
          Trees don&apos;t have organism photos on disk — the right column
          shows genus sprites instead.
        </p>
        <div className="sl-rows">
          {TREE_FORMS.map((f) => (
            <FormRow key={f.id} form={f} kind="tree" />
          ))}
        </div>
      </section>

      <footer className="sl-footer">
        <p>
          Feedback protocol: reference forms by <code>#id</code> anchors
          (e.g. <code>#new-water-bird</code>, <code>#creature-bee</code>).
          When the new-form batch reads well against its photo groupings,
          the bulk render pass (C3.D.3) can proceed.
        </p>
      </footer>
    </main>
  );
}
