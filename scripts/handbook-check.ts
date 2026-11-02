// Fail when the handbook site has fallen behind the concept docs, the world file, the art or the demos.
// Usage: bun scripts/handbook-check.ts [--site dist/site/game0]
//   Without --site it checks the sources the site is built from; `bun run build` runs it before building.
//   With --site it also checks the built pages; `bun run build` runs that after building, before anything deploys.
// Everything is discovered by scanning folders, so a new style, biome, doc, demo or sheet is caught without editing this file.
import { readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, relative } from "node:path";
import { parseBiomes, foliageUse, type BiomeDoc } from "../apps/web/src/data/biomes-doc";
import { chapters, excludedDocs } from "../apps/web/src/data/chapters.mjs";
import { archStyles } from "../apps/web/src/data/architecture";
import { plateJobs, readManifest, staleness, ROOT } from "./handbook-sheets";

const siteArg = process.argv.indexOf("--site");
const SITE = siteArg > 0 ? join(ROOT, process.argv[siteArg + 1] ?? "dist/site/game0") : undefined;

const problems: { check: string; msg: string }[] = [];
const checks: string[] = [];
let current = "";
const check = async (name: string, fn: () => unknown) => {
  current = name;
  checks.push(name);
  try { await fn(); } catch (e) { problem(`could not run: ${(e as Error).message}`); }
};
const problem = (msg: string) => problems.push({ check: current, msg });

const at = (p: string) => join(ROOT, p);
const dirs = async (dir: string) =>
  (await readdir(at(dir), { withFileTypes: true }).catch(() => [])).filter((d) => d.isDirectory() && !d.name.startsWith(".")).map((d) => d.name).sort();
const files = async (dir: string, ext: string) => (await readdir(at(dir)).catch(() => [])).filter((f) => f.endsWith(ext)).sort();
const walk = async (dir: string, ext: string): Promise<string[]> => {
  const out: string[] = [];
  for (const e of await readdir(at(dir), { withFileTypes: true }).catch(() => [])) {
    const p = `${dir}/${e.name}`;
    if (e.isDirectory()) out.push(...(await walk(p, ext)));
    else if (e.name.endsWith(ext)) out.push(p);
  }
  return out;
};

const world = await Bun.file(at("worlds/first-shard.world.json")).json() as { isles: { name: string; biome: string }[] };
let biomes: BiomeDoc[] = [];

await check("Biomes: concept/art-direction/biomes.md parses and matches the world file and concept art", async () => {
  biomes = parseBiomes(await Bun.file(at("concept/art-direction/biomes.md")).text());
  const ids = new Set(biomes.map((b) => b.id));
  for (const id of new Set(world.isles.map((i) => i.biome)))
    if (!ids.has(id)) problem(`world biome "${id}" (worlds/first-shard.world.json) has no "### ${id}" section in concept/art-direction/biomes.md`);
  for (const b of biomes) {
    if (!world.isles.some((i) => i.biome === b.id)) problem(`biome "${b.id}" in biomes.md has no isles in worlds/first-shard.world.json`);
    for (const name of b.isles) {
      const isle = world.isles.find((i) => i.name === name);
      if (!isle) problem(`biomes.md lists isle "${name}" under ${b.name}, but the world file has no such isle`);
      else if (isle.biome !== b.id) problem(`biomes.md lists "${name}" under ${b.name}, but the world file says it is ${isle.biome}`);
    }
  }
  for (const isle of world.isles)
    if (ids.has(isle.biome) && !biomes.find((b) => b.id === isle.biome)!.isles.includes(isle.name))
      problem(`isle "${isle.name}" (${isle.biome} in the world file) is missing from the ${isle.biome} isle list in biomes.md`);
  for (const folder of await dirs("art/concept/biomes"))
    if (!ids.has(folder)) problem(`art/concept/biomes/${folder}/ is not a biome in biomes.md, so the site never shows it`);
  for (const b of biomes) if (!(await files(`art/concept/biomes/${b.id}`, ".png")).length) problem(`biome "${b.id}" has no concept sheets in art/concept/biomes/${b.id}/`);
});

