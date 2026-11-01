import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

const MODELS = `${import.meta.env.BASE_URL}models/`;
const HORIZON = new THREE.Color(0xa9c9ee);
const ZENITH = new THREE.Color(0x3f73c9);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.append(renderer.domElement);

const scene = new THREE.Scene();
scene.background = HORIZON;
scene.fog = new THREE.Fog(HORIZON, 70, 420);

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 1500);
camera.position.set(-1.5, 8, 36);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0.8, -0.8, 0);
controls.enableDamping = true;
controls.minDistance = 14;
controls.maxDistance = 70;
controls.maxPolarAngle = 2.0;
controls.autoRotate = !reduceMotion;
controls.autoRotateSpeed = 0.35;
controls.addEventListener("start", () => (controls.autoRotate = false));

// Sky dome: zenith blue fading to the horizon (fog) colour
const sky = new THREE.Mesh(
  new THREE.SphereGeometry(1200, 32, 16),
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: { horizon: { value: HORIZON }, zenith: { value: ZENITH } },
    vertexShader: "varying vec3 vDir; void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: "uniform vec3 horizon; uniform vec3 zenith; varying vec3 vDir; void main() { gl_FragColor = vec4(mix(horizon, zenith, pow(clamp(vDir.y, 0.0, 1.0), 0.6)), 1.0); }",
  }),
);
scene.add(sky);

scene.add(new THREE.HemisphereLight(0xd6e6ff, 0x4a6b3a, 1.3));
const sun = new THREE.DirectionalLight(0xfff0d8, 3.2);
sun.position.set(-0.61, 0.67, 0.43).multiplyScalar(40);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -14, right: 14, top: 14, bottom: -14, near: 1, far: 100 });
sun.shadow.bias = -0.0005;
sun.shadow.normalBias = 0.03;
scene.add(sun);

// Waterfalls: streaks scrolling down the sheet, fading at the edges and the bottom.
// UV x runs across the fall, UV y from the bottom (0) to the lip (1).
const fallMaterial = new THREE.ShaderMaterial({
  transparent: true,
  depthWrite: false,
  side: THREE.DoubleSide,
  uniforms: { time: { value: 0 } },
  vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
  fragmentShader: `
    uniform float time;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
    }
    void main() {
      float down = 1.0 - vUv.y;
      float streak = noise(vec2(vUv.x * 26.0, down * 2.0 - time * 1.1)) * 0.65 + noise(vec2(vUv.x * 70.0, down * 6.0 - time * 2.0)) * 0.35;
      float foam = smoothstep(0.35, 0.75, streak);
      float edge = smoothstep(0.0, 0.2, min(vUv.x, 1.0 - vUv.x));
      float tail = 1.0 - smoothstep(0.65, 1.0, down);
      gl_FragColor = vec4(mix(vec3(0.55, 0.82, 0.92), vec3(1.0), foam), (0.45 + 0.55 * foam) * edge * tail);
    }`,
});

// Mist where each fall breaks up (volumes don't survive glTF export, so these are billboards)
const MIST: [number, number, number, number][] = [
  [1.82, -5.76, 8.55, 1.8],
  [1.74, -0.74, 8.17, 1.0],
  [6.31, -4.13, 5.25, 1.8],
  [6.01, -0.61, 5.0, 1.0],
];
function mistTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,0.9)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}
const mistMap = mistTexture();
const puffs: { sprite: THREE.Sprite; base: THREE.Vector3; phase: number; size: number }[] = [];

const isle = new THREE.Group();
scene.add(isle);
for (const [x, y, z, r] of MIST) {
  for (let i = 0; i < 7; i++) {
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: mistMap, transparent: true, depthWrite: false, opacity: 0.5 }));
    const base = new THREE.Vector3(x + (Math.random() - 0.5) * r, y + (Math.random() - 0.5) * r, z + (Math.random() - 0.5) * r);
    puffs.push({ sprite, base, phase: Math.random(), size: r * (1.6 + Math.random()) });
    isle.add(sprite);
  }
}

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const [island, backdrop] = await Promise.all([
  loader.loadAsync(MODELS + "floating-island.glb"),
  loader.loadAsync(MODELS + "sky-backdrop.glb"),
]);

island.scene.traverse((o) => {
  if (!(o instanceof THREE.Mesh)) return;
  const name = (o.material as THREE.Material).name;
  if (name === "Web_Waterfall") {
    o.material = fallMaterial;
    o.renderOrder = 1;
    return;
  }
  if (name === "Web_Cloud") return;
  o.castShadow = o.receiveShadow = true;
});
// Clouds are lit from inside so they stay bright on the shadow side
for (const root of [island.scene, backdrop.scene])
  root.traverse((o) => {
    const material = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined;
    if (material?.name !== "Web_Cloud") return;
    material.emissive.set(0xc8d8ff);
    material.emissiveIntensity = 0.45;
  });
isle.add(island.scene);
scene.add(backdrop.scene);
document.body.classList.add("ready");

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  if (!reduceMotion) {
    isle.position.y = Math.sin(t * 0.5) * 0.25;
    fallMaterial.uniforms.time.value = t;
    for (const p of puffs) {
      const k = (t * 0.12 + p.phase) % 1;
      p.sprite.position.copy(p.base).add(new THREE.Vector3(0, k * 1.2, 0));
      p.sprite.scale.setScalar(p.size * (0.7 + k * 0.6));
      p.sprite.material.opacity = 0.55 * Math.sin(k * Math.PI);
    }
  }
  controls.update();
  renderer.render(scene, camera);
});
