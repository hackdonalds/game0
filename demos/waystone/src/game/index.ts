// Lane C: all gameplay. Race select → skiff arrival → Maren → 3 shards → Storm Ridge (per-people route)
// → Stormspawn → relight the Waystone → end card. Built only on contracts.ts (Isle, GameContext).
import * as THREE from "three";
import type { GameContext, People } from "../contracts";
import { Rig } from "./anim";
import { Audio } from "./audio";
import { Stormspawn } from "./boss";
import { FollowCam } from "./camera";
import { byId, MAREN, PEOPLES } from "./data";
import { Fx, glowSprite } from "./fx";
import { Input } from "./input";
import { Player, type Env } from "./player";
import { UI } from "./ui";

type Stage = "talk" | "shards" | "ridge" | "boss" | "stone" | "done";
const STAGES: Stage[] = ["talk", "shards", "ridge", "boss", "stone", "done"];
const STORM: Record<Stage, number> = { talk: 0.4, shards: 0.5, ridge: 0.85, boss: 1, stone: 0.9, done: 0 };

const flat = (v: THREE.Vector3) => new THREE.Vector3(v.x, 0, v.z);
const dist2d = (a: THREE.Vector3, b: THREE.Vector3) => Math.hypot(a.x - b.x, a.z - b.z);
/** Distance on XZ from p to segment ab. */
function segDist(p: THREE.Vector3, a: THREE.Vector3, b: THREE.Vector3) {
  const abx = b.x - a.x, abz = b.z - a.z;
  const l2 = abx * abx + abz * abz || 1;
  const t = THREE.MathUtils.clamp(((p.x - a.x) * abx + (p.z - a.z) * abz) / l2, 0, 1);
  return Math.hypot(p.x - (a.x + abx * t), p.z - (a.z + abz * t));
}

export async function startGame(ctx: GameContext) {
  // main.ts awaits this before revealing the canvas, so the flow (which waits on the player) runs on its own
  void run(ctx).catch((e) => console.error("[game]", e));
}

