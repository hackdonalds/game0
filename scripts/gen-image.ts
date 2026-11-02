// Generate concept art via OpenRouter and save it into the repo with a prompt sidecar.
// Usage: bun run art:image "prompt" [--out art/concept/name] [--ref path.webp ...] [--aspect 16:9] [--quality high] [--model id]
//        bun run art:image --kit <type> "subject" [--figure 1.8] [--title "..."] --out art/kit/<kind>/<sheet> [--ref ...]
//   --kit builds the prompt from concept/art-direction/kit-sheets.md (scripts/kit-prompt.ts); the aspect defaults to the type's.
import { parseArgs } from "node:util";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, extname } from "node:path";
import { kitPrompt } from "./kit-prompt";

const DEFAULT_MODEL = "openai/gpt-image-2.5-sunburst";

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
  },
});

const kit = values.kit ? await kitPrompt(values.kit, positionals.join(" "), { figure: values.figure, title: values.title }) : undefined;
const prompt = kit?.prompt ?? positionals.join(" ").trim();
values.aspect ??= kit?.aspect ?? "16:9";
if (!prompt) throw new Error("Prompt is required");
const key = process.env.OPENROUTER_API_KEY;
if (!key) throw new Error("OPENROUTER_API_KEY is not set");

const mime: Record<string, string> = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
const refs = await Promise.all(
  values.ref!.map(async (p) => ({
    type: "image_url",
    image_url: { url: `data:${mime[extname(p).toLowerCase()] ?? "image/png"};base64,${(await readFile(p)).toString("base64")}` },
  })),
);

const res = await fetch("https://openrouter.ai/api/v1/images", {
  method: "POST",
  headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "X-Title": "game0" },
  body: JSON.stringify({
    model: values.model,
    prompt,
    aspect_ratio: values.aspect,
    quality: values.quality,
    ...(refs.length && { input_references: refs }),
  }),
});
if (!res.ok) throw new Error(`OpenRouter ${res.status}: ${await res.text()}`);
const data = await res.json();
const images: { url?: string; b64_json?: string }[] = data.data ?? [];
if (!images.length) throw new Error(`No image returned: ${JSON.stringify(data).slice(0, 500)}`);

const slug = (kit ? `${kit.type}-${kit.subject}` : prompt).toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 48).replace(/-+$/, "");
const base = values.out ?? `art/${kit ? "kit" : "concept"}/${new Date().toISOString().slice(0, 10)}-${slug}`;
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
  JSON.stringify({ prompt, ...(kit && { kit: { type: kit.type, subject: kit.subject, figure: kit.figure, ...(kit.title && { title: kit.title }) } }), model: values.model, aspect: values.aspect, quality: values.quality, refs: values.ref, generationId: data.id, createdAt: new Date().toISOString() }, null, 2) + "\n",
);
