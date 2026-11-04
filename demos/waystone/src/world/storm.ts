// Weather: rain around the camera, storm cloud vortex over the summit, lightning strikes near the Waystone,
// gust streaks across the rope bridge, and the glowing wind lane revealed at the end.
import * as THREE from "three";
import { BRIDGE, PLINTH_C, heightAt } from "./layout";
import { GLSL_NOISE, U } from "./materials";
import { mulberry32 } from "./noise";

// ---- gust schedule over the bridge (shared by gustAt and the streak visuals) ----
export const GUST_CYCLE = 6.2;
const WARN_END = 1.8, GUST_END = 3.7;
export function gustPhase(t: number) {
  const p = ((t % GUST_CYCLE) + GUST_CYCLE) % GUST_CYCLE;
  const k = Math.floor(t / GUST_CYCLE);
  const sign = Math.sin(k * 12.9898) * 43758.5453 % 1 > 0 ? 1 : -1;
  const sm = (a: number, b: number, v: number) => { const x = Math.min(1, Math.max(0, (v - a) / (b - a))); return x * x * (3 - 2 * x); };
  const warn = sm(0, 0.35, p) * (1 - sm(WARN_END - 0.1, WARN_END + 0.2, p));
  const strength = sm(WARN_END - 0.05, WARN_END + 0.35, p) * (1 - sm(GUST_END - 0.6, GUST_END, p));
  return { warn, strength, sign };
}
export const onBridge = (x: number, z: number) => Math.abs(x - BRIDGE.x) < 3.2 && z < BRIDGE.z0 + 1.5 && z > BRIDGE.z1 - 1.5;

export interface Storm {
  update(dt: number, t: number, camera: THREE.PerspectiveCamera, gust: { warn: number; strength: number; sign: number }, lane: number): void;
}

