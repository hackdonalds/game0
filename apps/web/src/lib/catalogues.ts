// One registry for every catalogue: cards for the index pages and the hub, facets for filtering, and text for search.
import shard from "../../../../worlds/first-shard.world.json";
import { bestiary, DANGER, REGIONS } from "../data/bestiary";
import { peopleEntries } from "../data/peoples-handbook";
import { skills } from "../data/skills";
import { isleNotes } from "../data/isles";
import { windNotes } from "../data/winds";
import { ships } from "../data/ships";
import { materials } from "../data/materials";
import { glossary } from "../data/glossary";
import { archStyles } from "../data/architecture";
import { biomes } from "../data/biomes";
import { base, cap, sortName } from "./text";

export interface Card {
  id: string;
  name: string;
  subtitle: string;
  summary: string;
  art: string;
  tone: string;
  href: string;
  /** Filter facets: facet name → value */
  facets: Record<string, string>;
  /** Small badges shown on the card */
  badges?: { label: string; class?: string }[];
  search: string;
}

export interface Catalogue {
  slug: string;
  title: string;
  kicker: string;
  summary: string;
  /** Facets offered as filters on the index, in order */
  filters: string[];
  cards: Card[];
  /** Hub cover: the art key of a representative entry */
  cover: string;
  /** Entries have their own pages */
  pages: boolean;
}

export const TONE: Record<string, string> = {
  meadow: "#5d8a3a", forest: "#3f7a3a", roothold: "#6b4e36", crag: "#7d766c", garden: "#7fa84a", lagoon: "#178f84", ruin: "#a5835a",
  meadows: "#5d8a3a", rootholds: "#6b4e36", gardens: "#7fa84a", crags: "#7d766c", sky: "#4f86b8", rim: "#b8552f", storm: "#4b3f78",
  galeborne: "#4f86b8", anchorkin: "#6c6a78", rootwarden: "#6b4e36",
  moorings: "#178f84", mooring: "#178f84", accord: "#a5772c", "old-world": "#a5835a",
  Metal: "#7d766c", Wood: "#7a5d44", Leather: "#9a5b3a", Cloth: "#5b6fa0", Stone: "#8c857c",
  Weapons: "#9b3f24", Arcane: "#5b4a86", "Defence and survival": "#3f6f8f", Gathering: "#5d8a3a", Crafting: "#a5772c", "Travel and lore": "#178f84", Innate: "#b08a2e",
};

export type ShardIsle = (typeof shard.isles)[number];
export type ShardWind = (typeof shard.winds)[number];
export const isleSlug = (id: string) => id.replace(/^isle_/, "");
export const windSlug = (id: string) => id.replace(/^wind_/, "");
export const peopleName = (id: string) => peopleEntries.find((p) => p.id === id)?.name ?? cap(id);

const region = (id: string) => REGIONS.find((r) => r.id === id)!.name;
const href = (kind: string, id: string) => `${base}/catalogue/${kind}/${id}/`;
const words = (...xs: (string | string[] | undefined)[]) => xs.flat().filter(Boolean).join(" ").toLowerCase();

const bestiaryCards: Card[] = bestiary.map((c) => ({
  id: c.id, name: c.name, subtitle: `${cap(c.size)} ${c.family.toLowerCase()} · ${c.temperament}`, summary: c.lore,
  art: `bestiary/${c.id}`, tone: TONE[c.region], href: href("bestiary", c.id),
  facets: { Region: region(c.region), Temperament: cap(c.temperament), Danger: c.boss ? "World boss" : DANGER[c.danger], Tameable: c.taming ? "Tameable" : "" },
  badges: [{ label: c.boss ? "World boss" : `Danger ${c.danger}` }],
  search: words(c.name, c.family, c.habitat, c.drops, Object.keys(c.skills), c.lore),
}));

const peopleCards: Card[] = peopleEntries.map((p) => ({
  id: p.id, name: p.name, subtitle: p.homeland, summary: p.blurb, art: `peoples/${p.id}`, tone: TONE[p.id], href: href("peoples", p.id),
  facets: {}, search: words(p.name, p.homeland, p.look, p.culture, p.knownFor, p.affinities),
}));

const skillCards: Card[] = [...skills].map((s) => ({
  id: s.id, name: s.name, subtitle: s.group, summary: s.summary, art: `skills/${s.id}`, tone: TONE[s.group], href: href("skills", s.id),
  facets: { Group: s.group, Affinity: s.affinity.map(peopleName).join(", ") },
  search: words(s.name, s.group, s.summary, s.description, s.sources, s.uses, s.milestones.map((m) => m.name)),
}));

const notes = new Map(isleNotes.map((n) => [n.id, n]));
const isleCards: Card[] = [...shard.isles].sort((a, b) => a.name.localeCompare(b.name)).map((i) => {
  const n = notes.get(i.id);
  const who = i.people !== "none" ? peopleName(i.people) : i.town ? "Accord town" : "Unclaimed";
  return {
    id: isleSlug(i.id), name: i.name, subtitle: `${who} · ${i.biome}`, summary: n?.blurb ?? "", art: `isles/${i.id}`, tone: TONE[i.biome],
    href: href("isles", isleSlug(i.id)),
    facets: { Tier: cap(i.tier), Biome: cap(i.biome), People: who, State: i.state === "stable" ? "" : cap(i.state) },
    badges: [{ label: cap(i.tier), class: `tier tier-${i.tier}` }, ...(i.state !== "stable" ? [{ label: cap(i.state) }] : [])],
    search: words(i.name, i.biome, who, i.tier, n?.blurb, n?.landmarks, n?.resources),
  };
});

