// Read every catalogue entry from concept/: concept/entries/<kind>/<id>.md (YAML frontmatter for the structured stats,
// the body for the prose), concept/glossary.md, and the per-style tables of the architecture docs.
// Each file is validated against a schema and cross-checked against the other entries and the world file; anything
// missing, misspelt or pointing nowhere throws with the file name, so a bad entry breaks the build instead of the page.
// Plain TypeScript with no Vite features: the site passes the files in from import.meta.glob (src/data/concept.ts),
// Bun scripts from disk (./concept-files.ts).
import { z } from "zod";
import { firstSentence, paragraphs, plain, sectionByAnchor, slugify, splitFrontmatter, tableRows } from "./frontmatter.mjs";
import { parseBiomes } from "../data/biomes-doc";
import type { Creature } from "../data/bestiary";
import type { IsleNote, Material, PeopleEntry, Ship, Skill, Term, WindNote } from "../data/types";

/** Markdown files under concept/, keyed by their path relative to concept/ ("entries/skills/blades.md") */
export type ConceptFiles = Record<string, string>;

interface World {
  isles: { id: string; name: string }[];
  winds: { id: string; name: string }[];
}

export interface ArchStyleText {
  id: string;
  name: string;
  /** The people who build it, or "" */
  people: string;
  motto: string;
  summary: string;
  traits: { label: string; value: string }[];
  grid: string;
  concept: { id: string; label: string }[];
  kitSheets: { id: string; label: string }[];
  biomes: string[];
}

export interface BodyPlan { id: string; name: string; skeleton: string; parts: string }

export const KINDS = ["peoples", "bestiary", "skills", "materials", "ships", "isles", "winds", "architecture"] as const;
export type Kind = (typeof KINDS)[number];

export const SKILL_GROUPS = ["Weapons", "Arcane", "Defence and survival", "Gathering", "Crafting", "Travel and lore", "Innate"] as const;
/** Bestiary regions that are not biomes */
const OPEN_REGIONS = [{ id: "sky", name: "The open sky" }, { id: "storm", name: "The storm below" }];

const text = z.string().trim().min(1);
const texts = z.array(text);
const art = text.describe("subject brief for the painted plate (scripts/handbook-art.ts)");
const quote = z.object({ text, by: text }).strict();
const named = z.object({ name: text, text }).strict();

const schemas = {
  peoples: z.object({
    name: text, homeland: text, blurb: text, look: text, knownFor: text, start: text,
    relations: z.array(z.object({ with: text, kind: z.enum(["ally", "rival", "trade", "wary"]), text }).strict()),
    signature: z.object({ customizable: texts, locked: texts }).strict(),
    quote, art,
  }).strict(),
  skills: z.object({
    name: text, group: z.enum(SKILL_GROUPS), summary: text,
    innateTo: text.optional(), limit: text.optional(),
    sources: texts.min(1), affinity: texts.default([]), uses: texts.min(1),
    milestones: z.array(z.object({ level: z.union([z.literal(25), z.literal(50), z.literal(75), z.literal(100)]), name: text, text }).strict()).length(4),
    art,
  }).strict(),
  materials: z.object({
    name: text, family: z.enum(["Metal", "Wood", "Leather", "Cloth", "Stone"]), tier: z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4)]),
    summary: text, where: text, gatheredWith: text, usedFor: texts.min(1), draft: z.boolean(), art,
  }).strict(),
  ships: z.object({
    name: text, aboard: z.number().int().positive(), steeredBy: z.number().int().positive(), steering: text, summary: text,
    roles: z.array(named).min(1), stats: z.array(z.object({ label: text, value: text }).strict()), building: text, uses: texts.min(1), art,
  }).strict(),
  bestiary: z.object({
    name: text, boss: z.boolean().optional(), family: text, bodyPlan: text,
    size: z.enum(["tiny", "small", "medium", "large", "huge", "colossal"]),
    /** Shoulder height (or body length for tiny creatures) in metres; sets the scale on its species sheet */
    height: z.number().positive().optional(),
    /** Nose-to-tail length in metres, for long flyers and swimmers; sets the scale on its species sheet */
    length: z.number().positive().optional(),
    /** Subject brief for the in-world scene painting */
    scene: text.optional(),
    temperament: z.enum(["passive", "neutral", "territorial", "hostile"]),
    danger: z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5)]),
    region: text, tiers: z.array(z.enum(["safe", "guarded", "wild"])).min(1),
    habitat: text, active: text, seasons: text,
    health: z.number().positive(), stamina: z.number().positive(),
    speed: z.object({ walk: z.number().optional(), climb: z.number().optional(), swim: z.number().optional(), fly: z.number().optional() }).strict(),
    skills: z.record(z.string(), z.number().min(0).max(100)),
    senses: text, behaviours: texts.min(1), actions: z.array(named).min(1), drops: texts,
    population: text.optional(),
    taming: z.object({ use: z.enum(["Ground mount", "Pack animal", "Flying mount"]), skill: z.number().min(0).max(100) }).strict().optional(),
    storm: named.optional(),
    quote, art,
  }).strict(),
  isles: z.object({ landmarks: texts, resources: texts, art }).strict(),
  winds: z.object({}).strict(),
  architecture: z.object({
    name: text, people: text.optional(), biomes: texts,
    concept: z.record(z.string(), text), kitSheets: z.record(z.string(), text),
  }).strict(),
};

