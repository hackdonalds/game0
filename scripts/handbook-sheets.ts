// Make every image the handbook shows: web-sized WebP plates in art/handbook/, which is build output (not committed).
// Usage: bun scripts/handbook-sheets.ts [--force]   (runs as part of `bun run build` and the web dev script)
// Sources → plates (art/README.md explains the layers):
//   art/concept/<kind>/<id>.webp                   → art/handbook/<kind>/<id>.webp (painted entry plates, copied as they are;
//                                                    art/concept/drafts/, where art:image saves by default, is skipped)
//   art/{concept,kit}/architecture/<style>/<s>.png → art/handbook/architecture/<style>-<s>.webp
//   art/models/architecture/<style>/sheet-<s>.png  → art/handbook/architecture/<style>-built-<s>.webp
//   art/{concept,kit}/biomes/<biome>/<s>.png       → art/handbook/biomes/<biome>-<s>.webp
//   art/models/nature/<biome>/sheet-<s>.png        → art/handbook/biomes/<biome>-built-<s>.webp
//   art/textures/foliage/<name>.png                → art/handbook/foliage/<name>.webp (alpha kept)
//   art/{concept,kit}/<kind>/…/<sheet>.png         → art/handbook/sheets/<kind>-…-<sheet>.webp (kinds in CONCEPT_KINDS)
// Two sources that would make the same plate are an error. Plates whose source is gone are deleted.
// Freshness: art/handbook/plates.json records a hash of each plate's source and settings, so a plate is remade
// whenever its source changes (checkouts reset mtimes, so mtimes alone cannot be trusted).
// scripts/handbook-check.ts uses plateJobs() and staleness() to fail the build when a plate lags its source.
import { copyFile, mkdir, readdir, stat, unlink } from "node:fs/promises";
import { dirname, join } from "node:path";
import { createHash } from "node:crypto";

export const ROOT = join(import.meta.dir, "..");
export const MANIFEST = "art/handbook/plates.json";

/** width 0 copies the source unchanged (painted entry plates are already web-sized WebP) */
export interface PlateJob { from: string; to: string; width: number }

const ofType = async (dir: string, ext: string) =>
  (await readdir(join(ROOT, dir)).catch(() => [])).filter((f) => f.endsWith(ext)).sort().map((f) => `${dir}/${f}`);
const pngs = (dir: string) => ofType(dir, ".png");
const dirs = async (dir: string) =>
  (await readdir(join(ROOT, dir), { withFileTypes: true }).catch(() => [])).filter((d) => d.isDirectory() && !d.name.startsWith(".")).map((d) => d.name).sort();
const stem = (f: string) => f.split("/").pop()!.replace(/\.(png|webp)$/, "");
const walkPngs = async (dir: string): Promise<string[]> =>
  [...(await pngs(dir)), ...(await Promise.all((await dirs(dir)).map((d) => walkPngs(`${dir}/${d}`)))).flat()].sort();

/** Art layers that hold source sheets: paintings, then kit reference sheets */
const LAYERS = ["concept", "kit"];

/** Sheet folders shown on catalogue entries (art/{concept,kit}/<kind>/…/<sheet>.png → art/handbook/sheets/<kind>-…-<sheet>.webp) */
export const CONCEPT_KINDS = ["ships", "bestiary", "peoples", "materials", "isles", "skills", "winds", "world"];

