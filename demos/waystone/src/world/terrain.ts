// Terrain: a grid over the layout whose edge vertices are snapped onto the land contour, so the lip and cliff
// walls follow the shape smoothly. A second surface hangs below as the rocky underside (limestone, moss, ivy).
import * as THREE from "three";
import { ARENA_C, BOUNDS, CAMP_C, PLINTH_C, land, pathDist, plinthRise, type LandSample } from "./layout";
import { painterly } from "./materials";
import { fbm, smooth } from "./noise";

const SKIRT = 6.5;

export interface Terrain {
  top: THREE.Mesh;
  under: THREE.Mesh;
  /** ground colour at a vertex near x,z (for grass tinting) */
  colorAt(x: number, z: number, out: THREE.Color): THREE.Color;
  normalYAt(x: number, z: number): number;
}

const C = {
  grass: new THREE.Color(0x5c8a3c),
  grassLight: new THREE.Color(0x8fb45a),
  grassDry: new THREE.Color(0xc4ad5e),
  grassDeep: new THREE.Color(0x3b6233),
  alpine: new THREE.Color(0x6d8a4a),
  path: new THREE.Color(0x9c7f58),
  pathDark: new THREE.Color(0x6f573c),
  soil: new THREE.Color(0x5a4230),
  rock: new THREE.Color(0xa89f8c),
  rockDark: new THREE.Color(0x6e665a),
  rockCool: new THREE.Color(0x9d9a8e),
  moss: new THREE.Color(0x56763a),
  ivy: new THREE.Color(0x6f8e34),
  crevice: new THREE.Color(0x4b443a),
};