type Raw<K extends Kind> = z.infer<(typeof schemas)[K]>;
interface Parsed<K extends Kind> { id: string; file: string; data: Raw<K>; body: string }

/** Every entry file of one kind, parsed and validated, in file-name order */
function entries<K extends Kind>(files: ConceptFiles, kind: K, needsBody: boolean): Parsed<K>[] {
  const prefix = `entries/${kind}/`;
  return Object.keys(files).filter((p) => p.startsWith(prefix)).sort().map((path) => {
    const file = `concept/${path}`;
    const id = path.slice(prefix.length);
    if (id.includes("/") || !id.endsWith(".md")) throw new Error(`${file}: entries are concept/entries/<kind>/<id>.md, with no subfolders`);
    const { data, body } = splitFrontmatter(files[path], file);
    const res = schemas[kind].safeParse(data);
    if (!res.success) throw new Error(`${file}: bad frontmatter:\n${z.prettifyError(res.error)}`);
    const prose = paragraphs(body);
    if (needsBody && !prose) throw new Error(`${file}: the body (the text after the frontmatter) is empty`);
    return { id: id.slice(0, -3), file, data: res.data as Raw<K>, body: prose };
  });
}

const fail = (file: string, msg: string): never => { throw new Error(`${file}: ${msg}`); };

/** Parse the per-style tables of concept/art-direction/architecture.md (traits, motto) and modular-kit.md (grid) */
function styleTables(files: ConceptFiles, styles: { id: string; name: string }[]) {
  const ARCH = "art-direction/architecture.md", KIT = "art-direction/modular-kit.md";
  const styleOf = (cell: string, file: string) => {
    const want = plain(cell).toLowerCase();
    return styles.find((s) => s.name.toLowerCase().startsWith(want))?.id ?? fail(`concept/${file}`, `table column or row "${cell}" names no style in concept/entries/architecture/`);
  };
  const archMd = files[ARCH] ?? fail(`concept/${ARCH}`, "missing");
  const looks = tableRows(sectionByAnchor(archMd, "core-idea-architecture-answers-the-sinking") ?? fail(`concept/${ARCH}`, 'no "## Core idea: architecture answers the sinking" section'));
  if (looks.length < 2) fail(`concept/${ARCH}`, "the core-idea table has no rows");
  const [head, ...rows] = looks;
  const cols = head.slice(1).map((h) => {
    const [name, motto] = h.split(":").map((s) => plain(s));
    if (!motto) fail(`concept/${ARCH}`, `table header "${h}" should be "<Style>: <motto>"`);
    return { id: styleOf(name, ARCH), motto: motto.charAt(0).toUpperCase() + motto.slice(1) };
  });
  const traits = new Map<string, { motto: string; traits: { label: string; value: string }[] }>(cols.map((c) => [c.id, { motto: c.motto, traits: [] }]));
  for (const [label, ...cells] of rows)
    cells.forEach((v, i) => { if (cols[i] && plain(v) && !/^[—–-]$/.test(plain(v))) traits.get(cols[i].id)!.traits.push({ label: plain(label), value: plain(v) }); });

  const kitMd = files[KIT] ?? fail(`concept/${KIT}`, "missing");
  const modules = tableRows(sectionByAnchor(kitMd, "modules-per-style") ?? fail(`concept/${KIT}`, 'no "## Modules per style" section'));
  const grid = new Map<string, string>();
  for (const [style, module, storey, wall, character] of modules.slice(1)) {
    const has = (s?: string) => s && !/^[—–-]$/.test(s.trim());
    const end = (s: string) => s.replace(/[.;]?$/, ".");
    const parts = /\d/.test(module ?? "") ? [`Module ${module}`, has(storey) && `storey ${storey}`, has(wall) && `wall ${wall}`].filter(Boolean).join(", ") : module;
    grid.set(styleOf(style, KIT), plain(`${end(parts!)} ${character ? end(character.charAt(0).toUpperCase() + character.slice(1)) : ""}`));
  }
  return { traits, grid };
}

