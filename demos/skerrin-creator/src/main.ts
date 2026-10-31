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
camera.position.set(0.8, 1.6, 3.2);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.1, 0);
controls.enableDamping = true;

const cfg: Config = await (await fetch(MODELS + "attachments.json")).json();
const base = await load(cfg.base.file);
const character = base.scene;
scene.add(character);

// Stand the character on the ground regardless of the rig's origin
const box = new THREE.Box3().setFromObject(character);
character.position.y -= box.min.y;

const mixer = new THREE.AnimationMixer(character);
const walkClip = cfg.base.walk ? (await load(cfg.base.walk)).animations[0] : undefined;
const walk = walkClip ? mixer.clipAction(walkClip) : undefined;

// A socket under each bone cancels the bone's world scale, so offsets in attachments.json are in metres
character.updateMatrixWorld(true);
const sockets: Record<string, THREE.Object3D> = {};
for (const [slot, { bone: boneName }] of Object.entries(cfg.slots)) {
  const bone = character.getObjectByName(boneName);
  if (!bone) throw new Error(`Bone ${boneName} not found`);
  const socket = new THREE.Object3D();
  const s = bone.getWorldScale(new THREE.Vector3());
  socket.scale.set(1 / s.x, 1 / s.y, 1 / s.z);
  bone.add(socket);
  sockets[slot] = socket;
}

const partCache = new Map<string, THREE.Object3D>();
const mounted: Record<string, { object: THREE.Object3D; option: Option } | undefined> = {};

function applyTransform(object: THREE.Object3D, o: Option) {
  object.position.fromArray(o.position);
  object.rotation.set(...(o.rotation.map(THREE.MathUtils.degToRad) as [number, number, number]));
  object.scale.setScalar(o.scale);
}

async function equip(slot: string, name: string) {
  mounted[slot]?.object.removeFromParent();
  mounted[slot] = undefined;
  if (name === "none") return refreshFit();
  const option = cfg.slots[slot].options[name];
  let object = partCache.get(option.file);
  if (!object) {
    object = (await load(option.file)).scene;
    partCache.set(option.file, object);
  }
  applyTransform(object, option);
  sockets[slot].add(object);
  mounted[slot] = { object, option };
  refreshFit();
}

const state = { horns: "ram", hand: "pickaxe", walk: false, rotate: false };
const gui = new GUI({ title: "Skerrin" });
for (const slot of Object.keys(cfg.slots)) {
  gui.add(state, slot as "horns" | "hand", ["none", ...Object.keys(cfg.slots[slot].options)]).onChange((v: string) => equip(slot, v));
}
gui.add(state, "walk").name("walk cycle").onChange((on: boolean) => (on ? walk?.reset().play() : walk?.stop()));
gui.add(state, "rotate").name("turntable");

// Fit panel: tune offsets for the mounted parts, then copy the JSON back into art/models/<people>/attachments.json
const fit = gui.addFolder("Fit (dev)").close();
function refreshFit() {
  for (const c of [...fit.children]) c.destroy();
  for (const [slot, m] of Object.entries(mounted)) {
    if (!m) continue;
    const f = fit.addFolder(slot);
    const o = m.option;
    const update = () => applyTransform(m.object, o);
    ["x", "y", "z"].forEach((axis, i) => f.add(o.position, i as any, -0.5, 0.5, 0.005).name(`pos ${axis}`).onChange(update));
    ["x", "y", "z"].forEach((axis, i) => f.add(o.rotation, i as any, -180, 180, 1).name(`rot ${axis}`).onChange(update));
    f.add(o, "scale", 0.01, 1, 0.005).onChange(update);
  }
  fit.add({ copy: () => { const json = JSON.stringify(cfg, null, 2); console.log(json); navigator.clipboard?.writeText(json); } }, "copy").name("copy attachments.json");
}

await Promise.all(Object.entries(state).filter(([k]) => k in cfg.slots).map(([slot, v]) => equip(slot, v as string)));
document.getElementById("loading")?.remove();
if (import.meta.env.DEV) Object.assign(window, { fitDebug: { mounted, applyTransform, cfg } });

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  mixer.update(dt);
  if (state.rotate) character.rotation.y += dt * 0.5;
  controls.update();
  renderer.render(scene, camera);
});
