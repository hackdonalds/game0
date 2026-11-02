// The handbook's chapters, in reading order, read from the `chapter:` frontmatter of each chapter's primary concept doc.
// A chapter renders its primary doc, then the docs it lists under `docs` (paths relative to concept/).
// Plain JS so astro.config.mjs can use it to rewrite links between concept docs into handbook URLs; it reads the docs
// from disk so it works the same in astro.config.mjs, in the site and in Bun scripts.
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { splitFrontmatter } from "../lib/frontmatter.mjs";

/** @typedef {{ slug: string; number: number; title: string; kicker: string; summary: string; docs: string[]; catalogues: string[]; demo?: "map" | "peoples" | "sail" | "shard"; art: string }} Chapter */

const DEMOS = ["map", "peoples", "sail", "shard"];
const CATALOGUES = ["peoples", "bestiary", "skills", "isles", "winds", "ships", "materials", "architecture", "biomes", "glossary"];

/** The repo root: the nearest folder at or above the working directory that has concept/ and worlds/ */
function repoRoot() {
  for (let dir = process.cwd(); ; dir = dirname(dir)) {
    if (existsSync(join(dir, "concept")) && existsSync(join(dir, "worlds"))) return dir;
    if (dirname(dir) === dir) throw new Error(`chapters.mjs: no concept/ folder at or above ${process.cwd()}`);
  }
}
const CONCEPT = join(repoRoot(), "concept");

/** Concept docs (paths relative to concept/), without the catalogue entries */
function conceptDocs(dir = CONCEPT) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return e.name === "entries" && dir === CONCEPT ? [] : conceptDocs(p);
    return e.name.endsWith(".md") ? [relative(CONCEPT, p)] : [];
  }).sort();
}

function readChapters() {
  const fail = (doc, msg) => { throw new Error(`concept/${doc}: chapter frontmatter ${msg}. See apps/web/src/data/chapters.mjs.`); };
  const docs = conceptDocs();
  /** @type {Chapter[]} */
  const out = [];
  for (const doc of docs) {
    const { data } = splitFrontmatter(readFileSync(join(CONCEPT, doc), "utf8"), `concept/${doc}`);
    const c = data.chapter;
    if (c === undefined) continue;
    if (typeof c !== "object" || !c) fail(doc, "must be a mapping");
    const known = ["slug", "number", "title", "kicker", "summary", "docs", "catalogues", "demo", "art"];
    for (const k of Object.keys(c)) if (!known.includes(k)) fail(doc, `has an unknown field "${k}" (known: ${known.join(", ")})`);
    for (const k of ["slug", "title", "kicker", "summary", "art"]) if (typeof c[k] !== "string" || !c[k].trim()) fail(doc, `needs a "${k}" (text)`);
    if (!/^[a-z][a-z0-9-]*$/.test(c.slug)) fail(doc, `"slug" must be lower-case letters, digits and dashes`);
    if (!Number.isInteger(c.number) || c.number < 1) fail(doc, `needs a "number" (1, 2, 3...)`);
    const more = c.docs ?? [];
    if (!Array.isArray(more) || more.some((d) => typeof d !== "string")) fail(doc, `"docs" must be a list of doc paths relative to concept/`);
    for (const d of more) if (!docs.includes(d)) fail(doc, `"docs" lists ${d}, which does not exist`);
    const cats = c.catalogues ?? [];
    if (!Array.isArray(cats) || cats.some((x) => !CATALOGUES.includes(x))) fail(doc, `"catalogues" must be a list from: ${CATALOGUES.join(", ")}`);
    if (c.demo !== undefined && !DEMOS.includes(c.demo)) fail(doc, `"demo" must be one of: ${DEMOS.join(", ")}`);
    out.push({ slug: c.slug, number: c.number, title: c.title.trim(), kicker: c.kicker.trim(), summary: c.summary.trim(), docs: [doc, ...more], catalogues: cats, ...(c.demo ? { demo: c.demo } : {}), art: c.art.trim() });
  }
  out.sort((a, b) => a.number - b.number);
  out.forEach((c, i) => {
    if (c.number !== i + 1) throw new Error(`Chapter numbers must run 1, 2, 3... without gaps: "${c.slug}" (concept/${c.docs[0]}) is ${c.number}, expected ${i + 1}`);
    const dup = out.find((o) => o !== c && o.slug === c.slug);
    if (dup) throw new Error(`Two chapters use the slug "${c.slug}": concept/${c.docs[0]} and concept/${dup.docs[0]}`);
  });
  const seen = new Map();
  for (const c of out) for (const d of c.docs) {
    if (seen.has(d)) throw new Error(`concept/${d} is in two chapters: ${seen.get(d)} and ${c.slug}`);
    seen.set(d, c.slug);
  }
  if (!out.length) throw new Error("No concept doc has chapter frontmatter, so the handbook would have no chapters");
  return out;
}

/** @type {Chapter[]} */
export const chapters = readChapters();

/** Map a concept doc path (relative to concept/) to its chapter slug. */
export const docToChapter = Object.fromEntries(chapters.flatMap((c) => c.docs.map((d) => [d, c.slug])));

/** Concept docs deliberately not rendered as chapters, with the reason. scripts/handbook-check.ts fails on any other doc
 *  under concept/ (outside concept/entries/) that no chapter renders. @type {Record<string, string>} */
export const excludedDocs = {
  "README.md": "Index of the concept folder for readers on GitHub; the handbook's chapter list and home page replace it.",
  "glossary.md": "The glossary terms; the handbook shows them as the glossary catalogue (apps/web/src/data/glossary.ts), not as a chapter.",
};
