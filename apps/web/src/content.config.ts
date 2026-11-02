import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const devlog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/devlog" }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    summary: z.string(),
  }),
});

// The concept docs are the handbook's chapters. Ids keep the path, e.g. "world/README.md". Catalogue entries
// (concept/entries/) are read by src/data/concept.ts instead.
const concept = defineCollection({
  loader: glob({ pattern: ["**/*.md", "!entries/**"], base: "../../concept", generateId: ({ entry }) => entry }),
});

export const collections = { devlog, concept };
