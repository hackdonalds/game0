// Read the markdown under concept/ from disk, for Bun scripts (the site uses import.meta.glob in src/data/concept.ts).
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import type { ConceptFiles } from "./concept";

export function readConceptFiles(root: string): ConceptFiles {
  const concept = join(root, "concept");
  const out: ConceptFiles = {};
  const walk = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith(".md")) out[relative(concept, p)] = readFileSync(p, "utf8");
    }
  };
  walk(concept);
  return out;
}