const windNoteMap = new Map(windNotes.map((n) => [n.id, n]));
const windCards: Card[] = shard.winds.map((w) => ({
  id: windSlug(w.id), name: w.name, subtitle: `${w.kind === "lane" ? "Accord lane" : "Wild current"} · ${w.strength} m/s`,
  summary: windNoteMap.get(w.id)?.blurb ?? "", art: "", tone: w.kind === "lane" ? "#4f86b8" : "#b8552f", href: href("winds", windSlug(w.id)),
  facets: { Kind: w.kind === "lane" ? "Accord lane" : "Wild current" },
  badges: [{ label: w.kind === "lane" ? "Guarded" : "Wild", class: `tier tier-${w.kind === "lane" ? "guarded" : "wild"}` }],
  search: words(w.name, w.kind, windNoteMap.get(w.id)?.blurb),
}));

const shipCards: Card[] = ships.map((s) => ({
  id: s.id, name: s.name, subtitle: `Up to ${s.aboard} aboard · ${s.steeredBy}`, summary: s.summary, art: `ships/${s.id}`, tone: "#7a5d44",
  href: href("ships", s.id), facets: {}, search: words(s.name, s.summary, s.description, s.uses),
}));

const materialCards: Card[] = [...materials].sort((a, b) => a.family.localeCompare(b.family) || a.tier - b.tier).map((m) => ({
  id: m.id, name: m.name, subtitle: `${m.family} · tier ${m.tier}`, summary: m.summary, art: `materials/${m.id}`, tone: TONE[m.family],
  href: href("materials", m.id), facets: { Family: m.family, Tier: `Tier ${m.tier}` },
  badges: m.draft ? [{ label: "Draft", class: "draft" }] : [],
  search: words(m.name, m.family, m.summary, m.where, m.usedFor),
}));

const glossaryCards: Card[] = [...glossary].sort((a, b) => sortName(a.term).localeCompare(sortName(b.term))).map((t) => ({
  id: t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name: t.term, subtitle: "", summary: t.definition, art: "", tone: "var(--teal)",
  href: `${base}/catalogue/glossary/#${t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`, facets: { Chapter: t.chapter }, search: words(t.term, t.definition),
}));

const archCards: Card[] = archStyles.map((a) => ({
  id: a.id, name: a.name, subtitle: `${a.motto} · ${a.kit.pieces.length} pieces, ${a.kit.prefabs.length} prefabs`, summary: a.summary,
  art: `architecture/${a.id}-${a.concept[0].id}`, tone: TONE[a.id], href: href("architecture", a.id),
  facets: {},
  search: words(a.name, a.motto, a.summary, a.traits.map((t) => t.value), a.kit.materials, a.kit.prefabs.map((p) => p.name)),
}));

const biomeCards: Card[] = biomes.map((b) => ({
  id: b.id, name: b.name, subtitle: `${b.altitude} up · ${shard.isles.filter((i) => i.biome === b.id).length} isles`, summary: b.summary,
  art: `biomes/${b.id}-isle-portrait`, tone: TONE[b.id], href: href("biomes", b.id), facets: {},
  search: words(b.name, b.summary, b.look.map((l) => l.value), b.signature, b.creatures, shard.isles.filter((i) => i.biome === b.id).map((i) => i.name)),
}));

export const catalogues: Catalogue[] = [
  { slug: "peoples", title: "Peoples", kicker: "Three peoples, one sky", summary: "The three playable peoples: look, culture, homeland, innate skill, starting point and old grudges.", filters: [], cards: peopleCards, cover: "peoples/galeborne", pages: true },
  { slug: "bestiary", title: "Bestiary", kicker: "Field guide", summary: "Every creature and world boss, with stats, habitats, actions and lore.", filters: ["Region", "Temperament", "Tameable"], cards: bestiaryCards, cover: "bestiary/crag-drake", pages: true },
  { slug: "skills", title: "Skills", kicker: "Everything is a skill", summary: "All the skills, where to learn them, and what each unlocks at 25, 50, 75 and 100.", filters: ["Group"], cards: skillCards, cover: "skills/wind", pages: true },
  { slug: "isles", title: "Isles and places", kicker: "The First Shard", summary: "Every isle of the First Shard: who lives there, its risk tier, landmarks and resources.", filters: ["Tier", "Biome", "State"], cards: isleCards, cover: "isles/isle_accord-hall", pages: true },
  { slug: "winds", title: "Wind currents", kicker: "Lanes and currents", summary: "The charted Accord lanes and the fast, dangerous wild currents.", filters: ["Kind"], cards: windCards, cover: "", pages: true },
  { slug: "ships", title: "Ships", kicker: "Skiff, cutter, galleon", summary: "The three ship sizes: crew, steering, cargo and wear.", filters: [], cards: shipCards, cover: "ships/galleon", pages: true },
  { slug: "materials", title: "Materials and gear", kicker: "Tiers by material", summary: "Material tiers set gear tiers. Where each is found and what it makes.", filters: ["Family", "Tier"], cards: materialCards, cover: "materials/skysteel", pages: true },
  { slug: "architecture", title: "Architecture", kicker: "How each people builds", summary: "The five building styles: concept sheets, modular kit references and the built kits, piece by piece.", filters: [], cards: archCards, cover: "architecture/rootwarden-landmark-root-village", pages: true },
  { slug: "biomes", title: "Biomes", kicker: "Seven kinds of isle", summary: "The look of every biome from crag to lagoon: ground, rock, plants, water and the isles that wear it.", filters: [], cards: biomeCards, cover: "biomes/meadow-isle-portrait", pages: true },
  { slug: "glossary", title: "Glossary", kicker: "Words of the sky", summary: "Every term in the handbook, in a sentence or two.", filters: ["Chapter"], cards: glossaryCards, cover: "", pages: false },
];

export const catalogue = (slug: string) => catalogues.find((c) => c.slug === slug)!;
