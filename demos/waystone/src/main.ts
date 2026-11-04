// Wiring only: renderer, loop, assets, then world (src/world) and game (src/game). Lanes own their folders.
import * as THREE from "three";
import { loadAssets } from "./assets";
import { createIsle } from "./world";
import { startGame } from "./game";
import type { Quality } from "./contracts";

const params = new URLSearchParams(location.search);
const touch = matchMedia("(pointer: coarse)").matches;
const quality: Quality = (params.get("q") as Quality) ?? (touch || innerWidth < 900 ? "low" : "high");

const renderer = new THREE.WebGLRenderer({ antialias: quality === "high", powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, quality === "high" ? 2 : 1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = quality === "high" ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 4000);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const bar = document.querySelector<HTMLElement>(".loading-bar");
const assets = await loadAssets(renderer, (d, n) => bar && (bar.style.width = `${(100 * d) / n}%`));
const isle = await createIsle({ scene, renderer, assets, quality });

const frames: ((dt: number, t: number) => void)[] = [];
await startGame({ scene, renderer, assets, quality, camera, isle, onFrame: (fn) => frames.push(fn) });
document.body.classList.add("ready");

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 1 / 20);
  const t = clock.elapsedTime;
  for (const fn of frames) fn(dt, t);
  isle.update(dt, t, camera);
  renderer.render(scene, camera);
});
