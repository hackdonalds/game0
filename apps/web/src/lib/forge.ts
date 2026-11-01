// three.js runtime for forge assets (spec: .claude/skills/asset-forge/references/runtime.md).
// A character is a people's body plus gear bound to the body's skeleton, driven by an appearance: bone and
// morph sliders clamped per people, body regions hidden under gear, dye masks, clips from the family library,
// and props on socket bones.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

export type Gear = { id: string; slot: string; file: string; dye?: string; mask?: string; part: { covers: string[]; hides: string[]; order: number; ownShape?: boolean } };
export type Family = { contract: any; peoples: Record<string, { file: string }>; gear: Gear[]; anims: { id: string; file: string }[] };
export type Manifest = Record<string, Family> & { props: { id: string; file: string; dye?: string }[] };
export type Dyes = { primary: string; secondary: string; accent: string };

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const textures = new THREE.TextureLoader();
const ramp = (() => {
  // Three-step toon ramp for the painterly look
  const t = new THREE.DataTexture(new Uint8Array([90, 90, 90, 255, 185, 185, 185, 255, 255, 255, 255, 255]), 3, 1);
  t.minFilter = t.magFilter = THREE.NearestFilter;
  t.needsUpdate = true;
  return t;
})();

/** Toon material with dye mask (R primary, G secondary, B accent) and body-region hiding. */
function forgeMaterial(source: THREE.Material | undefined, opts: { dyeMask?: THREE.Texture; regions?: boolean; colour?: THREE.Color }) {
  const src = source as THREE.MeshStandardMaterial | undefined;
  const mat = new THREE.MeshToonMaterial({ map: src?.map ?? null, color: opts.colour ?? new THREE.Color(1, 1, 1), gradientMap: ramp,
    side: THREE.DoubleSide, alphaTest: src?.alphaTest ?? 0, transparent: false });
  const uniforms = {
    dyeMask: { value: opts.dyeMask ?? null }, useDye: { value: 0 }, dyeOn: { value: new THREE.Vector3() }, hasMask: { value: opts.dyeMask ? 1 : 0 },
    dyePrimary: { value: new THREE.Color(1, 1, 1) }, dyeSecondary: { value: new THREE.Color(1, 1, 1) }, dyeAccent: { value: new THREE.Color(1, 1, 1) },
    covered: { value: 0 }, useRegions: { value: opts.regions ? 1 : 0 }, hideMask: { value: null as THREE.Texture | null }, useHideMask: { value: 0 },
  };
  mat.userData.forge = uniforms;
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute float region;\nflat varying float vRegion;\nvarying vec2 vForgeUv;")
      .replace("#include <uv_vertex>", "#include <uv_vertex>\nvRegion = region;\nvForgeUv = uv;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>
uniform sampler2D dyeMask; uniform int useDye; uniform vec3 dyeOn; uniform vec3 dyePrimary; uniform vec3 dyeSecondary; uniform vec3 dyeAccent;
uniform int covered; uniform int useRegions; flat varying float vRegion; varying vec2 vForgeUv;
uniform sampler2D hideMask; uniform int useHideMask;`)
      .replace("#include <clipping_planes_fragment>", `#include <clipping_planes_fragment>
if (useRegions == 1 && ((covered >> int(vRegion + 0.5)) & 1) != 0) discard;
if (useHideMask == 1 && texture2D(hideMask, vForgeUv).r > 0.5) discard;`)
      .replace("#include <map_fragment>", `#include <map_fragment>
if (useDye == 1) {
  vec3 m = texture2D(dyeMask, vForgeUv).rgb * dyeOn;
  float l = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
  diffuseColor.rgb = mix(diffuseColor.rgb, l * dyePrimary * 1.6, m.r);
  diffuseColor.rgb = mix(diffuseColor.rgb, l * dyeSecondary * 1.6, m.g);
  diffuseColor.rgb = mix(diffuseColor.rgb, l * dyeAccent * 1.6, m.b);
}`);
  };
  return mat;
}

function applyDyes(material: THREE.Material, dyes: Partial<Dyes> | null) {
  const u = material.userData.forge;
  if (!u?.hasMask.value) return;
  u.useDye.value = dyes ? 1 : 0;
  // A channel without a dye keeps its paint
  u.dyeOn.value.set(dyes?.primary ? 1 : 0, dyes?.secondary ? 1 : 0, dyes?.accent ? 1 : 0);
  if (dyes?.primary) u.dyePrimary.value.set(dyes.primary);
  if (dyes?.secondary) u.dyeSecondary.value.set(dyes.secondary);
  if (dyes?.accent) u.dyeAccent.value.set(dyes.accent);
}

const skinnedMeshes = (root: THREE.Object3D) => {
  const out: THREE.SkinnedMesh[] = [];
  root.traverse((o) => (o as THREE.SkinnedMesh).isSkinnedMesh && out.push(o as THREE.SkinnedMesh));
  return out;
};

export class ForgeCharacter {
  root = new THREE.Group();
  mixer: THREE.AnimationMixer;
  slots = new Map<string, { gear: Gear; meshes: THREE.SkinnedMesh[] }>();
  props = new Map<string, { holder: THREE.Object3D; socket: THREE.Bone }>();
  values: Record<string, number> = {};
  private baseClips: THREE.AnimationClip[] = [];
  private clips: THREE.AnimationClip[] = [];
  private spread = NaN;
  private action?: THREE.AnimationAction;
  private rest = new Map<string, { position: THREE.Vector3; scale: THREE.Vector3 }>();
  private restWorld = new Map<string, THREE.Matrix4>();
  private masks = new Map<string, HTMLImageElement>();
  private hideCanvas = document.createElement("canvas");
  private hideTexture = new THREE.CanvasTexture(this.hideCanvas);

  private constructor(public family: Family, public people: string, private base: string, private body: THREE.Object3D,
                      private bodyMeshes: THREE.SkinnedMesh[]) {
    this.root.add(body);
    this.mixer = new THREE.AnimationMixer(body);
    body.updateMatrixWorld(true);
    body.traverse((o) => {
      if ((o as THREE.Bone).isBone) {
        this.rest.set(o.name, { position: o.position.clone(), scale: o.scale.clone() });
        this.restWorld.set(o.name, o.matrixWorld.clone());
      }
    });
  }

  static async create(manifest: Manifest, base: string, familyName: string, people: string, skin = "#e1c7b9") {
    const family = manifest[familyName] as Family;
    const gltf = await loader.loadAsync(base + family.peoples[people].file);
    const meshes = skinnedMeshes(gltf.scene);
    for (const m of meshes) {
      const uv1 = m.geometry.getAttribute("uv1");
      if (uv1) {
        const region = new Float32Array(uv1.count);
        for (let i = 0; i < uv1.count; i++) region[i] = Math.floor(uv1.getX(i) * 32);
        m.geometry.setAttribute("region", new THREE.BufferAttribute(region, 1));
      }
      // A baked skin texture (bake_skin) is kept and tinted; untextured bodies take the skin colour
      const painted = !!(m.material as THREE.MeshStandardMaterial).map;
      m.material = forgeMaterial(m.material as THREE.Material, { regions: !!uv1, colour: new THREE.Color(painted ? "#ffffff" : skin) });
      m.frustumCulled = false;
    }
    const c = new ForgeCharacter(family, people, base, gltf.scene, meshes);
    // Clips carry the library rig's Hips height: scale that track once for this body, so nothing is rescaled per
    // frame (the mixer skips writes when a value doesn't change, so per-frame scaling would compound)
    const hips = c.rest.get("Hips")!;
    for (const a of family.anims) {
      const lib = await loader.loadAsync(base + a.file);
      const libHips = lib.scene.getObjectByName("Hips");
      const ratio = libHips ? hips.position.y / libHips.position.y : 1;
      for (const clip of lib.animations) {
        const own = clip.clone();
        for (const t of own.tracks) if (t.name === "Hips.position") for (let i = 0; i < t.values.length; i++) t.values[i] *= ratio;
        c.baseClips.push(own);
      }
    }
    c.rebuildClips();
    c.setMorph(`people_${people}`, 1);
    const defaults = family.contract.peoples[people]?.defaults ?? {};
    for (const [k, v] of Object.entries(defaults)) c.setSlider(k, v as number);
    return c;
  }

  get clipNames() { return this.clips.map((c) => c.name); }

  /** Shape key values implied by the current sliders (and the people's signature). */
  private keyValues() {
    const out: Record<string, number> = { [`people_${this.people}`]: 1 };
    for (const [name, v] of Object.entries(this.values)) if (!this.family.contract.sliders.bone[name] && v) out[`${name}_${v > 0 ? "pos" : "neg"}`] = Math.abs(v);
    return out;
  }

  /** Per-character clip copies with the contract's pose offsets (arms spread clear of wider bodies) baked in.
   *  Rebuilt only when the spread changes, never per frame. */
  rebuildClips() {
    const c = this.family.contract;
    const keys = this.keyValues();
    let deg = c.peoples[this.people]?.pose?.armSpread ?? 0;
    for (const [, rule] of Object.entries<any>(c.sliderPose ?? {})) deg += (rule.base ?? 0) + Object.entries<number>(rule.per).reduce((s, [k, w]) => s + w * (keys[k] ?? 0), 0);
    if (deg === this.spread) return;
    this.spread = deg;
    const playing = this.action?.getClip().name;
    const time = this.action?.time ?? 0;
    this.mixer.stopAllAction();
    for (const old of this.clips) this.mixer.uncacheClip(old);
    const sides = c.poseOffsets?.armSpread?.bones ?? {};
    this.clips = this.baseClips.map((clip) => {
      const own = clip.clone();
      for (const t of own.tracks) {
        const bone = t.name.split(".")[0];
        if (!t.name.endsWith(".quaternion") || !(bone in sides) || !deg) continue;
        // Rotate about the character's front axis, expressed in the bone's parent frame, after the clip's rotation
        const parent = this.body.getObjectByName(bone)!.parent!;
        const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(parent.getWorldQuaternion(new THREE.Quaternion()).invert());
        const off = new THREE.Quaternion().setFromAxisAngle(axis.normalize(), THREE.MathUtils.degToRad(deg) * sides[bone]);
        const q = new THREE.Quaternion();
        for (let i = 0; i < t.values.length; i += 4) {
          q.fromArray(t.values, i).premultiply(off).toArray(t.values, i);
        }
      }
      return own;
    });
    if (playing) {
      this.action = this.mixer.clipAction(this.clips.find((x) => x.name === playing)!).play();
      this.action.time = time;
    }
  }
  get bones() { return [...this.rest.keys()]; }

  /** Slider value in [-1, 1], clamped to the people's range. Bone sliders move bones; morph sliders set key pairs. */
  setSlider(name: string, value: number) {
    const [lo, hi] = this.family.contract.peoples[this.people]?.clamp?.[name] ?? [-1, 1];
    const v = THREE.MathUtils.clamp(value, lo, hi);
    this.values[name] = v;
    const bone = this.family.contract.sliders.bone[name];
    if (bone) this.applyBoneSliders();
    else {
      this.setMorph(`${name}_pos`, Math.max(v, 0));
      this.setMorph(`${name}_neg`, Math.max(-v, 0));
      if (this.baseClips.length) this.rebuildClips();
    }
    return v;
  }

  range(name: string): [number, number] {
    return this.family.contract.peoples[this.people]?.clamp?.[name] ?? [-1, 1];
  }

  /** Expressions (ARKit names) and raw shape keys, on the body and every worn piece that has the key. */
  setMorph(key: string, w: number) {
    for (const m of this.allMeshes()) {
      const i = m.morphTargetDictionary?.[key];
      if (i !== undefined) m.morphTargetInfluences![i] = w;
    }
  }

  private allMeshes() {
    return [...this.bodyMeshes, ...[...this.slots.values()].flatMap((s) => s.meshes)];
  }

  private applyBoneSliders() {
    for (const [name, r] of this.rest) {
      const b = this.body.getObjectByName(name)!;
      b.position.copy(r.position);
      b.scale.copy(r.scale);
    }
    for (const [name, def] of Object.entries<any>(this.family.contract.sliders.bone)) {
      const v = this.values[name] ?? 0;
      if (!v) continue;
      for (const boneName of def.bones) {
        const b = this.body.getObjectByName(boneName);
        if (!b) continue;
        const amount = v * def.amount;
        if (def.op === "uniformScale") {
          b.scale.multiplyScalar(1 + amount);
        } else if (def.op === "translateOut") b.position.x += boneName.startsWith("Left") ? amount : -amount;
        else if (def.op === "translateUp") b.position.y += amount;
        else if (def.op === "translateAlongLimb") b.position.add(this.rest.get(boneName)!.position.clone().normalize().multiplyScalar(amount));
      }
    }
  }

  /** Equip a gear piece (or clear the slot), bound to the body's skeleton by bone name. */
  async equip(slot: string, id: string | null, dyes?: Partial<Dyes>) {
    for (const m of this.slots.get(slot)?.meshes ?? []) m.removeFromParent();
    this.slots.delete(slot);
    if (id) {
      const gear = this.family.gear.find((g) => g.slot === slot && g.id === id)!;
      const gltf = await loader.loadAsync(this.base + gear.file);
      const mask = gear.dye ? await textures.loadAsync(this.base + gear.dye) : undefined;
      if (mask) {
        mask.flipY = false;
        mask.colorSpace = THREE.NoColorSpace;
      }
      const skel = this.bodyMeshes[0].skeleton;
      const meshes = skinnedMeshes(gltf.scene);
      gltf.scene.updateMatrixWorld(true);
      for (const m of meshes) {
        // The gear's joints, in its own order, mapped to the body's bones. Bind poses are the body's rest pose
        // times the gear's own dequantisation (meshopt builds fold it into each file's inverse bind matrices).
        const dequant = m.skeleton.bones[0].matrixWorld.clone().multiply(m.skeleton.boneInverses[0]);
        const bones = m.skeleton.bones.map((b) => skel.getBoneByName(b.name)!);
        const inverses = bones.map((b) => this.restWorld.get(b.name)!.clone().invert().multiply(dequant));
        m.bind(new THREE.Skeleton(bones, inverses), this.bodyMeshes[0].bindMatrix);
        m.material = forgeMaterial(m.material as THREE.Material, { dyeMask: mask });
        m.frustumCulled = false;
        m.renderOrder = gear.part.order;
        this.root.add(m);
      }
      if (gear.mask && !this.masks.has(gear.mask)) {
        const img = new Image();
        img.src = this.base + gear.mask;
        await img.decode();
        this.masks.set(gear.mask, img);
      }
      this.slots.set(slot, { gear, meshes });
      this.setMorph(`people_${this.people}`, 1);
      for (const name of Object.keys(this.values)) if (!this.family.contract.sliders.bone[name]) this.setSlider(name, this.values[name]);
      if (dyes) this.dye(slot, dyes);
    }
    this.refreshCovered();
  }

  /** Dye colours for a worn piece; until a dye is applied the piece shows its painted colours. */
  dye(slot: string, dyes: Partial<Dyes> | null) {
    for (const m of this.slots.get(slot)?.meshes ?? []) applyDyes(m.material as THREE.Material, dyes);
  }

  /** Skin colour: replaces an untextured body's colour, or tints a baked skin texture towards it. */
  skin(colour: string) {
    for (const m of this.bodyMeshes) {
      const mat = m.material as THREE.MeshToonMaterial;
      mat.color.set(mat.map ? new THREE.Color("#ffffff").lerp(new THREE.Color(colour), 0.45) : colour);
    }
  }

  private refreshCovered() {
    const regions: string[] = this.family.contract.regions;
    const hidden = new Set([...this.slots.values()].flatMap((s) => s.gear.part.hides));
    let covered = 0;
    for (const [slot, s] of this.slots) {
      const visible = !hidden.has(slot);
      s.meshes.forEach((m) => (m.visible = visible));
      if (visible) for (const r of s.gear.part.covers) covered |= 1 << regions.indexOf(r);
    }
    // One body mask: every visible piece's mask, combined
    const shown = [...this.slots.entries()].filter(([slot, s]) => !hidden.has(slot) && s.gear.mask).map(([, s]) => this.masks.get(s.gear.mask!)!);
    if (shown.length) {
      this.hideCanvas.width = shown[0].width;
      this.hideCanvas.height = shown[0].height;
      const ctx = this.hideCanvas.getContext("2d")!;
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, this.hideCanvas.width, this.hideCanvas.height);
      ctx.globalCompositeOperation = "lighten";
      for (const img of shown) ctx.drawImage(img, 0, 0, this.hideCanvas.width, this.hideCanvas.height);
      this.hideTexture.flipY = false;
      this.hideTexture.colorSpace = THREE.NoColorSpace;
      this.hideTexture.minFilter = this.hideTexture.magFilter = THREE.NearestFilter;
      this.hideTexture.generateMipmaps = false;
      this.hideTexture.needsUpdate = true;
    }
    for (const m of this.bodyMeshes) {
      const u = (m.material as THREE.Material).userData.forge;
      u.covered.value = covered;
      u.hideMask.value = this.hideTexture;
      u.useHideMask.value = shown.length ? 1 : 0;
    }
  }

  play(name: string | null) {
    this.action?.fadeOut(0.25);
    const clip = this.clips.find((c) => c.name === name);
    this.action = clip ? this.mixer.clipAction(clip).reset().fadeIn(0.25).play() : undefined;
  }

  /** Hold a prop on a socket bone; its Grip origin sits on the socket. */
  async hold(socket: string, file: string | null, dyes?: Partial<Dyes>, dyeFile?: string) {
    const current = this.props.get(socket);
    current?.holder.removeFromParent();
    this.props.delete(socket);
    if (!file) return;
    const bone = this.body.getObjectByName(socket) as THREE.Bone;
    const gltf = await loader.loadAsync(this.base + file);
    const mask = dyeFile ? await textures.loadAsync(this.base + dyeFile) : undefined;
    if (mask) {
      mask.flipY = false;
      mask.colorSpace = THREE.NoColorSpace;
    }
    gltf.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        m.material = forgeMaterial(m.material as THREE.Material, { dyeMask: mask });
        if (dyes) applyDyes(m.material as THREE.Material, dyes);
      }
    });
    const grip = gltf.scene.getObjectByName("Grip");
    const holder = new THREE.Group();
    if (grip) gltf.scene.position.sub(grip.position);
    holder.add(gltf.scene);
    bone.add(holder);
    this.props.set(socket, { holder, socket: bone });
  }

  update(dt: number) {
    this.mixer.update(dt);
    // Props keep their real size whatever the hand or body sliders do
    for (const { holder, socket } of this.props.values()) {
      const s = socket.getWorldScale(new THREE.Vector3());
      holder.scale.set(1 / s.x, 1 / s.y, 1 / s.z);
    }
  }
}
