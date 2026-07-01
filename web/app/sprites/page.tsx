/**
 * /sprites — Sprite library QA page (admin-only, NOT linked from nav).
 *
 * Layout: each row = one sprite form. Left = form template thumbnail,
 * middle = metadata, right = per-organism photo|sprite pairs, paginated.
 * A sticky filter bar at the top lets you toggle which form-rows to show
 * (chips show the form's sprite thumbnail so you can pick visually).
 *
 * Data flow:
 *   1. Server component enumerates every rendered sprite in
 *      web/public/creature_sprites/, matches each to its photo + form
 *      (via lib/sprite-gallery.ts).
 *   2. Server component defines the row specs below (label, description,
 *      form-matcher for sub-modes like reptile→lizard/turtle).
 *   3. Client FormRows component handles filter + pagination interactively.
 *
 * Hidden from nav by design.
 */
import { loadGallery } from "@/lib/sprite-gallery";
import { FormRows, type FormRowSpec } from "./FormRows";

export const metadata = {
  title: "Sprite library (admin) — Creatures AMS",
  description: "QA page for the pixel-art sprite forms.",
  robots: "noindex,nofollow",
};

// ------------------------------------------------------------------ //
// Row specs — one entry per row that shows up on the page.
// Each row has a `match` predicate that decides which gallery items
// belong to it. `form` is the taxonomy-classifier form name; aspect
// splits distinguish sub-modes (e.g. reptile <1 = turtle, >=1 = lizard).
// ------------------------------------------------------------------ //
const NEW_FORM_ROWS: FormRowSpec[] = [
  {
    id: "new-lizard",
    label: "lizard",
    kind: "new",
    match: { form: "reptile", aspectGte: 1.0 },
    sprites: [{ src: "/sprites/library/new/reptile-lizard.png" }],
    count: "Squamata (currently 0 in DB — see follow-up)",
    desc: "Top-down elongated body, 4 splayed legs, long tail. Rendered via form=reptile with --aspect ≥ 1.",
    photoNote: "Zero Squamata species in the taxonomy yet — lizards + snakes need to be ADDED to the DB (Amsterdam-geotagged only, per user).",
  },
  {
    id: "new-turtle",
    label: "turtle",
    kind: "new",
    match: { form: "reptile", aspectLt: 1.0 },
    sprites: [{ src: "/sprites/library/new/reptile-turtle.png" }],
    count: "Testudines",
    desc: "Top-down shell dome in a contrasting accent colour + 4 leg nubs + visible head + tail. Rendered via form=reptile with --aspect < 1.",
  },
  {
    id: "new-fish",
    label: "fish",
    kind: "new",
    match: { form: "fish" },
    sprites: [{ src: "/sprites/library/new/fish.png" }],
    count: "Actinopterygii + fish orders",
    desc: "Side-view fusiform body + closed tail fin + dorsal fin.",
  },
  {
    id: "new-amphibian",
    label: "amphibian",
    kind: "new",
    match: { form: "amphibian" },
    sprites: [{ src: "/sprites/library/new/amphibian.png" }],
    count: "Anura + Caudata",
    desc: "Aspect-driven: <0.85 fat toad, ~1.0 medium frog, ≥1.15 slim newt with visible tail.",
  },
  {
    id: "new-large-mammal",
    label: "large-mammal",
    kind: "new",
    match: { form: "large-mammal" },
    sprites: [{ src: "/sprites/library/new/large-mammal.png" }],
    count: "Artiodactyla + Perissodactyla + Carnivora",
    desc: "Aspect-driven: ≥1.15 tall (deer, boar), ~1.0 mid (fox — bushy tail), ≤0.75 low (badger/mustelid — head stripe optional).",
  },
  {
    id: "new-aquatic-mammal",
    label: "aquatic-mammal",
    kind: "new",
    match: { form: "aquatic-mammal" },
    sprites: [{ src: "/sprites/library/new/aquatic-mammal.png" }],
    count: "Lutra + Castor + Ondatra + Myocastor + Arvicola",
    desc: "Elongated waterline mammal — otter / muskrat / coypu / water-vole side view (no synthetic waterline; the map basemap draws water underneath).",
  },
  {
    id: "new-water-bird",
    label: "water-bird",
    kind: "new",
    match: { form: "water-bird" },
    sprites: [{ src: "/sprites/library/new/water-bird.png" }],
    count: "Anseriformes + Podicipediformes + Gruiformes",
    desc: "Duck / coot / goose / grebe on waterline (no dashed water pattern).",
  },
  {
    id: "new-wading-bird",
    label: "wading-bird",
    kind: "new",
    match: { form: "wading-bird" },
    sprites: [{ src: "/sprites/library/new/wading-bird.png" }],
    count: "Pelecaniformes + Ciconiiformes + Suliformes + Charadriiformes waders",
    desc: "Long-legged wader — small body high on stilt legs + S-curve neck + dagger bill. Heron / stork / spoonbill / cormorant / lapwing.",
  },
  {
    id: "new-raptor",
    label: "raptor",
    kind: "new",
    match: { form: "raptor" },
    sprites: [{ src: "/sprites/library/new/raptor.png" }],
    count: "Accipitriformes + Falconiformes + Strigiformes",
    desc: "Broad wings spread, top-down. Buteo, Falco, Accipiter, Circus, plus owls.",
  },
  {
    id: "new-gull",
    label: "gull",
    kind: "new",
    match: { form: "gull" },
    sprites: [{ src: "/sprites/library/new/gull.png" }],
    count: "Laridae + Sternidae",
    desc: "Iconic M-shape spread-wings silhouette from below. Reads at any saturation.",
  },
  {
    id: "new-snail",
    label: "snail",
    kind: "new",
    match: { form: "mollusc", aspectLt: 1.0 },
    sprites: [{ src: "/sprites/library/new/mollusc-snail.png" }],
    count: "shell-bearing Gastropoda",
    desc: "Small foot + spiral shell in accent colour + 2 tall eyestalks with eye-dot tips. Rendered via form=mollusc with --aspect < 1.",
  },
  {
    id: "new-slug",
    label: "slug",
    kind: "new",
    match: { form: "mollusc", aspectGte: 1.0 },
    sprites: [{ src: "/sprites/library/new/mollusc-slug.png" }],
    count: "shell-less Gastropoda (Arionidae, Limacidae, Deroceras)",
    desc: "Elongated fleshy body, no shell, 2 tall eyestalks. Rendered via form=mollusc with --aspect ≥ 1.",
  },
  {
    id: "new-dragonfly",
    label: "dragonfly",
    kind: "new",
    match: { form: "dragonfly" },
    sprites: [{ src: "/sprites/library/new/dragonfly.png" }],
    count: "Odonata",
    desc: "Four spread wings, long slender abdomen — dragonflies + damselflies.",
  },
  {
    id: "new-mushroom",
    label: "mushroom",
    kind: "new",
    match: { form: "mushroom" },
    sprites: [{ src: "/sprites/library/new/mushroom.png" }],
    count: "Agaricales / Boletales / Russulales / Pluteales / Tremellales / Geastrales",
    desc: "Cap-on-stipe agarics + boletes. Distinct from the `fungus` form (brackets / lichen crusts).",
  },
  {
    id: "new-grasshopper",
    label: "grasshopper",
    kind: "new",
    match: { form: "grasshopper" },
    sprites: [{ src: "/sprites/library/new/grasshopper.png" }],
    count: "Orthoptera",
    desc: "Side view with prominent bent hind leg (femur + tibia Z-shape). Grasshoppers, crickets, katydids.",
  },
  {
    id: "new-lagomorph",
    label: "lagomorph",
    kind: "new",
    match: { form: "lagomorph" },
    sprites: [{ src: "/sprites/library/new/lagomorph.png" }],
    count: "Lagomorpha",
    desc: "Rabbit / hare — mammal body + two tall separated ears with clear gap.",
  },
  {
    id: "new-rodent",
    label: "rodent",
    kind: "new",
    match: { form: "rodent" },
    sprites: [{ src: "/sprites/library/new/rodent.png" }],
    count: "Rodentia (excluding Sciuridae which uses `mammal`)",
    desc: "Side-view small rodent — big round ears + LONG THIN non-bushy tail. Distinct from the squirrel-shaped `mammal` form.",
  },
];

