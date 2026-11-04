// Third-person character controller: movement over isle.heightAt, circle colliders, void falls,
// per-people stats, the three innate skills, attack combo and hit reactions.
import * as THREE from "three";
import type { Isle } from "../contracts";
import type { PeopleDef } from "./data";
import type { Input } from "./input";
import type { Rig } from "./anim";

export const RADIUS = 0.45;

export interface Env {
  /** Gust acting on the player now (already filtered to the bridge). */
  gust: { dir: THREE.Vector3; strength: number } | null;
  /** Storm drain in hp/s (ridge path). */
  drain: number;
  /** Under an old tree: Take Root heals faster and drain is blocked. */
  nearTree: boolean;
  /** Can't act (dialogue, cutscene). */
  frozen: boolean;
  /** Extra circle colliders (NPCs, boss). */
  extra: { x: number; z: number; r: number }[];
  /** Place counts as a safe respawn point. */
  safe: boolean;
}

export type PlayerEvent =
  | { type: "step" }
  | { type: "jump" }
  | { type: "land"; hard: boolean }
  | { type: "swing"; combo: number }
  | { type: "strike"; pos: THREE.Vector3; dir: THREE.Vector3; dmg: number; combo: number }
  | { type: "void" }
  | { type: "dead" }
  | { type: "rooted" }
  | { type: "glide" }
  | { type: "hurt"; dmg: number };

export class Player {
  readonly pos = new THREE.Vector3();
  readonly vel = new THREE.Vector3();
  yaw = 0;
  hp: number;
  st: number;
  grounded = true;
  airborne = 0;
  gliding = false;
  anchored = false;
  rooted = false;
  rootCharge = 0; // 0..1 while settling into the ground
  dead = false;
  readonly lastSafe = new THREE.Vector3();
  private safeTimer = 0;
  private strideAcc = 0;
  private attackT = 0; // time left in current swing
  private struck = false;
  private combo = 0;
  private comboWindow = 0;
  private hitStun = 0;
  private invuln = 0;
  private sinceAttack = 9;
  private deadT = 0;
  private pullFree = 0;
  private peakFall = 0;
  private wasGliding = false;
  private events: PlayerEvent[] = [];
  readonly fwd = new THREE.Vector3();

  constructor(private isle: Isle, readonly def: PeopleDef, readonly rig: Rig) {
    this.hp = def.hp;
    this.st = def.stamina;
  }

  place(p: THREE.Vector3, yaw = this.yaw) {
    const h = this.isle.heightAt(p.x, p.z);
    this.pos.set(p.x, h ?? p.y, p.z);
    this.vel.set(0, 0, 0);
    this.yaw = yaw;
    this.grounded = true;
    this.gliding = this.anchored = this.rooted = false;
    this.lastSafe.copy(this.pos);
    this.sync();
  }

  respawn(at: THREE.Vector3, fullHeal: boolean) {
    this.dead = false;
    this.deadT = 0;
    this.hitStun = 0;
    this.invuln = 1.5;
    if (fullHeal) this.hp = this.def.hp;
    this.st = Math.max(this.st, this.def.stamina * 0.5);
    this.place(at);
    this.rig.play("idle", 0.05);
  }

  takeHit(dmg: number, from: THREE.Vector3, force: number) {
    if (this.dead || this.invuln > 0) return false;
    if (this.anchored) {
      dmg *= 0.5;
      force = 0;
    }
    if (this.rooted) force *= 0.3;
    this.hp -= dmg;
    this.invuln = 0.8;
    this.events.push({ type: "hurt", dmg });
    this.rig.hitFlash(0xff5040);
    const away = this.pos.clone().sub(from).setY(0);
    if (away.lengthSq() < 1e-4) away.set(Math.sin(this.yaw), 0, Math.cos(this.yaw)).negate();
    away.normalize();
    if (force > 0) {
      this.vel.addScaledVector(away, force * this.def.push);
      this.vel.y = Math.max(this.vel.y, 3.5);
      this.grounded = false;
      this.rooted = false;
      this.rootCharge = 0;
    }
    this.attackT = 0;
    if (this.hp <= 0) this.die();
    else {
      this.hitStun = 0.4;
      this.rig.play("hit", 0.08);
    }
    return true;
  }

  heal(n: number) {
    this.hp = Math.min(this.def.hp, this.hp + n);
  }

  private die() {
    this.hp = 0;
    this.dead = true;
    this.deadT = 0;
    this.gliding = this.anchored = this.rooted = false;
    this.rig.play("death", 0.15);
  }

  private ground(x: number, z: number) {
    return this.isle.heightAt(x, z);
  }

