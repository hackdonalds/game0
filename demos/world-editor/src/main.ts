import * as THREE from "three";
import { MapControls } from "three/addons/controls/MapControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import GUI from "lil-gui";
import {
  BIOMES, PEOPLES, STATES, TIERS, WIND_KINDS,
  emptyWorld, generateWorld, newIsle, parseWorld, uid,
  type Biome, type Isle, type Tier, type Wind, type World,
} from "./world";

// Worlds saved in the repo's worlds/ folder, bundled into the editor
const LIBRARY: Record<string, unknown> = Object.fromEntries(
  Object.entries(import.meta.glob("../../../worlds/*.world.json", { eager: true, import: "default" }))
    .map(([path, data]) => [path.split("/").pop()!.replace(".world.json", ""), data]),
);

// ---------- Scene ----------

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(renderer.domElement);
const canvas = renderer.domElement;

const labels = new CSS2DRenderer();
labels.setSize(innerWidth, innerHeight);
Object.assign(labels.domElement.style, { position: "fixed", inset: "0", pointerEvents: "none" });
document.body.append(labels.domElement);

const scene = new THREE.Scene();
const SKY = new THREE.Color(0x9cc3e6);
scene.background = SKY;
scene.fog = new THREE.Fog(SKY, 1500, 6000);
scene.add(new THREE.HemisphereLight(0xfff4dc, 0x5a7f8f, 2.2));
const sun = new THREE.DirectionalLight(0xffd79a, 2.4);
sun.position.set(1, 2, 1.4);
scene.add(sun);

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 1, 12000);

// Our pointer handler is registered before MapControls so it can claim a drag before the camera pans
canvas.addEventListener("pointerdown", onPointerDown);
const controls = new MapControls(camera, canvas);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.47;

const root = new THREE.Group();
scene.add(root);

// ---------- State ----------

type Selection = { type: "isle" | "wind" | "bridge"; id: string } | null;
type Tool = "select" | "isle" | "wind" | "bridge";

const STORAGE = "game0.world-editor";
let world: World = load();
let selection: Selection = null;
let tool: Tool = "select";
let snapshot = JSON.stringify(world);
const undoStack: string[] = [];
const redoStack: string[] = [];

function load(): World {
  try {
    const saved = localStorage.getItem(STORAGE);
    if (saved) return parseWorld(JSON.parse(saved));
  } catch { /* fall through to the library */ }
  const first = LIBRARY["first-shard"] ?? Object.values(LIBRARY)[0];
  return first ? parseWorld(structuredClone(first)) : generateWorld(7, "Shard of the Accord");
}

/** Record the current world as one undoable step, save it, and redraw. */
function commit() {
  const next = JSON.stringify(world);
  if (next === snapshot) return rebuild();
  undoStack.push(snapshot);
  if (undoStack.length > 200) undoStack.shift();
  redoStack.length = 0;
  snapshot = next;
  try { localStorage.setItem(STORAGE, next); } catch { /* storage may be unavailable */ }
  rebuild();
  gui.controllersRecursive().forEach((c) => c.updateDisplay());
}

function restore(from: string[], to: string[]) {
  const prev = from.pop();
  if (!prev) return;
  to.push(snapshot);
  snapshot = prev;
  world = parseWorld(JSON.parse(prev));
  try { localStorage.setItem(STORAGE, prev); } catch { /* ignore */ }
  if (selection && !find(selection)) selection = null;
  rebuild();
  buildGui();
}

function replaceWorld(next: World) {
  world = next;
  selection = null;
  commit();
  frame();
  buildGui();
}

function find(sel: NonNullable<Selection>) {
  const list = sel.type === "isle" ? world.isles : sel.type === "wind" ? world.winds : world.bridges;
  return (list as { id: string }[]).find((o) => o.id === sel.id);
}
const isleById = (id: string) => world.isles.find((i) => i.id === id);

// ---------- Drawing ----------

const TIER_COLOR: Record<Tier, number> = { safe: 0xf2c14e, guarded: 0x3fb6a8, wild: 0xe0533d };
const BIOME_COLOR: Record<Biome, number> = { meadow: 0x8fbf5a, forest: 0x4f8a3c, roothold: 0x6f9a3a, crag: 0xa9a196, garden: 0x9bc86a, lagoon: 0x7fbf8a, ruin: 0xb7a98c };
const ROCK_COLOR: Record<Biome, number> = { meadow: 0x8a6b4f, forest: 0x7a5d44, roothold: 0x6b4e36, crag: 0x8c857c, garden: 0x8a6b4f, lagoon: 0x7d6a58, ruin: 0x857a6c };

