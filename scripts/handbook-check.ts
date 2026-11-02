// Fail when the handbook site has fallen behind the concept docs, the world file, the art or the demos.
// Usage: bun scripts/handbook-check.ts [--site dist/site/game0]
//   Without --site it checks the sources the site is built from; `bun run build` runs it before building.
//   With --site it also checks the built pages; `bun run build` runs that after building, before anything deploys.
// Everything is discovered by scanning folders, so a new style, biome, doc, entry, demo or sheet is caught without editing this file.
import { readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, relative } from "node:path";
import { parseBiomes, foliageUse, type BiomeDoc } from "../apps/web/src/data/biomes-doc";
import { chapters, excludedDocs } from "../apps/web/src/data/chapters.mjs";
import { entryPage, loadConcept, type Concept } from "../apps/web/src/lib/concept";
import { readConceptFiles } from "../apps/web/src/lib/concept-files";
import { plateJobs, readManifest, staleness, ROOT } from "./handbook-sheets";
import { artStatus, STAGES, type EntryRef } from "../apps/web/src/lib/art-status";

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

const world = await Bun.file(at("worlds/first-shard.world.json")).json() as { isles: { id: string; name: string; biome: string }[]; winds: { id: string; name: string }[] };
let biomes: BiomeDoc[] = [];
// Every catalogue entry, from concept/entries/ and concept/glossary.md (undefined when they don't load; reported below)
const conceptFiles = readConceptFiles(ROOT);
let concept: Concept | undefined;
const archStyles = () => concept?.archStyles ?? [];

