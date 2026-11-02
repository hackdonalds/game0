import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { clamp01, fbm, hashStr, mulberry32, smooth } from "./noise";

export interface IsleDef {
  id: string;
  name: string;
  x: number;
  z: number;
  y: number;
  radius: number;
  biome: string;
  people: string;
  town: boolean;
  shrine: boolean;
  ancientTree: boolean;
}

/** Analytic shape of one isle in world space (already recentred). heightAt and the mesh share it. */
export class IsleShape {
  readonly cx: number;
  readonly cz: number;
  readonly top: number;
  readonly radius: number;
  readonly seed: number;
  readonly hills: number;
  readonly lipDrop = 1.3;
  readonly depth: number;
  readonly tipX: number;
  readonly tipZ: number;
  private readonly maxR2: number;
  private readonly o1: number;
  private readonly o2: number;

  constructor(readonly def: IsleDef, worldSeed: number, originX: number, originZ: number) {
    this.cx = def.x - originX;
    this.cz = def.z - originZ;
    this.top = def.y;
    this.radius = def.radius;
    this.seed = (hashStr(def.id) ^ Math.imul(worldSeed, 2654435761)) >>> 0 & 0xffff;
    const rng = mulberry32(this.seed);
    this.o1 = rng() * 50;
    this.o2 = rng() * 50;
    this.hills = Math.min(3.2, def.radius * 0.045);
    this.depth = def.radius * (0.95 + rng() * 0.35);
    this.tipX = (rng() - 0.5) * def.radius * 0.35;
    this.tipZ = (rng() - 0.5) * def.radius * 0.35;
    this.maxR2 = (def.radius * 1.2) ** 2;
  }

  /** Edge radius for a direction (cos, sin): irregular, never a perfect circle. */
  edgeR(c: number, s: number): number {
    return this.radius * (1 + 0.11 * fbm(c * 1.3 + this.o1, s * 1.3 + this.o2, this.seed, 3) + 0.035 * fbm(c * 4.5 + this.o2, s * 4.5, this.seed + 7, 2));
  }

  /** Top surface height at isle-local lx, lz with normalised radius d. */
  surface(lx: number, lz: number, d: number): number {
    const flat = smooth(0.18, 0.72, d);
    let h = this.top + this.hills * fbm(lx * 0.022 + this.o1, lz * 0.022, this.seed + 11, 4) * flat
      + 0.28 * fbm(lx * 0.11, lz * 0.11 + this.o2, this.seed + 13, 2);
    if (d > 0.84) {
      const k = (d - 0.84) / 0.16;
      h -= this.lipDrop * k * k;
    }
    return h;
  }

  /** Normalised radius (0 centre, 1 edge) of a world point. */
  dAt(x: number, z: number): number {
    const lx = x - this.cx, lz = z - this.cz;
    const r = Math.sqrt(lx * lx + lz * lz);
    if (r < 1e-6) return 0;
    return r / this.edgeR(lx / r, lz / r);
  }

  heightAt(x: number, z: number): number | null {
    const lx = x - this.cx, lz = z - this.cz;
    const r2 = lx * lx + lz * lz;
    if (r2 > this.maxR2) return null;
    const r = Math.sqrt(r2);
    const d = r < 1e-6 ? 0 : r / this.edgeR(lx / r, lz / r);
    if (d > 1) return null;
    return this.surface(lx, lz, d);
  }

  /** Point on the cliff/underside for direction (c, s) at depth fraction u (0 lip, 1 tip). */
  underPos(c: number, s: number, R: number, edgeY: number, u: number, out: THREE.Vector3): THREE.Vector3 {
    let f: number;
    if (u < 0.1) f = 1 - 0.05 * (u / 0.1);
    else f = 0.95 * Math.pow(1 - (u - 0.1) / 0.9, 0.62);
    f *= 1 + 0.17 * fbm(c * 2.2 + u * 3 + this.o1, s * 2.2 - u * 2, this.seed + 21, 3) * smooth(0.04, 0.3, u);
    const t = Math.pow(clamp01((u - 0.1) / 0.9), 1.5);
    const meanEdge = this.top - this.lipDrop;
    const y = edgeY + (meanEdge - edgeY) * u - this.depth * u;
    return out.set(this.cx + this.tipX * t + c * R * f, y, this.cz + this.tipZ * t + s * R * f);
  }
}

