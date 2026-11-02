// Copy the architecture, biome, nature-kit and foliage sheets into the handbook as web-sized WebP plates.
// Usage: bun scripts/handbook-sheets.ts [--force]   (runs as part of `bun run build` and the web dev script)
// Sources → plates:
//   art/concept/architecture/<style>/(kit/)<sheet>.png → art/handbook/architecture/<style>-<sheet>.webp
//   art/models/architecture/<style>/sheet-<s>.png      → art/handbook/architecture/<style>-built-<s>.webp
//   art/concept/biomes/<biome>/<sheet>.png              → art/handbook/biomes/<biome>-<sheet>.webp
//   art/models/nature/<biome>/sheet-<s>.png             → art/handbook/biomes/<biome>-built-<s>.webp
//   art/textures/foliage/<name>.png                     → art/handbook/foliage/<name>.webp (alpha kept)
//   art/concept/<kind>/…/<sheet>.png                    → art/handbook/sheets/<kind>-…-<sheet>.webp (kinds in CONCEPT_KINDS)
// Freshness: art/handbook/plates.json records a hash of each plate's source and settings, so a plate is remade
// whenever its source changes (git checkouts reset mtimes, so mtimes alone cannot be trusted).
// scripts/handbook-check.ts uses plateJobs() and isFresh() to fail the build when a plate lags its source.
import { mkdir, readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { createHash } from "node:crypto";

export const ROOT = join(import.meta.dir, "..");
export const MANIFEST = "art/handbook/plates.json";

export interface PlateJob { from: string; to: string; width: number }

const pngs = async (dir: string) =>
  (await readdir(join(ROOT, dir)).catch(() => [])).filter((f) => f.endsWith(".png")).sort().map((f) => `${dir}/${f}`);
const dirs = async (dir: string) =>
  (await readdir(join(ROOT, dir), { withFileTypes: true }).catch(() => [])).filter((d) => d.isDirectory() && !d.name.startsWith(".")).map((d) => d.name).sort();
const stem = (f: string) => f.split("/").pop()!.replace(/\.png$/, "");
const walkPngs = async (dir: string): Promise<string[]> =>
  [...(await pngs(dir)), ...(await Promise.all((await dirs(dir)).map((d) => walkPngs(`${dir}/${d}`)))).flat()].sort();

/** Concept sheet folders shown on catalogue entries (art/concept/<kind>/…/<sheet>.png → art/handbook/sheets/<kind>-…-<sheet>.webp) */
export const CONCEPT_KINDS = ["ships", "bestiary", "peoples", "materials", "isles", "skills", "winds", "world"];

/** Every plate the handbook should have, discovered by scanning the source folders */
export async function plateJobs(): Promise<PlateJob[]> {
  const jobs: PlateJob[] = [];
  const add = (from: string, to: string, width = 1600) => jobs.push({ from, to, width });
  for (const style of await dirs("art/concept/architecture")) {
    for (const f of [...(await pngs(`art/concept/architecture/${style}`)), ...(await pngs(`art/concept/architecture/${style}/kit`))])
      add(f, `art/handbook/architecture/${style}-${stem(f)}.webp`);
  }
  for (const style of await dirs("art/models/architecture"))
    for (const f of await pngs(`art/models/architecture/${style}`)) if (stem(f).startsWith("sheet-")) add(f, `art/handbook/architecture/${style}-built-${stem(f).replace(/^sheet-/, "")}.webp`);
  for (const biome of await dirs("art/concept/biomes"))
    for (const f of await pngs(`art/concept/biomes/${biome}`)) add(f, `art/handbook/biomes/${biome}-${stem(f)}.webp`);
  for (const biome of await dirs("art/models/nature"))
    for (const f of await pngs(`art/models/nature/${biome}`)) if (stem(f).startsWith("sheet-")) add(f, `art/handbook/biomes/${biome}-built-${stem(f).replace(/^sheet-/, "")}.webp`);
  for (const f of await pngs("art/textures/foliage")) add(f, `art/handbook/foliage/${stem(f)}.webp`, 512);
  for (const kind of CONCEPT_KINDS)
    for (const f of await walkPngs(`art/concept/${kind}`)) add(f, `art/handbook/sheets/${f.slice("art/concept/".length, -4).replaceAll("/", "-")}.webp`);
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
    await sharp(join(ROOT, j.from)).resize({ width: j.width, withoutEnlargement: true }).webp({ quality: 82, effort: 5, alphaQuality: 90 }).toFile(join(ROOT, j.to));
    made++;
  }
  const sorted = Object.fromEntries(Object.entries(next).sort(([a], [b]) => a.localeCompare(b)));
  if (JSON.stringify(sorted) !== JSON.stringify(manifest)) await Bun.write(join(ROOT, MANIFEST), `${JSON.stringify(sorted, null, 2)}\n`);
  console.log(`handbook plates: ${made} of ${jobs.length} written`);
}

if (import.meta.main) await main();
