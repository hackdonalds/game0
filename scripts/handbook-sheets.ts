// Copy the architecture and biome sheets into the handbook as web-sized WebP plates.
// Usage: bun scripts/handbook-sheets.ts [--force]
// Sources: art/concept/architecture/<style>/(kit/)*.png, art/models/architecture/<style>/sheet-*.png, art/concept/biomes/<biome>/*.png
// Output: art/handbook/architecture/<style>-<sheet>.webp and art/handbook/biomes/<biome>-<sheet>.webp, at most 1600 px wide.
import { readdir } from "node:fs/promises";
import sharp from "sharp";

const force = process.argv.includes("--force");
const pngs = async (dir: string) => (await readdir(dir).catch(() => [])).filter((f) => f.endsWith(".png")).map((f) => `${dir}/${f}`);

const jobs: { from: string; to: string }[] = [];
for (const style of await readdir("art/concept/architecture")) {
  if (style.startsWith(".")) continue;
  const out = (name: string) => `art/handbook/architecture/${style}-${name}.webp`;
  for (const f of await pngs(`art/concept/architecture/${style}`)) jobs.push({ from: f, to: out(f.split("/").pop()!.replace(".png", "")) });
  for (const f of await pngs(`art/concept/architecture/${style}/kit`)) jobs.push({ from: f, to: out(f.split("/").pop()!.replace(".png", "")) });
  for (const f of await pngs(`art/models/architecture/${style}`)) jobs.push({ from: f, to: out(`built-${f.split("/").pop()!.replace(/^sheet-|\.png$/g, "")}`) });
}
for (const biome of await readdir("art/concept/biomes")) {
  if (biome.startsWith(".")) continue;
  for (const f of await pngs(`art/concept/biomes/${biome}`)) jobs.push({ from: f, to: `art/handbook/biomes/${biome}-${f.split("/").pop()!.replace(".png", "")}.webp` });
}

let made = 0;
for (const j of jobs) {
  if (!force && (await Bun.file(j.to).exists())) continue;
  await sharp(j.from).resize({ width: 1600, withoutEnlargement: true }).webp({ quality: 82, effort: 5 }).toFile(j.to);
  made++;
}
console.log(`${made} of ${jobs.length} sheet(s) written`);
