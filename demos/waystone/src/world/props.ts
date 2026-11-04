// Placed set pieces (Waystone, camp with fire, jetty, rope bridge, old trees) and scattered trees and rocks.
import * as THREE from "three";
import type { Assets } from "../assets";
import { ARM, ARENA_C, BRIDGE, CAMP_C, GLIDE_C, JETTY, PLINTH_C, ROOT_TREE_S, armWidth, heightAt, jettyY, land, pathDist, type LandSample } from "./layout";
import { U } from "./materials";
import { fit, instance } from "./models";
import { mulberry32 } from "./noise";

export type Collider = { x: number; z: number; r: number };

export interface Props {
  colliders: Collider[];
  rootTrees: THREE.Vector3[];
  waystoneTop: THREE.Vector3;
  waystoneGlow: THREE.MeshStandardMaterial[];
  waystoneLight: THREE.PointLight;
  bridgeSegments: THREE.Object3D[];
  shardSpots: THREE.Vector3[];
  update(dt: number, t: number, camera: THREE.PerspectiveCamera, gust: number): void;
}

const v3 = (x: number, z: number, dy = 0) => new THREE.Vector3(x, (heightAt(x, z) ?? 0) + dy, z);

export function createProps(scene: THREE.Scene, assets: Assets, quality: "high" | "low"): Props {
  const hi = quality === "high";
  const colliders: Collider[] = [];
  const group = new THREE.Group();
  group.name = "props";
  scene.add(group);

  // ---- Waystone on its plinth ----
  const ws = fit(assets, "waystone");
  const wsPos = v3(PLINTH_C.x, PLINTH_C.z);
  ws.root.position.copy(wsPos).y -= 0.15;
  ws.root.rotation.y = 0.35;
  group.add(ws.root);
  colliders.push({ x: wsPos.x, z: wsPos.z, r: Math.max(0.9, Math.min(ws.size.x, ws.size.z) * 0.42) });
  for (const g of ws.glow) { g.userData.baseEmissive = g.emissiveIntensity || 1; g.emissiveIntensity = 0.12; }
  const waystoneTop = wsPos.clone().setY(wsPos.y + ws.size.y);
  const wsLight = new THREE.PointLight(0x8fe8ff, 0, 24, 1.6);
  wsLight.position.copy(wsPos).y += ws.size.y * 0.6;
  group.add(wsLight);

  // ---- Camp with fire ----
  const camp = fit(assets, "camp");
  const campPos = v3(CAMP_C.x, CAMP_C.z);
  camp.root.position.copy(campPos).y -= 0.05;
  camp.root.rotation.y = -0.5; // sail frame faces the path
  group.add(camp.root);
  colliders.push({ x: campPos.x, z: campPos.z, r: 1.25 });
  const firePos = campPos.clone().add(new THREE.Vector3(0, 0.2, 0));
  const fire = createFire(firePos, hi);
  group.add(fire.group);

  // ---- Jetty and skiff (deck along +z, out over the void) ----
  const jet = fit(assets, "jetty", { longAxisZ: true });
  const jz = JETTY.zc;
  // measured on the GLB: pier deck sits ~1.25 m above its base, pier centreline 1 m off the model centre
  jet.root.position.set(JETTY.x - (jet.real ? 1.0 : 0), jettyY() - (jet.real ? 1.25 : 2.66), jz);
  group.add(jet.root);
  for (const z of [JETTY.z0 + 3, JETTY.z0 + 6.5, JETTY.z1 - 0.4]) for (const x of [-JETTY.half + 0.1, JETTY.half - 0.1]) colliders.push({ x: JETTY.x + x, z, r: 0.22 });

  // ---- Rope bridge: tiled segments following the sag, posts at both ends ----
  const bridgeSegments: THREE.Object3D[] = [];
  const probe = fit(assets, "bridge", { longAxisZ: true });
  const segLen = Math.max(2, probe.size.z);
  const span = BRIDGE.z0 - BRIDGE.z1;
  const nSeg = Math.max(1, Math.round(span / segLen));
  const deck = (u: number) => heightAt(BRIDGE.x, BRIDGE.z0 - u * span) ?? 0;
  for (let i = 0; i < nSeg; i++) {
    const seg = i === 0 ? probe : fit(assets, "bridge", { longAxisZ: true });
    const u0 = i / nSeg, u1 = (i + 1) / nSeg;
    const y0 = deck(u0 + 0.001), y1 = deck(u1 - 0.001);
    const zc = BRIDGE.z0 - ((u0 + u1) / 2) * span;
    const pivot = new THREE.Group();
    pivot.position.set(BRIDGE.x, (y0 + y1) / 2 - 0.06, zc);
    pivot.rotation.x = Math.atan2(y1 - y0, span / nSeg); // seg forward is -z
    pivot.scale.z = span / nSeg / segLen;
    pivot.add(seg.root);
    group.add(pivot);
    bridgeSegments.push(pivot);
  }
  const postMat = new THREE.MeshStandardMaterial({ color: 0x5d4430, roughness: 1, flatShading: true });
  const postGeo = new THREE.CylinderGeometry(0.14, 0.2, 2.2, 7).translate(0, 0.8, 0);
  for (const z of [BRIDGE.z0 + 0.4, BRIDGE.z1 - 0.4]) for (const dx of [-1.25, 1.25]) {
    const p = new THREE.Mesh(postGeo, postMat);
    p.position.set(BRIDGE.x + dx, (heightAt(BRIDGE.x + dx, z) ?? deck(z > -30 ? 0 : 1)) - 0.3, z);
    p.castShadow = true;
    group.add(p);
    colliders.push({ x: p.position.x, z, r: 0.22 });
  }

  // ---- Old trees along the east arm (Rootwarden) ----
  const rootTrees: THREE.Vector3[] = [];
  const tmp2 = new THREE.Vector2(), tmp3 = new THREE.Vector2();
  ROOT_TREE_S.forEach((s, i) => {
    ARM.at(s, tmp2);
    ARM.at(Math.min(1, s + 0.01), tmp3);
    const tx = tmp3.x - tmp2.x, tz = tmp3.y - tmp2.y, tl = Math.hypot(tx, tz) || 1;
    let nx = -tz / tl, nz = tx / tl;
    // outward = away from the chasm (roughly the arm's centre of curvature)
    if ((tmp2.x - 14) * nx + (tmp2.y + 33) * nz < 0) { nx = -nx; nz = -nz; }
    const off = Math.min(2.8, armWidth(s) * 0.5);
    const x = tmp2.x + nx * off, z = tmp2.y + nz * off;
    const tree = fit(assets, "old-tree", { sway: 0.006 });
    const p = v3(x, z, -0.2);
    tree.root.position.copy(p);
    tree.root.rotation.y = i * 2.1 + 0.5;
    const sc = 0.92 + i * 0.07;
    tree.root.scale.setScalar(sc);
    group.add(tree.root);
    colliders.push({ x, z, r: 1.1 * sc });
    rootTrees.push(new THREE.Vector3(tmp2.x + nx * (off - 2.0), 0, tmp2.y + nz * (off - 2.0)));
  });
  for (const p of rootTrees) p.y = heightAt(p.x, p.z) ?? 0;

  // ---- Scatter: meadow trees, wind-bent pines, rock clusters ----
  const rng = mulberry32(1234);
  const L: LandSample = { sd: 0, h: 0, sdM: 0, sdS: 0, sdA: 0, s: 0 };
  const placed: { x: number; z: number; r: number }[] = [...colliders, { x: 0, z: 54, r: 6 }, { x: GLIDE_C.x, z: GLIDE_C.z, r: 5 }, { x: BRIDGE.x, z: BRIDGE.z0 - 1, r: 5 }];
  const shardSpots = [v3(-24, 21), v3(25, 9), v3(-15, 1)];
  for (const s of shardSpots) placed.push({ x: s.x, z: s.z, r: 4 });
  const free = (x: number, z: number, r: number) => placed.every((p) => Math.hypot(p.x - x, p.z - z) > p.r + r);
  const pick = (n: number, tries: number, ok: (x: number, z: number, l: LandSample) => boolean, r: number) => {
    const out: { x: number; z: number; y: number }[] = [];
    for (let i = 0; i < tries && out.length < n; i++) {
      const x = -46 + rng() * 92, z = -74 + rng() * 128;
      const l = land(x, z, L);
      if (!ok(x, z, l) || !free(x, z, r)) continue;
      placed.push({ x, z, r });
      out.push({ x, z, y: l.h });
    }
    return out;
  };
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  const mats = (pts: { x: number; z: number; y: number }[], smin: number, smax: number, lean = 0) =>
    pts.map((p) => {
      const s = smin + rng() * (smax - smin);
      e.set((rng() - 0.5) * lean, rng() * Math.PI * 2, (rng() - 0.5) * lean);
      return m4.compose(new THREE.Vector3(p.x, p.y - 0.15, p.z), q.setFromEuler(e), new THREE.Vector3(s, s * (0.9 + rng() * 0.2), s)).clone();
    });

  const meadowTrees = pick(hi ? 15 : 10, 4000, (x, z, l) => l.sdM > 3 && l.sdS < 0 && z > -5 && l.h < 3 && pathDist(x, z) > 4 && Math.hypot(x - CAMP_C.x, z - CAMP_C.z) > 9, 5.5);
  // a pair framing the camp
  const mtMats = mats(meadowTrees, 0.8, 1.25, 0.08);
  for (const p of [[CAMP_C.x + 7, CAMP_C.z + 3], [CAMP_C.x + 5.5, CAMP_C.z - 6]] as const) {
    if (free(p[0], p[1], 2)) { const y = heightAt(p[0], p[1]) ?? 0; mtMats.push(m4.compose(new THREE.Vector3(p[0], y - 0.15, p[1]), q.setFromEuler(e.set(0, rng() * 6, 0)), new THREE.Vector3(1.1, 1.1, 1.1)).clone()); meadowTrees.push({ x: p[0], z: p[1], y }); }
  }
  instance(fit(assets, "meadow-tree", { sway: 0.01 }).root, mtMats, group);
  meadowTrees.forEach((p) => colliders.push({ x: p.x, z: p.z, r: 0.55 }));

  const pines = pick(hi ? 15 : 9, 5000, (x, z, l) => {
    if (l.sd < 1.2 || pathDist(x, z) < 3) return false;
    const ridge = l.sdM > 0 && z < -6 && l.h > 3;
    const summitRim = l.sdS > 1.2 && Math.hypot(x - ARENA_C.x, z - ARENA_C.z) > 10.5 && Math.hypot(x - PLINTH_C.x, z - PLINTH_C.z) > 6.5;
    const westRim = l.sdM > 1.5 && l.sdM < 9 && x < -20 && z < 20;
    return ridge || summitRim || westRim;
  }, 6.5);
  // wind-bent: lean all pines the same way, away from the storm
  const pineMats = pines.map((p) => {
    const s = 0.75 + rng() * 0.5;
    q.setFromAxisAngle(new THREE.Vector3(1, 0, 0), 0.07 + rng() * 0.07).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rng() * Math.PI * 2));
    return m4.compose(new THREE.Vector3(p.x, p.y - 0.2, p.z), q, new THREE.Vector3(s, s, s)).clone();
  });
  instance(fit(assets, "pine", { sway: 0.008 }).root, pineMats, group, hi);
  pines.forEach((p) => colliders.push({ x: p.x, z: p.z, r: 0.45 }));

  const rockPts = pick(hi ? 46 : 20, 6000, (x, z, l) => {
    if (l.sd < 0.6) return false;
    const pd = pathDist(x, z);
    if (pd < 1.6) return false;
    if (Math.hypot(x - ARENA_C.x, z - ARENA_C.z) < 8.5) return false;
    if (Math.hypot(x - CAMP_C.x, z - CAMP_C.z) < 4) return false;
    const rocky = l.h > 2.5 || l.sd < 3.5 || l.sdA > 0;
    return rocky ? rng() < 0.9 : rng() < 0.22;
  }, 1.6);
  const rockMats = rockPts.map((p) => {
    const s = 0.5 + Math.pow(rng(), 2) * 1.7;
    e.set((rng() - 0.5) * 0.3, rng() * Math.PI * 2, (rng() - 0.5) * 0.3);
    if (s > 1.05) colliders.push({ x: p.x, z: p.z, r: 0.75 * s });
    return m4.compose(new THREE.Vector3(p.x, p.y - 0.25 * s, p.z), q.setFromEuler(e), new THREE.Vector3(s, s, s)).clone();
  });
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2 + 0.3;
    const dx = Math.cos(a), dz = Math.sin(a);
    const ax = ARENA_C.x - PLINTH_C.x, az = ARENA_C.z - PLINTH_C.z, al = Math.hypot(ax, az);
    if ((dx * ax + dz * az) / al > 0.75) continue; // keep the ramp clear
    const r = 5.2 + rng() * 0.6, x = PLINTH_C.x + dx * r, z = PLINTH_C.z + dz * r;
    const y = heightAt(x, z) ?? 11;
    const s = 1.3 + rng() * 0.9;
    e.set((rng() - 0.5) * 0.4, rng() * 6.28, (rng() - 0.5) * 0.4);
    rockMats.push(m4.compose(new THREE.Vector3(x, y - 0.5 * s, z), q.setFromEuler(e), new THREE.Vector3(s, s * 1.2, s)).clone());
  }
  instance(fit(assets, "rocks").root, rockMats, group, hi);

  // ---- hanging rock under the main body and the summit ----
  if (assets.get("underside").gltf) {
    for (const [x, z, w, top, rot] of [[0, 13, 74, -2.2, 0.4], [-2.5, -54, 31, 8.2, 2.2]] as const) {
      const u = fit(assets, "underside");
      const k = w / Math.max(u.size.x, u.size.z);
      u.root.scale.setScalar(k);
      u.root.position.set(x, top - u.size.y * k, z);
      u.root.rotation.y = rot;
      u.root.traverse((o) => { o.castShadow = false; });
      group.add(u.root);
    }
  }

  // ---- per-frame ----
  const baseRot = bridgeSegments.map((b) => b.rotation.z);
  let sway = 0;
  return {
    colliders,
    rootTrees,
    waystoneTop,
    waystoneGlow: ws.glow,
    waystoneLight: wsLight,
    bridgeSegments,
    shardSpots,
    update(dt, t, camera, gust) {
      fire.update(t, camera);
      sway += (gust - sway) * Math.min(1, dt * 3);
      bridgeSegments.forEach((b, i) => {
        const mid = Math.sin(((i + 0.5) / bridgeSegments.length) * Math.PI);
        b.rotation.z = baseRot[i] + (sway * 0.14 + Math.sin(t * 1.3 + i) * 0.012) * mid;
      });
    },
  };
}