export interface IslePalette { base: number; light: number; dry: number; dark: number }
export const BIOME_PALETTE: Record<string, IslePalette> = {
  roothold: { base: 0x4f7a3a, light: 0x6f9a48, dry: 0x9a9a56, dark: 0x12261f },
  meadow: { base: 0x5f8e40, light: 0x8db45a, dry: 0xd0b866, dark: 0x2a4a2a },
  forest: { base: 0x3e6a34, light: 0x5c8a3e, dry: 0x8f8a4a, dark: 0x12261f },
  crag: { base: 0x8c8a78, light: 0xb4ae98, dry: 0x6f7a52, dark: 0x4a4a44 },
  garden: { base: 0x6a9a42, light: 0x9cc05e, dry: 0xe3b45a, dark: 0x2f5a30 },
  lagoon: { base: 0x4f8a5e, light: 0x6fb08a, dry: 0x2fc4b2, dark: 0x0e5a57 },
  ruin: { base: 0x9a967f, light: 0xd8cfb6, dry: 0x7f8a5a, dark: 0x5a5548 },
};

export interface BuildOpts {
  rings: number;
  segs: number;
  under: number;
  roots: number;
  /** Distance to the nearest walking path (world XZ), for painting dirt paths. */
  pathDist?: (x: number, z: number) => number;
}

const tmpA = new THREE.Color(), tmpB = new THREE.Color();
const COL = {
  earth: new THREE.Color(0x7a5534),
  earthDark: new THREE.Color(0x4a3524),
  stone: new THREE.Color(0xd6cbb0),
  stoneDark: new THREE.Color(0x5e574c),
  path: new THREE.Color(0x8c7c5c),
  lip: new THREE.Color(0x8a7a46),
  root: new THREE.Color(0x4a3424),
  moss: new THREE.Color(0x4f7a3a),
};

