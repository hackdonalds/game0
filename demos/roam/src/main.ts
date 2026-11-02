import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { createWorld } from "./world";

const MODELS = `${import.meta.env.BASE_URL}models/`;

// ---------- Renderer ----------

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 4000);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const [world, gltf] = await Promise.all([createWorld(scene, renderer), loader.loadAsync(`${MODELS}rootwarden.glb`)]);

// ---------- Character ----------

const hero = gltf.scene;
hero.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) o.castShadow = true;
});
scene.add(hero);
const mixer = new THREE.AnimationMixer(hero);
const actions = Object.fromEntries(gltf.animations.map((c) => [c.name, mixer.clipAction(c)]));
for (const id of ["idle", "walk", "run"]) actions[id].play().setEffectiveWeight(0);
const jump = actions.jump_short.setLoop(THREE.LoopOnce, 1);
jump.clampWhenFinished = true;

// Clip speeds come from the anim library catalog; the controller moves faster, so clips play faster to match
const WALK = 2.2;
const RUN = 6;
const CLIP_SPEED = { walk: 0.754 * 2, run: 4.144 };
const GRAVITY = 22;
const JUMP_V = 7.5;
const RADIUS = 0.4;

const pos = world.spawn.clone();
const vel = new THREE.Vector3();
let yaw = 0; // facing, radians; 0 faces +Z
let grounded = true;
let airborne = 0;
let jumping = false;

// ---------- Input ----------

const keys = new Set<string>();
addEventListener("keydown", (e) => {
  keys.add(e.code);
  if (e.code === "Space") e.preventDefault();
});
addEventListener("keyup", (e) => keys.delete(e.code));
addEventListener("blur", () => keys.clear());

let camYaw = Math.PI; // camera sits behind the hero (looking towards +Z)
let camPitch = 0.28;
let camDist = 6.5;
let dragging = false;
const canvas = renderer.domElement;
canvas.addEventListener("pointerdown", (e) => {
  dragging = true;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointerup", () => (dragging = false));
canvas.addEventListener("pointermove", (e) => {
  if (!dragging && document.pointerLockElement !== canvas) return;
  camYaw -= e.movementX * 0.005;
  camPitch = THREE.MathUtils.clamp(camPitch + e.movementY * 0.004, -0.35, 1.2);
});
canvas.addEventListener("dblclick", () => canvas.requestPointerLock());
canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    camDist = THREE.MathUtils.clamp(camDist * (1 + e.deltaY * 0.001), 2.5, 18);
  },
  { passive: false },
);

// ---------- Movement ----------

const wish = new THREE.Vector3();
const weights = { idle: 1, walk: 0, run: 0 };

function ground(x: number, z: number) {
  return world.heightAt(x, z);
}