  update(dt: number, input: Input, camYaw: number, env: Env): PlayerEvent[] {
    const d = this.def;
    this.events.length = 0;
    this.invuln = Math.max(0, this.invuln - dt);
    this.hitStun = Math.max(0, this.hitStun - dt);
    this.comboWindow = Math.max(0, this.comboWindow - dt);
    this.sinceAttack += dt;

    if (this.dead) {
      this.deadT += dt;
      this.vel.x *= 0.9;
      this.vel.z *= 0.9;
      this.physics(dt, env);
      if (this.deadT > 2.2 && this.deadT - dt <= 2.2) this.events.push({ type: "dead" });
      this.sync();
      return this.events;
    }

    const act = !env.frozen && this.hitStun <= 0;
    const mx = act ? input.move.x : 0, my = act ? input.move.y : 0;
    const fx = -Math.sin(camYaw), fz = -Math.cos(camYaw);
    const wish = new THREE.Vector3(fx * my - fz * mx, 0, fz * my + fx * mx);
    const mag = Math.min(1, wish.length());
    if (mag > 0.01) wish.normalize();
    const skill = act && input.down("skill");

    // ---- Innate skills ----
    this.anchored = d.id === "anchorkin" && skill && this.grounded;
    const wantRoot = d.id === "rootwarden" && skill && this.grounded && this.attackT <= 0;
    if (wantRoot && Math.hypot(this.vel.x, this.vel.z) < 1.2) {
      this.rootCharge = Math.min(1, this.rootCharge + dt / 0.5);
      if (this.rootCharge >= 1 && !this.rooted) {
        this.rooted = true;
        this.events.push({ type: "rooted" });
      }
    } else {
      if (this.rooted) this.pullFree = 0.35; // pulling free takes a moment
      this.rooted = false;
      this.rootCharge = 0;
    }
    this.pullFree = Math.max(0, this.pullFree - dt);
    const glideNow = d.id === "galeborne" && skill && !this.grounded && this.airborne > 0.12 && this.vel.y < 2 && this.st > 0;
    if (glideNow && !this.gliding) this.events.push({ type: "glide" });
    this.gliding = glideNow;
    if (this.gliding) this.wasGliding = true;

    const rootedish = this.rootCharge > 0 || this.rooted || this.pullFree > 0;
    const locked = this.anchored || rootedish;

    // ---- Attack ----
    if (act && input.pressed("attack") && !locked && !this.gliding && this.attackT <= 0.12) {
      if (this.st >= 6) {
        this.combo = this.comboWindow > 0 ? (this.combo % 3) + 1 : 1;
        this.attackT = d.swing * (this.combo === 3 ? 1.35 : 1);
        this.struck = false;
        this.st -= 6;
        this.sinceAttack = 0;
        this.comboWindow = this.attackT + 0.45;
        this.rig.playFor("attack", this.attackT + 0.15);
        this.events.push({ type: "swing", combo: this.combo });
        if (mag > 0.01) this.yaw = Math.atan2(wish.x, wish.z);
      }
    }
    if (this.attackT > 0) {
      const total = d.swing * (this.combo === 3 ? 1.35 : 1);
      this.attackT -= dt;
      if (!this.struck && this.attackT < total * 0.5) {
        this.struck = true;
        this.fwd.set(Math.sin(this.yaw), 0, Math.cos(this.yaw));
        this.events.push({ type: "strike", pos: this.pos.clone().addScaledVector(this.fwd, 1.1), dir: this.fwd.clone(), dmg: d.damage * (this.combo === 3 ? 1.6 : 1), combo: this.combo });
      }
    }

    // ---- Horizontal movement ----
    const attacking = this.attackT > 0;
    let speed = locked ? 0 : d.speed * mag * (attacking ? 0.25 : 1);
    const accel = this.grounded ? d.accel : this.gliding ? 2.5 : 3.5;
    if (this.gliding) {
      // glide: forward along facing, steer with input
      if (mag > 0.01) {
        const target = Math.atan2(wish.x, wish.z);
        let dy = Math.atan2(Math.sin(target - this.yaw), Math.cos(target - this.yaw));
        this.yaw += dy * Math.min(1, 2.5 * dt);
      }
      wish.set(Math.sin(this.yaw), 0, Math.cos(this.yaw));
      speed = 9.5;
      this.st = Math.max(0, this.st - 9 * dt);
    }
    this.vel.x += (wish.x * speed - this.vel.x) * Math.min(1, accel * dt);
    this.vel.z += (wish.z * speed - this.vel.z) * Math.min(1, accel * dt);
    if (locked && this.grounded) this.vel.x = this.vel.z = 0;
    if (mag > 0.01 && !locked && !this.gliding && !attacking) {
      const target = Math.atan2(wish.x, wish.z);
      const dy = Math.atan2(Math.sin(target - this.yaw), Math.cos(target - this.yaw));
      this.yaw += dy * Math.min(1, 12 * dt);
    }

    // Gusts push unless anchored
    if (env.gust && env.gust.strength > 0.02 && !this.anchored) {
      const k = env.gust.strength * 16 * d.push * (this.rooted ? 0.3 : 1);
      this.vel.addScaledVector(env.gust.dir, k * dt);
    }

    // ---- Jump ----
    if (act && input.pressed("jump") && this.grounded && !locked) {
      this.vel.y = d.jump;
      this.grounded = false;
      this.airborne = 0;
      this.events.push({ type: "jump" });
      this.rig.play("jump", 0.08, 1.3);
    }

    this.physics(dt, env);

    // ---- Health, stamina ----
    const drain = env.nearTree ? 0 : env.drain;
    if (drain > 0) this.hp -= drain * dt;
    if (this.rooted) {
      const k = env.nearTree ? 3 : 1;
      this.hp = Math.min(d.hp, this.hp + 7 * k * dt);
      this.st = Math.min(d.stamina, this.st + 30 * k * dt);
    } else if (!this.gliding && this.sinceAttack > 0.8 && this.grounded) {
      this.st = Math.min(d.stamina, this.st + 16 * dt);
    }
    if (this.hp <= 0 && !this.dead) this.die();

    // ---- Safe point ----
    this.safeTimer -= dt;
    if (this.grounded && env.safe && this.safeTimer <= 0) {
      this.safeTimer = 0.3;
      const p = this.pos, g = (x: number, z: number) => this.ground(x, z) !== null;
      if (g(p.x + 1.5, p.z) && g(p.x - 1.5, p.z) && g(p.x, p.z + 1.5) && g(p.x, p.z - 1.5)) this.lastSafe.copy(p);
    }

    this.animate(dt);
    this.sync();
    return this.events;
  }

