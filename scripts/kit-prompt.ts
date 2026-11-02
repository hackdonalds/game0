// Build a kit reference sheet prompt from the templates in concept/art-direction/kit-sheets.md.
// Usage: bun run art:kit <type> "<subject>" [--figure 1.8] [--title "Crag: nature kit"]
//        bun run art:kit --list
// Prints the prompt, ready to paste into chatgpt.com (pipe to pbcopy) or to pass to art:image (which uses kitPrompt via --kit).
// The words live only in the doc: each "### <name>" block under "## Prompt templates" holds one ```text fence; {name}
// pulls in another block, {subject}, {figure} and {title} are filled in. Sheet types are the blocks with an **Aspect:** line.
import { parseArgs } from "node:util";
import { join } from "node:path";

export const DOC = "concept/art-direction/kit-sheets.md";
const ROOT = join(import.meta.dir, "..");

export interface KitBlock { name: string; text: string; aspect?: string }

/** Every block in the doc's "Prompt templates" section */
export async function kitBlocks(doc = join(ROOT, DOC)): Promise<Map<string, KitBlock>> {
  const md = await Bun.file(doc).text();
  const start = md.search(/^## Prompt templates\s*$/m);
  if (start < 0) throw new Error(`${DOC} has no "## Prompt templates" section`);
  const rest = md.slice(start).split("\n").slice(1).join("\n");
  const section = rest.slice(0, rest.search(/^## /m) >= 0 ? rest.search(/^## /m) : undefined);
  const blocks = new Map<string, KitBlock>();
  for (const part of section.split(/^### /m).slice(1)) {
    const name = part.split("\n")[0].trim();
    const text = part.match(/```text\n([\s\S]*?)\n```/)?.[1].trim();
    if (!text) throw new Error(`${DOC}: block "${name}" has no \`\`\`text fence`);
    const aspect = part.match(/^\*\*Aspect:\*\*\s*(\S+)/m)?.[1];
    blocks.set(name, { name, text, aspect });
  }
  return blocks;
}

/** Sheet types: blocks that carry an Aspect line */
export const sheetTypes = (blocks: Map<string, KitBlock>) => [...blocks.values()].filter((b) => b.aspect);

export interface KitPromptOptions { figure?: string | number; title?: string }

/** Compose the full prompt for one sheet type and subject */
export async function kitPrompt(type: string, subject: string, opts: KitPromptOptions = {}) {
  const blocks = await kitBlocks();
  const sheet = blocks.get(type);
  if (!sheet?.aspect) throw new Error(`Unknown sheet type "${type}". Types: ${sheetTypes(blocks).map((b) => b.name).join(", ")}`);
  if (!subject.trim()) throw new Error("Subject is required");
  const subj = subject.trim().replace(/[.\s]+$/, ""); // templates end the sentence after {subject}
  const values: Record<string, string> = {
    subject: subj,
    figure: String(opts.figure ?? 1.8),
    title: opts.title ? `Title at the top: "${opts.title}".` : "",
  };
  const expand = (text: string, seen: string[]): string =>
    text.replace(/\{([a-z-]+)\}/g, (m, name: string) => {
      if (name in values) return values[name];
      const b = blocks.get(name);
      if (!b) throw new Error(`${DOC}: block "${seen.at(-1)}" uses {${name}}, which is not a block`);
      if (seen.includes(name)) throw new Error(`${DOC}: block "${name}" includes itself`);
      return expand(b.text, [...seen, name]);
    });
  const prompt = expand(sheet.text, [type]).replace(/\s+/g, " ").trim();
  return { prompt, aspect: sheet.aspect, type, subject: subj, figure: Number(values.figure), title: opts.title };
}

if (import.meta.main) {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { figure: { type: "string" }, title: { type: "string" }, list: { type: "boolean" }, json: { type: "boolean" } },
  });
  if (values.list || !positionals.length) {
    for (const b of sheetTypes(await kitBlocks())) console.log(`${b.name.padEnd(11)} ${b.aspect}`);
    if (!values.list) console.error(`\nUsage: bun run art:kit <type> "<subject>" [--figure 1.8] [--title "..."] [--json]`);
    process.exit(values.list ? 0 : 1);
  }
  const [type, ...rest] = positionals;
  const subject = rest.join(" ");
  if (!subject.trim()) throw new Error("Subject is required");
  const out = await kitPrompt(type, subject, { figure: values.figure, title: values.title });
  console.log(values.json ? JSON.stringify(out, null, 2) : out.prompt);
}
