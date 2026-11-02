// Concept and kit reference sheets for catalogue entries, read from the plates of art/concept/<kind>/ and art/kit/<kind>/ (see
// scripts/handbook-sheets.ts). Sheets are discovered by file name; this file only decides which entry pages show them
// and how they are titled, so a new sheet whose name follows the pattern appears without editing anything.
import { plateKeys } from "../lib/art";
import { bestiary, bodyPlans } from "./bestiary";
import { materials } from "./materials";
import { skills } from "./skills";
import shard from "../../../../worlds/first-shard.world.json";

export interface Gallery { title: string; note: string; sheets: { art: string; label: string }[] }

const keys = plateKeys("sheets/");
const has = (stem: string) => keys.includes(`sheets/${stem}`);
const starting = (prefix: string) => keys.filter((k) => k.startsWith(`sheets/${prefix}`)).map((k) => k.slice("sheets/".length));

const LABELS: Record<string, string> = {
  "ships-kit-hulls": "Kit 1: hulls", "ships-kit-rigging": "Kit 2: masts and rigging", "ships-kit-sails": "Kit 3: sails and sail wear", "ships-kit-deck": "Kit 4: deck fittings",
  "bestiary-mount-tack": "Mount and pack tack",
  "peoples-gear-weapons-melee": "Melee weapons and shields by tier", "peoples-gear-weapons-ranged": "Ranged weapons and arcane foci by tier",
  "peoples-gear-armour-tiers": "Armour by material tier", "peoples-gear-clothing-kit": "Modular clothing kit",
  "skills-gathering-tools": "Gathering tools", "skills-crafting-stations-1": "Crafting stations 1", "skills-crafting-stations-2": "Crafting stations 2",
  "skills-innate": "The three innate skills", "winds-currents": "Lanes and wild currents",
  "world-storm-below": "The storm below", "world-drowned-vael": "Drowned Vael", "world-ancient-tree": "Ancient trees and Grudgewood",
  "world-sinking-stages": "The stages of a sinking", "world-newborn-isle": "An isle's birth", "world-relics": "Old-world relics",
};
const planName = (id: string) => (bodyPlans.find((b) => b.id === id)?.name ?? id).toLowerCase();
for (const b of bodyPlans) { LABELS[`bestiary-body-plans-${b.id}-body`] = "Base body and sockets"; LABELS[`bestiary-body-plans-${b.id}-parts`] = "Parts by socket"; }
const words = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replaceAll("-", " ");
const label = (stem: string, prefix = "") => LABELS[stem] ?? words(stem.slice(prefix.length));
const sheet = (stem: string, prefix = "") => ({ art: `sheets/${stem}`, label: label(stem, prefix) });
const gallery = (title: string, note: string, stems: string[], prefix = ""): Gallery[] =>
  stems.filter(has).length ? [{ title, note, sheets: stems.filter(has).map((s) => sheet(s, prefix)).sort((a, b) => a.label.localeCompare(b.label)) }] : [];

const WORLD = "World sheets";
const worldNote = "From the world brief: the storm, the drowned world and the life of an isle.";

const FAMILY: Record<string, string> = { Metal: "metals", Wood: "woods", Leather: "leathers", Cloth: "cloths", Stone: "stones" };