export function createStorm(scene: THREE.Scene, quality: "high" | "low", waystoneTop: THREE.Vector3): Storm {
  const hi = quality === "high";
  const rng = mulberry32(404);

  // ---- rain: camera-relative wrapped box of streaks ----
  const nRain = hi ? 2600 : 700;
  const rg = new THREE.BufferGeometry();
  const rp = new Float32Array(nRain * 4 * 3), rs = new Float32Array(nRain * 4 * 3), rc = new Float32Array(nRain * 4 * 2);
  const ri: number[] = [];
  for (let i = 0; i < nRain; i++) {
    const sx = rng(), sy = rng(), sz = rng();
    for (let k = 0; k < 4; k++) {
      rs.set([sx, sy, sz], (i * 4 + k) * 3);
      rc.set([k & 1 ? 1 : -1, k & 2 ? 1 : 0], (i * 4 + k) * 2);
    }
    ri.push(i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 1, i * 4 + 3, i * 4 + 2);
  }
  rg.setAttribute("position", new THREE.BufferAttribute(rp, 3));
  rg.setAttribute("aSeed", new THREE.BufferAttribute(rs, 3));
  rg.setAttribute("aCorner", new THREE.BufferAttribute(rc, 2));
  rg.setIndex(ri);
  const rainMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { ...U, uRain: { value: 0 }, uBox: { value: new THREE.Vector3(36, 26, 36) } },
    vertexShader: `uniform float uTime, uRain, uWind; uniform vec2 uWindDir; uniform vec3 uBox; attribute vec3 aSeed; attribute vec2 aCorner; varying float vA; varying float vV;
      void main() {
        vec3 vel = vec3(uWindDir.x * (3.0 + uWind * 9.0), -22.0, uWindDir.y * (3.0 + uWind * 9.0));
        vec3 p = aSeed * uBox + vel * uTime * (0.9 + aSeed.y * 0.2);
        p = mod(p - cameraPosition + uBox * 0.5, uBox) - uBox * 0.5 + cameraPosition;
        vec3 dir = normalize(vel);
        vec3 side = normalize(cross(dir, normalize(cameraPosition - p)));
        p += side * aCorner.x * 0.01 + dir * aCorner.y * 0.55;
        vA = uRain * step(aSeed.x * 0.999, uRain * 1.2) * (1.0 - smoothstep(10.0, 18.0, length(p - cameraPosition))) * smoothstep(1.5, 4.0, length(p - cameraPosition));
        vV = aCorner.y;
        gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: `uniform float uFlash; varying float vA; varying float vV;
      void main() { gl_FragColor = vec4(vec3(0.75, 0.8, 0.9) + uFlash, vA * 0.26 * (0.3 + vV)); }`,
  });
  const rain = new THREE.Mesh(rg, rainMat);
  rain.frustumCulled = false;
  rain.renderOrder = 20;
  scene.add(rain);

  // ---- storm vortex: dark swirling cloud deck over the summit ----
  const vortexMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    fog: false,
    uniforms: { ...U, uC: { value: new THREE.Vector2(PLINTH_C.x, PLINTH_C.z) }, uLane: { value: 0 } },
    vertexShader: `varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform float uTime, uStorm, uFlash, uLane; uniform vec2 uC; varying vec3 vW;
      ${GLSL_NOISE}
      void main() {
        vec2 d = vW.xz - uC;
        float r = length(d);
        float a = atan(d.y, d.x);
        float swirl = a + 18.0 / (r * 0.05 + 1.0) * 0.25 + uTime * 0.05;
        vec2 q = vec2(cos(swirl), sin(swirl)) * r * 0.018;
        float n = wFbm(q * 2.0 + uTime * 0.01);
        float n2 = wFbm(q * 5.0 - uTime * 0.02 + n);
        float body = smoothstep(0.35, 0.75, n * 0.75 + n2 * 0.4);
        float fall = 1.0 - smoothstep(60.0, 230.0, r);
        float eye = smoothstep(4.0, 26.0, r);
        float alpha = body * fall * eye * smoothstep(0.05, 0.6, uStorm) * 0.92;
        vec3 col = mix(vec3(0.09, 0.1, 0.14), vec3(0.28, 0.3, 0.38), n2);
        col += vec3(0.55, 0.65, 0.95) * uFlash * (0.6 + n2);
        gl_FragColor = vec4(col, alpha);
        #include <colorspace_fragment>
      }`,
  });
  const vortex = new THREE.Mesh(new THREE.CircleGeometry(240, 48).rotateX(Math.PI / 2), vortexMat);
  vortex.position.set(PLINTH_C.x, 62, PLINTH_C.z);
  vortex.renderOrder = 10;
  scene.add(vortex);

  // dark cloud masses hanging around the summit
  const puffTex = darkPuffTexture();
  const darkPuffs: THREE.Sprite[] = [];
  for (let i = 0; i < (hi ? 14 : 8); i++) {
    const m = new THREE.SpriteMaterial({ map: puffTex, color: 0x3a4150, transparent: true, depthWrite: false, opacity: 0, fog: true });
    const s = new THREE.Sprite(m);
    const a = (i / (hi ? 14 : 8)) * Math.PI * 2 + rng(), r = 85 + rng() * 70;
    s.position.set(PLINTH_C.x + Math.cos(a) * r, 38 + rng() * 25, PLINTH_C.z + Math.sin(a) * r * 0.8 - 10);
    const size = 40 + rng() * 40;
    s.scale.set(size * 1.7, size, 1);
    s.userData = { a, r, y: s.position.y, w: 0.02 + rng() * 0.03 };
    scene.add(s);
    darkPuffs.push(s);
  }

  // ---- lightning ----
  const boltMat = new THREE.MeshBasicMaterial({ color: 0xdfe9ff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, side: THREE.DoubleSide });
  const bolt = new THREE.Mesh(new THREE.BufferGeometry(), boltMat);
  bolt.frustumCulled = false;
  bolt.renderOrder = 30;
  scene.add(bolt);
  const strikeLight = new THREE.PointLight(0xbfd4ff, 0, 90, 1.2);
  scene.add(strikeLight);
  let nextStrike = 2, strikeT = -10;
  const strike = (camera: THREE.Camera) => {
    const a = rng() * Math.PI * 2, r = 9 + rng() * 34;
    const x = PLINTH_C.x + Math.cos(a) * r, z = PLINTH_C.z + Math.sin(a) * r;
    const gy = heightAt(x, z) ?? -35;
    const pts: THREE.Vector3[] = [];
    const top = new THREE.Vector3(x + (rng() - 0.5) * 30, 62, z + (rng() - 0.5) * 30);
    const end = new THREE.Vector3(x, gy, z);
    const n = 16;
    for (let i = 0; i <= n; i++) {
      const p = top.clone().lerp(end, i / n);
      if (i > 0 && i < n) p.add(new THREE.Vector3((rng() - 0.5) * 5, (rng() - 0.5) * 2, (rng() - 0.5) * 5));
      pts.push(p);
    }
    // branch
    const bi = 4 + Math.floor(rng() * 6);
    const branch: THREE.Vector3[] = [pts[bi].clone()];
    for (let i = 1; i < 6; i++) branch.push(branch[i - 1].clone().add(new THREE.Vector3((rng() - 0.5) * 6, -3 - rng() * 3, (rng() - 0.5) * 6)));
    bolt.geometry.dispose();
    bolt.geometry = ribbon([pts, branch], [0.55, 0.3], camera.position);
    strikeLight.position.copy(end).y += 6;
    strikeT = 0;
  };

  // ---- gust streaks across the bridge ----
  const nStreak = hi ? 80 : 40;
  const sg = new THREE.BufferGeometry();
  const quad: number[] = [], qc: number[] = [], qs: number[] = [], qi: number[] = [];
  for (let i = 0; i < nStreak; i++) {
    const seed = [rng(), rng(), rng(), rng()];
    for (let pl = 0; pl < 2; pl++) {
      const b = quad.length / 3;
      for (let k = 0; k < 4; k++) {
        quad.push(0, 0, 0);
        qc.push(k & 1 ? 1 : 0, k & 2 ? 1 : -1, pl);
        qs.push(...seed);
      }
      qi.push(b, b + 1, b + 2, b + 1, b + 3, b + 2);
    }
  }
  sg.setAttribute("position", new THREE.Float32BufferAttribute(quad, 3));
  sg.setAttribute("aCorner", new THREE.Float32BufferAttribute(qc, 3));
  sg.setAttribute("aSeed", new THREE.Float32BufferAttribute(qs, 4));
  sg.setIndex(qi);
  const streakMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    uniforms: { uTime: U.uTime, uWarn: { value: 0 }, uGust: { value: 0 }, uSign: { value: 1 }, uB: { value: new THREE.Vector3(BRIDGE.x, (BRIDGE.z0 + BRIDGE.z1) / 2, BRIDGE.z0 - BRIDGE.z1) }, uY: { value: 10 } },
    vertexShader: `uniform float uTime, uWarn, uGust, uSign, uY; uniform vec3 uB; attribute vec3 aCorner; attribute vec4 aSeed; varying float vA; varying float vU;
      void main() {
        float speed = mix(14.0, 34.0, uGust) * (0.8 + aSeed.w * 0.4);
        float range = 44.0;
        float x = mod(aSeed.x * range + uTime * speed, range) - range * 0.5;
        float len = mix(2.0, 5.5, uGust) * (0.6 + aSeed.y * 0.8);
        float wob = sin(uTime * 3.0 + aSeed.z * 20.0) * 0.4;
        vec3 p = vec3(uB.x + uSign * (x + aCorner.x * len), uY + aSeed.y * 4.0 - 0.8 + wob, uB.y + (aSeed.z - 0.5) * (uB.z + 3.0));
        float dc = length(p - cameraPosition);
        float w = max(0.025, dc * 0.0022) * (1.0 + 0.6 * uGust);
        if (aCorner.z < 0.5) p.y += aCorner.y * w; else p.z += aCorner.y * w;
        float vis = uWarn * step(aSeed.w, 0.45) * 0.6 + uGust;
        vA = vis * (1.0 - smoothstep(0.32, 0.5, abs(x / range))) * smoothstep(3.0, 8.0, dc);
        vU = aCorner.x;
        gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: `varying float vA; varying float vU;
      void main() { float a = vA * sin(vU * 3.14159) * 0.45; gl_FragColor = vec4(vec3(0.85, 0.92, 1.0) * a, a); }`,
  });
  const streaks = new THREE.Mesh(sg, streakMat);
  streaks.frustumCulled = false;
  streaks.renderOrder = 15;
  scene.add(streaks);
  streakMat.uniforms.uY.value = (heightAt(BRIDGE.x, (BRIDGE.z0 + BRIDGE.z1) / 2) ?? 10) - 0.5;

  // ---- wind lane: a glowing ribbon streaming off the Waystone across the cloud sea, towards the sunset ----
  const lanePts = [
    waystoneTop.clone().add(new THREE.Vector3(0, -0.8, 0)),
    waystoneTop.clone().add(new THREE.Vector3(-3, 4, -8)),
    new THREE.Vector3(-22, waystoneTop.y + 9, -88),
    new THREE.Vector3(-70, waystoneTop.y + 11, -118),
    new THREE.Vector3(-170, waystoneTop.y + 9, -165),
    new THREE.Vector3(-340, waystoneTop.y + 8, -250),
    new THREE.Vector3(-620, waystoneTop.y + 20, -390),
    new THREE.Vector3(-1100, waystoneTop.y + 50, -620),
  ];
  const laneCurve = new THREE.CatmullRomCurve3(lanePts, false, "centripetal");
  const laneGeo = laneRibbon(laneCurve, hi ? 260 : 140);
  const laneMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    fog: false,
    uniforms: { uTime: U.uTime, uLane: { value: 0 }, uReveal: { value: 0 } },
    vertexShader: `attribute vec2 aUV; varying vec2 vUV; void main() { vUV = aUV; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform float uTime, uLane, uReveal; varying vec2 vUV;
      ${GLSL_NOISE}
      void main() {
        float along = vUV.x, across = vUV.y;
        float edge = pow(1.0 - abs(across * 2.0 - 1.0), 1.6);
        float flow = wNoise(vec2(along * 90.0 - uTime * 2.2, across * 3.0));
        float streak = smoothstep(0.45, 0.95, wNoise(vec2(along * 260.0 - uTime * 5.0, across * 9.0)));
        float reveal = smoothstep(uReveal, uReveal - 0.03, along);
        float fade = (1.0 - smoothstep(0.55, 1.0, along)) * smoothstep(0.0, 0.01, along);
        vec3 teal = vec3(0.45, 1.0, 0.95), gold = vec3(1.0, 0.82, 0.45);
        vec3 col = mix(teal, gold, 0.5 + 0.5 * sin(along * 40.0 - uTime * 1.5));
        float a = edge * (0.25 + 0.4 * flow + 0.6 * streak) * reveal * fade * uLane * 0.6;
        gl_FragColor = vec4(col * a, a);
      }`,
  });
  const lane = new THREE.Mesh(laneGeo, laneMat);
  lane.frustumCulled = false;
  lane.renderOrder = 25;
  lane.visible = false;
  scene.add(lane);

  return {
    update(dt, t, camera, gust, laneLevel) {
      const s = U.uStorm.value;
      rainMat.uniforms.uRain.value = Math.max(0, (s - 0.2) / 0.8);
      rain.visible = s > 0.2;
      vortex.visible = s > 0.04;
      vortexMat.uniforms.uLane.value = laneLevel;
      for (const p of darkPuffs) {
        const u = p.userData as { a: number; r: number; y: number; w: number };
        u.a += u.w * dt;
        p.position.x = PLINTH_C.x + Math.cos(u.a) * u.r;
        p.position.z = PLINTH_C.z + Math.sin(u.a) * u.r * 0.8 - 10;
        const m = p.material as THREE.SpriteMaterial;
        m.opacity = Math.min(1, s * 1.1) * 0.85;
        m.color.setRGB(0.23 + U.uFlash.value * 0.5, 0.25 + U.uFlash.value * 0.55, 0.31 + U.uFlash.value * 0.6);
        p.visible = m.opacity > 0.01;
      }
      // lightning
      if (s > 0.35) {
        nextStrike -= dt * (0.4 + s);
        if (nextStrike <= 0) { strike(camera); nextStrike = 2.5 + rng() * 6; }
      }
      strikeT += dt;
      const flick = strikeT >= 0 && strikeT < 0.5 ? (strikeT < 0.07 ? 1 : strikeT < 0.13 ? 0.25 : strikeT < 0.2 ? 0.85 : Math.max(0, 1 - (strikeT - 0.2) / 0.3) * 0.4) : 0;
      boltMat.opacity = flick;
      bolt.visible = flick > 0;
      U.uFlash.value = flick * 0.5 * Math.min(1, s * 1.5);
      strikeLight.intensity = flick * 4000;
      // gust streaks
      streakMat.uniforms.uWarn.value = gust.warn;
      streakMat.uniforms.uGust.value = gust.strength;
      streakMat.uniforms.uSign.value = gust.sign;
      streaks.visible = gust.warn + gust.strength > 0.01;
      // wind lane
      lane.visible = laneLevel > 0.001;
      laneMat.uniforms.uLane.value = laneLevel;
      laneMat.uniforms.uReveal.value = Math.min(1.05, laneLevel * 1.1);
    },
  };
}

