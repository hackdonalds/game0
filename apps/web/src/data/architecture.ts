// The five architecture styles, from concept/art-direction/architecture.md and modular-kit.md.
// Sheets are plates under art/handbook/architecture/ (made by scripts/handbook-sheets.ts); kit counts come from each kit.json.
import rootwardenKit from "../../../../art/models/architecture/rootwarden/kit.json";
import anchorkinKit from "../../../../art/models/architecture/anchorkin/kit.json";
import galeborneKit from "../../../../art/models/architecture/galeborne/kit.json";
import accordKit from "../../../../art/models/architecture/accord/kit.json";
import oldWorldKit from "../../../../art/models/architecture/old-world/kit.json";

interface Kit { prefix: string; materials: string[]; pieces: { family: string; tris: number }[]; prefabs: { name: string }[] }

export interface Sheet { id: string; label: string }

export interface ArchStyle {
  id: string;
  name: string;
  /** The people who build it, or "" */
  people: string;
  motto: string;
  summary: string;
  traits: { label: string; value: string }[];
  /** Grid of the modular kit */
  grid: string;
  concept: Sheet[];
  kitSheets: Sheet[];
  kit: Kit;
  /** Biomes it is built in */
  biomes: string[];
}

export const archStyles: ArchStyle[] = [
  {
    id: "rootwarden", name: "Rootwardens", people: "rootwarden", motto: "Grow, don't build",
    summary: "Round domes, mounds and root arches, half-buried in the isle. Buildings are coaxed out of living buttress roots, woven walls and moss roofs, with flowers growing from the structure.",
    traits: [
      { label: "Silhouette", value: "Round: domes, mounds, root arches, half-buried" },
      { label: "Structure", value: "Growth: buttress roots, woven living walls, moss roofs" },
      { label: "Materials", value: "Bark, root wood, moss, lichen, flowers" },
      { label: "Meets the isle", value: "Inside it: root caverns and the underside root mass" },
      { label: "Doors", value: "Low and round" },
      { label: "Night light", value: "Amber windows, teal fungus lanterns" },
      { label: "Signature", value: "Flowers growing from the structure" },
    ],
    grid: "No rectilinear grid. Root segments end in round sockets (0.6, 1.0, 1.6 and 2.5 m), dome shells come in radii 3, 5 and 8 m, and openings take burl inserts.",
    concept: [
      { id: "landmark-root-village", label: "Ancient-tree root village (landmark)" },
      { id: "dwelling", label: "Root dwelling" },
      { id: "civic-tending-hall", label: "Tending hall (civic)" },
      { id: "outpost-root-shelter", label: "Travelling root-shelter" },
      { id: "props", label: "Props" },
    ],
    kitSheets: [
      { id: "kit-roots", label: "Root segments" }, { id: "kit-shells", label: "Dome shells" }, { id: "kit-details", label: "Details" },
      { id: "kit-assembly", label: "Assembly" }, { id: "materials", label: "Materials" },
    ],
    kit: rootwardenKit, biomes: ["roothold", "forest"],
  },
  {
    id: "anchorkin", name: "Anchorkin", people: "anchorkin", motto: "Build to stay",
    summary: "Squat, broad and stepped, with thick battered walls of dark basalt veined with teal crystal. Forged chain is structure, binding houses down the cliff and to the underside.",
    traits: [
      { label: "Silhouette", value: "Horizontal: squat, broad, stepped, battered walls" },
      { label: "Structure", value: "Mass: thick walls, heavy arches, forged chain as structure" },
      { label: "Materials", value: "Dark basalt and slate with teal crystal veins, black iron" },
      { label: "Meets the isle", value: "Chained down the cliff and underside" },
      { label: "Doors", value: "Huge" },
      { label: "Night light", value: "Teal crystal veins" },
      { label: "Signature", value: "Ledger inscription bands, oath-marks on doorposts" },
    ],
    grid: "3 m module, 4 m storey, 1 m walls battered 8° inward. Wide and low, with 2 × 3.2 m doors for huge folk.",
    concept: [
      { id: "landmark-ledger-wall", label: "The Ledger Wall (landmark)" },
      { id: "dwelling", label: "Dwelling" },
      { id: "civic-chain-forge", label: "Chain-forge hall (civic)" },
      { id: "outpost-blockhouse", label: "Chained blockhouse outpost" },
      { id: "props", label: "Props" },
    ],
    kitSheets: [
      { id: "kit-structure", label: "Structure" }, { id: "kit-roofs", label: "Roofs" }, { id: "kit-details", label: "Details" },
      { id: "kit-assembly", label: "Assembly" }, { id: "materials", label: "Materials" },
    ],
    kit: anchorkinKit, biomes: ["lagoon"],
  },
  {
    id: "galeborne", name: "Galeborne", people: "galeborne", motto: "Build to leave",
    summary: "Tall narrow towers, spires and sail arcs held up by tension: ropes, struts and cantilevers out over the edge. Pale timber and cream sailcloth, gold beacons and wind chimes at night.",
    traits: [
      { label: "Silhouette", value: "Vertical: tall narrow towers, spires, sail arcs" },
      { label: "Structure", value: "Tension: ropes, struts, cantilevers over the edge" },
      { label: "Materials", value: "Pale timber, cream sailcloth, whitewashed stone" },
      { label: "Meets the isle", value: "Overhangs the cliff: perches, docks, landing platforms" },
      { label: "Doors", value: "Tall and narrow" },
      { label: "Night light", value: "Gold beacons and wind chimes" },
      { label: "Signature", value: "Feather and sail motifs, weathervanes" },
    ],
    grid: "2 m module, 3 m storey, 0.3 m timber or stone skin. Narrow and tall: stacks of 3 to 5 storeys with cantilevered decks.",
    concept: [
      { id: "landmark-beacon-spire", label: "Beacon spire (landmark)" },
      { id: "dwelling", label: "Cliff nest-house" },
      { id: "civic-shipyard", label: "Shipyard dock (civic)" },
      { id: "outpost-pavilion", label: "Travelling pavilion" },
      { id: "props", label: "Props" },
    ],
    kitSheets: [
      { id: "kit-structure", label: "Structure" }, { id: "kit-roofs", label: "Roofs" }, { id: "kit-details", label: "Details" },
      { id: "kit-assembly", label: "Assembly" }, { id: "materials", label: "Materials" },
    ],
    kit: galeborneKit, biomes: ["crag"],
  },
  {
    id: "accord", name: "Accord towns", people: "", motto: "Where the three meet",
    summary: "The shared towns: an Anchorkin stone ground floor, Rootwarden deadwood frames above, Galeborne awnings and sails, terracotta roofs and gothic spires.",
    traits: [
      { label: "Silhouette", value: "Crowded gables and spires around a hall and plaza" },
      { label: "Structure", value: "Stone ground floor, timber-framed upper floors" },
      { label: "Materials", value: "Crystal-veined basalt, deadwood timber, plaster, terracotta, sailcloth" },
      { label: "Meets the isle", value: "Basalt docks and stepped streets" },
      { label: "Signature", value: "Teal-and-gold banners, shop signs, flower boxes" },
    ],
    grid: "2 m module, 3 m storey, 0.5 m walls: Anchorkin-style stone ground floor, timber upper floors, sail awnings.",
    concept: [
      { id: "landmark-accord-hall", label: "Accord Hall (landmark)" },
      { id: "market-hall", label: "Market hall" },
      { id: "town-house", label: "Town house" },
      { id: "props", label: "Plaza and street props" },
    ],
    kitSheets: [
      { id: "kit-structure", label: "Structure" }, { id: "kit-roofs", label: "Roofs" }, { id: "kit-details", label: "Details" },
      { id: "kit-assembly", label: "Assembly" }, { id: "materials", label: "Materials" },
    ],
    kit: accordKit, biomes: ["meadow"],
  },
  {
    id: "old-world", name: "Old world", people: "", motto: "A language nobody understands",
    summary: "Ruins left by the drowned world: precise, geometric, too perfect. Pale stone, razor-clean rings and dead teal channels, being reclaimed by moss and roots.",
    traits: [
      { label: "Silhouette", value: "Monoliths, rings and gates" },
      { label: "Structure", value: "Exact, monumental blocks; nothing leans" },
      { label: "Materials", value: "Pale perfect stone, glyph bands, dead and lit teal channels" },
      { label: "Meets the isle", value: "Sunken vaults; fragments that float free" },
      { label: "Signature", value: "Perfect geometry being reclaimed" },
    ],
    grid: "4 m module, 6 m storey, 1 m razor-clean walls. Rings come in radii 4, 8 and 16 m with one standard channel width.",
    concept: [
      { id: "landmark-monolith-gate", label: "Monolith gate (landmark)" },
      { id: "ruin-fragments", label: "Ruin fragments" },
      { id: "vault-entrance", label: "Sunken vault entrance" },
    ],
    kitSheets: [
      { id: "kit-structure", label: "Structure" }, { id: "kit-rings", label: "Rings" }, { id: "kit-details", label: "Details" },
      { id: "kit-assembly", label: "Assembly" }, { id: "materials", label: "Materials" },
    ],
    kit: oldWorldKit, biomes: ["ruin"],
  },
];

/** Piece count per family, largest first */
export const familyCounts = (kit: Kit) =>
  Object.entries(kit.pieces.reduce<Record<string, number>>((m, p) => ((m[p.family] = (m[p.family] ?? 0) + 1), m), {})).sort((a, b) => b[1] - a[1]);
