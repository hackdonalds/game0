// Three-level NPC simulation, written the way the shard server would run it: no rendering in here.
// Full: 20 Hz steering near players. Light: 1 Hz state machine nearby. Abstract: timed plans everywhere else.

export interface SimIsle { x: number; y: number; z: number; radius: number; town: boolean; people: string; tier: string; name: string; biome: string }

export const Tier = { Abstract: 0, Light: 1, Full: 2 } as const;
export type Tier = (typeof Tier)[keyof typeof Tier];
export const JOBS = ["trader", "hauler", "gatherer", "worker"] as const;
export type Job = (typeof JOBS)[number];

export interface Npc {
  id: number;
  job: Job;
  home: number;
  tier: Tier;
  // The plan: travelling from → to, or an activity on one isle when from === to
  from: number;
  to: number;
  depart: number;
  arrive: number;
  // Local state, only meaningful at Light and Full
  x: number; y: number; z: number;
  px: number; pz: number; // position at the previous Light tick, for interpolation
  vx: number; vz: number;
  tx: number; tz: number;
  state: "walk" | "work" | "greet";
  until: number;
  nextThink: number;
}

export interface Settings { fullRadius: number; lightRadius: number }

export interface TierStats { count: number; updates: number; ms: number }

const SAIL_SPEED = 14; // m/s along a route
const WALK_SPEED = 1.4;
const FULL_HZ = 20;
const LIGHT_HZ = 1;
const ABSTRACT_CHECK = 2; // seconds of sim time between batch checks
const TIER_CHECK = 0.25; // real seconds between tier reassignments

// Small deterministic hash so abstract positions are stable without storing them
const hash = (a: number, b: number) => {
  let h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x632be5ab, 0xc2b2ae35);
  h ^= h >>> 15; h = Math.imul(h, 0x27d4eb2d); h ^= h >>> 13;
  return (h >>> 0) / 4294967296;
};

export class Sim {
  npcs: Npc[] = [];
  t = 0;
  player = { x: 0, y: 0, z: 0 };
  stats: Record<"full" | "light" | "abstract" | "tiering", TierStats> = {
    full: { count: 0, updates: 0, ms: 0 }, light: { count: 0, updates: 0, ms: 0 },
    abstract: { count: 0, updates: 0, ms: 0 }, tiering: { count: 0, updates: 0, ms: 0 },
  };
  private towns: number[];
  private wild: number[];
  private homes: number[];
  private fullAcc = 0;
  private abstractAcc = 0;
  private tierAcc = 0;
  private rand: () => number;

  constructor(public isles: SimIsle[], count: number, public settings: Settings, seed = 1) {
    let a = seed;
    this.rand = () => ((a = Math.imul(a ^ (a >>> 15), a | 1) + 0x6d2b79f5) >>> 0) / 4294967296;
    this.towns = isles.map((_, i) => i).filter((i) => isles[i].town);
    this.wild = isles.map((_, i) => i).filter((i) => isles[i].tier === "wild");
    // Homes: homeland isles, towns, and the unclaimed Garden Isles where farmers live
    this.homes = isles.map((_, i) => i).filter((i) => isles[i].people !== "none" || isles[i].town || isles[i].biome === "garden");
    for (let id = 0; id < count; id++) this.npcs.push(this.spawn(id));
  }

  private pick<T>(xs: T[]) { return xs[Math.floor(this.rand() * xs.length)]; }

  private spawn(id: number): Npc {
    const r = this.rand();
    const job: Job = r < 0.15 ? "trader" : r < 0.35 ? "hauler" : r < 0.5 ? "gatherer" : "worker";
    const home = job === "trader" ? this.pick(this.towns) : this.pick(this.homes);
    const n: Npc = {
      id, job, home, tier: Tier.Abstract, from: home, to: home, depart: 0, arrive: 0,
      x: 0, y: 0, z: 0, px: 0, pz: 0, vx: 0, vz: 0, tx: 0, tz: 0, state: "work", until: 0, nextThink: 0,
    };
    // Start part-way through a plan so the world is already in motion
    this.plan(n, -this.rand() * 300);
    return n;
  }

  private nearestTown(i: number) {
    const a = this.isles[i];
    return this.towns.reduce((best, t) => (Math.hypot(this.isles[t].x - a.x, this.isles[t].z - a.z) < Math.hypot(this.isles[best].x - a.x, this.isles[best].z - a.z) ? t : best), this.towns[0]);
  }

