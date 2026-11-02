import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import clips from "../public/models/rootwarden.clips.json";

// Ground speed per clip (m/s), measured from the library's root motion and scaled to this body
const SPEED: Record<string, number> = Object.fromEntries(Object.entries(clips).map(([k, v]) => [k, v.speed]));
const FADE = 0.2;
const GRAVITY = 14;
const JUMP_SPEED = 4.6;
const TAKEOFF = 0.1; // seconds into JumpStart when the feet leave the ground
const HITS = ["hit_reaction_0", "hit_reaction_1", "face_punch_0", "hit_waist", "gunshot_reaction"];
const ATTACKS = ["punch_combo_1", "punch_combo_2", "punch_combo_3", "kick", "attack"];

// ---------- Scene ----------

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.prepend(renderer.domElement);

const SKY = new THREE.Color(0x9cc3e6);
const scene = new THREE.Scene();
scene.background = SKY;
scene.fog = new THREE.Fog(SKY, 18, 60);
scene.add(new THREE.HemisphereLight(0xfff4dc, 0x5a7f8f, 2));
const sun = new THREE.DirectionalLight(0xffd79a, 2.4);
sun.position.set(4, 8, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 0.5, far: 30 });
scene.add(sun, sun.target);

const ground = new THREE.Mesh(new THREE.CircleGeometry(60, 64), new THREE.MeshStandardMaterial({ color: 0x8fbf5a, roughness: 1 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(120, 120, 0x6f9a3a, 0x7fae4c);
grid.position.y = 0.002;
scene.add(grid);

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 200);
camera.position.set(3.2, 2.4, 5.2);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 2;
controls.maxDistance = 16;
controls.target.set(0, 1, 0);

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// ---------- Crate (carried prop, held between the hands) ----------

function crateTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  g.fillStyle = "#a8743f";
  g.fillRect(0, 0, 128, 128);
  g.strokeStyle = "#6b4423";
  g.lineWidth = 12;
  g.strokeRect(6, 6, 116, 116);
  g.lineWidth = 8;
  g.beginPath();
  g.moveTo(10, 10);
  g.lineTo(118, 118);
  g.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const crate = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.42, 0.42), new THREE.MeshStandardMaterial({ map: crateTexture(), roughness: 0.9 }));
crate.castShadow = true;
crate.position.set(1.4, 0.21, -0.6);
scene.add(crate);

// ---------- Character ----------

const status = document.getElementById("status")!;
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const gltf = await loader.loadAsync(`${import.meta.env.BASE_URL}models/rootwarden.glb`);
const hero = gltf.scene;
hero.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) o.castShadow = true;
});
scene.add(hero);
const hands = [hero.getObjectByName("handL")!, hero.getObjectByName("handR")!];
const materials: THREE.MeshStandardMaterial[] = [];
hero.traverse((o) => {
  const m = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined;
  if (m?.emissive) materials.push(m);
});

const mixer = new THREE.AnimationMixer(hero);
const actions = Object.fromEntries(gltf.animations.map((clip) => [clip.name, mixer.clipAction(clip)]));
for (const name of ["jump_start", "jump_land", ...HITS, ...ATTACKS]) {
  actions[name].setLoop(THREE.LoopOnce, 1);
  actions[name].clampWhenFinished = true;
}

let current = actions.idle;
current.play();
function fadeTo(name: string, restart = false, fade = FADE, startAt = 0) {
  const next = actions[name];
  if (next === current && !restart) return;
  next.reset().setEffectiveWeight(1).play();
  next.time = startAt;
  current.crossFadeTo(next, fade, false);
  current = next;
}

// ---------- State ----------

const keys = new Set<string>();
let carrying = false;
let oneShot: string | null = null; // Hit / Attack / landing while it plays
let jump: "start" | "air" | null = null;
let jumpTime = 0;
let vy = 0;
let attackIndex = 0;
let preview: "Walk" | "Run" | null = null; // in-place locomotion from the buttons
let heading = 0;
let flash = 0;

function locomotion(moving: boolean, running: boolean) {
  if (carrying) return moving ? "carry_walk" : "carry_idle";
  return moving ? (running ? "run" : "walk") : "idle";
}

function play(shot: "Jump" | "Hit" | "Attack") {
  if (shot === "Jump") {
    if (jump || oneShot) return;
    jump = "start";
    jumpTime = 0;
    fadeTo("jump_start", true, 0.08);
    return;
  }
  if (jump || ATTACKS.includes(oneShot ?? "")) return;
  if (shot === "Attack") {
    if (carrying) return;
    oneShot = ATTACKS[attackIndex++ % ATTACKS.length];
    fadeTo(oneShot, true, 0.1);
  } else {
    oneShot = HITS[Math.floor(Math.random() * HITS.length)];
    fadeTo(oneShot, true, 0.06);
    damage();
  }
}

mixer.addEventListener("finished", (e) => {
  if (e.action === actions[oneShot ?? ""]) oneShot = null;
});

