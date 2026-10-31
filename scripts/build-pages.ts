// Build the Astro site and every demo, then merge them into dist/pages for GitHub Pages.
import { $ } from "bun";
import { cp, readdir, rm } from "node:fs/promises";

// Nested under /game0 so `bun run preview` serves the same paths as GitHub Pages
const OUT = "dist/site/game0";
await rm(OUT, { recursive: true, force: true });

await $`bun run --filter @game0/web build`;
await cp("apps/web/dist", OUT, { recursive: true });

for (const name of await readdir("demos")) {
  if (!(await Bun.file(`demos/${name}/package.json`).exists())) continue;
  await $`bun run build`.cwd(`demos/${name}`);
  await cp(`demos/${name}/dist`, `${OUT}/demos/${name}`, { recursive: true });
}
await Bun.write(`${OUT}/.nojekyll`, "");
console.log(`Pages output ready in ${OUT}`);
