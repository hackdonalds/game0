// Handbook notes for every isle on the First Shard. Ids match worlds/first-shard.world.json.
// Lore from concept/world/README.md; creatures from bestiary.ts.

import type { IsleNote } from "./types";

export const isleNotes: IsleNote[] = [
  // Accord Hall and the four Accord towns (safe)
  {
    id: "isle_accord-hall",
    blurb:
      "The neutral heart of the First Shard, where the Tether Accord was signed after the great sinking. All five peoples keep a seat in its hall, and all four spoke lanes run home to its docks. No blade is drawn on its lawns.",
    landmarks: ["The Hall of the Accord", "The Five Seats", "The Tether Shrine", "The Spoke Docks"],
    resources: ["Orchard fruit and garden herbs (Herbalism)", "Windfall timber from the orchard edge (Woodcutting)", "Carp from the reflecting ponds (Fishing)"],
    art: "a large round floating meadow isle crowned by a great domed hall of pale stone and gold trim, five tall banners around a central plaza, orchards and reflecting ponds, wooden docks reaching out on four sides with small sailships moored, seen from a slight aerial angle above the clouds",
  },
  {
    id: "isle_tetherport",
    blurb:
      "The shard's great shipyard, between the Rootholds and the Garden Isles. Ships ride at rows of carved tether posts, and the Rootward lane leaves from its northern pier. Rootborn timber and Mossback cloth meet here and leave as hulls and sails.",
    landmarks: ["The Tether Posts", "Keelwright Yards", "The Rootward Pier", "The Accord Shrine of Tetherport"],
    resources: ["Shipyard offcut timber (Woodcutting)", "Flax from the hedgerows (Herbalism)", "Sky-pond fish (Fishing)"],
    art: "a floating meadow isle ringed with long wooden piers and tall carved tether posts, half-built ship hulls on slipways, a harbour town of timber halls and sail lofts, a small shrine with a teal crystal on a hill, seen from a slight aerial angle",
  },
  {
    id: "isle_windmarket",
    blurb:
      "The busiest market in the sky, between the Garden Isles and the Glimmer Lagoons. Its order book is the same on every shard, so prices called here are heard everywhere. Mossback caravans and Rillfolk traders fill its stalls from dawn.",
    landmarks: ["The Great Order Book", "The Awning Rows", "Gardenward Quay", "The Accord Shrine of Windmarket"],
    resources: ["Market garden herbs (Herbalism)", "Spilt grain and seed from the caravans (Herbalism)", "Pond fish below the quay (Fishing)"],
    art: "a floating meadow isle covered in a bustling market town of colourful cloth awnings and timber stalls, a tall hall with a carved order board, windmills on the edge, many small sailships docked along a quay, seen from a slight aerial angle",
  },
  {
    id: "isle_lanterncross",
    blurb:
      "The lowest Accord town, between the Glimmer Lagoons and the Crag Spires. Skerrin ore meets Rillfolk goods under thousands of hanging lanterns, and the glow is a beacon for skiffs at night. On still evenings the storm can be heard far below.",
    landmarks: ["The Lantern Crossing", "The Ore Scales", "Lagoonward Steps", "The Accord Shrine of Lanterncross"],
    resources: ["Glowmoss from the town wells (Herbalism)", "Pond fish and lagoon eels sold fresh (Fishing)", "Ore tailings dropped by the haulers (Mining)"],
    art: "a floating meadow isle at dusk with a crossroads town strung with hundreds of glowing lanterns, stone weighing houses and timber inns, glowing teal water channels, sailships arriving with ore crates, dark storm clouds far below, seen from a slight aerial angle",
  },
  {
    id: "isle_oathgate",
    blurb:
      "The Accord town on the contested northwest frontier, between the Rootholds and the Crag Spires. Grudges are heard here before they become feuds, and Veiled oath-caravans swear and settle their vows under its arch. The Spireward lane climbs west from its gate.",
    landmarks: ["The Oath Arch", "The Hearing Ring", "Spireward Gate", "The Accord Shrine of Oathgate"],
    resources: ["Hedge timber (Woodcutting)", "Meadow herbs (Herbalism)", "Loose stone from the old walls (Mining)"],
    art: "a floating meadow isle with a walled town built around a great carved stone arch hung with embroidered oath cloths, a round stone hearing ring, Veiled caravan wagons and tents by the gate, distant crag spires and giant trees on the horizon, seen from a slight aerial angle",
  },

  // The Rootholds (north, Rootborn)
  {
    id: "isle_elderroot",
    blurb:
      "The heart of the Rootholds, held up by the oldest tree on the shard. Its roots spill over the isle's edge into the clouds, and the Rootborn live in caverns carved between them. New Rootborn take their first steps here, beneath bark owls and among rootcrawler tunnels.",
    landmarks: ["The Eldertree", "The Root Halls", "The Shrine of the First Root", "Rootward Landing"],
    resources: ["Oak and elder timber from fallen limbs (Woodcutting)", "Copper and tin in the root caverns (Mining)", "Lichen, mushrooms and root sap (Herbalism)", "Rootcrawler chitin (Hunting)"],
    art: "a large floating isle crowned by a colossal ancient tree, its huge roots wrapping the rock and trailing down into the clouds, carved stone doorways and glowing windows set among the roots, a small stone shrine with a teal crystal, moss and lichen everywhere, seen from a slight aerial angle",
  },
  {
    id: "isle_rootmother",
    blurb:
      "A quiet isle bridged to Elderroot, where the Rootborn say all their trees began. Its ancient tree is tended day and night, and its seedlings are carried to every isle the Rootborn hope to save.",
    landmarks: ["The Rootmother Tree", "The Seedling Terraces", "The Tending Circle"],
    resources: ["Seedlings and bloom herbs (Herbalism)", "Fallen birch and cedar (Woodcutting)", "Bark owl feathers (Hunting)"],
    art: "a floating isle with a vast gnarled mother tree wrapped in hanging moss, rows of seedlings on stone terraces around its roots, Rootborn tenders working by lantern light, a rope bridge to a larger isle, seen from a slight aerial angle",
  },
  {
    id: "isle_deephold",
    blurb:
      "The one Roothold isle with no ancient tree, so the Rootborn dig down instead of up. Its stonewright quarries and halls run deep into the rock, and the Rootborn say they cut only what the isle can spare.",
    landmarks: ["The Deep Quarry", "The Stonewrights' Hall", "The Carved Stair"],
    resources: ["Granite and slate (Mining)", "Copper and iron seams (Mining)", "Cave mushrooms (Herbalism)", "Rootcrawler chitin (Hunting)"],
    art: "a floating rocky isle with deep stepped quarries cut into its top, carved stone halls and pillars along the quarry walls, small trees and moss on the rim, stone blocks on wooden cranes, seen from a slight aerial angle",
  },
  {
    id: "isle_hollowgrain",
    blurb:
      "The highest isle of the Rootholds, held by an ancient tree so old its trunk is hollow. Bark owls nest in the hollows by the hundred. The Rootborn elder who keeps it is known only by the isle's name.",
    landmarks: ["The Hollow Trunk", "The Owl Galleries", "The Elder's Seat"],
    resources: ["Ancient deadwood (Woodcutting)", "Bark owl feathers (Hunting)", "Hollow lichen and owl-moss (Herbalism)"],
    art: "a small high floating isle crowned by an enormous ancient tree with a hollow trunk open to the sky, owls perched in its many hollows, roots spilling over the edge, moss and lichen glowing faintly at dusk, seen from a slight aerial angle",
  },

  // The Garden Isles (east, Mossbacks)
  {
    id: "isle_ledgerhome",
    blurb:
      "The Mossback seat, where the Ledger is kept: the record of every isle that has ever sunk. Terraced fields climb to the vault, and moss grazers wander the lower slopes. New Mossbacks begin here, among the scribes and the farmers.",
    landmarks: ["The Ledger Vault", "The Reading Steps", "The Shrine of Long Memory", "Gardenward Moorings"],
    resources: ["Grain and vegetables from the terraces (Herbalism)", "Moss grazer wool and hide (Hunting)", "Fishpond carp (Fishing)", "Old Ledger fragments to study (Lore)"],
    art: "a broad floating isle of green terraced fields climbing to a squat domed stone vault with gold trim, moss-covered walls, slow herd beasts grazing, a small shrine garden with a teal crystal, rope bridges to three smaller garden isles, seen from a slight aerial angle",
  },
  {
    id: "isle_terrace-hill",
    blurb:
      "A steep garden isle stepped from rim to summit. Burrow moles are a constant plague here, and the job board always wants them gone.",
    landmarks: ["The Hundred Steps", "The Mole Fences", "Summit Orchard"],
    resources: ["Orchard fruit (Herbalism)", "Root vegetables (Herbalism)", "Burrow mole pelts (Hunting)"],
    art: "a small floating hill isle stepped into many narrow green terraces with stone retaining walls, an orchard on the summit, little mounds of dug earth among the crops, a rope bridge leading away, seen from a slight aerial angle",
  },
  {
    id: "isle_slowfield",
    blurb:
      "The widest fields in the Garden Isles, worked at a pace only a Mossback could love. Moss grazer herds drift across it from season to season. It feeds half of Windmarket's stalls.",
    landmarks: ["The Long Furrow", "The Grazer Commons", "Harvest Barns"],
    resources: ["Wheat and flax (Herbalism)", "Moss grazer wool and hide (Hunting)", "Hedgerow timber (Woodcutting)"],
    art: "a wide flat floating isle of golden fields and green hedgerows, great timber barns, a herd of slow mossy beasts grazing, a lone Mossback farmer with a garden on its shell walking a furrow, seen from a slight aerial angle",
  },
  {
    id: "isle_greenshell",
    blurb:
      "A small isle shaped like a domed shell, given over to herb gardens and the shrines Mossbacks carry on their backs. Young Mossbacks come here to plant their first shell garden.",
    landmarks: ["The Shell Gardens", "The Shrine Kiln", "The Seed Library"],
    resources: ["Rare herbs and flowers (Herbalism)", "Clay for shrine-making (Stonecraft)", "Seeds for shell gardens (Herbalism)"],
    art: "a small domed floating isle covered in neat herb gardens and flowering beds, tiny stone shrines dotted among them, a clay kiln with smoke curling up, Mossbacks tending plants, seen from a slight aerial angle",
  },

  // The Glimmer Lagoons (south, Rillfolk)
  {
    id: "isle_glimmerpool",
    blurb:
      "The Rillfolk heart: a lake isle whose water glows teal from below. Stilt houses and boardwalks ring the pool, and divers set out from here for the drowned world. New Rillfolk start on its docks, with a net in one paw.",
    landmarks: ["The Glimmerpool", "The Divers' Ring", "The Shrine of Still Water", "Lagoonward Docks"],
    resources: ["Lagoon fish and lantern eels (Fishing)", "Glowweed and reed (Herbalism)", "Shellback crab shell (Hunting)"],
    art: "a floating isle holding a wide round lake glowing teal from within, wooden stilt houses and boardwalks around the shore, little boats and diving platforms, a small shrine on a reed island with a teal crystal, water spilling from the isle's edge as mist, seen from a slight aerial angle",
  },
  {
    id: "isle_otterwake",
    blurb:
      "A lively lagoon isle of cookhouses and river slides, where young Rillfolk learn to swim and to haggle. The smell of grilled eel carries across the bridge.",
    landmarks: ["The Slides", "Wake Cookhouses", "The Haggling Pier"],
    resources: ["River fish (Fishing)", "Reed and water herbs (Herbalism)", "Driftwood (Woodcutting)"],
    art: "a floating lagoon isle with winding glowing streams and water slides between pools, wooden cookhouses with smoke rising, otter-folk swimming and fishing, a rope bridge leading to a larger lake isle, seen from a slight aerial angle",
  },
  {
    id: "isle_lanternmere",
    blurb:
      "A deep, dark mere where lantern eels glow at night. Cooks pay well for its catch, and fishers work it from boats hung with their own lanterns.",
    landmarks: ["The Mere", "The Eel Lights", "Night Market Jetty"],
    resources: ["Lantern eels (Fishing)", "Deep-water glowweed (Herbalism)", "Shellback crab shell and meat (Hunting)"],
    art: "a floating isle at night holding a dark round mere lit by glowing eels beneath the surface, small boats with hanging lanterns, a wooden jetty and huts, reeds along the shore, seen from a slight aerial angle",
  },
  {
    id: "isle_shellbay",
    blurb:
      "The lowest of the home isles, with the storm close below its rim. Shellback crabs crowd its shallows, and its dive wells are the safest way down to the drowned world.",
    landmarks: ["The Dive Wells", "Crab Shallows", "The Salvagers' Rack"],
    resources: ["Shellback crab shell and meat (Hunting)", "Shellfish and lagoon fish (Fishing)", "Old-world relics from the dive wells (Salvage)"],
    art: "a small low floating isle with a curved sandy bay and glowing shallows full of large crabs, wooden racks of salvaged old-world stone, ropes descending through a well in the rock, dark storm clouds churning not far below, seen from a slight aerial angle",
  },

  // The Crag Spires (west, Skerrin)
  {
    id: "isle_high-spire",
    blurb:
      "The highest home isle on the shard, a needle of rock the Skerrin have carved into a town of ledges and stairs. Crag drakes nest on its crown. New Skerrin begin here and learn to climb before they learn to mine.",
    landmarks: ["The Crown Ledge", "The Hanging Stair", "The Shrine of the Peak", "Spireward Hook"],
    resources: ["Copper and iron ore (Mining)", "Climbing routes up the spire (Climbing)", "Cliff goat hide and horn (Hunting)", "Crag drake scales (Hunting)"],
    art: "a tall needle-like floating rock spire carved with ledges, stairs and cliff houses, rope lifts and timber platforms, small drakes circling its peak, a tiny shrine with a teal crystal on the top ledge, rope bridges to three smaller crags, seen from a slight aerial angle above the clouds",
  },
  {
    id: "isle_hornfast",
    blurb:
      "The Skerrin stronghold that faces the Rootholds across the frontier. Its walls are hung with carved horns, one for every herder who held it. Few Rootborn are welcome.",
    landmarks: ["The Horn Wall", "The Watch Spur", "The Herders' Pens"],
    resources: ["Granite (Mining)", "Cliff goat hide and horn (Hunting)", "Mountain herbs (Herbalism)"],
    art: "a rugged floating crag isle with a stone fortress whose walls are hung with carved curled horns, goat pens on narrow ledges, a lookout spur pointing towards distant giant trees, seen from a slight aerial angle",
  },
  {
    id: "isle_ironcleft",
    blurb:
      "The highest point on the shard, split by a cleft full of iron. Skerrin mines run right through the isle and out of its underside. Stonewing bats swarm in the old shafts at night.",
    landmarks: ["The Cleft", "Underside Galleries", "The Ore Hoist"],
    resources: ["Iron ore (Mining)", "Coal (Mining)", "Stonewing bat leather (Hunting)"],
    art: "a high floating crag isle split down the middle by a deep cleft, mine entrances and timber scaffolds on its walls, ore carts on rope hoists, mine shafts opening on its rocky underside, bats leaving at dusk, seen from a slight aerial angle",
  },
  {
    id: "isle_goatstair",
    blurb:
      "A crag of natural ledges climbing like a staircase. Cliff goat herds live here all year, and young Skerrin learn to ride and tame them.",
    landmarks: ["The Stair", "The Taming Ledge", "Herders' Bothies"],
    resources: ["Cliff goat milk, hide and horn (Hunting)", "Tameable cliff goats (Taming)", "Mountain herbs (Herbalism)"],
    art: "a floating crag isle shaped into natural stepped ledges like a giant staircase, herds of cliff goats leaping between them, small stone huts and wooden pens, sparse alpine grass and flowers, seen from a slight aerial angle",
  },

  // Guarded crossings
  {
    id: "isle_waystone",
    blurb:
      "A small rest isle off the Lantern Spoke, marked by a standing stone carved with every lane on the shard. Skiff crews stop here to mend sails and eat.",
    landmarks: ["The Waystone", "The Mending Green"],
    resources: ["Meadow herbs (Herbalism)", "Burrow boar meat and hide (Hunting)"],
    art: "a small round floating meadow isle with a tall carved standing stone at its centre, a few skiffs tied up at a short jetty, a campfire and patched sails drying on the grass, seen from a slight aerial angle",
  },
  {
    id: "isle_ferrymoor",
    blurb:
      "A wooded isle beside the Tether Spoke, where ferries moor overnight. Its trees are young and plentiful, so new woodcutters practise here.",
    landmarks: ["The Ferry Moorings", "Learners' Wood"],
    resources: ["Pine and birch timber (Woodcutting)", "Glider squirrel fur (Hunting)", "Forest herbs (Herbalism)"],
    art: "a small floating forest isle of young pine and birch trees, a wooden mooring post line with ferries tied up, stacked logs and a woodcutters' hut, squirrels gliding between trees, seen from a slight aerial angle",
  },

  // The wild rim
  {
    id: "isle_grudgewood",
    blurb:
      "An ancient tree standing on some of the richest ore in the sky. The Rootborn want the tree left whole, the Skerrin want the ore beneath it, and neither has ever held it for long. The Grudge Wind blows straight past.",
    landmarks: ["The Grudge Tree", "The Broken Diggings", "The Last Truce Stone"],
    resources: ["Iron and rare ore under the roots (Mining)", "Ancient timber (Woodcutting)", "Bloom herbs (Herbalism)"],
    art: "a floating forest isle crowned by a huge ancient tree whose roots grip glittering veins of ore, abandoned mine shafts and stone barricades around its base, a cracked truce stone, stormy wind streaming past, seen from a slight aerial angle",
  },
  {
    id: "isle_ironreach",
    blurb:
      "A wild crag on the Long Gale, claimed by no one and fought over by many. Its iron is the best outside the Spires, and its caves hide stonewing swarms and ruin stalkers.",
    landmarks: ["The Reach", "Claim-jumpers' Camp", "The Bat Caves"],
    resources: ["Iron ore (Mining)", "Skysteel ore (Mining)", "Stonewing bat leather (Hunting)"],
    art: "a jagged floating crag isle on a strong wind current, rough mining camps with torn tents and timber shoring, dark cave mouths, bats swirling, fierce wind streaks around it, seen from a slight aerial angle",
  },
  {
    id: "isle_hollowsky",
    blurb:
      "A forest isle pierced by great holes, so the sky shows through its ground. Gale hawks nest in the gaps, and ruin stalkers prowl the old-world stones among the trees.",
    landmarks: ["The Sky Wells", "The Hawk Spires", "The Mossed Gate"],
    resources: ["Old-growth timber (Woodcutting)", "Rare forest herbs (Herbalism)", "Old-world relics (Salvage)"],
    art: "a floating forest isle pierced by several large round holes that show open sky and clouds beneath, tall dark trees and mossy old-world stone ruins, hawks circling above, seen from a slight aerial angle",
  },
  {
    id: "isle_ashfall",
    blurb:
      "A grey crag isle in its last days, slowly settling towards the storm. Ash-coloured dust falls from its underside, and every crew on the shard comes to strip it before it goes.",
    landmarks: ["The Tilted Spur", "The Ash Quarry", "The Leavers' Dock"],
    resources: ["Iron and copper ore (Mining)", "Salvage from abandoned camps (Salvage)", "Ash-grey stone (Mining)"],
    art: "a tilted grey floating crag isle sinking towards a churning storm, dust and rubble streaming from its underside, abandoned mining huts and a broken dock, small sailships crowding around it to salvage, seen from a slight aerial angle",
  },
  {
    id: "isle_last-light",
    blurb:
      "The easternmost isle on the shard, the first to see dawn and the last to lose sunset. A lonely meadow on the rim, with an old beacon that no one remembers lighting.",
    landmarks: ["The Old Beacon", "Dawnfield"],
    resources: ["Meadow herbs and flowers (Herbalism)", "Burrow boar meat and hide (Hunting)", "Cloud whale sightings for Lore"],
    art: "a small floating meadow isle on the edge of the world at sunrise, a tall old stone beacon tower on a grassy rise, wildflowers and long grass, a cloud whale drifting past in the distance, seen from a slight aerial angle",
  },
  {
    id: "isle_vael-s-shadow",
    blurb:
      "Broken ruins above the place where Vael sank. The Veiled come to mourn, the Rillfolk come to dive, and the two rarely part peacefully. Ruin stalkers haunt its fallen halls.",
    landmarks: ["The Mourning Steps", "The Shattered Oath Hall", "The Drowned Gate"],
    resources: ["Vaelish relics (Salvage)", "Old-world stone (Stonecraft)", "Inscriptions to study (Lore)"],
    art: "a low floating isle of broken pale stone ruins with tall arches and toppled statues, fragments of embroidered cloth tied to the columns, a great broken gateway at its edge, glowing storm clouds very close below, seen from a slight aerial angle",
  },
  {
    id: "isle_stormbite",
    blurb:
      "A low crag that the storm reaches up and strikes again and again. Its stone is scorched and full of skysteel, and skyrays hunt the ships that come for it.",
    landmarks: ["The Bitten Peak", "The Scorch Fields", "Skyray Roost"],
    resources: ["Skysteel ore (Mining)", "Storm-glass (Mining)", "Skyray hide (Hunting)"],
    art: "a jagged low floating crag isle with a scorched black peak, lightning forking up from the storm clouds just below and striking it, glinting veins of blue-silver ore, great rays gliding around it, seen from a slight aerial angle",
  },
  {
    id: "isle_wreckrest",
    blurb:
      "The lowest isle on the shard, sinking slowly into the storm, its shores heaped with the wrecks of ships that never came home. Salvagers race the storm for what remains.",
    landmarks: ["The Hull Graveyard", "The Sunk Stair", "The Last Mooring"],
    resources: ["Ship timber from the wrecks (Woodcutting)", "Old-world relics (Salvage)", "Lost cargo (Salvage)"],
    art: "a low ruined floating isle tilted and sinking into dark churning storm clouds, its edges piled with broken wooden ship hulls and torn sails, crumbling old-world stone stairs, salvagers on ropes, seen from a slight aerial angle",
  },
  {
    id: "isle_cinderkey",
    blurb:
      "A black-stone crag in the far southwest, cracked by old lightning. Its seams are rich and its winds are cruel. Gale hawks harass any skiff that lingers.",
    landmarks: ["The Black Key", "Cinder Seams"],
    resources: ["Coal and iron ore (Mining)", "Skysteel ore (Mining)", "Gale hawk feathers (Hunting)"],
    art: "a floating crag isle of dark cinder-black rock cracked with glinting seams, a few lonely mining shelters, flocks of hawks wheeling in the wind, seen from a slight aerial angle",
  },
  {
    id: "isle_brokenreach",
    blurb:
      "The far western rim, where a great old-world span juts out into empty sky and ends in nothing. No one knows where it once led. Ruin stalkers wait in its arches.",
    landmarks: ["The Broken Span", "The Stalker Arches", "The Sealed Vault"],
    resources: ["Old-world relics (Salvage)", "Carved stone (Stonecraft)", "Inscriptions to study (Lore)"],
    art: "a floating ruin isle with a colossal broken stone bridge of old-world arches jutting out into empty sky and ending abruptly, moss and vines over the stones, shadowy prowling shapes in the arches, seen from a slight aerial angle",
  },
  {
    id: "isle_duskcrown",
    blurb:
      "A wild forest in the far northwest whose canopy turns red and violet at every hour. Bark owls and stranger things wake here at night. Rootborn and Skerrin both claim it, and neither lives on it.",
    landmarks: ["The Crown Canopy", "The Night Glade"],
    resources: ["Duskwood timber (Woodcutting)", "Night-blooming herbs (Herbalism)", "Bark owl feathers (Hunting)"],
    art: "a small floating forest isle with a dense ring of trees whose leaves glow red and violet like dusk, forming a crown around a dark central glade, owls in the branches, fireflies, seen from a slight aerial angle",
  },
];
