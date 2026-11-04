// Third-person orbit camera with collision against terrain (heightAt) and circle colliders.
import * as THREE from "three";
import type { Isle } from "../contracts";

export class FollowCam {
  yaw = Math.PI;
  pitch = 0.3;
  dist = 7;
  private curDist = 7;
  readonly look = new THREE.Vector3();
  private want = new THREE.Vector3();
  private tmp = new THREE.Vector3();
  shake = 0;

  constructor(private cam: THREE.PerspectiveCamera, private isle: Isle, private touch: boolean) {}

  input(dx: number, dy: number, zoom: number) {
    const k = this.touch ? 0.006 : 0.0028;
    this.yaw -= dx * k;
    this.pitch = THREE.MathUtils.clamp(this.pitch + dy * k * 0.8, -0.25, 1.15);
    this.dist = THREE.MathUtils.clamp(this.dist * (1 + zoom * 0.001), 3, 14);
  }

  /** Swing the camera behind a yaw (used after arrival / respawn). */
  behind(yaw: number) {
    this.yaw = yaw + Math.PI;
  }

  update(dt: number, target: THREE.Vector3, height: number, snap = false) {
    this.look.set(target.x, target.y + height * 0.85, target.z);
    const cp = Math.cos(this.pitch);
    const dir = this.tmp.set(Math.sin(this.yaw) * cp, Math.sin(this.pitch), Math.cos(this.yaw) * cp);
    // pull in when the boom hits ground or a collider
    // portrait screens have a narrow horizontal view, so pull back to keep the character from filling it
    const portrait = THREE.MathUtils.clamp(1 / this.cam.aspect, 1, 1.9);
    let d = this.dist * (0.85 + height * 0.08) * portrait;
    const steps = 12;
    for (let i = 1; i <= steps; i++) {
      const s = (d * i) / steps;
      const x = this.look.x + dir.x * s, y = this.look.y + dir.y * s, z = this.look.z + dir.z * s;
      const g = this.isle.heightAt(x, z);
      let hit = g !== null && y < g + 0.35;
      // colliders are flat circles with no height: only let them block the boom near the ground
      if (!hit && (g === null || y < g + 3))
        for (const c of this.isle.colliders) {
          if (c.r < 0.6) continue; // posts and thin trunks: seeing past them beats a camera jammed into the back
          const dx = x - c.x, dz = z - c.z;
          if (dx * dx + dz * dz < (c.r + 0.25) ** 2) {
            hit = true;
            break;
          }
        }
      if (hit) {
        d = Math.max(1.2, (d * (i - 1)) / steps);
        break;
      }
    }
    // pull in fast, ease out slowly
    this.curDist = snap ? d : d < this.curDist ? d : this.curDist + (d - this.curDist) * Math.min(1, 3 * dt);
    this.want.copy(this.look).addScaledVector(dir, this.curDist);
    if (snap) this.cam.position.copy(this.want);
    else this.cam.position.lerp(this.want, 1 - Math.exp(-16 * dt));
    if (this.shake > 0) {
      this.shake = Math.max(0, this.shake - dt * 2.5);
      const s = this.shake * 0.25;
      this.cam.position.x += (Math.random() - 0.5) * s;
      this.cam.position.y += (Math.random() - 0.5) * s;
    }
    this.cam.lookAt(this.look);
  }
}
