// asset-forge runner: runs one headless Blender step from scripts/forge/<step>.py, or a Node-side step,
// and prints the step's JSON result. Blender steps never touch the network and never spend credits.
//
// Usage:
//   bun run art:forge <step> --key value ...      # flags become the step's JSON args
//   bun run art:forge inspect --in art/models/galeborne/base-rigged.glb
//   bun run art:forge web --in out/galeborne.glb   # meshopt + webp copy for three.js (<in>.web.glb)
//   bun run art:forge godot --in out/galeborne.glb # headless Godot import check
//
// Values that parse as JSON (numbers, arrays, objects, true/false) are passed as JSON, everything else as strings.
// BLENDER and GODOT env vars override the default app paths.
import { existsSync } from "node:fs";
import { cp, mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

const BLENDER = process.env.BLENDER ?? "/Applications/Blender.app/Contents/MacOS/Blender";
const GODOT = process.env.GODOT ?? "/Applications/Godot.app/Contents/MacOS/Godot";

const [step, ...rest] = process.argv.slice(2);
if (!step) {
  const steps = (await readdir("scripts/forge")).filter((f) => f.endsWith(".py") && f !== "lib.py").map((f) => f.slice(0, -3));
  console.log(`steps: ${[...steps, "web", "godot"].join(", ")}`);
  process.exit(0);
}

const args: Record<string, unknown> = {};
for (let i = 0; i < rest.length; i++) {
  const key = rest[i].replace(/^--/, "");
  const raw = rest[i + 1] && !rest[i + 1].startsWith("--") ? rest[++i] : "true";
  try { args[key] = JSON.parse(raw); } catch { args[key] = raw; }
}

async function run(cmd: string[]) {
  const proc = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" });
  const [out, err] = await Promise.all([new Response(proc.stdout).text(), new Response(proc.stderr).text()]);
  return { code: await proc.exited, out, err };
}

if (step === "web") {
  // three.js build: meshopt geometry + webp textures. Godot keeps the plain GLB. Unused attributes are kept
  // (TEXCOORD_1 carries body regions) and the node graph is left alone (sockets, gear meshes, skeleton).
  const input = String(args.in);
  const output = String(args.out ?? input.replace(/\.glb$/, ".web.glb"));
  const { code, out, err } = await run(["bunx", "gltf-transform", "optimize", input, output, "--compress", "meshopt", "--texture-compress", "webp", "--simplify", "false",
    "--prune-attributes", "false", "--flatten", "false", "--join", "false", "--palette", "false", "--instance", "false"]);
  console.log(JSON.stringify({ ok: code === 0, out: output, log: (code ? err || out : "").slice(-2000) }));
  process.exit(code);
}

if (step === "godot") {
  // Import the GLB into a throwaway Godot project and report importer errors.
  const input = String(args.in);
  const dir = await mkdtemp(join(tmpdir(), "forge-godot-"));
  await writeFile(join(dir, "project.godot"), 'config_version=5\n[application]\nconfig/name="forge-check"\n');
  await cp(input, join(dir, basename(input)));
  for (const extra of [".dye.png"]) {
    const side = input.replace(/\.glb$/, extra);
    if (existsSync(side)) await cp(side, join(dir, basename(side)));
  }
  const { code, out, err } = await run([GODOT, "--headless", "--path", dir, "--import", "--quit"]);
  const log = `${out}\n${err}`;
  const errors = log.split("\n").filter((l) => /ERROR|SCRIPT ERROR|Failed/i.test(l));
  const imported = existsSync(join(dir, ".godot", "imported"));
  await rm(dir, { recursive: true, force: true });
  console.log(JSON.stringify({ ok: code === 0 && errors.length === 0 && imported, errors: errors.slice(0, 20) }));
  process.exit(errors.length ? 1 : code);
}

const script = `scripts/forge/${step}.py`;
if (!existsSync(script)) throw new Error(`unknown step ${step}`);
const { code, out, err } = await run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", script, "--", JSON.stringify(args)]);
const line = out.split("\n").find((l) => l.startsWith("FORGE_RESULT "));
if (!line) {
  console.error(`${step} crashed (exit ${code})\n${(err || out).split("\n").slice(-40).join("\n")}`);
  process.exit(1);
}
console.log(JSON.stringify(JSON.parse(line.slice(13)), null, 2));
process.exit(code);