const hash = (s: string) => [...s].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 16777619), 2166136261) >>> 0;
function seeded(seed: number) {
  let a = seed;
  return () => ((a = Math.imul(a ^ (a >>> 15), a | 1) + 0x6d2b79f5) >>> 0) / 4294967296;
}
const mat = (color: number, extra: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.9, ...extra });

const windViews: { wind: Wind; curve: THREE.Curve<THREE.Vector3>; length: number; arrows: THREE.InstancedMesh }[] = [];
let selectionRing: THREE.Object3D | undefined;
let storm: THREE.Mesh;
let boundary: THREE.LineLoop;

function clearRoot() {
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    m.geometry?.dispose();
    (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => x?.dispose());
    if (o instanceof CSS2DObject) o.element.remove();
  });
  root.clear();
  windViews.length = 0;
}

function rebuild() {
  clearRoot();
  selectionRing = undefined;

  storm = new THREE.Mesh(new THREE.CircleGeometry(world.size * 3, 64), new THREE.MeshStandardMaterial({ color: 0x8fa6bf, roughness: 1 }));
  storm.rotation.x = -Math.PI / 2;
  storm.position.y = world.stormY;
  const haze = new THREE.Mesh(new THREE.CircleGeometry(world.size * 3, 64), new THREE.MeshBasicMaterial({ color: 0xf4f8fc, transparent: true, opacity: 0.45, depthWrite: false }));
  haze.rotation.x = -Math.PI / 2;
  haze.position.y = world.stormY + 12;
  boundary = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(Array.from({ length: 128 }, (_, k) => new THREE.Vector3(Math.cos((k / 128) * Math.PI * 2) * world.size, 0, Math.sin((k / 128) * Math.PI * 2) * world.size))),
    new THREE.LineDashedMaterial({ color: 0xffffff, dashSize: 20, gapSize: 14, transparent: true, opacity: 0.6 }),
  );
  boundary.computeLineDistances();
  root.add(storm, haze, boundary);

  world.isles.forEach((i) => root.add(isleView(i)));
  world.bridges.forEach((b) => {
    const v = bridgeView(b.a, b.b);
    if (v) { v.userData = { type: "bridge", id: b.id }; root.add(v); }
  });
  world.winds.forEach((w) => root.add(windView(w)));
  drawSelection();
  updateHelp();
}

