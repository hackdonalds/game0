// Small effects made in code: soft sprites, sword arcs, spark bursts, ground rings.
import * as THREE from "three";

let soft: THREE.Texture | null = null;
export function softTexture() {
  if (soft) return soft;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.35, "rgba(255,255,255,.55)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  soft = new THREE.CanvasTexture(c);
  soft.colorSpace = THREE.SRGBColorSpace;
  return soft;
}

export function glowSprite(color: THREE.ColorRepresentation, size: number, opacity = 1) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: softTexture(), color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending }));
  s.scale.setScalar(size);
  return s;
}

interface Live {
  obj: THREE.Object3D;
  t: number;
  life: number;
  tick: (k: number, dt: number) => void;
}

export class Fx {
  private live: Live[] = [];
  constructor(private scene: THREE.Scene) {}

  private add(obj: THREE.Object3D, life: number, tick: (k: number, dt: number) => void) {
    this.scene.add(obj);
    this.live.push({ obj, t: 0, life, tick });
  }

  /** Sword arc in front of a character. */
  slash(pos: THREE.Vector3, yaw: number, height: number, combo: number) {
    const geo = new THREE.RingGeometry(0.9, 1.5, 24, 1, -Math.PI * 0.45, Math.PI * 0.9);
    const mat = new THREE.MeshBasicMaterial({ color: combo === 3 ? 0xffe39a : 0xdff4ff, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending });
    const m = new THREE.Mesh(geo, mat);
    m.position.copy(pos).setY(pos.y + height * 0.55);
    m.rotation.set(-Math.PI / 2 + (combo === 2 ? 0.5 : combo === 1 ? -0.3 : 0), 0, 0);
    const holder = new THREE.Group();
    holder.position.copy(m.position);
    m.position.set(0, 0, 0);
    holder.rotation.y = yaw - Math.PI / 2;
    holder.rotation.z = combo === 2 ? 0.4 : combo === 1 ? -0.3 : 0;
    holder.add(m);
    if (combo === 3) holder.scale.setScalar(1.3);
    this.add(holder, 0.22, (k) => {
      mat.opacity = 0.8 * (1 - k);
      m.rotation.z = -0.8 + k * 1.6;
    });
  }

  burst(pos: THREE.Vector3, color: THREE.ColorRepresentation, n = 14, speed = 4, size = 0.25, life = 0.6) {
    const geo = new THREE.BufferGeometry();
    const p = new Float32Array(n * 3);
    const v: THREE.Vector3[] = [];
    for (let i = 0; i < n; i++) {
      p.set([pos.x, pos.y, pos.z], i * 3);
      v.push(new THREE.Vector3(Math.random() - 0.5, Math.random() * 0.8, Math.random() - 0.5).normalize().multiplyScalar(speed * (0.4 + Math.random() * 0.6)));
    }
    geo.setAttribute("position", new THREE.BufferAttribute(p, 3));
    const mat = new THREE.PointsMaterial({ map: softTexture(), color, size, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    this.add(pts, life, (k, dt) => {
      const a = geo.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < n; i++) {
        v[i].y -= 6 * dt;
        a.setXYZ(i, a.getX(i) + v[i].x * dt, a.getY(i) + v[i].y * dt, a.getZ(i) + v[i].z * dt);
      }
      a.needsUpdate = true;
      mat.opacity = 1 - k;
    });
  }

  /** Expanding ground ring (telegraphs and shockwaves). */
  ring(pos: THREE.Vector3, radius: number, color: THREE.ColorRepresentation, life: number, grow = true) {
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending });
    const m = new THREE.Mesh(new THREE.RingGeometry(0.85, 1, 48).rotateX(-Math.PI / 2), mat);
    m.position.copy(pos).setY(pos.y + 0.08);
    this.add(m, life, (k) => {
      m.scale.setScalar(radius * (grow ? 0.15 + 0.85 * k : 1));
      mat.opacity = 0.75 * (grow ? 1 - k * k : 0.4 + 0.4 * Math.sin(k * 30));
    });
  }

  update(dt: number) {
    for (let i = this.live.length - 1; i >= 0; i--) {
      const l = this.live[i];
      l.t += dt;
      const k = Math.min(1, l.t / l.life);
      l.tick(k, dt);
      if (k >= 1) {
        this.scene.remove(l.obj);
        l.obj.traverse((o) => {
          const m = o as THREE.Mesh;
          if (m.geometry) m.geometry.dispose();
          if (m.material) (m.material as THREE.Material).dispose();
        });
        this.live.splice(i, 1);
      }
    }
  }
}
