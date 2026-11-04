// Debug free camera for the world lane (?fly, or ?cam=x,y,z,tx,ty,tz for a fixed shot). Overrides the game camera.
import * as THREE from "three";

export function createFly(params: URLSearchParams) {
  const cam = params.get("cam")?.split(",").map(Number);
  let active = params.has("fly") || !!cam;
  const keys = new Set<string>();
  let yaw = 0, pitch = -0.2, dragging = false, lx = 0, ly = 0;
  const pos = new THREE.Vector3(0, 20, 80);
  let init = false;
  if (cam && cam.length >= 6) {
    pos.set(cam[0], cam[1], cam[2]);
    const d = new THREE.Vector3(cam[3] - cam[0], cam[4] - cam[1], cam[5] - cam[2]).normalize();
    yaw = Math.atan2(-d.x, -d.z);
    pitch = Math.asin(d.y);
    init = true;
  }
  if (active) {
    addEventListener("keydown", (e) => keys.add(e.code), true);
    addEventListener("keyup", (e) => keys.delete(e.code), true);
    addEventListener("pointerdown", (e) => { dragging = true; lx = e.clientX; ly = e.clientY; }, true);
    addEventListener("pointerup", () => (dragging = false), true);
    addEventListener("pointermove", (e) => {
      if (!dragging) return;
      yaw -= (e.clientX - lx) * 0.004;
      pitch = THREE.MathUtils.clamp(pitch - (e.clientY - ly) * 0.004, -1.5, 1.5);
      lx = e.clientX; ly = e.clientY;
    }, true);
  }
  const e = new THREE.Euler(0, 0, 0, "YXZ");
  const v = new THREE.Vector3();
  return {
    get active() { return active; },
    /** Jump the camera to a shot (for screenshots). */
    set(x: number, y: number, z: number, tx: number, ty: number, tz: number) {
      active = true;
      pos.set(x, y, z);
      const d = new THREE.Vector3(tx - x, ty - y, tz - z).normalize();
      yaw = Math.atan2(-d.x, -d.z);
      pitch = Math.asin(d.y);
      init = true;
    },
    update(dt: number, camera: THREE.PerspectiveCamera) {
      if (!active) return;
      if (!init) { pos.copy(camera.position); init = true; }
      const sp = (keys.has("ShiftLeft") ? 40 : 12) * dt;
      e.set(pitch, yaw, 0);
      const f = v.set(0, 0, -1).applyEuler(e);
      if (keys.has("KeyW")) pos.addScaledVector(f, sp);
      if (keys.has("KeyS")) pos.addScaledVector(f, -sp);
      const r = new THREE.Vector3(1, 0, 0).applyEuler(e);
      if (keys.has("KeyD")) pos.addScaledVector(r, sp);
      if (keys.has("KeyA")) pos.addScaledVector(r, -sp);
      if (keys.has("KeyE")) pos.y += sp;
      if (keys.has("KeyQ")) pos.y -= sp;
      camera.position.copy(pos);
      camera.quaternion.setFromEuler(e);
      camera.updateMatrixWorld();
    },
  };
}