function isleView(i: Isle) {
  const g = new THREE.Group();
  g.position.set(i.x, i.y, i.z);
  g.userData = { type: "isle", id: i.id };
  const r = i.radius;
  const rand = seeded(hash(i.id));
  const s1 = rand() * 6, s2 = rand() * 6;
  const outline = (geo: THREE.BufferGeometry) => {
    const p = geo.attributes.position;
    for (let k = 0; k < p.count; k++) {
      const a = Math.atan2(p.getZ(k), p.getX(k));
      const f = 1 + 0.12 * Math.sin(a * 3 + s1) + 0.07 * Math.sin(a * 5 + s2);
      p.setX(k, p.getX(k) * f);
      p.setZ(k, p.getZ(k) * f);
    }
    geo.computeVertexNormals();
    return geo;
  };
  const sinking = i.state === "sinking";
  const tint = (c: number) => (sinking ? new THREE.Color(c).lerp(new THREE.Color(0x3a2a2a), 0.45).getHex() : c);

  const top = new THREE.Mesh(outline(new THREE.CylinderGeometry(r, r * 0.92, r * 0.18, 16)), mat(tint(BIOME_COLOR[i.biome])));
  top.position.y = -r * 0.09;
  const under = new THREE.Mesh(outline(new THREE.ConeGeometry(r * 0.92, r * 1.3, 16)), mat(tint(ROCK_COLOR[i.biome])));
  under.rotation.x = Math.PI;
  under.position.y = -r * 0.18 - r * 0.65;
  g.add(top, under);

  const ring = new THREE.Mesh(new THREE.RingGeometry(r * 1.2, r * 1.28, 64), new THREE.MeshBasicMaterial({ color: TIER_COLOR[i.tier], transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthWrite: false }));
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.5;
  g.add(ring);

  const onTop = (m: THREE.Object3D, spread: number, h = 0) => {
    const a = rand() * Math.PI * 2, d = Math.sqrt(rand()) * r * spread;
    m.position.set(Math.cos(a) * d, h, Math.sin(a) * d);
    g.add(m);
    return m;
  };
  if (i.biome === "lagoon") {
    const water = new THREE.Mesh(outline(new THREE.CircleGeometry(r * 0.55, 20)), mat(0x5fd6e8, { emissive: 0x2aa6c0, emissiveIntensity: 0.6 }));
    water.rotation.x = -Math.PI / 2;
    water.position.y = 0.6;
    g.add(water);
  }
  if (i.biome === "forest" || i.biome === "roothold") for (let k = 0; k < 7; k++) {
    const h = r * (0.18 + rand() * 0.12);
    onTop(new THREE.Mesh(new THREE.ConeGeometry(h * 0.35, h, 6), mat(0x3d6e33)), 0.75, h / 2);
  }
  if (i.biome === "crag") for (let k = 0; k < 3; k++) {
    const h = r * (0.4 + rand() * 0.5);
    onTop(new THREE.Mesh(new THREE.ConeGeometry(h * 0.28, h, 5), mat(0x9b948a)), 0.6, h / 2);
  }
  if (i.biome === "garden") for (let k = 0; k < 4; k++) {
    const t = new THREE.Mesh(new THREE.CylinderGeometry(r * (0.55 - k * 0.12), r * (0.58 - k * 0.12), r * 0.05, 16), mat(k % 2 ? 0xb7d77a : 0x86b552));
    t.position.y = r * 0.025 + k * r * 0.05;
    g.add(t);
  }
  if (i.biome === "ruin") for (let k = 0; k < 6; k++) {
    const h = r * (0.08 + rand() * 0.25);
    onTop(new THREE.Mesh(new THREE.BoxGeometry(r * 0.06, h, r * 0.06), mat(0xd8cdb4)), 0.7, h / 2);
  }
  if (i.ancientTree) {
    const tree = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.05, r * 0.09, r * 0.6, 7), mat(0x5b3f2a));
    trunk.position.y = r * 0.3;
    const crown = new THREE.Mesh(new THREE.IcosahedronGeometry(r * 0.32, 0), mat(0xc9b84a, { emissive: 0x5a4a10, emissiveIntensity: 0.4 }));
    crown.position.y = r * 0.68;
    tree.add(trunk, crown);
    g.add(tree);
  }
  if (i.town) for (let k = 0; k < 9; k++) {
    const house = new THREE.Group();
    const w = r * 0.07, h = r * (0.05 + rand() * 0.05);
    const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), mat(0xf1e6cf));
    body.position.y = h / 2;
    const roof = new THREE.Mesh(new THREE.ConeGeometry(w * 0.8, w * 0.7, 4), mat(0xb5553b));
    roof.position.y = h + w * 0.35;
    roof.rotation.y = Math.PI / 4;
    house.add(body, roof);
    onTop(house, 0.45);
  }
  if (i.shrine) {
    const shrine = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.03, r * 0.05, r * 0.35, 6), mat(0x9ff2e6, { emissive: 0x39d6c2, emissiveIntensity: 1.2 }));
    shrine.position.set(r * 0.62, r * 0.175, 0);
    g.add(shrine);
  }
  if (i.state === "newborn") {
    const glow = new THREE.Mesh(new THREE.TorusGeometry(r * 0.95, r * 0.04, 6, 48), new THREE.MeshBasicMaterial({ color: 0x9fe9ff }));
    glow.rotation.x = Math.PI / 2;
    g.add(glow);
  }
  if (sinking) g.rotation.set(0.1, 0, 0.14);

  const el = document.createElement("div");
  el.className = "label";
  const detail = [i.tier, i.people !== "none" ? i.people : "", i.state !== "stable" ? i.state : ""].filter(Boolean).join(" · ");
  el.innerHTML = `${escape(i.name)}<small>${detail}</small>`;
  const label = new CSS2DObject(el);
  label.position.y = r * (i.ancientTree ? 1.15 : 0.6);
  g.add(label);
  return g;
}

const escape = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

function bridgeView(aId: string, bId: string) {
  const a = isleById(aId), b = isleById(bId);
  if (!a || !b) return;
  const pa = new THREE.Vector3(a.x, a.y, a.z), pb = new THREE.Vector3(b.x, b.y, b.z);
  const dir = pb.clone().sub(pa).setY(0).normalize();
  pa.addScaledVector(dir, a.radius * 0.9);
  pb.addScaledVector(dir, -b.radius * 0.9);
  const len = pa.distanceTo(pb);
  const g = new THREE.Group();
  const deck = new THREE.Mesh(new THREE.BoxGeometry(5, 1, len), mat(0xa77b4f));
  const rope = new THREE.Mesh(new THREE.BoxGeometry(6, 0.4, len), mat(0x6e5236));
  rope.position.y = 3;
  g.add(deck, rope);
  g.position.copy(pa).lerp(pb, 0.5);
  g.lookAt(pb);
  return g;
}

