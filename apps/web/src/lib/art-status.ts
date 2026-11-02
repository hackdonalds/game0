// What each catalogue entry has of its art pipeline: description → plate and scene (concept art) → its own kit sheet
// and the shared kit it builds on (kit reference sheets) → the 3D model. Found by file naming only, so nothing is
// listed twice: an entry is done when its files exist. Shown as a strip on every entry page; scripts/handbook-check.ts
// prints the gaps as warnings. Plain Node, so the site (at build time) and Bun scripts share it.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export type Stage = "description" | "plate" | "scene" | "sheet" | "kit" | "model";
export const STAGES: { id: Stage; label: string }[] = [
  { id: "description", label: "Description" }, { id: "plate", label: "Plate" }, { id: "scene", label: "Scene" },
  { id: "sheet", label: "Kit sheet" }, { id: "kit", label: "Shared kit" }, { id: "model", label: "3D model" },
];

/** Paths (relative to the repo root) that satisfy a stage, or null when the stage doesn't apply to the kind. Any one path is enough. */
type Paths = Partial<Record<Stage, string[] | null>>;

export interface EntryRef { kind: string; id: string; bodyPlan?: string; family?: string; biome?: string }

const MATERIAL_SHEET: Record<string, string> = { Metal: "metals", Wood: "woods", Leather: "leathers", Cloth: "cloths", Stone: "stones" };

function paths({ kind, id, bodyPlan, family, biome }: EntryRef): Paths {
  const paintings = { plate: [`art/concept/${kind}/${id}.webp`], scene: [`art/concept/${kind}/${id}-scene.webp`] };
  switch (kind) {
    case "bestiary":
      return { ...paintings, sheet: [`art/kit/bestiary/${id}.png`], kit: bodyPlan ? [`art/kit/bestiary/body-plans/${bodyPlan}-body.png`] : [], model: [`art/models/bestiary/${id}.glb`] };
    case "peoples":
      return { ...paintings, sheet: [`art/kit/peoples/${id}/base-turnaround.png`], kit: [`art/kit/peoples/${id}/signatures.png`], model: [`art/models/${id}/base-rigged.glb`, `art/models/${id}/base.glb`] };
    case "ships":
      return { ...paintings, sheet: [`art/kit/ships/${id}.png`], kit: [`art/kit/ships/kit-hulls.png`], model: [`art/models/ships/${id}.glb`] };
    case "architecture":
      return { plate: [`art/concept/architecture/${id}.webp`], scene: [`art/concept/architecture/${id}-scene.webp`], sheet: [`art/kit/architecture/${id}/kit-assembly.png`], kit: [`art/kit/architecture/${id}/kit-structure.png`, `art/kit/architecture/${id}/kit-roots.png`], model: [`art/models/architecture/${id}/kit.json`] };
    case "materials":
      return { ...paintings, sheet: [`art/kit/materials/${id}.png`], kit: family && MATERIAL_SHEET[family] ? [`art/kit/materials/${MATERIAL_SHEET[family]}.png`] : [], model: [`art/models/materials/${id}.glb`] };
    case "skills":
      // A skill's own sheet is its VFX and pose sheet; its tools and weapons come from the shared gear kit
      return { ...paintings, sheet: [`art/kit/skills/${id}.png`], kit: null, model: null };
    case "isles":
      return { ...paintings, scene: [...paintings.scene, `art/concept/isles/${id.replace(/^isle_/, "")}-portrait.png`], sheet: [`art/kit/isles/${id}.png`], kit: biome ? [`art/kit/biomes/${biome}/nature.png`] : [], model: null };
    case "winds":
      return { ...paintings, sheet: [`art/kit/winds/${id}.png`], kit: null, model: null };
    default:
      return {};
  }
}

let root: string | undefined;
/** The repo root: the nearest folder at or above the working directory that has concept/ and art/ */
function repoRoot() {
  if (root) return root;
  for (let dir = process.cwd(); ; dir = dirname(dir)) {
    if (existsSync(join(dir, "concept")) && existsSync(join(dir, "art"))) return (root = dir);
    if (dirname(dir) === dir) throw new Error(`art-status: no concept/ and art/ at or above ${process.cwd()}`);
  }
}

export interface StageStatus { id: Stage; label: string; state: "done" | "missing" | "n/a"; file?: string; wanted?: string }

/** The pipeline status of one entry. `exists` defaults to checking the repo on disk. */
export function artStatus(entry: EntryRef, exists = (p: string) => existsSync(join(repoRoot(), p))): StageStatus[] {
  const p = paths(entry);
  return STAGES.map(({ id, label }) => {
    if (id === "description") return { id, label, state: "done" };
    const list = p[id];
    if (list === null || list === undefined) return { id, label, state: "n/a" };
    const file = list.find(exists);
    return file ? { id, label, state: "done", file } : { id, label, state: "missing", wanted: list[0] };
  });
}
