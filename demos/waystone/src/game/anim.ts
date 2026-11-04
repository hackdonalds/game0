// Character rig: a model instance fitted to its manifest height, with named clips and crossfades.
// Stand-ins without clips get simple procedural motion (bob, lean, squash) so states still read.
import * as THREE from "three";
import type { Assets } from "../assets";

export type Clip = "idle" | "walk" | "run" | "jump" | "fall" | "attack" | "hit" | "death" | "talk" | "glide" | "brace" | "kneel";
const ONCE: Clip[] = ["attack", "hit", "death", "jump"];
const FALLBACK: Partial<Record<Clip, Clip[]>> = {
  run: ["walk"], walk: ["run"], fall: ["jump", "idle"], jump: ["fall"], glide: ["fall", "jump"], brace: ["idle"], kneel: ["idle"], talk: ["idle"], hit: [], death: [],
};

export class Rig {
  readonly root = new THREE.Group(); // positioned by game code
  readonly body = new THREE.Group(); // procedural offsets for stand-ins
  readonly model: THREE.Object3D;
  readonly height: number;
  readonly hasClips: boolean;
  private mixer?: THREE.AnimationMixer;
  private actions = new Map<Clip, THREE.AnimationAction>();
  private current?: THREE.AnimationAction;
  private currentName: Clip = "idle";
  private onceUntil = 0;
  private time = 0;
  private flash = 0;
  private mats: THREE.MeshStandardMaterial[] = [];
  state: Clip = "idle";
  speed = 0; // horizontal speed, for walk/run timescale and stand-in bob

