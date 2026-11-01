import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import GUI from "lil-gui";
import shard from "../../../worlds/first-shard.world.json";
import { Sim, Tier, type SimIsle } from "./sim";

type ShardIsle = SimIsle & { shrine: boolean };
const isles = shard.isles as ShardIsle[];

// ---------- Scene ----------

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(renderer.domElement);

const labels = new CSS2DRenderer();
labels.setSize(innerWidth, innerHeight);
Object.assign(labels.domElement.style, { position: "fixed", inset: "0", pointerEvents: "none" });
document.body.append(labels.domElement);

const SKY = new THREE.Color(0x9cc3e6);
const scene = new THREE.Scene();
scene.background = SKY;
scene.fog = new THREE.Fog(SKY, 1400, 4200);
scene.add(new THREE.HemisphereLight(0xfff4dc, 0x5a7f8f, 2.2));
const sunLight = new THREE.DirectionalLight(0xffd79a, 2.2);
sunLight.position.set(1, 2, 1.4);
scene.add(sunLight);

const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 1, 10000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.48;
controls.minDistance = 20;
controls.maxDistance = 3500;

const sea = new THREE.Mesh(new THREE.CircleGeometry(shard.size * 3, 64), new THREE.MeshStandardMaterial({ color: 0x8fa6bf, roughness: 1 }));
sea.rotation.x = -Math.PI / 2;
sea.position.y = shard.stormY;
scene.add(sea);

const BIOME: Record<string, number> = { meadow: 0x8fbf5a, forest: 0x4f8a3c, roothold: 0x6f9a3a, crag: 0xa9a196, garden: 0x9bc86a, lagoon: 0x7fbf8a, ruin: 0xb7a98c };
const isleMeshes: THREE.Mesh[] = [];
isles.forEach((i, index) => {
  const top = new THREE.Mesh(new THREE.CylinderGeometry(i.radius, i.radius * 0.92, i.radius * 0.16, 20), new THREE.MeshStandardMaterial({ color: BIOME[i.biome] ?? 0x8fbf5a, flatShading: true }));
  top.position.set(i.x, i.y - i.radius * 0.08, i.z);
  top.userData.index = index;
  const under = new THREE.Mesh(new THREE.ConeGeometry(i.radius * 0.92, i.radius * 1.2, 20), new THREE.MeshStandardMaterial({ color: 0x7a5d44, flatShading: true }));
  under.rotation.x = Math.PI;
  under.position.set(i.x, i.y - i.radius * 0.16 - i.radius * 0.6, i.z);
  under.userData.index = index;
  scene.add(top, under);
  isleMeshes.push(top, under);
  if (i.town || i.shrine) {
    const el = document.createElement("div");
    el.className = "label";
    el.textContent = i.name;
    const label = new CSS2DObject(el);
    label.position.set(i.x, i.y + 18, i.z);
    scene.add(label);
  }
});

// ---------- Characters ----------

const VIS = 3; // characters are drawn 3x real size so they read from the default camera distance
const params = { npcs: 5000, timeScale: 6, fullRadius: 120, lightRadius: 350, showAbstract: true, tour: true };
let sim: Sim;
let walkers: THREE.InstancedMesh;
let ships: THREE.InstancedMesh;
let dots: THREE.Points;

const FULL_COLOR = new THREE.Color(0xffd166);
const LIGHT_COLOR = new THREE.Color(0x2fb5a5);

function build() {
  if (walkers) { scene.remove(walkers, ships, dots); walkers.dispose(); ships.dispose(); dots.geometry.dispose(); }
  sim = new Sim(isles, params.npcs, params, 7);
  const capsule = new THREE.CapsuleGeometry(0.35 * VIS, 0.9 * VIS, 3, 6);
  capsule.translate(0, 0.8 * VIS, 0);
  walkers = new THREE.InstancedMesh(capsule, new THREE.MeshStandardMaterial({ roughness: 0.6 }), params.npcs);
  walkers.frustumCulled = false;
  const hull = new THREE.BoxGeometry(1.4 * VIS, 0.8 * VIS, 3.6 * VIS);
  ships = new THREE.InstancedMesh(hull, new THREE.MeshStandardMaterial({ roughness: 0.6 }), params.npcs);
  ships.frustumCulled = false;
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(params.npcs * 3), 3));
  dots = new THREE.Points(g, new THREE.PointsMaterial({ color: 0x3d5a80, size: 3, sizeAttenuation: false }));
  dots.frustumCulled = false;
  scene.add(walkers, ships, dots);
}
build();

// ---------- Player ----------

