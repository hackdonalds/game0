// The Stormspawn: a cloud-wrapped boar. Whole-body motion only (hover, wind-up, charge, recoil, slam, fade).
// Fair by design: every attack is telegraphed for ~0.9 s and the charge locks its line early.
import * as THREE from "three";
import type { Assets } from "../assets";
import type { Isle } from "../contracts";
import type { Fx } from "./fx";
import { glowSprite } from "./fx";
import type { Audio } from "./audio";
import type { Player } from "./player";

const LEASH = 9; // metres from the arena centre

type State = "dormant" | "wake" | "stalk" | "windup" | "charge" | "recoil" | "hop" | "dying" | "gone";

export class Stormspawn {
  readonly root = new THREE.Group();
  private body = new THREE.Group();
  private model: THREE.Object3D;
  readonly maxHp = 300;
  hp = this.maxHp;
  state: State = "dormant";
  private t = 0;
  private cycle = 0;
  readonly pos = new THREE.Vector3();
  private yaw = 0;
  private chargeDir = new THREE.Vector3();
  private chargeLeft = 0;
  private hitPlayer = false;
  private wisps: THREE.Sprite[] = [];
  private eyes: THREE.Sprite[] = [];
  private mats: THREE.MeshStandardMaterial[] = [];
  private light?: THREE.PointLight;
  private flash = 0;
  private knock = new THREE.Vector3();
  readonly height: number;
  onDefeated?: () => void;