  constructor(assets: Assets, key: string) {
    const m = assets.get(key);
    this.model = m.clone();
    const e = m.entry as { height?: number; scale?: number; yOffset?: number; rotY?: number };
    this.height = e.height ?? 1.8;
    if (m.gltf) {
      if (e.scale) this.model.scale.setScalar(e.scale);
      else {
        const box = new THREE.Box3().setFromObject(this.model);
        const h = box.max.y - box.min.y;
        if (h > 0.01) this.model.scale.setScalar(this.height / h);
        const box2 = new THREE.Box3().setFromObject(this.model);
        this.model.position.y -= box2.min.y;
      }
      if (e.yOffset) this.model.position.y += e.yOffset;
      if (e.rotY) this.model.rotation.y = e.rotY;
    }
    this.body.add(this.model);
    this.root.add(this.body);
    this.model.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      // own the materials so hit flashes don't leak between clones
      const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const own = list.map((mt) => mt.clone());
      mesh.material = Array.isArray(mesh.material) ? own : own[0];
      for (const mt of own) if ((mt as THREE.MeshStandardMaterial).isMeshStandardMaterial) this.mats.push(mt as THREE.MeshStandardMaterial);
    });
    this.hasClips = m.animations.length > 0;
    if (this.hasClips) {
      this.mixer = new THREE.AnimationMixer(this.model);
      for (const c of m.animations) {
        const n = c.name.toLowerCase().split("|").pop()!.trim() as Clip;
        if (!this.actions.has(n)) this.actions.set(n, this.mixer.clipAction(c));
      }
      for (const n of ONCE) {
        const a = this.actions.get(n);
        if (a) {
          a.setLoop(THREE.LoopOnce, 1);
          a.clampWhenFinished = true;
        }
      }
      this.play("idle", 0);
    }
  }

  has(n: Clip) {
    return this.actions.has(n);
  }

  /** Clip length in seconds after fallback (0 for stand-ins). */
  duration(n: Clip) {
    const r = this.mixer ? this.resolve(n) : null;
    return r ? this.actions.get(r)!.getClip().duration : 0;
  }

  /** Play a one-shot stretched to last `secs`. */
  playFor(n: Clip, secs: number, fade = 0.08) {
    const d = this.duration(n);
    this.play(n, fade, d > 0 ? d / secs : 1);
  }

  private resolve(n: Clip): Clip | null {
    if (this.actions.has(n)) return n;
    for (const f of FALLBACK[n] ?? ["idle"]) if (this.actions.has(f)) return f;
    return this.actions.has("idle") ? "idle" : null;
  }

  /** Crossfade to a clip. Looping clips persist; one-shots return to `state` when done. */
  play(n: Clip, fade = 0.18, timeScale = 1) {
    this.state = n;
    if (ONCE.includes(n)) this.onceUntil = this.time + 10; // until finished
    if (!this.mixer) {
      this.currentName = n;
      return;
    }
    const r = this.resolve(n);
    if (!r) return;
    const a = this.actions.get(r)!;
    if (a === this.current && !ONCE.includes(r)) {
      a.setEffectiveTimeScale(timeScale);
      return;
    }
    a.reset().setEffectiveTimeScale(timeScale).setEffectiveWeight(1).fadeIn(fade).play();
    if (this.current && this.current !== a) this.current.fadeOut(fade);
    this.current = a;
    this.currentName = r;
    if (ONCE.includes(r)) this.onceUntil = this.time + a.getClip().duration / Math.max(0.01, timeScale);
  }

  /** Seconds left on the current one-shot (0 when a loop is playing). */
  oneShotLeft() {
    return Math.max(0, this.onceUntil - this.time);
  }

  /** Set a looping base state, unless a one-shot is still playing. */
  base(n: Clip, timeScale = 1) {
    // one-shots finish first, except a take-off, which any state but the fall loop may cut
    if (this.onceUntil > this.time && ONCE.includes(this.state) && !(this.state === "jump" && n !== "fall" && n !== "jump")) return;
    if (this.state !== n) this.play(n);
    else if (this.current) this.current.setEffectiveTimeScale(timeScale);
  }

  hitFlash(color = 0xffffff) {
    this.flash = 1;
    for (const m of this.mats) m.emissive.setHex(color);
  }

  update(dt: number) {
    this.time += dt;
    if (this.state && ONCE.includes(this.state) && this.time > this.onceUntil && this.state !== "death") this.state = "idle";
    this.mixer?.update(dt);
    if (this.flash > 0) {
      this.flash = Math.max(0, this.flash - dt * 5);
      for (const m of this.mats) m.emissiveIntensity = this.flash * 0.9;
    }
    if (this.hasClips) return;
    // Procedural stand-in motion
    const b = this.body, t = this.time, s = this.state;
    const k = 1 - Math.exp(-12 * dt);
    let y = 0, rx = 0, rz = 0, sy = 1;
    if (s === "walk" || s === "run") {
      y = Math.abs(Math.sin(t * (s === "run" ? 11 : 7))) * 0.08;
      rx = 0.12;
      rz = Math.sin(t * (s === "run" ? 11 : 7)) * 0.05;
    } else if (s === "idle" || s === "talk") {
      sy = 1 + Math.sin(t * 2) * 0.015 + (s === "talk" ? Math.abs(Math.sin(t * 9)) * 0.02 : 0);
    } else if (s === "jump" || s === "fall") rx = -0.1;
    else if (s === "glide") (rx = 1.1), (y = 0.6);
    else if (s === "brace") (sy = 0.82), (rx = 0.25);
    else if (s === "kneel") (sy = 0.68), (rz = Math.sin(t * 1.5) * 0.02);
    else if (s === "attack") {
      const p = 1 - this.oneShotLeft() / 0.4;
      rx = Math.sin(Math.min(1, p) * Math.PI) * 0.5;
    } else if (s === "hit") rx = -0.3;
    else if (s === "death") (rz = 1.5), (y = 0.3);
    b.position.y += (y - b.position.y) * k;
    b.rotation.x += (rx - b.rotation.x) * k;
    b.rotation.z += (rz - b.rotation.z) * k;
    b.scale.y += (sy - b.scale.y) * k;
    if (ONCE.includes(s) && this.onceUntil - this.time > 5) this.onceUntil = this.time + (s === "attack" ? 0.4 : s === "hit" ? 0.35 : s === "jump" ? 0.3 : 99);
  }
}
