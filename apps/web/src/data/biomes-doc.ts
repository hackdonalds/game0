// Parse concept/art-direction/biomes.md into biome entries. The doc is the single source of the biomes' text;
// this parser fails loudly when a field it expects is missing, so a reworded doc breaks the build instead of
// leaving stale text on the site. Plain TypeScript (no Vite features) so scripts/handbook-check.ts can use it too.

export interface BiomeDoc {
  /** Lower-case heading, matches the world file's `biome` field */
  id: string;
  name: string;
  /** Isle names from the italic list under the heading */
  isles: string[];
  /** The line under the heading after the isle list */
  intro: string;
  altitude: string;
  mood: string;
  ground: string;
  rock: string;
  trees: string;
  understory: string;
  water: string;
  signature: string;
  creatures: string;
  open?: string;
}

const FIELDS = ["Mood", "Ground", "Rock", "Trees", "Understory", "Water", "Signature", "Creatures"] as const;
const SOURCE = "concept/art-direction/biomes.md";

/** Strip inline markdown (links, emphasis, code) to plain text */
const plain = (s: string) => s.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/[*_`]/g, "").replace(/\s+/g, " ").trim();
const section = (md: string, heading: RegExp) => {
  const start = md.search(heading);
  if (start < 0) return undefined;
  const rest = md.slice(start).replace(heading, "");
  const end = rest.search(/^## /m);
  return end < 0 ? rest : rest.slice(0, end);
};
const fail = (msg: string): never => {
  throw new Error(`${SOURCE}: ${msg}. Update the doc or apps/web/src/data/biomes-doc.ts so the handbook does not drift.`);
};

/** Altitude ranges from the "Shared rules" table, keyed by lower-case biome id */
function altitudeTable(md: string) {
  const out = new Map<string, string>();
  const rules = section(md, /^## Shared rules\s*$/m) ?? fail('no "## Shared rules" section');
  for (const line of rules.split("\n")) {
    const cells = line.split("|").map((c) => c.trim()).filter(Boolean);
    if (cells.length < 2 || !/\d/.test(cells[0]) || /^-+$/.test(cells[0])) continue;
    for (const name of cells[1].split(/,|\band\b/)) if (name.trim()) out.set(name.trim().toLowerCase(), `${cells[0]} m`);
  }
  return out;
}

export function parseBiomes(md: string): BiomeDoc[] {
  const body = section(md, /^## The seven biomes\s*$/m) ?? fail('no "## The seven biomes" section');
  const table = altitudeTable(md);
  const blocks = body.split(/^### /m).slice(1);
  if (!blocks.length) fail('no "### <Biome>" headings under "## The seven biomes"');

  return blocks.map((block) => {
    const [heading, ...lines] = block.split("\n");
    const name = heading.trim();
    const id = name.toLowerCase();
    const where = `biome "${name}"`;
    const introLine = lines.find((l) => l.trim().startsWith("*") && !l.trim().startsWith("**")) ?? fail(`${where} has no italic isle line under its heading`);
    const isles = [...introLine.matchAll(/(?<!\*)\*([^*]+)\*(?!\*)/g)].flatMap((m) => m[1].split(/,\s*|\s+and\s+/)).map((s) => s.trim().replace(/[.,;:]+$/, "")).filter(Boolean);
    if (!isles.length) fail(`${where}: no isles in the italic list`);
    // The sentence after the last italic isle list
    const intro = plain(introLine.slice(introLine.lastIndexOf("*") + 1)).replace(/^[\s.,;:]+/, "");
    if (!intro) fail(`${where}: nothing after the isle list`);

    const field = (label: string) => {
      const line = lines.find((l) => new RegExp(`^\\s*-\\s*\\*\\*${label}:\\*\\*`).test(l));
      return line ? plain(line.replace(/^\s*-\s*\*\*[^*]+\*\*/, "")) : undefined;
    };
    const values = Object.fromEntries(FIELDS.map((f) => [f, field(f) ?? fail(`${where} has no "- **${f}:**" line`)])) as Record<(typeof FIELDS)[number], string>;

    const range = intro.match(/(−?\d+ to −?\d+) m\b/);
    const altitude = range ? `${range[1]} m` : table.get(id) ?? fail(`${where}: no altitude ("<a> to <b> m") in its intro line or the Shared rules table`);

    const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/[.;]?$/, ".");
    return {
      id, name, isles, intro, altitude,
      mood: sentence(values.Mood), ground: sentence(values.Ground), rock: sentence(values.Rock), trees: sentence(values.Trees),
      understory: sentence(values.Understory), water: sentence(values.Water), signature: sentence(values.Signature), creatures: sentence(values.Creatures),
      open: field("Open") && sentence(field("Open")!),
    };
  });
}

/** Which painted foliage sprites (art/textures/foliage/<name>.png) each nature kit script uses, keyed by biome id */
export function foliageUse(scripts: Record<string, string>) {
  const use = new Map<string, Set<string>>();
  for (const [path, src] of Object.entries(scripts)) {
    const biome = path.match(/nature-([a-z-]+)\.py$/)?.[1];
    if (!biome) continue;
    for (const m of src.matchAll(/foliage\/([a-z0-9-]+)\.png/g)) {
      if (!use.has(m[1])) use.set(m[1], new Set());
      use.get(m[1])!.add(biome);
    }
  }
  return use;
}
