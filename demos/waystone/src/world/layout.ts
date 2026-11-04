// Waystone isle layout: one analytic height/shape function shared by the terrain mesh and heightAt.
// +z is south (jetty, spawn), -z is north (Storm Ridge, chasm, summit rock with the Waystone).
//
//   main body   meadow disc, ridge rising north to a cliff over the chasm (bridge start, glide spur)
//   summit      separate rock across the chasm: arena, raised plinth with the Waystone, low SW landing ledge
//   east arm    narrow winding rock spine joining main to summit around the chasm's east end (old trees)
import * as THREE from "three";
import { fbm, smooth } from "./noise";

export const RIDGE_H = 10; // main body at the chasm lip
export const ARENA_H = 11;
export const LEDGE_H = 5;
export const SPUR_H = 15;
export const PLINTH_RISE = 3.2;

const MAIN = { x: 0, z: 10, r: 42 };
const CHASM_Z = -24;
const SUMMIT = { x: -2, z: -54, r: 17 };
const LEDGE = { x: -13, z: -44, r: 6.5 };
export const ARENA_C = { x: 2, z: -50 };
export const PLINTH_C = { x: -1, z: -62 };
export const CAMP_C = { x: 11, z: 29 };
export const GLIDE_C = { x: -18, z: -22.3 };

export const BRIDGE = { x: 4, z0: -21.2, z1: -39.2, half: 1.15, sag: 0.9 };
export const JETTY = { x: 0, z0: 49.5, z1: 57.0, half: 0.8, zc: 54.05 };

/** Dense samples of a smoothed polyline with cumulative length, for distance queries. */
export class Track {
  readonly px: Float32Array;
  readonly pz: Float32Array;
  readonly len: Float32Array;
  readonly total: number;
  readonly minX: number; readonly maxX: number; readonly minZ: number; readonly maxZ: number;
  constructor(pts: [number, number][], step = 1.2) {
    const curve = new THREE.CatmullRomCurve3(pts.map(([x, z]) => new THREE.Vector3(x, 0, z)), false, "centripetal");
    const n = Math.max(4, Math.ceil(curve.getLength() / step));
    const sp = curve.getSpacedPoints(n);
    this.px = new Float32Array(sp.map((p) => p.x));
    this.pz = new Float32Array(sp.map((p) => p.z));
    this.len = new Float32Array(sp.length);
    for (let i = 1; i < sp.length; i++) this.len[i] = this.len[i - 1] + Math.hypot(sp[i].x - sp[i - 1].x, sp[i].z - sp[i - 1].z);
    this.total = this.len[sp.length - 1];
    this.minX = Math.min(...this.px); this.maxX = Math.max(...this.px);
    this.minZ = Math.min(...this.pz); this.maxZ = Math.max(...this.pz);
  }
  /** Distance to the track; `out.s` gets the arc fraction 0..1 of the closest point. */
  dist(x: number, z: number, out?: { s: number }, pad = 1e9): number {
    if (x < this.minX - pad || x > this.maxX + pad || z < this.minZ - pad || z > this.maxZ + pad) return 1e9;
    let best = 1e18, bs = 0;
    const { px, pz, len } = this;
    for (let i = 0; i < px.length - 1; i++) {
      const ax = px[i], az = pz[i], dx = px[i + 1] - ax, dz = pz[i + 1] - az;
      const l2 = dx * dx + dz * dz || 1e-9;
      let t = ((x - ax) * dx + (z - az) * dz) / l2;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const ex = ax + dx * t - x, ez = az + dz * t - z;
      const d2 = ex * ex + ez * ez;
      if (d2 < best) { best = d2; bs = len[i] + (len[i + 1] - len[i]) * t; }
    }
    if (out) out.s = bs / this.total;
    return Math.sqrt(best);
  }
  /** Point at arc fraction s. */
  at(s: number, out = new THREE.Vector2()): THREE.Vector2 {
    const target = s * this.total;
    let i = 0;
    while (i < this.len.length - 2 && this.len[i + 1] < target) i++;
    const t = (target - this.len[i]) / Math.max(1e-6, this.len[i + 1] - this.len[i]);
    return out.set(this.px[i] + (this.px[i + 1] - this.px[i]) * t, this.pz[i] + (this.pz[i + 1] - this.pz[i]) * t);
  }
}

// The east arm: a winding rock spine from the meadow's north-east up to the arena
export const ARM = new Track([[13, -6], [20, -13], [28, -21], [31.5, -31], [28.5, -41], [20, -48], [11, -51], [6, -51]], 0.8);
export const ROOT_TREE_S = [0.34, 0.56, 0.77];
const ARM_START_H = 0.9;

