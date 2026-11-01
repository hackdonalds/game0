// Compress the models listed in each people's attachments.json for the web (1k WebP textures, no geometry changes)
// and write an index of the peoples.
// Usage: bun scripts/web-models.ts <outDir> <art/models/<people>/attachments.json ...>
import { $ } from "bun";
import { basename, dirname, join } from "node:path";
import { mkdir, stat } from "node:fs/promises";

const GLTF = join(import.meta.dir, "../node_modules/.bin/gltf-transform");
const [outDir, ...configs] = process.argv.slice(2);
const peoples: string[] = [];

for (const config of configs) {
  const people = basename(dirname(config));
  const root = dirname(dirname(config)); // art/models
  const cfg = await Bun.file(config).json();
  if (!(await Bun.file(join(root, cfg.base.file)).exists())) {
    console.log(`skip ${people}: ${cfg.base.file} not rigged yet`);
    continue;
  }
  peoples.push(people);
  await Bun.write(join(outDir, people, "attachments.json"), JSON.stringify(cfg, null, 2));

  const files = new Set<string>([cfg.base.file, cfg.base.walk].filter(Boolean));
  for (const slot of Object.values<any>(cfg.slots)) for (const opt of Object.values<any>(slot.options)) files.add(opt.file);
  for (const file of files) {
    const src = join(root, file);
    const out = join(outDir, file);
    const fresh = await stat(out).then((o) => o.mtimeMs > Bun.file(src).lastModified, () => false);
    if (fresh) continue;
    await mkdir(dirname(out), { recursive: true });
    await $`${GLTF} optimize ${src} ${out} --texture-compress webp --texture-size 1024 --simplify false --compress false`.quiet();
    console.log(`${out} ${((await stat(out)).size / 1e6).toFixed(1)} MB`);
  }
}
await Bun.write(join(outDir, "peoples.json"), JSON.stringify(peoples));
