// Generate the art every catalogue entry is missing: painted plates and scenes (concept art), and kit reference sheets.
// Usage: bun run art:handbook [--what plate,scene,kit] [--only kind[,kind]] [--ids id,id] [--force] [--dry-run]
//                             [--max-usd 5] [--concurrency 4]
// Needs OPENAI_API_KEY (see scripts/gen-image.ts). Subjects come from concept/: each chapter doc's `chapter.art`, each
// entry's `art` (plate) and `scene`, and for creatures the body plans of concept/monsters/README.md plus each
// creature's `bodyPlan` and `height`. Kit prompts are built from concept/art-direction/kit-sheets.md.
//   plate  → art/concept/<kind>/<id>.webp          scene → art/concept/<kind>/<id>-scene.webp
//   kit    → art/kit/bestiary/body-plans/<plan>-{body,parts}.png, then art/kit/bestiary/<id>.png (species sheet)
// Paintings are stored as WebP (quality 86) to keep Git LFS small; kit sheets stay PNG. Every image gets a .json
// sidecar logging prompt, refs and cost. Jobs run in stages so a species sheet can reference its body-plan sheets.
// --ids matches entry ids and body plan ids. The run stops starting new jobs once --max-usd is spent.
import { parseArgs } from "node:util";
import { $ } from "bun";
import { mkdir, unlink } from "node:fs/promises";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";
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
    what: { type: "string", default: "plate" }, "dry-run": { type: "boolean", default: false },
    "max-usd": { type: "string", default: "5" },
  },
});

const STYLE_REF = "art/references/world-tree-floating-isle.webp";
const KIT_STYLE_REF = "art/references/style-test-01-market-town.png";
const STYLE = "Style: hand-painted stylized game art, painterly, soft lighting with gentle rim light, softer muted colours with gentle saturation, epic and luminous fantasy, never grim. No text, no labels, no border, no frame.";

const world = await Bun.file(join(ROOT, "worlds/first-shard.world.json")).json();
const concept = loadConcept(readConceptFiles(ROOT), world, chapters);

type Job = { what: "plate" | "scene" | "kit"; stage: number; kind: string; id: string; out: string; prompt: string; aspect: string; quality: string;
  refs?: string[]; kit?: { type: string; figure?: string; title?: string } };
const jobs: Job[] = [];
const out = (kind: string, id: string) => `art/concept/${kind}/${id}`;
const scene = (subject: string) => `In-world scene illustration for a fantasy world handbook: ${subject}. Wide cinematic composition, the subject clearly readable, people and ships at true scale. The world is floating isles above a sea of clouds, with the dark storm far below: there is no ocean, and ships sail through the air, never on water. The first attachment is only a reference for palette and brushwork: do not copy its giant tree, its buildings or its composition, and add no castles, spires or giant trees the scene doesn't ask for. The second attachment is the creature's approved design: keep it exactly. ${STYLE}`;
const plate = (subject: string) => `Plate for an illustrated field guide: ${subject}. Soft vignette fading to warm parchment at the edges. ${STYLE}`;

for (const c of chapters)
  jobs.push({ what: "plate", stage: 0, kind: "chapters", id: c.slug, out: out("chapters", c.slug), aspect: "16:9", quality: "high",
    prompt: `Chapter cover illustration for a fantasy world handbook: ${c.art}. Wide cinematic composition with calm space in the upper third. ${STYLE}` });
for (const p of concept.peopleEntries) jobs.push({ what: "plate", stage: 0, kind: "peoples", id: p.id, out: out("peoples", p.id), aspect: "1:1", quality: "high", prompt: plate(p.art) });
for (const s of concept.ships) jobs.push({ what: "plate", stage: 0, kind: "ships", id: s.id, out: out("ships", s.id), aspect: "1:1", quality: "high", prompt: plate(s.art) });
for (const [kind, list] of [["skills", concept.skills], ["isles", concept.isleNotes], ["materials", concept.materials]] as const)
  for (const e of list) jobs.push({ what: "plate", stage: 0, kind, id: e.id, out: out(kind, e.id), aspect: "1:1", quality: "medium", prompt: plate(e.art) });
for (const b of concept.bestiary)
  jobs.push({ what: "plate", stage: 0, kind: "bestiary", id: b.id, out: out("bestiary", b.id), aspect: "1:1", quality: "high",
    prompt: `Bestiary plate for a fantasy field guide: ${b.art}. The whole creature is in view at a three-quarter angle, set in its habitat, with a soft vignette fading to warm parchment at the edges. ${STYLE}` });


// Scenes: every entry with a `scene` brief, painted to match its plate
for (const b of concept.bestiary) if (b.scene)
  jobs.push({ what: "scene", stage: 1, kind: "bestiary", id: `${b.id}-scene`, out: out("bestiary", `${b.id}-scene`), aspect: "16:9", quality: "high",
    prompt: scene(b.scene), refs: [STYLE_REF, `${out("bestiary", b.id)}.webp`] });