  private physics(dt: number, env: Env) {
    const nx = this.pos.x + this.vel.x * dt;
    const nz = this.pos.z + this.vel.z * dt;
    const gh = this.ground(nx, nz);
    // refuse steps up steeper than a stair (walls, cliffs)
    const blocked = gh !== null && gh > this.pos.y + (this.grounded ? 0.7 : 0.35);
    if (!blocked) {
      if (this.grounded) {
        this.strideAcc += Math.hypot(nx - this.pos.x, nz - this.pos.z);
        const stride = 0.9 + this.def.speed * 0.12;
        if (this.strideAcc > stride) {
          this.strideAcc = 0;
          this.events.push({ type: "step" });
        }
      }
      this.pos.x = nx;
      this.pos.z = nz;
    } else {
      this.vel.x = this.vel.z = 0;
    }
    const cols = this.isle.colliders.concat(env.extra);
    for (const c of cols) {
      const dx = this.pos.x - c.x, dz = this.pos.z - c.z;
      const min = c.r + RADIUS;
      const d2 = dx * dx + dz * dz;
      if (d2 < min * min && d2 > 1e-6) {
        const d = Math.sqrt(d2);
        this.pos.x = c.x + (dx / d) * min;
        this.pos.z = c.z + (dz / d) * min;
      }
    }
    // vertical
    if (this.gliding) {
      this.vel.y += (-2.2 - this.vel.y) * Math.min(1, 4 * dt);
    } else this.vel.y -= this.def.gravity * dt;
    this.pos.y += this.vel.y * dt;
    this.peakFall = Math.min(this.peakFall, this.vel.y);
    const h = this.ground(this.pos.x, this.pos.z);
    if (h !== null && this.pos.y <= h + (this.grounded ? 0.45 : 0) && this.vel.y <= 0.01) {
      if (!this.grounded) {
        const impact = -this.peakFall;
        const hard = impact > 15 && !this.wasGliding;
        if (hard && !this.dead) {
          const dmg = (impact - 15) * 3.5 * this.def.fallDamage;
          this.hp -= dmg;
          this.events.push({ type: "hurt", dmg });
          if (this.hp <= 0) this.die();
        }
        this.events.push({ type: "land", hard });
      }
      this.pos.y = h;
      this.vel.y = 0;
      this.grounded = true;
      this.airborne = 0;
      this.peakFall = 0;
      this.wasGliding = false;
      this.gliding = false;
    } else {
      this.grounded = false;
      this.airborne += dt;
    }
    // into the void
    if (h === null && this.pos.y < this.lastSafe.y - 9 && !this.dead) this.events.push({ type: "void" });
    if (this.pos.y < this.lastSafe.y - 60) this.events.push({ type: "void" });
  }

  private animate(dt: number) {
    const r = this.rig;
    const hs = Math.hypot(this.vel.x, this.vel.z);
    r.speed = hs;
    if (this.hitStun > 0 || this.attackT > 0) return r.update(dt);
    if (this.gliding) r.base("glide");
    else if (this.anchored) r.base("brace");
    else if (this.rootCharge > 0 || this.rooted) r.base("kneel");
    else if (!this.grounded && this.airborne > 0.2) r.base(this.vel.y > 0 ? "jump" : "fall");
    else if (!this.grounded) {
      /* keep take-off */
    } else if (hs < 0.4) r.base("idle");
    else if (hs < this.def.speed * 0.6) r.base("walk", THREE.MathUtils.clamp(hs / 1.1, 0.7, 2.2)); // UAL walk ~1.0 m/s
    else r.base("run", THREE.MathUtils.clamp(hs / 5.5, 0.8, 1.4)); // UAL jog ~5.5 m/s
    r.update(dt);
  }

  private sync() {
    this.rig.root.position.copy(this.pos);
    this.rig.root.rotation.y = this.yaw;
  }
}
