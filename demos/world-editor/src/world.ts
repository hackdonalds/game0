// The world file format shared by the editor and, later, the game client and shard server.
// Units are metres. The map is the XZ plane; Y is altitude above the cloud sea (storm layer is below 0).

export const FORMAT = "game0-world";
export const VERSION = 1;

export const PEOPLES = ["none", "galeborne", "anchorkin", "rootwarden"] as const;
export const BIOMES = ["meadow", "forest", "roothold", "crag", "garden", "lagoon", "ruin"] as const;
export const TIERS = ["safe", "guarded", "wild"] as const;
export const STATES = ["stable", "sinking", "newborn"] as const;
export const WIND_KINDS = ["lane", "wild"] as const;

export type People = (typeof PEOPLES)[number];
export type Biome = (typeof BIOMES)[number];
export type Tier = (typeof TIERS)[number];
export type IsleState = (typeof STATES)[number];
export type WindKind = (typeof WIND_KINDS)[number];

export interface Isle {
  id: string;
  name: string;
  x: number;
  z: number;
  /** Altitude of the isle's top surface */
  y: number;
  radius: number;
  biome: Biome;
  /** Which people calls it home; "none" for shared or wild land */
  people: People;
  tier: Tier;
  town: boolean;
  shrine: boolean;
  /** Ancient tree that Treetending (a Rootwarden speciality) keeps, slowing the isle's sinking */
  ancientTree: boolean;
  state: IsleState;
}

/** An enchanted wind current. It blows along its points, first to last. */
export interface Wind {
  id: string;
  name: string;
  kind: WindKind;
  points: [number, number][];
  y: number;
  /** Width of the current in metres */
  width: number;
  /** Wind speed in metres per second */
  strength: number;
  /** 0 = steady, 1 = violently gusty and shifting */
  gustiness: number;
}

export interface Bridge {
  id: string;
  a: string;
  b: string;
}

export interface World {
  format: typeof FORMAT;
  version: number;
  name: string;
  seed: number;
  /** Radius of the playable sky in metres */
  size: number;
  /** Altitude of the storm layer; isles that sink below it are lost */
  stormY: number;
  /** Ambient wind outside currents, in metres per second, blowing towards this heading (degrees, 0 = +Z) */
  ambientWind: { heading: number; strength: number };
  isles: Isle[];
  winds: Wind[];
  bridges: Bridge[];
}

export const uid = (prefix: string) => `${prefix}_${Math.random().toString(36).slice(2, 9)}`;

export function emptyWorld(name = "New shard"): World {
  return { format: FORMAT, version: VERSION, name, seed: 1, size: 1200, stormY: -60, ambientWind: { heading: 45, strength: 3 }, isles: [], winds: [], bridges: [] };
}

export function newIsle(x: number, z: number, patch: Partial<Isle> = {}): Isle {
  return { id: uid("isle"), name: "Unnamed isle", x, z, y: 0, radius: 40, biome: "meadow", people: "none", tier: "wild", town: false, shrine: false, ancientTree: false, state: "stable", ...patch };
}

/** Accepts a parsed JSON value and returns a clean World, filling defaults and dropping broken references. */
export function parseWorld(data: unknown): World {
  const d = data as Partial<World>;
  if (!d || d.format !== FORMAT) throw new Error(`Not a ${FORMAT} file`);
  if ((d.version ?? 0) > VERSION) throw new Error(`World version ${d.version} is newer than this editor (${VERSION})`);
  const base = emptyWorld();
  const isles = (d.isles ?? []).map((i) => newIsle(i.x, i.z, i));
  const ids = new Set(isles.map((i) => i.id));
  return {
    ...base,
    ...d,
    ambientWind: { ...base.ambientWind, ...d.ambientWind },
    version: VERSION,
    isles,
    winds: (d.winds ?? []).filter((w) => w.points?.length >= 2).map((w) => ({ ...({ id: uid("wind"), name: "Wind", kind: "lane", y: 0, width: 60, strength: 12, gustiness: 0.2 } as Wind), ...w })),
    bridges: (d.bridges ?? []).filter((b) => ids.has(b.a) && ids.has(b.b) && b.a !== b.b),
  };
}

