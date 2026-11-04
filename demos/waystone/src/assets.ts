// Loads models listed in public/assets.json. A missing file yields a labelled stand-in, so code works before art lands.
import * as THREE from "three";
import { GLTFLoader, type GLTF } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

export interface ModelEntry {
  file: string;
  height?: number;
  length?: number;
  width?: number;
  rigged?: boolean;
  [k: string]: unknown;
}

export interface Model {
  key: string;
  entry: ModelEntry;
  /** Null when the GLB is missing: callers get a stand-in from clone(). */
  gltf: GLTF | null;
  animations: THREE.AnimationClip[];
  /** A fresh instance (SkeletonUtils clone for rigged models). */
  clone(): THREE.Object3D;
}

export interface Assets {
  get(key: string): Model;
  base: string;
}

const BASE = import.meta.env.BASE_URL;

export async function loadAssets(renderer: THREE.WebGLRenderer, onProgress?: (done: number, total: number) => void): Promise<Assets> {
  const manifest = (await (await fetch(`${BASE}assets.json`)).json()) as { models: Record<string, ModelEntry> };
  const { clone: skClone } = await import("three/addons/utils/SkeletonUtils.js");
  // GLBs are meshopt-compressed with WebP textures (gltf-transform), so no Draco/KTX2 decoder files are needed
  void renderer;
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const entries = Object.entries(manifest.models);
  let done = 0;
  const models = new Map<string, Model>();
  await Promise.all(
    entries.map(async ([key, entry]) => {
      let gltf: GLTF | null = null;
      try {
        gltf = await loader.loadAsync(`${BASE}models/${entry.file}`);
        gltf.scene.traverse((o) => {
          if ((o as THREE.Mesh).isMesh) o.castShadow = o.receiveShadow = true;
        });
      } catch {
        console.warn(`[assets] ${key}: ${entry.file} missing, using stand-in`);
      }
      models.set(key, {
        key,
        entry,
        gltf,
        animations: gltf?.animations ?? [],
        clone: () => (gltf ? (entry.rigged ? skClone(gltf.scene) : gltf.scene.clone()) : standIn(key, entry)),
      });
      onProgress?.(++done, entries.length);
    }),
  );
  return {
    base: BASE,
    get(key) {
      const m = models.get(key);
      if (!m) throw new Error(`No model "${key}" in assets.json`);
      return m;
    },
  };
}

function standIn(key: string, e: ModelEntry): THREE.Object3D {
  const h = e.height ?? 1.5;
  const r = Math.max(0.3, h * 0.2);
  const color = new THREE.Color().setHSL((hash(key) % 360) / 360, 0.45, 0.55);
  const mesh = new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(0.01, h - 2 * r), 4, 12), new THREE.MeshStandardMaterial({ color }));
  mesh.position.y = h / 2;
  mesh.castShadow = true;
  const g = new THREE.Group();
  g.name = `standin:${key}`;
  g.add(mesh);
  return g;
}

function hash(s: string) {
  let h = 0;
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0;
  return Math.abs(h);
}
