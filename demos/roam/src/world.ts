import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import world from "../../../worlds/first-shard.world.json";
import { buildIsleGeometry, IsleShape, type IsleDef } from "./world/isle";
import { kitMaterial, painterly, windTime } from "./world/materials";
import { mulberry32 } from "./world/noise";
import { createSky } from "./world/sky";

export interface World {
  /** Ground height at x,z (top of terrain or bridge deck), or null when there is no ground (the player falls). */
  heightAt(x: number, z: number): number | null;
  /** Solid obstacles as circles on XZ for simple collision: trees, rocks, buildings. */
  colliders: { x: number; z: number; r: number; top: number }[];
  spawn: THREE.Vector3;
  sun: THREE.DirectionalLight; // shadow-casting; update() moves its shadow box to follow `focus`
  update(dt: number, elapsed: number, focus: THREE.Vector3): void;
}

interface KitEntry {
  id: string;
  file: string;
  category?: string;
  biomes?: string[];
  radius?: number;
  height?: number;
  minScale?: number;
  maxScale?: number;
  collide?: boolean;
}
interface KitPart { geometry: THREE.BufferGeometry; material: THREE.Material | THREE.Material[] }
type Collider = World["colliders"][number];

const WALKABLE = ["isle_elderroot", "isle_rootmother", "isle_deephold", "isle_hollowgrain"];
const BRIDGE_HALF = 1.2;
const SUN_DIR = new THREE.Vector3(-0.5, 0.52, 0.68).normalize();
const SHADOW_HALF = 30;
const KIT = `${import.meta.env.BASE_URL}models/kit/`;

// Elderroot-local layout (Elderroot centre is the origin)
const SPAWN_XZ = [0, 4] as const;
const VILLAGE_XZ = [-6, 36] as const;
const SHRINE_XZ = [-11, -9] as const;
const HERO_TREE_XZ = [-22, -22] as const;

interface Bridge {
  ax: number; az: number; ay: number;
  bx: number; bz: number; by: number;
  dx: number; dz: number; len: number; sag: number;
}
const deckY = (b: Bridge, t: number) => b.ay + (b.by - b.ay) * t - b.sag * Math.sin(Math.PI * t);

/**
 * Compressed kit models store positions and normals as normalized integers with the scale on the node
 * (KHR_mesh_quantization). Baking the node transform into those integer arrays would clamp them to ±1, so
 * expand every attribute to floats first.
 */
function dequantize(g: THREE.BufferGeometry) {
  for (const [name, attr] of Object.entries(g.attributes)) {
    const a = attr as THREE.BufferAttribute;
    if (a.array instanceof Float32Array && !a.normalized && !(a as unknown as THREE.InterleavedBufferAttribute).isInterleavedBufferAttribute) continue;
    const out = new Float32Array(a.count * a.itemSize);
    for (let i = 0; i < a.count; i++) for (let k = 0; k < a.itemSize; k++) out[i * a.itemSize + k] = a.getComponent(i, k);
    g.setAttribute(name, new THREE.BufferAttribute(out, a.itemSize));
  }
  return g;
}

async function loadCatalog(name: string): Promise<KitEntry[]> {
  try {
    const r = await fetch(`${KIT}${name}.json`);
    if (!r.ok) return [];
    const j: unknown = await r.json();
    return Array.isArray(j) ? (j as KitEntry[]).filter((e) => e && typeof e.id === "string" && typeof e.file === "string") : [];
  } catch {
    return [];
  }
}

