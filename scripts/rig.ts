// Rig a static A-pose humanoid GLB locally with headless Blender, retarget the CC0 Quaternius
// animation library onto it, then optimise it. Writes <out>.clips.json with clip speeds.
// Usage: bun run art:rig <in.glb> <out.glb> [--force]   rig and animate (stops if the body isn't rig-ready)
//        bun run art:rig --check <in.glb>                rig-readiness report only (free, a few seconds)
import { $ } from "bun";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: { check: { type: "boolean", default: false }, force: { type: "boolean", default: false } },
});
const [src, out] = positionals;
if (!src || (!out && !values.check)) throw new Error("Usage: bun run art:rig <in.glb> <out.glb> [--force] | --check <in.glb>");
const blender = process.env.BLENDER ?? "/Applications/Blender.app/Contents/MacOS/Blender";
const work = await mkdtemp(join(tmpdir(), "rig-"));

type Report = { height: number; ok: boolean; issues: { level: "fail" | "warn"; message: string }[] };
await $`${blender} -b --factory-startup -P scripts/rig/autorig.py -- ${src} ${work}/check.blend --check`.quiet();
const report: Report = await Bun.file(`${work}/check.check.json`).json();
console.log(`${src}: ${report.ok ? "rig-ready" : "NOT rig-ready"} (height ${report.height} m)`);
for (const i of report.issues) console.log(`  ${i.level === "fail" ? "✗" : "!"} ${i.message}`);
if (values.check) {
  console.log(`Skeleton preview: blender -b --factory-startup -P scripts/rig/render.py -- ${work}/check.blend <out_dir>`);
  process.exit(report.ok ? 0 : 1);
}
if (!report.ok && !values.force) {
  console.error("Fix the concept or regenerate the model, or rerun with --force to rig anyway.");
  process.exit(1);
}

await $`${blender} -b --factory-startup -P scripts/rig/autorig.py -- ${src} ${work}/rig.blend`.quiet();
await $`${blender} -b --factory-startup -P scripts/rig/retarget.py -- ${work}/rig.blend ${work}/anim.glb ${work}/anim.blend`.quiet();
await Bun.write(out.replace(/\.glb$/, ".clips.json"), Bun.file(`${work}/anim.clips.json`));
await $`bunx gltf-transform optimize ${work}/anim.glb ${out} --compress meshopt --texture-compress webp --texture-size 1024`;
console.log(`Rigged ${src} -> ${out} (debug .blend files in ${work})`);