function windCurve(w: Wind) {
  const pts = w.points.map(([x, z]) => new THREE.Vector3(x, w.y, z));
  const closed = pts.length > 2 && pts[0].distanceTo(pts[pts.length - 1]) < 1;
  if (closed) pts.pop();
  return new THREE.CatmullRomCurve3(pts, closed, "centripetal");
}

function windView(w: Wind) {
  const g = new THREE.Group();
  const curve = windCurve(w);
  const length = curve.getLength();
  const steps = Math.max(16, Math.ceil(length / 12));
  const color = w.kind === "lane" ? 0xcfe8ff : 0xff9a3c;

  // Flat ribbon showing the current's width
  const pos: number[] = [];
  const idx: number[] = [];
  const up = new THREE.Vector3(0, 1, 0);
  for (let k = 0; k <= steps; k++) {
    const u = k / steps;
    const p = curve.getPointAt(u), t = curve.getTangentAt(u);
    const side = new THREE.Vector3().crossVectors(t, up).normalize().multiplyScalar(w.width / 2);
    pos.push(p.x + side.x, p.y, p.z + side.z, p.x - side.x, p.y, p.z - side.z);
    if (k < steps) idx.push(k * 2, k * 2 + 1, k * 2 + 2, k * 2 + 1, k * 2 + 3, k * 2 + 2);
  }
  const ribbonGeo = new THREE.BufferGeometry();
  ribbonGeo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  ribbonGeo.setIndex(idx);
  const ribbon = new THREE.Mesh(ribbonGeo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.14 + w.gustiness * 0.08, side: THREE.DoubleSide, depthWrite: false }));
  ribbon.userData = { type: "wind", id: w.id };
  g.add(ribbon);

  const core = new THREE.Mesh(new THREE.TubeGeometry(curve, steps, 1.2, 5, curve.closed), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7 }));
  core.userData = { type: "wind", id: w.id };
  g.add(core);

  // Chevrons that drift along the current at a speed scaled from its strength
  const count = Math.max(4, Math.round(length / 45));
  const arrowGeo = new THREE.ConeGeometry(Math.min(8, w.width * 0.12), 16, 4);
  arrowGeo.rotateX(Math.PI / 2);
  const arrows = new THREE.InstancedMesh(arrowGeo, new THREE.MeshBasicMaterial({ color }), count);
  arrows.userData = { type: "wind", id: w.id };
  g.add(arrows);
  windViews.push({ wind: w, curve, length, arrows });

  const el = document.createElement("div");
  el.className = "label wind";
  el.textContent = `${w.name} · ${w.strength} m/s`;
  const label = new CSS2DObject(el);
  label.position.copy(curve.getPointAt(0.5)).add(new THREE.Vector3(0, 8, 0));
  g.add(label);
  return g;
}

const dummy = new THREE.Object3D();
function animateWinds(time: number) {
  for (const v of windViews) {
    const n = v.arrows.count;
    const shift = (time * v.wind.strength * 3) / v.length;
    for (let k = 0; k < n; k++) {
      const u = (((k / n + shift) % 1) + 1) % 1;
      const p = v.curve.getPointAt(u);
      dummy.position.copy(p);
      dummy.lookAt(p.clone().add(v.curve.getTangentAt(u)));
      const gust = 1 + Math.sin(time * 4 + k * 1.7) * v.wind.gustiness * 0.4;
      dummy.scale.setScalar(gust);
      dummy.updateMatrix();
      v.arrows.setMatrixAt(k, dummy.matrix);
    }
    v.arrows.instanceMatrix.needsUpdate = true;
  }
}

