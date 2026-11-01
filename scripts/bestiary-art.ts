// Generate a painted plate for every bestiary entry that doesn't have one yet.
// Usage: bun run art:bestiary [--only id,id] [--force]
// Needs OPENROUTER_API_KEY. Images go to art/bestiary/<id>.png with a .json prompt sidecar.
import { parseArgs } from "node:util";
import { $ } from "bun";
import { bestiary } from "../apps/web/src/data/bestiary";

const { values } = parseArgs({ options: { only: { type: "string" }, force: { type: "boolean", default: false } } });
const only = values.only?.split(",");
const STYLE_REF = "art/references/world-tree-floating-isle.webp";

const prompt = (subject: string) =>
  `Bestiary plate for a fantasy field guide: ${subject}. The whole creature is in view at a three-quarter angle, set in its habitat, ` +
  `with a soft vignette fading to warm parchment at the edges. No text, no labels, no border, no frame. ` +
  `Style: hand-painted stylized game art, painterly, soft lighting with gentle rim light, softer muted colours with gentle saturation, epic and luminous fantasy, never grim.`;

const todo = [];
for (const c of bestiary) {
  if (only && !only.includes(c.id)) continue;
  if (!values.force && (await Bun.file(`art/bestiary/${c.id}.png`).exists())) continue;
  todo.push(c);
}
console.log(`${todo.length} plate(s) to generate`);

// A few at a time, to stay friendly with rate limits
const CONCURRENCY = 3;
let failed = 0;
for (let i = 0; i < todo.length; i += CONCURRENCY) {
  await Promise.all(todo.slice(i, i + CONCURRENCY).map(async (c) => {
    try {
      await $`bun scripts/gen-image.ts ${prompt(c.art)} --out art/bestiary/${c.id} --ref ${STYLE_REF} --aspect 1:1`.quiet();
      console.log(`✓ ${c.id}`);
    } catch (e) {
      failed++;
      console.error(`✗ ${c.id}: ${(e as { stderr?: Buffer }).stderr?.toString().trim() || e}`);
    }
  }));
}
if (failed) process.exit(1);
