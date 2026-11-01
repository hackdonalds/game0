// Compress environment models for the web: meshopt geometry, GPU instancing, materials kept separate
// so pages can find them by name (e.g. Web_Waterfall). UVs are kept for animated shaders.
// Usage: bun scripts/web-environment.ts <outDir> <model.glb ...>
import { $ } from "bun";
import { basename, join } from "node:path";
import { mkdir, stat } from "node:fs/promises";

const GLTF = join(import.meta.dir, "../node_modules/.bin/gltf-transform");
const [outDir, ...files] = process.argv.slice(2);
await mkdir(outDir, { recursive: true });

for (const src of files) {
  const out = join(outDir, basename(src));
  const fresh = await stat(out).then((o) => o.mtimeMs > Bun.file(src).lastModified, () => false);
  if (fresh) continue;
  await $`${GLTF} optimize ${src} ${out} --compress meshopt --palette false --texture-compress false --prune-attributes false`.quiet();
  console.log(`${out} ${((await stat(out)).size / 1e6).toFixed(1)} MB`);
}