function drawSelection() {
  if (selectionRing) root.remove(selectionRing);
  selectionRing = undefined;
  if (!selection) return;
  const g = new THREE.Group();
  if (selection.type === "isle") {
    const i = isleById(selection.id)!;
    const ring = new THREE.Mesh(new THREE.RingGeometry(i.radius * 1.36, i.radius * 1.46, 64), new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide, depthWrite: false, transparent: true }));
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(i.x, i.y + 0.6, i.z);
    g.add(ring);
  } else if (selection.type === "wind") {
    const w = world.winds.find((x) => x.id === selection!.id)!;
    w.points.forEach(([x, z], index) => {
      const h = new THREE.Mesh(new THREE.SphereGeometry(7, 12, 8), new THREE.MeshBasicMaterial({ color: index === 0 ? 0x7dffb0 : 0xffffff }));
      h.position.set(x, w.y, z);
      h.userData = { type: "handle", id: w.id, index };
      g.add(h);
    });
  } else {
    const b = world.bridges.find((x) => x.id === selection!.id)!;
    const v = bridgeView(b.a, b.b);
    if (v) {
      v.traverse((o) => { if ((o as THREE.Mesh).isMesh) (o as THREE.Mesh).material = new THREE.MeshBasicMaterial({ color: 0xffffff }); });
      v.scale.set(1.6, 2, 1);
      g.add(v);
    }
  }
  selectionRing = g;
  root.add(g);
}

// ---------- Interaction ----------

const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const DRAFT_Y = 10;

function setNdc(e: PointerEvent | MouseEvent) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
}

function hit(): { type: string; id: string; index?: number } | undefined {
  const hits = raycaster.intersectObjects(root.children, true);
  // Handles win over everything, then isles and bridges, then wind ribbons
  const tagged = hits.map((h) => {
    let o: THREE.Object3D | null = h.object;
    while (o && !o.userData.type) o = o.parent;
    return o?.userData as { type: string; id: string; index?: number } | undefined;
  }).filter(Boolean) as { type: string; id: string; index?: number }[];
  const rank = (t: string) => ["handle", "isle", "bridge", "wind"].indexOf(t);
  return tagged.sort((a, b) => rank(a.type) - rank(b.type))[0];
}

function onPlane(y: number) {
  const p = new THREE.Vector3();
  return raycaster.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -y), p) ? p : undefined;
}

type Drag =
  | { kind: "isle"; isle: Isle; offset: THREE.Vector3; view: THREE.Object3D }
  | { kind: "handle"; wind: Wind; index: number }
  | { kind: "wind"; wind: Wind; start: THREE.Vector3; original: [number, number][] }
  | { kind: "empty"; x: number; y: number };
let drag: Drag | undefined;
let bridgeFrom: string | undefined;
let draft: [number, number][] = [];
let draftLine: THREE.Line | undefined;

function select(sel: Selection) {
  selection = sel;
  drawSelection();
  buildGui();
}

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return;
  setNdc(e);
  const target = hit();
  controls.enabled = true;

  if (tool === "isle") {
    const p = onPlane(0);
    if (!p) return;
    controls.enabled = false;
    const isle = newIsle(Math.round(p.x), Math.round(p.z));
    world.isles.push(isle);
    selection = { type: "isle", id: isle.id };
    commit();
    buildGui();
    return;
  }
  if (tool === "wind") {
    const p = onPlane(DRAFT_Y);
    if (!p) return;
    controls.enabled = false;
    draft.push([Math.round(p.x), Math.round(p.z)]);
    drawDraft();
    return;
  }
  if (tool === "bridge") {
    controls.enabled = false;
    if (target?.type !== "isle") { bridgeFrom = undefined; return updateHelp(); }
    if (!bridgeFrom || bridgeFrom === target.id) {
      bridgeFrom = target.id;
      select({ type: "isle", id: target.id });
      return updateHelp();
    }
    const a = bridgeFrom, b = target.id;
    if (!world.bridges.some((x) => (x.a === a && x.b === b) || (x.a === b && x.b === a))) {
      const bridge = { id: uid("bridge"), a, b };
      world.bridges.push(bridge);
      selection = { type: "bridge", id: bridge.id };
      commit();
      buildGui();
    }
    bridgeFrom = undefined;
    return updateHelp();
  }

  // Select tool
  if (!target) { drag = { kind: "empty", x: e.clientX, y: e.clientY }; return; }
  controls.enabled = false;
  canvas.setPointerCapture(e.pointerId);
  if (target.type === "handle") {
    drag = { kind: "handle", wind: world.winds.find((w) => w.id === target.id)!, index: target.index! };
  } else if (target.type === "isle") {
    const isle = isleById(target.id)!;
    if (selection?.id !== isle.id) select({ type: "isle", id: isle.id });
    const p = onPlane(isle.y)!;
    const view = root.children.find((o) => o.userData.id === isle.id)!;
    drag = { kind: "isle", isle, offset: new THREE.Vector3(isle.x, isle.y, isle.z).sub(p), view };
  } else if (target.type === "wind") {
    const wind = world.winds.find((w) => w.id === target.id)!;
    if (selection?.id !== wind.id) select({ type: "wind", id: wind.id });
    drag = { kind: "wind", wind, start: onPlane(wind.y)!, original: wind.points.map((p) => [...p] as [number, number]) };
  } else if (target.type === "bridge") {
    select({ type: "bridge", id: target.id });
  }
}

