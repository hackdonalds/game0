import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
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
const state: Record<string, any> = { people: peoples.includes("rootwarden") ? "rootwarden" : peoples[0], animation: "none", turntable: false };
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

// Gizmo: drag a mounted part by hand; changes are written back into its attachments.json option
const gizmo = new TransformControls(camera, renderer.domElement);
gizmo.setSize(0.8);
scene.add(gizmo.getHelper());
gizmo.addEventListener("dragging-changed", (e) => (controls.enabled = !e.value));
gizmo.addEventListener("objectChange", () => {
  const m = Object.values(mounted).find((x) => x?.object === gizmo.object);
  if (!m) return;
  const { object, option } = m;
  if (gizmo.mode === "scale") {
    // Keep scale uniform: take whichever axis the user dragged
    const s = object.scale.toArray().reduce((a, b) => (Math.abs(b - option.scale) > Math.abs(a - option.scale) ? b : a));
    object.scale.setScalar(s);
  }
  // Update the arrays in place: the Fit sliders are bound to them
  object.position.toArray().forEach((v, i) => (option.position[i] = +v.toFixed(3)));
  [object.rotation.x, object.rotation.y, object.rotation.z].forEach((r, i) => (option.rotation[i] = +THREE.MathUtils.radToDeg(r).toFixed(1)));
  option.scale = +object.scale.x.toFixed(3);
  fitFolder.controllersRecursive().forEach((c) => c.updateDisplay());
});
const gizmoState = { target: "off", mode: "translate" as "translate" | "rotate" | "scale", space: "local" as "local" | "world" };

function attachGizmo() {
  const m = mounted[gizmoState.target];
  if (m) gizmo.attach(m.object);
  else gizmo.detach();
  gizmo.setMode(gizmoState.mode);
  gizmo.setSpace(gizmoState.space);
}

addEventListener("keydown", (e) => {
  if ((e.target as HTMLElement).tagName === "INPUT") return;
  const modes: Record<string, typeof gizmoState.mode> = { w: "translate", e: "rotate", r: "scale" };
  if (modes[e.key]) gizmoState.mode = modes[e.key];
  else if (e.key === "q") gizmoState.space = gizmoState.space === "local" ? "world" : "local";
  else return;
  attachGizmo();
  fitFolder.controllersRecursive().forEach((c) => c.updateDisplay());
});

// Fit panel: tune offsets for the mounted parts, then paste the copied JSON into art/models/<people>/attachments.json
function refreshFit() {
  const wasOpen = !fitFolder._closed;
  fitFolder.destroy();
  fitFolder = gui.addFolder("Fit (dev)");
  if (!wasOpen) fitFolder.close();

  const slots = Object.keys(mounted).filter((s) => mounted[s]);
  if (!slots.includes(gizmoState.target)) gizmoState.target = "off";
  fitFolder.add({ copy: () => { const json = JSON.stringify(cfg, null, 2); console.log(json); navigator.clipboard?.writeText(json); } }, "copy").name("copy attachments.json");
  const g = fitFolder.addFolder("gizmo · keys W E R Q");
  // Picking a part collapses the other parts' sliders so the selected one stays on screen
  g.add(gizmoState, "target", ["off", ...slots]).name("part").onChange(() => { attachGizmo(); focusPart(); });
  g.add(gizmoState, "mode", ["translate", "rotate", "scale"]).onChange(attachGizmo);
  g.add(gizmoState, "space", ["local", "world"]).onChange(attachGizmo);

  const partFolders: Record<string, GUI> = {};
  const focusPart = () => {
    for (const [slot, f] of Object.entries(partFolders)) f.open(gizmoState.target === "off" || slot === gizmoState.target);
  };
  for (const slot of slots) {
    const m = mounted[slot]!;
    const f = (partFolders[slot] = fitFolder.addFolder(slot));
    const o = m.option;
    const update = () => applyTransform(m.object, o);
    ["x", "y", "z"].forEach((axis, i) => f.add(o.position, i as any, -0.6, 0.6, 0.005).name(`pos ${axis}`).onChange(update));
    ["x", "y", "z"].forEach((axis, i) => f.add(o.rotation, i as any, -180, 180, 1).name(`rot ${axis}`).onChange(update));
    f.add(o, "scale", 0.01, 3, 0.005).onChange(update);
  }
  focusPart();
  attachGizmo();
}

await loadPeople(state.people);
document.getElementById("loading")?.remove();
// Dev-only fitting helper: give the offset (metres) and rotation (degrees) in world axes for the bind pose
// (+Y up, +Z the character's front, -X its right), and it stores the equivalent bone-local values.
function fitWorld(slot: string, offset: [number, number, number], euler: [number, number, number], scale: number) {
  const m = mounted[slot];
  if (!m) throw new Error(`${slot} not mounted`);
  const inv = m.object.parent!.getWorldQuaternion(new THREE.Quaternion()).invert();
  const world = new THREE.Quaternion().setFromEuler(new THREE.Euler(...(euler.map(THREE.MathUtils.degToRad) as [number, number, number])));
  const local = new THREE.Euler().setFromQuaternion(inv.clone().multiply(world));
  m.option.position = new THREE.Vector3(...offset).applyQuaternion(inv).toArray().map((v) => +v.toFixed(3)) as Option["position"];
  m.option.rotation = [local.x, local.y, local.z].map((r) => Math.round(THREE.MathUtils.radToDeg(r))) as Option["rotation"];
  m.option.scale = scale;
  applyTransform(m.object, m.option);
  return m.option;
}

if (import.meta.env.DEV) Object.assign(window, { fitDebug: { get mounted() { return mounted; }, applyTransform, get cfg() { return cfg; }, camera, controls, play, loadPeople, fitWorld } });

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
