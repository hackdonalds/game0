// Shared painterly shading: wrapped, softly stepped sun diffuse, warm-over-teal rim, optional world-space
// brush noise (ground) and wind sway (foliage). Applied to the terrain and to every GLB placed by the world.
import * as THREE from "three";

/** Shared uniforms every world shader reads (wind, storm, lightning flash). */
export const U = {
  uTime: { value: 0 },
  uWind: { value: 0.35 }, // 0 calm .. 1 storm
  uWindDir: { value: new THREE.Vector2(0.8, 0.6).normalize() },
  uStorm: { value: 0 },
  uFlash: { value: 0 },
};

const RIM_WARM = new THREE.Color(0xf0b56a);
const RIM_COOL = new THREE.Color(0x3fa6b8);

const WRAPPED_LIGHTS = THREE.ShaderChunk.lights_physical_pars_fragment.replace(
  "float dotNL = saturate( dot( geometryNormal, directLight.direction ) );",
  `float ndlRaw = dot( geometryNormal, directLight.direction );
	float dotNL = saturate( ( ndlRaw + 0.35 ) / 1.35 );
	dotNL = mix( dotNL, smoothstep( 0.1, 0.6, dotNL ), 0.4 );`,
);

export const GLSL_NOISE = `
float wHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float wNoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(wHash(i), wHash(i + vec2(1, 0)), u.x), mix(wHash(i + vec2(0, 1)), wHash(i + vec2(1, 1)), u.x), u.y);
}
float wFbm(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++) { s += wNoise(p) * a; p = p * 2.03 + vec2(17.1, 9.3); a *= 0.5; }
  return s;
}`;

export interface PaintOpts {
  /** world-space brush noise on the albedo (terrain) */
  ground?: boolean;
  /** wind sway by local height (instanced foliage) */
  sway?: number;
  rim?: number;
}

export function painterly<T extends THREE.MeshStandardMaterial>(m: T, opts: PaintOpts = {}): T {
  if (m.userData.painted) return m;
  m.userData.painted = true;
  const rim = opts.rim ?? 0.22;
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (shader, r) => {
    prev?.call(m, shader, r);
    Object.assign(shader.uniforms, U, { uRimWarm: { value: RIM_WARM }, uRimCool: { value: RIM_COOL } });
    shader.vertexShader = `uniform float uTime; uniform float uWind; uniform vec2 uWindDir;\nvarying vec3 vWPos;\n` + shader.vertexShader
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        ${opts.sway ? `{
          vec3 ip = vec3(0.0);
          #ifdef USE_INSTANCING
            ip = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
          #endif
          float hgt = clamp(position.y, 0.0, 12.0);
          float ph = uTime * (1.3 + uWind) + ip.x * 0.31 + ip.z * 0.23;
          float amp = ${opts.sway.toFixed(4)} * hgt * (0.5 + uWind * 1.4);
          vec2 bend = uWindDir * (0.6 + 0.4 * sin(ph)) * uWind * 1.6 + vec2(sin(ph), cos(ph * 0.83)) * 0.5;
          transformed.xz += bend * amp;
        }` : ""}`,
      )
      .replace(
        "#include <worldpos_vertex>",
        `#include <worldpos_vertex>
        {
          vec4 wp = vec4(transformed, 1.0);
          #ifdef USE_INSTANCING
            wp = instanceMatrix * wp;
          #endif
          vWPos = (modelMatrix * wp).xyz;
        }`,
      );
    shader.fragmentShader = `uniform vec3 uRimWarm; uniform vec3 uRimCool; uniform float uStorm; uniform float uFlash;\nvarying vec3 vWPos;\n${GLSL_NOISE}\n` + shader.fragmentShader
      .replace("#include <lights_physical_pars_fragment>", WRAPPED_LIGHTS)
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        ${opts.ground ? `{
          float n1 = wFbm(vWPos.xz * 0.35);
          float n2 = wNoise(vWPos.xz * vec2(2.3, 0.9) + n1 * 3.0);
          diffuseColor.rgb *= 0.86 + 0.22 * n1 + 0.1 * (n2 - 0.5);
          diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.08, 1.02, 0.86), smoothstep(0.55, 0.8, wNoise(vWPos.xz * 0.06)) * 0.5);
          // steep faces: layered limestone with cracks and mossy ledges
          vec3 fn = normalize(cross(dFdx(vWPos), dFdy(vWPos)));
          float steep = 1.0 - smoothstep(0.45, 0.75, abs(fn.y));
          if (steep > 0.01) {
            vec2 wp = vec2(dot(vWPos.xz, normalize(vec2(fn.z, -fn.x) + 1e-4)), vWPos.y);
            float warp = wFbm(wp * 0.25) * 3.0;
            float band = sin(wp.y * 1.6 + warp);
            float block = wNoise(vec2(wp.x * 0.5, floor(wp.y * 0.8 + warp * 0.3) * 3.1));
            float crack = smoothstep(0.08, 0.0, abs(wNoise(wp * vec2(0.9, 0.35)) - 0.5)) ;
            vec3 rockc = vec3(0.56, 0.52, 0.45) * (0.75 + 0.35 * block) * (0.85 + 0.15 * band);
            rockc *= 1.0 - crack * 0.55;
            float moss = smoothstep(0.6, 0.85, wNoise(wp * 0.6 + 7.0)) * smoothstep(-0.2, 0.6, band);
            rockc = mix(rockc, vec3(0.3, 0.38, 0.18), moss * 0.6);
            diffuseColor.rgb = mix(diffuseColor.rgb, rockc * (0.7 + 0.5 * diffuseColor.rgb / max(0.001, max(diffuseColor.r, max(diffuseColor.g, diffuseColor.b)))) * 0.85, steep * 0.85);
          }
        }` : ""}`,
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        {
          vec3 vdir = normalize(vViewPosition);
          float fres = pow(1.0 - saturate(dot(normal, vdir)), 3.0);
          vec3 rimc = mix(uRimCool, uRimWarm, saturate(normal.y * 0.6 + 0.55)) * (1.0 - 0.6 * uStorm);
          totalEmissiveRadiance += rimc * fres * ${rim.toFixed(3)} * (0.4 + diffuseColor.rgb);
          totalEmissiveRadiance += diffuseColor.rgb * uFlash * 0.55 * vec3(0.8, 0.9, 1.0);
        }`,
      );
  };
  const key = `paint-${opts.ground ? 1 : 0}-${opts.sway ?? 0}-${rim}`;
  const prevKey = m.customProgramCacheKey.bind(m);
  m.customProgramCacheKey = () => prevKey() + key;
  return m;
}

/** Make a GLB's materials painterly in place (keeps maps); returns materials whose name contains "glow". */
export function paintModel(root: THREE.Object3D, opts: PaintOpts = {}): THREE.MeshStandardMaterial[] {
  const glow: THREE.MeshStandardMaterial[] = [];
  const done = new Set<THREE.Material>();
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of mats) {
      if (done.has(mat)) continue;
      done.add(mat);
      const s = mat as THREE.MeshStandardMaterial;
      if (!s.isMeshStandardMaterial) continue;
      if (s.map) s.map.colorSpace = THREE.SRGBColorSpace;
      if (/glow/i.test(s.name)) {
        glow.push(s);
        if (s.emissive.getHex() === 0) s.emissive.set(0xffffff);
        if (!s.emissiveMap && s.map) s.emissiveMap = s.map;
      }
      s.roughness = Math.max(s.roughness, 0.85);
      s.metalness = Math.min(s.metalness, 0.1);
      painterly(s, opts);
    }
  });
  return glow;
}