await check("Entries: every concept/entries/<kind>/<id>.md and concept/glossary.md loads, and every isle and wind has an entry", async () => {
  try { concept = loadConcept(conceptFiles, world, chapters); } catch (e) { return problem((e as Error).message); }
  const isles = new Set(concept.isleNotes.map((n) => n.id)), winds = new Set(concept.windNotes.map((n) => n.id));
  for (const i of world.isles) if (!isles.has(i.id)) problem(`isle "${i.name}" (worlds/first-shard.world.json) has no concept/entries/isles/${i.id}.md, so its page has no text`);
  for (const w of world.winds) if (!winds.has(w.id)) problem(`wind "${w.name}" (worlds/first-shard.world.json) has no concept/entries/winds/${w.id}.md, so its page has no text`);
});

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
  const styles = new Set(archStyles().map((a) => a.id));
  for (const style of await dirs("art/models/architecture"))
    if (existsSync(at(`art/models/architecture/${style}/kit.json`)) && !styles.has(style))
      problem(`art/models/architecture/${style}/kit.json has no concept/entries/architecture/${style}.md`);
  for (const style of await dirs("art/concept/architecture"))
    if (!styles.has(style)) problem(`art/concept/architecture/${style}/ has no concept/entries/architecture/${style}.md`);
  for (const a of archStyles()) {
    const entry = `concept/entries/architecture/${a.id}.md`;
    if (!existsSync(at(`art/models/architecture/${a.id}/kit.json`))) problem(`${entry} has no art/models/architecture/${a.id}/kit.json`);
    // Every concept and kit sheet in art/ is listed (so it is shown), and every listed sheet exists
    const listed = new Map([...a.concept.map((s) => [s.id, `art/concept/architecture/${a.id}/${s.id}.png`]), ...a.kitSheets.map((s) => [s.id, `art/kit/architecture/${a.id}/${s.id}.png`])] as [string, string][]);
    for (const f of await files(`art/concept/architecture/${a.id}`, ".png")) if (!listed.has(f.replace(".png", ""))) problem(`art/concept/architecture/${a.id}/${f} is not listed under "concept" in ${entry}`);
    for (const f of await files(`art/kit/architecture/${a.id}`, ".png")) if (!listed.has(f.replace(".png", ""))) problem(`art/kit/architecture/${a.id}/${f} is not listed under "kitSheets" in ${entry}`);
    for (const [id, src] of listed) if (!existsSync(at(src))) problem(`${entry} lists sheet "${id}", but ${src} does not exist`);
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

await check("Chapters: every concept/ doc (outside concept/entries/) is a handbook chapter or excluded with a reason", async () => {
  const docs = (await walk("concept", ".md")).map((p) => relative("concept", p)).filter((d) => !d.startsWith("entries/")).sort();
  const inChapters = new Map(chapters.flatMap((c) => c.docs.map((d) => [d, c.slug])));
  for (const d of docs)
    if (!inChapters.has(d) && !(d in excludedDocs))
      problem(`concept/${d} is in no chapter: list it under "chapter: docs:" in the frontmatter of a chapter's first doc, give it its own "chapter:" frontmatter, or add it to excludedDocs in apps/web/src/data/chapters.mjs with a reason`);
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
  for (const kind of await dirs("art/handbook"))
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
    // Every entry file has a built page that shows its text, and every glossary term is on the glossary page
    const flat = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&#39;|&#x27;|&[a-z]+;|&#\d+;/g, " ").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ");
    const opening = (text: string) => text.replace(/[^\w\s]/g, " ").split(/\s+/).filter(Boolean).slice(0, 6).join(" ");
    const shown: Record<string, (id: string) => string | undefined> = {
      peoples: (id) => concept?.peopleEntries.find((x) => x.id === id)?.culture, skills: (id) => concept?.skills.find((x) => x.id === id)?.description,
      materials: (id) => concept?.materials.find((x) => x.id === id)?.description, ships: (id) => concept?.ships.find((x) => x.id === id)?.description,
      bestiary: (id) => concept?.bestiary.find((x) => x.id === id)?.lore, isles: (id) => concept?.isleNotes.find((x) => x.id === id)?.blurb,
      winds: (id) => concept?.windNotes.find((x) => x.id === id)?.blurb, architecture: (id) => concept?.archStyles.find((x) => x.id === id)?.summary,
    };
    for (const path of Object.keys(conceptFiles).filter((p) => p.startsWith("entries/")).sort()) {
      const where = entryPage(path)!;
      const html = await page(`catalogue/${where}`);
      if (!html) { problem(`concept/${path} has no built page /catalogue/${where}/`); continue; }
      const [kind, id] = [path.split("/")[1], path.split("/")[2].replace(/\.md$/, "")];
      const text = shown[kind]?.(id);
      if (text && !flat(html).includes(opening(text))) problem(`/catalogue/${where}/ does not show the text of concept/${path} ("${opening(text)}…")`);
    }
    const glossaryPage = flat((await page("catalogue/glossary")) ?? "");
    for (const t of concept?.glossary ?? []) if (!glossaryPage.includes(opening(t.definition))) problem(`the glossary page does not show "${t.term}" from concept/glossary.md`);
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

// Art pipeline gaps are warnings, not failures: an entry may be published before all its art exists
if (concept) {
  const refs: EntryRef[] = [
    ...concept.bestiary.map((b) => ({ kind: "bestiary", id: b.id, bodyPlan: b.bodyPlan })),
    ...concept.peopleEntries.map((p) => ({ kind: "peoples", id: p.id })),
    ...concept.ships.map((s) => ({ kind: "ships", id: s.id })),
    ...concept.archStyles.map((a) => ({ kind: "architecture", id: a.id })),
    ...concept.materials.map((m) => ({ kind: "materials", id: m.id, family: m.family })),
    ...concept.skills.map((s) => ({ kind: "skills", id: s.id })),
    ...concept.isleNotes.map((i) => ({ kind: "isles", id: i.id, biome: world.isles.find((w) => w.id === i.id)?.biome })),
    ...concept.windNotes.map((w) => ({ kind: "winds", id: w.id })),
  ];
  const kinds = [...new Set(refs.map((r) => r.kind))];
  const rows = kinds.map((kind) => {
    const list = refs.filter((r) => r.kind === kind).map((r) => artStatus(r, (p) => existsSync(at(p))));
    return { kind, total: list.length, cells: STAGES.slice(1).map((st) => {
      const states = list.map((l) => l.find((x) => x.id === st.id)!.state);
      return states.every((x) => x === "n/a") ? "–" : `${states.filter((x) => x === "done").length}/${list.length}`;
    }) };
  });
  const gaps = rows.reduce((n, r) => n + r.cells.reduce((m, c) => (c === "–" ? m : m + r.total - Number(c.split("/")[0])), 0), 0);
  console.log(`! Art pipeline: ${gaps} missing piece(s) across ${refs.length} entries (warning only; see each entry page's pipeline strip)`);
  console.log(`    ${"kind".padEnd(13)}${STAGES.slice(1).map((s) => s.label.padEnd(12)).join("")}`);
  for (const r of rows) console.log(`    ${r.kind.padEnd(13)}${r.cells.map((c) => c.padEnd(12)).join("")}`);
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