export function buildTerrain(quality: "high" | "low"): Terrain {
  const cell = quality === "high" ? 0.55 : 0.95;
  const nx = Math.ceil((BOUNDS.maxX - BOUNDS.minX) / cell) + 1;
  const nz = Math.ceil((BOUNDS.maxZ - BOUNDS.minZ) / cell) + 1;
  const N = nx * nz;
  const sd = new Float32Array(N);
  const px = new Float32Array(N), pz = new Float32Array(N), ph = new Float32Array(N), psd = new Float32Array(N);
  const L: LandSample = { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 };
  const sdAt = (x: number, z: number) => land(x, z, L).sd;

  for (let j = 0; j < nz; j++) {
    for (let i = 0; i < nx; i++) {
      const k = j * nx + i;
      const x = BOUNDS.minX + i * cell, z = BOUNDS.minZ + j * cell;
      sd[k] = land(x, z, L).sd;
    }
  }
  // which vertices are used: inside, or a neighbour of an inside vertex
  const used = new Uint8Array(N);
  for (let j = 0; j < nz - 1; j++) for (let i = 0; i < nx - 1; i++) {
    const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
    if (sd[a] >= 0 || sd[b] >= 0 || sd[c] >= 0 || sd[d] >= 0) used[a] = used[b] = used[c] = used[d] = 1;
  }
  // snap vertices near the contour onto it (inside → just inside, outside → skirt line just outside)
  const e = 0.15;
  for (let k = 0; k < N; k++) {
    if (!used[k]) continue;
    let x = BOUNDS.minX + (k % nx) * cell, z = BOUNDS.minZ + Math.floor(k / nx) * cell;
    let s = sd[k];
    const target = s < 0 ? -0.35 : s < cell * 0.5 ? 0.03 : s;
    for (let it = 0; it < 3 && Math.abs(s - target) > 0.02; it++) {
      const gx = (sdAt(x + e, z) - sdAt(x - e, z)) / (2 * e);
      const gz = (sdAt(x, z + e) - sdAt(x, z - e)) / (2 * e);
      const g2 = gx * gx + gz * gz || 1;
      const step = Math.max(-cell * 1.2, Math.min(cell * 1.2, s - target));
      x -= (gx * step) / g2;
      z -= (gz * step) / g2;
      s = sdAt(x, z);
    }
    const l = land(x, z, L);
    px[k] = x; pz[k] = z; psd[k] = s;
    ph[k] = s < 0 ? l.h - SKIRT * (0.8 + 0.4 * fbm(x * 0.2, z * 0.2, 41, 2)) : l.h;
  }

  // index remap for used vertices
  const remap = new Int32Array(N).fill(-1);
  let nv = 0;
  for (let k = 0; k < N; k++) if (used[k]) remap[k] = nv++;
  const topPos = new Float32Array(nv * 3), botPos = new Float32Array(nv * 3);
  const vsd = new Float32Array(nv);
  for (let k = 0; k < N; k++) {
    const v = remap[k];
    if (v < 0) continue;
    const x = px[k], z = pz[k], s = psd[k];
    topPos[v * 3] = x; topPos[v * 3 + 1] = ph[k]; topPos[v * 3 + 2] = z;
    vsd[v] = s;
    let yb: number;
    if (s < 0) yb = ph[k];
    else {
      const depth = 11 * (1 - Math.exp(-s / 6));
      const stal = smooth(1.5, 9, s) * 7 * Math.pow(Math.max(0, fbm(x * 0.085, z * 0.085, 43, 3) + 0.15), 1.6);
      const crag = 1.6 * fbm(x * 0.32, z * 0.32, 44, 2) * smooth(0.3, 4, s);
      yb = ph[k] - SKIRT - depth - stal - crag;
    }
    botPos[v * 3] = x + (s > 0 ? 0.25 * fbm(z * 0.2, 3, 45, 2) * smooth(0, 3, s) : 0);
    botPos[v * 3 + 1] = yb;
    botPos[v * 3 + 2] = z;
  }
  const idx: number[] = [];
  for (let j = 0; j < nz - 1; j++) for (let i = 0; i < nx - 1; i++) {
    const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
    const ia = remap[a], ib = remap[b], ic = remap[c], id = remap[d];
    if (ia < 0 || ib < 0 || ic < 0 || id < 0) continue;
    // split along the shorter diagonal of the snapped quad
    const dad = (px[a] - px[d]) ** 2 + (pz[a] - pz[d]) ** 2, dbc = (px[b] - px[c]) ** 2 + (pz[b] - pz[c]) ** 2;
    const tris = dad < dbc ? [[ia, ic, id], [ia, id, ib]] : [[ia, ic, ib], [ib, ic, id]];
    for (const t of tris) {
      if (vsd[t[0]] < 0 && vsd[t[1]] < 0 && vsd[t[2]] < 0) continue;
      idx.push(t[0], t[1], t[2]);
    }
  }

  const topGeo = new THREE.BufferGeometry();
  topGeo.setAttribute("position", new THREE.BufferAttribute(topPos, 3));
  topGeo.setIndex(idx);
  topGeo.computeVertexNormals();
  const botGeo = new THREE.BufferGeometry();
  botGeo.setAttribute("position", new THREE.BufferAttribute(botPos, 3));
  const bidx = new Uint32Array(idx.length);
  for (let i = 0; i < idx.length; i += 3) { bidx[i] = idx[i]; bidx[i + 1] = idx[i + 2]; bidx[i + 2] = idx[i + 1]; }
  botGeo.setIndex(new THREE.BufferAttribute(bidx, 1));
  botGeo.computeVertexNormals();

  // colours
  const topCol = new Float32Array(nv * 3), botCol = new Float32Array(nv * 3);
  const tn = topGeo.getAttribute("normal") as THREE.BufferAttribute;
  const col = new THREE.Color(), tmp = new THREE.Color();
  for (let v = 0; v < nv; v++) {
    const x = topPos[v * 3], y = topPos[v * 3 + 1], z = topPos[v * 3 + 2], s = vsd[v];
    const ny = tn.getY(v);
    topColor(x, y, z, s, ny, col, tmp);
    topCol[v * 3] = col.r; topCol[v * 3 + 1] = col.g; topCol[v * 3 + 2] = col.b;
    underColor(x, botPos[v * 3 + 1], z, s, y, col, tmp);
    botCol[v * 3] = col.r; botCol[v * 3 + 1] = col.g; botCol[v * 3 + 2] = col.b;
  }
  topGeo.setAttribute("color", new THREE.BufferAttribute(topCol, 3));
  botGeo.setAttribute("color", new THREE.BufferAttribute(botCol, 3));

  const mat = painterly(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0 }), { ground: true, rim: 0.12 });
  const top = new THREE.Mesh(topGeo, mat);
  top.receiveShadow = true;
  top.castShadow = true;
  top.name = "terrain";
  const under = new THREE.Mesh(botGeo, painterly(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0 }), { ground: true, rim: 0.06 }));
  under.name = "underside";
  under.receiveShadow = true;

  const vAt = (x: number, z: number) => {
    const i = Math.round((x - BOUNDS.minX) / cell), j = Math.round((z - BOUNDS.minZ) / cell);
    return remap[Math.max(0, Math.min(nz - 1, j)) * nx + Math.max(0, Math.min(nx - 1, i))];
  };
  return {
    top,
    under,
    colorAt(x, z, out) {
      const v = vAt(x, z);
      if (v < 0) return out.copy(C.grass);
      return out.setRGB(topCol[v * 3], topCol[v * 3 + 1], topCol[v * 3 + 2]);
    },
    normalYAt(x, z) {
      const v = vAt(x, z);
      return v < 0 ? 1 : tn.getY(v);
    },
  };
}

