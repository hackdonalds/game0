// Shapes of the handbook's catalogue data. Each catalogue lives in its own file in this folder.
// Every entry with an `art` prompt gets a painted plate from scripts/handbook-art.ts.

export type PeopleId = "galeborne" | "anchorkin" | "rootwarden";

export type SkillGroup = "Weapons" | "Arcane" | "Defence and survival" | "Gathering" | "Crafting" | "Travel and lore" | "Innate";

export interface Skill {
  id: string;
  name: string;
  group: SkillGroup;
  /** One sentence */
  summary: string;
  /** Two or three sentences */
  description: string;
  /** Where it can be learned: named trainers and places on the First Shard, books, places tied to the skill */
  sources: string[];
  /** Peoples with a cultural affinity for it */
  affinity: PeopleId[];
  /** What it's used for in play */
  uses: string[];
  /** What unlocks at 25 / 50 / 75 / 100. Techniques for combat and arcane skills; recipes, abilities or access for the rest */
  milestones: { level: 25 | 50 | 75 | 100; name: string; text: string }[];
  art: string;
}

export interface Ship {
  id: string;
  name: string;
  aboard: number;
  steeredBy: string;
  summary: string;
  description: string;
  roles: { name: string; text: string }[];
  stats: { label: string; value: string }[];
  /** Shipwright level and materials, marked draft where undecided */
  building: string;
  uses: string[];
  art: string;
}

export type MaterialFamily = "Metal" | "Wood" | "Leather" | "Cloth" | "Stone";

export interface Material {
  id: string;
  name: string;
  family: MaterialFamily;
  /** 1 = commonest. Gear tier comes from the material */
  tier: 1 | 2 | 3 | 4;
  summary: string;
  description: string;
  where: string;
  gatheredWith: string;
  usedFor: string[];
  /** True when the concept docs haven't decided this material yet */
  draft: boolean;
  art: string;
}

export interface IsleNote {
  /** Matches the isle id in worlds/first-shard.world.json */
  id: string;
  blurb: string;
  landmarks: string[];
  resources: string[];
  art: string;
}

export interface WindNote {
  /** Matches the wind id in worlds/first-shard.world.json */
  id: string;
  blurb: string;
}

export interface Term {
  term: string;
  definition: string;
  /** Chapter slug it belongs to: vision, world, peoples, play, sailing, economy, creatures, society, simulation, art */
  chapter: string;
}

export interface PeopleEntry {
  id: PeopleId;
  name: string;
  homeland: string;
  /** Short line for cards */
  blurb: string;
  look: string;
  culture: string;
  knownFor: string;
  affinities: string[];
  start: string;
  relations: { with: PeopleId; kind: "ally" | "rival" | "trade" | "wary"; text: string }[];
  /** The one skill only this people can learn */
  innate: { name: string; text: string; limit: string };
  signature: { customizable: string[]; locked: string[] };
  quote: { text: string; by: string };
  art: string;
}
