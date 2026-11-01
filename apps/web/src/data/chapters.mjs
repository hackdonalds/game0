// The handbook's chapters, in reading order. Each chapter renders one or more concept docs (paths relative to concept/).
// Plain JS so astro.config.mjs can use it to rewrite links between concept docs into handbook URLs.

/** @typedef {{ slug: string; number: number; title: string; kicker: string; summary: string; docs: string[]; catalogues: string[]; demo?: "map" | "peoples" | "sail" | "shard"; art: string }} Chapter */

/** @type {Chapter[]} */
export const chapters = [
  {
    slug: "vision", number: 1, title: "Vision", kicker: "What the game is",
    summary: "A sandbox of floating isles with no classes, no endgame and a world that keeps moving. The pillars every other decision answers to.",
    docs: ["vision.md"], catalogues: ["glossary"],
    art: "a sweeping vista of many floating isles at golden hour, waterfalls spilling from their edges into a sea of clouds, small sailing ships with glowing enchanted sails crossing between them, an enormous ancient tree on the central isle",
  },
  {
    slug: "world", number: 2, title: "The World", kicker: "Above the drowned world",
    summary: "Why the isles float is a mystery. That they sink is not. The storm below, the Tether Accord, the seasons and the First Shard.",
    docs: ["world/README.md"], catalogues: ["isles", "winds", "glossary"], demo: "map",
    art: "a dramatic view down past the edge of a floating isle into a churning living storm layer far below with lightning, ancient drowned ruins faintly visible through gaps in the clouds, and an isle slowly sinking into it",
  },
  {
    slug: "peoples", number: 3, title: "Peoples", kicker: "Three peoples, one sky",
    summary: "Galeborne, Anchorkin and Rootwardens: who they are, where they live, their innate skills, what they hold against each other, and how players shape them.",
    docs: ["world/peoples.md", "art-direction/character-customization.md"], catalogues: ["peoples"], demo: "peoples",
    art: "three fantasy travellers standing together on a cliff edge at dawn seen from behind: a tall slender figure with a folded feathered mantle, a huge broad figure with grey stone skin veined with teal crystal, and a stocky bark-skinned figure with moss and small flowers on its shoulders, looking out over floating isles",
  },
  {
    slug: "play", number: 4, title: "How You Play", kicker: "Everything is a skill",
    summary: "Classless skills learned at their source, six technique slots, stamina and cooldowns, risk tiers, death and loot, quests and the first hours.",
    docs: ["mechanics/README.md"], catalogues: ["skills", "materials"],
    art: "an open old book of skills on a wooden table in a trainer's workshop, glowing wind runes rising from its pages, surrounded by a sword, a pickaxe, a cooking pot, a coil of rope and a sailmaker's needle, warm window light",
  },
  {
    slug: "sailing", number: 5, title: "Sailing", kicker: "Sail, wind and wear",
    summary: "Skiffs, cutters and galleons trimmed against enchanted wind currents. Charted Accord lanes, wild shortcuts, and sails that wear thin.",
    docs: ["sailing/README.md"], catalogues: ["ships", "winds"], demo: "sail",
    art: "a wooden sailing galleon with glowing enchanted sails heeling hard into a visible stream of wind current between floating isles, crew working the rigging, wind streaks in the air",
  },
  {
    slug: "economy", number: 6, title: "Economy and Crafting", kicker: "Gather, craft, haul",
    summary: "One gold currency, town markets shared across shards, gear that wears out, crafters at the centre, and cargo worth fighting for.",
    docs: ["economy/README.md"], catalogues: ["materials", "skills"],
    art: "a bustling floating market town dock at morning, traders unloading crates and barrels from a cutter, stalls with ore, timber, cloth and glowing crystals, scales and coins on a counter",
  },
  {
    slug: "creatures", number: 7, title: "Creatures", kicker: "The bestiary",
    summary: "Wildlife of the isles, the storm-touched, taming, living populations, and the world bosses that rise with the storm.",
    docs: ["monsters/README.md"], catalogues: ["bestiary"],
    art: "a field naturalist's view of sky wildlife: a cloud whale drifting past a floating isle, a crag drake on a spire, gale hawks circling, a herd of mossy grazers below, all in soft morning light",
  },
  {
    slug: "society", number: 8, title: "Society", kicker: "Guilds, grudges, reputation",
    summary: "How players and peoples relate: guilds, reputation, old grudges and new friendships. Built to grow as new peoples join.",
    docs: ["social/README.md"], catalogues: ["peoples", "glossary"],
    art: "a great round hall in an Accord town with banners of three peoples hanging from the rafters, envoys of different fantasy peoples gathered around a large round table with a map, warm lantern light",
  },
  {
    slug: "simulation", number: 9, title: "Simulation", kicker: "A living shard",
    summary: "Thousands of NPCs and bot characters at three levels of detail, so the world feels lived in from day one.",
    docs: ["simulation/README.md"], catalogues: [], demo: "shard",
    art: "a floating isle town at dusk seen from above, hundreds of tiny lantern-carrying townsfolk in the streets, caravans of small ships with lights leaving along a glowing wind lane toward distant isles",
  },
  {
    slug: "art", number: 10, title: "Art Direction", kicker: "Painterly and luminous",
    summary: "Stylized painterly, epic and never grim. The palette, the visual rules and how art becomes game assets.",
    docs: ["art-direction/README.md"], catalogues: [],
    art: "an artist's easel on the edge of a floating isle with a half-finished painting of the sky isles, paint palette with soft muted golds teals and greens, brushes, the real vista behind it in matching colours",
  },
];

/** Map a concept doc path (relative to concept/) to its chapter slug. */
export const docToChapter = Object.fromEntries(chapters.flatMap((c) => c.docs.map((d) => [d, c.slug])));
