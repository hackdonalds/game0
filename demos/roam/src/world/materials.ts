import * as THREE from "three";

/** Shared time uniform for foliage wind sway. */
export const windTime = { value: 0 };

export type PaintKind = "kit" | "foliage" | "glow";

const RIM_WARM = new THREE.Color(0xe3b45a);
const RIM_COOL = new THREE.Color(0x2fc4b2);

// Wrapped, softly stepped diffuse for the direct (sun) light.
const WRAPPED_LIGHTS = THREE.ShaderChunk.lights_physical_pars_fragment.replace(
  "float dotNL = saturate( dot( geometryNormal, directLight.direction ) );",
  `float ndlRaw = dot( geometryNormal, directLight.direction );
	float dotNL = saturate( ( ndlRaw + 0.3 ) / 1.3 );
	dotNL = mix( dotNL, smoothstep( 0.08, 0.55, dotNL ), 0.45 );`,
);

const cache = new Map<string, THREE.MeshStandardMaterial>();

/**
 * Painterly standard material: vertex colours, roughness 1, wrapped/stepped sun diffuse and a soft
 * warm-over-teal rim. Foliage sways in the wind; glow is self-lit by its vertex colour.
 */
export function painterly(kind: PaintKind, vertexColors: boolean, color = 0xffffff, map: THREE.Texture | null = null): THREE.MeshStandardMaterial {
  const key = `${kind}|${vertexColors}|${color}|${map?.uuid ?? ""}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const m = new THREE.MeshStandardMaterial({
    color,
    vertexColors,
    roughness: 1,
    metalness: 0,
    side: kind === "foliage" ? THREE.DoubleSide : THREE.FrontSide,
    map,
  });
  if (kind === "glow") {
    m.emissive.set(vertexColors ? 0x000000 : map ? 0xffffff : color);
    m.emissiveMap = map;
    m.emissiveIntensity = map ? 1.1 : 1.6;
  }
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = windTime;
    shader.uniforms.uRimWarm = { value: RIM_WARM };
    shader.uniforms.uRimCool = { value: RIM_COOL };
    if (kind === "foliage") {
      shader.vertexShader = "uniform float uTime;\n" + shader.vertexShader.replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        vec3 ip = vec3( 0.0 );
        #ifdef USE_INSTANCING
          ip = vec3( instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2] );
        #endif
        float swayH = clamp( position.y, 0.0, 3.0 );
        float ph = uTime * 1.7 + ip.x * 0.31 + ip.z * 0.23;
        float amp = 0.045 * swayH;
        transformed.x += ( sin( ph ) + 0.35 * sin( ph * 2.7 + 1.3 ) ) * amp;
        transformed.z += ( cos( ph * 0.83 ) + 0.3 * sin( ph * 3.1 ) ) * amp * 0.7;`,
      );
    }
    shader.fragmentShader = "uniform vec3 uRimWarm;\nuniform vec3 uRimCool;\n" + shader.fragmentShader
      .replace("#include <lights_physical_pars_fragment>", WRAPPED_LIGHTS)
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        {
          vec3 vdir = normalize( vViewPosition );
          float fres = pow( 1.0 - saturate( dot( normal, vdir ) ), 3.0 );
          vec3 rim = mix( uRimCool, uRimWarm, saturate( normal.y * 0.6 + 0.55 ) );
          totalEmissiveRadiance += rim * fres * 0.22 * ( 0.4 + diffuseColor.rgb );
          ${kind === "glow" && vertexColors ? "totalEmissiveRadiance += diffuseColor.rgb * 1.8;" : ""}
        }`,
      );
  };
  m.customProgramCacheKey = () => `painterly-${kind}-${vertexColors}`;
  cache.set(key, m);
  return m;
}

/**
 * Pick a painterly material for a GLB material by its name: Kit, Kit_Foliage, Kit_Glow for the vertex-coloured
 * kits; textured architecture keeps its painted map, and its fungus and amber materials glow.
 */
export function kitMaterial(src: THREE.Material, hasColors: boolean): THREE.MeshStandardMaterial {
  const s = src as THREE.MeshStandardMaterial;
  const name = s.name ?? "";
  const kind: PaintKind = /glow|fungus|amber/i.test(name) ? "glow" : /foliage/i.test(name) ? "foliage" : "kit";
  if (s.map) {
    s.map.colorSpace = THREE.SRGBColorSpace;
    return painterly(kind, false, 0xffffff, s.map);
  }
  return painterly(kind, hasColors, hasColors ? 0xffffff : s.color ? s.color.getHex() : 0xcccccc);
}
