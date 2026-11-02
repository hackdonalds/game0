import * as THREE from "three";

export const HORIZON = new THREE.Color(0xc9d6d4);
export const ZENITH = new THREE.Color(0x3f82c8);
const CLOUD_LIT = new THREE.Color(0xfff2dc);
const CLOUD_SHADE = new THREE.Color(0x6fa9a6);
const SUN_GLOW = new THREE.Color(0xffd28a);

const NOISE = `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + vec2(17.1, 9.3); a *= 0.5; }
  return s;
}`;

export interface Sky {
  update(elapsed: number, focus: THREE.Vector3): void;
}

export function createSky(scene: THREE.Scene, sunDir: THREE.Vector3): Sky {
  scene.background = HORIZON.clone();
  scene.fog = new THREE.FogExp2(HORIZON.getHex(), 0.0011);

  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(50, 32, 16),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
      uniforms: { horizon: { value: HORIZON }, zenith: { value: ZENITH }, sunDir: { value: sunDir }, sunCol: { value: SUN_GLOW } },
      vertexShader: `varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = vec4(p.xy, p.w * 0.99999, p.w);
        }`,
      fragmentShader: `uniform vec3 horizon; uniform vec3 zenith; uniform vec3 sunDir; uniform vec3 sunCol; varying vec3 vDir;
        void main() {
          vec3 d = normalize(vDir);
          float up = clamp(d.y, 0.0, 1.0);
          vec3 c = mix(horizon, zenith, pow(up, 0.42));
          // warm band just above the horizon, towards the sun
          float toward = max(dot(normalize(d.xz + 1e-4), normalize(sunDir.xz + 1e-4)), 0.0);
          c = mix(c, sunCol, (1.0 - smoothstep(0.0, 0.18, up)) * (0.18 + 0.3 * toward));
          float s = max(dot(d, normalize(sunDir)), 0.0);
          c += sunCol * (pow(s, 6.0) * 0.18 + pow(s, 80.0) * 0.6 + pow(s, 900.0) * 1.5);
          c = mix(c, horizon, smoothstep(0.0, -0.15, d.y));
          gl_FragColor = vec4(c, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    }),
  );
  dome.renderOrder = -1000;
  dome.frustumCulled = false;
  scene.add(dome);

  // Cloud sea: soft drifting noise far below, fading into the horizon colour with distance.
  const cloudMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uCam: { value: new THREE.Vector3() },
      uFog: { value: HORIZON },
      uLit: { value: CLOUD_LIT },
      uShade: { value: CLOUD_SHADE },
      uSun: { value: SUN_GLOW },
      sunDir: { value: sunDir },
    },
    vertexShader: `varying vec3 vWorld;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: `uniform float uTime; uniform vec3 uCam; uniform vec3 uFog; uniform vec3 uLit; uniform vec3 uShade; uniform vec3 uSun; uniform vec3 sunDir;
      varying vec3 vWorld;
      ${NOISE}
      void main() {
        vec2 p = vWorld.xz * 0.0045;
        vec2 drift = vec2(uTime * 0.006, uTime * 0.0035);
        float c = fbm(p + drift);
        float c2 = fbm(p * 2.6 - drift * 1.7 + c);
        float billow = smoothstep(0.32, 0.78, c * 0.7 + c2 * 0.45);
        vec3 col = mix(uShade, uLit, billow);
        // warm sheen on the tops, facing the sun
        vec2 sd = normalize(sunDir.xz + 1e-4);
        float facing = clamp(fbm(p + drift + sd * 0.04) - c + 0.5, 0.0, 1.0);
        col += uSun * pow(facing, 3.0) * 0.25 * billow;
        float dist = length(vWorld.xz - uCam.xz);
        col = mix(col, uFog, smoothstep(200.0, 2200.0, dist) * 0.8 + 0.05);
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const cloud = new THREE.Mesh(new THREE.PlaneGeometry(7000, 7000, 1, 1).rotateX(-Math.PI / 2), cloudMat);
  cloud.position.y = -40;
  cloud.renderOrder = -900;
  scene.add(cloud);

  return {
    update(elapsed, focus) {
      dome.position.copy(focus);
      cloud.position.x = focus.x;
      cloud.position.z = focus.z;
      cloudMat.uniforms.uTime.value = elapsed;
      (cloudMat.uniforms.uCam.value as THREE.Vector3).copy(focus);
    },
  };
}