/** Load and cross-check everything under concept/ that the catalogues show */
export function loadConcept(files: ConceptFiles, world: World, chapters: { slug: string; title: string }[]) {
  const isleNames = new Set(world.isles.map((i) => i.name));
  const biomes = parseBiomes(files["art-direction/biomes.md"] ?? fail("concept/art-direction/biomes.md", "missing"));
  const REGIONS = [...biomes.map((b) => ({ id: b.id, name: `${b.name} isles` })), ...OPEN_REGIONS];

  // Peoples first: other kinds point at them
  const rawPeoples = entries(files, "peoples", true);
  const peopleIds = new Set(rawPeoples.map((p) => p.id));
  const peopleNameOf = (id: string) => rawPeoples.find((p) => p.id === id)!.data.name;
  const needPeople = (file: string, id: string, field: string) => { if (!peopleIds.has(id)) fail(file, `${field} "${id}" is not a people in concept/entries/peoples/`); };

  // Skills, ordered by group then name
  const rawSkills = entries(files, "skills", true).sort((a, b) => SKILL_GROUPS.indexOf(a.data.group) - SKILL_GROUPS.indexOf(b.data.group) || a.data.name.localeCompare(b.data.name));
  const skillNames = new Set(rawSkills.map((s) => s.data.name));
  const skills: Skill[] = rawSkills.map(({ id, file, data: s, body }) => {
    s.affinity.forEach((p) => needPeople(file, p, "affinity"));
    if ((s.group === "Innate") !== Boolean(s.innateTo)) fail(file, 'innate skills (group: Innate) need "innateTo: <people id>", and only they may have it');
    if (s.innateTo) { needPeople(file, s.innateTo, "innateTo"); if (!s.limit) fail(file, 'an innate skill needs a "limit"'); }
    if ([...s.milestones].map((m) => m.level).join() !== "25,50,75,100") fail(file, "milestones must be levels 25, 50, 75 and 100, in that order");
    // Every source ends in an isle of the world file: "Trainer at Oathgate", "Reading the Ledger at Ledgerstone"
    for (const src of s.sources) {
      const place = src.match(/\b(?:at|in|on|of)\s+([A-Z][\w']*(?:\s+[A-Z][\w']*)*)$/)?.[1];
      if (!place || !isleNames.has(place)) fail(file, `source "${src}" should end with "at|in|on|of <isle>", naming an isle in worlds/first-shard.world.json${place ? ` ("${place}" is not one)` : ""}`);
    }
    const innate = s.innateTo;
    return {
      id, name: s.name, group: s.group, summary: s.summary,
      description: innate ? `${body} ${s.limit}` : body,
      sources: innate ? [`Innate to the ${peopleNameOf(innate)}`, ...s.sources] : s.sources,
      affinity: innate ? [innate] : s.affinity,
      uses: s.uses, milestones: s.milestones, art: s.art,
      ...(innate ? { innateTo: innate, text: body, limit: s.limit } : {}),
    } as Skill;
  });

  const peopleEntries: PeopleEntry[] = rawPeoples.map(({ id, file, data: p, body }) => {
    p.relations.forEach((r) => needPeople(file, r.with, "relations.with"));
    const innate = skills.filter((s) => s.innateTo === id);
    if (innate.length !== 1) fail(file, `needs exactly one innate skill (a skill entry with "innateTo: ${id}"), found ${innate.length}`);
    return {
      id, name: p.name, homeland: p.homeland, blurb: p.blurb, look: p.look, culture: body, knownFor: p.knownFor,
      affinities: skills.filter((s) => s.group !== "Innate" && s.affinity.includes(id)).map((s) => s.name),
      start: p.start, relations: p.relations as PeopleEntry["relations"],
      innate: { name: innate[0].name, text: innate[0].text!, limit: innate[0].limit! },
      signature: p.signature, quote: p.quote, art: p.art,
    };
  });

  const materials: Material[] = entries(files, "materials", true).map(({ id, file, data: m, body }) => {
    const skill = m.gatheredWith.match(/^([A-Z][a-z]+(?: [A-Z][a-z]+)?)/)?.[1];
    if (!skill || !skillNames.has(skill)) fail(file, `gatheredWith "${m.gatheredWith}" should start with a skill name`);
    return { id, ...m, description: body };
  });

  const ships: Ship[] = entries(files, "ships", true).map(({ id, data: s, body }) => ({
    id, name: s.name, aboard: s.aboard, steeredBy: `${s.steeredBy}: ${s.steering}`, summary: s.summary, description: body, roles: s.roles,
    stats: [{ label: "Aboard", value: `Up to ${s.aboard}` }, { label: "Steered by", value: String(s.steeredBy) }, ...s.stats],
    building: s.building, uses: s.uses, art: s.art,
  })).sort((a, b) => a.aboard - b.aboard);

  const MONSTERS = "monsters/README.md";
  const planRows = tableRows(sectionByAnchor(files[MONSTERS] ?? fail(`concept/${MONSTERS}`, "missing"), "body-plans") ?? fail(`concept/${MONSTERS}`, 'no "## Body plans" section')).slice(1);
  const bodyPlans: BodyPlan[] = planRows.map(([id, name, skeleton, parts]) => ({ id: plain(id), name: plain(name), skeleton: plain(skeleton), parts: plain(parts) }));
  const bestiary: Creature[] = entries(files, "bestiary", true).map(({ id, file, data: c, body }) => {
    if (!bodyPlans.some((b) => b.id === c.bodyPlan)) fail(file, `bodyPlan "${c.bodyPlan}" is not in the body plans table of concept/${MONSTERS}: ${bodyPlans.map((b) => b.id).join(", ")}`);
    if (!REGIONS.some((r) => r.id === c.region)) fail(file, `region "${c.region}" is not a biome in concept/art-direction/biomes.md or one of: ${OPEN_REGIONS.map((r) => r.id).join(", ")}`);
    for (const s of Object.keys(c.skills)) if (!skillNames.has(s)) fail(file, `skill "${s}" is not a skill in concept/entries/skills/`);
    if (c.boss && c.danger !== 5) fail(file, "world bosses are always danger 5");
    return { id, ...c, lore: body } as Creature;
  }).sort((a, b) => REGIONS.findIndex((r) => r.id === a.region) - REGIONS.findIndex((r) => r.id === b.region) || Number(a.boss ?? 0) - Number(b.boss ?? 0) || a.name.localeCompare(b.name));

  const byId = <T extends { id: string }>(list: T[]) => new Map(list.map((x) => [x.id, x]));
  const worldIsles = byId(world.isles), worldWinds = byId(world.winds);
  const isleNotes: IsleNote[] = entries(files, "isles", true).map(({ id, file, data, body }) => {
    if (!worldIsles.has(id)) fail(file, `"${id}" is not an isle id in worlds/first-shard.world.json (the file name is the isle id)`);
    return { id, blurb: body, ...data };
  });
  const windNotes: WindNote[] = entries(files, "winds", true).map(({ id, file, body }) => {
    if (!worldWinds.has(id)) fail(file, `"${id}" is not a wind id in worlds/first-shard.world.json (the file name is the wind id)`);
    return { id, blurb: body };
  });

  const rawStyles = entries(files, "architecture", true);
  const tables = styleTables(files, rawStyles.map((s) => ({ id: s.id, name: s.data.name })));
  const biomeIds = new Set(biomes.map((b) => b.id));
  const archStyles: ArchStyleText[] = rawStyles.map(({ id, file, data: a, body }) => {
    if (a.people) needPeople(file, a.people, "people");
    for (const b of a.biomes) if (!biomeIds.has(b)) fail(file, `biome "${b}" is not in concept/art-direction/biomes.md`);
    const t = tables.traits.get(id) ?? fail(file, `style "${a.name}" has no column in the core-idea table of concept/art-direction/architecture.md`);
    const grid = tables.grid.get(id) ?? fail(file, `style "${a.name}" has no row in "Modules per style" in concept/art-direction/modular-kit.md`);
    return {
      id, name: a.name, people: a.people ?? "", motto: t.motto, summary: body, traits: t.traits, grid,
      concept: Object.entries(a.concept).map(([id, label]) => ({ id, label })), kitSheets: Object.entries(a.kitSheets).map(([id, label]) => ({ id, label })),
      biomes: a.biomes,
    };
  });

  // Glossary: "## <Chapter title>" headings, then "- **Term**: definition" or "- **Term**: [source](path)"
  const short: Record<string, (id: string) => string | undefined> = {
    peoples: (id) => peopleEntries.find((p) => p.id === id)?.blurb,
    skills: (id) => skills.find((s) => s.id === id)?.summary,
    ships: (id) => ships.find((s) => s.id === id)?.summary,
    materials: (id) => materials.find((s) => s.id === id)?.summary,
    isles: (id) => { const n = isleNotes.find((s) => s.id === id); return n && firstSentence(n.blurb); },
    winds: (id) => { const n = windNotes.find((s) => s.id === id); return n && firstSentence(n.blurb); },
    bestiary: (id) => { const n = bestiary.find((s) => s.id === id); return n && firstSentence(n.lore); },
  };
  const GLOSSARY = "concept/glossary.md";
  const glossary: Term[] = [];
  let chapter: string | undefined;
  for (const line of (files["glossary.md"] ?? fail(GLOSSARY, "missing")).split("\n")) {
    const h = line.match(/^## (.+)$/);
    if (h) { chapter = chapters.find((c) => c.title === h[1].trim())?.slug ?? fail(GLOSSARY, `heading "${h[1]}" is not a chapter title (${chapters.map((c) => c.title).join(", ")})`); continue; }
    if (!/^[-*] /.test(line)) continue;
    const m = line.match(/^[-*] \*\*(.+?)\*\*:\s*(.+)$/) ?? fail(GLOSSARY, `"${line}" should be "- **Term**: definition"`);
    if (!chapter) fail(GLOSSARY, `term "${m[1]}" comes before the first "## <Chapter>" heading`);
    const link = m[2].trim().match(/^\[[^\]]+\]\(([^)#]*)(?:#([^)]+))?\)\.?$/);
    let definition = plain(m[2]);
    if (link) {
      const [, path, anchor] = link;
      const entry = path.match(/^entries\/([a-z]+)\/([^/]+)\.md$/);
      if (entry) definition = short[entry[1]]?.(entry[2]) ?? fail(GLOSSARY, `"${m[1]}" links to ${path}, which is not a catalogue entry`);
      else {
        const doc = files[path] ?? fail(GLOSSARY, `"${m[1]}" links to ${path}, which is not a concept doc`);
        const sec = anchor ? sectionByAnchor(splitFrontmatter(doc, path).body, anchor) : splitFrontmatter(doc, path).body;
        definition = (sec !== undefined ? paragraphs(sec).split("\n\n")[0] : "") || fail(GLOSSARY, `"${m[1]}" links to ${path}${anchor ? `#${anchor}` : ""}, which has no paragraph to show`);
      }
    }
    glossary.push({ term: plain(m[1]), definition, chapter: chapter! });
  }
  const dupTerm = glossary.find((t, i) => glossary.findIndex((o) => o.term.toLowerCase() === t.term.toLowerCase()) !== i);
  if (dupTerm) fail(GLOSSARY, `"${dupTerm.term}" is defined twice`);

  // Every entry file must belong to a known kind
  for (const path of Object.keys(files))
    if (path.startsWith("entries/") && !KINDS.some((k) => path.startsWith(`entries/${k}/`)))
      fail(`concept/${path}`, `is not under a known kind (${KINDS.join(", ")}), so no catalogue shows it`);

  return { peopleEntries, skills, materials, ships, bestiary, bodyPlans, REGIONS, isleNotes, windNotes, archStyles, glossary };
}

export type Concept = ReturnType<typeof loadConcept>;

/** The catalogue page path of an entry file (relative to concept/), for links and checks: "entries/isles/isle_x.md" → "isles/x" */
export function entryPage(path: string) {
  const m = path.match(/^entries\/([a-z]+)\/([^/]+)\.md$/);
  if (!m) return undefined;
  const [, kind, id] = m;
  return `${kind}/${id.replace(/^(isle|wind)_/, "")}`;
}
export { slugify };
