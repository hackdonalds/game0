// The architecture styles. Every fact comes from a source:
//   name, builder, biomes, sheet labels, summary → concept/entries/architecture/<style>.md
//   motto and traits → the core-idea table of concept/art-direction/architecture.md
//   modular grid → the "Modules per style" table of concept/art-direction/modular-kit.md
//   piece and prefab counts → art/models/architecture/<style>/kit.json
// Sheets are plates made by scripts/handbook-sheets.ts.
import { concept } from "./concept";
import type { ArchStyleText } from "../lib/concept";

interface Kit { prefix: string; materials: string[]; pieces: { family: string; tris: number }[]; prefabs: { name: string }[] }

export interface Sheet { id: string; label: string }

export interface ArchStyle extends ArchStyleText {
  kit: Kit;
}

const kits = Object.fromEntries(
  Object.entries(import.meta.glob<Kit>("../../../../art/models/architecture/*/kit.json", { eager: true, import: "default" }))
    .map(([path, kit]) => [path.split("/").at(-2)!, kit]),
);

export const archStyles: ArchStyle[] = concept.archStyles.map((a) => ({
  ...a,
  kit: kits[a.id] ?? (() => { throw new Error(`concept/entries/architecture/${a.id}.md: no art/models/architecture/${a.id}/kit.json`); })(),
}));

/** Piece count per family, largest first */
export const familyCounts = (kit: { pieces: { family: string }[] }) =>
  Object.entries(kit.pieces.reduce<Record<string, number>>((m, p) => ((m[p.family] = (m[p.family] ?? 0) + 1), m), {})).sort((a, b) => b[1] - a[1]);