// Kit sheets for creatures: each body plan's base body, then its parts, then one species sheet per creature
const kitOut = (path: string) => `art/kit/bestiary/${path}`;
for (const p of concept.bodyPlans) {
  const members = concept.bestiary.filter((b) => b.bodyPlan === p.id);
  if (!members.length) continue;
  // The base body is scaled per species, so draw it at a typical member's size: the median
  const median = (xs: number[]) => xs.length ? [...xs].sort((a, b) => a - b)[Math.floor((xs.length - 1) / 2)] : 0;
  const tallest = median(members.flatMap((b) => b.height ? [b.height] : []));
  const longest = median(members.flatMap((b) => b.length ? [b.length] : []));
  const size = (b: (typeof members)[number]) => b.length ? `${b.length} m long` : b.height ? `${b.height} m` : "";
  const sizes = members.map((b) => size(b) ? `${b.name} ${size(b)}` : b.name).join(", ");
  jobs.push({ what: "kit", stage: 0, kind: "bestiary", id: p.id, out: kitOut(`body-plans/${p.id}-body`), aspect: "16:9", quality: "high", refs: [KIT_STYLE_REF],
    kit: { type: "body-plan", figure: "1.8", title: `Body plan: ${p.name.toLowerCase()}` },
    prompt: `${p.name} body plan (${p.skeleton}). Sockets: ${p.parts}. One base body shared by ${sizes}${longest ? `; draw it about ${longest} m long` : tallest ? `; draw it about ${tallest} m at the shoulder` : ""}` });
  jobs.push({ what: "kit", stage: 1, kind: "bestiary", id: p.id, out: kitOut(`body-plans/${p.id}-parts`), aspect: "16:9", quality: "high", refs: [KIT_STYLE_REF, `${kitOut(`body-plans/${p.id}-body`)}.png`],
    kit: { type: "body-parts", title: `Body plan parts: ${p.name.toLowerCase()}` },
    prompt: `${p.name} body plan, fitting the base body in the second attachment. Sockets and their parts: ${p.parts}. Include the parts these species need: ${members.map((b) => `${b.name} (${b.art})`).join("; ")}` });
  for (const b of members)
    jobs.push({ what: "kit", stage: 2, kind: "bestiary", id: b.id, out: kitOut(b.id), aspect: "16:9", quality: "high",
      refs: [KIT_STYLE_REF, `${kitOut(`body-plans/${p.id}-body`)}.png`, `${kitOut(`body-plans/${p.id}-parts`)}.png`, `${out("bestiary", b.id)}.webp`],
      kit: { type: "species", figure: "1.8", title: b.name },
      prompt: `${b.name.toUpperCase()}, ${b.art}, built on the ${p.name.toLowerCase()} body plan${b.length ? `; about ${b.length} m long` : b.height ? `; about ${b.height} m at the shoulder` : ""}. Draw the creature alone: none of the scenery in that description${b.storm ? `. It HAS a storm-touched variant, which must be drawn: "${b.storm.name}": ${b.storm.text}` : ". It has no storm-touched variant"}` });
}

const only = values.only?.split(","), ids = values.ids?.split(",");
const todo: Job[] = [];
for (const j of jobs) {
  if (!values.what!.split(",").includes(j.what)) continue;
  if (only && !only.includes(j.kind)) continue;
  if (ids && !ids.includes(j.id.replace(/-scene$/, ""))) continue;
  if (!values.force && (await Bun.file(`${j.out}.${j.what === "kit" ? "png" : "webp"}`).exists())) continue;
  todo.push(j);
}
console.log(`${todo.length} image(s) to generate`);
if (values["dry-run"]) {
  for (const j of todo) console.log(`  [${j.what} stage ${j.stage}] ${j.out}  (${j.kit?.type ?? j.what}, ${j.aspect}, refs: ${(j.refs ?? [STYLE_REF]).join(", ")})\n    ${j.prompt}`);
  process.exit(0);
}

const limit = Number(values.concurrency), maxUsd = Number(values["max-usd"]);
let spent = 0, failed = 0;
for (const stage of [...new Set(todo.map((j) => j.stage))].sort()) {
  const queue = todo.filter((j) => j.stage === stage);
  let next = 0;
  await Promise.all(Array.from({ length: limit }, async () => {
    while (next < queue.length) {
      if (spent >= maxUsd) { console.error(`stopping: $${spent.toFixed(2)} spent, cap is $${maxUsd}`); return; }
      const j = queue[next++];
      try {
        const missing = (j.refs ?? []).filter((r) => !existsSync(r));
        if (missing.length) throw new Error(`missing reference ${missing.join(", ")}`);
        await mkdir(dirname(j.out), { recursive: true });
        const refs = (j.refs ?? [STYLE_REF]).flatMap((r) => ["--ref", r]);
        const kit = j.kit ? ["--kit", j.kit.type, ...(j.kit.figure ? ["--figure", j.kit.figure] : []), ...(j.kit.title ? ["--title", j.kit.title] : [])] : [];
        const res = await $`bun scripts/gen-image.ts ${kit} ${j.prompt} --out ${j.out} ${refs} --aspect ${j.aspect} --quality ${j.quality}`.quiet();
        const cost = Number(res.stdout.toString().match(/cost \$([\d.]+)/)?.[1] ?? 0);
        spent += cost;
        if (j.what !== "kit") {
          await sharp(`${j.out}.png`).webp({ quality: 86, effort: 5 }).toFile(`${j.out}.webp`);
          await unlink(`${j.out}.png`);
        }
        console.log(`✓ ${j.out}  $${cost.toFixed(3)}  (total $${spent.toFixed(2)})`);
      } catch (e) {
        failed++;
        console.error(`✗ ${j.out}: ${(e as { stderr?: Buffer }).stderr?.toString().trim().slice(0, 300) || e}`);
      }
    }
  }));
}
console.log(`spent $${spent.toFixed(2)}`);
if (failed) { console.error(`${failed} failed`); process.exit(1); }