function createFire(at: THREE.Vector3, hi: boolean) {
  const group = new THREE.Group();
  const light = new THREE.PointLight(0xff8a3a, 9, 16, 1.5);
  light.position.copy(at).y += 0.8;
  light.castShadow = false;
  group.add(light);
  const mk = (n: number, kind: number) => {
    const g = new THREE.BufferGeometry();
    const seeds = new Float32Array(n);
    for (let i = 0; i < n; i++) seeds[i] = i / n + Math.random() * 0.001;
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 3, 0), 8);
    const m = new THREE.ShaderMaterial({
      uniforms: { uTime: U.uTime, uWind: U.uWind, uWindDir: U.uWindDir, uPx: { value: 600 } },
      transparent: true,
      depthWrite: false,
      blending: kind === 2 ? THREE.NormalBlending : THREE.AdditiveBlending,
      vertexShader: `uniform float uTime, uWind, uPx; uniform vec2 uWindDir; attribute float aSeed; varying float vLife; varying float vSeed;
        float h(float n) { return fract(sin(n * 91.7) * 43758.5); }
        void main() {
          float kind = ${kind}.0;
          float dur = kind == 0.0 ? 0.9 : kind == 1.0 ? 2.6 : 7.0;
          float life = fract(uTime / dur + aSeed * 7.31);
          float s = aSeed * 13.7;
          vec3 p;
          float size;
          vec2 drift = uWindDir * (0.4 + uWind * 1.6);
          if (kind == 0.0) {
            float r = 0.32 * (1.0 - life) * h(s);
            float a = h(s + 1.0) * 6.283;
            p = vec3(cos(a) * r, life * (0.9 + 0.7 * h(s + 2.0)), sin(a) * r);
            p.xz += drift * life * life * 0.25;
            size = mix(0.75, 0.18, life) * (0.7 + 0.5 * h(s + 3.0));
          } else if (kind == 1.0) {
            float a = h(s + 1.0) * 6.283 + life * 5.0;
            p = vec3(cos(a) * 0.3 * life, life * 4.2, sin(a) * 0.3 * life);
            p.xz += drift * life * 1.4;
            size = 0.06 * (1.0 - life * 0.5);
          } else {
            p = vec3((h(s) - 0.5) * 0.4, 0.8 + life * 6.5, (h(s + 1.0) - 0.5) * 0.4);
            p.xz += drift * life * life * 3.0;
            size = mix(0.5, 2.6, life);
          }
          vLife = life; vSeed = h(s + 5.0);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_PointSize = size * uPx / -mv.z;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `uniform float uTime; varying float vLife; varying float vSeed;
        void main() {
          vec2 c = gl_PointCoord - 0.5;
          float d = length(c) * 2.0;
          float kind = ${kind}.0;
          if (d > 1.0) discard;
          vec4 col;
          if (kind == 0.0) {
            vec3 hot = vec3(1.0, 0.86, 0.5), mid = vec3(1.0, 0.45, 0.12), cool = vec3(0.7, 0.12, 0.04);
            vec3 cc = vLife < 0.4 ? mix(hot, mid, vLife / 0.4) : mix(mid, cool, (vLife - 0.4) / 0.6);
            float a = (1.0 - d * d) * smoothstep(0.0, 0.08, vLife) * (1.0 - vLife);
            col = vec4(cc * 1.6, a * 0.9);
          } else if (kind == 1.0) {
            float fl = 0.6 + 0.4 * sin(uTime * 20.0 + vSeed * 50.0);
            col = vec4(vec3(1.0, 0.6, 0.2) * 2.0 * fl, (1.0 - d) * (1.0 - vLife));
          } else {
            float a = (1.0 - d) * smoothstep(0.0, 0.15, vLife) * (1.0 - vLife) * 0.22;
            col = vec4(vec3(0.32, 0.3, 0.34), a);
          }
          gl_FragColor = col;
        }`,
    });
    const pts = new THREE.Points(g, m);
    pts.position.copy(at);
    pts.renderOrder = kind === 2 ? 5 : 6;
    group.add(pts);
    return m;
  };
  const mats = [mk(hi ? 46 : 26, 0), mk(hi ? 30 : 14, 1), mk(hi ? 14 : 7, 2)];
  // glowing embers bed
  const bed = new THREE.Mesh(new THREE.CircleGeometry(0.45, 12).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff7a2a, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false }));
  bed.position.copy(at).y += 0.06;
  group.add(bed);
  return {
    group,
    update(t: number, camera: THREE.PerspectiveCamera) {
      const px = (innerHeight * Math.min(devicePixelRatio, 2)) / (2 * Math.tan((camera.fov * Math.PI) / 360));
      for (const m of mats) m.uniforms.uPx.value = px;
      light.intensity = 9 * (0.82 + 0.12 * Math.sin(t * 13.1) + 0.08 * Math.sin(t * 27.3 + 1.2) + 0.06 * Math.sin(t * 5.7));
    },
  };
}