await check("Kits: every architecture and nature kit.json is shown by a catalogue", async () => {
  const styles = new Set(archStyles.map((a) => a.id));
  for (const style of await dirs("art/models/architecture"))
    if (existsSync(at(`art/models/architecture/${style}/kit.json`)) && !styles.has(style))
      problem(`art/models/architecture/${style}/kit.json has no entry in apps/web/src/data/architecture.ts`);
  for (const style of await dirs("art/concept/architecture"))
    if (!styles.has(style)) problem(`art/concept/architecture/${style}/ has no entry in apps/web/src/data/architecture.ts`);
  for (const a of archStyles) {
    if (!existsSync(at(`art/models/architecture/${a.id}/kit.json`))) problem(`architecture.ts style "${a.id}" has no art/models/architecture/${a.id}/kit.json`);
    // Every concept and kit sheet in art/ is listed (so it is shown), and every listed sheet exists
    const listed = new Map([...a.concept.map((s) => [s.id, `art/concept/architecture/${a.id}/${s.id}.png`]), ...a.kitSheets.map((s) => [s.id, `art/concept/architecture/${a.id}/kit/${s.id}.png`])] as [string, string][]);
    for (const f of await files(`art/concept/architecture/${a.id}`, ".png")) if (!listed.has(f.replace(".png", ""))) problem(`art/concept/architecture/${a.id}/${f} is not listed in architecture.ts "${a.id}".concept`);
    for (const f of await files(`art/concept/architecture/${a.id}/kit`, ".png")) if (!listed.has(f.replace(".png", ""))) problem(`art/concept/architecture/${a.id}/kit/${f} is not listed in architecture.ts "${a.id}".kitSheets`);
    for (const [id, src] of listed) if (!existsSync(at(src))) problem(`architecture.ts "${a.id}" lists sheet "${id}", but ${src} does not exist`);
    for (const b of a.biomes) if (biomes.length && !biomes.some((x) => x.id === b)) problem(`architecture.ts "${a.id}" is built in unknown biome "${b}"`);
  }
  const ids = new Set(biomes.map((b) => b.id));
  if (!ids.size) return; // biomes.md did not parse; reported above
  for (const biome of await dirs("art/models/nature"))
    if (existsSync(at(`art/models/nature/${biome}/kit.json`)) && !ids.has(biome))
      problem(`art/models/nature/${biome}/kit.json has no "### ${biome}" biome in biomes.md, so no biome page shows it`);
});

await check("Kits: every kit manifest validates (scripts/kit/validate.ts)", async () => {
  const run = Bun.spawnSync(["bun", "scripts/kit/validate.ts"], { cwd: ROOT, stdout: "pipe", stderr: "pipe" });
  if (run.exitCode !== 0) {
    const out = `${run.stdout.toString()}${run.stderr.toString()}`.split("\n").filter((l) => l.trim() && !/\bok\b/i.test(l));
    problem(`bun scripts/kit/validate.ts failed:\n      ${out.slice(0, 30).join("\n      ")}`);
  }
});

await check("Chapters: every concept/ doc is a handbook chapter or excluded with a reason", async () => {
  const docs = (await walk("concept", ".md")).map((p) => relative("concept", p)).sort();
  const inChapters = new Map(chapters.flatMap((c) => c.docs.map((d) => [d, c.slug])));
  for (const d of docs)
    if (!inChapters.has(d) && !(d in excludedDocs))
      problem(`concept/${d} is in no chapter: add it to a chapter's docs in apps/web/src/data/chapters.mjs, or to excludedDocs there with a reason`);
  for (const [d, slug] of inChapters) if (!docs.includes(d)) problem(`chapter "${slug}" renders concept/${d}, which does not exist`);
  for (const [d, why] of Object.entries(excludedDocs)) {
    if (!docs.includes(d)) problem(`excludedDocs lists concept/${d}, which does not exist`);
    if (inChapters.has(d)) problem(`concept/${d} is both a chapter doc and excluded`);
    if (!String(why).trim()) problem(`excludedDocs entry concept/${d} gives no reason`);
  }
});

await check("Demos: every demos/<name>/demo.json is built and listed in the workshop", async () => {
  for (const name of await dirs("demos")) {
    const meta = at(`demos/${name}/demo.json`), pkg = at(`demos/${name}/package.json`);
    if (existsSync(meta)) {
      const d = await Bun.file(meta).json();
      if (typeof d.title !== "string" || !d.title.trim() || typeof d.summary !== "string" || !d.summary.trim()) problem(`demos/${name}/demo.json needs a title and a summary`);
      if (!existsSync(pkg)) problem(`demos/${name} has a demo.json but no package.json, so scripts/build-pages.ts never builds it and its workshop link is dead`);
    } else if (existsSync(pkg)) problem(`demos/${name} is built and deployed but has no demo.json, so the workshop never lists it`);
  }
});