  constructor(assets: Assets, private isle: Isle, private fx: Fx, private audio: Audio, private arena: THREE.Vector3, lowQuality: boolean) {
    const m = assets.get("stormspawn");
    this.height = (m.entry.height ?? 1.6) * 1.6; // boss-sized: a storm-swollen boar, taller than any of the peoples' shoulders
    this.model = m.clone();
    if (m.gltf) {
      const e = m.entry as { scale?: number; rotY?: number };
      const box = new THREE.Box3().setFromObject(this.model);
      const s = e.scale ?? this.height / Math.max(0.01, box.max.y - box.min.y);
      this.model.scale.setScalar(s);
      const b2 = new THREE.Box3().setFromObject(this.model);
      this.model.position.y -= b2.min.y;
      if (e.rotY) this.model.rotation.y = e.rotY;
    } else {
      // stand-in: a squat boar-ish blob lying along +Z
      this.model = new THREE.Group();
      const mat = new THREE.MeshStandardMaterial({ color: 0x59607a, roughness: 0.9 });
      const torso = new THREE.Mesh(new THREE.SphereGeometry(0.8, 20, 14), mat);
      torso.scale.set(1, 0.85, 1.45);
      torso.position.y = 0.8;
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.5, 16, 12), mat);
      head.position.set(0, 0.85, 1.15);
      const snout = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 0.35, 12).rotateX(Math.PI / 2), mat);
      snout.position.set(0, 0.75, 1.6);
      const tuskM = new THREE.MeshStandardMaterial({ color: 0xe8e2d0 });
      for (const sx of [-1, 1]) {
        const tusk = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.4, 8), tuskM);
        tusk.position.set(sx * 0.22, 0.7, 1.6);
        tusk.rotation.x = -0.9;
        this.model.add(tusk);
      }
      for (const o of [torso, head, snout]) (o.castShadow = true), this.model.add(o);
    }
    this.model.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      const mt = (mesh.material as THREE.Material).clone() as THREE.MeshStandardMaterial;
      mesh.material = mt;
      if (mt.isMeshStandardMaterial) this.mats.push(mt);
    });
    this.body.add(this.model);
    // cloud wrap and lightning eyes
    for (let i = 0; i < (lowQuality ? 8 : 16); i++) {
      const w = glowSprite(i % 3 ? 0x8a93b8 : 0xc9d2f0, 0.9 + Math.random() * 0.8, 0.35);
      (w.material as THREE.SpriteMaterial).blending = THREE.NormalBlending;
      this.wisps.push(w);
      this.body.add(w);
    }
    for (const sx of [-1, 1]) {
      const e = glowSprite(0x9ff4ff, 0.35);
      e.position.set(sx * 0.22, this.height * 0.62, this.height * 0.82);
      this.eyes.push(e);
      this.body.add(e);
    }
    if (!lowQuality) {
      this.light = new THREE.PointLight(0x8fdcff, 6, 9, 2);
      this.light.position.set(0, this.height * 0.7, 0.6);
      this.body.add(this.light);
    }
    this.root.add(this.body);
    this.pos.copy(arena);
    this.pos.y = this.groundAt(arena.x, arena.z);
    this.root.visible = true;
  }

  private groundAt(x: number, z: number) {
    return this.isle.heightAt(x, z) ?? this.arena.y;
  }

  get alive() {
    return this.state !== "dying" && this.state !== "gone";
  }
  get engaged() {
    return this.state !== "dormant" && this.alive;
  }
  get vulnerable() {
    return this.state === "recoil";
  }
  get collider() {
    return { x: this.pos.x, z: this.pos.z, r: this.height * 0.55 };
  }

  wake() {
    if (this.state !== "dormant") return;
    this.state = "wake";
    this.t = 0;
    this.audio.roar();
  }

  /** Player strike landed? Returns true on hit. */
  strike(at: THREE.Vector3, dir: THREE.Vector3, dmg: number) {
    if (!this.alive || this.state === "dormant") return false;
    const to = this.pos.clone().sub(at).setY(0);
    const reach = this.height * 0.6 + 1.3;
    if (to.length() > reach) return false;
    const mult = this.vulnerable ? 1.6 : 0.8;
    this.hp -= dmg * mult;
    this.flash = 1;
    this.knock.copy(dir).multiplyScalar(this.vulnerable ? 2.5 : 1.2);
    this.fx.burst(this.pos.clone().setY(this.pos.y + this.height * 0.6), 0xbfe8ff, 12, 5);
    if (this.hp <= 0) {
      this.hp = 0;
      this.state = "dying";
      this.t = 0;
      this.audio.roar();
      for (const m of this.mats) (m.transparent = true), (m.needsUpdate = true);
    }
    return true;
  }

  update(dt: number, player: Player) {
    this.t += dt;
    const p = player.pos;
    const toP = new THREE.Vector3(p.x - this.pos.x, 0, p.z - this.pos.z);
    const dist = toP.length();
    if (dist > 0.01) toP.divideScalar(dist);
    const enraged = this.hp < this.maxHp * 0.5;
    let hover = 0.5 + Math.sin(this.t * 2.2) * 0.15;
    let pitch = 0, roll = 0;
    let faceP = true;

    switch (this.state) {
      case "dormant":
        hover = 0.35 + Math.sin(this.t * 1.2) * 0.08;
        break;
      case "wake":
        hover = 0.5 + Math.min(1, this.t) * 0.6;
        pitch = -0.4 * Math.sin(Math.min(1, this.t / 1.2) * Math.PI);
        if (this.t > 1.3) this.go("stalk");
        break;
      case "stalk": {
        // drift to a comfortable distance, circling a little
        const want = 6.5;
        const side = new THREE.Vector3(-toP.z, 0, toP.x);
        const radial = THREE.MathUtils.clamp(dist - want, -1, 1) * 2.2;
        // drift back toward the arena centre so fights stay away from the edges
        const home = new THREE.Vector3(this.arena.x - this.pos.x, 0, this.arena.z - this.pos.z);
        const hd = home.length();
        const pull = hd > 4 ? home.multiplyScalar((Math.min(hd - 4, 3) * 0.9) / hd) : home.set(0, 0, 0);
        this.move(toP.clone().multiplyScalar(radial).addScaledVector(side, 1.2).add(pull), dt);
        if (this.t > (enraged ? 1.3 : 1.9) && !player.dead) {
          this.cycle++;
          const next: State = this.cycle % 3 === 0 ? "hop" : "windup";
          this.go(next);
          if (next === "windup") this.audio.roar();
        }
        break;
      }
      case "windup": {
        const T = enraged ? 0.75 : 0.95;
        const k = this.t / T;
        pitch = -0.45 * Math.min(1, k * 1.5);
        hover = 0.35;
        roll = Math.sin(this.t * 40) * 0.05 * k;
        // lock the line at 60%: dodge after that and it misses
        if (k < 0.6) this.chargeDir.copy(toP);
        else faceP = false;
        this.pos.addScaledVector(this.chargeDir, -0.8 * dt);
        if (k >= 1) {
          this.go("charge");
          this.chargeLeft = 13;
          this.hitPlayer = false;
          this.audio.charge();
        }
        break;
      }
      case "charge": {
        faceP = false;
        const sp = enraged ? 17 : 15;
        const step = sp * dt;
        const next = this.pos.clone().addScaledVector(this.chargeDir, step);
        // stay inside the arena and over ground
        const out = Math.hypot(next.x - this.arena.x, next.z - this.arena.z) > LEASH + 1.5 || this.isle.heightAt(next.x, next.z) === null;
        const blocked = this.isle.colliders.some((c) => (next.x - c.x) ** 2 + (next.z - c.z) ** 2 < (c.r + 0.8) ** 2);
        if (out || blocked) {
          this.go("recoil");
          this.audio.thump();
          this.fx.burst(this.pos.clone().setY(this.pos.y + 0.5), 0x9aa5c8, 16, 4);
          break;
        }
        this.pos.copy(next);
        this.chargeLeft -= step;
        pitch = 0.2;
        hover = 0.3;
        if (!this.hitPlayer && dist < this.height * 0.6 + 0.9 && Math.abs(p.y - this.pos.y) < 2) {
          this.hitPlayer = true;
          if (player.takeHit(16, this.pos, 9)) {
            this.audio.hurt();
          }
          // an anchored Anchorkin stops it dead
          if (player.anchored) {
            this.go("recoil");
            this.audio.thump();
            break;
          }
        }
        if (this.chargeLeft <= 0) this.go("recoil");
        break;
      }
      case "recoil":
        hover = 0.2 + Math.abs(Math.sin(this.t * 6)) * 0.25 * Math.max(0, 1 - this.t);
        pitch = 0.25 * Math.sin(this.t * 8) * Math.max(0, 1 - this.t / 1.4);
        roll = Math.sin(this.t * 5) * 0.15;
        faceP = false;
        if (this.t > 1.4) this.go("stalk");
        break;
      case "hop": {
        // rises, hangs, slams: jump or step out of the ring
        const T1 = 0.9, T2 = 1.25;
        if (this.t < T1) {
          hover = 0.5 + (this.t / T1) * 3;
          if (this.t < 0.05) this.fx.ring(this.pos, 4.5, 0xffd37a, T1 + 0.35, false);
        } else if (this.t < T2) {
          hover = 3.5 * (1 - (this.t - T1) / (T2 - T1));
        } else {
          this.fx.ring(this.pos, 4.5, 0xbfe8ff, 0.45);
          this.fx.burst(this.pos.clone().setY(this.pos.y + 0.3), 0xc9d2f0, 22, 7);
          this.audio.thump();
          const airborne = p.y > this.groundAt(p.x, p.z) + 0.5;
          if (dist < 4.5 && !airborne && player.takeHit(12, this.pos, 7)) this.audio.hurt();
          this.go("recoil");
          this.t = 0.4; // shorter stagger after a slam
        }
        break;
      }
      case "dying": {
        faceP = false;
        hover = 0.5 + this.t * 1.2;
        this.yaw += dt * (2 + this.t * 6);
        const k = Math.min(1, this.t / 2.2);
        this.body.scale.setScalar(1 - k * 0.7);
        for (const m of this.mats) m.opacity = 1 - k;
        for (const w of this.wisps) (w.material as THREE.SpriteMaterial).opacity = 0.35 * (1 - k);
        if (this.light) this.light.intensity = 6 * (1 - k);
        if (Math.random() < 0.4) this.fx.burst(this.pos.clone().setY(this.pos.y + hover + 0.6), 0xbfe8ff, 4, 3, 0.3, 0.8);
        if (k >= 1) {
          this.state = "gone";
          this.root.visible = false;
          this.onDefeated?.();
        }
        break;
      }
      case "gone":
        return;
    }

    // knockback from player hits
    if (this.knock.lengthSq() > 1e-4) {
      this.move(this.knock.clone().multiplyScalar(4), dt);
      this.knock.multiplyScalar(Math.exp(-8 * dt));
    }
    if (faceP && dist > 0.1) {
      const target = Math.atan2(toP.x, toP.z);
      this.yaw += Math.atan2(Math.sin(target - this.yaw), Math.cos(target - this.yaw)) * Math.min(1, 6 * dt);
    } else if (this.state === "charge" || this.state === "windup") {
      this.yaw = Math.atan2(this.chargeDir.x, this.chargeDir.z);
    }
    this.pos.y = this.groundAt(this.pos.x, this.pos.z);
    this.root.position.copy(this.pos);
    this.body.position.y = hover;
    this.body.rotation.set(pitch, 0, roll);
    this.root.rotation.y = this.yaw;

    // cloud wrap swirl; eyes flare on wind-up
    const n = this.wisps.length;
    this.wisps.forEach((w, i) => {
      const a = (i / n) * Math.PI * 2 + this.t * (0.6 + (i % 3) * 0.25);
      const r = this.height * (0.55 + 0.2 * Math.sin(this.t * 1.3 + i));
      w.position.set(Math.cos(a) * r, this.height * (0.35 + 0.45 * ((i * 0.37) % 1)) + Math.sin(this.t * 2 + i) * 0.1, Math.sin(a) * r * 1.3);
    });
    const flare = this.state === "windup" || this.state === "hop" ? 1.8 : this.state === "charge" ? 1.5 : 1;
    for (const e of this.eyes) e.scale.setScalar(0.35 * flare * (0.85 + Math.random() * 0.3));
    if (this.light) this.light.intensity = this.state === "dying" ? this.light.intensity : 4 * flare + Math.random() * 2;
    if (this.flash > 0) {
      this.flash = Math.max(0, this.flash - dt * 5);
      for (const m of this.mats) {
        m.emissive.setHex(0xbfe8ff);
        m.emissiveIntensity = this.flash;
      }
    }
  }

  private move(v: THREE.Vector3, dt: number) {
    const nx = this.pos.x + v.x * dt, nz = this.pos.z + v.z * dt;
    if (this.isle.heightAt(nx, nz) === null) return;
    if ((nx - this.arena.x) ** 2 + (nz - this.arena.z) ** 2 > LEASH * LEASH) return;
    this.pos.x = nx;
    this.pos.z = nz;
  }

  private go(s: State) {
    this.state = s;
    this.t = 0;
  }
}