canvas.addEventListener("pointermove", (e) => {
  setNdc(e);
  if (!drag) {
    const t = tool === "select" || tool === "bridge" ? hit() : undefined;
    canvas.style.cursor = tool === "isle" || tool === "wind" ? "crosshair" : t ? "pointer" : "";
    if (tool === "wind" && draft.length) drawDraft(onPlane(DRAFT_Y));
    return;
  }
  if (drag.kind === "isle") {
    const p = onPlane(drag.isle.y);
    if (!p) return;
    p.add(drag.offset);
    drag.isle.x = Math.round(p.x);
    drag.isle.z = Math.round(p.z);
    drag.view.position.set(drag.isle.x, drag.isle.y, drag.isle.z);
    drawSelection();
  } else if (drag.kind === "handle") {
    const p = onPlane(drag.wind.y);
    if (!p) return;
    const pts = drag.wind.points;
    const closed = pts.length > 2 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1];
    pts[drag.index] = [Math.round(p.x), Math.round(p.z)];
    // Keep closed loops closed when moving their shared end point
    if (closed && drag.index === 0) pts[pts.length - 1] = [...pts[0]];
    if (closed && drag.index === pts.length - 1) pts[0] = [...pts[pts.length - 1]];
    rebuild();
  } else if (drag.kind === "wind") {
    const p = onPlane(drag.wind.y);
    if (!p) return;
    const dx = Math.round(p.x - drag.start.x), dz = Math.round(p.z - drag.start.z);
    drag.wind.points = drag.original.map(([x, z]) => [x + dx, z + dz]);
    rebuild();
  }
});

addEventListener("pointerup", (e) => {
  const d = drag;
  drag = undefined;
  controls.enabled = true;
  if (!d) return;
  if (d.kind === "empty") {
    if (Math.hypot(e.clientX - d.x, e.clientY - d.y) < 4) select(null);
    return;
  }
  commit();
});

canvas.addEventListener("dblclick", () => { if (tool === "wind") finishDraft(); });

function drawDraft(cursor?: THREE.Vector3) {
  if (draftLine) { scene.remove(draftLine); draftLine.geometry.dispose(); }
  const pts = draft.map(([x, z]) => new THREE.Vector3(x, DRAFT_Y, z));
  if (cursor) pts.push(cursor);
  draftLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xffffff }));
  scene.add(draftLine);
  updateHelp();
}

function finishDraft() {
  // A double-click adds the same point twice; drop near-duplicates
  const pts = draft.filter((p, k) => k === 0 || Math.hypot(p[0] - draft[k - 1][0], p[1] - draft[k - 1][1]) > 3);
  if (pts.length >= 2) {
    const wind: Wind = { id: uid("wind"), name: `Wind ${world.winds.length + 1}`, kind: "lane", points: pts, y: DRAFT_Y, width: 60, strength: 12, gustiness: 0.2 };
    world.winds.push(wind);
    selection = { type: "wind", id: wind.id };
    commit();
    buildGui();
  }
  cancelDraft();
}

function cancelDraft() {
  draft = [];
  if (draftLine) { scene.remove(draftLine); draftLine.geometry.dispose(); draftLine = undefined; }
  updateHelp();
}

function deleteSelection() {
  if (!selection) return;
  const id = selection.id;
  if (selection.type === "isle") {
    world.isles = world.isles.filter((i) => i.id !== id);
    world.bridges = world.bridges.filter((b) => b.a !== id && b.b !== id);
  } else if (selection.type === "wind") world.winds = world.winds.filter((w) => w.id !== id);
  else world.bridges = world.bridges.filter((b) => b.id !== id);
  selection = null;
  commit();
  buildGui();
}

