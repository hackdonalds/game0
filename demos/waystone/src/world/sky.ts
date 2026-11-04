// Dusk sky dome with painted clouds, the cloud sea far below, drifting cloud banks, distant isle silhouettes,
// sun + hemisphere light and fog. Storm level (U.uStorm) darkens all of it.
import * as THREE from "three";
import { GLSL_NOISE, painterly, U } from "./materials";
import { fbm, mulberry32 } from "./noise";
import type { Assets } from "../assets";
import { fit } from "./models";

export const SUN_DIR = new THREE.Vector3(-0.78, 0.25, -0.42).normalize();
export const CLOUD_Y = -92;

const CALM = {
  zenith: new THREE.Color(0x30477f),
  mid: new THREE.Color(0x8b88b4),
  horizon: new THREE.Color(0xf2b183),
  sun: new THREE.Color(0xffc27a),
  fog: new THREE.Color(0xd9a891),
  cloudLit: new THREE.Color(0xffd4a6),
  cloudShade: new THREE.Color(0x7f7fa6),
};
const STORM = {
  zenith: new THREE.Color(0x151a26),
  mid: new THREE.Color(0x303848),
  horizon: new THREE.Color(0x5f6675),
  sun: new THREE.Color(0x8a7a6a),
  fog: new THREE.Color(0x4a5160),
  cloudLit: new THREE.Color(0x6d7584),
  cloudShade: new THREE.Color(0x232a36),
};

export interface Sky {
  sun: THREE.DirectionalLight;
  hemi: THREE.HemisphereLight;
  update(dt: number, t: number, camera: THREE.Camera, focus: THREE.Vector3, lane: number): void;
}

