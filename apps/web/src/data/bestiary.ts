// The bestiary: stat blocks for every creature and world boss, from concept/entries/bestiary/<id>.md.
// Design rules live in concept/monsters/README.md. Regions are the biomes of concept/art-direction/biomes.md, plus the
// open sky and the storm below.
import { concept } from "./concept";

export type Temperament = "passive" | "neutral" | "territorial" | "hostile";
export type Size = "tiny" | "small" | "medium" | "large" | "huge" | "colossal";
export type Tier = "safe" | "guarded" | "wild";
/** A biome id from concept/art-direction/biomes.md, "sky" or "storm" */
export type Region = string;

export const REGIONS: { id: Region; name: string }[] = concept.REGIONS;

export const DANGER = ["", "Harmless", "Low", "Moderate", "High", "Deadly"] as const;

export interface Creature {
  id: string;
  name: string;
  boss?: boolean;
  family: string;
  size: Size;
  temperament: Temperament;
  /** 1–5; world bosses are always 5 */
  danger: 1 | 2 | 3 | 4 | 5;
  region: Region;
  tiers: Tier[];
  habitat: string;
  active: string;
  seasons: string;
  health: number;
  stamina: number;
  /** metres per second */
  speed: { walk?: number; climb?: number; swim?: number; fly?: number };
  /** The same 0–100 skills players use */
  skills: Record<string, number>;
  senses: string;
  behaviours: string[];
  actions: { name: string; text: string }[];
  drops: string[];
  population?: string;
  taming?: { use: "Ground mount" | "Pack animal" | "Flying mount"; skill: number };
  storm?: { name: string; text: string };
  lore: string;
  quote: { text: string; by: string };
  /** Subject brief for the bestiary plate */
  art: string;
}

export const bestiary: Creature[] = concept.bestiary;
