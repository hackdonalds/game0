// Markdown with YAML frontmatter, and the few markdown helpers the handbook's readers share.
// Plain JS with no Vite features, so astro.config.mjs (through chapters.mjs), the site and Bun scripts can all use it.
import { parse } from "yaml";

/** Split a markdown file into its YAML frontmatter (an object, empty when there is none) and its body.
 *  Throws with the file name when the YAML is broken or is not a mapping. */
export function splitFrontmatter(text, where) {
  const src = text.replace(/^﻿/, "").replace(/\r\n?/g, "\n");
  const m = src.match(/^---\n([\s\S]*?)\n---[ \t]*(?:\n|$)/);
  if (!m) return { data: {}, body: src.trim() };
  let data;
  try {
    data = parse(m[1]) ?? {};
  } catch (e) {
    throw new Error(`${where}: the frontmatter is not valid YAML: ${e.message}`);
  }
  if (typeof data !== "object" || Array.isArray(data)) throw new Error(`${where}: the frontmatter must be a YAML mapping of field: value`);
  return { data, body: src.slice(m[0].length).trim() };
}

/** Inline markdown (links, emphasis, code) to plain text, on one line */
export const plain = (s) => s.replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/[*_`]/g, "").replace(/\s+/g, " ").trim();

/** The body's paragraphs as plain text, separated by a blank line. Headings, tables and lists are not paragraphs. */
export const paragraphs = (md) =>
  md.split(/\n\s*\n/).map((p) => p.trim()).filter((p) => p && !/^(#|\||[-*+] |\d+\. |>)/.test(p)).map(plain).join("\n\n");

/** The first sentence of a plain-text paragraph */
export const firstSentence = (s) => (s.match(/^[\s\S]*?[.!?](?=\s|$)/)?.[0] ?? s).trim();

/** GitHub-style heading anchor: "The Tether Accord" → "the-tether-accord" */
export const slugify = (s) => plain(s).toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, "").replace(/\s/g, "-");

/** The text of the section under the heading whose anchor is `anchor`, up to the next heading of the same or higher level */
export function sectionByAnchor(md, anchor) {
  const lines = md.split("\n");
  const start = lines.findIndex((l) => /^#{1,6} /.test(l) && slugify(l.replace(/^#+ /, "")) === anchor);
  if (start < 0) return undefined;
  const depth = lines[start].match(/^#+/)[0].length;
  const end = lines.findIndex((l, i) => i > start && new RegExp(`^#{1,${depth}} `).test(l));
  return lines.slice(start + 1, end < 0 ? undefined : end).join("\n");
}

/** Rows of the first markdown table in `md`, as arrays of trimmed cell strings (header row first, separator dropped) */
export function tableRows(md) {
  const rows = [];
  for (const line of md.split("\n")) {
    if (!line.trim().startsWith("|")) { if (rows.length) break; continue; }
    const cells = line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    if (cells.every((c) => /^:?-+:?$/.test(c) || c === "")) continue;
    rows.push(cells);
  }
  return rows;
}
