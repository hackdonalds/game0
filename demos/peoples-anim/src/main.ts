import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const PEOPLES = ["anchorkin", "rootwarden", "galeborne"];
const CLIPS: [string, string][] = [
  ["idle", "Idle"], ["walk", "Walk"], ["run", "Run"], ["jump_short", "Jump"], ["punch_combo_2", "Punch"],
  ["parry", "Block"], ["hit_reaction_0", "Hit"], ["roll_dodge_1", "Dodge roll"], ["wave", "Wave"], ["dying_backwards", "Death"],
];
const SPACING = 1.9;
const MODELS = `${import.meta.env.BASE_URL}models/`;

// ---------- Scene ----------

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.prepend(renderer.domElement);

const SKY = new THREE.Color(0x9cc3e6);
const scene = new THREE.Scene();
scene.background = SKY;
scene.fog = new THREE.Fog(SKY, 16, 42);
scene.add(new THREE.HemisphereLight(0xfff4dc, 0x5a7f8f, 2));
const sun = new THREE.DirectionalLight(0xffd79a, 2.4);
sun.position.set(3, 7, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -5, right: 5, top: 4, bottom: -4 });
scene.add(sun, sun.target);

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 100);
camera.position.set(1.2, 2.3, 7.4);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.95, 0);
controls.maxPolarAngle = Math.PI * 0.49;
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

/** One ground lane per character, so each can scroll at its own speed. */
function lane(x: number, shade: number) {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  g.fillStyle = `hsl(88, 40%, ${48 + shade}%)`;
  g.fillRect(0, 0, 64, 64);
  g.fillStyle = `hsl(88, 40%, ${42 + shade}%)`;
  g.fillRect(0, 0, 32, 32);
  g.fillRect(32, 32, 32, 32);
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.magFilter = THREE.NearestFilter;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.repeat.set(1, 30);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(SPACING, 60), new THREE.MeshStandardMaterial({ map: tex, roughness: 1 }));
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.x = x;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return tex;
}

// ---------- Characters ----------

type Person = { mixer: THREE.AnimationMixer; actions: Record<string, THREE.AnimationAction>; speeds: Record<string, number>; ground: THREE.CanvasTexture; label: HTMLElement; root: THREE.Object3D };
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const people: Person[] = await Promise.all(
  PEOPLES.map(async (name, i) => {
    const x = (i - 1) * SPACING;
    const [gltf, clips] = await Promise.all([
      loader.loadAsync(`${MODELS}${name}.glb`),
      fetch(`${MODELS}${name}.clips.json`).then((r) => r.json()),
    ]);
    gltf.scene.position.x = x;
    gltf.scene.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = true;
    });
    scene.add(gltf.scene);
    const mixer = new THREE.AnimationMixer(gltf.scene);
    const actions = Object.fromEntries(gltf.animations.map((c) => [c.name, mixer.clipAction(c)]));
    const speeds = Object.fromEntries(Object.entries(clips as Record<string, { speed: number }>).map(([k, v]) => [k, v.speed]));
    const label = Object.assign(document.createElement("div"), { className: "label" });
    document.body.append(label);
    return { mixer, actions, speeds, ground: lane(x, i % 2 ? 3 : 0), label, root: gltf.scene };
  }),
);

// ---------- Clip switching ----------

const bar = document.getElementById("clips")!;
const buttons = CLIPS.map(([id, label]) => {
  const b = Object.assign(document.createElement("button"), { textContent: label });
  b.onclick = () => play(id);
  bar.append(b);
  return b;
});
let current = "";
let loops = true;

function play(id: string) {
  current = id;
  buttons.forEach((b, i) => b.classList.toggle("on", CLIPS[i][0] === id));
  const once = ["jump_short", "punch_combo_2", "parry", "hit_reaction_0", "roll_dodge_1", "wave", "dying_backwards"].includes(id);
  loops = !once;
  for (const p of people) {
    const next = p.actions[id];
    next.reset();
    next.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    next.clampWhenFinished = true;
    next.play();
    for (const a of Object.values(p.actions)) if (a !== next && a.isRunning()) a.crossFadeTo(next, 0.25, false);
    const name = PEOPLES[people.indexOf(p)];
    const speed = p.speeds[id];
    p.label.innerHTML = `${name[0].toUpperCase()}${name.slice(1)}<small>${speed ? `${speed.toFixed(2)} m/s` : "&nbsp;"}</small>`;
  }
}

// One-shots replay together after a pause, so all three stay in step
let replay: ReturnType<typeof setTimeout> | undefined;
for (const p of people)
  p.mixer.addEventListener("finished", () => {
    if (loops) return;
    clearTimeout(replay);
    replay = setTimeout(() => !loops && play(current), 900);
  });

addEventListener("keydown", (e) => {
  if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
  const i = CLIPS.findIndex(([id]) => id === current);
  play(CLIPS[(i + (e.key === "ArrowRight" ? 1 : -1) + CLIPS.length) % CLIPS.length][0]);
});
play("walk");

// ---------- Loop ----------

const timer = new THREE.Timer();
const head = new THREE.Vector3();
renderer.setAnimationLoop((t) => {
  timer.update(t);
  const dt = Math.min(timer.getDelta(), 0.05);
  for (const p of people) {
    p.mixer.update(dt);
    // A lane is 60 m long with 30 texture repeats: 2 m per repeat; scroll backwards under the walker
    p.ground.offset.y -= ((p.speeds[current] ?? 0) * dt) / 2;
    head.set(p.root.position.x, 2.15, 0).project(camera);
    p.label.style.left = `${((head.x + 1) / 2) * innerWidth}px`;
    p.label.style.top = `${((1 - head.y) / 2) * innerHeight}px`;
  }
  controls.update();
  renderer.render(scene, camera);
});
