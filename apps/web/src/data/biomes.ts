// The seven biomes of the First Shard. Every fact comes from a canonical source at build time:
//   text (name, isles, altitude, mood, ground, rock, trees, understory, water, signature, creatures, open question)
//     → concept/art-direction/biomes.md, parsed by ./biomes-doc.ts (the build fails if a field is missing)
//   concept and nature-kit sheets → plates under art/handbook/biomes/ (made from art/ by scripts/handbook-sheets.ts)
//   nature kit → art/models/nature/<biome>/kit.json
//   painted leaf cards → art/handbook/foliage/ plates, and which kits use them → scripts/kit/nature-<biome>.py
// Only presentation (labels and order of sheets, which fields to show) lives here. Ids match the world file's `biome` field.
import doc from "../../../../concept/art-direction/biomes.md?raw";
import { foliageUse, parseBiomes } from "./biomes-doc";
import { plateKeys } from "../lib/art";
import type { Sheet } from "./architecture";

export interface NaturePiece { id: string; family: string; name: string; size: number[]; tris: number; notes?: string }
export interface NatureKit { style: string; prefix: string; materials: string[]; pieces: NaturePiece[] }

export interface Biome {
  id: string;
  name: string;
  altitude: string;
  /** The doc's intro line and mood */
  summary: string;
  look: { label: string; value: string }[];
  signature: string;
  creatures: string;
  /** Isles the doc lists for this biome */
  isles: string[];
  /** Concept sheets (plates biomes/<id>-<sheet>) */
  sheets: Sheet[];
  /** Built nature kit sheets (plates biomes/<id>-built-<sheet>) */
  builtSheets: Sheet[];
  kit?: NatureKit;
  /** Painted leaf cards the kit uses */
  foliage: string[];
  open?: string;
}

const kits = Object.fromEntries(
  Object.entries(import.meta.glob<NatureKit>("../../../../art/models/nature/*/kit.json", { eager: true, import: "default" }))
    .map(([path, kit]) => [path.split("/").at(-2)!, kit]),
);
const kitScripts = import.meta.glob<string>("../../../../scripts/kit/nature-*.py", { eager: true, query: "?raw", import: "default" });
const leafUse = foliageUse(kitScripts);

// Presentation: sheet labels and order. Unknown sheets still show, with a label made from the file name.
const SHEET_LABELS: Record<string, string> = {
  "isle-portrait": "Isle portrait: top, lip and underside",
  "isle-portrait-wild": "Isle portrait, wild variant",
  nature: "Nature: trees, plants and rocks",
  terrain: "Terrain materials",
  "built-pieces": "Every piece of the built nature kit",
  "built-prefabs": "Prefabs assembled from the kit",
};
const ORDER = Object.keys(SHEET_LABELS);
const label = (id: string) => SHEET_LABELS[id] ?? id.charAt(0).toUpperCase() + id.slice(1).replace(/-/g, " ");
const sheetsFor = (biome: string, built: boolean): Sheet[] =>
  plateKeys(`biomes/${biome}-`)
    .map((k) => k.slice(`biomes/${biome}-`.length))
    .filter((id) => id.startsWith("built-") === built)
    .sort((a, b) => ((ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99)) || a.localeCompare(b))
    .map((id) => ({ id, label: label(id) }));

export const biomes: Biome[] = parseBiomes(doc).map((b) => ({
  id: b.id, name: b.name, altitude: b.altitude,
  summary: `${b.intro} ${b.mood}`,
  look: [
    { label: "Ground", value: b.ground },
    { label: "Rock", value: b.rock },
    { label: "Trees", value: b.trees },
    { label: "Understory", value: b.understory },
    { label: "Water", value: b.water },
  ],
  signature: b.signature, creatures: b.creatures, isles: b.isles, open: b.open,
  sheets: sheetsFor(b.id, false), builtSheets: sheetsFor(b.id, true),
  kit: kits[b.id],
  foliage: [...leafUse].filter(([, users]) => users.has(b.id)).map(([leaf]) => leaf).sort(),
}));

for (const id of Object.keys(kits))
  if (!biomes.some((b) => b.id === id)) throw new Error(`art/models/nature/${id}/kit.json has no "### ${id}" biome in concept/art-direction/biomes.md`);

/** The painted leaf cards (art/textures/foliage), with the biomes whose kits use each */
export const foliage = plateKeys("foliage/").map((key) => {
  const id = key.slice("foliage/".length);
  return { id, name: label(id), art: key, biomes: biomes.filter((b) => leafUse.get(id)?.has(b.id)).map((b) => b.id) };
});

/** Tree and landmark pieces of a nature kit, tallest first */
export const kitTrees = (kit: NatureKit) => kit.pieces.filter((p) => p.family === "hero" || p.family === "tree").sort((a, b) => b.size[1] - a.size[1]);
/** "w × d m, h m tall" */
export const pieceSize = (p: NaturePiece) => `${p.size[1]} m tall, ${p.size[0]} × ${p.size[2]} m`;
