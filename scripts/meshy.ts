// Generate and rig 3D models with the Meshy API, saving GLBs into the repo with a task sidecar.
// Usage:
//   bun run art:3d model <out> <front.png> [side.png back.png ...] [--polycount 20000] [--pose a-pose|t-pose|none]
//   bun run art:3d rig <out> --task <meshy task id> [--height 1.8]
// <out> is a path without extension, e.g. art/models/skerrin/base
import { parseArgs } from "node:util";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, extname } from "node:path";

const API = "https://api.meshy.ai/openapi/v1";
const key = process.env.MESHY_API_KEY;
if (!key) throw new Error("MESHY_API_KEY is not set");

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    polycount: { type: "string", default: "20000" },
    pose: { type: "string", default: "a-pose" },
    task: { type: "string" },
    height: { type: "string", default: "1.8" },
  },
});
const [command, out, ...images] = positionals;
if (!command || !out) throw new Error("Usage: bun run art:3d <model|rig> <out> ...");

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
    if (["FAILED", "CANCELED"].includes(task.status)) throw new Error(`${path} ${task.status}: ${JSON.stringify(task.task_error)}`);
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

await mkdir(dirname(out), { recursive: true });

if (command === "model") {
  if (!images.length) throw new Error("At least one image is required");
  const multi = images.length > 1;
  const body = {
    ...(multi ? { image_urls: await Promise.all(images.map(dataUri)) } : { image_url: await dataUri(images[0]) }),
    ai_model: "meshy-7.1",
    should_texture: true,
    enable_pbr: true,
    should_remesh: true,
    topology: "triangle",
    target_polycount: Number(values.polycount),
    pose_mode: values.pose === "none" ? "" : values.pose,
    target_formats: ["glb"],
    multi_view_thumbnails: true,
  };
  const endpoint = multi ? "/multi-image-to-3d" : "/image-to-3d";
  const { result: id } = await api(endpoint, { method: "POST", body: JSON.stringify(body) });
  const task = await waitFor(`${endpoint}/${id}`);
  await download(task.model_urls.glb, `${out}.glb`);
  if (task.thumbnail_url) await download(task.thumbnail_url, `${out}.thumb.png`);
  await writeFile(`${out}.json`, JSON.stringify({ taskId: id, endpoint, images, polycount: body.target_polycount, pose: body.pose_mode, credits: task.consumed_credits, createdAt: new Date().toISOString() }, null, 2) + "\n");
  console.log(`task ${id}`);
} else if (command === "rig") {
  if (!values.task) throw new Error("--task is required");
  const { result: id } = await api("/rigging", { method: "POST", body: JSON.stringify({ input_task_id: values.task, height_meters: Number(values.height) }) });
  const task = await waitFor(`/rigging/${id}`);
  await download(task.result.rigged_character_glb_url, `${out}.glb`);
  const anims = task.result.basic_animations;
  if (anims?.walking_glb_url) await download(anims.walking_glb_url, `${out}.walk.glb`);
  if (anims?.running_glb_url) await download(anims.running_glb_url, `${out}.run.glb`);
  await writeFile(`${out}.json`, JSON.stringify({ taskId: id, inputTaskId: values.task, height: Number(values.height), credits: task.consumed_credits, createdAt: new Date().toISOString() }, null, 2) + "\n");
} else throw new Error(`Unknown command ${command}`);
