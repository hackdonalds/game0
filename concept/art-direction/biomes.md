# Biomes

> Draft. Concept sheets in `art/concept/biomes/<biome>/`. The look of each of the seven biomes in `worlds/first-shard.world.json`: ground, rock, plants, water and what makes each one recognisable. It is the brief for the nature and terrain concept sheets and kits, as [architecture](architecture.md) is for buildings.

Sources: the isle entries and paintings ([`entries/isles/`](../entries/isles/), `art/concept/isles/`), [materials](../entries/materials/) and [creatures](../entries/bestiary/). Where the paintings disagree with this doc, this doc wins.

## Shared rules

**Altitude sets the mood.** The shard is a vertical world, and each biome sits at its own height above the storm layer, so the look runs from cold and bare at the top to wet and glowing at the bottom.

| Altitude (m above the cloud sea) | Biomes | Character |
| --- | --- | --- |
| 30 to 50 | Crag | Thin air, wind, bare rock, sparse alpine growth |
| 10 to 35 | Roothold, forest | Old growth, deep shade, giant trees |
| 0 to 20 | Meadow, garden | Open, tended, sunlit; the shard's middle ground |
| −5 to −25 | Lagoon | Wet, dim, teal glow; the storm flickers below |
| −45 to 10 | Ruin | Pale, broken, alien; mostly low and sinking |

**Every isle has three layers,** and each biome defines all three:

1. **Top:** ground cover, plants, paths, water.
2. **Lip:** the rounded edge where soil meets rock: overhanging grass, roots, ledges.
3. **Underside:** the rock that tapers to a point, with the biome's stone, roots and hanging growth. It is seen from bridges, ships and gliding, so it is as important as the top.

**Tier shows on the land.** Safe isles are tended: mown grass, swept paths, planted beds. Guarded isles are managed but rough. Wild isles are raw: long grass, deadfall, exposed rock, no paths.

**Sinking shows on the land.** A sinking isle tilts a few degrees, its lip cracks and crumbles, plants on the low side wilt and brown, and dust and stones stream from its underside. Newborn isles are bare fresh rock with the first moss, pioneer grass and no trees.

**Seasons** (decided: four) change colour more than shape: spring adds blossom and fresh green, summer is full and gold-lit, autumn turns leaves amber and red, winter frosts the crags and bares the deciduous trees. Evergreen biomes (crag pines, roothold moss) change least. Seasons are a shader and texture swap, not new models.

**Readability.** Ground stays soft and muted so characters and combat effects read against it. Saturated colour and glow are kept for points of interest: flowers, fungus, crystal, water.

**Painterly, not realistic.** Chunky readable shapes and clumped foliage masses (like the approved style tests), detail painted into textures, a few silhouettes per species rather than many.

## The seven biomes

### Roothold

*Elderroot, Rootmother, Deephold, Hollowgrain.* The Rootwardens' home among the oldest trees, 10 to 30 m up.

- **Mood:** ancient, shaded, sacred; green-gold light through a high canopy, glowing fungus at dusk.
- **Ground:** deep moss over dark loam, leaf litter, roots breaking the surface everywhere. Paths are packed earth between roots.
- **Rock:** mossy grey granite and slate (Deephold is quarried in steps). The underside is wrapped in huge roots that trail down into the clouds.
- **Trees:** the ancient tree (one per shrine isle, landmark scale, 30 to 50 m), oak and elder, birch and cedar; Hollowgrain's tree is hollow and open to the sky.
- **Understory:** ferns, root arches, fallen trunks, lichen-covered boulders, teal glowing mushrooms, seedling terraces on Rootmother.
- **Water:** springs that seep from roots and fall as thin waterfalls from the lip.
- **Signature:** roots at every scale, from ground cover to the isle's underside.
- **Creatures:** rootcrawlers in the caverns, bark owls in the hollows.

### Crag

*High Spire, Featherfast, Ironcleft, Gale Stair* (Galeborne), and the wild *Ironreach, Cinderkey, Stormbite, Ashfall*. The highest isles, 30 to 50 m up, except the low wild ones.

- **Mood:** windswept, vertical, bright and cold; long views, streaming cloud.
- **Ground:** thin alpine turf in patches over bare stone, scree slopes, wind-flattened grass and small bright flowers in sheltered ledges.
- **Rock:** cragslate: grey-blue, layered and sharp, with no ore seams on the Galeborne isles, broken into ledges and natural stairs (Gale Stair), split by clefts (Ironcleft). Wild crags are darker: cinder-black rock with glinting ore seams (Cinderkey, Ironreach), scorched black with storm-glass veins (Stormbite), ash-grey and crumbling (Ashfall, sinking).
- **Trees:** few: wind-bent pines and stunted junipers clinging to ledges, growing sideways from cliffs.
- **Understory:** cushion plants, lichen, alpine flowers, tumbled boulders, drake nests on the peaks.
- **Water:** snow on the highest peaks in winter, thin falls blown to spray by the wind.
- **Signature:** height and wind: spire silhouettes, ledges, everything leaning one way.
- **Creatures:** cliff goats, crag drakes, stonewing bats, gale hawks; skyrays around Stormbite.

### Meadow

*Accord Hall, Tetherport, Windmarket, Lanterncross, Oathgate, Waystone, Last Light.* The open middle ground, 0 to 20 m up, and home to the Accord towns.

- **Mood:** open, warm, welcoming; the classic sunlit sky isle of the approved style tests.
- **Ground:** rolling grass, long at the edges and mown in towns, drifts of wildflowers, hedgerows, clover.
- **Rock:** pale limestone, warm cream with soft weathering; quarried on Waystone. The underside is pale rock with grass and ivy hanging over the lip.
- **Trees:** meadow birch, orchard trees (apple and pear with spring blossom), lone broad oaks as landmarks, hedge rows.
- **Understory:** wildflowers, bushes, standing stones, low dry-stone walls.
- **Water:** reflecting ponds (Accord Hall), sky-ponds, streams that end in waterfalls off the lip.
- **Signature:** openness: long sightlines, flowers, and towns that sit comfortably in the grass.
- **Creatures:** burrow boars, glider squirrels.