// ---------- Procedural generation ----------

function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const HOMELANDS: { people: People; biome: Biome; names: string[]; tree?: boolean }[] = [
  { people: "rootwarden", biome: "roothold", names: ["Elderroot", "Deephold", "Barkmoor", "Rootmother", "Hollowgrain"], tree: true },
  { people: "galeborne", biome: "crag", names: ["High Spire", "Featherfast", "Ironcleft", "Gale Stair", "Shalepeak"] },
  // The Garden Isles belong to no people: unclaimed farmland for player plots
  { people: "none", biome: "garden", names: ["Hearthfield", "Terrace Hill", "Slowfield", "Greenfold", "Mossmere"] },
  { people: "anchorkin", biome: "lagoon", names: ["Ledgerstone", "Chainwake", "Brightrill", "Anchor Bay", "Lanternmere"] },
];
const TOWNS = ["Accord Hall", "Tetherport", "Lanterncross", "Windmarket", "Oathgate", "Saltcloud"];
const WILD = ["Ashfall", "Brokenreach", "Cinderkey", "Duskcrown", "Grimwater", "Hollowsky", "Ruinmark", "Stormbite", "Thornveil", "Vael's Shadow", "Wreckrest", "Gloamrock", "Sundered Isle", "Last Light"];

/** Generates a plausible shard: four homelands, Accord towns linked by wind lanes, wild isles around the rim. */
export function generateWorld(seed: number, name = `Shard ${seed}`): World {
  const r = rng(seed);
  const pick = <T,>(xs: T[]) => xs[Math.floor(r() * xs.length)];
  const range = (a: number, b: number) => a + r() * (b - a);
  const w = { ...emptyWorld(name), seed };
  // Deterministic ids, so the same seed always produces an identical world
  let next = 0;
  const gid = (prefix: string) => `${prefix}_g${next++}`;
  w.ambientWind = { heading: Math.round(range(0, 360)), strength: Math.round(range(2, 5)) };
  const fits = (x: number, z: number, rad: number) => w.isles.every((i) => Math.hypot(i.x - x, i.z - z) > i.radius + rad + 25);
  const place = (cx: number, cz: number, spread: number, rad: number, patch: Partial<Isle>) => {
    for (let n = 0; n < 40; n++) {
      const a = r() * Math.PI * 2, d = r() * spread;
      const x = cx + Math.cos(a) * d, z = cz + Math.sin(a) * d;
      if (Math.hypot(x, z) + rad < w.size && fits(x, z, rad)) {
        const isle = newIsle(Math.round(x), Math.round(z), { id: gid("isle"), radius: Math.round(rad), y: Math.round(range(-15, 25)), ...patch });
        w.isles.push(isle);
        return isle;
      }
    }
  };

  // Central Accord town, then smaller towns between the homelands
  const towns: Isle[] = [];
  const hub = place(0, 0, 10, 70, { name: TOWNS[0], biome: "meadow", tier: "safe", town: true, shrine: true });
  if (hub) towns.push(hub);
  const turn = r() * Math.PI * 2;
  HOMELANDS.forEach((h, k) => {
    const a = turn + (k / HOMELANDS.length) * Math.PI * 2;
    const hx = Math.cos(a) * w.size * 0.55, hz = Math.sin(a) * w.size * 0.55;
    const names = [...h.names];
    const count = 3 + Math.floor(r() * 2);
    const cluster: Isle[] = [];
    for (let n = 0; n < count; n++) {
      const isle = place(hx, hz, n === 0 ? 0 : 160, n === 0 ? range(60, 75) : range(30, 50), {
        name: names.splice(Math.floor(r() * names.length), 1)[0], biome: h.biome, people: h.people, tier: "guarded",
        shrine: n === 0, ancientTree: !!h.tree && n < 2,
      });
      if (isle) cluster.push(isle);
    }
    // Bridges link each homeland isle to its nearest neighbour in the cluster
    cluster.slice(1).forEach((isle) => {
      const near = cluster.filter((o) => o !== isle).sort((p, q) => Math.hypot(p.x - isle.x, p.z - isle.z) - Math.hypot(q.x - isle.x, q.z - isle.z))[0];
      if (near && Math.hypot(near.x - isle.x, near.z - isle.z) - near.radius - isle.radius < 120) w.bridges.push({ id: gid("bridge"), a: isle.id, b: near.id });
    });
    // A town on the lane between this homeland and the next
    const b = a + Math.PI / HOMELANDS.length;
    const town = place(Math.cos(b) * w.size * 0.42, Math.sin(b) * w.size * 0.42, 40, range(45, 55), { name: TOWNS[k + 1], biome: "meadow", tier: "safe", town: true, shrine: true });
    if (town) towns.push(town);
  });

  // Wild isles fill the rim and the gaps
  const wildNames = [...WILD];
  for (let n = 0; n < 14; n++) {
    const a = r() * Math.PI * 2, d = range(0.3, 0.92) * w.size;
    place(Math.cos(a) * d, Math.sin(a) * d, 30, range(25, 55), {
      name: wildNames.splice(Math.floor(r() * wildNames.length), 1)[0] ?? "Nameless rock",
      biome: pick<Biome>(["forest", "crag", "ruin", "meadow", "ruin"]), tier: "wild",
    });
  }
  const wild = w.isles.filter((i) => i.tier === "wild");
  for (let n = 0; n < 2 && wild.length; n++) wild.splice(Math.floor(r() * wild.length), 1)[0].state = "sinking";
  const birth = place(0, 0, w.size * 0.85, 35, { name: "Unnamed newborn isle", biome: "meadow", tier: "wild", state: "newborn" });
  if (birth) birth.y = Math.round(w.stormY + 30);

  // Accord lanes: a steady ring through the outer towns, plus spokes to the hub
  const ring = towns.slice(1).sort((p, q) => Math.atan2(p.z, p.x) - Math.atan2(q.z, q.x));
  if (ring.length > 2) {
    const pts = ring.map((t) => [t.x, t.z] as [number, number]);
    w.winds.push({ id: gid("wind"), name: "Accord Ring", kind: "lane", points: [...pts, pts[0]], y: 10, width: 70, strength: 12, gustiness: 0.1 });
  }
  if (hub) ring.filter((_, k) => k % 2 === 0).forEach((t, k) => {
    const pts: [number, number][] = [[hub.x, hub.z], [(hub.x + t.x) / 2 + range(-40, 40), (hub.z + t.z) / 2 + range(-40, 40)], [t.x, t.z]];
    w.winds.push({ id: gid("wind"), name: `Hub lane ${k + 1}`, kind: "lane", points: k % 2 ? pts.reverse() : pts, y: 15, width: 60, strength: 10, gustiness: 0.1 });
  });
  // Wild currents: fast, gusty arcs across the rim
  for (let n = 0; n < 3; n++) {
    const a0 = r() * Math.PI * 2, sweep = range(0.8, 1.6) * (r() < 0.5 ? -1 : 1), d = range(0.7, 0.95) * w.size;
    const pts: [number, number][] = [];
    for (let s = 0; s <= 4; s++) {
      const a = a0 + (sweep * s) / 4, dd = d + range(-80, 80);
      pts.push([Math.round(Math.cos(a) * dd), Math.round(Math.sin(a) * dd)]);
    }
    w.winds.push({ id: gid("wind"), name: `Wild current ${n + 1}`, kind: "wild", points: pts, y: Math.round(range(-10, 30)), width: 90, strength: Math.round(range(18, 26)), gustiness: 0.7 });
  }
  return w;
}
