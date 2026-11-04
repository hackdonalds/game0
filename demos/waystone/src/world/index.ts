// Lane D: the Waystone isle. Builds terrain, sky, props, foliage and weather and implements the Isle contract.
// Debug URL flags: ?fly (free camera: WASD/QE, drag to look, Shift fast), ?cam=x,y,z,tx,ty,tz (fixed camera),
// ?storm=0..1 (force storm level), ?lane (light the lane after 1 s).
import * as THREE from "three";
import type { Isle, WorldContext } from "../contracts";
import { createFoliage } from "./foliage";
import { ARENA_C, BRIDGE, CAMP_C, GLIDE_C, JETTY, PLINTH_C, heightAt, initLayout, jettyY } from "./layout";
import { U } from "./materials";
import { createProps } from "./props";
import { createSky } from "./sky";
import { createStorm, gustPhase, onBridge } from "./storm";
import { buildTerrain } from "./terrain";
import { createFly } from "./fly";

export async function createIsle({ scene, renderer, assets, quality }: WorldContext): Promise<Isle> {
  initLayout();
  const terrain = buildTerrain(quality);
  scene.add(terrain.top, terrain.under);
  const sky = createSky(scene, quality, assets);
  const props = createProps(scene, assets, quality);
  const foliage = createFoliage(scene, terrain, quality);
  const weather = createStorm(scene, quality, props.waystoneTop);
  void renderer;

  const P = (x: number, z: number, dy = 0) => new THREE.Vector3(x, (heightAt(x, z) ?? 0) + dy, z);
  const points = {
    spawn: new THREE.Vector3(JETTY.x, jettyY(), JETTY.z1 - 1.2),
    camp: P(CAMP_C.x, CAMP_C.z),
    maren: P(CAMP_C.x - 2.6, CAMP_C.z - 2.2),
    shards: props.shardSpots,
    ridgeStart: P(0, -5),
    glideLaunch: P(GLIDE_C.x, GLIDE_C.z),
    glideLanding: P(-13, -44),
    bridgeStart: P(BRIDGE.x, BRIDGE.z0 + 0.6),
    bridgeEnd: P(BRIDGE.x, BRIDGE.z1 - 0.6),
    rootTrees: props.rootTrees,
    arena: P(ARENA_C.x, ARENA_C.z),
    waystone: P(PLINTH_C.x, PLINTH_C.z),
  };

  const params = new URLSearchParams(location.search);
  let stormTarget = params.has("storm") ? Number(params.get("storm")) : 0.35;
  let storm = stormTarget;
  let laneLit = false, lane = 0, laneT = 0;
  const glowBase = props.waystoneGlow.map((g) => (g.userData.baseEmissive as number) || 1);
  const fly = createFly(params);
  const focus = new THREE.Vector3(), fwd = new THREE.Vector3();
  let lastT = 0, tOffset = 0; // debug time shift (setTime)

  const isle: Isle = {
    points,
    heightAt,
    colliders: props.colliders,
    sun: sky.sun,
    setStorm(level) {
      if (!laneLit) stormTarget = THREE.MathUtils.clamp(level, 0, 1);
    },
    lightTheLane() {
      if (laneLit) return;
      laneLit = true;
      stormTarget = 0;
    },
    gustAt(x, z, t) {
      const dir = new THREE.Vector3(1, 0, 0);
      if (laneLit || !onBridge(x, z)) return { dir, strength: 0 };
      const g = gustPhase(t);
      dir.x = g.sign;
      return { dir, strength: g.strength * Math.min(1, 0.45 + storm) };
    },
    update(dt, t, camera) {
      lastT = t;
      t += tOffset;
      fly.update(dt, camera as THREE.PerspectiveCamera);
      U.uTime.value = t;
      // storm eases towards its target; it clears slowly once the lane is lit
      const rate = laneLit ? 0.35 : 0.8;
      storm += (stormTarget - storm) * Math.min(1, dt * rate);
      U.uStorm.value = storm;
      U.uWind.value = 0.25 + storm * 0.75;
      if (laneLit) { laneT += dt; lane = Math.min(1, laneT / 6); }
      // waystone glow: guttering while dark, blazing once relit
      const gutter = 0.1 + 0.08 * Math.sin(t * 7.3) * Math.sin(t * 2.1);
      const lit = THREE.MathUtils.smoothstep(laneT, 0, 2.5);
      props.waystoneGlow.forEach((g, i) => (g.emissiveIntensity = glowBase[i] * (gutter * (1 - lit) + 3.2 * lit)));
      props.waystoneLight.intensity = 1.5 * (1 - lit) * (1 + Math.sin(t * 7.3)) + 70 * lit;
      // shadow focus: a little ahead of the camera, on the ground
      camera.getWorldDirection(fwd);
      fwd.y = 0;
      fwd.normalize();
      focus.copy(camera.position).addScaledVector(fwd, quality === "high" ? 16 : 10);
      focus.y = heightAt(focus.x, focus.z) ?? camera.position.y - 5;
      const g = laneLit ? { warn: 0, strength: 0, sign: 1 } : gustPhase(t);
      sky.update(dt, t, camera, focus, lane);
      foliage.update(camera);
      props.update(dt, t, camera as THREE.PerspectiveCamera, g.strength * g.sign);
      weather.update(dt, t, camera as THREE.PerspectiveCamera, g, lane);
    },
  };
  if (params.has("lane")) setTimeout(() => isle.lightTheLane(), 1000);
  // debug: render frames by hand (screenshots / timing when the page runs in the background)
  let dbgT = 0;
  const dbgCam = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 4000);
  const render = (frames = 1, dt = 1 / 60) => {
    const gl = renderer.getContext();
    const t0 = performance.now();
    for (let i = 0; i < frames; i++) {
      dbgT += dt;
      dbgCam.aspect = innerWidth / innerHeight;
      dbgCam.updateProjectionMatrix();
      isle.update(dt, dbgT, dbgCam);
      renderer.render(scene, dbgCam);
    }
    const px = new Uint8Array(4);
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    return (performance.now() - t0) / frames;
  };
  const shot = (...a: [number, number, number, number, number, number]) => {
    for (const sel of ["#ui", ".loading"]) { const el = document.querySelector<HTMLElement>(sel); if (el) el.style.display = "none"; }
    const c = renderer.domElement;
    c.style.transition = "none";
    c.style.opacity = "1";
    fly.set(...a);
    return render(3);
  };
  (window as unknown as { __isle: unknown }).__isle = { THREE, isle, fly, U, render, shot, setTime: (v: number) => (tOffset = v - lastT), renderer, scene, setStorm: (v: number) => { stormTarget = v; storm = v; } };
  return isle;
}