  /** The utility-planner stand-in: choose the next segment when the current one ends. */
  private plan(n: Npc, now: number) {
    const at = n.to;
    const wasTravel = n.from !== n.to;
    let dest = at;
    if (!wasTravel || n.arrive === 0) {
      if (n.job === "trader") dest = this.pick(this.towns.filter((t) => t !== at));
      else if (n.job === "hauler") dest = at === n.home ? this.nearestTown(n.home) : n.home;
      else if (n.job === "gatherer") dest = at === n.home ? this.pick(this.wild) : n.home;
      if (n.arrive === 0 && this.rand() < 0.6) dest = at; // some start mid-activity
    }
    n.from = at;
    n.to = dest;
    n.depart = now;
    if (dest === at) n.arrive = now + 40 + this.rand() * 160;
    else {
      const a = this.isles[at], b = this.isles[dest];
      n.arrive = now + Math.hypot(b.x - a.x, b.z - a.z) / SAIL_SPEED;
    }
  }

  /** Where the plan says this NPC is at time t. Used for Abstract NPCs and when promoting. */
  planPosition(n: Npc, t: number, out: { x: number; y: number; z: number }) {
    const a = this.isles[n.from], b = this.isles[n.to];
    if (n.from === n.to) {
      const ang = hash(n.id, Math.floor(n.depart)) * Math.PI * 2;
      const d = Math.sqrt(hash(n.id + 7, Math.floor(n.depart))) * a.radius * 0.7;
      out.x = a.x + Math.cos(ang) * d; out.z = a.z + Math.sin(ang) * d; out.y = a.y + 1;
    } else {
      const u = Math.min(1, Math.max(0, (t - n.depart) / (n.arrive - n.depart)));
      out.x = a.x + (b.x - a.x) * u; out.z = a.z + (b.z - a.z) * u;
      out.y = a.y + (b.y - a.y) * u + Math.sin(u * Math.PI) * 25 + 4;
    }
    return out;
  }

  private tmp = { x: 0, y: 0, z: 0 };

  /** Advance by realDt seconds of wall time, with sim time running timeScale times faster. */
  step(realDt: number, timeScale: number) {
    const dt = realDt * timeScale;
    this.t += dt;
    for (const s of Object.values(this.stats)) { s.updates = 0; s.ms = 0; }

    this.tierAcc += realDt;
    if (this.tierAcc >= TIER_CHECK) { this.tierAcc = 0; this.assignTiers(); }

    // Abstract: one cheap batch pass; real work only for plans that have ended
    this.abstractAcc += dt;
    if (this.abstractAcc >= ABSTRACT_CHECK) {
      this.abstractAcc = 0;
      const t0 = performance.now();
      for (const n of this.npcs) {
        if (n.tier !== Tier.Abstract) continue;
        while (n.arrive <= this.t) { this.plan(n, n.arrive); this.stats.abstract.updates++; }
      }
      this.stats.abstract.ms += performance.now() - t0;
    }

    // Light: each NPC thinks once per second of wall time, staggered
    const t1 = performance.now();
    const now = performance.now() / 1000;
    for (const n of this.npcs) {
      if (n.tier !== Tier.Light || now < n.nextThink) continue;
      n.nextThink = now + 1 / LIGHT_HZ;
      n.px = n.x; n.pz = n.z;
      this.think(n, timeScale / LIGHT_HZ, false);
      this.stats.light.updates++;
    }
    this.stats.light.ms += performance.now() - t1;

    // Full: fixed 20 Hz steps with neighbour avoidance
    this.fullAcc += realDt;
    const t2 = performance.now();
    while (this.fullAcc >= 1 / FULL_HZ) {
      this.fullAcc -= 1 / FULL_HZ;
      this.fullStep(timeScale / FULL_HZ);
    }
    this.stats.full.ms += performance.now() - t2;
  }

  private assignTiers() {
    const t0 = performance.now();
    const { fullRadius, lightRadius } = this.settings;
    const p = this.player;
    let full = 0, light = 0;
    for (const n of this.npcs) {
      const pos = n.tier === Tier.Abstract ? this.planPosition(n, this.t, this.tmp) : n;
      const d = Math.hypot(pos.x - p.x, pos.z - p.z);
      const want = d < fullRadius ? Tier.Full : d < lightRadius ? Tier.Light : Tier.Abstract;
      if (want !== n.tier) {
        if (n.tier === Tier.Abstract) this.promote(n);
        if (want === Tier.Abstract) this.demote(n);
        n.tier = want;
      }
      if (n.tier === Tier.Full) full++; else if (n.tier === Tier.Light) light++;
    }
    this.stats.full.count = full;
    this.stats.light.count = light;
    this.stats.abstract.count = this.npcs.length - full - light;
    this.stats.tiering.ms += performance.now() - t0;
    this.stats.tiering.updates++;
  }

  /** Abstract → Light/Full: catch the plan up to now and place the NPC where it says. */
  private promote(n: Npc) {
    while (n.arrive <= this.t) this.plan(n, n.arrive);
    this.planPosition(n, this.t, n);
    n.px = n.x; n.pz = n.z; n.vx = n.vz = 0;
    n.state = "work"; n.until = this.t + this.rand() * 4; n.tx = n.x; n.tz = n.z;
    n.nextThink = performance.now() / 1000 + this.rand() / LIGHT_HZ;
  }

