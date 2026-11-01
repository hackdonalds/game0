// The bestiary: stat blocks for every creature and world boss. Source for the site's /bestiary pages
// and for scripts/bestiary-art.ts, which generates each entry's plate into art/bestiary/<id>.png.
// Design rules live in concept/monsters/README.md.

export type Temperament = "passive" | "neutral" | "territorial" | "hostile";
export type Size = "tiny" | "small" | "medium" | "large" | "huge" | "colossal";
export type Tier = "safe" | "guarded" | "wild";

export const REGIONS = [
  { id: "meadows", name: "Meadows and forests" },
  { id: "rootholds", name: "The Rootholds" },
  { id: "gardens", name: "The Garden Isles" },
  { id: "crags", name: "The Crag Spires" },
  { id: "lagoons", name: "The Glimmer Lagoons" },
  { id: "sky", name: "The open sky" },
  { id: "rim", name: "The wild rim" },
  { id: "storm", name: "The storm below" },
] as const;
export type Region = (typeof REGIONS)[number]["id"];

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
  /** Prompt for the bestiary plate */
  art: string;
}

export const bestiary: Creature[] = [
  {
    id: "burrow-boar", name: "Burrow Boar", family: "Beast", size: "medium", temperament: "neutral", danger: 2,
    region: "meadows", tiers: ["guarded", "wild"], habitat: "Meadow and forest isles", active: "Day", seasons: "All year; litters in spring",
    health: 140, stamina: 90, speed: { walk: 6 }, skills: { Unarmed: 30, Evasion: 10 }, senses: "Keen smell, poor eyesight",
    behaviours: ["graze", "flee", "charge"],
    actions: [
      { name: "Tusk charge", text: "Runs up to 12 m in a straight line and knocks the first target down. Cooldown 8 s." },
      { name: "Root up", text: "Digs at the ground, turning up roots and the odd buried coin." },
    ],
    drops: ["Boar meat", "Thick hide", "Tusks"], population: "10 per isle, refills in 90 minutes",
    taming: { use: "Ground mount", skill: 25 },
    storm: { name: "Stormtusk", text: "Hostile. Its charge leaves a trail of crackling static that slows anyone who crosses it." },
    lore: "Stocky, bristle-backed pigs that dig shallow burrows under the turf of almost every green isle. They ignore travellers until cornered, then charge with surprising speed. Young Rootborn ride them on their first trips between isles.",
    quote: { text: "Let it eat. If it stops eating, start running.", by: "Rootborn saying" },
    art: "a stocky wild boar with russet bristles, short curved tusks and a mossy patch on its back, pawing the turf",
  },
  {
    id: "glider-squirrel", name: "Glider Squirrel", family: "Beast", size: "tiny", temperament: "passive", danger: 1,
    region: "meadows", tiers: ["safe", "guarded", "wild"], habitat: "Forest canopies, town orchards", active: "Day", seasons: "All year; sleeps through winter",
    health: 15, stamina: 60, speed: { walk: 5, climb: 5, fly: 8 }, skills: { Evasion: 40, Climbing: 60 }, senses: "Sharp eyes, nervous",
    behaviours: ["wander", "climb", "flee"],
    actions: [{ name: "Glide", text: "Leaps from a branch and glides up to 40 m between trees, or off the isle's edge to the one below." }],
    drops: ["Soft fur", "Acorn caches"], population: "20 per isle, refills in 30 minutes",
    lore: "Fluffy, wide-eyed squirrels with a skin membrane between their legs. They glide from tree to tree and, when frightened, off the edge of the isle entirely. Sailors say a squirrel landing on your deck means fair winds.",
    quote: { text: "Seventeen acorns, three buttons and a Skerrin ear tag. All in one nest.", by: "Ledger of small things, Mossback archive" },
    art: "a small fluffy squirrel with big eyes and wide gliding membranes spread between its legs, mid-glide",
  },
  {
    id: "rootcrawler", name: "Rootcrawler", family: "Insect", size: "small", temperament: "territorial", danger: 2,
    region: "rootholds", tiers: ["guarded", "wild"], habitat: "Caverns and root tunnels under old isles", active: "Day and night (underground)", seasons: "All year",
    health: 60, stamina: 70, speed: { walk: 4, climb: 4 }, skills: { Unarmed: 25, "Heavy Armour": 40, Climbing: 70 }, senses: "Feels vibrations, blind",
    behaviours: ["guard", "swarm", "climb"],
    actions: [
      { name: "Mandible snap", text: "A quick bite that slows the target for 3 s." },
      { name: "Call the brood", text: "Clicks loudly; other rootcrawlers within 20 m join the fight." },
    ],
    drops: ["Chitin plates", "Root sap"], population: "15 per cavern, refills in 1 hour",
    storm: { name: "Stormcrawler", text: "Hostile. Its shell holds a charge that shocks anyone who strikes it with metal." },
    lore: "Beetles the size of a dog that gnaw dead roots beneath the oldest isles. The Rootborn tolerate them because they clear rot, but they defend their tunnels fiercely. Their chitin makes light, tough armour.",
    quote: { text: "They eat the dead roots. Only the dead ones. Usually.", by: "Elder Hollowgrain, Rootborn" },
    art: "a dog-sized beetle with dark green-bronze chitin, long mandibles and root fibres clinging to its legs, in a root tunnel",
  },
  {
    id: "bark-owl", name: "Bark Owl", family: "Bird", size: "small", temperament: "passive", danger: 1,
    region: "rootholds", tiers: ["safe", "guarded", "wild"], habitat: "Hollows of the ancient trees", active: "Night", seasons: "All year",
    health: 25, stamina: 80, speed: { walk: 1, fly: 12 }, skills: { Evasion: 50 }, senses: "Sees in the dark, silent flight",
    behaviours: ["sleep by day", "fly", "flee"],
    actions: [{ name: "Vanish", text: "Presses itself against bark and becomes almost impossible to see." }],
    drops: ["Barred feathers"], population: "4 per ancient tree",
    lore: "Owls whose feathers look exactly like the bark of the ancient trees. The Rootborn believe they carry the trees' dreams, and harming one is a deep insult in the Rootholds.",
    quote: { text: "If the owls leave a tree, start counting its days.", by: "Rootborn tending lore" },
    art: "a round owl whose feathers perfectly mimic grey-brown tree bark with lichen spots, perched in a hollow of a huge ancient tree at dusk, glowing amber eyes",
  },
  {
    id: "moss-grazer", name: "Moss Grazer", family: "Beast", size: "large", temperament: "passive", danger: 1,
    region: "gardens", tiers: ["safe", "guarded"], habitat: "Terraced meadows of the Garden Isles", active: "Day", seasons: "All year; moves to sheltered terraces in winter",
    health: 260, stamina: 120, speed: { walk: 3 }, skills: { "Heavy Armour": 30 }, senses: "Calm, slow to notice threats",
    behaviours: ["graze", "migrate", "flee"],
    actions: [{ name: "Hunker down", text: "Pulls its head into its mossy coat and takes half damage until it moves again." }],
    drops: ["Moss wool", "Grazer milk"], population: "Herds of 6–12, refill in 3 hours",
    taming: { use: "Pack animal", skill: 20 },
    lore: "Shaggy, slow herd beasts whose thick coats grow living moss. The Mossbacks keep whole herds on their terraces and use them to carry harvests between isles. They follow anyone holding fresh clover.",
    quote: { text: "Load it, lead it, and do not rush it. It will not rush.", by: "Mossback caravan master" },
    art: "a large shaggy herd animal like a gentle yak whose thick coat grows green moss and small flowers, carrying woven baskets, on a terraced garden isle",
  },
  {
    id: "burrow-mole", name: "Burrow Mole", family: "Beast", size: "small", temperament: "neutral", danger: 1,
    region: "gardens", tiers: ["safe", "guarded"], habitat: "Farm terraces and soft soil", active: "Dusk and night", seasons: "Spring to autumn",
    health: 35, stamina: 50, speed: { walk: 3 }, skills: { Unarmed: 15 }, senses: "Smell and touch, nearly blind",
    behaviours: ["ambush", "flee"],
    actions: [{ name: "Pop up", text: "Bursts out of the ground under a target, then vanishes again." }],
    drops: ["Velvet pelt", "Stolen turnips"], population: "8 per farm isle, refills in 40 minutes",
    lore: "Fat, velvet-furred moles that tunnel through farm terraces and eat crops from below. Clearing them is the most common job on any Garden Isle board, and the first fight for many new Mossbacks.",
    quote: { text: "Posted: 3 silver per mole, 10 for the big one. You will know the big one.", by: "Terrace Hill job board" },
    art: "a plump mole with velvety dark fur, large pink digging claws and a stolen turnip, popping out of a vegetable bed",
  },
  {
    id: "cliff-goat", name: "Cliff Goat", family: "Beast", size: "medium", temperament: "neutral", danger: 2,
    region: "crags", tiers: ["guarded", "wild"], habitat: "Sheer cliffs and spires", active: "Day", seasons: "All year",
    health: 110, stamina: 140, speed: { walk: 7, climb: 6 }, skills: { Unarmed: 30, Climbing: 70 }, senses: "Sure-footed, watchful",
    behaviours: ["graze", "flee", "charge", "climb"],
    actions: [
      { name: "Headbutt", text: "Rams a target and pushes it back 4 m. Near a cliff edge, this is the dangerous part." },
      { name: "Leap", text: "Jumps up to 6 m up or across a gap." },
    ],
    drops: ["Goat meat", "Hide", "Horn"], population: "12 per isle, refills in 2 hours",
    taming: { use: "Ground mount", skill: 40 },
    storm: { name: "Stormhorn", text: "Hostile. Its headbutt releases a lightning charge that arcs to anyone nearby." },
    lore: "Wild cousins of the Skerrin's herds, these goats climb walls no one else can. A tamed cliff goat is the only mount that can carry a rider straight up the Crag Spires.",
    quote: { text: "We did not tame them. We just agreed to climb in the same direction.", by: "Skerrin herder" },
    art: "a muscular mountain goat with thick curling horns and shaggy grey-cream coat, standing on a narrow ledge of a sheer cliff spire",
  },
  {
    id: "crag-drake", name: "Crag Drake", family: "Drake", size: "large", temperament: "territorial", danger: 4,
    region: "crags", tiers: ["wild"], habitat: "Nests on the highest spires", active: "Day", seasons: "All year; fiercest in spring when nesting",
    health: 420, stamina: 160, speed: { walk: 4, climb: 5, fly: 16 }, skills: { Unarmed: 60, "Heavy Armour": 50, Wind: 30 }, senses: "Sharp eyes, spots movement at 200 m",
    behaviours: ["guard", "fly", "dive at ships"],
    actions: [
      { name: "Raking dive", text: "Dives from above and claws everything in a 6 m line. Cooldown 12 s." },
      { name: "Wing gust", text: "A Wind technique that knocks targets back and fills a ship's sails the wrong way." },
      { name: "Tail sweep", text: "Strikes all targets behind it." },
    ],
    drops: ["Drake scales", "Drake wing leather", "Eggs (spring)"], population: "1 pair per spire",
    storm: { name: "Storm drake", text: "Hostile. Breathes a short cone of crackling wind and hunts ships on wild routes." },
    lore: "Small cousins of the legendary sky dragons, no bigger than a cart horse, with slate-grey scales that blend into the rock. They leave you alone unless you climb near their nests, and nesting season makes them reckless.",
    quote: { text: "We mine around their spires. Not because we are afraid. Because we are not stupid.", by: "Ironcleft foreman, Skerrin" },
    art: "a lean drake with slate-grey rock-like scales, leathery wings spread, perched on top of a jagged rock spire guarding a nest",
  },
  {
    id: "stonewing-bat", name: "Stonewing Bat", family: "Beast", size: "tiny", temperament: "territorial", danger: 2,
    region: "crags", tiers: ["guarded", "wild"], habitat: "Caves and mine shafts", active: "Night", seasons: "All year; hibernates in winter",
    health: 12, stamina: 60, speed: { fly: 10 }, skills: { Unarmed: 15, Evasion: 60 }, senses: "Echolocation",
    behaviours: ["sleep by day", "swarm", "fly"],
    actions: [{ name: "Swarm", text: "Dozens attack together, blinding a target for 2 s and dealing small, constant damage." }],
    drops: ["Bat wing", "Guano (fertiliser)"], population: "Colonies of 30–60, refill in 1 hour",
    lore: "Tiny bats with wings stiff as slate. They pour out of the Crag Spires' caves at dusk in clouds. Alone they are nothing; a disturbed colony can drive a miner out of a shaft.",
    quote: { text: "Lantern low, voice lower.", by: "Skerrin mining rule" },
    art: "a swarm of tiny dark bats with stiff slate-grey wings bursting from a cave mouth in a cliff at dusk, one bat in front in detail",
  },
  {
    id: "lantern-eel", name: "Lantern Eel", family: "Fish", size: "medium", temperament: "territorial", danger: 3,
    region: "lagoons", tiers: ["guarded", "wild"], habitat: "Deep glowing lagoons", active: "Night", seasons: "All year; spawns in autumn",
    health: 150, stamina: 100, speed: { swim: 9 }, skills: { Unarmed: 40, Evasion: 40, Tide: 30 }, senses: "Senses heat and movement in water",
    behaviours: ["guard", "ambush"],
    actions: [
      { name: "Glow lure", text: "Pulses its light, drawing small fish and the curious. Then strikes." },
      { name: "Shock", text: "A Tide technique: stuns everything in the water within 5 m for 2 s." },
    ],
    drops: ["Eel meat (prized)", "Glow oil"], population: "6 per lagoon, refills in 2 hours",
    storm: { name: "Storm eel", text: "Hostile. Leaves the water in surges and slithers through the air on storm wind." },
    lore: "Long eels whose bellies glow the same teal as the Glimmer Lagoons. Rillfolk cooks pay well for their meat, and Rillfolk divers keep well away from their dens.",
    quote: { text: "Best soup in the sky. Worst way to get the ingredients.", by: "Glimmerpool cook" },
    art: "a long sleek eel with glowing teal bioluminescent spots along its body, curling through clear glowing lagoon water at night",
  },
  {
    id: "shellback-crab", name: "Shellback Crab", family: "Crustacean", size: "medium", temperament: "neutral", danger: 2,
    region: "lagoons", tiers: ["safe", "guarded", "wild"], habitat: "Lagoon shores and shallows", active: "Day and night", seasons: "All year; moults in summer",
    health: 180, stamina: 70, speed: { walk: 3, swim: 4 }, skills: { Unarmed: 30, "Heavy Armour": 60 }, senses: "Wide view, slow to react",
    behaviours: ["wander", "guard"],
    actions: [
      { name: "Pinch", text: "Grabs and holds a target for 2 s." },
      { name: "Shell up", text: "Takes almost no damage from the front while braced." },
    ],
    drops: ["Crab meat", "Shell plates"], population: "10 per lagoon isle, refills in 1 hour",
    lore: "Broad crabs with shells like overturned shields, often grown over with tiny lagoon plants. They scuttle sideways from trouble and pinch hard when cornered.",
    quote: { text: "Sideways is still away.", by: "Rillfolk proverb" },
    art: "a broad crab with a shield-like shell grown over with tiny water plants and shells, raising one big claw on a glowing lagoon shore",
  },
  {
    id: "cloud-whale", name: "Cloud Whale", family: "Sky beast", size: "colossal", temperament: "passive", danger: 1,
    region: "sky", tiers: ["guarded", "wild"], habitat: "The open sky between isles", active: "Day and night", seasons: "Migrates: north in summer, south in winter",
    health: 9000, stamina: 999, speed: { fly: 7 }, skills: { Wind: 80 }, senses: "Feels the winds; ignores small things",
    behaviours: ["migrate", "fly"],
    actions: [
      { name: "Wake", text: "The air behind it carries ships 30% faster for a while." },
      { name: "Song", text: "A low call heard across the shard. Sailors use it to find the season's routes." },
    ],
    drops: ["Nothing. Hunting them is forbidden by the Tether Accord."],
    lore: "Vast, gentle beasts that drift between the isles on the high winds, as big as a galleon or larger. Their migrations mark the seasons, and ships follow their wake for the free speed. The Tether Accord forbids hunting them, and every people agrees.",
    quote: { text: "When the whales turn south, haul your winter stores.", by: "Accord sailing almanac" },
    art: "an enormous gentle whale drifting through the sky among clouds, pale blue-grey skin with soft markings, small floating isles and a tiny sailing ship in its wake for scale",
  },
  {
    id: "gale-hawk", name: "Gale Hawk", family: "Bird", size: "small", temperament: "hostile", danger: 3,
    region: "sky", tiers: ["wild"], habitat: "Wild wind currents", active: "Day", seasons: "All year; flocks grow in autumn",
    health: 40, stamina: 120, speed: { fly: 20 }, skills: { Unarmed: 35, Evasion: 60, Wind: 20 }, senses: "Hunts by sight from great heights",
    behaviours: ["swarm", "fly", "dive at ships"],
    actions: [
      { name: "Strafe", text: "Dives through a ship's crew, striking one target, and climbs away." },
      { name: "Shred", text: "Tears at sails. Each hit wears the sail a little." },
    ],
    drops: ["Hawk feathers (fletching)"], population: "Flocks of 5–12 on each wild current",
    lore: "Fast, sharp-winged hawks that ride the wild currents in flocks. They see skiffs as prey and dive at crews and sails. Sailweavers curse them more than any storm.",
    quote: { text: "Mend the sail, then shoot the bird. Never the other way round.", by: "Skiff captain's rule" },
    art: "a fierce sharp-winged hawk with storm-grey and white feathers diving with talons out through wind streaks, a ship's sail behind",
  },
  {
    id: "skyray", name: "Skyray", family: "Sky beast", size: "huge", temperament: "territorial", danger: 4,
    region: "sky", tiers: ["wild"], habitat: "Open sky near the rim", active: "Dusk and night", seasons: "All year",
    health: 900, stamina: 300, speed: { fly: 18 }, skills: { Unarmed: 55, Evasion: 40, Wind: 60 }, senses: "Feels wind changes",
    behaviours: ["guard", "fly", "dive at ships"],
    actions: [
      { name: "Wing slam", text: "Glides over a ship and slams down, damaging the hull and knocking crew off their feet." },
      { name: "Tail barb", text: "Poisons a target: no stamina refill for 6 s." },
      { name: "Updraft", text: "A Wind technique that tosses small ships off course." },
    ],
    drops: ["Ray leather", "Tail barb"], population: "1–2 per wild sky region",
    taming: { use: "Flying mount", skill: 85 },
    storm: { name: "Storm ray", text: "Hostile. Trails lightning from its wingtips and hunts ships during surges." },
    lore: "Great flat rays that glide on rim winds, wider than a cutter's deck. They defend their stretch of sky against ships. Only a master tamer can win one over, and a tamed skyray is the rarest mount in the sky.",
    quote: { text: "It did not attack the ship. It attacked the shadow of the ship. We were just in the way.", by: "Wreck survivor, Last Light" },
    art: "a huge manta ray gliding through the evening sky with wide wings, deep blue and violet skin with pale glowing markings, a long barbed tail",
  },
  {
    id: "ruin-stalker", name: "Ruin Stalker", family: "Beast", size: "medium", temperament: "hostile", danger: 4,
    region: "rim", tiers: ["wild"], habitat: "Old-world ruins on wild isles", active: "Night", seasons: "All year",
    health: 220, stamina: 160, speed: { walk: 9, climb: 7 }, skills: { Unarmed: 65, Evasion: 55, Climbing: 60 }, senses: "Sees in the dark, smells blood",
    behaviours: ["ambush", "hunt", "climb"],
    actions: [
      { name: "Pounce", text: "Leaps from hiding up to 10 m and pins a target for 2 s." },
      { name: "Rend", text: "Two quick strikes that make the target bleed." },
      { name: "Fade", text: "Slips out of sight among ruins for 4 s." },
    ],
    drops: ["Stalker pelt", "Fangs", "Old-world trinkets"], population: "2–4 per ruin isle, refills in 4 hours",
    storm: { name: "Storm stalker", text: "Its pounce leaves a lightning mark that the next strike detonates." },
    lore: "Lean, pale cats that den in the ruins of the drowned world's lost towns. They hunt alone and from above, and they love the stone pillars where treasure hunters like to rest.",
    quote: { text: "Never camp under a pillar.", by: "Salvager's first rule" },
    art: "a lean pale grey big cat with faint stone-like stripes, crouched on top of a broken ancient pillar among overgrown ruins at night, glowing eyes",
  },
  {
    id: "stormspawn", name: "Stormspawn", family: "Storm-touched", size: "medium", temperament: "hostile", danger: 3,
    region: "storm", tiers: ["guarded", "wild"], habitat: "Wherever a storm surge reaches", active: "During storm surges", seasons: "Any",
    health: 160, stamina: 999, speed: { walk: 6, fly: 6 }, skills: { Unarmed: 45, Wind: 40 }, senses: "Drawn to life and light",
    behaviours: ["swarm", "hunt"],
    actions: [
      { name: "Storm touch", text: "A strike that drains stamina from the target." },
      { name: "Burst", text: "When killed, releases a small lightning burst that hits everyone within 3 m." },
    ],
    drops: ["Storm residue (used in Sailweaving)"],
    lore: "Not a creature of its own, but what the storm makes of local wildlife: twisted shapes of boars, goats and birds, wrapped in dark cloud with lightning for eyes. They pour onto isles during surges and fade when it ends.",
    quote: { text: "It had the shape of a goat. It did not have a goat's eyes.", by: "Hornfast watch report" },
    art: "a twisted creature shaped like a goat made of dark swirling storm cloud with crackling lightning for eyes and veins, emerging from a dark stormy mist",
  },
  {
    id: "tempest-serpent", name: "The Tempest Serpent", boss: true, family: "World boss", size: "colossal", temperament: "hostile", danger: 5,
    region: "storm", tiers: ["wild"], habitat: "Sky lanes near the rim, during storm surges", active: "During storm surges", seasons: "Most often in autumn",
    health: 60000, stamina: 999, speed: { fly: 22 }, skills: { Unarmed: 90, Wind: 95, "Heavy Armour": 70 }, senses: "Feels every ship in the storm",
    behaviours: ["fly", "dive at ships", "hunt"],
    actions: [
      { name: "Coil", text: "Wraps around an isle's edge or a galleon, crushing everything in reach." },
      { name: "Gale breath", text: "A cone of storm wind that tears sails and throws crew overboard." },
      { name: "Thunder dive", text: "Plunges through a ship from above, then rises again elsewhere." },
      { name: "Grows with the crowd", text: "Gains health and new attacks for every player taking part." },
    ],
    drops: ["Reward chest for everyone who helped", "Bonus drop: serpent scale, rare Wind techniques, relics"],
    lore: "A sky serpent hundreds of metres long that rises from the storm on the worst nights of a surge. It hunts ships more than people. Fleets that bring it down share the spoils, and ships fight over the scales it sheds.",
    quote: { text: "The sea was supposed to be below us. Then it came up, with teeth.", by: "Tetherport harbour log" },
    art: "a colossal sky serpent made of storm cloud and dark blue scales with lightning running along its spine, coiling around a floating isle in a raging storm, a galleon with tiny figures in front for scale",
  },
  {
    id: "drowned-colossus", name: "The Drowned Colossus", boss: true, family: "World boss", size: "colossal", temperament: "hostile", danger: 5,
    region: "storm", tiers: ["wild"], habitat: "Sinking isles, during their last days", active: "During sinking events", seasons: "Any",
    health: 80000, stamina: 999, speed: { walk: 3 }, skills: { Unarmed: 85, Stone: 90, "Heavy Armour": 95 }, senses: "Seeks relics",
    behaviours: ["guard", "charge"],
    actions: [
      { name: "Ruin fist", text: "Smashes the ground, cracking the isle and throwing everyone nearby." },
      { name: "Old-world beam", text: "Its chest opens and fires a line of light across the isle." },
      { name: "Shed stones", text: "Drops pieces of itself that become smaller constructs." },
      { name: "Grows with the crowd", text: "Gains health and new attacks for every player taking part." },
    ],
    drops: ["Reward chest for everyone who helped", "Bonus drop: relic core, old-world gear, rare Stone techniques"],
    lore: "A walking ruin built by the drowned world, made of carved stone, rusted metal and old glyphs. It climbs onto isles in their last days as if it were looking for something. Whatever it seeks, it carries relics inside it.",
    quote: { text: "The glyphs on its chest match the Ledger's oldest page. The one we cannot read.", by: "Mossback archivist" },
    art: "a colossal ancient construct made of carved weathered stone blocks, rusted bronze and glowing teal glyphs, climbing onto the crumbling edge of a sinking floating isle, tiny adventurers below for scale",
  },
  {
    id: "stormmother", name: "The Stormmother", boss: true, family: "World boss", size: "colossal", temperament: "hostile", danger: 5,
    region: "storm", tiers: ["wild"], habitat: "The deepest wild isles, during rare great surges", active: "During great storm surges", seasons: "Winter",
    health: 120000, stamina: 999, speed: { fly: 10 }, skills: { Wind: 100, Tide: 90, Oathcraft: 80 }, senses: "Sees through every stormspawn",
    behaviours: ["fly", "swarm"],
    actions: [
      { name: "Call the brood", text: "Summons waves of stormspawn from the clouds." },
      { name: "Eye of the storm", text: "A calm circle opens; everyone outside it is struck by lightning." },
      { name: "Drown the sky", text: "Rain so heavy that ships lose speed and stamina won't refill." },
      { name: "Grows with the crowd", text: "Gains health and new attacks for every player taking part." },
    ],
    drops: ["Reward chest for everyone who helped", "Bonus drop: master techniques, storm relics, achievements"],
    lore: "The rarest sight in the sky: a towering shape of cloud and lightning with something like a face, rising only in the great winter surges. Some say she is the storm itself. The stormspawn obey her, and she has never been seen twice in the same place.",
    quote: { text: "We did not beat her. She left.", by: "Survivor of the first great surge" },
    art: "a towering ethereal figure made of dark storm clouds and lightning with a vague serene feminine face, arms spread, rising above a stormy sea of clouds, swarms of small storm creatures around her, tiny sailing ships below for scale",
  },
];
