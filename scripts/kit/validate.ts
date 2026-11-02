// Check kit manifests against the modular-kit rules: architecture (art/models/architecture/<style>/kit.json) and
// nature (art/models/nature/<biome>/kit.json).
// Usage: bun scripts/kit/validate.ts [kit.json ...]   (default: every kit)
import { Glob } from "bun";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";

const ROOT = join(import.meta.dir, "../..");
const STYLES = ["rootwarden", "anchorkin", "galeborne", "accord", "old-world"];
const BIOMES = ["roothold", "crag", "meadow", "garden", "forest", "lagoon", "ruin"];
const BUDGET: Record<string, number> = {
  foundation: 600, wall: 600, corner: 400, floor: 300, access: 600, roof: 600, crown: 1500, insert: 400,
  trim: 300, attachment: 800, root: 800, shell: 1500, ring: 800, block: 600, prop: 800,
  // nature kits
  tree: 3000, hero: 15000, plant: 600, ground: 300, rock: 800, lip: 1500, underside: 2000, water: 800,
};
const VARIANTS = new Set(["intact", "mossy", "broken", "overgrown", "sinking", "lit", "dead"]);
const SOCKETS = new Set([0.6, 1.0, 1.6, 2.5]);
const RADII: Record<string, number[]> = { rootwarden: [3, 5, 8], "old-world": [4, 8, 16] };

const files = process.argv.length > 2
  ? process.argv.slice(2)
  : [...new Glob("art/models/{architecture,nature}/*/kit.json").scanSync(ROOT)].map((f) => join(ROOT, f));

const onGrid = (v: number, step: number) => Math.abs(v / step - Math.round(v / step)) < 1e-6;
let failed = 0;

for (const file of files) {
  const kit = await Bun.file(file).json();
  const errors: string[] = [];
  const err = (id: string, msg: string) => errors.push(`${id}: ${msg}`);
  const nature = file.includes("/nature/");
  if (!(nature ? BIOMES : STYLES).includes(kit.style)) err("kit", `unknown ${nature ? "biome" : "style"} ${kit.style}`);
  if (dirname(file).split("/").pop() !== kit.style) err("kit", `folder does not match style ${kit.style}`);
  const base = kit.grid?.base ?? 0.5;
  const ids = new Set<string>();
  const refDir = nature ? join(ROOT, "art/concept/biomes", kit.style) : join(ROOT, "art/concept/architecture", kit.style, "kit");

  for (const p of kit.pieces ?? []) {
    const id = p.id ?? "?";
    if (ids.has(id)) err(id, "duplicate id");
    ids.add(id);
    if (!id.startsWith(`${kit.prefix}-`)) err(id, `id must start with ${kit.prefix}-`);
    if (!(p.family in BUDGET)) err(id, `unknown family ${p.family}`);
    else if (!(p.tris > 0) || p.tris > BUDGET[p.family]) err(id, `tris ${p.tris} outside 1..${BUDGET[p.family]}`);
    if (!Array.isArray(p.size) || p.size.length !== 3 || p.size.some((v: number) => !(v > 0))) err(id, "size must be [w, h, d] > 0");
    else if (!p.free && !p.size.every((v: number) => onGrid(v, base))) err(id, `size ${p.size} not on the ${base} m grid (mark details free: true)`);
    if (!["bottom-left-front", "bottom-center"].includes(p.pivot)) err(id, `pivot ${p.pivot}`);
    for (const v of p.variants ?? []) if (!VARIANTS.has(v)) err(id, `unknown variant ${v}`);
    if (!p.ref?.sheet || !existsSync(join(refDir, `${p.ref.sheet}.png`))) err(id, `ref sheet ${p.ref?.sheet} missing`);
    for (const s of p.sockets ?? []) if (!SOCKETS.has(s.diameter)) err(id, `socket ${s.name} diameter ${s.diameter}`);
    if (p.radius !== undefined && RADII[kit.style] && !RADII[kit.style].includes(p.radius)) err(id, `radius ${p.radius} not in ${RADII[kit.style]}`);
  }
  // Openings must accept inserts that exist
  for (const p of kit.pieces ?? [])
    for (const o of [p.opening, ...(p.openings ?? [])].filter(Boolean))
      if (o.accepts && ![...ids].some((i) => i.startsWith(o.accepts) && i !== p.id)) err(p.id, `no insert matches ${o.accepts}`);
  // Prefabs may only use pieces from this kit
  for (const f of kit.prefabs ?? []) {
    if (!f.id?.startsWith(`${kit.prefix}-`)) err(f.id ?? "prefab", `prefab id must start with ${kit.prefix}-`);
    for (const { id, count } of f.pieces ?? []) {
      if (!ids.has(id)) err(f.id, `unknown piece ${id}`);
      if (!(count >= 1)) err(f.id, `count for ${id} must be ≥ 1`);
    }
  }

  const rel = file.replace(`${ROOT}/`, "");
  if (errors.length) {
    failed++;
    console.log(`✗ ${rel} (${kit.pieces?.length ?? 0} pieces)\n  ${errors.join("\n  ")}`);
  } else console.log(`✓ ${rel} (${kit.pieces.length} pieces)`);
}
process.exit(failed ? 1 : 0);
