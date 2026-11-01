// Ship forge assets to a web demo: a meshopt + webp copy of every family asset (bodies, gear, clip libraries,
// props) with its dye mask, and a manifest the three.js runtime reads.
// Usage: bun scripts/web-forge.ts <outDir> [family ...]   (default family: humanoid)
import { $ } from "bun";
import { Glob } from "bun";
import { mkdir, stat } from "node:fs/promises";
import { dirname, join, relative } from "node:path";

const ROOT = join(import.meta.dir, "..");
const GLTF = join(ROOT, "node_modules/.bin/gltf-transform");
const [outDir, ...families] = process.argv.slice(2);
if (!outDir) throw new Error("usage: bun scripts/web-forge.ts <outDir> [family ...]");

async function ship(src: string, out: string) {
  const fresh = await stat(out).then((o) => o.mtimeMs > Bun.file(src).lastModified, () => false);
  if (!fresh) {
    await mkdir(dirname(out), { recursive: true });
    // Same flags as `art:forge web`: keep TEXCOORD_1 (body regions), sockets, gear meshes and the skeleton
    await $`${GLTF} optimize ${src} ${out} --compress meshopt --texture-compress webp --texture-size 1024 --simplify false --prune-attributes false --flatten false --join false --palette false --instance false`.quiet();
    console.log(`${relative(ROOT, out)} ${((await stat(out)).size / 1e6).toFixed(2)} MB`);
  }
  const dye = src.replace(/\.glb$/, ".dye.png");
  if (await Bun.file(dye).exists()) await Bun.write(out.replace(/\.glb$/, ".dye.png"), Bun.file(dye));
  return (await Bun.file(dye).exists()) ? relative(outDir, out.replace(/\.glb$/, ".dye.png")) : undefined;
}

const manifest: Record<string, unknown> = {};
for (const family of families.length ? families : ["humanoid"]) {
  const dir = join(ROOT, "art/families", family);
  const contract = await Bun.file(join(dir, "contract.json")).json();
  const entry: any = { contract, peoples: {}, gear: [], anims: [] };
  for await (const f of new Glob("peoples/*.body.glb").scan(dir)) {
    const id = f.split("/")[1].replace(".body.glb", "");
    const out = join(outDir, family, f);
    await ship(join(dir, f), out);
    entry.peoples[id] = { file: relative(outDir, out), rest: await Bun.file(join(dir, `peoples/${id}.rest.json`)).json().catch(() => null) };
  }
  for await (const f of new Glob("gear/*/*.glb").scan(dir)) {
    const out = join(outDir, family, f);
    const dye = await ship(join(dir, f), out);
    const part = await Bun.file(join(dir, f.replace(/\.glb$/, ".part.json"))).json();
    // Body mask: the body faces this piece hides, in the shared body UV space
    const maskSrc = join(dir, f.replace(/\.glb$/, ".mask.png"));
    const mask = (await Bun.file(maskSrc).exists()) ? out.replace(/\.glb$/, ".mask.png") : undefined;
    if (mask) await Bun.write(mask, Bun.file(maskSrc));
    entry.gear.push({ id: f.split("/")[2].replace(".glb", ""), slot: f.split("/")[1], file: relative(outDir, out), dye, mask: mask && relative(outDir, mask), part });
  }
  for await (const f of new Glob("anims/*.glb").scan(dir)) {
    const out = join(outDir, family, f);
    await ship(join(dir, f), out);
    entry.anims.push({ id: f.split("/")[1].replace(".glb", ""), file: relative(outDir, out) });
  }
  manifest[family] = entry;
}
const props: any[] = [];
const rigid = join(ROOT, "art/families/rigid");
for await (const f of new Glob("prop/*.glb").scan(rigid)) {
  const out = join(outDir, "rigid", f);
  const dye = await ship(join(rigid, f), out);
  props.push({ id: f.split("/")[1].replace(".glb", ""), file: relative(outDir, out), dye });
}
manifest.props = props;
await Bun.write(join(outDir, "forge.json"), JSON.stringify(manifest, null, 2));
console.log(`wrote ${relative(ROOT, join(outDir, "forge.json"))}`);
