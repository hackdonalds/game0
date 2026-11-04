// Model fitting and instancing. GLBs from public/models are normalised to their assets.json size hint
// (base on y=0, centred on x/z); missing files get a hand-built procedural fallback instead of a capsule.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import type { Assets } from "../assets";
import { paintModel, painterly } from "./materials";
import { mulberry32 } from "./noise";

export interface Fitted {
  root: THREE.Object3D;
  size: THREE.Vector3;
  glow: THREE.MeshStandardMaterial[];
  real: boolean;
}

/** A fresh, normalised instance of a model. `longAxisZ` rotates the longest horizontal axis onto z. */
export function fit(assets: Assets, key: string, opts: { longAxisZ?: boolean; sway?: number } = {}): Fitted {
  const m = assets.get(key);
  const e = m.entry;
  let inner: THREE.Object3D;
  let real = !!m.gltf;
  if (m.gltf) inner = m.clone();
  else {
    const fb = FALLBACK[key];
    inner = fb ? fb() : m.clone();
    real = false;
  }
  const glow = paintModel(inner, { sway: real ? opts.sway : undefined });
  const holder = new THREE.Group();
  holder.add(inner);
  inner.updateMatrixWorld(true);
  let box = new THREE.Box3().setFromObject(inner);
  let size = box.getSize(new THREE.Vector3());
  if (opts.longAxisZ && size.x > size.z) {
    inner.rotation.y = Math.PI / 2;
    inner.updateMatrixWorld(true);
    box = new THREE.Box3().setFromObject(inner);
    size = box.getSize(new THREE.Vector3());
  }
  let s = typeof e.scale === "number" ? (e.scale as number) : 1;
  if (typeof e.scale !== "number" && real) {
    if (e.height) s = e.height / size.y;
    else if (e.length) s = e.length / Math.max(size.x, size.z);
    else if (e.width) s = e.width / Math.max(size.x, size.z);
  }
  inner.scale.multiplyScalar(s);
  inner.updateMatrixWorld(true);
  box = new THREE.Box3().setFromObject(inner);
  const c = box.getCenter(new THREE.Vector3());
  inner.position.x -= c.x;
  inner.position.z -= c.z;
  inner.position.y -= box.min.y - (typeof e.yOffset === "number" ? (e.yOffset as number) : 0);
  size = box.getSize(new THREE.Vector3());
  const root = new THREE.Group();
  root.name = key;
  root.add(holder);
  return { root, size, glow, real };
}

/** One InstancedMesh per mesh of `obj`, placed by `mats`. */
export function instance(obj: THREE.Object3D, mats: THREE.Matrix4[], parent: THREE.Object3D, shadows = true): THREE.InstancedMesh[] {
  obj.updateMatrixWorld(true);
  const out: THREE.InstancedMesh[] = [];
  const tmp = new THREE.Matrix4();
  obj.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const im = new THREE.InstancedMesh(mesh.geometry, mesh.material, mats.length);
    for (let i = 0; i < mats.length; i++) im.setMatrixAt(i, tmp.multiplyMatrices(mats[i], mesh.matrixWorld));
    im.castShadow = shadows;
    im.receiveShadow = true;
    im.computeBoundingSphere();
    parent.add(im);
    out.push(im);
  });
  return out;
}

// ---- procedural fallbacks (used until lane B's GLBs land, and if a file is ever missing) ----

function col(g: THREE.BufferGeometry, c: number | THREE.Color, jitter = 0, seed = 1): THREE.BufferGeometry {
  g = g.index ? g.toNonIndexed() : g;
  g.deleteAttribute("uv");
  const n = g.getAttribute("position").count;
  const a = new Float32Array(n * 3);
  const base = new THREE.Color(c), t = new THREE.Color();
  const rng = mulberry32(seed);
  for (let i = 0; i < n; i += 3) {
    t.copy(base).offsetHSL(0, 0, (rng() - 0.5) * jitter);
    for (let k = 0; k < 3; k++) { a[(i + k) * 3] = t.r; a[(i + k) * 3 + 1] = t.g; a[(i + k) * 3 + 2] = t.b; }
  }
  g.setAttribute("color", new THREE.BufferAttribute(a, 3));
  g.computeVertexNormals();
  return g;
}
function lumpy(g: THREE.BufferGeometry, amt: number, seed: number): THREE.BufferGeometry {
  const p = g.getAttribute("position");
  const rng = mulberry32(seed);
  const offs = new Map<string, number>();
  for (let i = 0; i < p.count; i++) {
    const k = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
    let o = offs.get(k);
    if (o === undefined) { o = 1 + (rng() - 0.5) * amt; offs.set(k, o); }
    p.setXYZ(i, p.getX(i) * o, p.getY(i) * o, p.getZ(i) * o);
  }
  return g;
}
const mat = (kind: "solid" | "leaf" | "glow" = "solid") => {
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: kind !== "leaf" });
  if (kind === "glow") { m.name = "glow"; m.emissive.set(0x8ff0ff); m.emissiveIntensity = 1; }
  if (kind === "leaf") painterly(m, { sway: 0.025 });
  return m;
};
const meshOf = (parts: THREE.BufferGeometry[], m: THREE.Material) => new THREE.Mesh(mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g))), m);

