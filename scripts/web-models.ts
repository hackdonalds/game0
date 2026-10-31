// Compress the models listed in an attachments.json for the web (1k WebP textures, no geometry changes).
// Usage: bun scripts/web-models.ts <attachments.json> <outDir>
import { $ } from "bun";
import { dirname, join } from "node:path";
import { mkdir, stat } from "node:fs/promises";

const [config, outDir] = process.argv.slice(2);
const root = dirname(dirname(config)); // art/models
const cfg = await Bun.file(config).json();
const files = new Set<string>([cfg.base.file, cfg.base.walk].filter(Boolean));
for (const slot of Object.values<any>(cfg.slots)) for (const opt of Object.values<any>(slot.options)) files.add(opt.file);

await Bun.write(join(outDir, "attachments.json"), JSON.stringify(cfg, null, 2));
for (const file of files) {
  const src = join(root, file);
  const out = join(outDir, file);
  const fresh = await stat(out).then((o) => o.mtimeMs > Bun.file(src).lastModified, () => false);
  if (fresh) continue;
  await mkdir(dirname(out), { recursive: true });
  await $`bunx gltf-transform optimize ${src} ${out} --texture-compress webp --texture-size 1024 --simplify false --compress false`.quiet();
  console.log(`${out} ${((await stat(out)).size / 1e6).toFixed(1)} MB`);
}