function duplicateSelection() {
  if (selection?.type === "isle") {
    const src = isleById(selection.id)!;
    const copy = { ...src, id: uid("isle"), name: `${src.name} copy`, x: src.x + src.radius * 2.6 };
    world.isles.push(copy);
    selection = { type: "isle", id: copy.id };
  } else if (selection?.type === "wind") {
    const src = world.winds.find((w) => w.id === selection!.id)!;
    const copy = { ...src, id: uid("wind"), name: `${src.name} copy`, points: src.points.map(([x, z]) => [x + 80, z + 80] as [number, number]) };
    world.winds.push(copy);
    selection = { type: "wind", id: copy.id };
  } else return;
  commit();
  buildGui();
}

function setTool(t: Tool) {
  if (tool === "wind" && t !== "wind") cancelDraft();
  tool = t;
  bridgeFrom = undefined;
  document.querySelectorAll<HTMLButtonElement>("#tools button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tool === t)));
  canvas.style.cursor = t === "isle" || t === "wind" ? "crosshair" : "";
  updateHelp();
}

document.querySelectorAll<HTMLButtonElement>("#tools button").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool as Tool)));

addEventListener("keydown", (e) => {
  if ((e.target as HTMLElement).closest("input, textarea, select")) return;
  const mod = e.ctrlKey || e.metaKey;
  if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); return e.shiftKey ? restore(redoStack, undoStack) : restore(undoStack, redoStack); }
  if (mod && e.key.toLowerCase() === "y") { e.preventDefault(); return restore(redoStack, undoStack); }
  if (mod && e.key.toLowerCase() === "d") { e.preventDefault(); return duplicateSelection(); }
  if (mod) return;
  if (e.key === "Enter" && tool === "wind") return finishDraft();
  if (e.key === "Escape") { if (draft.length) return cancelDraft(); bridgeFrom = undefined; return select(null); }
  if (e.key === "Backspace" && tool === "wind" && draft.length) { draft.pop(); return drawDraft(); }
  if (e.key === "Delete" || e.key === "Backspace") return deleteSelection();
  if (e.key === "f" || e.key === "F") return frame();
  const tools: Record<string, Tool> = { v: "select", i: "isle", w: "wind", b: "bridge" };
  if (tools[e.key.toLowerCase()]) setTool(tools[e.key.toLowerCase()]);
});

// ---------- File actions ----------