/** Camera-facing ribbons through polylines (built once per strike). */
function ribbon(lines: THREE.Vector3[][], widths: number[], eye: THREE.Vector3): THREE.BufferGeometry {
  const pos: number[] = [], idx: number[] = [];
  lines.forEach((pts, li) => {
    const w0 = widths[li];
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      const t = pts[Math.min(pts.length - 1, i + 1)].clone().sub(pts[Math.max(0, i - 1)]).normalize();
      const side = t.clone().cross(eye.clone().sub(p).normalize()).normalize().multiplyScalar(w0 * (1 - (i / pts.length) * 0.6));
      const b = pos.length / 3;
      pos.push(p.x - side.x, p.y - side.y, p.z - side.z, p.x + side.x, p.y + side.y, p.z + side.z);
      if (i > 0) idx.push(b - 2, b - 1, b, b - 1, b + 1, b);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  return g;
}

function laneRibbon(curve: THREE.CatmullRomCurve3, n: number): THREE.BufferGeometry {
  const pos: number[] = [], uv: number[] = [], idx: number[] = [];
  const frames = curve.computeFrenetFrames(n, false);
  const up = new THREE.Vector3(0, 1, 0);
  for (let strip = 0; strip < 3; strip++) {
    const rot = (strip / 3) * Math.PI;
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      const p = curve.getPointAt(u);
      const t = frames.tangents[i];
      const side = new THREE.Vector3().crossVectors(t, up).normalize();
      const vert = new THREE.Vector3().crossVectors(side, t).normalize();
      const dir = side.clone().multiplyScalar(Math.cos(rot)).addScaledVector(vert, Math.sin(rot));
      const w = (1.0 + Math.pow(u, 0.7) * 60) * (strip === 0 ? 1 : 0.5);
      const b = pos.length / 3;
      pos.push(p.x - dir.x * w, p.y - dir.y * w, p.z - dir.z * w, p.x + dir.x * w, p.y + dir.y * w, p.z + dir.z * w);
      uv.push(u, 0, u, 1);
      if (i > 0) idx.push(b - 2, b - 1, b, b - 1, b + 1, b);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("aUV", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

function darkPuffTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 128;
  const g = c.getContext("2d")!;
  const rng = mulberry32(9);
  for (let i = 0; i < 60; i++) {
    const x = 30 + rng() * 196, y = 40 + rng() * 55, r = 12 + rng() * 32 * (1 - Math.abs(x - 128) / 170);
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    const v = 200 + rng() * 55;
    grd.addColorStop(0, `rgba(${v},${v},${v},0.5)`);
    grd.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grd;
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