// Walking paths (dirt): jetty → camp → meadow → ridge → bridge, with branches to the glide cliff and the east arm
export const PATHS: Track[] = [
  new Track([[0, 51], [1, 44], [5, 37], [8, 33.5], [6, 25], [0, 17], [-4, 9], [-2, 0], [1, -7], [3, -14], [4, -21]]),
  new Track([[0, -6], [-6, -11], [-11, -15], [-15, -18], [-18, -21.5]]),
  new Track([[1, -4], [7, -5], [13, -6], [20, -13]]),
  new Track([[-13, -44], [-8, -47.5], [-2, -49.5], [2, -50]]),
  new Track([[2, -50], [1, -55], [0, -58.5], [-1, -61]]),
  new Track([[1, 44], [-6, 41], [-14, 36]]),
];

const gauss = (dx: number, dz: number, r: number) => Math.exp(-(dx * dx + dz * dz) / (2 * r * r));
const hyp = Math.hypot;

export function sdMain(x: number, z: number): number {
  const dx = x - MAIN.x, dz = z - MAIN.z;
  const d = hyp(dx, dz) || 1e-6;
  const c = dx / d, s = dz / d;
  const r = MAIN.r * (1 + 0.07 * fbm(c * 1.4 + 3.1, s * 1.4 + 1.7, 7, 3) + 0.025 * fbm(c * 5 + 9, s * 5, 8, 2));
  const cut = z - (CHASM_Z + 0.9 * fbm(x * 0.07, 3.3, 9, 2));
  return Math.min(r - d, cut);
}

export function sdSummit(x: number, z: number): number {
  const dx = x - SUMMIT.x, dz = z - SUMMIT.z;
  const d = hyp(dx, dz) || 1e-6;
  const r = SUMMIT.r * (1 + 0.08 * fbm((dx / d) * 1.6 + 5, (dz / d) * 1.6, 17, 3));
  const ledge = LEDGE.r * (1 + 0.1 * fbm(x * 0.2, z * 0.2, 18, 2)) - hyp(x - LEDGE.x, z - LEDGE.z);
  return Math.max(r - d, ledge);
}

const armQ = { s: 0 };
export function armWidth(s: number): number {
  let w = 2.9 + 2.2 * smooth(0.12, 0.0, s);
  for (const k of ROOT_TREE_S) w += 2.6 * Math.exp(-((s - k) ** 2) / (2 * 0.035 ** 2));
  return w;
}
/** Signed distance to the arm; also leaves the arc fraction in armQ.s. */
export function sdArm(x: number, z: number): number {
  const d = ARM.dist(x, z, armQ, 10);
  if (d > 1e8) return -1e3;
  return armWidth(armQ.s) * (1 + 0.12 * fbm(x * 0.25, z * 0.25, 19, 2)) - d;
}

export function pathDist(x: number, z: number): number {
  let d = 1e9;
  for (const p of PATHS) d = Math.min(d, p.dist(x, z, undefined, 4));
  // the arm's ridge path
  d = Math.min(d, ARM.dist(x, z, undefined, 4) + 0.2);
  return d;
}

function pad(h: number, x: number, z: number, cx: number, cz: number, r0: number, r1: number, target: number) {
  return h + (target - h) * (1 - smooth(r0, r1, hyp(x - cx, z - cz)));
}

export function mainH(x: number, z: number): number {
  const meadow = 0.75 * fbm(x * 0.026 + 3, z * 0.026, 11, 3) + 0.2 * fbm(x * 0.11, z * 0.11, 12, 2) + 0.35;
  const ramp = smooth(4, -21, z);
  const xm = 1 - smooth(6, 22, x);
  let h = meadow * (1 - ramp * 0.5) + ramp * RIDGE_H * xm;
  h += ramp * xm * 1.1 * fbm(x * 0.08 + 7, z * 0.08, 13, 3);
  h += (SPUR_H - RIDGE_H) * gauss(x - GLIDE_C.x, z - GLIDE_C.z - 1.5, 6.5) * smooth(-6, -16, z);
  h = pad(h, x, z, BRIDGE.x, BRIDGE.z0 - 1, 2.5, 5.5, RIDGE_H);
  h = pad(h, x, z, GLIDE_C.x, GLIDE_C.z, 2.5, 5.5, SPUR_H);
  h = pad(h, x, z, CAMP_C.x, CAMP_C.z, 3.5, 8, 0.45);
  // a gentle hollow towards the south rim so the jetty sits low
  h -= 0.5 * smooth(30, 50, z);
  return h;
}

