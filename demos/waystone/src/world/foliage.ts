// Instanced grass tufts and wildflowers in tiles; tiles beyond the draw distance are hidden, and blades shrink
// away towards that distance so the cut-off never shows. Wind from the shared uniforms sways them.
import * as THREE from "three";
import { ARENA_C, CAMP_C, JETTY, PLINTH_C, land, pathDist, type LandSample } from "./layout";
import { U } from "./materials";
import { mulberry32, fbm, smooth } from "./noise";
import type { Terrain } from "./terrain";

const TILE = 12;

interface Tile { cx: number; cz: number; meshes: THREE.InstancedMesh[] }

export interface Foliage { update(camera: THREE.Camera): void }

function tuftGeometry(blades: number, seed: number): THREE.BufferGeometry {
  const pos: number[] = [], tip: number[] = [], nrm: number[] = [], idx: number[] = [];
  const rng = mulberry32(seed);
  for (let b = 0; b < blades; b++) {
    const a = rng() * Math.PI * 2, r = rng() * 0.12;
    const ox = Math.cos(a) * r, oz = Math.sin(a) * r;
    const yaw = rng() * Math.PI;
    const w = 0.045 + rng() * 0.03, h = 0.3 + rng() * 0.32;
    const lean = 0.12 + rng() * 0.2, la = rng() * Math.PI * 2;
    const cx = Math.cos(yaw), cz = Math.sin(yaw);
    const base = pos.length / 3;
    const rows = [0, 0.55, 1];
    for (const t of rows) {
      const ww = w * (1 - t) * (t === 1 ? 0 : 1);
      const lx = Math.cos(la) * lean * t * t, lz = Math.sin(la) * lean * t * t;
      if (t < 1) {
        pos.push(ox - cx * ww + lx, h * t, oz - cz * ww + lz, ox + cx * ww + lx, h * t, oz + cz * ww + lz);
        tip.push(t, t);
        nrm.push(0, 1, 0, 0, 1, 0);
      } else {
        pos.push(ox + lx, h, oz + lz);
        tip.push(1);
        nrm.push(0, 1, 0);
      }
    }
    idx.push(base, base + 1, base + 2, base + 1, base + 3, base + 2, base + 2, base + 3, base + 4);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute("aTip", new THREE.Float32BufferAttribute(tip, 1));
  g.setIndex(idx);
  return g;
}

function flowerGeometry(): THREE.BufferGeometry {
  const q1 = new THREE.PlaneGeometry(0.34, 0.42).translate(0, 0.21, 0);
  const q2 = q1.clone().rotateY(Math.PI / 2);
  const g = new THREE.BufferGeometry();
  const p = [...q1.getAttribute("position").array, ...q2.getAttribute("position").array];
  const uv = [...q1.getAttribute("uv").array, ...q2.getAttribute("uv").array];
  g.setAttribute("position", new THREE.Float32BufferAttribute(p, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(new Array(p.length).fill(0).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
  const tip = new Float32Array(p.length / 3);
  for (let i = 0; i < tip.length; i++) tip[i] = p[i * 3 + 1] / 0.42;
  g.setAttribute("aTip", new THREE.BufferAttribute(tip, 1));
  const i1 = q1.getIndex()!.array as ArrayLike<number>;
  g.setIndex([...Array.from(i1), ...Array.from(i1).map((i) => i + 4)]);
  return g;
}

function flowerTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = 64; c.height = 64;
  const g = c.getContext("2d")!;
  g.strokeStyle = "#4f7a34"; g.lineWidth = 3;
  g.beginPath(); g.moveTo(32, 64); g.quadraticCurveTo(28, 40, 32, 22); g.stroke();
  g.fillStyle = "#5f8a3a";
  g.beginPath(); g.ellipse(25, 44, 7, 3, -0.6, 0, Math.PI * 2); g.fill();
  g.fillStyle = "#ffffff";
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    g.beginPath(); g.ellipse(32 + Math.cos(a) * 7, 16 + Math.sin(a) * 7, 6, 3.6, a, 0, Math.PI * 2); g.fill();
  }
  g.fillStyle = "#f3c443";
  g.beginPath(); g.arc(32, 16, 3.6, 0, Math.PI * 2); g.fill();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function swayMaterial(fade: number, opts: { map?: THREE.Texture; flower?: boolean }): THREE.MeshLambertMaterial {
  const m = new THREE.MeshLambertMaterial({ map: opts.map ?? null, alphaTest: opts.map ? 0.5 : 0, side: THREE.DoubleSide });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U, { uFade: { value: fade } });
    sh.vertexShader = `uniform float uTime, uWind, uFade, uFlash; uniform vec2 uWindDir; attribute float aTip; varying float vTip;\n` + sh.vertexShader.replace(
      "#include <begin_vertex>",
      `#include <begin_vertex>
      vTip = aTip;
      vec3 ip = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
      float d = distance(cameraPosition.xz, ip.xz);
      float k = 1.0 - smoothstep(uFade * 0.6, uFade, d);
      transformed *= k;
      float ph = uTime * (1.6 + uWind * 1.8) + dot(ip.xz, uWindDir) * 0.32;
      float wave = sin(ph) * 0.5 + 0.5;
      float gustN = sin(ph * 0.37 + ip.x * 0.05) * 0.5 + 0.5;
      float bend = (0.08 + uWind * 0.38) * (0.4 + 0.6 * wave) * (0.6 + 0.6 * gustN);
      vec2 wiggle = vec2(sin(ph * 2.3 + ip.z), cos(ph * 1.9 + ip.x)) * 0.04;
      // rotate the bend into the instance's local frame (instances only have yaw + uniform scale)
      mat2 inv = mat2(instanceMatrix[0][0], instanceMatrix[2][0], instanceMatrix[0][2], instanceMatrix[2][2]);
      float sc = length(vec2(instanceMatrix[0][0], instanceMatrix[0][2]));
      vec2 dl = inv * (uWindDir * bend + wiggle) / (sc * sc);
      transformed.xz += dl * aTip * aTip * k;
      transformed.y -= length(dl) * aTip * aTip * 0.3 * k;`,
    );
    sh.fragmentShader = `uniform float uFlash; varying float vTip;\n` + sh.fragmentShader
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        ${opts.flower ? "" : "diffuseColor.rgb *= mix(0.8, 1.25, vTip);"}`,
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        totalEmissiveRadiance += diffuseColor.rgb * (uFlash * 0.5 + ${opts.flower ? "0.06" : "0.1 * vTip"});`,
      );
    if (opts.flower) {
      // petals take the instance colour, the green stem keeps its own
      sh.fragmentShader = sh.fragmentShader.replace(
        "#include <map_fragment>",
        `#ifdef USE_MAP
          vec4 texel = texture2D(map, vMapUv);
          float white = step(0.8, min(texel.r, min(texel.g, texel.b)));
          diffuseColor.a *= texel.a;
          diffuseColor.rgb = white > 0.5 ? diffuseColor.rgb * vColor.rgb : texel.rgb;
        #endif`,
      ).replace("#include <color_fragment>", "");
    }
  };
  m.customProgramCacheKey = () => `sway-${opts.flower ? 1 : 0}`;
  return m;
}

