// Generate painted plates for every handbook entry that doesn't have one yet: chapter covers and catalogue entries.
// Usage: bun run art:handbook [--only kind[,kind]] [--ids id,id] [--force] [--concurrency 4]
// Needs OPENROUTER_API_KEY. Subjects are the `art:` briefs in concept/: each chapter doc's `chapter.art` and each
// concept/entries/<kind>/<id>.md's `art`. Output: art/concept/<kind>/<id>.webp, with a .json sidecar that logs what
// was generated. Plates are stored as WebP (quality 86) to keep Git LFS small; the generated PNG is converted and removed.
import { parseArgs } from "node:util";
import { $ } from "bun";
import { mkdir, unlink } from "node:fs/promises";
import { join } from "node:path";
import sharp from "sharp";
import { loadConcept } from "../apps/web/src/lib/concept";
import { readConceptFiles } from "../apps/web/src/lib/concept-files";
import { chapters } from "../apps/web/src/data/chapters.mjs";

const ROOT = join(import.meta.dir, "..");
process.chdir(ROOT);

const { values } = parseArgs({
  options: {
    only: { type: "string" }, ids: { type: "string" }, force: { type: "boolean", default: false },
    concurrency: { type: "string", default: "4" },
  },
});

const STYLE_REF = "art/references/world-tree-floating-isle.webp";
const STYLE = "Style: hand-painted stylized game art, painterly, soft lighting with gentle rim light, softer muted colours with gentle saturation, epic and luminous fantasy, never grim. No text, no labels, no border, no frame.";

const world = await Bun.file(join(ROOT, "worlds/first-shard.world.json")).json();
const concept = loadConcept(readConceptFiles(ROOT), world, chapters);

type Job = { kind: string; id: string; out: string; prompt: string; aspect: string; quality: string };
const jobs: Job[] = [];
const out = (kind: string, id: string) => `art/concept/${kind}/${id}`;
const plate = (subject: string) => `Plate for an illustrated field guide: ${subject}. Soft vignette fading to warm parchment at the edges. ${STYLE}`;

for (const c of chapters)
  jobs.push({ kind: "chapters", id: c.slug, out: out("chapters", c.slug), aspect: "16:9", quality: "high",
    prompt: `Chapter cover illustration for a fantasy world handbook: ${c.art}. Wide cinematic composition with calm space in the upper third. ${STYLE}` });
for (const p of concept.peopleEntries) jobs.push({ kind: "peoples", id: p.id, out: out("peoples", p.id), aspect: "1:1", quality: "high", prompt: plate(p.art) });
for (const s of concept.ships) jobs.push({ kind: "ships", id: s.id, out: out("ships", s.id), aspect: "1:1", quality: "high", prompt: plate(s.art) });
for (const [kind, list] of [["skills", concept.skills], ["isles", concept.isleNotes], ["materials", concept.materials]] as const)
  for (const e of list) jobs.push({ kind, id: e.id, out: out(kind, e.id), aspect: "1:1", quality: "medium", prompt: plate(e.art) });
for (const b of concept.bestiary)
  jobs.push({ kind: "bestiary", id: b.id, out: out("bestiary", b.id), aspect: "1:1", quality: "high",
    prompt: `Bestiary plate for a fantasy field guide: ${b.art}. The whole creature is in view at a three-quarter angle, set in its habitat, with a soft vignette fading to warm parchment at the edges. ${STYLE}` });

const only = values.only?.split(","), ids = values.ids?.split(",");
const todo: Job[] = [];
for (const j of jobs) {
  if (only && !only.includes(j.kind)) continue;
  if (ids && !ids.includes(j.id)) continue;
  if (!values.force && (await Bun.file(`${j.out}.webp`).exists())) continue;
  todo.push(j);
}
console.log(`${todo.length} plate(s) to generate`);

const limit = Number(values.concurrency);
let next = 0, failed = 0;
await Promise.all(Array.from({ length: limit }, async () => {
  while (next < todo.length) {
    const j = todo[next++];
    try {
      await mkdir(`art/concept/${j.kind}`, { recursive: true });
      await $`bun scripts/gen-image.ts ${j.prompt} --out ${j.out} --ref ${STYLE_REF} --aspect ${j.aspect} --quality ${j.quality}`.quiet();
      await sharp(`${j.out}.png`).webp({ quality: 86, effort: 5 }).toFile(`${j.out}.webp`);
      await unlink(`${j.out}.png`);
      console.log(`✓ ${j.kind}/${j.id}`);
    } catch (e) {
      failed++;
      console.error(`✗ ${j.kind}/${j.id}: ${(e as { stderr?: Buffer }).stderr?.toString().trim().slice(0, 300) || e}`);
    }
  }
}));
if (failed) { console.error(`${failed} failed`); process.exit(1); }
