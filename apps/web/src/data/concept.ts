// Every catalogue entry, read from concept/ at build time (see ../lib/concept.ts for the layout and the checks).
// The other data modules in this folder re-export their part of it under their old names.
import shard from "../../../../worlds/first-shard.world.json";
import { loadConcept, type ConceptFiles } from "../lib/concept";
import { chapters } from "./chapters.mjs";

const raw = import.meta.glob<string>("../../../../concept/**/*.md", { query: "?raw", import: "default", eager: true });
const files: ConceptFiles = Object.fromEntries(Object.entries(raw).map(([path, text]) => [path.replace(/^(\.\.\/)+concept\//, ""), text]));

export const concept = loadConcept(files, shard, chapters);
