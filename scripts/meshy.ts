// Meshy API pipeline: generate, retexture and rig models, saving GLBs into the repo with a task sidecar
// and an entry in the credit ledger. Paid commands print their cost and need --yes to run.
//
// Usage:
//   bun run art:3d model <out> <front.png> [side.png back.png] [options]   # image or multi-image to 3D
//   bun run art:3d retexture <out> --task <id> (--style-image <png> | --style "<prompt>") [--yes]
//   bun run art:3d rig <out> --task <id> [--height 1.8] [--yes]
//   bun run art:3d balance
//
// model options:
//   --model meshy-t2.5|meshy-t2|meshy-7.1|meshy-6   (default meshy-t2.5)
//   --texture             generate textures in the same pass (default: mesh only)
//   --polycount <n>       target faces (default 20000 for 7.1/6, 4000 for Smart Topology)
//   --pose a-pose|t-pose|none   (default none)
//   --ultra               Ultra 2K geometry, meshy-7.1 only (+5)
//   --keep-lighting       keep painted lighting in the texture, meshy-6 only
//   --pbr                 also generate metallic/roughness/normal maps (off for the hand-painted look)
//   --enhance             let Meshy enhance the input images (off: keep concept art as drawn)
//
// <out> is a path without extension, e.g. art/models/galeborne/base
import { parseArgs } from "node:util";
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, extname } from "node:path";

const API = "https://api.meshy.ai/openapi/v1";
const LEDGER = "art/models/credit-ledger.csv";
const BUDGET = Number(process.env.MESHY_SESSION_BUDGET ?? 250);
const SMART = ["meshy-t2", "meshy-t2.5"];

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    model: { type: "string", default: "meshy-t2.5" },
    texture: { type: "boolean", default: false },
    polycount: { type: "string" },
    pose: { type: "string", default: "none" },
    ultra: { type: "boolean", default: false },
    "keep-lighting": { type: "boolean", default: false },
    pbr: { type: "boolean", default: false },
    enhance: { type: "boolean", default: false },
    task: { type: "string" },
    style: { type: "string" },
    "style-image": { type: "string" },
    height: { type: "string", default: "1.8" },
    session: { type: "string", default: process.env.MESHY_SESSION ?? new Date().toISOString().slice(0, 10) },
    yes: { type: "boolean", default: false },
    "over-budget": { type: "boolean", default: false },
  },
});
const [command, out, ...images] = positionals;

const key = process.env.MESHY_API_KEY;
if (!key) throw new Error("MESHY_API_KEY is not set");
const headers = { Authorization: `Bearer ${key}`, "Content-Type": "application/json" };

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`Meshy ${res.status} ${path}: ${await res.text()}`);
  return res.json();
}

async function waitFor(path: string) {
  for (;;) {
    const task = await api(path);
    if (task.status === "SUCCEEDED") return task;
    if (["FAILED", "CANCELED"].includes(task.status)) throw new Error(`${path} ${task.status} (refunded): ${JSON.stringify(task.task_error)}`);
    process.stdout.write(`\r${path} ${task.status} ${task.progress ?? 0}%   `);
    await Bun.sleep(10_000);
  }
}

async function download(url: string, file: string) {
  await writeFile(file, Buffer.from(await (await fetch(url)).arrayBuffer()));
  console.log(`\n${file}`);
}

const mime: Record<string, string> = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
const dataUri = async (p: string) => `data:${mime[extname(p).toLowerCase()] ?? "image/png"};base64,${(await readFile(p)).toString("base64")}`;

async function sessionSpend() {
  const text = await Bun.file(LEDGER).text().catch(() => "");
  return text.split("\n").slice(1).filter(Boolean).map((l) => l.split(",")).filter((c) => c[1] === values.session).reduce((s, c) => s + Number(c[4]), 0);
}

// Show the cost and stop unless --yes; refuse when the session budget would be exceeded
async function guard(estimate: number, what: string) {
  const spent = await sessionSpend();
  console.log(`${what}: ~${estimate} credits. Session "${values.session}" has spent ${spent}/${BUDGET}.`);
  if (spent + estimate > BUDGET && !values["over-budget"]) throw new Error(`Session budget of ${BUDGET} would be exceeded; rerun with --over-budget after the user approves`);
  if (!values.yes) {
    console.log("Dry run. Rerun with --yes to spend the credits.");
    process.exit(0);
  }
}

async function record(kind: string, taskId: string, credits: number, model: string) {
  if (!(await Bun.file(LEDGER).exists())) await writeFile(LEDGER, "date,session,kind,output,credits,model,task_id\n");
  await appendFile(LEDGER, `${new Date().toISOString()},${values.session},${kind},${out},${credits},${model},${taskId}\n`);
}

if (command === "balance") {
  console.log(await api("/balance"));
  process.exit(0);
}
if (!command || !out) throw new Error("Usage: bun run art:3d <model|retexture|rig|balance> <out> ...");
await mkdir(dirname(out), { recursive: true });