  /** Light/Full → Abstract: keep the plan, drop the local state. Nobody is near enough to see the jump. */
  private demote(_n: Npc) {}

  /** The state machine shared by Light and Full. dt is sim seconds since the last think. */
  private think(n: Npc, dt: number, full: boolean) {
    if (n.arrive <= this.t) {
      this.plan(n, this.t);
      if (n.from === n.to) { n.state = "work"; n.until = this.t; }
    }
    if (n.from !== n.to) { this.planPosition(n, this.t, n); return; } // sailing follows the route
    const isle = this.isles[n.from];
    n.y = isle.y + 1;
    if (n.state !== "walk" && this.t >= n.until) {
      const ang = this.rand() * Math.PI * 2, d = Math.sqrt(this.rand()) * isle.radius * 0.75;
      n.tx = isle.x + Math.cos(ang) * d; n.tz = isle.z + Math.sin(ang) * d;
      n.state = "walk";
    }
    if (n.state === "walk" && !full) {
      const dx = n.tx - n.x, dz = n.tz - n.z, d = Math.hypot(dx, dz), stepLen = WALK_SPEED * dt;
      if (d <= stepLen) { n.x = n.tx; n.z = n.tz; n.state = "work"; n.until = this.t + 3 + this.rand() * 8; }
      else { n.x += (dx / d) * stepLen; n.z += (dz / d) * stepLen; }
    }
  }

  // Spatial hash over Full NPCs only, for separation
  private grid = new Map<number, Npc[]>();
  private fullStep(dt: number) {
    const CELL = 4;
    const key = (x: number, z: number) => (Math.floor(x / CELL) & 0xffff) | ((Math.floor(z / CELL) & 0xffff) << 16);
    this.grid.clear();
    const full: Npc[] = [];
    for (const n of this.npcs) {
      if (n.tier !== Tier.Full) continue;
      full.push(n);
      const k = key(n.x, n.z);
      const cell = this.grid.get(k);
      if (cell) cell.push(n); else this.grid.set(k, [n]);
    }
    const p = this.player;
    for (const n of full) {
      this.think(n, dt, true);
      this.stats.full.updates++;
      if (n.from !== n.to) continue;
      // Notice the player: stop and turn to greet when close
      const pd = Math.hypot(p.x - n.x, p.z - n.z);
      if (pd < 8 && n.state !== "greet") { n.state = "greet"; n.until = this.t + 4; }
      if (n.state === "greet" && this.t >= n.until) n.state = "work";
      // Seek target
      let ax = 0, az = 0;
      if (n.state === "walk") {
        const dx = n.tx - n.x, dz = n.tz - n.z, d = Math.hypot(dx, dz);
        if (d < 0.5) { n.state = "work"; n.until = this.t + 3 + this.rand() * 8; }
        else { ax += (dx / d) * WALK_SPEED - n.vx; az += (dz / d) * WALK_SPEED - n.vz; }
      } else { ax -= n.vx * 2; az -= n.vz * 2; }
      // Separation from neighbours
      const cx = Math.floor(n.x / CELL), cz = Math.floor(n.z / CELL);
      for (let ix = -1; ix <= 1; ix++) for (let iz = -1; iz <= 1; iz++) {
        const cell = this.grid.get(((cx + ix) & 0xffff) | (((cz + iz) & 0xffff) << 16));
        if (!cell) continue;
        for (const o of cell) {
          if (o === n) continue;
          const dx = n.x - o.x, dz = n.z - o.z, d2 = dx * dx + dz * dz;
          if (d2 > 0.0001 && d2 < 2.5) { const f = (2.5 - d2) * 1.5; ax += dx * f; az += dz * f; }
        }
      }
      // Keep personal space around the player
      if (pd < 2.5 && pd > 0.01) { ax += ((n.x - p.x) / pd) * 4; az += ((n.z - p.z) / pd) * 4; }
      n.vx += ax * dt * 4; n.vz += az * dt * 4;
      const sp = Math.hypot(n.vx, n.vz);
      if (sp > WALK_SPEED * 1.5) { n.vx *= (WALK_SPEED * 1.5) / sp; n.vz *= (WALK_SPEED * 1.5) / sp; }
      n.x += n.vx * dt; n.z += n.vz * dt;
      // Stay on the isle
      const isle = this.isles[n.from];
      const ex = n.x - isle.x, ez = n.z - isle.z, ed = Math.hypot(ex, ez), max = isle.radius * 0.85;
      if (ed > max) { n.x = isle.x + (ex / ed) * max; n.z = isle.z + (ez / ed) * max; }
      n.px = n.x; n.pz = n.z;
    }
  }
}