/** Every plate the handbook should have, discovered by scanning the source folders */
export async function plateJobs(): Promise<PlateJob[]> {
  const jobs: PlateJob[] = [];
  const add = (from: string, to: string, width = 1600) => {
    const clash = jobs.find((j) => j.to === to);
    if (clash) throw new Error(`${from} and ${clash.from} would both make ${to}: rename one`);
    jobs.push({ from, to, width });
  };
  for (const kind of (await dirs("art/concept")).filter((k) => k !== "drafts"))
    for (const f of await ofType(`art/concept/${kind}`, ".webp")) add(f, `art/handbook/${kind}/${stem(f)}.webp`, 0);
  for (const layer of LAYERS)
    for (const style of await dirs(`art/${layer}/architecture`))
      for (const f of await pngs(`art/${layer}/architecture/${style}`)) add(f, `art/handbook/architecture/${style}-${stem(f)}.webp`);
  for (const style of await dirs("art/models/architecture"))
    for (const f of await pngs(`art/models/architecture/${style}`)) if (stem(f).startsWith("sheet-")) add(f, `art/handbook/architecture/${style}-built-${stem(f).replace(/^sheet-/, "")}.webp`);
  for (const layer of LAYERS)
    for (const biome of await dirs(`art/${layer}/biomes`))
      for (const f of await pngs(`art/${layer}/biomes/${biome}`)) add(f, `art/handbook/biomes/${biome}-${stem(f)}.webp`);
  for (const biome of await dirs("art/models/nature"))
    for (const f of await pngs(`art/models/nature/${biome}`)) if (stem(f).startsWith("sheet-")) add(f, `art/handbook/biomes/${biome}-built-${stem(f).replace(/^sheet-/, "")}.webp`);
  for (const f of await pngs("art/textures/foliage")) add(f, `art/handbook/foliage/${stem(f)}.webp`, 512);
  for (const layer of LAYERS)
    for (const kind of CONCEPT_KINDS)
      for (const f of await walkPngs(`art/${layer}/${kind}`)) add(f, `art/handbook/sheets/${f.slice(`art/${layer}/`.length, -4).replaceAll("/", "-")}.webp`);
  return jobs;
}

/** Hash of a job's source bytes and output settings */
export async function jobHash(j: PlateJob) {
  return createHash("sha1").update(new Uint8Array(await Bun.file(join(ROOT, j.from)).arrayBuffer())).update(`:${j.width}`).digest("hex").slice(0, 16);
}

export async function readManifest(): Promise<Record<string, string>> {
  const f = Bun.file(join(ROOT, MANIFEST));
  return (await f.exists()) ? await f.json() : {};
}

/** A plate is fresh when it exists and was made from the current source (by the manifest hash; for plates made before
 *  the manifest existed, by mtime). Returns the reason it is stale, or "" when fresh. */
export async function staleness(j: PlateJob, manifest: Record<string, string>, hash?: string): Promise<string> {
  const out = await stat(join(ROOT, j.to)).catch(() => undefined);
  if (!out) return "missing";
  const recorded = manifest[j.to];
  if (recorded) return recorded === (hash ?? (await jobHash(j))) ? "" : "source changed since the plate was made";
  const src = await stat(join(ROOT, j.from));
  return out.mtimeMs >= src.mtimeMs ? "" : "older than its source";
}

async function main() {
  const sharp = (await import("sharp")).default;
  const force = process.argv.includes("--force");
  const jobs = await plateJobs();
  const manifest = await readManifest();
  const next: Record<string, string> = {};
  let made = 0;
  for (const j of jobs) {
    const hash = await jobHash(j);
    next[j.to] = hash;
    if (!force && !(await staleness(j, manifest, hash))) continue;
    await mkdir(dirname(join(ROOT, j.to)), { recursive: true });
    if (j.width) await sharp(join(ROOT, j.from)).resize({ width: j.width, withoutEnlargement: true }).webp({ quality: 82, effort: 5, alphaQuality: 90 }).toFile(join(ROOT, j.to));
    else await copyFile(join(ROOT, j.from), join(ROOT, j.to));
    made++;
  }
  // Plates whose source was renamed or deleted
  const wanted = new Set(jobs.map((j) => j.to));
  let pruned = 0;
  for (const kind of await dirs("art/handbook"))
    for (const f of await ofType(`art/handbook/${kind}`, ".webp"))
      if (!wanted.has(f)) { await unlink(join(ROOT, f)); pruned++; }
  const sorted = Object.fromEntries(Object.entries(next).sort(([a], [b]) => a.localeCompare(b)));
  if (JSON.stringify(sorted) !== JSON.stringify(manifest)) await Bun.write(join(ROOT, MANIFEST), `${JSON.stringify(sorted, null, 2)}\n`);
  console.log(`handbook plates: ${made} of ${jobs.length} written${pruned ? `, ${pruned} without a source removed` : ""}`);
}

if (import.meta.main) await main();