if (command === "model") {
  if (!images.length) throw new Error("At least one image is required");
  const model = values.model!;
  const smart = SMART.includes(model);
  const multi = images.length > 1;
  if (smart && multi) throw new Error("Smart Topology doesn't support multi-image input; pass one image or use meshy-7.1");
  if (values.ultra && model !== "meshy-7.1") throw new Error("--ultra needs meshy-7.1");
  if (values["keep-lighting"] && model !== "meshy-6") throw new Error("--keep-lighting only works on meshy-6");

  const polycount = Number(values.polycount ?? (smart ? 4000 : 20000));
  const body = {
    ...(multi ? { image_urls: await Promise.all(images.map(dataUri)) } : { image_url: await dataUri(images[0]) }),
    ai_model: model,
    ...(smart ? { model_type: "smart-topology", target_polycount: polycount } : { should_remesh: true, topology: "triangle", target_polycount: polycount }),
    ...(values.ultra && { geometry_resolution: "2k" }),
    should_texture: values.texture,
    ...(values.texture && { enable_pbr: values.pbr, texture_resolution: "2k" }),
    ...(model === "meshy-6" && { remove_lighting: !values["keep-lighting"] }),
    ...(!smart && { image_enhancement: values.enhance }),
    ...(values.pose !== "none" && { pose_mode: values.pose }),
    target_formats: ["glb"],
    multi_view_thumbnails: true,
  };
  const estimate = (smart ? 5 : 20) + (values.texture ? 10 : 0) + (values.ultra ? 5 : 0);
  await guard(estimate, `${multi ? "multi-image" : "image"}-to-3d ${model}${values.texture ? " textured" : " mesh-only"}`);

  const endpoint = multi ? "/multi-image-to-3d" : "/image-to-3d";
  const { result: id } = await api(endpoint, { method: "POST", body: JSON.stringify(body) });
  const task = await waitFor(`${endpoint}/${id}`);
  await download(task.model_urls.glb, `${out}.glb`);
  if (task.thumbnail_url) await download(task.thumbnail_url, `${out}.thumb.png`);
  for (const [view, url] of Object.entries<string>(task.thumbnail_urls ?? {})) if (url) await download(url, `${out}.${view}.png`);
  await writeFile(`${out}.json`, JSON.stringify({ taskId: id, endpoint, images, model, textured: values.texture, polycount, pose: values.pose, credits: task.consumed_credits, createdAt: new Date().toISOString() }, null, 2) + "\n");
  await record(command, id, task.consumed_credits ?? estimate, model);
  console.log(`task ${id} · ${task.consumed_credits} credits`);
} else if (command === "retexture") {
  if (!values.task) throw new Error("--task is required");
  if (!values.style && !values["style-image"]) throw new Error("--style or --style-image is required");
  await guard(10, "retexture meshy-7");
  const body = {
    input_task_id: values.task,
    ai_model: "meshy-7", // Retexture rejects meshy-7.1
    ...(values["style-image"] ? { image_style_url: await dataUri(values["style-image"]) } : { text_style_prompt: values.style }),
    enable_original_uv: true,
    enable_pbr: values.pbr,
    target_formats: ["glb"],
  };
  const { result: id } = await api("/retexture", { method: "POST", body: JSON.stringify(body) });
  const task = await waitFor(`/retexture/${id}`);
  await download(task.model_urls.glb, `${out}.glb`);
  if (task.thumbnail_url) await download(task.thumbnail_url, `${out}.thumb.png`);
  await writeFile(`${out}.json`, JSON.stringify({ taskId: id, inputTaskId: values.task, style: values.style ?? values["style-image"], credits: task.consumed_credits, createdAt: new Date().toISOString() }, null, 2) + "\n");
  await record(command, id, task.consumed_credits ?? 10, "meshy-7");
} else if (command === "rig") {
  if (!values.task) throw new Error("--task is required");
  await guard(5, "rigging (free on the web app; API includes walk and run clips)");
  const { result: id } = await api("/rigging", { method: "POST", body: JSON.stringify({ input_task_id: values.task, height_meters: Number(values.height) }) });
  const task = await waitFor(`/rigging/${id}`);
  await download(task.result.rigged_character_glb_url, `${out}.glb`);
  const anims = task.result.basic_animations;
  if (anims?.walking_glb_url) await download(anims.walking_glb_url, `${out}.walk.glb`);
  if (anims?.running_glb_url) await download(anims.running_glb_url, `${out}.run.glb`);
  await writeFile(`${out}.json`, JSON.stringify({ taskId: id, inputTaskId: values.task, height: Number(values.height), credits: task.consumed_credits, createdAt: new Date().toISOString() }, null, 2) + "\n");
  await record(command, id, task.consumed_credits ?? 5, "rig");
} else throw new Error(`Unknown command ${command}`);
