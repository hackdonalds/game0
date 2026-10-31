import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import GUI from "lil-gui";

type Option = { file: string; position: [number, number, number]; rotation: [number, number, number]; scale: number };
type Config = { base: { file: string; walk?: string }; slots: Record<string, { bone: string; options: Record<string, Option> }> };

const MODELS = `${import.meta.env.BASE_URL}models/`;
const loader = new GLTFLoader();
const load = (file: string) => loader.loadAsync(MODELS + file);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.append(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1c2a26);
scene.add(new THREE.HemisphereLight(0xfff3d6, 0x2a4a44, 2));
const sun = new THREE.DirectionalLight(0xffe2a8, 2.5);
sun.position.set(2, 4, 3);
scene.add(sun);
const ground = new THREE.Mesh(new THREE.CircleGeometry(1.2, 48), new THREE.MeshStandardMaterial({ color: 0x4f6b45 }));
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.05, 50);
camera.position.set(0.8, 1.6, 3.6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1, 0);
controls.enableDamping = true;

// Meshy's API rig names bones "Head", "Spine02"; its web rig exports Mixamo names ("mixamorig:Head", "Spine2"),
// which GLTFLoader sanitises to "mixamorigHead". attachments.json uses the Meshy names.
const BONE_ALIASES: Record<string, string> = { Spine02: "Spine2", Spine01: "Spine1" };
function findBone(root: THREE.Object3D, name: string) {
  const candidates = [name, `mixamorig${name}`, `mixamorig${BONE_ALIASES[name] ?? name}`, BONE_ALIASES[name]];
  for (const c of candidates) {
    const bone = c && root.getObjectByName(c);
    if (bone) return bone;
  }
  throw new Error(`Bone ${name} not found`);
}

function applyTransform(object: THREE.Object3D, o: Option) {
  object.position.fromArray(o.position);
  object.rotation.set(...(o.rotation.map(THREE.MathUtils.degToRad) as [number, number, number]));
  object.scale.setScalar(o.scale);
}

const partCache = new Map<string, THREE.Object3D>();
let cfg: Config;
let character: THREE.Object3D | undefined;
let mixer: THREE.AnimationMixer | undefined;
let clips: THREE.AnimationClip[] = [];
let sockets: Record<string, THREE.Object3D> = {};
let mounted: Record<string, { object: THREE.Object3D; option: Option } | undefined> = {};

const peoples: string[] = await (await fetch(MODELS + "peoples.json")).json();
const state: Record<string, any> = { people: peoples.includes("skerrin") ? "skerrin" : peoples[0], animation: "none", turntable: false };
const gui = new GUI({ title: "Peoples" });
gui.add(state, "people", peoples).onChange(loadPeople);
let slotFolder = gui.addFolder("Customize");
let fitFolder = gui.addFolder("Fit (dev)").close();
let animController: ReturnType<GUI["add"]> | undefined;
gui.add(state, "turntable");

async function loadPeople(people: string) {
  document.body.classList.add("loading");
  cfg = await (await fetch(`${MODELS}${people}/attachments.json`)).json();
  const base = await load(cfg.base.file);

  character?.removeFromParent();
  mixer?.stopAllAction();
  character = base.scene;
  scene.add(character);
  const box = new THREE.Box3().setFromObject(character);
  character.position.y -= box.min.y;

  mixer = new THREE.AnimationMixer(character);
  clips = [...base.animations];
  if (cfg.base.walk) clips.push(...(await load(cfg.base.walk)).animations);

  character.updateMatrixWorld(true);
  sockets = {};
  mounted = {};
  for (const [slot, { bone: boneName }] of Object.entries(cfg.slots)) {
    const bone = findBone(character, boneName);
    // The socket cancels the bone's world scale, so offsets in attachments.json are in metres
    const socket = new THREE.Object3D();
    const s = bone.getWorldScale(new THREE.Vector3());
    socket.scale.set(1 / s.x, 1 / s.y, 1 / s.z);
    bone.add(socket);
    sockets[slot] = socket;
  }

  slotFolder.destroy();
  slotFolder = gui.addFolder("Customize");
  for (const slot of Object.keys(cfg.slots)) {
    const names = Object.keys(cfg.slots[slot].options);
    state[slot] = names[0];
    slotFolder.add(state, slot, ["none", ...names]).onChange((v: string) => equip(slot, v));
  }
  animController?.destroy();
  state.animation = clips.find((c) => /idle/i.test(c.name))?.name ?? "none";
  animController = gui.add(state, "animation", ["none", ...clips.map((c) => c.name)]).onChange(play);
  play(state.animation);

  await Promise.all(Object.keys(cfg.slots).map((slot) => equip(slot, state[slot])));
  document.body.classList.remove("loading");
}

function play(name: string) {
  mixer?.stopAllAction();
  const clip = clips.find((c) => c.name === name);
  if (clip) mixer?.clipAction(clip).reset().play();
}

async function equip(slot: string, name: string) {
  mounted[slot]?.object.removeFromParent();
  mounted[slot] = undefined;
  if (name !== "none") {
    const option = cfg.slots[slot].options[name];
    let object = partCache.get(option.file);
    if (!object) {
      object = (await load(option.file)).scene;
      partCache.set(option.file, object);
    }
    applyTransform(object, option);
    sockets[slot].add(object);
    mounted[slot] = { object, option };
  }
  refreshFit();
}

// Fit panel: tune offsets for the mounted parts, then paste the copied JSON into art/models/<people>/attachments.json
function refreshFit() {
  fitFolder.destroy();
  fitFolder = gui.addFolder("Fit (dev)").close();
  for (const [slot, m] of Object.entries(mounted)) {
    if (!m) continue;
    const f = fitFolder.addFolder(slot);
    const o = m.option;
    const update = () => applyTransform(m.object, o);
    ["x", "y", "z"].forEach((axis, i) => f.add(o.position, i as any, -0.6, 0.6, 0.005).name(`pos ${axis}`).onChange(update));
    ["x", "y", "z"].forEach((axis, i) => f.add(o.rotation, i as any, -180, 180, 1).name(`rot ${axis}`).onChange(update));
    f.add(o, "scale", 0.01, 1.5, 0.005).onChange(update);
  }
  fitFolder.add({ copy: () => { const json = JSON.stringify(cfg, null, 2); console.log(json); navigator.clipboard?.writeText(json); } }, "copy").name("copy attachments.json");
}

await loadPeople(state.people);
document.getElementById("loading")?.remove();
if (import.meta.env.DEV) Object.assign(window, { fitDebug: { get mounted() { return mounted; }, applyTransform, get cfg() { return cfg; }, camera, controls, play, loadPeople } });

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  mixer?.update(dt);
  if (state.turntable && character) character.rotation.y += dt * 0.5;
  controls.update();
  renderer.render(scene, camera);
});