function canopy(blobs: [number, number, number, number][], color: number, seed: number) {
  return blobs.map(([x, y, z, r], i) => col(lumpy(new THREE.IcosahedronGeometry(r, 1), 0.35, seed + i), color, 0.12, seed + i).translate(x, y, z));
}

const FALLBACK: Record<string, () => THREE.Object3D> = {
  "meadow-tree": () => {
    const g = new THREE.Group();
    g.add(meshOf([col(new THREE.CylinderGeometry(0.22, 0.38, 3.4, 7).translate(0, 1.7, 0), 0x5a4232, 0.1)], mat()));
    g.add(meshOf(canopy([[0, 4.4, 0, 2.2], [1.2, 3.8, 0.4, 1.5], [-1.1, 4.0, -0.5, 1.6], [0.2, 5.4, -0.2, 1.4]], 0x5d8a3a, 3), mat("leaf")));
    return g;
  },
  pine: () => {
    const g = new THREE.Group();
    g.add(meshOf([col(new THREE.CylinderGeometry(0.12, 0.3, 6, 6).translate(0, 3, 0), 0x4d3a2c, 0.1)], mat()));
    const cones: THREE.BufferGeometry[] = [];
    for (let i = 0; i < 4; i++) {
      const r = 2.1 - i * 0.45, y = 2.6 + i * 1.5;
      cones.push(col(lumpy(new THREE.ConeGeometry(r, 2.4, 7, 1), 0.2, 9 + i).translate(i * 0.25, y, 0), 0x2f5536, 0.1, i));
    }
    g.add(meshOf(cones, mat("leaf")));
    return g;
  },
  "old-tree": () => {
    const g = new THREE.Group();
    const trunk = [col(lumpy(new THREE.CylinderGeometry(0.7, 1.4, 6, 9, 3), 0.15, 2).translate(0, 3, 0), 0x5b4535, 0.1)];
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + 0.4;
      trunk.push(col(new THREE.CylinderGeometry(0.25, 0.45, 4, 6).rotateZ(0.9).rotateY(a).translate(Math.cos(a) * 1.5, 6.4, -Math.sin(a) * 1.5), 0x5b4535, 0.1));
    }
    g.add(meshOf(trunk, mat()));
    g.add(meshOf(canopy([[0, 9, 0, 3.6], [2.8, 8, 1, 2.6], [-2.6, 8.2, -1, 2.7], [0.6, 8.4, 2.8, 2.4], [-0.8, 8.4, -2.8, 2.5], [0, 10.8, 0, 2.4]], 0x6c8a34, 21), mat("leaf")));
    return g;
  },
  rocks: () => {
    const parts = [
      col(lumpy(new THREE.DodecahedronGeometry(0.9, 0), 0.35, 1).scale(1.3, 0.8, 1).translate(0, 0.6, 0), 0xb9b09a, 0.15, 1),
      col(lumpy(new THREE.DodecahedronGeometry(0.55, 0), 0.35, 2).translate(1.1, 0.35, 0.3), 0xa49c88, 0.15, 2),
      col(lumpy(new THREE.DodecahedronGeometry(0.4, 0), 0.35, 3).translate(-0.9, 0.25, 0.5), 0xc4bba4, 0.15, 3),
    ];
    return meshOf(parts, mat());
  },
  waystone: () => {
    const g = new THREE.Group();
    const stone = col(lumpy(new THREE.CylinderGeometry(0.7, 1.05, 5.4, 6, 4), 0.08, 4).translate(0, 2.7, 0), 0x9a9587, 0.12, 4);
    const cap = col(lumpy(new THREE.ConeGeometry(0.72, 0.8, 6), 0.1, 5).translate(0, 5.8, 0), 0x8f8a7c, 0.1, 5);
    const base = col(lumpy(new THREE.CylinderGeometry(1.5, 1.8, 0.6, 8), 0.15, 6).translate(0, 0.3, 0), 0x7e786a, 0.1, 6);
    g.add(meshOf([stone, cap, base], mat()));
    const runes: THREE.BufferGeometry[] = [];
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + Math.PI / 6;
      for (let k = 0; k < 3; k++) {
        const y = 1.4 + k * 1.3, r = 1.0 - (y / 5.4) * 0.33 + 0.02;
        runes.push(col(new THREE.BoxGeometry(0.08, 0.7 - k * 0.1, 0.04).rotateY(-a + Math.PI / 2).translate(Math.cos(a) * r * 0.87, y, Math.sin(a) * r * 0.87), 0xbff6ff));
      }
    }
    g.add(meshOf(runes, mat("glow")));
    return g;
  },
  camp: () => {
    const g = new THREE.Group();
    const parts: THREE.BufferGeometry[] = [];
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * Math.PI * 2;
      parts.push(col(lumpy(new THREE.DodecahedronGeometry(0.22, 0), 0.3, i).translate(Math.cos(a) * 0.75, 0.15, Math.sin(a) * 0.75), 0x9c9585, 0.2, i));
    }
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      parts.push(col(new THREE.CylinderGeometry(0.06, 0.08, 0.9, 5).rotateZ(0.9).rotateY(a).translate(Math.cos(a) * 0.22, 0.3, Math.sin(a) * 0.22), 0x4a3526, 0.1));
    }
    parts.push(col(new THREE.CylinderGeometry(0.22, 0.24, 1.9, 8).rotateZ(Math.PI / 2).translate(-0.4, 0.22, 1.7), 0x6b4f37, 0.1));
    parts.push(col(new THREE.CylinderGeometry(0.22, 0.24, 1.7, 8).rotateZ(Math.PI / 2).rotateY(1.1).translate(1.8, 0.22, 0.4), 0x6b4f37, 0.1));
    // sail frame behind the fire
    parts.push(col(new THREE.CylinderGeometry(0.08, 0.1, 2.9, 6).translate(-1.8, 1.45, -1.8), 0x5a4232));
    parts.push(col(new THREE.CylinderGeometry(0.08, 0.1, 2.9, 6).translate(1.8, 1.45, -1.8), 0x5a4232));
    parts.push(col(new THREE.CylinderGeometry(0.06, 0.06, 4.0, 6).rotateZ(Math.PI / 2).translate(0, 2.75, -1.8), 0x5a4232));
    parts.push(col(new THREE.BoxGeometry(0.7, 0.55, 0.55).translate(2.0, 0.27, -0.9), 0x7a5a3c, 0.1));
    g.add(meshOf(parts, mat()));
    const sail = new THREE.PlaneGeometry(3.3, 2.2, 6, 4);
    const sp = sail.getAttribute("position");
    for (let i = 0; i < sp.count; i++) sp.setZ(i, Math.sin(sp.getX(i) * 1.4) * 0.12 + (1.1 - sp.getY(i)) * 0.08);
    const sailMesh = new THREE.Mesh(col(sail.translate(0, 1.6, -1.8), 0xe7dcc0, 0.08, 7), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide }));
    g.add(sailMesh);
    const patch = new THREE.Mesh(col(new THREE.PlaneGeometry(0.8, 0.7).translate(-0.8, 1.3, -1.72), 0xa8553f), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide }));
    const patch2 = new THREE.Mesh(col(new THREE.PlaneGeometry(0.6, 0.5).translate(0.9, 2.1, -1.72), 0x3f7a6a), patch.material);
    g.add(patch, patch2);
    return g;
  },
  jetty: () => {
    const g = new THREE.Group();
    const parts: THREE.BufferGeometry[] = [];
    for (let i = 0; i < 20; i++) parts.push(col(new THREE.BoxGeometry(3.0, 0.12, 0.5).translate((i % 2) * 0.06, 2.9, -5 + i * 0.55), 0x8a6a48, 0.18, i));
    for (const x of [-1.45, 1.45]) for (let k = 0; k < 4; k++) parts.push(col(new THREE.CylinderGeometry(0.16, 0.2, 3.6, 7).translate(x, 2.1 + (k === 3 ? 0.6 : 0), -4.8 + k * 3.4), 0x5d4430, 0.1, k));
    g.add(meshOf(parts, mat()));
    // skiff alongside
    const hull = new THREE.SphereGeometry(1, 14, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2).scale(1.1, 0.75, 3.4);
    const skiff = new THREE.Group();
    skiff.add(meshOf([col(hull, 0x6d4d33, 0.1), col(new THREE.BoxGeometry(1.8, 0.1, 0.4).translate(0, -0.15, 0.8), 0x8a6a48)], new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide })));
    skiff.add(meshOf([col(new THREE.CylinderGeometry(0.06, 0.08, 3.6, 6).translate(0, 1.6, -0.6), 0x5d4430)], mat()));
    const sail = new THREE.Mesh(col(new THREE.PlaneGeometry(1.6, 2.2).translate(0.82, 1.9, -0.6).rotateY(0.15), 0xe8dcc0), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide }));
    skiff.add(sail);
    skiff.position.set(2.9, 2.75, 1.5);
    skiff.rotation.z = 0.05;
    g.add(skiff);
    return g;
  },
  bridge: () => {
    const parts: THREE.BufferGeometry[] = [];
    for (let i = 0; i < 12; i++) parts.push(col(new THREE.BoxGeometry(2.2, 0.08, 0.38).translate(0, 0.04, -3 + 0.25 + i * 0.5), 0x8a6a48, 0.2, i));
    for (const x of [-1.05, 1.05]) {
      parts.push(col(new THREE.CylinderGeometry(0.035, 0.035, 6, 4).rotateX(Math.PI / 2).translate(x, 1.0, 0), 0xc9b48a));
      parts.push(col(new THREE.CylinderGeometry(0.04, 0.04, 6, 4).rotateX(Math.PI / 2).translate(x, 0.02, 0), 0xc9b48a));
      for (let k = 0; k < 5; k++) parts.push(col(new THREE.CylinderGeometry(0.02, 0.02, 1.0, 3).translate(x, 0.5, -2.4 + k * 1.2), 0xc9b48a));
    }
    return meshOf(parts, mat());
  },
};