const CREATURE_FORM_ROWS: FormRowSpec[] = [
  {
    id: "creature-bug",
    label: "bug",
    kind: "creature",
    match: { form: "bug" },
    sprites: [{ src: "/creature_sprites/aphidoidea.png" }],
    count: "default for Hemiptera",
    desc: "Tiny oval body, no wings (aphid, scale, mealybug, mite).",
  },
  {
    id: "creature-beetle",
    label: "beetle",
    kind: "creature",
    match: { form: "beetle" },
    sprites: [{ src: "/creature_sprites/coccinella-septempunctata.png" }],
    count: "Coleoptera",
    desc: "Hard oval shell with elytra seam.",
  },
  {
    id: "creature-caterpillar",
    label: "caterpillar",
    kind: "creature",
    match: { form: "caterpillar" },
    sprites: [{ src: "/creature_sprites/cossus-cossus.png" }],
    count: "Lepidoptera larvae",
    desc: "Horizontal segmented worm — represents the LARVAL stage of moth/butterfly species.",
    photoNote: "iNat photos are almost always the adult (see the moth row). Sprite still applies to the larval stage of these species.",
  },
  {
    id: "creature-moth",
    label: "moth",
    kind: "creature",
    match: { form: "moth" },
    sprites: [{ src: "/creature_sprites/noctua-pronuba.png" }],
    count: "Lepidoptera adults",
    desc: "Symmetric spread wings, top-down (moths + butterflies).",
  },
  {
    id: "creature-bee",
    label: "bee",
    kind: "creature",
    match: { form: "bee" },
    sprites: [{ src: "/creature_sprites/apis-mellifera.png" }],
    count: "Hymenoptera + Diptera",
    desc: "Side-view balanced abdomen + thorax + head, wing arch over the thorax only.",
  },
  {
    id: "creature-spider",
    label: "spider",
    kind: "creature",
    match: { form: "spider" },
    sprites: [{ src: "/creature_sprites/araneidae.png" }],
    count: "Arachnida",
    desc: "Round body with 8 long jointed legs (knee-bend + foot dot).",
  },
  {
    id: "creature-bird",
    label: "bird",
    kind: "creature",
    match: { form: "bird" },
    sprites: [{ src: "/creature_sprites/cyanistes-caeruleus.png" }],
    count: "Passerines + non-specialised orders",
    desc: "Perched passerine — body, head, tail, eye.",
  },
  {
    id: "creature-mammal",
    label: "mammal",
    kind: "creature",
    match: { form: "mammal" },
    sprites: [{ src: "/creature_sprites/sciurus-vulgaris.png" }],
    count: "Sciuridae + Eulipotyphla + generic small mammals",
    desc: "Side-view 4-legged small mammal with a bushy tail (squirrel-shaped).",
  },
  {
    id: "creature-bat",
    label: "bat",
    kind: "creature",
    match: { form: "bat" },
    sprites: [{ src: "/creature_sprites/pipistrellus-pipistrellus.png" }],
    count: "Chiroptera",
    desc: "Small body with scalloped wing membrane arched up.",
  },
  {
    id: "creature-fungus",
    label: "fungus",
    kind: "creature",
    match: { form: "fungus" },
    sprites: [{ src: "/sprites/library/new/fungus-lichen.png" }],
    count: "Fungi + lichens (excluding cap-on-stipe agarics/boletes)",
    desc: "Right-side-up top-down lobed patch. Two modes via --aspect: ≥1 bracket cluster (with growth ring), <1 crust/lichen (lobed + speckled + tiny holes).",
  },
];

const ALL_ROWS: FormRowSpec[] = [...NEW_FORM_ROWS, ...CREATURE_FORM_ROWS];

export default function SpriteLibraryPage() {
  const gallery = loadGallery();
  return (
    <main className="sprite-library">
      <header className="sl-hero">
        <h1>Sprite library</h1>
        <p className="sl-sub">
          Hidden admin QA page. Each row is one sprite form —{" "}
          <b>form template on the left</b>, meta in the middle,{" "}
          <b>every species that uses this form on the right</b> as a
          photo | sprite pair (paginated). Use the filter chips below
          to hide/show whole rows.
        </p>
        <p className="sl-counts">
          <b>{ALL_ROWS.length}</b> forms · <b>{gallery.length.toLocaleString()}</b> per-organism sprites
        </p>
      </header>

      <FormRows rows={ALL_ROWS} gallery={gallery} />

      <footer className="sl-footer">
        <p>
          Feedback protocol: reference forms by <code>#id</code> anchors
          (e.g. <code>#new-water-bird</code>, <code>#creature-bee</code>)
          or per-organism sprites by <code>#g-&lt;slug&gt;</code>
          (e.g. <code>#g-cyprinus-carpio</code>).
        </p>
      </footer>
    </main>
  );
}