export async function createWorld(scene: THREE.Scene, renderer: THREE.WebGLRenderer): Promise<World> {
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const sky = createSky(scene, SUN_DIR);
  scene.add(new THREE.HemisphereLight(0xffe4b8, 0x2a7a70, 1.05));
  const sun = new THREE.DirectionalLight(0xffd79a, 3.1);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -SHADOW_HALF, right: SHADOW_HALF, top: SHADOW_HALF, bottom: -SHADOW_HALF, near: 1, far: 260 });
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.04;
  sun.shadow.radius = 3;
  scene.add(sun, sun.target);

  // ---- Isles -------------------------------------------------------------------------------
  const defs = world.isles as unknown as IsleDef[];
  const elder = defs.find((d) => d.id === "isle_elderroot")!;
  const ox = elder.x, oz = elder.z;
  const shapes = new Map<string, IsleShape>();
  for (const d of defs) shapes.set(d.id, new IsleShape(d, world.seed, ox, oz));
  const walk = WALKABLE.map((id) => shapes.get(id)!).filter(Boolean);

  // ---- Bridges (geometry of the deck curve) ------------------------------------------------
  const bridges: Bridge[] = [];
  for (const br of world.bridges) {
    if (!WALKABLE.includes(br.a) || !WALKABLE.includes(br.b)) continue;
    const A = shapes.get(br.a)!, B = shapes.get(br.b)!;
    let dx = B.cx - A.cx, dz = B.cz - A.cz;
    const dl = Math.hypot(dx, dz);
    dx /= dl; dz /= dl;
    const ra = A.edgeR(dx, dz) * 0.9, rb = B.edgeR(-dx, -dz) * 0.9;
    const ax = A.cx + dx * ra, az = A.cz + dz * ra, bx = B.cx - dx * rb, bz = B.cz - dz * rb;
    const ay = A.heightAt(ax, az) ?? A.top, by = B.heightAt(bx, bz) ?? B.top;
    const len = Math.hypot(bx - ax, bz - az);
    bridges.push({ ax, az, ay, bx, bz, by, dx, dz, len, sag: Math.min(2.5, len * 0.035) });
  }

  const heightAt = (x: number, z: number): number | null => {
    let best: number | null = null;
    for (let i = 0; i < walk.length; i++) {
      const h = walk[i].heightAt(x, z);
      if (h !== null && (best === null || h > best)) best = h;
    }
    for (let i = 0; i < bridges.length; i++) {
      const b = bridges[i];
      const px = x - b.ax, pz = z - b.az;
      const along = px * b.dx + pz * b.dz;
      if (along < 0 || along > b.len) continue;
      const side = Math.abs(px * -b.dz + pz * b.dx);
      if (side > BRIDGE_HALF) continue;
      const h = deckY(b, along / b.len);
      if (best === null || h > best) best = h;
    }
    return best;
  };

  // Walking paths: spawn to the village, shrine and each bridge; other isles centre to bridge.
  const paths: [number, number, number, number][] = [
    [SPAWN_XZ[0], SPAWN_XZ[1], VILLAGE_XZ[0], VILLAGE_XZ[1]],
    [SPAWN_XZ[0], SPAWN_XZ[1], SHRINE_XZ[0], SHRINE_XZ[1]],
  ];
  for (const b of bridges) {
    const near = (x: number, z: number) => walk.find((s) => s.dAt(x, z) < 1.05)!;
    for (const [px, pz] of [[b.ax, b.az], [b.bx, b.bz]] as const) {
      const s = near(px, pz);
      if (!s) continue;
      const fx = s.def.id === "isle_elderroot" ? SPAWN_XZ[0] : s.cx, fz = s.def.id === "isle_elderroot" ? SPAWN_XZ[1] : s.cz;
      paths.push([fx, fz, px, pz]);
    }
  }
  const pathDist = (x: number, z: number) => {
    let m = Infinity;
    for (const [x1, z1, x2, z2] of paths) {
      const vx = x2 - x1, vz = z2 - z1;
      const t = Math.max(0, Math.min(1, ((x - x1) * vx + (z - z1) * vz) / (vx * vx + vz * vz)));
      const d = Math.hypot(x - x1 - vx * t, z - z1 - vz * t);
      if (d < m) m = d;
    }
    return m;
  };

  // ---- Terrain meshes ----------------------------------------------------------------------
  const terrainMat = painterly("kit", true);
  for (const s of walk) {
    const geo = buildIsleGeometry(s, {
      rings: Math.ceil(s.radius / 1.0),
      segs: Math.ceil((Math.PI * 2 * s.radius) / 1.1),
      under: 30,
      roots: Math.round(s.radius * 0.35),
      pathDist,
    });
    const mesh = new THREE.Mesh(geo, terrainMat);
    mesh.receiveShadow = true;
    mesh.castShadow = true;
    mesh.name = s.def.name;
    scene.add(mesh);
  }
  const far: THREE.BufferGeometry[] = [];
  for (const d of defs) {
    if (WALKABLE.includes(d.id)) continue;
    far.push(buildIsleGeometry(shapes.get(d.id)!, { rings: 10, segs: 40, under: 10, roots: 0 }));
  }
  const farGeo = far.length ? mergeGeometries(far, false) : null;
  if (farGeo) {
    const mesh = new THREE.Mesh(farGeo, terrainMat);
    mesh.name = "distant-isles";
    scene.add(mesh);
  }

  // ---- Kit catalogs ------------------------------------------------------------------------
  const [nature, settlement, rootwarden] = await Promise.all([loadCatalog("nature"), loadCatalog("settlement"), loadCatalog("rootwarden")]);
  const catalog = [...nature, ...settlement, ...rootwarden];
  const byId = new Map(catalog.map((e) => [e.id, e]));
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const assetCache = new Map<string, Promise<KitPart[] | null>>();
  const loadAsset = (e: KitEntry) => {
    let p = assetCache.get(e.id);
    if (!p) {
      p = loader.loadAsync(KIT + e.file).then((gltf) => {
        const parts: KitPart[] = [];
        gltf.scene.updateMatrixWorld(true);
        gltf.scene.traverse((o) => {
          const m = o as THREE.Mesh;
          if (!m.isMesh) return;
          const geometry = dequantize(m.geometry.clone()).applyMatrix4(m.matrixWorld);
          const hasColors = !!geometry.attributes.color;
          const mats = Array.isArray(m.material) ? m.material : [m.material];
          const conv = mats.map((src) => kitMaterial(src, hasColors));
          parts.push({ geometry, material: conv.length === 1 ? conv[0] : conv });
        });
        return parts;
      }).catch((err) => {
        console.warn(`[world] kit asset ${e.id} failed to load`, err);
        return null;
      });
      assetCache.set(e.id, p);
    }
    return p;
  };

  const roothold = (list: KitEntry[]) => {
    const r = list.filter((e) => !e.biomes || e.biomes.length === 0 || e.biomes.includes("roothold"));
    return r.length ? r : list;
  };
  const match = (...keys: string[]) => (e: KitEntry) => keys.some((k) => e.id.includes(k) || (e.category ?? "").includes(k));
  const not = (f: (e: KitEntry) => boolean) => (e: KitEntry) => !f(e);
  const isBridge = match("bridge");
  const pick = {
    trees: roothold(catalog.filter((e) => match("oak", "pine", "tree")(e) && !e.id.includes("ancient") && !isBridge(e))),
    rocks: roothold(catalog.filter((e) => match("rock", "boulder")(e) && !isBridge(e))),
    bushes: roothold(catalog.filter(match("bush", "shrub"))),
    ferns: roothold(catalog.filter(match("fern"))),
    grass: roothold(catalog.filter((e) => match("grass", "tuft")(e) && !match("mushroom")(e))),
    mushrooms: roothold(catalog.filter(match("mushroom"))),
    flowers: roothold(catalog.filter(match("flower"))),
    // Rootwarden architecture replaces the placeholder settlement huts and props when it is available
    huts: rootwarden.some((e) => e.category === "building")
      ? rootwarden.filter((e) => e.category === "building")
      : settlement.filter((e) => e.id.startsWith("settle-hut")),
    props: rootwarden.some((e) => e.category === "prop")
      ? rootwarden.filter((e) => e.category === "prop")
      : settlement.filter((e) => match("lantern", "barrel", "crate", "fence", "well", "cart", "sign")(e) && not(isBridge)(e)),
    decor: rootwarden.filter((e) => e.category === "decor"),
  };
  const ancient = byId.get("nature-ancient-tree");
  const shrine = byId.get("settle-shrine");
  const plank = byId.get("settle-bridge-plank");
  const post = byId.get("settle-bridge-post");

  // ---- Placement ---------------------------------------------------------------------------
  const colliders: Collider[] = [];
  const colliderIds: string[] = [];
  /** Instances grouped by "isleIndex|assetId" so each isle's batch is frustum-culled on its own. */
  const batches = new Map<string, { entry: KitEntry; mats: THREE.Matrix4[]; shadow: boolean }>();
  const big: { x: number; z: number; r: number }[] = [];
  const q = new THREE.Quaternion(), sc = new THREE.Vector3(), pv = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);

  const place = (isle: number, e: KitEntry, x: number, z: number, yaw: number, scale: number, shadow: boolean, sink = 0) => {
    const h = heightAt(x, z);
    if (h === null) return false;
    const key = `${isle}|${e.id}`;
    let b = batches.get(key);
    if (!b) batches.set(key, (b = { entry: e, mats: [], shadow }));
    b.mats.push(new THREE.Matrix4().compose(pv.set(x, h - sink * scale, z), q.setFromAxisAngle(up, yaw), sc.setScalar(scale)));
    if (e.collide) {
      colliders.push({ x, z, r: (e.radius ?? 0.5) * scale, top: h + (e.height ?? 2) * scale });
      colliderIds.push(e.id);
    }
    return true;
  };
  const scaleOf = (e: KitEntry, rng: () => number) => {
    const a = e.minScale ?? 1, b = e.maxScale ?? a;
    return a + (b - a) * rng();
  };
  const choose = <T,>(list: T[], rng: () => number) => list[Math.floor(rng() * list.length)];
  const clearOf = (x: number, z: number, r: number) => {
    for (const o of big) if ((o.x - x) ** 2 + (o.z - z) ** 2 < (o.r + r) ** 2) return false;
    return true;
  };
  const nearSpawn = (x: number, z: number, r: number) => Math.hypot(x - SPAWN_XZ[0], z - SPAWN_XZ[1]) < r;
  const bridgeAt = (x: number, z: number, pad: number) => {
    for (const b of bridges) {
      const px = x - b.ax, pz = z - b.az;
      const along = px * b.dx + pz * b.dz;
      if (along > -pad && along < b.len + pad && Math.abs(px * -b.dz + pz * b.dx) < BRIDGE_HALF + pad) return true;
    }
    return false;
  };
  const slopeAt = (x: number, z: number) => {
    const h0 = heightAt(x, z), hx = heightAt(x + 0.7, z), hz = heightAt(x, z + 0.7);
    if (h0 === null || hx === null || hz === null) return 1;
    return Math.hypot(hx - h0, hz - h0) / 0.7;
  };

  const rng = mulberry32((world.seed * 7919) ^ 0x5eed);
  const elderIdx = walk.findIndex((s) => s.def.id === "isle_elderroot");

  // Hero pieces on Elderroot
  if (ancient) {
    const s = scaleOf(ancient, rng);
    if (place(elderIdx, ancient, HERO_TREE_XZ[0], HERO_TREE_XZ[1], rng() * Math.PI * 2, s, true, 0.1)) big.push({ x: HERO_TREE_XZ[0], z: HERO_TREE_XZ[1], r: (ancient.radius ?? 4) * s + 2 });
  }
  if (shrine) {
    const s = scaleOf(shrine, rng);
    const yaw = Math.atan2(SPAWN_XZ[0] - SHRINE_XZ[0], SPAWN_XZ[1] - SHRINE_XZ[1]);
    if (place(elderIdx, shrine, SHRINE_XZ[0], SHRINE_XZ[1], yaw, s, true)) big.push({ x: SHRINE_XZ[0], z: SHRINE_XZ[1], r: (shrine.radius ?? 2) * s + 1.5 });
  }
  // Village: 3-5 huts on a ring facing the square, props between them
  if (pick.huts.length) {
    const n = 3 + Math.floor(rng() * 3);
    const a0 = rng() * Math.PI * 2;
    for (let i = 0; i < n; i++) {
      const e = pick.huts[i % pick.huts.length];
      const s = scaleOf(e, rng);
      for (let tries = 0; tries < 8; tries++) {
        const a = a0 + (i / n) * Math.PI * 2 + (rng() - 0.5) * 0.5;
        const r = (e.radius ?? 3) * s;
        const rr = Math.max(10, r * 2) + rng() * 3;
        const x = VILLAGE_XZ[0] + Math.cos(a) * rr, z = VILLAGE_XZ[1] + Math.sin(a) * rr;
        if (pathDist(x, z) < r + 1.5 || !clearOf(x, z, r) || slopeAt(x, z) > 0.35) continue;
        const yaw = Math.atan2(VILLAGE_XZ[0] - x, VILLAGE_XZ[1] - z);
        if (place(elderIdx, e, x, z, yaw, s, true, 0.05)) { big.push({ x, z, r }); break; }
      }
    }
  }
  if (pick.props.length) {
    const wellish = pick.props.find((e) => e.id.includes("well"));
    if (wellish) {
      const s = scaleOf(wellish, rng);
      const x = VILLAGE_XZ[0] + 1.5, z = VILLAGE_XZ[1] + 2.5;
      if (place(elderIdx, wellish, x, z, rng() * 6.28, s, true)) big.push({ x, z, r: (wellish.radius ?? 1) * s + 0.5 });
    }
    const n = rootwarden.length ? 5 + Math.floor(rng() * 3) : 14 + Math.floor(rng() * 8);
    for (let i = 0; i < n; i++) {
      const e = choose(pick.props, rng);
      const s = scaleOf(e, rng);
      for (let tries = 0; tries < 10; tries++) {
        const a = rng() * Math.PI * 2, rr = 4 + rng() * 12;
        const x = VILLAGE_XZ[0] + Math.cos(a) * rr, z = VILLAGE_XZ[1] + Math.sin(a) * rr;
        const r = (e.radius ?? 0.6) * s;
        const isLantern = e.id.includes("lantern") || e.id.includes("sign");
        if ((!isLantern && pathDist(x, z) < r + 1.4) || !clearOf(x, z, r + 0.3)) continue;
        const yaw = e.id.includes("fence") ? a + Math.PI / 2 : rng() * Math.PI * 2;
        if (place(elderIdx, e, x, z, yaw, s, true)) { big.push({ x, z, r }); break; }
      }
    }
    // Grown roots arching out of the ground around the village edge
    for (let i = 0; i < 8 && pick.decor.length; i++) {
      const e = choose(pick.decor, rng);
      const s = scaleOf(e, rng);
      for (let tries = 0; tries < 10; tries++) {
        const a = rng() * Math.PI * 2, rr = 17 + rng() * 9;
        const x = VILLAGE_XZ[0] + Math.cos(a) * rr, z = VILLAGE_XZ[1] + Math.sin(a) * rr;
        const r = (e.radius ?? 1.5) * s;
        if (pathDist(x, z) < r + 1.4 || !clearOf(x, z, r + 0.5) || slopeAt(x, z) > 0.4) continue;
        if (place(elderIdx, e, x, z, rng() * Math.PI * 2, s, true, 0.15)) { big.push({ x, z, r }); break; }
      }
    }
    // Lanterns and signposts along the paths
    const lanterns = pick.props.filter((e) => e.id.includes("lantern") || e.id.includes("sign"));
    if (lanterns.length) {
      for (const [x1, z1, x2, z2] of paths) {
        const L = Math.hypot(x2 - x1, z2 - z1);
        const nx = -(z2 - z1) / L, nz = (x2 - x1) / L;
        for (let d = 9; d < L - 3; d += rootwarden.length ? 22 : 14) {
          const side = rng() < 0.5 ? -1 : 1;
          const x = x1 + ((x2 - x1) * d) / L + nx * 2.4 * side, z = z1 + ((z2 - z1) * d) / L + nz * 2.4 * side;
          const e = choose(lanterns, rng);
          if (clearOf(x, z, 0.5) && !bridgeAt(x, z, 0.5)) {
            const isle = walk.findIndex((s) => s.dAt(x, z) < 0.95);
            if (isle >= 0 && place(isle, e, x, z, rng() * 6.28, scaleOf(e, rng), true)) big.push({ x, z, r: 0.5 });
          }
        }
      }
    }
  }

  // Per-isle nature
  walk.forEach((s, isle) => {
    const area = Math.PI * s.radius * s.radius;
    const R = s.radius * 1.12;
    const rand = mulberry32(s.seed + 1234);
    const sample = (out: { x: number; z: number; d: number }) => {
      for (let t = 0; t < 30; t++) {
        const x = s.cx + (rand() * 2 - 1) * R, z = s.cz + (rand() * 2 - 1) * R;
        const d = s.dAt(x, z);
        if (d < 0.97) { out.x = x; out.z = z; out.d = d; return true; }
      }
      return false;
    };
    const pt = { x: 0, z: 0, d: 0 };
    const inVillage = (x: number, z: number, pad: number) => s === walk[elderIdx] && Math.hypot(x - VILLAGE_XZ[0], z - VILLAGE_XZ[1]) < 18 + pad;
    const blocked = (x: number, z: number, clear: number) => nearSpawn(x, z, 6) || pathDist(x, z) < clear || bridgeAt(x, z, clear);

    // Ancient trees on the other ancient-tree isles
    if (s.def.ancientTree && s.def.id !== "isle_elderroot" && ancient) {
      const a = rand() * Math.PI * 2;
      const x = s.cx + Math.cos(a) * s.radius * 0.25, z = s.cz + Math.sin(a) * s.radius * 0.25;
      const sc2 = scaleOf(ancient, rand) * 0.85;
      if (!blocked(x, z, 3) && place(isle, ancient, x, z, rand() * 6.28, sc2, true, 0.1)) big.push({ x, z, r: (ancient.radius ?? 4) * sc2 + 2 });
    }
    // Trees: 0.5 per 100 m²
    if (pick.trees.length) {
      const n = Math.round(area * 0.005);
      for (let i = 0, placed = 0; i < n * 6 && placed < n; i++) {
        if (!sample(pt) || pt.d > 0.86) continue;
        const e = choose(pick.trees, rand);
        const sc2 = scaleOf(e, rand);
        const r = (e.radius ?? 1) * sc2;
        if (blocked(pt.x, pt.z, 3.5 + r) || inVillage(pt.x, pt.z, r) || !clearOf(pt.x, pt.z, Math.max(r, 2.2) + 1.2)) continue;
        if (place(isle, e, pt.x, pt.z, rand() * 6.28, sc2, true, 0.15)) { big.push({ x: pt.x, z: pt.z, r: Math.max(r, 2.2) }); placed++; }
      }
    }
    // Rocks: favour slopes and the lip
    if (pick.rocks.length) {
      const n = Math.round(area * 0.0018 + s.radius * 0.5);
      for (let i = 0, placed = 0; i < n * 8 && placed < n; i++) {
        if (!sample(pt)) continue;
        const slope = slopeAt(pt.x, pt.z);
        if (pt.d < 0.78 && slope < 0.18 && rand() > 0.12) continue;
        const e = choose(pick.rocks, rand);
        const sc2 = scaleOf(e, rand);
        const r = (e.radius ?? 0.8) * sc2;
        if (blocked(pt.x, pt.z, 2 + r) || inVillage(pt.x, pt.z, r) || !clearOf(pt.x, pt.z, r + 0.4)) continue;
        if (place(isle, e, pt.x, pt.z, rand() * 6.28, sc2, true, 0.25)) { big.push({ x: pt.x, z: pt.z, r }); placed++; }
      }
    }
    // Ground cover: dense, no shadows cast, light clearance
    const cover: [KitEntry[], number, number][] = [
      [pick.bushes, 0.012, 1.8],
      [pick.ferns, 0.03, 1.4],
      [pick.grass, 0.28, 0.9],
      [pick.mushrooms, 0.008, 1.2],
      [pick.flowers, 0.04, 1.0],
    ];
    for (const [list, density, clear] of cover) {
      if (!list.length) continue;
      const n = Math.round(area * density);
      // Clumpy: seed clusters, then scatter around each
      for (let i = 0; i < n; ) {
        if (!sample(pt)) { i++; continue; }
        const cx = pt.x, cz = pt.z;
        const clump = 1 + Math.floor(rand() * 6);
        for (let k = 0; k < clump && i < n; k++, i++) {
          const x = cx + (rand() - 0.5) * 3, z = cz + (rand() - 0.5) * 3;
          if (s.dAt(x, z) > 0.97 || blocked(x, z, clear)) continue;
          let hit = false;
          for (const c of colliders) if ((c.x - x) ** 2 + (c.z - z) ** 2 < c.r * c.r) { hit = true; break; }
          if (hit) continue;
          const e = choose(list, rand);
          place(isle, e, x, z, rand() * 6.28, scaleOf(e, rand), list === pick.bushes, 0.03);
        }
      }
    }
  });

  // ---- Bridges: kit planks or procedural fallback ------------------------------------------
  const plankParts = plank ? await loadAsset(plank) : null;
  const postParts = post ? await loadAsset(post) : null;
  const deckMats: THREE.Matrix4[] = [];
  const postMats: THREE.Matrix4[] = [];
  const ropes: THREE.BufferGeometry[] = [];
  const pa = new THREE.Vector3(), pb = new THREE.Vector3(), dummy = new THREE.Object3D();
  for (const b of bridges) {
    const n = Math.max(1, Math.round(b.len / 2));
    for (let i = 0; i < n; i++) {
      const t0 = i / n, t1 = (i + 1) / n;
      pa.set(b.ax + (b.bx - b.ax) * t0, deckY(b, t0), b.az + (b.bz - b.az) * t0);
      pb.set(b.ax + (b.bx - b.ax) * t1, deckY(b, t1), b.az + (b.bz - b.az) * t1);
      dummy.position.copy(pa);
      dummy.scale.set(1, 1, pa.distanceTo(pb) / 2);
      dummy.lookAt(pb);
      dummy.updateMatrix();
      deckMats.push(dummy.matrix.clone());
    }
    const nx = -b.dz, nz = b.dx;
    for (const [x, z, y, yaw] of [[b.ax, b.az, b.ay, 0], [b.bx, b.bz, b.by, Math.PI]] as const) {
      for (const side of [-1, 1]) {
        const px = x + nx * (BRIDGE_HALF + 0.15) * side, pz = z + nz * (BRIDGE_HALF + 0.15) * side;
        postMats.push(new THREE.Matrix4().compose(pv.set(px, y - 0.1, pz), q.setFromAxisAngle(up, Math.atan2(b.dx, b.dz) + yaw), sc.setScalar(1)));
        colliders.push({ x: px, z: pz, r: 0.2, top: y + 1.4 });
        colliderIds.push("");
      }
    }
    // Rope rails
    for (const side of [-1, 1]) {
      const pts: THREE.Vector3[] = [];
      for (let k = 0; k <= 16; k++) {
        const t = k / 16;
        pts.push(new THREE.Vector3(
          b.ax + (b.bx - b.ax) * t + nx * (BRIDGE_HALF + 0.15) * side,
          deckY(b, t) + 1.05 - Math.sin(Math.PI * t) * 0.35,
          b.az + (b.bz - b.az) * t + nz * (BRIDGE_HALF + 0.15) * side,
        ));
      }
      ropes.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, 0.045, 5, false));
    }
  }
  const addInstanced = (parts: KitPart[], mats: THREE.Matrix4[], shadow: boolean) => {
    for (const part of parts) {
      const im = new THREE.InstancedMesh(part.geometry, part.material, mats.length);
      for (let i = 0; i < mats.length; i++) im.setMatrixAt(i, mats[i]);
      im.instanceMatrix.needsUpdate = true;
      im.castShadow = shadow;
      im.receiveShadow = true;
      im.computeBoundingSphere();
      scene.add(im);
    }
  };
  if (bridges.length) {
    if (plankParts?.length) addInstanced(plankParts, deckMats, true);
    else {
      const g = new THREE.BoxGeometry(2.5, 0.14, 0.42);
      g.translate(0, -0.07, 0.25);
      const planks: THREE.BufferGeometry[] = [];
      for (let k = 0; k < 4; k++) planks.push(g.clone().translate(0, 0, k * 0.5));
      const beam = new THREE.BoxGeometry(0.16, 0.18, 2).translate(0, -0.2, 1);
      planks.push(beam.clone().translate(-1.05, 0, 0), beam.clone().translate(1.05, 0, 0));
      const merged = mergeGeometries(planks, false)!;
      addInstanced([{ geometry: merged, material: painterly("kit", false, 0x8a6440) }], deckMats, true);
    }
    if (postParts?.length) addInstanced(postParts, postMats, true);
    else {
      const g = new THREE.CylinderGeometry(0.13, 0.16, 1.5, 7).translate(0, 0.75, 0);
      addInstanced([{ geometry: g, material: painterly("kit", false, 0x5a3f28) }], postMats, true);
    }
    const ropeGeo = mergeGeometries(ropes, false);
    if (ropeGeo) {
      const m = new THREE.Mesh(ropeGeo, painterly("kit", false, 0xc9a66b));
      m.castShadow = true;
      scene.add(m);
    }
  }

  // ---- Kit instancing ----------------------------------------------------------------------
  const entries = [...new Set([...batches.values()].map((b) => b.entry))];
  const loaded = new Map<string, KitPart[] | null>();
  await Promise.all(entries.map(async (e) => loaded.set(e.id, await loadAsset(e))));
  for (const b of batches.values()) {
    const parts = loaded.get(b.entry.id);
    if (!parts || !parts.length || !b.mats.length) continue;
    addInstanced(parts, b.mats, b.shadow);
  }
  // Drop colliders whose asset failed to load
  for (let i = colliders.length - 1; i >= 0; i--) {
    const id = colliderIds[i];
    if (id && !loaded.get(id)?.length) colliders.splice(i, 1);
  }

  // ---- Spawn -------------------------------------------------------------------------------
  const spawn = new THREE.Vector3(SPAWN_XZ[0], heightAt(SPAWN_XZ[0], SPAWN_XZ[1]) ?? elder.y, SPAWN_XZ[1]);

  // ---- Update ------------------------------------------------------------------------------
  const texel = (SHADOW_HALF * 2) / 2048;
  const update = (_dt: number, elapsed: number, focus: THREE.Vector3) => {
    windTime.value = elapsed;
    sky.update(elapsed, focus);
    const fx = Math.round(focus.x / texel) * texel, fy = Math.round(focus.y / texel) * texel, fz = Math.round(focus.z / texel) * texel;
    sun.target.position.set(fx, fy, fz);
    sun.position.set(fx + SUN_DIR.x * 120, fy + SUN_DIR.y * 120, fz + SUN_DIR.z * 120);
    sun.target.updateMatrixWorld();
  };
  update(0, 0, spawn);

  return { heightAt, colliders, spawn, sun, update };
}
