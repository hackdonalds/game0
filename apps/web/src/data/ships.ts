// The three ship sizes. Source for the site's ship pages and for each ship's painted plate.
// Design rules live in concept/sailing/README.md. Numbers marked "(draft)" are not decided yet.

import type { Ship } from "./types";

export const ships: Ship[] = [
  {
    id: "skiff",
    name: "Skiff",
    aboard: 5,
    steeredBy: "1: one person steers and trims the sails",
    summary: "A small, nimble boat for short hops, solo hauls and small groups.",
    description:
      "The skiff is the first ship most players ride, on the trip from their home isles to the nearest Accord town. One skipper handles both tiller and sail, so it is easy to learn and quick to turn. It carries little cargo and little armour, which makes it a favourite target for gale hawks on wild routes.",
    roles: [
      { name: "Skipper", text: "Steers and trims the single sail. Their Sailing skill decides how well the skiff holds a course." },
      { name: "Lookout", text: "Watches for gale hawks, skyrays and other ships, and calls the wind ahead." },
      { name: "Archers and casters", text: "Defend from the open deck. A Wind caster can fill the sail in calm air." },
    ],
    stats: [
      { label: "Aboard", value: "Up to 5" },
      { label: "Steered by", value: "1" },
      { label: "Cargo", value: "Small: about 10 crates (draft)" },
      { label: "Speed", value: "Quick to turn, modest top speed (draft)" },
      { label: "Sail wear", value: "Light; one sail to re-enchant (draft)" },
    ],
    building: "Shipwright 25 and Sailweaving 25 for the sail. Meadow birch or rootwood planks, copper fittings and one plain sailcloth (draft).",
    uses: ["Short trips between nearby isles", "Solo and small-group hauls", "Scouting wild currents", "Reaching sinking isles quickly"],
    art: "a small single-masted wooden skiff with a glowing teal-patterned sail, gliding along a wind current between floating isles at morning",
  },
  {
    id: "cutter",
    name: "Cutter",
    aboard: 10,
    steeredBy: "1: one person steers and trims the sails",
    summary: "A fast, sturdy ship for hauling and raiding, steered by a single skipper.",
    description:
      "The cutter is the working ship of the sky lanes. It is fast enough to outrun trouble and big enough to carry a real cargo or a full group of fighters. One skipper still steers and trims, so a cutter is only as good as the hands on its wheel.",
    roles: [
      { name: "Skipper", text: "Steers and trims the sails. Needs Sailing 50." },
      { name: "Lookout", text: "Watches the sky from the mast and reads the wind ahead." },
      { name: "Archers and casters", text: "Fight from the deck against flying creatures and enemy crews." },
      { name: "Repair crew", text: "Patch the hull with Carpentry and mend sails with Sailweaving during the voyage." },
    ],
    stats: [
      { label: "Aboard", value: "Up to 10" },
      { label: "Steered by", value: "1" },
      { label: "Cargo", value: "Medium: about 40 crates (draft)" },
      { label: "Speed", value: "The fastest ship when well trimmed (draft)" },
      { label: "Sail wear", value: "Moderate; two sails to re-enchant (draft)" },
    ],
    building: "Shipwright 50 and Sailweaving 50 for the sails. Rootwood or duskcrown yew planks, iron fittings and two plain sailcloths (draft).",
    uses: ["Hauling trade goods between Accord towns", "Group trips to wild isles and the rim", "Raiding and defending cargo in open-PvP sky", "Chasing storm surges and world bosses"],
    art: "a sleek two-masted wooden cutter leaning into a strong wind, sails taut and glowing teal at the seams, golden sunset clouds below",
  },
  {
    id: "galleon",
    name: "Galleon",
    aboard: 100,
    steeredBy: "2: a helmsman steers while a sailmaster works the sails",
    summary: "A great ship for guilds, big cargo and long voyages, crewed like a floating town.",
    description:
      "A galleon carries up to a hundred people and a hold full of goods. It is too big for one pair of hands: the helmsman steers while the sailmaster works the sails, and the two must work as one. A galleon is a guild's pride and a target the whole shard can see coming.",
    roles: [
      { name: "Helmsman", text: "Steers the ship and chooses its heading against the wind. Needs Sailing 75." },
      { name: "Sailmaster", text: "Works the sails and calls the trim to the crew. Needs Sailing 75." },
      { name: "Lookout", text: "Watches the sky from the crow's nest for creatures, ships and storm surges." },
      { name: "Archers and casters", text: "Line the rails to defend the ship. Wind casters can fill the sails in calm air." },
      { name: "Repair crew", text: "Patch the hull and mend sails during the voyage and after fights." },
      { name: "Boarding party", text: "Fighters who cross to enemy ships when the decks come close (draft)." },
    ],
    stats: [
      { label: "Aboard", value: "Up to 100" },
      { label: "Steered by", value: "2" },
      { label: "Cargo", value: "Large: about 400 crates (draft)" },
      { label: "Speed", value: "Slow to turn, strong in steady lanes (draft)" },
      { label: "Sail wear", value: "Heavy; many sails to re-enchant (draft)" },
    ],
    building: "Shipwright 75 and Sailweaving 75 for the great sails. Many duskcrown yew planks, skysteel fittings and a full set of sailcloth, usually gathered by a whole guild (draft).",
    uses: ["Guild trade runs with huge cargo", "Moving big groups to sinking-isle events and isle births", "Fighting world bosses like the Tempest Serpent from the deck", "Carrying settlers off a sinking isle"],
    art: "a towering three-masted wooden galleon with gold trim and many glowing teal sails, sailing past a giant ancient tree on a floating isle",
  },
];
