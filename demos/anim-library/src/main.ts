import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

type Entry = {
  id: string; name: string; set: string; tags: string[]; variantOf?: string; loop: boolean; speed: number;
  frames: number; fps: number; source: string; sourceClip: string; upperSource?: string; license: string; note?: string;
};
const BASE = `${import.meta.env.BASE_URL}biped/`;
const SET_ORDER = ["idle", "locomotion", "social", "combat", "ranged", "magic", "reaction", "death", "monster"];

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
scene.fog = new THREE.Fog(SKY, 14, 40);
scene.add(new THREE.HemisphereLight(0xfff4dc, 0x5a7f8f, 2));
const sun = new THREE.DirectionalLight(0xffd79a, 2.4);
sun.position.set(3, 7, 4);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
Object.assign(sun.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3 });
scene.add(sun, sun.target);

// The ground scrolls under the character instead of the character walking away
const tile = document.createElement("canvas");
tile.width = tile.height = 64;
const g = tile.getContext("2d")!;
g.fillStyle = "#8fbf5a";
g.fillRect(0, 0, 64, 64);
g.fillStyle = "#7fae4c";
g.fillRect(0, 0, 32, 32);
g.fillRect(32, 32, 32, 32);
const groundTex = new THREE.CanvasTexture(tile);
groundTex.wrapS = groundTex.wrapT = THREE.RepeatWrapping;
groundTex.magFilter = THREE.NearestFilter;
groundTex.colorSpace = THREE.SRGBColorSpace;
groundTex.repeat.set(40, 40);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ map: groundTex, roughness: 1 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 100);
camera.position.set(3.4, 2.1, 4.6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.95, 0);
controls.maxPolarAngle = Math.PI * 0.49;
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// ---------- Library ----------

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const catalog: Entry[] = await (await fetch(`${BASE}catalog.json`)).json();
const body = await loader.loadAsync(`${BASE}reference.glb`);
body.scene.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) o.castShadow = true;
});
scene.add(body.scene);
const mixer = new THREE.AnimationMixer(body.scene);

const sets = [...new Set(catalog.map((e) => e.set))].sort((a, b) => SET_ORDER.indexOf(a) - SET_ORDER.indexOf(b));
const clips = new Map<string, THREE.AnimationClip>();
const loading = new Map<string, Promise<void>>();
function loadSet(set: string) {
  if (!loading.has(set))
    loading.set(set, loader.loadAsync(`${BASE}clips/${set}.glb`).then((gltf) => gltf.animations.forEach((c) => clips.set(c.name, c))));
  return loading.get(set)!;
}

// ---------- UI ----------

const list = document.getElementById("clips")!;
const search = document.getElementById("search") as HTMLInputElement;
const title = document.getElementById("title")!;
const meta = document.getElementById("meta")!;
const move = document.getElementById("move") as HTMLInputElement;
const slow = document.getElementById("slow") as HTMLInputElement;
let shown: Entry[] = [];
let selected: Entry | null = null;
let action: THREE.AnimationAction | null = null;

function render() {
  const q = search.value.trim().toLowerCase();
  shown = catalog
    .filter((e) => !q || [e.id, e.name, e.set, e.source, ...e.tags].join(" ").toLowerCase().includes(q))
    .sort((a, b) => SET_ORDER.indexOf(a.set) - SET_ORDER.indexOf(b.set));
  list.replaceChildren();
  for (const set of sets) {
    const items = shown.filter((e) => e.set === set);
    if (!items.length) continue;
    const h = document.createElement("h2");
    h.textContent = `${set} · ${items.length}`;
    list.append(h);
    for (const e of items) {
      const b = document.createElement("button");
      b.dataset.id = e.id;
      b.className = e === selected ? "on" : "";
      b.innerHTML = `<span></span><small>${e.loop ? "loop" : `${(e.frames / e.fps).toFixed(1)} s`}</small>`;
      b.firstElementChild!.textContent = e.name;
      b.onclick = () => select(e);
      list.append(b);
    }
  }
}

async function select(e: Entry) {
  selected = e;
  for (const b of list.querySelectorAll<HTMLButtonElement>("button")) b.classList.toggle("on", b.dataset.id === e.id);
  list.querySelector(`[data-id="${e.id}"]`)?.scrollIntoView({ block: "nearest" });
  title.textContent = e.name;
  const rows: [string, string][] = [
    ["id", e.id],
    ["set", e.set + (e.variantOf ? ` (variant of ${e.variantOf})` : "")],
    ["length", `${e.frames} frames, ${(e.frames / e.fps).toFixed(2)} s${e.loop ? ", loops" : ""}`],
    ["speed", e.speed ? `${e.speed} m/s` : "in place"],
    ["source", `${e.source}: ${e.sourceClip}${e.upperSource ? ` + upper body from ${e.upperSource}` : ""}`],
    ["licence", e.license],
  ];
  meta.replaceChildren(...rows.flatMap(([k, v]) => [Object.assign(document.createElement("dt"), { textContent: k }), Object.assign(document.createElement("dd"), { textContent: v })]));
  document.querySelector("#info .note")?.remove();
  if (e.note) meta.after(Object.assign(document.createElement("p"), { className: "note", textContent: e.note }));
  await loadSet(e.set);
  if (selected !== e) return;
  const next = mixer.clipAction(clips.get(e.id)!);
  next.reset();
  next.setLoop(e.loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  next.clampWhenFinished = true;
  next.play();
  if (action && action !== next) action.crossFadeTo(next, 0.2, false);
  action = next;
}

// One-shots replay after a short pause so they can be watched more than once
mixer.addEventListener("finished", (ev) => {
  const a = ev.action as THREE.AnimationAction;
  setTimeout(() => a === action && a.reset().play(), 700);
});

search.addEventListener("input", render);
addEventListener("keydown", (ev) => {
  if (ev.target === search || !shown.length || !["ArrowDown", "ArrowUp"].includes(ev.key)) return;
  ev.preventDefault();
  const i = selected ? shown.indexOf(selected) : -1;
  select(shown[(i + (ev.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length]);
});
render();
select(catalog.find((e) => e.id === "walk") ?? catalog[0]);
sets.forEach(loadSet); // warm the rest in the background

// ---------- Loop ----------

const clock = new THREE.Timer();
renderer.setAnimationLoop((t) => {
  clock.update(t);
  const dt = Math.min(clock.getDelta(), 0.05) * (slow.checked ? 0.5 : 1);
  mixer.update(dt);
  // Clips face +Z; scroll the ground backwards at the clip's ground speed
  if (move.checked && selected?.speed) groundTex.offset.y -= (selected.speed * dt * 40) / 80;
  controls.update();
  renderer.render(scene, camera);
});
