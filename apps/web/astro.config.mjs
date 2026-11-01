import { defineConfig } from "astro/config";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { docToChapter } from "./src/data/chapters.mjs";

const BASE = "/game0";
const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const CONCEPT = join(REPO, "concept");
const GITHUB = "https://github.com/hackdonalds/game0/blob/main/";

/** Concept docs link to each other and to repo files. Point those links at handbook pages or GitHub, and wrap tables so they scroll on phones. */
function handbookLinks() {
  const walk = (node, parent, fn) => { fn(node, parent); node.children?.forEach((c) => walk(c, node, fn)); };
  return (tree, file) => {
    const from = file.path ? dirname(file.path) : CONCEPT;
    walk(tree, null, (node, parent) => {
      if (node.type !== "element") return;
      if (node.tagName === "table" && parent && !(parent.properties?.className ?? []).includes("table-wrap")) {
        const i = parent.children.indexOf(node);
        parent.children[i] = { type: "element", tagName: "div", properties: { className: ["table-wrap"] }, children: [node] };
        return;
      }
      if (node.tagName !== "a") return;
      const href = String(node.properties?.href ?? "");
      if (!href || /^(https?:|mailto:|#)/.test(href)) return;
      const [path, hash = ""] = href.split("#");
      const abs = resolve(from, path);
      const inConcept = relative(CONCEPT, abs);
      const chapter = !inConcept.startsWith("..") && docToChapter[inConcept];
      if (chapter) node.properties.href = `${BASE}/${chapter}/${hash ? `#${hash}` : ""}`;
      else if (abs.startsWith(join(REPO, "worlds"))) node.properties.href = `${BASE}/catalogue/isles/`;
      else if (abs.startsWith(join(REPO, "demos")) && !abs.includes("/src")) node.properties.href = `${BASE}/workshop/`;
      else node.properties.href = GITHUB + relative(REPO, abs);
    });
  };
}

export default defineConfig({
  site: "https://hackdonalds.github.io",
  base: BASE,
  trailingSlash: "ignore",
  markdown: { rehypePlugins: [handbookLinks] },
  redirects: { "/bestiary": "/catalogue/bestiary" },
});