export function createSky(scene: THREE.Scene, quality: "high" | "low", assets: Assets): Sky {
  const hi = quality === "high";
  const zenith = CALM.zenith.clone(), mid = CALM.mid.clone(), horizon = CALM.horizon.clone(), sunCol = CALM.sun.clone();
  const fogCol = CALM.fog.clone(), cloudLit = CALM.cloudLit.clone(), cloudShade = CALM.cloudShade.clone();
  scene.background = fogCol;
  const fog = new THREE.FogExp2(fogCol.getHex(), 0.0011);
  scene.fog = fog;

  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(100, 32, 16),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
      uniforms: { ...U, zenith: { value: zenith }, mid: { value: mid }, horizon: { value: horizon }, sunDir: { value: SUN_DIR }, sunCol: { value: sunCol }, cLit: { value: cloudLit }, cShade: { value: cloudShade }, uLane: { value: 0 } },
      vertexShader: `varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = vec4(p.xy, p.w * 0.99999, p.w);
        }`,
      fragmentShader: `uniform vec3 zenith, mid, horizon, sunDir, sunCol, cLit, cShade; uniform float uTime, uStorm, uFlash, uLane;
        varying vec3 vDir;
        ${GLSL_NOISE}
        void main() {
          vec3 d = normalize(vDir);
          float up = clamp(d.y, 0.0, 1.0);
          vec3 c = mix(horizon, mid, smoothstep(0.0, 0.28, up));
          c = mix(c, zenith, smoothstep(0.22, 0.85, up));
          float toward = max(dot(normalize(d.xz + 1e-4), normalize(sunDir.xz)), 0.0);
          c = mix(c, sunCol, (1.0 - smoothstep(0.0, 0.25, up)) * (0.15 + 0.55 * pow(toward, 3.0)) * (1.0 - uStorm * 0.8));
          float s = max(dot(d, sunDir), 0.0);
          c += sunCol * (pow(s, 4.0) * 0.4 + pow(s, 28.0) * 0.7 + pow(s, 400.0) * 1.2) * (1.0 - uStorm * 0.9);
          c += vec3(1.0, 0.93, 0.8) * smoothstep(0.99955, 0.9998, s) * 3.0 * (1.0 - uStorm);
          // painted clouds: long dusk streaks, heavy and dark in the storm
          if (d.y > -0.02) {
            vec2 uv = d.xz / (d.y + 0.12);
            vec2 q = uv * vec2(0.55, 1.1) + vec2(uTime * 0.004, uTime * 0.002);
            float n = wFbm(q * 1.3 + wFbm(q * 0.7) * 1.4);
            float cover = mix(0.5, 0.3, uStorm);
            float cl = smoothstep(cover, cover + 0.25, n) * smoothstep(-0.02, 0.12, d.y);
            float lit = clamp(wFbm(q * 1.3 + sunDir.xz * 0.15) - n + 0.55, 0.0, 1.0);
            vec3 ccol = mix(cShade, cLit, lit * (0.6 + 0.4 * pow(toward, 2.0)));
            ccol += sunCol * pow(s, 8.0) * 0.6 * (1.0 - uStorm);
            c = mix(c, ccol, cl * mix(0.75, 0.95, uStorm));
          }
          c += vec3(0.75, 0.82, 1.0) * uFlash * 0.5 * (0.4 + up);
          c = mix(c, horizon * 0.85, smoothstep(0.0, -0.2, d.y));
          gl_FragColor = vec4(c, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    }),
  );
  dome.renderOrder = -1000;
  dome.frustumCulled = false;
  scene.add(dome);

  // Cloud sea
  const seaMat = new THREE.ShaderMaterial({
    fog: false,
    uniforms: { ...U, uCam: { value: new THREE.Vector3() }, uFog: { value: fogCol }, uLit: { value: cloudLit }, uShade: { value: cloudShade }, uSun: { value: sunCol }, sunDir: { value: SUN_DIR } },
    vertexShader: `varying vec3 vWorld;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform float uTime, uStorm, uFlash; uniform vec3 uCam, uFog, uLit, uShade, uSun, sunDir;
      varying vec3 vWorld;
      ${GLSL_NOISE}
      void main() {
        vec2 p = vWorld.xz * 0.006;
        vec2 drift = vec2(uTime * 0.007, uTime * 0.004);
        float c = wFbm(p + drift);
        float c2 = wFbm(p * 2.7 - drift * 1.6 + c);
        float billow = smoothstep(0.3, 0.8, c * 0.7 + c2 * 0.45);
        vec3 col = mix(uShade, uLit, billow);
        float facing = clamp(wFbm(p + drift + normalize(sunDir.xz) * 0.05) - c + 0.5, 0.0, 1.0);
        col += uSun * pow(facing, 3.0) * 0.35 * billow * (1.0 - uStorm);
        col += vec3(0.6, 0.7, 0.9) * uFlash * 0.35 * billow;
        float dist = length(vWorld.xz - uCam.xz);
        col = mix(col, uFog, smoothstep(150.0, 2600.0, dist) * 0.85 + 0.05);
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000).rotateX(-Math.PI / 2), seaMat);
  sea.position.y = CLOUD_Y;
  sea.renderOrder = -900;
  scene.add(sea);

  // Cloud banks: soft billboards drifting below and around the isle
  const puffTex = makePuffTexture();
  const puffs: { s: THREE.Sprite; a: number; r: number; y: number; w: number }[] = [];
  const rng = mulberry32(77);
  const nPuffs = hi ? 26 : 14;
  for (let i = 0; i < nPuffs; i++) {
    const m = new THREE.SpriteMaterial({ map: puffTex, color: 0xffffff, transparent: true, depthWrite: false, opacity: 0.75, fog: true });
    const s = new THREE.Sprite(m);
    const r = 90 + rng() * 380, a = rng() * Math.PI * 2, y = CLOUD_Y + 12 + rng() * 45, size = 60 + rng() * 120;
    s.scale.set(size * 1.8, size, 1);
    s.position.set(Math.cos(a) * r, y, Math.sin(a) * r);
    s.renderOrder = -800;
    scene.add(s);
    puffs.push({ s, a, r, y, w: (rng() - 0.5) * 0.004 });
  }

  // Distant isles
  const isles = new THREE.Group();
  const isleMat = painterly(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 }), { rim: 0.5 });
  const spots: [number, number, number, number][] = [
    // angle (deg, 0 = +x, 90 = +z), distance, top height, radius
    [205, 620, -18, 40], [232, 1100, 30, 85], [256, 460, -40, 22], [300, 820, 5, 55], [330, 1500, 70, 120],
    [20, 760, -25, 45], [62, 1200, 25, 90], [118, 640, -45, 30], [160, 980, -5, 55], [278, 1800, 110, 150], [176, 1600, 50, 110],
  ];
  const under = assets.get("underside").gltf ? fit(assets, "underside") : null;
  for (const [deg, dist, y, r] of hi ? spots : spots.filter((_, i) => i % 3 !== 1 && i < 9)) {
    const a = (deg * Math.PI) / 180;
    let m: THREE.Object3D;
    if (under) {
      m = under.root.clone();
      m.scale.setScalar((r * 2) / Math.max(under.size.x, under.size.z));
      m.position.set(Math.cos(a) * dist, y - under.size.y * m.scale.y, Math.sin(a) * dist);
      m.traverse((o) => { o.castShadow = false; o.receiveShadow = false; });
    } else {
      m = new THREE.Mesh(distantIsle(r, Math.floor(deg * 7 + dist), hi), isleMat);
      m.position.set(Math.cos(a) * dist, y, Math.sin(a) * dist);
    }
    m.rotation.y = a * 3.1;
    isles.add(m);
  }
  scene.add(isles);

  const hemi = new THREE.HemisphereLight(0xb4bde0, 0x7a6450, 1.25);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffc690, 2.9);
  sun.castShadow = true;
  const sm = hi ? 2048 : 1024;
  sun.shadow.mapSize.set(sm, sm);
  const half = hi ? 42 : 30;
  Object.assign(sun.shadow.camera, { left: -half, right: half, top: half, bottom: -half, near: 1, far: 320 });
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = hi ? 0.04 : 0.08;
  scene.add(sun, sun.target);
  const texel = (2 * half) / sm;
  const tmpV = new THREE.Vector3();
  const sunCalm = new THREE.Color(0xffc690), sunStorm = new THREE.Color(0x9aa4c0);
  const hemiSky = new THREE.Color(0xa9b6e0), hemiSkyStorm = new THREE.Color(0x6c7890);

  return {
    sun,
    hemi,
    update(dt, t, camera, focus, lane) {
      const s = U.uStorm.value;
      zenith.copy(CALM.zenith).lerp(STORM.zenith, s);
      mid.copy(CALM.mid).lerp(STORM.mid, s);
      horizon.copy(CALM.horizon).lerp(STORM.horizon, s);
      sunCol.copy(CALM.sun).lerp(STORM.sun, s);
      fogCol.copy(CALM.fog).lerp(STORM.fog, s);
      cloudLit.copy(CALM.cloudLit).lerp(STORM.cloudLit, s);
      cloudShade.copy(CALM.cloudShade).lerp(STORM.cloudShade, s);
      // the lit lane warms the whole sky a little
      horizon.lerp(CALM.sun, lane * 0.12);
      fog.color.copy(fogCol);
      fog.density = 0.0011 + s * 0.0016;
      (dome.material as THREE.ShaderMaterial).uniforms.uLane.value = lane;
      dome.position.copy(camera.position);
      sea.position.x = camera.position.x;
      sea.position.z = camera.position.z;
      (seaMat.uniforms.uCam.value as THREE.Vector3).copy(camera.position);
      for (const p of puffs) {
        p.a += p.w * dt;
        p.s.position.set(Math.cos(p.a) * p.r, p.y, Math.sin(p.a) * p.r);
        (p.s.material as THREE.SpriteMaterial).color.copy(cloudLit).lerp(cloudShade, 0.35);
      }
      const f = U.uFlash.value;
      sun.intensity = (3.1 - 1.2 * s) + f * 2; // keep the ridge readable at full storm
      sun.color.copy(sunCalm).lerp(sunStorm, s);
      hemi.intensity = 1.35 - 0.1 * s + f * 2.2;
      hemi.color.copy(hemiSky).lerp(hemiSkyStorm, s);
      // shadow box follows the focus, snapped to texels to stop shimmering
      tmpV.copy(focus);
      tmpV.x = Math.round(tmpV.x / texel) * texel;
      tmpV.z = Math.round(tmpV.z / texel) * texel;
      sun.target.position.copy(tmpV);
      sun.position.copy(tmpV).addScaledVector(SUN_DIR, 150);
      void t;
    },
  };
}

function makePuffTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 128;
  const g = c.getContext("2d")!;
  const rng = mulberry32(5);
  for (let i = 0; i < 46; i++) {
    const x = 40 + rng() * 176, y = 50 + rng() * 40 - Math.abs(x - 128) * 0.12, r = 14 + rng() * 30 * (1 - Math.abs(x - 128) / 160);
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    const v = 230 + rng() * 25;
    grd.addColorStop(0, `rgba(${v},${v},${v},0.55)`);
    grd.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grd;
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function distantIsle(R: number, seed: number, hi: boolean): THREE.BufferGeometry {
  const segs = hi ? 28 : 16, rings = hi ? 7 : 4;
  const pos: number[] = [], col: number[] = [], idx: number[] = [];
  const top = new THREE.Color(0x5e8040), rock = new THREE.Color(0xb9ae94), dark = new THREE.Color(0x5b5248), tree = new THREE.Color(0x35532e);
  const c = new THREE.Color();
  const depth = R * (1.0 + 0.3 * Math.sin(seed));
  // top cap centre
  pos.push(0, R * 0.08, 0); col.push(top.r, top.g, top.b);
  for (let r = 0; r <= rings; r++) {
    const u = r / rings; // 0 = lip, 1 = tip
    for (let j = 0; j < segs; j++) {
      const a = (j / segs) * Math.PI * 2;
      const n = fbm(Math.cos(a) * 1.3 + seed, Math.sin(a) * 1.3, seed, 3);
      const rr = R * (1 + 0.15 * n) * (r === 0 ? 1 : 0.95 * Math.pow(1 - u, 0.7)) * (1 + 0.2 * fbm(a * 3, u * 4, seed + 3, 2) * u);
      const y = r === 0 ? 0 : -depth * u * (1 + 0.15 * n);
      pos.push(Math.cos(a) * rr, y, Math.sin(a) * rr);
      c.copy(r === 0 ? top : rock).lerp(dark, u * 0.7);
      col.push(c.r, c.g, c.b);
    }
  }
  pos.push(0, -depth * 1.05, 0); col.push(dark.r, dark.g, dark.b);
  for (let j = 0; j < segs; j++) idx.push(0, 1 + ((j + 1) % segs), 1 + j);
  for (let r = 0; r < rings; r++) for (let j = 0; j < segs; j++) {
    const a = 1 + r * segs + j, b = 1 + r * segs + ((j + 1) % segs), cc = a + segs, d = b + segs;
    idx.push(a, b, cc, b, d, cc);
  }
  const tip = pos.length / 3 - 1, last = 1 + rings * segs;
  for (let j = 0; j < segs; j++) idx.push(last + j, last + ((j + 1) % segs), tip);
  // a few tree cones on top
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  const parts = [g.toNonIndexed()];
  const rng = mulberry32(seed);
  const nt = Math.floor(3 + rng() * 6);
  for (let i = 0; i < nt; i++) {
    const a = rng() * Math.PI * 2, d = rng() * R * 0.75, h = R * (0.12 + rng() * 0.12);
    const cone = new THREE.ConeGeometry(h * 0.4, h, 6).toNonIndexed();
    cone.translate(Math.cos(a) * d, h / 2 + R * 0.04, Math.sin(a) * d);
    const n = cone.getAttribute("position").count;
    cone.setAttribute("color", new THREE.Float32BufferAttribute(new Array(n).fill(0).flatMap(() => [tree.r, tree.g, tree.b]), 3));
    cone.deleteAttribute("uv");
    cone.deleteAttribute("normal");
    parts.push(cone);
  }
  const merged = mergeSimple(parts);
  merged.computeVertexNormals();
  return merged;
}

function mergeSimple(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  let n = 0;
  for (const p of parts) n += p.getAttribute("position").count;
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
  let o = 0;
  for (const p of parts) {
    pos.set(p.getAttribute("position").array as Float32Array, o * 3);
    col.set(p.getAttribute("color").array as Float32Array, o * 3);
    o += p.getAttribute("position").count;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return g;
}
