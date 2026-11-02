// Build the Astro site and every demo, then merge them into dist/site/game0 for GitHub Pages.
// The handbook's plates are remade from their sources first, and scripts/handbook-check.ts runs before and after the
// build: if the site has drifted from the concept docs, world, art or demos, the build fails and nothing deploys.
import { $ } from "bun";
import { cp, readdir, rm } from "node:fs/promises";

// Nested under /game0 so `bun run preview` serves the same paths as GitHub Pages
const OUT = "dist/site/game0";
await rm(OUT, { recursive: true, force: true });

await $`bun scripts/handbook-sheets.ts`;
await $`bun scripts/handbook-check.ts`;
await $`bun run --filter @game0/web build`;
await cp("apps/web/dist", OUT, { recursive: true });

for (const name of await readdir("demos")) {
  if (!(await Bun.file(`demos/${name}/package.json`).exists())) continue;
  await $`bun run build`.cwd(`demos/${name}`);
  await cp(`demos/${name}/dist`, `${OUT}/demos/${name}`, { recursive: true });
}
await Bun.write(`${OUT}/.nojekyll`, "");
await $`bun scripts/handbook-check.ts --site ${OUT}`;
console.log(`Pages output ready in ${OUT}`);