const player = new THREE.Group();
const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.5 * VIS, 1.2 * VIS, 4, 8), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xff5a36, emissiveIntensity: 0.9 }));
body.position.y = 1.1 * VIS;
player.add(body);
const ringMat = (color: number) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5, side: THREE.DoubleSide, depthWrite: false });
const fullRing = new THREE.Mesh(new THREE.RingGeometry(0.985, 1, 128), ringMat(0xffd166));
const lightRing = new THREE.Mesh(new THREE.RingGeometry(0.993, 1, 128), ringMat(0x2fb5a5));
for (const r of [fullRing, lightRing]) { r.rotation.x = -Math.PI / 2; r.position.y = 0.5; player.add(r); }
scene.add(player);

const start = isles.findIndex((i) => i.name === "Accord Hall");
const pos = new THREE.Vector3(isles[start].x, isles[start].y, isles[start].z);
let flight: { from: THREE.Vector3; to: THREE.Vector3; t: number; dur: number } | undefined;
let hoverUntil = 4;
let clockT = 0;

function goTo(index: number) {
  const i = isles[index];
  const ang = Math.random() * Math.PI * 2, d = Math.random() * i.radius * 0.4;
  const to = new THREE.Vector3(i.x + Math.cos(ang) * d, i.y, i.z + Math.sin(ang) * d);
  flight = { from: pos.clone(), to, t: 0, dur: Math.max(3, pos.distanceTo(to) / 90) };
}