export function createFoliage(scene: THREE.Scene, terrain: Terrain, quality: "high" | "low"): Foliage {
  const hi = quality === "high";
  const fade = hi ? 75 : 34;
  const density = hi ? 4.2 : 1.8; // tufts per m² on open meadow
  const flowerDensity = hi ? 0.45 : 0.16;
  const grassGeo = tuftGeometry(hi ? 5 : 3, 3);
  const grassMat = swayMaterial(fade, {});
  const flowerMat = swayMaterial(fade * 0.7, { map: flowerTexture(), flower: true });
  const flowerGeo = flowerGeometry();
  const tiles: Tile[] = [];
  const L: LandSample = { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 };
  const rng = mulberry32(91);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const gc = new THREE.Color(), tint = new THREE.Color();
  const PETALS = [0xfaf4e6, 0xf3c443, 0xb48ad8, 0xf09ab0, 0xfaf4e6, 0xe9e2ff].map((c) => new THREE.Color(c));
  const group = new THREE.Group();
  group.name = "foliage";
  scene.add(group);

  for (let tz = -78; tz < 58; tz += TILE) {
    for (let tx = -48; tx < 48; tx += TILE) {
      const grass: THREE.Matrix4[] = [], gcol: THREE.Color[] = [], flowers: THREE.Matrix4[] = [], fcol: THREE.Color[] = [];
      const n = Math.round(TILE * TILE * density);
      for (let i = 0; i < n; i++) {
        const x = tx + rng() * TILE, z = tz + rng() * TILE;
        const l = land(x, z, L);
        if (l.sd < 0.5) continue;
        if (Math.abs(x - JETTY.x) < JETTY.half + 0.3 && z > JETTY.z0 - 1) continue;
        const pd = pathDist(x, z);
        if (pd < 0.8 + rng() * 0.9) continue;
        const dc = Math.hypot(x - CAMP_C.x, z - CAMP_C.z);
        if (dc < 2.6 + rng() * 1.5) continue;
        const dA = Math.hypot(x - ARENA_C.x, z - ARENA_C.z);
        if (dA < 5.5 && rng() > 0.15) continue;
        if (Math.hypot(x - PLINTH_C.x, z - PLINTH_C.z) < 5.5 && rng() > 0.25) continue;
        terrain.colorAt(x, z, gc);
        const green = gc.g - Math.max(gc.r, gc.b) * 0.92;
        if (green < 0.0 && rng() > 0.25) continue;
        // slope from neighbouring heights
        const l2 = l;
        const ny = terrain.normalYAt(x, z);
        if (ny < 0.8 && rng() > 0.2) continue;
        const patch = fbm(x * 0.07, z * 0.07, 93, 2);
        if (patch < -0.35 && rng() > 0.4) continue;
        const edgeLong = 1 + 0.5 * smooth(5, 0.5, l2.sd);
        const s = (0.65 + rng() * 0.6) * (0.75 + 0.5 * smooth(0.9, 3, pd)) * edgeLong * (1 - 0.35 * smooth(4, 10, l2.h));
        q.setFromAxisAngle(up, rng() * Math.PI * 2);
        m4.compose(v.set(x, l2.h - 0.03, z), q, sc.set(s, s * (0.85 + rng() * 0.3), s));
        grass.push(m4.clone());
        tint.copy(gc).lerp(new THREE.Color(0xa6c86a), 0.3 + 0.15 * rng()).multiplyScalar(0.95 + rng() * 0.15);
        gcol.push(tint.clone());
        if (rng() < flowerDensity / density * (patch > 0.15 ? 3 : 0.6) && l2.h < 8) {
          const fs = 1.1 + rng() * 0.6;
          m4.compose(v.set(x + 0.1, l2.h - 0.02, z), q, sc.set(fs, fs, fs));
          flowers.push(m4.clone());
          const pc = PETALS[Math.floor((fbm(x * 0.05, z * 0.05, 94, 2) * 0.5 + 0.5) * PETALS.length + rng() * 1.6) % PETALS.length];
          fcol.push(pc);
        }
      }
      const meshes: THREE.InstancedMesh[] = [];
      if (grass.length) {
        const im = new THREE.InstancedMesh(grassGeo, grassMat, grass.length);
        grass.forEach((mm, i) => { im.setMatrixAt(i, mm); im.setColorAt(i, gcol[i]); });
        im.receiveShadow = true;
        im.computeBoundingSphere();
        meshes.push(im);
      }
      if (flowers.length) {
        const im = new THREE.InstancedMesh(flowerGeo, flowerMat, flowers.length);
        flowers.forEach((mm, i) => { im.setMatrixAt(i, mm); im.setColorAt(i, fcol[i]); });
        im.receiveShadow = true;
        im.computeBoundingSphere();
        meshes.push(im);
      }
      if (meshes.length) {
        for (const m of meshes) group.add(m);
        tiles.push({ cx: tx + TILE / 2, cz: tz + TILE / 2, meshes });
      }
    }
  }
  const lim = fade + TILE * 0.75;
  return {
    update(camera) {
      const p = camera.position;
      for (const t of tiles) {
        const vis = Math.hypot(t.cx - p.x, t.cz - p.z) < lim;
        for (const m of t.meshes) m.visible = vis;
      }
    },
  };
}