await check("Plates: every source sheet has a plate that is up to date, and no plate is orphaned", async () => {
  const jobs = await plateJobs();
  const manifest = await readManifest();
  for (const j of jobs) {
    const why = await staleness(j, manifest);
    if (why) problem(`${j.to} is ${why === "missing" ? "missing" : `stale (${why})`}; source ${j.from}. Run bun run art:sheets`);
  }
  const made = new Set(jobs.map((j) => j.to));
  for (const kind of ["architecture", "biomes", "foliage", "sheets"])
    for (const f of await files(`art/handbook/${kind}`, ".webp"))
      if (!made.has(`art/handbook/${kind}/${f}`)) problem(`art/handbook/${kind}/${f} has no source sheet any more (renamed or deleted?): delete the plate or restore the source`);
});

await check("Foliage: every leaf card a nature kit script uses exists", async () => {
  const scripts = Object.fromEntries(await Promise.all((await files("scripts/kit", ".py")).filter((f) => f.startsWith("nature-")).map(async (f) => [f, await Bun.file(at(`scripts/kit/${f}`)).text()])));
  for (const [leaf, users] of foliageUse(scripts))
    if (!existsSync(at(`art/textures/foliage/${leaf}.png`))) problem(`art/textures/foliage/${leaf}.png is used by ${[...users].join(", ")} but does not exist`);
});

if (SITE) {
  const page = async (p: string) => { const f = Bun.file(join(SITE, p, "index.html")); return (await f.exists()) ? await f.text() : undefined; };
  await check(`Site: the built pages in ${relative(ROOT, SITE)} show every chapter, catalogue entry, kit, plate and demo`, async () => {
    if (!existsSync(SITE)) return problem(`${relative(ROOT, SITE)} does not exist; build first`);
    for (const c of chapters) if (!(await page(c.slug))) problem(`chapter page /${c.slug}/ was not built`);
    for (const a of archStyles) {
      const html = await page(`catalogue/architecture/${a.id}`);
      if (!html) problem(`architecture page /catalogue/architecture/${a.id}/ was not built`);
    }
    for (const b of biomes) {
      const html = await page(`catalogue/biomes/${b.id}`);
      if (!html) { problem(`biome page /catalogue/biomes/${b.id}/ was not built`); continue; }
      for (const field of [b.mood, b.ground, b.signature]) {
        const words = field.replace(/[^\w\s]/g, " ").split(/\s+/).filter(Boolean).slice(0, 6).join(" ");
        if (!html.replace(/<[^>]+>/g, " ").replace(/&#39;|&[a-z]+;/g, " ").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").includes(words)) problem(`/catalogue/biomes/${b.id}/ does not show the doc's text "${words}…"`);
      }
      if (existsSync(at(`art/models/nature/${b.id}/kit.json`)) && !html.includes('id="nature-kit"')) problem(`/catalogue/biomes/${b.id}/ has no nature kit section`);
    }
    // Every plate made from a source sheet appears in some built page (Astro keeps the file stem in the hashed name)
    const html = (await walk(relative(ROOT, SITE), ".html")).filter((p) => !p.includes("/demos/"));
    const all = (await Promise.all(html.map((p) => Bun.file(at(p)).text()))).join("\n");
    for (const j of await plateJobs()) {
      const stem = j.to.split("/").pop()!.replace(".webp", "");
      if (!new RegExp(`/${stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\.[\\w-]+\\.webp`).test(all)) problem(`plate ${j.to} is not shown on any page`);
    }
    const workshop = (await page("workshop")) ?? "";
    for (const name of await dirs("demos")) {
      if (!existsSync(at(`demos/${name}/demo.json`))) continue;
      if (!workshop.includes(`/demos/${name}/`)) problem(`the workshop page does not link demos/${name}`);
      if (!existsSync(join(SITE, "demos", name, "index.html"))) problem(`demo ${name} was not built into ${relative(ROOT, SITE)}/demos/${name}/`);
    }
  });
}

for (const c of checks) {
  const mine = problems.filter((p) => p.check === c);
  console.log(`${mine.length ? "✗" : "✓"} ${c}`);
  for (const p of mine) console.log(`    - ${p.msg}`);
}
if (problems.length) {
  console.error(`\nhandbook check failed: ${problems.length} problem(s). The site has drifted from its sources; fix them before deploying.`);
  process.exit(1);
}
console.log("\nhandbook check passed");