const raycaster = new THREE.Raycaster();
let down = { x: 0, y: 0 };
renderer.domElement.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; });
renderer.domElement.addEventListener("pointerup", (e) => {
  if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return;
  raycaster.setFromCamera(new THREE.Vector2((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1), camera);
  const hit = raycaster.intersectObjects(isleMeshes)[0];
  if (!hit) return;
  params.tour = false;
  gui.controllersRecursive().forEach((c) => c.updateDisplay());
  goTo(hit.object.userData.index);
});

function updatePlayer(dt: number) {
  clockT += dt;
  if (flight) {
    flight.t = Math.min(1, flight.t + dt / flight.dur);
    const u = flight.t * flight.t * (3 - 2 * flight.t);
    pos.lerpVectors(flight.from, flight.to, u);
    pos.y += Math.sin(u * Math.PI) * 60;
    if (flight.t >= 1) { flight = undefined; hoverUntil = clockT + 8; }
  } else if (params.tour && clockT > hoverUntil) {
    let next: number;
    do next = Math.floor(Math.random() * isles.length); while (isles[next].tier === "wild" && Math.random() < 0.6);
    goTo(next);
  }
  const before = player.position.clone();
  player.position.copy(pos);
  fullRing.scale.setScalar(params.fullRadius);
  lightRing.scale.setScalar(params.lightRadius);
  // The camera follows the player
  const delta = player.position.clone().sub(before);
  camera.position.add(delta);
  controls.target.add(delta);
  sim.player.x = pos.x; sim.player.y = pos.y; sim.player.z = pos.z;
}

// ---------- Draw ----------

const m = new THREE.Matrix4();
const q = new THREE.Quaternion();
const s = new THREE.Vector3(1, 1, 1);
const v = new THREE.Vector3();
const yAxis = new THREE.Vector3(0, 1, 0);
const tmp = { x: 0, y: 0, z: 0 };

function draw() {
  const now = performance.now() / 1000;
  let w = 0, sh = 0, dn = 0;
  const arr = (dots.geometry.attributes.position as THREE.BufferAttribute).array as Float32Array;
  for (const n of sim.npcs) {
    if (n.tier === Tier.Abstract) {
      if (!params.showAbstract) continue;
      sim.planPosition(n, sim.t, tmp);
      arr[dn * 3] = tmp.x; arr[dn * 3 + 1] = tmp.y; arr[dn * 3 + 2] = tmp.z;
      dn++;
      continue;
    }
    const color = n.tier === Tier.Full ? FULL_COLOR : LIGHT_COLOR;
    // Light NPCs move once a second; interpolate between their last two positions like a client would
    const f = n.tier === Tier.Light ? Math.min(1, Math.max(0, 1 - (n.nextThink - now))) : 1;
    v.set(n.px + (n.x - n.px) * f, n.y, n.pz + (n.z - n.pz) * f);
    if (n.from !== n.to) {
      const a = isles[n.from], b = isles[n.to];
      q.setFromAxisAngle(yAxis, Math.atan2(b.x - a.x, b.z - a.z));
      ships.setMatrixAt(sh, m.compose(v, q, s));
      ships.setColorAt(sh++, color);
    } else {
      const face = n.state === "greet" ? Math.atan2(sim.player.x - n.x, sim.player.z - n.z) : Math.atan2(n.tx - n.x, n.tz - n.z);
      q.setFromAxisAngle(yAxis, face);
      walkers.setMatrixAt(w, m.compose(v, q, s));
      walkers.setColorAt(w++, color);
    }
  }
  walkers.count = w; ships.count = sh;
  walkers.instanceMatrix.needsUpdate = ships.instanceMatrix.needsUpdate = true;
  if (walkers.instanceColor) walkers.instanceColor.needsUpdate = true;
  if (ships.instanceColor) ships.instanceColor.needsUpdate = true;
  dots.geometry.setDrawRange(0, dn);
  dots.geometry.attributes.position.needsUpdate = true;
}

// ---------- HUD ----------

const hud = document.getElementById("hud")!;
const acc = { full: { u: 0, ms: 0 }, light: { u: 0, ms: 0 }, abstract: { u: 0, ms: 0 }, tiering: { u: 0, ms: 0 }, draw: 0, frames: 0, time: 0 };
let shown = "";

function report(dt: number, drawMs: number) {
  for (const k of ["full", "light", "abstract", "tiering"] as const) { acc[k].u += sim.stats[k].updates; acc[k].ms += sim.stats[k].ms; }
  acc.draw += drawMs; acc.frames++; acc.time += dt;
  if (acc.time < 0.5) return;
  const per = (x: number) => x / acc.time;
  const row = (name: string, color: string, count: number, k: "full" | "light" | "abstract", rate: string) =>
    `<tr><td><i style="background:${color}"></i>${name}</td><td>${count.toLocaleString()}</td><td>${rate}</td><td>${Math.round(per(acc[k].u)).toLocaleString()}</td><td>${per(acc[k].ms).toFixed(2)}</td></tr>`;
  const st = sim.stats;
  const simMs = per(acc.full.ms + acc.light.ms + acc.abstract.ms + acc.tiering.ms);
  const fullPerUpdate = acc.full.u ? acc.full.ms / acc.full.u : 0;
  const naive = fullPerUpdate * sim.npcs.length * 20;
  shown = `
    <table>
      <tr><th>Level</th><th>NPCs</th><th>Rate</th><th>Updates/s</th><th>ms/s</th></tr>
      ${row("Full", "#ffd166", st.full.count, "full", "20 Hz")}
      ${row("Light", "#2fb5a5", st.light.count, "light", "1 Hz")}
      ${row("Abstract", "#3d5a80", st.abstract.count, "abstract", "on plan end")}
      <tr><td>Tier checks</td><td></td><td>4 Hz</td><td>${Math.round(per(acc.tiering.u))}</td><td>${per(acc.tiering.ms).toFixed(2)}</td></tr>
    </table>
    <p><b>Simulation: ${simMs.toFixed(1)} ms per second</b> (${(simMs / 10).toFixed(2)}% of one core).<br>
    If all ${sim.npcs.length.toLocaleString()} were Full: about ${naive.toFixed(0)} ms per second.<br>
    Drawing (client side, not part of the server cost): ${(acc.draw / acc.frames).toFixed(1)} ms per frame.</p>`;
  hud.innerHTML = shown;
  for (const k of ["full", "light", "abstract", "tiering"] as const) { acc[k].u = 0; acc[k].ms = 0; }
  acc.draw = 0; acc.frames = 0; acc.time = 0;
}

// ---------- GUI ----------

const gui = new GUI({ title: "Living Shard" });
gui.add(params, "npcs", 500, 30000, 500).name("NPCs").onFinishChange(build);
gui.add(params, "timeScale", 1, 30, 1).name("time scale");
gui.add(params, "fullRadius", 20, 400, 5).name("full radius (m)");
gui.add(params, "lightRadius", 50, 1200, 10).name("light radius (m)");
gui.add(params, "showAbstract").name("show abstract");
gui.add(params, "tour").name("auto tour");
gui.add({ overview: () => { camera.position.set(pos.x, pos.y + 1900, pos.z + 1500); controls.target.copy(pos); } }, "overview").name("Overview");
gui.add({ close: () => { camera.position.set(pos.x, pos.y + 260, pos.z + 330); controls.target.copy(pos); } }, "close").name("Close up");

camera.position.set(pos.x, pos.y + 380, pos.z + 480);
controls.target.copy(pos);

// ---------- Loop ----------

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  labels.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.1);
  updatePlayer(dt);
  sim.step(dt, params.timeScale);
  const t0 = performance.now();
  draw();
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
  report(dt, performance.now() - t0);
});
