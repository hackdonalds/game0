// The seven biomes of the First Shard, from concept/art-direction/biomes.md. Ids match the world file's `biome` field.
// Sheets are plates under art/handbook/biomes/ (made by scripts/handbook-sheets.ts).
import type { Sheet } from "./architecture";

export interface Biome {
  id: string;
  name: string;
  altitude: string;
  summary: string;
  look: { label: string; value: string }[];
  signature: string;
  creatures: string;
  /** Architecture styles built here */
  styles: string[];
  sheets: Sheet[];
  open?: string;
}

const sheets = (extra: Sheet[] = []): Sheet[] => [
  { id: "isle-portrait", label: "Isle portrait: top, lip and underside" }, ...extra,
  { id: "nature", label: "Nature: trees, plants and rocks" },
  { id: "terrain", label: "Terrain materials" },
];

export const biomes: Biome[] = [
  {
    id: "roothold", name: "Roothold", altitude: "10 to 30 m",
    summary: "The Rootwardens' home among the oldest trees: ancient and shaded, green-gold light through a high canopy and glowing fungus at dusk.",
    look: [
      { label: "Ground", value: "Deep moss over dark loam, leaf litter, roots breaking the surface; packed-earth paths between roots" },
      { label: "Rock", value: "Mossy grey granite and slate; the underside is wrapped in huge roots trailing into the clouds" },
      { label: "Trees", value: "The ancient tree on shrine isles (30 to 50 m), oak and elder, birch and cedar" },
      { label: "Understory", value: "Ferns, root arches, fallen trunks, lichen boulders, teal glowing mushrooms" },
      { label: "Water", value: "Springs seeping from roots, thin waterfalls from the lip" },
    ],
    signature: "Roots at every scale, from ground cover to the isle's underside.",
    creatures: "Rootcrawlers in the caverns, bark owls in the hollows.",
    styles: ["rootwarden"], sheets: sheets(),
  },
  {
    id: "crag", name: "Crag", altitude: "30 to 50 m",
    summary: "The highest isles: windswept, vertical, bright and cold, with long views and streaming cloud. Galeborne spires above, dark ore-seamed wild crags on the rim.",
    look: [
      { label: "Ground", value: "Thin alpine turf over bare stone, scree, wind-flattened grass, small bright flowers on ledges" },
      { label: "Rock", value: "Grey-blue layered cragslate; wild crags are cinder-black with ore seams or scorched with storm-glass veins" },
      { label: "Trees", value: "Few: wind-bent pines and stunted junipers growing sideways from cliffs" },
      { label: "Understory", value: "Cushion plants, lichen, alpine flowers, tumbled boulders, drake nests" },
      { label: "Water", value: "Winter snow on the peaks, thin falls blown to spray" },
    ],
    signature: "Height and wind: spire silhouettes, ledges, everything leaning one way.",
    creatures: "Cliff goats, crag drakes, stonewing bats, gale hawks; skyrays around Stormbite.",
    styles: ["galeborne"], sheets: sheets([{ id: "isle-portrait-wild", label: "Wild crag portrait" }]),
  },
  {
    id: "meadow", name: "Meadow", altitude: "0 to 20 m",
    summary: "The open middle ground and home of the Accord towns: warm and welcoming, the classic sunlit sky isle.",
    look: [
      { label: "Ground", value: "Rolling grass, long at the edges and mown in towns, wildflower drifts, hedgerows, clover" },
      { label: "Rock", value: "Pale cream limestone with soft weathering; grass and ivy hang over the lip" },
      { label: "Trees", value: "Meadow birch, apple and pear orchards, lone broad oaks, hedge rows" },
      { label: "Understory", value: "Wildflowers, bushes, standing stones, low dry-stone walls" },
      { label: "Water", value: "Reflecting ponds, sky-ponds, streams ending in waterfalls off the lip" },
    ],
    signature: "Openness: long sightlines, flowers, and towns that sit comfortably in the grass.",
    creatures: "Burrow boars, glider squirrels.",
    styles: ["accord"], sheets: sheets(),
  },
  {
    id: "garden", name: "Garden", altitude: "0 to 10 m",
    summary: "The Garden Isles in the east: unclaimed farmland for player plots, cultivated and abundant, the patchwork that changes most with the seasons.",
    look: [
      { label: "Ground", value: "Terraced fields with stone retaining walls, wheat and flax, vegetable rows, herb beds" },
      { label: "Rock", value: "Pale limestone and warm clay; terrace walls step down into the underside" },
      { label: "Trees", value: "Orchards, windbreak poplars, hedgerows" },
      { label: "Understory", value: "Crops by season, flowering beds, fenced plots, haystacks" },
      { label: "Water", value: "Fishponds, irrigation channels, a few wells" },
    ],
    signature: "Terraces and patchwork: the land itself is shaped by hand.",
    creatures: "Moss grazers in herds, burrow moles in the soft soil.",
    styles: [], sheets: sheets(),
    open: "The Garden Isles have no architecture style yet; farms and plot buildings need their own pass.",
  },
  {
    id: "forest", name: "Forest", altitude: "10 to 35 m",
    summary: "Wild and border woodland: deep, quiet and a little dangerous, dappled light giving way to dark glades.",
    look: [
      { label: "Ground", value: "Needle and leaf litter, ferns, moss, exposed roots, deadfall" },
      { label: "Rock", value: "Dark mossy stone; Hollowsky is pierced by holes that show the sky beneath" },
      { label: "Trees", value: "Dense pine and birch, old-growth giants, the glowing Duskcrown tree and the scarred Grudge Tree" },
      { label: "Understory", value: "Ferns, brambles, fallen logs, stumps, mushrooms, fireflies at night" },
      { label: "Water", value: "Brooks and still pools" },
    ],
    signature: "Canopy: these are the isles where the sky is hard to see.",
    creatures: "Glider squirrels, bark owls, hawks.",
    styles: ["rootwarden"], sheets: sheets(),
  },
  {
    id: "lagoon", name: "Lagoon", altitude: "−5 to −25 m",
    summary: "The Anchorkin Moorings, the lowest isles, chained together near the storm: dim, wet and watchful, with teal glow from the water.",
    look: [
      { label: "Ground", value: "Dark wet stone, tough grass, reeds, sand in the bays, slick slate paving" },
      { label: "Rock", value: "Dark basalt and slate with teal crystal veins; the underside streaked by storm spray" },
      { label: "Trees", value: "Few: twisted salt-tolerant trees and dead snags leaning from the storm wind" },
      { label: "Understory", value: "Reed beds, glowweed, shells on the shore, drift timber caught in chains" },
      { label: "Water", value: "Dark round meres and chain pools glowing teal from eels and weed beneath" },
    ],
    signature: "Dark stone, glowing water and the great chains that tie the isles together.",
    creatures: "Lantern eels, shellback crabs.",
    styles: ["anchorkin"], sheets: sheets(),
  },
  {
    id: "ruin", name: "Ruin", altitude: "−45 to 10 m",
    summary: "Old-world remains on the wild rim, mostly low and sinking: silent, strange and melancholy, pale stone under a storm-lit sky.",
    look: [
      { label: "Ground", value: "Cracked pale paving, toppled blocks overgrown with moss, rubble fields, wrecked hulls on Wreckrest" },
      { label: "Rock", value: "Ruinstone: unnaturally smooth where intact, sheared clean where broken, dead teal channels" },
      { label: "Trees", value: "Few and opportunistic: a lone tree splitting a slab, roots gripping fallen arches" },
      { label: "Understory", value: "Moss drapes, ivy, saplings in cracks, floating stone fragments" },
      { label: "Water", value: "Rainwater in the channels; nothing flows" },
    ],
    signature: "Perfect geometry being reclaimed: the old-world ruin kit placed on the land.",
    creatures: "Prowlers in the arches; storm creatures during surges.",
    styles: ["old-world"], sheets: sheets(),
  },
];
