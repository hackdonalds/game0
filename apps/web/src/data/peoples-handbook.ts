// Handbook entries for the playable peoples, in lineup order.
// Sources: concept/world/README.md, concept/world/peoples.md, concept/art-direction/character-customization.md,
// concept/mechanics/README.md (skills and first hours).

import type { PeopleEntry } from "./types";

export const peopleEntries: PeopleEntry[] = [
  {
    id: "galeborne",
    name: "Galeborne",
    homeland: "The Crag Spires",
    blurb: "Hollow-boned, feather-mantled folk of the highest isles. They glide where others need a ship, and they build the best ships in the sky.",
    look: "Tall, light and narrow, with hollow bones. A feathered mantle grows from their shoulders and forearms and folds against the body like a cloak. Their skin runs from sky-pale to dusk-blue, and a crest of feathers takes the place of hair.",
    culture:
      "The Galeborne nest on the sheer Crag Spires, the highest isles on the shard, where the wind never stops. A Galeborne child learns to glide before they learn to swim. They are the best sailors and shipwrights in the sky, and their couriers carry word between every town. They build masts and hulls from the ancient wood the Rootwardens guard, and they don't see why a tree should outlive the people who need it. When an isle sinks, the Galeborne are the first off it and the last to mourn it.",
    knownFor: "Sailors, shipwrights, scouts and couriers.",
    affinities: ["Sailing", "Shipwright", "Wind", "Bows", "Evasion", "Sailweaving"],
    innate: {
      name: "Glide",
      text: "Spread the mantle to glide down from any height without fall damage. Riding a wind current, a Galeborne can glide between nearby isles without a ship. Higher skill gives longer glides and lets them catch updrafts.",
      limit: "Costs stamina. Can't gain height without an updraft, and can't glide while carrying a heavy load.",
    },
    start: "High Spire, the shrine isle of the Crag Spires, in guarded space. The first quests teach gliding from ledge to ledge and a first sail, then a skiff ride down the Spireward lane to Oathgate.",
    relations: [
      { with: "rootwarden", kind: "rival", text: "Galeborne ships need ancient wood; the Rootwardens say every old tree felled hastens the sinking. Grudgewood, on their shared frontier, is the oldest quarrel on the shard." },
      { with: "anchorkin", kind: "trade", text: "Wary trade partners. Galeborne ships carry Anchorkin chain and stone to every market, but the Anchorkin don't trust a people who can leave any isle the moment it falls." },
    ],
    signature: {
      customizable: ["Feather colour and pattern", "Crest shape", "Mantle length", "Skin tone (sky-pale to dusk)", "Eye colour", "Face markings"],
      locked: ["Feathered mantle"],
    },
    quote: { text: "An isle is only somewhere to land.", by: "Courier Ysra Highwind, Galeborne" },
    art: "a tall, slender Galeborne near-human with sky-pale skin and a crest of slate-blue and white feathers instead of hair, a feathered mantle growing from the shoulders and forearms folded like a cloak, wearing a light leather flight harness with brass buckles and a courier satchel, waist-up three-quarter view, standing on a windswept ledge of a towering rock spire high above the clouds, the mantle catching the wind",
  },
  {
    id: "anchorkin",
    name: "Anchorkin",
    homeland: "The Moorings",
    blurb: "Huge stone-skinned folk of the lowest isles, chained together above the storm. Nothing moves an Anchorkin who doesn't want to move.",
    look: "Huge, broad and heavy, with skin of living stone veined with teal crystal. Their marks of deeds are carved into the stone, and their beards are coarse stone fibre.",
    culture:
      "The Anchorkin live on the Moorings, the lowest isles on the shard, so close to the storm that the sky below them flickers. Generations ago they chained their isles together with great forged links, and they say the Moorings have held because they refuse to let go. They keep the Ledger, carved in stone, which records every isle that has ever sunk and why. Anchorkin take a long time to decide and never change their minds. A post given to an Anchorkin is held.",
    knownFor: "Masons, chainsmiths, guards and keepers of the Ledger.",
    affinities: ["Stone", "Stonecraft", "Smithing", "Shields", "Heavy Armour", "Lore"],
    innate: {
      name: "Anchor",
      text: "Plant your feet: you can't be knocked back, pushed or pulled. On a ship, an anchored Anchorkin steadies it against gusts and rams. During a sinking event they can hold a breaking bridge or ledge for a while.",
      limit: "Can't move while anchored. Too heavy to swim, and they take extra fall damage.",
    },
    start: "Ledgerstone, the shrine isle of the Moorings, in guarded space. The first quests teach the chains, the Ledger and a first shift on watch, then a skiff ride up the Moorward lane to Lanterncross.",
    relations: [
      { with: "rootwarden", kind: "ally", text: "Old allies who hold the land: the Rootwardens with roots, the Anchorkin with chains." },
      { with: "galeborne", kind: "wary", text: "They trade with the Galeborne and need their ships, but a people who can glide away from any isle is not a people you can count on." },
    ],
    signature: {
      customizable: ["Stone type (slate, basalt, sandstone, marble)", "Crystal vein colour", "Carved marks", "Build", "Stone-fibre beard"],
      locked: ["Stone skin", "Great weight"],
    },
    quote: { text: "It is carved. That is the end of the argument, not the start of it.", by: "Ledgerkeeper Ommeth, Anchorkin" },
    art: "a huge, broad Anchorkin with skin of grey slate stone veined with glowing teal crystal, carved marks on the shoulders and brow, a coarse beard of stone fibres, wearing heavy forged iron chain across the chest over a leather apron with gold trim, waist-up three-quarter view, standing on a low isle bound by giant iron chains, a flickering storm layer close below",
  },
  {
    id: "rootwarden",
    name: "Rootwardens",
    homeland: "The Rootholds",
    blurb: "Bark-skinned and slow to age, they live in the roots beneath the oldest isles and tend the ancient trees that slow the sinking.",
    look: "Broad and stocky, with bark-grained wooden skin. Moss, lichen and small flowers grow on their shoulders and in their beards, and their gear is carved from stone.",
    culture:
      "The Rootwardens live in caverns among the roots of the oldest isles. They tend the ancient trees day and night, because tending slows an isle's sinking. Anyone can learn Treetending, but no one is better at it. They are right that tending helps, though no tending can save an isle once it starts to fall. They age slowly, think slowly and hold a grudge for a very long time.",
    knownFor: "Treetenders, herbalists, healers and keepers of the old trees.",
    affinities: ["Treetending", "Bloom", "Herbalism", "Field Medicine", "Woodcutting", "Heavy Weapons"],
    innate: {
      name: "Take Root",
      text: "Stand still to take root and regenerate health and stamina. Near an ancient tree, rooting also speeds regeneration for nearby allies.",
      limit: "Can't move or dodge while rooted, and pulling free takes a moment. Weak to fire.",
    },
    start: "Elderroot, the shrine isle of the Rootholds, in guarded space. The first quests teach tending and gathering among the roots, then a skiff ride down the Rootward lane to Tetherport.",
    relations: [
      { with: "anchorkin", kind: "ally", text: "Old allies who hold the land together. Rootwarden healers keep Anchorkin watches standing, and Anchorkin guards keep the groves safe." },
      { with: "galeborne", kind: "rival", text: "The Galeborne fell ancient trees for masts and hulls. To a Rootwarden, every one of those ships is a sunken isle waiting to happen." },
    ],
    signature: {
      customizable: ["Wood type (oak, birch, cedar, ashen)", "Bark pattern", "Growth (moss, lichen, flowers, mushrooms)", "Beard foliage", "Crystal inlays"],
      locked: ["Bark skin", "Plant growth"],
    },
    quote: { text: "Every root you cut is a year the isle won't have.", by: "Elder Hollowgrain, Rootwarden" },
    art: "a broad, stocky Rootwarden with bark-grained oak skin, moss and lichen on the shoulders, a beard of moss and small white flowers, teal crystal inlays in the brow, wearing carved stone shoulder plates over leather, waist-up three-quarter view, standing among the giant glowing roots of an ancient tree in a root cavern",
  },
];
