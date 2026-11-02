// Generate concept art via the OpenAI Images API (default) or OpenRouter, and save it into the repo with a prompt sidecar.
// Usage: bun run art:image "prompt" [--out art/concept/<kind>/<name> | art/kit/<kind>/<name>] [--ref path.webp ...] [--aspect 16:9] [--quality high] [--model id] [--provider openai|openrouter] [--dry-run]
//        bun run art:image --kit <type> "subject" [--figure 1.8] [--title "..."] --out art/kit/<kind>/<sheet> [--ref ...]
//   --kit builds the prompt from concept/art-direction/kit-sheets.md (scripts/kit-prompt.ts); the aspect defaults to the type's.
//   OpenAI: refs go to /v1/images/edits (first ref = style reference); the sidecar records token use and cost in USD.
//   Without --out, images land in art/concept/drafts/ (never shown on the site) until they are reviewed and moved.
import { parseArgs } from "node:util";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, extname } from "node:path";
import { kitPrompt } from "./kit-prompt";

const DEFAULT_MODEL = "gpt-image-2.5-sunburst";
// USD per 1M tokens (OpenAI pricing for GPT Image 2.5, Nov 2026)
const RATES = { textIn: 5, imageIn: 8, imageOut: 30 };
const SIZES: Record<string, string> = { "1:1": "1024x1024", "16:9": "1536x864", "21:9": "1792x768", "3:2": "1536x1024", "2:3": "1024x1536", "9:16": "864x1536" };

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    out: { type: "string" },
    ref: { type: "string", multiple: true, default: [] },
    aspect: { type: "string" },
    quality: { type: "string", default: "high" },
    model: { type: "string", default: DEFAULT_MODEL },
    kit: { type: "string" },
    figure: { type: "string" },
    title: { type: "string" },
    provider: { type: "string", default: "openai" },
    "dry-run": { type: "boolean", default: false },
  },
});

const kit = values.kit ? await kitPrompt(values.kit, positionals.join(" "), { figure: values.figure, title: values.title }) : undefined;
const prompt = kit?.prompt ?? positionals.join(" ").trim();
values.aspect ??= kit?.aspect ?? "16:9";
if (!prompt) throw new Error("Prompt is required");
const mime: Record<string, string> = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
const openai = values.provider === "openai";
const model = openai ? values.model!.replace(/^openai\//, "") : values.model!.includes("/") ? values.model! : `openai/${values.model}`;
const size = SIZES[values.aspect!];
if (openai && !size) throw new Error(`No OpenAI size for aspect ${values.aspect}; use one of ${Object.keys(SIZES).join(", ")}`);
if (values["dry-run"]) {
  console.log(JSON.stringify({ provider: values.provider, model, size, aspect: values.aspect, quality: values.quality, refs: values.ref, prompt }, null, 2));
  process.exit(0);
}

let data: { id?: string; data?: { url?: string; b64_json?: string }[]; usage?: Usage };
if (openai) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY is not set");
  let res: Response;
  if (values.ref!.length) {
    const form = new FormData();
    form.append("model", model);
    form.append("prompt", prompt);
    form.append("size", size);
    form.append("quality", values.quality!);
    for (const p of values.ref!) form.append("image[]", new Blob([await readFile(p)], { type: mime[extname(p).toLowerCase()] ?? "image/png" }), p.split("/").pop());
    res = await fetch("https://api.openai.com/v1/images/edits", { method: "POST", headers: { Authorization: `Bearer ${key}` }, body: form });
  } else {
    res = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, prompt, size, quality: values.quality }),
    });
  }
  if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
  data = await res.json();
} else {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error("OPENROUTER_API_KEY is not set");
  const refs = await Promise.all(
    values.ref!.map(async (p) => ({
      type: "image_url",
      image_url: { url: `data:${mime[extname(p).toLowerCase()] ?? "image/png"};base64,${(await readFile(p)).toString("base64")}` },
    })),
  );
  const res = await fetch("https://openrouter.ai/api/v1/images", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "X-Title": "game0" },
    body: JSON.stringify({ model, prompt, aspect_ratio: values.aspect, quality: values.quality, ...(refs.length && { input_references: refs }) }),
  });
  if (!res.ok) throw new Error(`OpenRouter ${res.status}: ${await res.text()}`);
  data = await res.json();
}
const images = data.data ?? [];
if (!images.length) throw new Error(`No image returned: ${JSON.stringify(data).slice(0, 500)}`);

interface Usage { input_tokens?: number; output_tokens?: number; input_tokens_details?: { text_tokens?: number; image_tokens?: number } }
const u = data.usage;
const cost = u && Math.round(((u.input_tokens_details?.text_tokens ?? 0) * RATES.textIn + (u.input_tokens_details?.image_tokens ?? 0) * RATES.imageIn + (u.output_tokens ?? 0) * RATES.imageOut) / 1e2) / 1e4;

const slug = (kit ? `${kit.type}-${kit.subject}` : prompt).toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 48).replace(/-+$/, "");
const base = values.out ?? `art/concept/drafts/${new Date().toISOString().slice(0, 10)}-${slug}`;
await mkdir(dirname(base), { recursive: true });

for (const [i, img] of images.entries()) {
  let bytes: Buffer;
  let type = "png";
  if (img.b64_json) bytes = Buffer.from(img.b64_json, "base64");
  else if (img.url?.startsWith("data:")) {
    const [, t, b64] = img.url.match(/^data:image\/(\w+);base64,(.+)$/)!;
    [type, bytes] = [t, Buffer.from(b64, "base64")];
  } else if (img.url) bytes = Buffer.from(await (await fetch(img.url)).arrayBuffer());
  else throw new Error(`Unrecognised image entry: ${JSON.stringify(img).slice(0, 200)}`);
  const file = `${base}${images.length > 1 ? `-${i + 1}` : ""}.${type === "jpeg" ? "jpg" : type}`;
  await writeFile(file, bytes);
  console.log(file);
}
await writeFile(
  `${base}.json`,
  JSON.stringify({ prompt, ...(kit && { kit: { type: kit.type, subject: kit.subject, figure: kit.figure, ...(kit.title && { title: kit.title }) } }), provider: values.provider, model, size, aspect: values.aspect, quality: values.quality, refs: values.ref, ...(data.id && { generationId: data.id }), ...(u && { usage: u, costUSD: cost }), createdAt: new Date().toISOString() }, null, 2) + "\n",
);
if (cost !== undefined) console.log(`cost $${cost.toFixed(4)}`);
