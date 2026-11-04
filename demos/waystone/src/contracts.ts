// The seam between lanes: src/world/* builds the isle (Isle), src/game/* runs play on top of it (startGame).
// Change this file only by agreement between both sides; main.ts wires them together.
import type * as THREE from "three";
import type { Assets } from "./assets";

export type People = "galeborne" | "anchorkin" | "rootwarden";
export type Quality = "high" | "low"; // low = phones / weak GPUs

export interface IslePoints {
  spawn: THREE.Vector3; // on the jetty, where the skiff lands
  camp: THREE.Vector3; // campfire; Maren stands near it
  maren: THREE.Vector3;
  shards: THREE.Vector3[]; // 3 glimmer shards in the meadow
  ridgeStart: THREE.Vector3; // where the Storm Ridge begins (all routes)
  glideLaunch: THREE.Vector3; // Galeborne: cliff edge to jump from
  glideLanding: THREE.Vector3; // Galeborne: ledge below the Waystone
  bridgeStart: THREE.Vector3; // Anchorkin: rope bridge ends
  bridgeEnd: THREE.Vector3;
  rootTrees: THREE.Vector3[]; // Rootwarden: old trees along the draining ridge path
  arena: THREE.Vector3; // Stormspawn fight centre
  waystone: THREE.Vector3;
}

export interface Isle {
  points: IslePoints;
  /** Ground height at x,z, or null over the void (falling off = respawn). */
  heightAt(x: number, z: number): number | null;
  /** Solid obstacles (trees, stone, camp) as circles on the XZ plane. */
  colliders: { x: number; z: number; r: number }[];
  /** 0 calm .. 1 full storm; drives sky, clouds, wind, lightning. */
  setStorm(level: number): void;
  /** Ending: storm breaks, the lane lights up across the cloud sea. */
  lightTheLane(): void;
  /** Gust direction and strength 0..1 on the bridge right now (Anchorkin route). */
  gustAt(x: number, z: number, t: number): { dir: THREE.Vector3; strength: number };
  update(dt: number, t: number, camera: THREE.Camera): void;
  sun: THREE.DirectionalLight;
}

export interface WorldContext {
  scene: THREE.Scene;
  renderer: THREE.WebGLRenderer;
  assets: Assets;
  quality: Quality;
}

export interface GameContext extends WorldContext {
  camera: THREE.PerspectiveCamera;
  isle: Isle;
  /** Register a per-frame callback. */
  onFrame(fn: (dt: number, t: number) => void): void;
}
