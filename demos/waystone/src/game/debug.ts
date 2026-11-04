// Play-test bot, loaded only with ?debug (dynamic import, separate chunk). Drives the game through the
// same keyboard events a player sends, stepping the simulation manually so it works in a hidden tab.
/* eslint-disable @typescript-eslint/no-explicit-any */
import * as THREE from "three";

type W = any;
const w = window as W;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const r1 = (v: THREE.Vector3) => v.toArray().map((n) => +n.toFixed(1));

export function installBot() {
  const ws = () => w.__ws;
  const step = (s: number) => w.__wsStep(s);
  const key = (c: string, d: boolean) => w.__key(c, d);
  const tap = (c: string) => w.__tap(c);
  const walk = (x: number, z: number, stop = 1.2, max = 30) => w.__walkTo(x, z, stop, max);

  /** Walk a list of waypoints. */
  w.__path = (pts: [number, number][], stop = 1.2) => pts.map(([x, z]) => walk(x, z, stop));

  /** Wait for respawn fades (real-time timers) while stepping. */
  w.__settle = async () => {
    for (let i = 0; i < 20; i++) {
      step(0.1);
      await sleep(60);
    }
  };

  w.__start = async (idx: number) => {
    while (!document.querySelector(".ws-start")) await sleep(100);
    (document.querySelectorAll(".ws-card .dots button")[idx] as HTMLElement).click();
    await sleep(50);
    (document.querySelector(".ws-start") as HTMLElement).click();
    await sleep(1300);
    step(4.5);
    return ws().player.def.name;
  };

  w.__talk = async () => {
    const pages: string[] = [];
    tap("KeyE");
    for (let i = 0; i < 10; i++) {
      const d = document.querySelector(".ws-dialog") as HTMLElement;
      if (d.hidden) break;
      pages.push(d.querySelector("p")!.textContent!.slice(0, 60));
      step(0.2);
      tap("KeyE");
      await sleep(0);
    }
    step(0.1);
    return pages;
  };

  w.__intro = async (idx: number) => {
    const name = await w.__start(idx);
    const P = ws().isle.points;
    walk(P.spawn.x, P.spawn.z - 9, 1); // down the jetty first
    walk(P.maren.x, P.maren.z, 2.2);
    const pages = await w.__talk();
    for (const s of P.shards) walk(s.x, s.z, 0.8);
    return { name, pages, stage: ws().stage, shards: ws().shards, hp: ws().player.hp };
  };

  w.__fight = (maxT = 120) => {
    const pl = ws().player, b = ws().boss;
    let t = 0;
    const log: any = { hits: 0, hurt: 0, deaths: 0, trace: [] };
    let prevHp = pl.hp, prevB = b.hp;
    const all = ["KeyW", "KeyA", "KeyS", "KeyD"];
    while (t < maxT && b.state !== "gone") {
      const dx = b.pos.x - pl.pos.x, dz = b.pos.z - pl.pos.z, d = Math.hypot(dx, dz);
      ws().follow.yaw = Math.atan2(-dx, -dz);
      all.forEach((k) => key(k, false));
      if (b.state === "windup" || b.state === "charge") {
        // sidestep toward the arena centre, never toward the edge
        const A = ws().isle.points.arena;
        const fx = dx / (d || 1), fz = dz / (d || 1);
        const right = -fz * (A.x - pl.pos.x) + fx * (A.z - pl.pos.z);
        key(right >= 0 ? "KeyD" : "KeyA", true);
      }
      else if (b.state === "hop") {
        if (d < 5.5) tap("Space");
      } else if (d > 2.2) key("KeyW", true);
      else if (b.state !== "dormant") tap("KeyF");
      if (pl.dead) {
        log.deaths++;
        step(4);
      }
      step(0.1);
      t += 0.1;
      if (Math.round(t * 10) % 20 === 0) log.trace.push({ b: b.state, bp: r1(b.pos), pp: r1(pl.pos), d: +d.toFixed(1) });
      if (b.hp < prevB) log.hits++;
      prevB = b.hp;
      if (pl.hp < prevHp - 0.5) log.hurt++;
      prevHp = pl.hp;
    }
    all.forEach((k) => key(k, false));
    if (log.trace.length > 12) log.trace = log.trace.slice(0, 12);
    return { t: +t.toFixed(1), bossHp: Math.round(b.hp), state: b.state, playerHp: +pl.hp.toFixed(1), ...log };
  };

  /** Interact with the Waystone and let the ending play. */
  w.__finish = () => {
    const P = ws().isle.points;
    const prompt = (document.querySelector(".ws-prompt") as HTMLElement).innerText;
    tap("KeyE");
    step(2);
    const stage = ws().stage;
    step(5.5);
    return { prompt, stage, end: (document.querySelector(".ws-end") as HTMLElement | null)?.innerText, at: r1(ws().player.pos), stone: r1(P.waystone) };
  };

  w.__pos = () => ({ p: r1(ws().player.pos), hp: +ws().player.hp.toFixed(1), st: +ws().player.st.toFixed(0), stage: ws().stage, grounded: ws().player.grounded });
}