const fileInput = document.getElementById("file") as HTMLInputElement;
document.getElementById("undo")!.addEventListener("click", () => restore(undoStack, redoStack));
document.getElementById("redo")!.addEventListener("click", () => restore(redoStack, undoStack));
document.getElementById("new")!.addEventListener("click", () => { if (confirm("Start an empty world? You can undo this.")) replaceWorld(emptyWorld()); });
document.getElementById("generate")!.addEventListener("click", () => {
  const seed = Math.floor(Math.random() * 100000);
  replaceWorld(generateWorld(seed));
});
document.getElementById("import")!.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  fileInput.value = "";
  if (!file) return;
  try {
    replaceWorld(parseWorld(JSON.parse(await file.text())));
  } catch (err) {
    alert(`Couldn't import ${file.name}: ${(err as Error).message}`);
  }
});
document.getElementById("export")!.addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(world, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${world.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "world"}.world.json`;
  a.click();
  URL.revokeObjectURL(a.href);
});

// ---------- Properties panel ----------

let gui = new GUI({ title: "World" });

function buildGui() {
  gui.destroy();
  const sel = selection && find(selection);
  if (!selection || !sel) {
    gui = new GUI({ title: "World" });
    gui.add(world, "name").onFinishChange(commit);
    gui.add(world, "size", 300, 4000, 50).name("radius (m)").onChange(rebuild).onFinishChange(() => { commit(); });
    gui.add(world, "stormY", -300, 0, 5).name("storm layer y").onChange(rebuild).onFinishChange(commit);
    const names = Object.keys(LIBRARY);
    if (names.length) {
      const lib = gui.addFolder("Repo worlds");
      const pick = { world: names[0] };
      lib.add(pick, "world", names).name("file");
      lib.add({ open: () => replaceWorld(parseWorld(structuredClone(LIBRARY[pick.world]))) }, "open").name("Open (undoable)");
    }
    const amb = gui.addFolder("Ambient wind");
    amb.add(world.ambientWind, "heading", 0, 359, 1).name("heading (°)").onFinishChange(commit);
    amb.add(world.ambientWind, "strength", 0, 15, 0.5).name("speed (m/s)").onFinishChange(commit);
    const gen = gui.addFolder("Generate");
    gen.add(world, "seed", 1, 99999, 1).onFinishChange(commit);
    gen.add({ regenerate: () => replaceWorld(generateWorld(world.seed, world.name)) }, "regenerate").name("Generate from seed");
    const stats = { isles: world.isles.length, towns: world.isles.filter((i) => i.town).length, winds: world.winds.length, bridges: world.bridges.length };
    const info = gui.addFolder("Contents");
    for (const k of Object.keys(stats) as (keyof typeof stats)[]) info.add(stats, k).disable();
    return;
  }
  const live = (c: { onChange: (f: () => void) => typeof c; onFinishChange: (f: () => void) => typeof c }) => c.onChange(rebuild).onFinishChange(commit);
  if (selection.type === "isle") {
    const i = sel as Isle;
    gui = new GUI({ title: "Isle" });
    gui.add(i, "name").onFinishChange(commit);
    live(gui.add(i, "biome", BIOMES as unknown as string[]));
    live(gui.add(i, "people", PEOPLES as unknown as string[]));
    live(gui.add(i, "tier", TIERS as unknown as string[]).name("risk tier"));
    live(gui.add(i, "state", STATES as unknown as string[]));
    live(gui.add(i, "radius", 10, 200, 1).name("radius (m)"));
    live(gui.add(i, "y", world.stormY, 200, 1).name("altitude (m)"));
    live(gui.add(i, "town"));
    live(gui.add(i, "shrine").name("Accord shrine"));
    live(gui.add(i, "ancientTree").name("ancient tree"));
    const pos = gui.addFolder("Position").close();
    live(pos.add(i, "x"));
    live(pos.add(i, "z"));
  } else if (selection.type === "wind") {
    const w = sel as Wind;
    gui = new GUI({ title: "Wind current" });
    gui.add(w, "name").onFinishChange(commit);
    live(gui.add(w, "kind", WIND_KINDS as unknown as string[]));
    live(gui.add(w, "strength", 1, 40, 0.5).name("speed (m/s)"));
    live(gui.add(w, "gustiness", 0, 1, 0.05));
    live(gui.add(w, "width", 10, 300, 5).name("width (m)"));
    live(gui.add(w, "y", world.stormY, 200, 1).name("altitude (m)"));
    gui.add({ reverse: () => { w.points.reverse(); commit(); drawSelection(); } }, "reverse").name("Reverse direction");
    gui.add({ close: () => {
      const [a, b] = [w.points[0], w.points[w.points.length - 1]];
      if (a[0] === b[0] && a[1] === b[1]) w.points.pop(); else w.points.push([...a]);
      commit(); drawSelection();
    } }, "close").name("Toggle loop");
  } else {
    gui = new GUI({ title: "Bridge" });
    const b = sel as unknown as { a: string; b: string };
    gui.add({ from: isleById(b.a)?.name ?? "?" }, "from").disable();
    gui.add({ to: isleById(b.b)?.name ?? "?" }, "to").disable();
  }
  gui.add({ duplicate: duplicateSelection }, "duplicate").name("Duplicate (Ctrl+D)");
  gui.add({ remove: deleteSelection }, "remove").name("Delete (Del)");
}

// ---------- Help ----------

const help = document.getElementById("help")!;
function updateHelp() {
  const tips: Record<Tool, string> = {
    select: "Click to select, drag isles, winds or their handles to move. Drag empty sky to pan, right-drag to orbit. F frames the world, Ctrl+Z undoes.",
    isle: "Click on the sky to place an isle. Edit it in the panel on the right.",
    wind: draft.length
      ? `${draft.length} point${draft.length > 1 ? "s" : ""}. Keep clicking; Enter or double-click finishes, Backspace removes a point, Esc cancels.`
      : "Click points to draw a wind current. It blows from the first point (green handle) to the last.",
    bridge: bridgeFrom ? `From ${isleById(bridgeFrom)?.name}. Click the isle to bridge to.` : "Click an isle, then another, to link them with a bridge.",
  };
  help.textContent = tips[tool];
}

// ---------- Loop ----------

function frame() {
  const s = world.size;
  camera.position.set(0, s * 1.7, s * 1.35);
  controls.target.set(0, 0, 0);
  controls.maxDistance = s * 4;
  scene.fog = new THREE.Fog(SKY, s * 2.5, s * 6);
  controls.update();
}

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  labels.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  animateWinds(t);
  if (selectionRing && selection?.type === "isle") selectionRing.children[0]?.scale.setScalar(1 + Math.sin(t * 4) * 0.02);
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
});

rebuild();
frame();
buildGui();