function updateJump(dt: number) {
  if (!jump) return;
  jumpTime += dt;
  if (jump === "start" && jumpTime >= TAKEOFF) {
    jump = "air";
    vy = JUMP_SPEED;
  }
  if (jump !== "air") return;
  vy -= GRAVITY * dt;
  hero.position.y += vy * dt;
  if (current === actions.jump_start && jumpTime > 0.5) fadeTo("jump_loop", false, 0.25);
  if (hero.position.y <= 0) {
    hero.position.y = 0;
    jump = null;
    oneShot = "jump_land";
    fadeTo("jump_land", true, 0.08, 0.05);
    setTimeout(() => oneShot === "jump_land" && (oneShot = null), 600);
  }
}

function toggleCarry() {
  if (oneShot || jump) return;
  carrying = !carrying;
  if (!carrying) {
    crate.position.y = 0.21;
    crate.rotation.set(0, heading, 0);
  }
  syncButtons();
}

// The library's carry clip holds the load between the palms, so the crate follows the hands
const handL = new THREE.Vector3();
const handR = new THREE.Vector3();
function holdCrate() {
  hands[0].getWorldPosition(handL);
  hands[1].getWorldPosition(handR);
  crate.position.copy(handL).add(handR).multiplyScalar(0.5);
  crate.position.x += Math.sin(heading) * 0.08; // clear of the Rootwarden's belly
  crate.position.z += Math.cos(heading) * 0.08;
  crate.rotation.set(0, heading, 0);
}

function damage() {
  flash = 1;
  const el = document.createElement("div");
  el.className = "float";
  el.textContent = `-${10 + Math.floor(Math.random() * 15)}`;
  const head = new THREE.Vector3();
  hero.getObjectByName("head")!.getWorldPosition(head);
  head.y += 0.5;
  head.project(camera);
  el.style.left = `${((head.x + 1) / 2) * innerWidth}px`;
  el.style.top = `${((1 - head.y) / 2) * innerHeight}px`;
  document.body.append(el);
  requestAnimationFrame(() => {
    el.style.transform = "translateY(-50px)";
    el.style.opacity = "0";
  });
  setTimeout(() => el.remove(), 1000);
}

// ---------- Input ----------

addEventListener("keydown", (e) => {
  const k = e.key.toLowerCase();
  if (e.repeat) return;
  if (k === " ") play("Jump");
  else if (k === "f") play("Attack");
  else if (k === "h") play("Hit");
  else if (k === "c") toggleCarry();
  else {
    keys.add(k);
    if ("wasd".includes(k) || k.startsWith("arrow")) preview = null, syncButtons();
  }
});
addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
addEventListener("blur", () => keys.clear());

const buttons = [...document.querySelectorAll<HTMLButtonElement>("#clips button")];
for (const b of buttons) {
  b.addEventListener("click", () => {
    if (b.dataset.loco) preview = preview === b.dataset.loco ? null : (b.dataset.loco as "Walk" | "Run");
    else if (b.dataset.shot) play(b.dataset.shot as "Jump" | "Hit" | "Attack");
    else toggleCarry();
    syncButtons();
  });
}
function syncButtons() {
  for (const b of buttons) b.classList.toggle("on", b.dataset.loco ? preview === b.dataset.loco : b.hasAttribute("data-carry") && carrying);
}

// ---------- Loop ----------

const clock = new THREE.Clock();
const move = new THREE.Vector3();
const fwd = new THREE.Vector3();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);

  camera.getWorldDirection(fwd);
  fwd.y = 0;
  fwd.normalize();
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
  move.set(0, 0, 0);
  if (keys.has("w") || keys.has("arrowup")) move.add(fwd);
  if (keys.has("s") || keys.has("arrowdown")) move.sub(fwd);
  if (keys.has("d") || keys.has("arrowright")) move.add(right);
  if (keys.has("a") || keys.has("arrowleft")) move.sub(right);
  const steering = move.lengthSq() > 0;
  const running = keys.has("shift") || preview === "Run";
  const loco = locomotion(steering || preview !== null, running);

  // Hits, attacks and landings root the character; jumps keep their momentum
  const canMove = oneShot === null;
  if (steering && canMove) {
    move.normalize();
    const target = Math.atan2(move.x, move.z);
    let d = target - heading;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    heading += d * Math.min(1, dt * 10);
    const speed = SPEED[loco as keyof typeof SPEED] ?? 0;
    hero.position.addScaledVector(move, speed * dt);
  }
  hero.rotation.y = heading;
  updateJump(dt);
  if (!oneShot && !jump) fadeTo(loco);

  mixer.update(dt);
  if (carrying) holdCrate();

  flash = Math.max(0, flash - dt * 3);
  for (const m of materials) m.emissive.setRGB(flash * 0.8, 0, 0);

  const delta = hero.position.clone().setY(0).sub(sun.target.position);
  sun.target.position.add(delta);
  sun.position.add(delta);
  controls.target.lerp(new THREE.Vector3(hero.position.x, 1 + hero.position.y * 0.5, hero.position.z), 0.1);
  camera.position.add(delta.multiplyScalar(0.9));
  controls.update();

  status.innerHTML = `<b>Clip</b>${current.getClip().name}<br><b>Carrying</b>${carrying ? "yes" : "no"}`;
  renderer.render(scene, camera);
});