function topColor(x: number, y: number, z: number, s: number, ny: number, out: THREE.Color, tmp: THREE.Color) {
  const n1 = fbm(x * 0.045, z * 0.045, 31, 3), n2 = fbm(x * 0.13, z * 0.13, 32, 2), n3 = fbm(x * 0.02 + 5, z * 0.02, 33, 2);
  // meadow greens: light rolls, deeper hollows, dry gold patches
  out.copy(C.grass).lerp(C.grassLight, smooth(-0.3, 0.6, n1) * 0.7);
  out.lerp(C.grassDeep, smooth(0.1, -0.6, n2) * 0.35);
  out.lerp(C.grassDry, smooth(0.15, 0.6, n3) * 0.45);
  // higher ground turns alpine and thin
  out.lerp(C.alpine, smooth(3, 10, y) * 0.55);
  // exposed rock: slopes, ridge crags, summit rim, plinth
  let rock = smooth(0.86, 0.66, ny);
  rock = Math.max(rock, smooth(6, 12, y) * smooth(0.1, 0.5, fbm(x * 0.09, z * 0.09, 34, 3)));
  const dPl = Math.hypot(x - PLINTH_C.x, z - PLINTH_C.z);
  rock = Math.max(rock, (1 - smooth(3.4, 4.4, dPl)) * smooth(2.2, 3.2, dPl) * 0.7, smooth(4.3, 5.0, dPl) * (1 - smooth(5.6, 6.6, dPl)) * 0.9);
  if (dPl > 4.2) rock = Math.max(rock, smooth(0.25, 1.4, plinthRise(x, z)) * 0.85);
  tmp.copy(C.rock).lerp(C.rockDark, smooth(-0.4, 0.5, n2) * 0.6).lerp(C.rockCool, smooth(8, 14, y) * 0.3);
  out.lerp(tmp, rock);
  // worn dirt paths, camp and arena
  const pd = pathDist(x, z) + n2 * 0.5;
  let dirt = 1 - smooth(0.7, 1.9, pd);
  dirt = Math.max(dirt, 1 - smooth(2.2, 5, Math.hypot(x - CAMP_C.x, z - CAMP_C.z) + n2 * 1.5));
  const dA = Math.hypot(x - ARENA_C.x, z - ARENA_C.z);
  dirt = Math.max(dirt, (1 - smooth(3, 8.5, dA + n2 * 2)) * 0.8);
  tmp.copy(C.path).lerp(C.pathDark, smooth(0.2, -0.5, n1) * 0.5);
  out.lerp(tmp, dirt * (1 - rock * 0.6));
  // lip: soil then pale rock down the skirt
  if (s < 0.9) {
    if (s < 0) out.copy(C.rock).lerp(C.soil, 0.35 + 0.3 * n2);
    else out.lerp(C.soil, smooth(0.9, 0.0, s) * 0.55);
  }
}

function underColor(x: number, y: number, z: number, s: number, topY: number, out: THREE.Color, tmp: THREE.Color) {
  const below = topY - y; // depth below the lip
  const n1 = fbm(x * 0.12, y * 0.25 + z * 0.12, 51, 3), n2 = fbm(x * 0.4 + y * 0.2, z * 0.4, 52, 2);
  // limestone with strata
  const strata = 0.5 + 0.5 * Math.sin(y * 1.7 + n1 * 3);
  out.copy(C.rock).lerp(C.rockDark, strata * 0.35 + smooth(0.1, -0.5, n2) * 0.4);
  // deeper is darker and cooler (ambient occlusion and cloud shade)
  tmp.copy(C.crevice);
  out.lerp(tmp, smooth(6, 40, below) * 0.55);
  // moss and ivy hanging down from the lip
  const ivy = smooth(14, 2, below + n1 * 8) * smooth(-0.2, 0.3, n2 + 0.2);
  out.lerp(n2 > 0.1 ? C.ivy : C.moss, Math.min(1, ivy + (s < 0 ? 0.5 : 0)));
}