### Garden

*Hearthfield, Terrace Hill, Slowfield, Greenfold.* The Garden Isles in the east, 0 to 10 m up, unclaimed farmland for player plots.

- **Mood:** cultivated, abundant, peaceful; patchwork colour that changes most with the seasons.
- **Ground:** terraced fields with stone retaining walls, furrowed soil, wheat and flax, vegetable rows, herb beds, meadow strips between plots.
- **Rock:** pale limestone (quarried on Terrace Hill) and warm clay; the underside shows terrace walls stepping down into the rock.
- **Trees:** orchards, windbreak poplars, hedgerows.
- **Understory:** crops by season, flowering beds, scarecrows' poles, fenced plots, haystacks.
- **Water:** fishponds, irrigation channels, a few wells.
- **Signature:** terraces and patchwork: the land itself is shaped by hand.
- **Creatures:** moss grazers in herds, burrow moles in the soft soil.
- **Open:** the Garden Isles have no architecture style yet; farms and plot buildings need their own pass.

### Forest

*Ferrymoor, Grudgewood, Hollowsky, Duskcrown.* Wild and border woodland, 10 to 35 m up.

- **Mood:** deep, quiet, a little dangerous; dappled light, then dark glades.
- **Ground:** needle and leaf litter, ferns, moss, exposed roots, deadfall.
- **Rock:** dark mossy stone; Hollowsky is pierced by holes that show sky beneath.
- **Trees:** dense pine and birch (Ferrymoor), old-growth giants (Hollowsky), the Duskcrown tree, a broad-crowned tree with red and violet leaves that glow at dusk (it yields duskcrown yew timber but reads as a broadleaf, as in the concept sheet), and the ancient Grudge Tree with axe scars at Grudgewood.
- **Understory:** ferns, brambles, fallen logs, stumps, mushrooms, fireflies at night.
- **Water:** brooks and still pools.
- **Signature:** canopy: these are the isles where the sky is hard to see.
- **Creatures:** glider squirrels, bark owls, hawks.

### Lagoon

*Ledgerstone, Chainwake, Lanternmere, Anchor Bay.* The Anchorkin Moorings, the lowest isles, −5 to −25 m, chained together near the storm.

- **Mood:** dim, wet, watchful; teal glow from the water and the storm flickering below.
- **Ground:** dark wet stone, sparse tough grass, reeds, sand in the bays (Anchor Bay), slick slate paving in the settlements.
- **Rock:** basalt and slate, dark and heavy, with teal crystal veins. The underside is streaked dark by spray from the storm.
- **Trees:** few: twisted salt-tolerant trees and dead snags leaning away from the storm wind.
- **Understory:** reed beds, glowweed, shells and crab shells on the shore, drift timber caught in chains.
- **Water:** the defining feature: dark round meres and chain pools that glow teal from eels and weed beneath, glowing shallows in the bays.
- **Signature:** dark stone, glowing water and the great chains that tie the isles together.
- **Creatures:** lantern eels, shellback crabs.

### Ruin

*Vael's Shadow, Wreckrest, Brokenreach.* Old-world remains on the wild rim, mostly low and sinking.

- **Mood:** silent, strange, melancholy; pale stone under a storm-lit sky.
- **Ground:** cracked pale paving and toppled blocks overgrown with moss, grass in the joints, rubble fields. Wreckrest is piled with wrecked ship hulls and torn sails.
- **Rock:** ruinstone: pale, unnaturally smooth where intact, sheared clean where broken. Dead teal channels run into the rock of the underside.
- **Trees:** few and opportunistic: a lone tree splitting a slab, roots gripping fallen arches.
- **Understory:** moss drapes, ivy, saplings in cracks, floating stone fragments.
- **Water:** rainwater in the channels; nothing flows.
- **Signature:** perfect geometry being reclaimed: the old-world ruin kit placed on the land.
- **Creatures:** ruin stalkers in the arches; storm creatures during surges.

## What to make

Per biome, the nature kit needs:

| Asset group | Contents |
| --- | --- |
| Trees | 2 to 3 species × 2 to 3 silhouettes each, plus a landmark tree where the biome has one |
| Understory | 4 to 6 pieces: bushes, ferns, flowers, reeds, crops |
| Ground cover | Grass and flower clumps, litter, scattered for instancing |
| Rocks | 4 to 5 boulders and outcrops in the biome's stone, plus cliff and ledge pieces for the lip |
| Underside | Rock taper pieces, hanging roots or growth, drips and falls |
| Water | Pond, pool and channel edges, and the biome's waterfall |
| Terrain materials | Ground, path, lip and cliff, underside: four painted textures per biome |

Shared across biomes: fallen logs, stumps, small stones and pebbles, and a seasonal variant of each foliage texture.

## Next steps

1. Concept sheets per biome: one "isle portrait" (top, lip and underside together) and one nature sheet (trees, plants, rocks), generated like the architecture sheets.
2. Nature kit sheets and a terrain materials sheet per biome, then manifests.
3. Build in Blender with `scripts/kit/kitlib.py`, and replace the placeholder nature kit and the vertex-coloured terrain in the roam demo.

## Open questions

- Weather per biome: wind streaks and snow on crags, mist in forests, drizzle and storm flashes at the lagoons?
- Do biomes blend on large isles, or does each isle keep one biome?
- How strongly should newborn isles differ from established ones in the same biome?
