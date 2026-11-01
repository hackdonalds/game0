// Handbook entries for the five playable peoples, in lineup order.
// Sources: concept/world/README.md, concept/world/peoples.md, concept/art-direction/character-customization.md,
// concept/mechanics/README.md (skills and first hours). The short card data stays in peoples.ts.

import type { PeopleEntry } from "./types";

export const peopleEntries: PeopleEntry[] = [
  {
    id: "rootborn",
    name: "Rootborn",
    homeland: "The Rootholds",
    blurb: "Bark-skinned and slow to age, they live in the roots beneath the oldest isles and believe the ancient trees hold back the sinking.",
    look: "Broad and stocky, with bark-grained wooden skin. Moss and lichen grow on their shoulders and in their beards, and their gear is carved from stone.",
    culture:
      "The Rootborn live in caverns carved among the roots of the oldest isles. They tend the ancient trees day and night, because they believe the roots slow an isle's sinking. They are right, though no tending can save an isle once it starts to fall. They age slowly, think slowly and hold a grudge for a very long time.",
    knownFor: "Stonewrights and keepers of the old trees.",
    affinities: ["Bloom", "Stone", "Stonecraft", "Woodcutting", "Herbalism", "Heavy Weapons"],
    start: "Elderroot, the shrine isle of the Rootholds, in guarded space. The first quests teach tending and gathering among the roots, then a skiff ride down the Rootward lane to Tetherport.",
    relations: [
      { with: "mossback", kind: "ally", text: "Old allies who tend the land together. The Rootholds sit beside the Garden Isles, and Tetherport is their shared town." },
      { with: "skerrin", kind: "rival", text: "The Rootborn say Skerrin mining weakens isles and hastens the sinking. The quarrel over Grudgewood has never been settled." },
      { with: "rillfolk", kind: "trade", text: "No old quarrel. Rillfolk traders buy Rootborn stonework and bring fish and lagoon goods north." },
      { with: "veiled", kind: "ally", text: "A people who lost their city to the sinking find a quiet welcome among those who fight it. Veiled caravans often guard Rootborn groves for hire." },
    ],
    signature: {
      customizable: ["Wood type (oak, birch, cedar, ashen)", "Bark pattern", "Growth (moss, lichen, flowers, mushrooms)", "Beard foliage", "Crystal inlays"],
      locked: ["Bark skin", "Plant growth"],
    },
    quote: { text: "Every root you cut is a year the isle won't have.", by: "Elder Hollowgrain, Rootborn" },
    art: "a broad, stocky Rootborn with bark-grained oak skin, moss and lichen on the shoulders, a beard of moss and small white flowers, teal crystal inlays in the brow, wearing carved stone shoulder plates over leather, waist-up three-quarter view, standing among the giant glowing roots of an ancient tree in a root cavern",
  },
  {
    id: "veiled",
    name: "Veiled Ones",
    homeland: "Lost Vael",
    blurb: "Their city sank generations ago. They wander in oath-caravans and wear masks as a mourning vow, until Vael is raised.",
    look: "Very tall and always masked, with no visible face. They wrap themselves in living cloth embroidered with shimmering oath markings.",
    culture:
      "Vael sank generations ago, and the Veiled have had no homeland since. They travel the sky lanes in oath-caravans, bound by sworn vows. Their masks are a mourning vow, worn until Vael is raised. An oath given by one of the Veiled is kept, and every oath kept is stitched into their cloth.",
    knownFor: "Oath-keepers, mercenaries and envoys.",
    affinities: ["Oathcraft", "Blades", "Polearms", "Wind", "Sailing", "Lore"],
    start: "Aboard an oath-caravan travelling the Accord lanes, in guarded space. Their first steps happen on deck and at the caravan's stops, which end at an Accord town.",
    relations: [
      { with: "rillfolk", kind: "rival", text: "Rillfolk divers bring up relics from the drowned world. To the Veiled, that is robbing the dead of Vael." },
      { with: "mossback", kind: "rival", text: "The Mossback Ledger records that Vael sank because of a broken oath. The Veiled say the Ledger lies." },
      { with: "rootborn", kind: "ally", text: "The Rootborn fight the sinking that took Vael. Veiled envoys speak well of them, and many caravans take Rootborn contracts." },
      { with: "skerrin", kind: "trade", text: "Skerrin hire Veiled swords to guard ore convoys and claims. The Veiled ask no questions, only that the contract is kept." },
    ],
    signature: {
      customizable: ["Mask shape", "Mask engraving", "Mask material", "Eye-glow colour through the slits", "Oath markings on the cloth", "Drape style", "Height"],
      locked: ["Mask always on", "Face never shown"],
    },
    quote: { text: "We will take the mask off in Vael. Not one day before.", by: "Oathbearer Sefa, of the Ninth Caravan" },
    art: "a very tall Veiled One in a smooth engraved pale mask with no visible face, soft teal light glowing through the eye slits, wrapped in flowing layered cloth embroidered with shimmering gold oath markings, waist-up three-quarter view, standing on the deck of a caravan sailship among the clouds, embroidered banners behind",
  },
  {
    id: "mossback",
    name: "Mossbacks",
    homeland: "The Garden Isles",
    blurb: "Patient tortoise-folk who carry gardens on their shells and keep the Ledger, the record of every isle that has ever sunk.",
    look: "Tortoise-folk who carry a small garden and a shrine on a domed shell.",
    culture:
      "Mossbacks are slow, patient and have long memories. They farm the terraced Garden Isles and keep the Ledger, the record of every isle that has ever sunk. Every Mossback grows a small garden on their own shell, and it grows with them. Their caravans move slowly but always arrive.",
    knownFor: "Farmers, caravan masters and record keepers.",
    affinities: ["Herbalism", "Cooking", "Alchemy", "Taming", "Lore", "Shields"],
    start: "Ledgerhome, the shrine isle of the Garden Isles, in guarded space. The first quests teach farming and gathering on the terraces, then a skiff ride down the Gardenward lane to Windmarket.",
    relations: [
      { with: "rootborn", kind: "ally", text: "Old allies who tend the land together. Rootborn trees and Mossback fields have kept each other alive for ages." },
      { with: "veiled", kind: "rival", text: "The Ledger records that Vael sank because of a broken oath. Mossbacks will not change the Ledger, and the Veiled will not forgive it." },
      { with: "rillfolk", kind: "trade", text: "Rillfolk traders carry Mossback grain to every market. Windmarket, between their homelands, runs on their trade." },
      { with: "skerrin", kind: "wary", text: "Every isle the Skerrin dig is an isle the Ledger watches. Mossbacks buy their iron, but they write down where it came from." },
    ],
    signature: {
      customizable: ["Shell shape and pattern", "Shell garden (plants and shrine type)", "Scale pattern", "Beak shape"],
      locked: ["Shell", "Shell garden"],
    },
    quote: { text: "It is written. That is the end of the argument, not the start of it.", by: "Ledgerkeeper Ommeth, Mossback" },
    art: "an elderly Mossback tortoise-person with a high domed shell carrying a small flowering garden and a tiny stone shrine, green-brown scales, a gentle beaked face, wearing a woven cloth robe with gold trim and a satchel of scrolls, waist-up three-quarter view, standing on green terraced fields with a domed stone vault behind",
  },
  {
    id: "skerrin",
    name: "Skerrin",
    homeland: "The Crag Spires",
    blurb: "Sure-hooved goat-folk of the sheer cliff isles. They dig deep for stone and ore, and they don't believe the Rootborn's warnings.",
    look: "Lean goat-folk with large curled horns and sure-footed hooves.",
    culture:
      "The Skerrin live on the cliffs and undersides of the Crag Spires, the highest isles on the shard. They herd cliff goats, climb anything and dig into the isles for stone and ore. They call Rootborn warnings about mining superstition. A Skerrin's horns tell their story, carved and ringed for every deed.",
    knownFor: "Miners, climbers and herders.",
    affinities: ["Mining", "Climbing", "Smithing", "Taming", "Heavy Weapons", "Thrown"],
    start: "High Spire, the shrine isle of the Crag Spires, in guarded space. The first quests teach climbing and mining on the spire, then a skiff ride down the Spireward lane to Oathgate.",
    relations: [
      { with: "rillfolk", kind: "trade", text: "Trade partners of long standing: Skerrin ore for Rillfolk goods and relics. Lanterncross, between their homelands, weighs both." },
      { with: "rootborn", kind: "rival", text: "The Rootborn say Skerrin mining hastens the sinking. The Skerrin call it superstition, and Grudgewood's ore is still unmined." },
      { with: "veiled", kind: "trade", text: "Skerrin hire Veiled mercenaries to guard their claims on the wild rim. Both sides like a clear contract." },
      { with: "mossback", kind: "wary", text: "The Mossbacks buy Skerrin iron and then write down where it came from. The Skerrin do not like being written down." },
    ],
    signature: {
      customizable: ["Horn shape (ram, ibex, spiral, broken)", "Horn rings and carvings", "Fur colour and pattern", "Beard", "Ear tags"],
      locked: ["Horns", "Hooves"],
    },
    quote: { text: "The isle is stone. Stone doesn't mind.", by: "Forewoman Brannick of Ironcleft, Skerrin" },
    art: "a lean Skerrin goat-person with large curled ram horns ringed with bronze and carved with marks, grey-brown fur, a short beard and ear tags, wearing a leather mining harness with a pick over the shoulder and a coil of rope, waist-up three-quarter view, standing on a narrow cliff ledge of a towering rock spire high above the clouds",
  },
  {
    id: "rillfolk",
    name: "Rillfolk",
    homeland: "The Glimmer Lagoons",
    blurb: "Otter-folk traders who move between every people, and the only divers who dare the drowned world below.",
    look: "Sleek otter-folk with glossy fur.",
    culture:
      "The Rillfolk live on the Glimmer Lagoons, the lowest isles, where the water glows and the storm is close below. They trade between every people and cook better than any of them. They are the only people who dive into the drowned world, and they know more about it than anyone alive.",
    knownFor: "River traders, divers and cooks.",
    affinities: ["Salvage", "Fishing", "Cooking", "Tide", "Sailing", "Daggers"],
    start: "Glimmerpool, the shrine isle of the Glimmer Lagoons, in guarded space. The first quests teach fishing and a first shallow dive, then a skiff ride up the Lagoonward lane to Lanterncross.",
    relations: [
      { with: "skerrin", kind: "trade", text: "Trade partners: Rillfolk goods and relics for Skerrin ore. The two homelands sit side by side across Lanterncross." },
      { with: "veiled", kind: "rival", text: "The Veiled say diving robs the dead of Vael. The Rillfolk say the dead don't need their relics, and keep diving." },
      { with: "mossback", kind: "trade", text: "Mossback grain and Rillfolk fish fill Windmarket's stalls. A friendly trade, if a slow one." },
      { with: "rootborn", kind: "trade", text: "No grudge, only business. Rillfolk carry lagoon goods north and bring carved stone back." },
    ],
    signature: {
      customizable: ["Fur colour and pattern", "Whisker style", "Facial markings", "Tail shape and ornaments"],
      locked: ["Tail", "Otter head"],
    },
    quote: { text: "Everything sinks in the end. Best to be the one waiting at the bottom.", by: "Tessaly Quickwater, Rillfolk diver" },
    art: "a sleek Rillfolk otter-person with glossy dark brown fur, pale whisker markings and long whiskers, wearing a fitted leather diving harness with brass clasps, a net bag of glinting relics and shell beads, waist-up three-quarter view, standing on a wooden boardwalk beside a lagoon glowing teal at dusk",
  },
];