/** Build the merged isle mesh geometry (top, cliff band, underside, hanging roots) in world space. */
export function buildIsleGeometry(shape: IsleShape, opts: BuildOpts): THREE.BufferGeometry {
  const pal = BIOME_PALETTE[shape.def.biome] ?? BIOME_PALETTE.roothold;
  const cBase = new THREE.Color(pal.base), cLight = new THREE.Color(pal.light), cDry = new THREE.Color(pal.dry), cDark = new THREE.Color(pal.dark);
  const { rings, segs, under } = opts;
  const pos: number[] = [];
  const col: number[] = [];
  const idx: number[] = [];
  const cosT = new Float32Array(segs), sinT = new Float32Array(segs), edgeRs = new Float32Array(segs), edgeYs = new Float32Array(segs);
  for (let j = 0; j < segs; j++) {
    const t = (j / segs) * Math.PI * 2;
    cosT[j] = Math.cos(t);
    sinT[j] = Math.sin(t);
    edgeRs[j] = shape.edgeR(cosT[j], sinT[j]);
    edgeYs[j] = shape.surface(cosT[j] * edgeRs[j], sinT[j] * edgeRs[j], 1);
  }
  const s = shape.seed;

  const topColor = (x: number, z: number, d: number) => {
    const n1 = fbm(x * 0.045, z * 0.045, s + 31, 3);
    const n2 = fbm(x * 0.13, z * 0.13, s + 37, 2);
    tmpA.copy(cBase).lerp(cLight, clamp01(0.45 + n1 * 0.9));
    tmpA.lerp(cDry, smooth(0.25, 0.75, n2) * 0.22);
    tmpA.lerp(cDark, smooth(0.25, 0.6, -n1) * 0.35);
    if (d > 0.9) tmpA.lerp(COL.lip, smooth(0.9, 1, d) * 0.35);
    if (opts.pathDist) {
      const pd = opts.pathDist(x, z);
      if (pd < 1.6) tmpA.lerp(COL.path, (1 - smooth(0.4, 1.6, pd + n2 * 0.35)) * 0.6);
    }
    col.push(tmpA.r, tmpA.g, tmpA.b);
  };

  // Centre vertex
  const cy = shape.surface(0, 0, 0);
  pos.push(shape.cx, cy, shape.cz);
  topColor(shape.cx, shape.cz, 0);
  // Top rings
  for (let i = 1; i <= rings; i++) {
    const d = i / rings;
    for (let j = 0; j < segs; j++) {
      const lx = cosT[j] * edgeRs[j] * d, lz = sinT[j] * edgeRs[j] * d;
      pos.push(shape.cx + lx, shape.surface(lx, lz, d), shape.cz + lz);
      topColor(shape.cx + lx, shape.cz + lz, d);
    }
  }
  // Underside rings (k = 1..under-1), then the tip
  const v = new THREE.Vector3();
  for (let k = 1; k < under; k++) {
    const u = Math.pow(k / under, 1.35);
    for (let j = 0; j < segs; j++) {
      shape.underPos(cosT[j], sinT[j], edgeRs[j], edgeYs[j], u, v);
      pos.push(v.x, v.y, v.z);
      const n = fbm(v.x * 0.08 + v.y * 0.05, v.z * 0.08 - v.y * 0.05, s + 41, 3);
      if (u < 0.12) {
        tmpA.copy(COL.earth).lerp(COL.earthDark, clamp01(u / 0.12 * 0.7 + n * 0.4));
        tmpA.lerp(COL.moss, smooth(0.1, 0.5, n) * (1 - u / 0.12) * 0.6);
      } else {
        const strata = 0.9 + 0.1 * Math.sin(v.y * 1.4 + n * 4);
        tmpB.copy(COL.stone).lerp(COL.stoneDark, smooth(0.15, 1, u) * 0.85 + n * 0.12);
        tmpB.multiplyScalar(strata);
        tmpA.copy(COL.earthDark).lerp(tmpB, smooth(0.1, 0.24, u));
        if (u < 0.35) tmpA.lerp(COL.moss, smooth(0.3, 0.6, n) * (1 - u / 0.35) * 0.5);
      }
      col.push(tmpA.r, tmpA.g, tmpA.b);
    }
  }
  shape.underPos(1, 0, 0, shape.top - shape.lipDrop, 1, v);
  const tip = pos.length / 3;
  pos.push(v.x, v.y, v.z);
  col.push(COL.stoneDark.r * 0.8, COL.stoneDark.g * 0.8, COL.stoneDark.b * 0.8);

  // Indices: centre fan, ring strips, tip fan (one continuous sheet, consistent winding)
  const ringStart = (r: number) => 1 + (r - 1) * segs; // r = 1..rings+under-1
  for (let j = 0; j < segs; j++) idx.push(0, ringStart(1) + ((j + 1) % segs), ringStart(1) + j);
  const totalRings = rings + under - 1;
  for (let r = 1; r < totalRings; r++) {
    const a0 = ringStart(r), b0 = ringStart(r + 1);
    for (let j = 0; j < segs; j++) {
      const j1 = (j + 1) % segs;
      const a = a0 + j, b = a0 + j1, c = b0 + j, d = b0 + j1;
      idx.push(a, b, c, b, d, c);
    }
  }
  const last = ringStart(totalRings);
  for (let j = 0; j < segs; j++) idx.push(last + j, last + ((j + 1) % segs), tip);

  let geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();

  // Hanging root strands
  if (opts.roots > 0) {
    const rng = mulberry32(s + 99);
    const parts: THREE.BufferGeometry[] = [geo];
    const p = new THREE.Vector3();
    for (let i = 0; i < opts.roots; i++) {
      const j = Math.floor(rng() * segs);
      const u = 0.06 + rng() * 0.4;
      shape.underPos(cosT[j], sinT[j], edgeRs[j], edgeYs[j], u, p);
      p.x -= cosT[j] * 0.4;
      p.z -= sinT[j] * 0.4;
      const len = 5 + rng() * (shape.radius * 0.28);
      const pts: THREE.Vector3[] = [];
      for (let q = 0; q <= 5; q++) {
        const f = q / 5;
        pts.push(new THREE.Vector3(
          p.x + cosT[j] * f * 1.5 + Math.sin(f * 5 + i) * 0.8 * f,
          p.y - len * f,
          p.z + sinT[j] * f * 1.5 + Math.cos(f * 4 + i * 1.7) * 0.8 * f,
        ));
      }
      const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 14, 0.12 + rng() * 0.22, 5, false);
      tube.deleteAttribute("uv");
      const tp = tube.attributes.position as THREE.BufferAttribute;
      const cols = new Float32Array(tp.count * 3);
      const shade = 0.8 + rng() * 0.4;
      for (let q = 0; q < tp.count; q++) {
        const f = clamp01((p.y - tp.getY(q)) / len);
        cols[q * 3] = COL.root.r * shade * (1 + f * 0.3);
        cols[q * 3 + 1] = COL.root.g * shade * (1 + f * 0.25);
        cols[q * 3 + 2] = COL.root.b * shade;
      }
      tube.setAttribute("color", new THREE.BufferAttribute(cols, 3));
      parts.push(tube);
    }
    const merged = mergeGeometries(parts, false);
    if (merged) {
      geo.dispose();
      geo = merged;
    }
  }
  geo.computeBoundingSphere();
  return geo;
}