async function run(ctx: GameContext) {
  const { scene, camera, isle, assets, renderer, quality } = ctx;
  const P = isle.points;
  const groundY = (v: THREE.Vector3) => isle.heightAt(v.x, v.z) ?? v.y;
  const at = (v: THREE.Vector3) => new THREE.Vector3(v.x, groundY(v), v.z);

  const input = new Input(renderer.domElement, document.getElementById("ui")!);
  const ui = new UI(input);
  const audio = new Audio();
  const fx = new Fx(scene);
  const follow = new FollowCam(camera, isle, input.touch);
  input.onFirstGesture = () => audio.start();
  ui.muteBtn.textContent = audio.muted ? "🔇" : "🔊";
  ui.muteBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    audio.start();
    audio.setMuted(!audio.muted);
    ui.muteBtn.textContent = audio.muted ? "🔇" : "🔊";
  });
  ui.muteBtn.textContent = audio.muted ? "🔇" : "🔊";
  ui.muteBtn.addEventListener("pointerdown", (e) => e.stopPropagation());

  // ---------- Storm level, eased ----------
  let storm = 0.3, stormTarget = 0.3, stormSent = -1;
  const setStorm = (v: number) => (stormTarget = v);

  // ---------- Frame loop (single callback; phases switch inside) ----------
  let phase: "select" | "arrive" | "play" | "end" = "select";
  let tick: (dt: number, t: number) => void = () => {};
  let clockT = 0;
  const frame = (dt: number, t: number) => {
    clockT = t;
    input.update();
    storm += (stormTarget - storm) * Math.min(1, dt * 0.6);
    if (Math.abs(storm - stormSent) > 0.005) {
      stormSent = storm;
      isle.setStorm(storm);
      audio.setStorm(storm);
    }
    tick(dt, t);
    fx.update(dt);
    input.endFrame();
  };
  ctx.onFrame((dt, t) => {
    if (!manual) frame(dt, t);
  });
  let manual = false;
  const debug = new URLSearchParams(location.search).has("debug");
  if (debug) void import("./debug").then((m) => m.installBot());
  if (debug)
    Object.assign(window, {
      /** Step the whole game by `secs` at 60 Hz, then render once. */
      __wsStep(secs: number) {
        manual = true;
        for (let i = 0; i < Math.round(secs * 60); i++) {
          clockT += 1 / 60;
          frame(1 / 60, clockT);
          isle.update(1 / 60, clockT, camera);
        }
        renderer.render(scene, camera);
      },
      __wsRealtime() { manual = false; },
      __key(code: string, down: boolean) { dispatchEvent(new KeyboardEvent(down ? "keydown" : "keyup", { code, bubbles: true })); },
      __tap(code: string) {
        const w = window as unknown as { __key: (c: string, d: boolean) => void; __wsStep: (s: number) => void };
        w.__key(code, true); w.__wsStep(1 / 60); w.__key(code, false); w.__wsStep(1 / 60);
      },
      /** Hold W toward x,z until within `stop` m (camera yaw steers). */
      __walkTo(x: number, z: number, stop = 1.5, max = 30, extra?: () => void) {
        const w = window as unknown as { __key: (c: string, d: boolean) => void; __wsStep: (s: number) => void; __ws: { player: Player } };
        const p = w.__ws.player.pos;
        let t = 0;
        w.__key("KeyW", true);
        while (t < max) {
          const dx = x - p.x, dz = z - p.z;
          if (Math.hypot(dx, dz) < stop) break;
          follow.yaw = Math.atan2(-dx, -dz);
          extra?.();
          w.__wsStep(0.1);
          t += 0.1;
        }
        w.__key("KeyW", false);
        w.__wsStep(0.3);
        return { t: +t.toFixed(1), pos: p.toArray().map((v) => +v.toFixed(2)) };
      },
    });

  // ---------- Race select: turntable floating off the jetty ----------
  const outward = flat(P.spawn).sub(flat(P.camp));
  if (outward.lengthSq() < 1e-4) outward.set(0, 0, 1);
  outward.normalize();
  const spawnY = groundY(P.spawn);
  const tablePos = flat(P.spawn).addScaledVector(outward, 22).setY(spawnY + 6);
  const table = new THREE.Group();
  table.position.copy(tablePos);
  table.rotation.y = Math.atan2(outward.x, outward.z); // local +Z points out to sea, toward the camera
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(2.9, 2.4, 0.5, 48), new THREE.MeshStandardMaterial({ color: 0x5b5f6b, roughness: 0.95 }));
  disc.position.y = -0.25;
  disc.receiveShadow = true;
  const rim = new THREE.Mesh(new THREE.TorusGeometry(2.85, 0.05, 8, 64).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x7fe0d0 }));
  rim.position.y = 0.01;
  const spin = new THREE.Group();
  table.add(disc, rim, spin);
  const tableLight = new THREE.PointLight(0xffe2b0, 30, 14, 2);
  tableLight.position.set(0, 4, 3);
  table.add(tableLight);
  const turn: Rig[] = PEOPLES.map((p, i) => {
    const r = new Rig(assets, p.id);
    standInFace(r, assets.get(p.id).gltf === null);
    const a = (i / 3) * Math.PI * 2;
    r.root.position.set(Math.sin(a) * 1.7, 0, Math.cos(a) * 1.7);
    r.root.rotation.y = a;
    spin.add(r.root);
    return r;
  });
  scene.add(table);
  let selIdx = 0, spinAngle = 0;

  const played: People[] = JSON.parse(sessionStorage.getItem("ws.played") ?? "[]");
  const last = sessionStorage.getItem("ws.people") as People | null;
  const nextUnplayed = PEOPLES.find((p) => !played.includes(p.id))?.id ?? PEOPLES[0].id;
  const initial = sessionStorage.getItem("ws.again") ? nextUnplayed : last ?? PEOPLES[0].id;
  sessionStorage.removeItem("ws.again");

  const tableCam = () => {
    const hfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect);
    const portrait = camera.aspect < 0.8;
    const d = THREE.MathUtils.clamp(3.4 / Math.tan(hfov / 2), 8, 17);
    // look below the figures so they sit in the upper half, clear of the card
    const lookY = tablePos.y + (portrait ? -1.6 : -0.2);
    return { pos: tablePos.clone().addScaledVector(outward, d).setY(tablePos.y + 2.4), look: new THREE.Vector3(tablePos.x, lookY, tablePos.z) };
  };
  tick = (dt, t) => {
    const want = -(selIdx / 3) * Math.PI * 2;
    let dA = Math.atan2(Math.sin(want - spinAngle), Math.cos(want - spinAngle));
    spinAngle += dA * Math.min(1, 6 * dt);
    spin.rotation.y = spinAngle;
    turn.forEach((r, i) => {
      r.root.rotation.y = (i / 3) * Math.PI * 2 + (i === selIdx ? Math.sin(t * 0.6) * 0.5 : 0);
      r.base("idle");
      r.update(dt);
    });
    const c = tableCam();
    camera.position.lerp(c.pos, 1 - Math.exp(-4 * dt));
    camera.lookAt(c.look);
  };
  { const c = tableCam(); camera.position.copy(c.pos); camera.lookAt(c.look); }
  setStorm(0.3);

  const people = await ui.select(initial, played, (id) => {
    selIdx = PEOPLES.findIndex((p) => p.id === id);
    audio.ui();
  });
  audio.start();
  audio.theme();
  sessionStorage.setItem("ws.people", people);
  const def = byId(people);

  // ---------- World actors ----------
  await ui.fade(true);
  scene.remove(table);
  const rig = new Rig(assets, people);
  standInFace(rig, assets.get(people).gltf === null);
  scene.add(rig.root);
  const player = new Player(isle, def, rig);
  const faceCamp = Math.atan2(P.camp.x - P.spawn.x, P.camp.z - P.spawn.z);
  player.place(P.spawn, faceCamp);
  ui.setPeople(def);

  const maren = new Rig(assets, "maren");
  standInFace(maren, assets.get("maren").gltf === null);
  maren.root.position.copy(at(P.maren));
  maren.root.rotation.y = Math.atan2(P.camp.x - P.maren.x, P.camp.z - P.maren.z) + Math.PI;
  scene.add(maren.root);
  const marenTag = glowSprite(0xe9c46a, 0.5);
  marenTag.position.set(0, maren.height + 0.6, 0);
  maren.root.add(marenTag);

  const shards = P.shards.map((p, i) => {
    const g = new THREE.Group();
    const m = assets.get("shard").clone();
    if (!assets.get("shard").gltf) {
      // stand-in crystal
      g.add(new THREE.Mesh(new THREE.OctahedronGeometry(0.28).scale(1, 1.8, 1), new THREE.MeshStandardMaterial({ color: 0x9ff4ff, emissive: 0x3fb7c9, emissiveIntensity: 1.2, roughness: 0.2 })));
    } else g.add(m);
    g.add(glowSprite(0x8ff0ff, 1.6, 0.7));
    g.position.copy(at(p)).setY(groundY(p) + 0.9);
    scene.add(g);
    return { g, base: g.position.y, got: false, phase: i * 2.1 };
  });

  const boss = new Stormspawn(assets, isle, fx, audio, at(P.arena), quality === "low");
  scene.add(boss.root);

  // where the shards fly to at the end (the world lane lights the stone itself)
  const stoneTop = at(P.waystone).setY(groundY(P.waystone) + 3.5);

  // ---------- Quest ----------
  let stage: Stage = "talk";
  let shardCount = 0;
  let playTime = 0;
  const routeText: Record<People, string> = {
    galeborne: "Glide from the cliff to the Waystone ledge",
    anchorkin: "Cross the rope bridge, anchoring in the gusts",
    rootwarden: "Walk the ridge path, rooting under the old trees",
  };
  const steps = () => [
    { id: "talk", text: "Talk to Maren at the campfire" },
    { id: "shards", text: `Find the glimmer shards (${shardCount}/3)` },
    { id: "ridge", text: routeText[people] },
    { id: "boss", text: "Defeat the Stormspawn" },
    { id: "stone", text: "Set the shards in the Waystone" },
  ];
  const refreshQuest = () => ui.quest(steps(), STAGES.indexOf(stage));
  const setStage = (s: Stage) => {
    stage = s;
    setStorm(STORM[s]);
    refreshQuest();
  };
  refreshQuest();
  setStorm(0.35);

  const checkpoint = () => {
    if (stage === "talk" || stage === "shards") return at(P.camp).add(outward.clone().multiplyScalar(2.5));
    if (stage === "ridge") return at(P.ridgeStart);
    const end = people === "galeborne" ? P.glideLanding : people === "anchorkin" ? P.bridgeEnd : P.rootTrees[P.rootTrees.length - 1] ?? P.ridgeStart;
    return at(end);
  };

  // Route geometry
  const rootPath = [P.ridgeStart, ...P.rootTrees, P.arena];
  const onRootPath = (p: THREE.Vector3) => {
    let d = Infinity;
    for (let i = 0; i < rootPath.length - 1; i++) d = Math.min(d, segDist(p, rootPath[i], rootPath[i + 1]));
    return d < 6 && dist2d(p, P.arena) > 10 && dist2d(p, P.ridgeStart) > 8 && !onBridge(p);
  };
  const nearTree = (p: THREE.Vector3) => P.rootTrees.some((tr) => dist2d(p, tr) < 4.5);
  const onBridge = (p: THREE.Vector3) => segDist(p, P.bridgeStart, P.bridgeEnd) < 3.5;

  const routeTarget = () => {
    const p = player.pos;
    if (people === "galeborne") return player.grounded && dist2d(p, P.glideLaunch) > 3 && dist2d(p, P.arena) > dist2d(P.glideLaunch, P.arena) ? P.glideLaunch : P.glideLanding;
    if (people === "anchorkin") return dist2d(p, P.bridgeEnd) < dist2d(P.bridgeStart, P.bridgeEnd) && segDist(p, P.bridgeStart, P.bridgeEnd) < 4 ? P.bridgeEnd : dist2d(p, P.bridgeStart) > 3 && dist2d(p, P.arena) > dist2d(P.bridgeStart, P.arena) ? P.bridgeStart : P.bridgeEnd;
    // next root tree closer to the arena than we are
    const dA = dist2d(p, P.arena);
    return P.rootTrees.find((tr) => dist2d(tr, P.arena) < dA - 2) ?? P.arena;
  };
  const objective = (): { p: THREE.Vector3; label: string; lift: number } | null => {
    switch (stage) {
      case "talk": return { p: at(P.maren), label: "Maren", lift: maren.height + 0.4 };
      case "shards": {
        const s = shards.filter((x) => !x.got).sort((a, b) => dist2d(a.g.position, player.pos) - dist2d(b.g.position, player.pos))[0];
        return s ? { p: s.g.position.clone(), label: "Shard", lift: 0.6 } : null;
      }
      case "ridge": { const r = routeTarget(); return { p: at(r), label: r === P.glideLaunch ? "Cliff edge" : r === P.bridgeStart ? "Bridge" : r === P.arena || r === P.glideLanding || r === P.bridgeEnd ? "Waystone" : "Old tree", lift: 1 }; }
      case "boss": return boss.alive ? { p: boss.pos.clone(), label: "", lift: boss.height + 1 } : null;
      case "stone": return { p: at(P.waystone), label: "Waystone", lift: 2.5 };
      default: return null;
    }
  };

  async function talkToMaren() {
    const pages =
      stage === "talk" ? [MAREN.greet[people], ...MAREN.intro, MAREN.route[people], MAREN.warn]
      : stage === "shards" ? [MAREN.reminder.shards]
      : stage === "ridge" ? [MAREN.reminder.ridge[people]]
      : stage === "boss" ? [MAREN.reminder.boss]
      : stage === "stone" ? [MAREN.reminder.stone]
      : [MAREN.reminder.done];
    maren.play("talk");
    await ui.say("Maren · skiff warden", pages, () => audio.talk());
    maren.play("idle");
    if (stage === "talk") {
      marenTag.visible = false;
      setStage(shardCount >= 3 ? "ridge" : "shards");
      ui.toast("Quest: Relight the Waystone");
    }
  }

  let relit = false;
  let relightStep: ((dt: number) => void) | undefined;
  async function relight() {
    relit = true;
    setStage("done");
    input.enabled = false;
    ui.prompts([]);
    // shards fly from the player into the stone
    const from = player.pos.clone().setY(player.pos.y + 1.2);
    const to = stoneTop.clone();
    const motes = [0, 1, 2].map(() => glowSprite(0x9ff4ff, 0.8));
    motes.forEach((m) => scene.add(m));
    let k = 0;
    await new Promise<void>((done) => {
      relightStep = (dt) => {
        k = Math.min(1, k + dt / 1.4);
        motes.forEach((m, i) => {
          const a = i * 2.1 + k * 6;
          m.position.lerpVectors(from, to, k * k).add(new THREE.Vector3(Math.cos(a), Math.sin(k * Math.PI) * 1.5, Math.sin(a)).multiplyScalar(1 - k));
        });
        if (k >= 1) {
          relightStep = undefined;
          done();
        }
      };
    });
    motes.forEach((m) => scene.remove(m));
    audio.pickup();
    fx.ring(at(P.waystone), 14, 0x9ff4ff, 1.6);
    fx.burst(to, 0x9ff4ff, 40, 9, 0.5, 1.4);
    follow.shake = 0.6;
    setStorm(0);
    isle.setStorm(0);
    isle.lightTheLane();
    audio.theme(true);
    endCam = 0;
    const secs = playTime;
    const nowPlayed = Array.from(new Set([...played, people]));
    sessionStorage.setItem("ws.played", JSON.stringify(nowPlayed));
    endAfter = 5;
    endFn = () => {
      phase = "end";
      document.exitPointerLock?.();
      const next = PEOPLES.find((p) => !nowPlayed.includes(p.id)) ?? PEOPLES[(PEOPLES.findIndex((p) => p.id === people) + 1) % 3];
      ui.end(def, secs, next, () => {
        sessionStorage.setItem("ws.again", "1");
        location.reload();
      });
    };
  }
  let endAfter = -1;
  let endFn: (() => void) | undefined;
  let endCam = -1;

  // ---------- Arrival: skiff approach from the cloud sea ----------
  const arriveFrom = flat(P.spawn).addScaledVector(outward, 34).setY(spawnY + 12);
  follow.behind(faceCamp);
  follow.update(0, player.pos, rig.height, true);
  const arriveTo = camera.position.clone();
  camera.position.copy(arriveFrom);
  camera.lookAt(player.pos);
  phase = "arrive";
  await ui.fade(false);
  ui.toast("Waystone · rest isle off the Lantern Spoke", 3.5);
  let arriveT = 0;
  const lookTmp = new THREE.Vector3();
  let busy = false; // respawn fades

  async function respawn(to: THREE.Vector3, full: boolean, msg: string) {
    if (busy) return;
    busy = true;
    await ui.fade(true);
    player.respawn(to, full);
    if (!full) player.hp = Math.max(1, player.hp - def.hp * 0.1);
    follow.behind(player.yaw);
    follow.update(0, player.pos, rig.height, true);
    ui.toast(msg);
    await ui.fade(false);
    busy = false;
  }

  let gustWarned = 0;
  let rootedSoundT = 0;
  tick = (dt, t) => {
    // ---- Arrival camera ----
    if (phase === "arrive") {
      arriveT += dt / 3.6;
      const k = THREE.MathUtils.smootherstep(Math.min(1, arriveT), 0, 1);
      camera.position.lerpVectors(arriveFrom, arriveTo, k);
      camera.position.y += Math.sin(k * Math.PI) * 3;
      lookTmp.copy(player.pos).setY(player.pos.y + rig.height * 0.85);
      camera.lookAt(lookTmp);
      rig.base("idle");
      rig.update(dt);
      maren.update(dt);
      if (arriveT >= 1) {
        phase = "play";
        input.enabled = true;
        ui.hud.hidden = false;
      }
      return;
    }

    relightStep?.(dt);
    if (phase === "play" && !relit) playTime += dt;
    // ---- Camera input ----
    if (phase === "play" && !relit) follow.input(input.look.x, input.look.y, input.zoom);

    // ---- Hazards ----
    const p = player.pos;
    const ridgeOn = STAGES.indexOf(stage) >= 2 && stage !== "done";
    const bridge = onBridge(p);
    const gust = bridge && !relit ? isle.gustAt(p.x, p.z, t) : null;
    const rootP = ridgeOn && onRootPath(p);
    const tree = nearTree(p);
    const talkRange = dist2d(p, P.maren) < 3.2;
    const stoneRange = dist2d(p, P.waystone) < 5.5;
    const env: Env = {
      gust,
      drain: rootP ? 11 : 0,
      nearTree: tree,
      frozen: ui.talking || busy || relit,
      extra: [
        { x: maren.root.position.x, z: maren.root.position.z, r: 0.45 },
        { x: P.waystone.x, z: P.waystone.z, r: 1.0 },
        ...(boss.alive && boss.state !== "charge" ? [boss.collider] : []),
      ],
      safe: !bridge && !rootP,
    };

    // ---- Interact ----
    if (input.pressed("interact") || (ui.talking && input.pressed("attack"))) {
      if (ui.talking) ui.advance();
      else if (talkRange && !relit) void talkToMaren();
      else if (stoneRange && stage === "stone") void relight();
    }

    // ---- Player ----
    const evs = player.update(dt, input, follow.yaw, env);
    for (const e of evs) {
      if (e.type === "step") audio.step(people === "anchorkin" ? 1 : people === "rootwarden" ? 0.5 : 0);
      else if (e.type === "jump") audio.step(0.2);
      else if (e.type === "land") {
        audio.step(1);
        if (e.hard) follow.shake = 0.4;
      } else if (e.type === "swing") {
        audio.swing();
        fx.slash(player.pos, player.yaw, rig.height, e.combo);
      } else if (e.type === "strike") {
        if (boss.strike(e.pos, e.dir, e.dmg)) {
          audio.hit(e.combo === 3);
          follow.shake = e.combo === 3 ? 0.35 : 0.18;
        }
      } else if (e.type === "hurt") {
        follow.shake = 0.5;
        audio.hurt();
      } else if (e.type === "rooted") audio.heal();
      else if (e.type === "glide") audio.gust();
      else if (e.type === "void") void respawn(player.lastSafe.clone(), false, "Caught by the wind… back to solid ground");
      else if (e.type === "dead") void respawn(checkpoint(), true, "You wake by the last safe light");
    }
    if (player.rooted && (rootedSoundT -= dt) <= 0) {
      rootedSoundT = 1.2;
      audio.heal();
      fx.burst(p.clone().setY(p.y + 0.3), tree ? 0xc8ffb0 : 0x9fe0b8, tree ? 8 : 4, 1.5, 0.2, 1);
    }

    // ---- Maren faces the player when near ----
    const toP = Math.atan2(p.x - maren.root.position.x, p.z - maren.root.position.z);
    if (dist2d(p, P.maren) < 7) {
      const r = maren.root.rotation;
      r.y += Math.atan2(Math.sin(toP - r.y), Math.cos(toP - r.y)) * Math.min(1, 4 * dt);
    }
    if (!ui.talking) maren.base("idle");
    maren.update(dt);
    marenTag.position.y = maren.height + 0.6 + Math.sin(t * 3) * 0.1;

    // ---- Shards ----
    for (const s of shards) {
      if (s.got) continue;
      s.g.position.y = s.base + Math.sin(t * 2 + s.phase) * 0.18;
      s.g.rotation.y += dt * 1.6;
      if (Math.hypot(p.x - s.g.position.x, p.z - s.g.position.z) < 1.5 && Math.abs(p.y + 1 - s.g.position.y) < 2.2) {
        s.got = true;
        scene.remove(s.g);
        shardCount++;
        audio.pickup();
        fx.burst(s.g.position, 0x9ff4ff, 18, 4);
        ui.toast(`Glimmer shard ${shardCount}/3`);
        if (stage === "shards") setStorm(STORM.shards + shardCount * 0.1);
        if (shardCount >= 3 && stage === "shards") {
          setStage("ridge");
          ui.toast(`All shards found. ${people === "galeborne" ? "To the cliff edge" : people === "anchorkin" ? "To the rope bridge" : "To the ridge path"}`, 3.5);
        } else refreshQuest();
      }
    }

    // ---- Ridge → boss ----
    if (stage === "ridge" && dist2d(p, P.arena) < 12 && player.grounded) setStage("boss");
    if ((stage === "boss" || stage === "ridge") && boss.state === "dormant" && dist2d(p, P.arena) < 13 && player.grounded) {
      if (stage === "ridge") setStage("boss");
      boss.wake();
      ui.toast("The Stormspawn wakes!");
    }
    if (boss.state !== "gone") boss.update(dt, player);
    boss.onDefeated ??= () => {
      setStage("stone");
      ui.toast("The Stormspawn breaks apart. Set the shards in the stone.", 3.5);
    };
    ui.bossBar(boss.engaged ? boss.hp / boss.maxHp : null);

    // ---- Gust warning + push feedback ----
    if (bridge && !relit) {
      const soon = isle.gustAt(p.x, p.z, t + 0.8).strength;
      if (soon > 0.35 && t - gustWarned > 2.5) {
        gustWarned = t;
        audio.gust();
      }
    }

    // ---- Camera ----
    if (endAfter > 0 && (endAfter -= dt) <= 0) endFn?.();
    if (endCam >= 0) {
      // ending: slow orbit around the stone
      endCam += dt;
      const c = at(P.waystone);
      const a = follow.yaw + endCam * 0.15;
      const d = 14 + Math.min(8, endCam * 1.5);
      camera.position.lerp(new THREE.Vector3(c.x + Math.sin(a) * d, c.y + 9 + Math.min(6, endCam * 0.8), c.z + Math.cos(a) * d), 1 - Math.exp(-2 * dt));
      camera.lookAt(c.x, c.y + 3, c.z);
    } else if (ui.talking) {
      // frame both speakers from the side
      const m = maren.root.position;
      const mid = player.pos.clone().add(m).multiplyScalar(0.5);
      const side = new THREE.Vector3(-(m.z - player.pos.z), 0, m.x - player.pos.x).normalize();
      if (side.dot(new THREE.Vector3().subVectors(camera.position, mid)) < 0) side.negate();
      const want = mid.clone().addScaledVector(side, 4.2 + rig.height).setY(mid.y + rig.height * 0.9);
      camera.position.lerp(want, 1 - Math.exp(-4 * dt));
      camera.lookAt(mid.x, mid.y + rig.height * 0.7, mid.z);
    } else follow.update(dt, player.pos, rig.height);

    // ---- HUD ----
    ui.bars(player.hp / def.hp, player.st / def.stamina);
    const chips: [string, string, boolean?][] = [];
    if (!ui.talking && !relit) {
      if (talkRange) chips.push(["E", "Talk to Maren"]);
      else if (stoneRange && stage === "stone") chips.push(["E", "Set the shards in the Waystone"]);
      const skillKey = "Shift";
      if (people === "galeborne") {
        if (player.gliding) chips.push(["", "Gliding… steer with move"]);
        else if (!player.grounded && player.airborne > 0.15) chips.push([skillKey, "Hold to Glide", stage === "ridge"]);
        else if (stage === "ridge" && dist2d(p, P.glideLaunch) < 6) chips.push(["Space", "Jump off the edge, then hold Shift to glide"]);
      } else if (people === "anchorkin") {
        const soon = bridge ? isle.gustAt(p.x, p.z, t + 0.8).strength : 0;
        if (player.anchored) chips.push(["", "Anchored: nothing moves you"]);
        else if (bridge && (soon > 0.35 || (gust && gust.strength > 0.3))) chips.push([skillKey, "Gust! Hold to Anchor", true]);
        else if (bridge) chips.push([skillKey, "Hold to Anchor when gusts come"]);
        else if (boss.state === "windup") chips.push([skillKey, "Anchor to stop the charge"]);
      } else {
        if (player.rooted) chips.push(["", tree ? "Rooted under the old tree: healing fast" : "Rooted: healing"]);
        else if (player.rootCharge > 0) chips.push(["", "Taking root…"]);
        else if (rootP && !tree) chips.push(["", "The storm drains you. Reach the old tree", true]);
        else if (tree && ridgeOn && player.hp < def.hp * 0.95) chips.push([skillKey, "Stand still and hold to Take Root"]);
        else if (player.hp < def.hp * 0.5) chips.push([skillKey, "Hold to Take Root"]);
      }
      if (boss.vulnerable) chips.push(["Click", "Stunned! Strike now"]);
      else if (boss.state === "windup" && people !== "anchorkin") chips.push(["", "It's rearing up: step aside!", true]);
      else if (boss.state === "hop") chips.push(["Space", "Jump or leave the ring!", true]);
    }
    ui.prompts(input.touch ? chips.map(([, txt, w]) => ["", txt.replace("Shift", def.skill.name), w]) : chips);
    ui.interactAvailable((talkRange && !relit) || (stoneRange && stage === "stone") || ui.talking);

    // objective marker
    const o = objective();
    if (o && !ui.talking && !relit) {
      const v = o.p.clone().setY(o.p.y + o.lift).project(camera);
      const behind = v.z > 1;
      const dm = Math.round(dist2d(player.pos, o.p));
      ui.setMarker({ x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight, behind }, `${o.label}${o.label ? " · " : ""}${dm} m`, stage === "boss");
    } else ui.setMarker(null);

    audio.update(dist2d(p, P.camp));
  };

  // Debug hooks for automated play-testing (?debug)
  if (debug) {
    Object.assign(window, {
      __ws: {
        player, boss, isle, input, follow,
        get stage() { return stage; },
        get time() { return clockT; },
        get shards() { return shardCount; },
        tp(x: number, z: number) { player.place(new THREE.Vector3(x, 0, z)); },
        tpTo(k: keyof typeof P, i = 0) { const v = P[k]; player.place(Array.isArray(v) ? v[i] : v); },
      },
    });
  }
}

/** Stand-ins get a little visor so you can tell which way they face. */
function standInFace(r: Rig, isStandIn: boolean) {
  if (!isStandIn) return;
  const h = r.height;
  const visor = new THREE.Mesh(new THREE.BoxGeometry(h * 0.22, h * 0.07, h * 0.12), new THREE.MeshStandardMaterial({ color: 0x1d2433, roughness: 0.4 }));
  visor.position.set(0, h * 0.82, Math.max(0.3, h * 0.2) * 0.9);
  r.model.add(visor);
}