/** Galleries for a catalogue entry, shown below it */
export function conceptGalleries(kind: string, id: string): Gallery[] {
  switch (kind) {
    case "ships":
      return [
        ...gallery("Concept sheet", "Views and details for modelling.", [`ships-${id}`], "ships-"),
        ...gallery("Ship kit reference sheets", "Shared by all three ships: the modular pieces hulls and rigs are assembled from.", starting("ships-kit-")),
      ];
    case "bestiary": {
      const c = bestiary.find((x) => x.id === id);
      return [
        ...(c && has(`bestiary-body-plans-${c.bodyPlan}-body`)
          ? gallery("Species sheet", `This creature built on the ${planName(c.bodyPlan)} body plan: its parts, colour mask and storm-touched variant where there is one.`, [`bestiary-${id}`], "bestiary-")
          : gallery("Turnaround", "Front, side and back for modelling, with callouts and the storm-touched variant where there is one.", [`bestiary-${id}`], "bestiary-")),
        ...(c ? gallery("Body plan kit", `Shared by every ${planName(c.bodyPlan)} creature: one base body and rig, and the parts that snap onto its sockets.`, [`bestiary-body-plans-${c.bodyPlan}-body`, `bestiary-body-plans-${c.bodyPlan}-parts`]) : []),
        ...(c?.taming ? gallery("Tack", "Saddles and harness for tamed creatures.", ["bestiary-mount-tack"]) : []),
        ...(c?.region === "storm" ? gallery(WORLD, worldNote, ["world-storm-below"]) : []),
      ];
    }
    case "peoples":
      return [
        ...gallery("Base body", "Front, side and back in the rigging A-pose: the input for the 3D base model.", [`peoples-${id}-base-turnaround`], `peoples-${id}-`),
        ...gallery("Costume and customization sheets", "Outfits from starting clothes to heavy armour, and the signature features players customize.", starting(`peoples-${id}-`).filter((s) => s !== `peoples-${id}-base-turnaround`), `peoples-${id}-`),
        ...gallery("Shared gear sheets", "Made once and fitted to every people.", starting("peoples-gear-")),
      ];
    case "materials": {
      const m = materials.find((x) => x.id === id);
      const fam = m && FAMILY[m.family];
      return [
        ...gallery("Materials sheet", "All four tiers of the family: raw, refined, a crafted item and a texture swatch.", fam ? [`materials-${fam}`] : [], "materials-"),
        ...(m?.family === "Metal" || m?.family === "Leather" ? gallery("Gear by tier", "How the material shows on gear.", ["peoples-gear-armour-tiers", ...(m.family === "Metal" ? ["peoples-gear-weapons-melee"] : [])]) : []),
        ...(id === "relic" ? gallery(WORLD, worldNote, ["world-relics"]) : []),
      ];
    }
    case "isles": {
      const isle = shard.isles.find((i) => i.id === `isle_${id}`) as { name: string; state?: string } | undefined;
      if (isle) LABELS[`isles-${id}-portrait`] ??= isle.name;
      return [
        ...gallery("Isle portrait", "Top, edge and underside together.", [`isles-${id}-portrait`], "isles-"),
        ...gallery(WORLD, worldNote, [
          ...(isle?.state === "sinking" ? ["world-sinking-stages"] : []),
          ...(id === "grudgewood" ? ["world-ancient-tree"] : []),
          ...(id === "vael-s-shadow" ? ["world-drowned-vael", "world-relics"] : []),
        ]),
      ];
    }
    case "skills": {
      const s = skills.find((x) => x.id === id);
      const g = s?.group;
      const extra: string[] = [
        `skills-magic-${id}`,
        ...(g === "Innate" ? ["skills-innate"] : []),
        ...(g === "Gathering" ? ["skills-gathering-tools"] : []),
        ...(g === "Crafting" ? ["skills-crafting-stations-1", "skills-crafting-stations-2"] : []),
        ...(g === "Weapons" ? [["bows", "thrown"].includes(id) ? "peoples-gear-weapons-ranged" : "peoples-gear-weapons-melee"] : []),
        ...(g === "Arcane" ? ["peoples-gear-weapons-ranged"] : []),
        ...(["light-armour", "heavy-armour"].includes(id) ? ["peoples-gear-armour-tiers"] : []),
        ...(["tailoring", "leatherworking"].includes(id) ? ["peoples-gear-clothing-kit"] : []),
        ...(["sailing", "shipwright", "sailweaving"].includes(id) ? starting("ships-kit-") : []),
        ...(id === "taming" ? ["bestiary-mount-tack"] : []),
        ...(id === "treetending" ? ["world-ancient-tree", "world-sinking-stages"] : []),
        ...(id === "salvage" ? ["world-drowned-vael", "world-relics"] : []),
        ...(id === "lore" ? ["world-relics", "world-newborn-isle"] : []),
      ];
      return gallery("Concept sheets", "Effects, tools and gear for this skill.", extra, "skills-");
    }
    case "winds":
      return gallery("Concept sheet", "How currents look in the sky.", ["winds-currents"]);
    default:
      return [];
  }
}