/** Raised rock under the Waystone: steep sides, a ramp down towards the arena. */
export function plinthRise(x: number, z: number): number {
  const dx = x - PLINTH_C.x, dz = z - PLINTH_C.z;
  const d = hyp(dx, dz);
  const wob = 0.5 * fbm(x * 0.4, z * 0.4, 24, 2);
  const cliff = 1 - smooth(4.2 + wob, 5.6 + wob, d);
  const ax = ARENA_C.x - PLINTH_C.x, az = ARENA_C.z - PLINTH_C.z, al = hyp(ax, az);
  const t = (dx * ax + dz * az) / al, lat = Math.abs(dx * az - dz * ax) / al;
  const ramp = t > 0 ? (1 - smooth(4.5, 10.5, t)) * (1 - smooth(1.5, 2.4, lat)) : 0;
  return PLINTH_RISE * Math.max(cliff, ramp);
}

export function summitH(x: number, z: number): number {
  const dA = hyp(x - ARENA_C.x, z - ARENA_C.z);
  const flat = 1 - smooth(7.5, 11, dA);
  let h = ARENA_H + (1 - flat) * 0.7 * fbm(x * 0.09, z * 0.09, 21, 3);
  h = h + (LEDGE_H - h) * (1 - smooth(3, 9.5, hyp(x - LEDGE.x, z - LEDGE.z)));
  h += plinthRise(x, z);
  // craggy north rim behind the stone
  const dS = hyp(x - SUMMIT.x, z - SUMMIT.z);
  h += 4 * smooth(9, 16, dS) * smooth(-55, -66, z) * (0.6 + 0.6 * fbm(x * 0.15, z * 0.15, 22, 2));
  return h;
}

export function armH(s: number, x: number, z: number): number {
  return ARM_START_H + (ARENA_H - ARM_START_H) * smooth(0.05, 0.96, s) + 0.35 * fbm(x * 0.12, z * 0.12, 23, 2) * Math.sin(Math.PI * s);
}

export interface LandSample { sd: number; h: number; sdM: number; sdS: number; sdA: number; s: number }
const LS: LandSample = { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 };

/** Shape and height of the land at x,z (h is meaningful slightly outside the edge too, for the cliff skirt). */
export function land(x: number, z: number, out: LandSample = LS): LandSample {
  const sM = sdMain(x, z), sS = sdSummit(x, z), sA = sdArm(x, z);
  const s = armQ.s;
  const sd = Math.max(sM, sS, sA);
  let h = mainH(x, z);
  if (sA > -3) {
    const hA = armH(s, x, z);
    h += (Math.max(h, hA) - h) * smooth(-2.5, 1.2, sA);
    if (sM < 0) h += (hA - h) * smooth(1, -1.5, sM);
  }
  if (sS > -4) h += (summitH(x, z) - h) * smooth(-2, 1.5, sS);
  // worn paths sit a touch lower
  h -= 0.07 * (1 - smooth(0.6, 1.8, pathDist(x, z)));
  // rounded lip
  const k = 1 - smooth(0, 2.2, sd);
  h -= 1.0 * k * k;
  out.sd = sd; out.h = h; out.sdM = sM; out.sdS = sS; out.sdA = sA; out.s = s;
  return out;
}

export function bridgeDeckY(u: number): number {
  const y0 = landY(BRIDGE.x, BRIDGE.z0), y1 = landY(BRIDGE.x, BRIDGE.z1);
  return y0 + (y1 - y0) * u - BRIDGE.sag * Math.sin(Math.PI * u);
}
function landY(x: number, z: number) {
  return land(x, z, { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 }).h;
}
let JETTY_Y = 0;
export const jettyY = () => JETTY_Y;

const LQ: LandSample = { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 };
let bridgeY0 = 0, bridgeY1 = 0;
export function initLayout() {
  JETTY_Y = landY(JETTY.x, JETTY.z0) + 0.05;
  bridgeY0 = landY(BRIDGE.x, BRIDGE.z0);
  bridgeY1 = landY(BRIDGE.x, BRIDGE.z1);
}

export function heightAt(x: number, z: number): number | null {
  // rope bridge deck
  if (Math.abs(x - BRIDGE.x) < BRIDGE.half && z < BRIDGE.z0 && z > BRIDGE.z1) {
    const u = (BRIDGE.z0 - z) / (BRIDGE.z0 - BRIDGE.z1);
    return bridgeY0 + (bridgeY1 - bridgeY0) * u - BRIDGE.sag * Math.sin(Math.PI * u);
  }
  // jetty deck
  if (Math.abs(x - JETTY.x) < JETTY.half && z > JETTY.z0 - 1 && z < JETTY.z1) {
    const l = land(x, z, LQ);
    return l.sd > 0 ? Math.max(l.h, JETTY_Y) : JETTY_Y;
  }
  const l = land(x, z, LQ);
  return l.sd > 0 ? l.h : null;
}

export const BOUNDS = { minX: -48, maxX: 48, minZ: -76, maxZ: 57 };