function step(dt: number) {
  const f = (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0) - (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0);
  const s = (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) - (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0);
  const running = keys.has("ShiftLeft") || keys.has("ShiftRight");
  // Movement is relative to the camera: forward is where the camera looks
  const fx = -Math.sin(camYaw), fz = -Math.cos(camYaw);
  wish.set(fx * f - fz * s, 0, fz * f + fx * s);
  const moving = wish.lengthSq() > 0;
  if (moving) wish.normalize();
  const speed = moving ? (running ? RUN : WALK) : 0;

  // Ease horizontal velocity; less control in the air
  const accel = grounded ? 12 : 3;
  vel.x += (wish.x * speed - vel.x) * Math.min(1, accel * dt);
  vel.z += (wish.z * speed - vel.z) * Math.min(1, accel * dt);
  if (moving) {
    const target = Math.atan2(wish.x, wish.z);
    let d = target - yaw;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    yaw += d * Math.min(1, 12 * dt);
  }

  if (grounded && keys.has("Space")) {
    vel.y = JUMP_V;
    grounded = false;
    airborne = 0;
    jumping = true;
    jump.reset().setEffectiveTimeScale(1.4).setEffectiveWeight(1).play();
    jump.time = 0.3; // skip the crouch so the leap matches the take-off
  }

  const nx = pos.x + vel.x * dt;
  const nz = pos.z + vel.z * dt;
  // Walls: refuse steps up steeper than a stair
  const gh = ground(nx, nz);
  if (gh === null || gh <= pos.y + 0.7 || !grounded) {
    pos.x = nx;
    pos.z = nz;
  } else {
    vel.x = vel.z = 0;
  }
  for (const c of world.colliders) {
    if (pos.y > c.top) continue;
    const dx = pos.x - c.x, dz = pos.z - c.z;
    const min = c.r + RADIUS;
    const d2 = dx * dx + dz * dz;
    if (d2 < min * min && d2 > 1e-6) {
      const d = Math.sqrt(d2);
      pos.x = c.x + (dx / d) * min;
      pos.z = c.z + (dz / d) * min;
    }
  }

  vel.y -= GRAVITY * dt;
  pos.y += vel.y * dt;
  const h = ground(pos.x, pos.z);
  if (h !== null && pos.y <= h + (grounded ? 0.5 : 0) && vel.y <= 0) {
    // Snap to ground when walking downhill; land when falling
    pos.y = h;
    vel.y = 0;
    if (jumping) jump.fadeOut(0.15);
    jumping = false;
    grounded = true;
  } else {
    grounded = false;
    airborne += dt;
  }
  if (pos.y < -70) {
    pos.copy(world.spawn);
    vel.set(0, 0, 0);
  }

  // Locomotion blend: idle / walk / run by horizontal speed
  const hs = Math.hypot(vel.x, vel.z);
  const target = { idle: 0, walk: 0, run: 0 };
  if (hs < 0.3) target.idle = 1;
  else if (hs < WALK + 0.5) target.walk = 1;
  else target.run = 1;
  const air = jumping && airborne > 0.05;
  for (const k of ["idle", "walk", "run"] as const) {
    weights[k] += (target[k] - weights[k]) * Math.min(1, 10 * dt);
    actions[k].setEffectiveWeight(air ? weights[k] * 0.15 : weights[k]);
  }
  actions.walk.setEffectiveTimeScale(THREE.MathUtils.clamp(hs / CLIP_SPEED.walk, 0.6, 1.8));
  actions.run.setEffectiveTimeScale(THREE.MathUtils.clamp(hs / CLIP_SPEED.run, 0.7, 1.6));

  hero.position.copy(pos);
  hero.rotation.y = yaw;
}

// ---------- Camera ----------

const look = new THREE.Vector3();
const want = new THREE.Vector3();
const shoulder = new THREE.Vector3();
function follow(dt: number) {
  // Over the shoulder: aim a little above the head and offset to the right
  shoulder.set(Math.cos(camYaw) * 0.6, 0, -Math.sin(camYaw) * 0.6);
  look.set(pos.x, pos.y + 1.6, pos.z).add(shoulder);
  const cp = Math.cos(camPitch);
  want.set(look.x + Math.sin(camYaw) * cp * camDist, look.y + Math.sin(camPitch) * camDist, look.z + Math.cos(camYaw) * cp * camDist);
  const gh = world.heightAt(want.x, want.z);
  if (gh !== null) want.y = Math.max(want.y, gh + 0.6);
  camera.position.lerp(want, 1 - Math.exp(-14 * dt));
  camera.lookAt(look);
}
follow(1);

// ---------- Loop ----------

document.body.classList.add("ready");
const timer = new THREE.Timer();
renderer.setAnimationLoop((t) => {
  timer.update(t);
  const dt = Math.min(timer.getDelta(), 1 / 20);
  step(dt);
  mixer.update(dt);
  follow(dt);
  world.update(dt, timer.getElapsed(), pos);
  renderer.render(scene, camera);
});
