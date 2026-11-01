# Runtime contract (Godot 4.7 and three.js)

What the engines must do with forge assets. Implement once per engine; every asset then works.

Reference implementation for three.js: `demos/creator/src/forge.ts` (`ForgeCharacter`). Godot is still to do.

## Appearance

A character is data:
```json
{"family": "humanoid", "people": "galeborne",
 "sliders": {"height": 0.3, "shoulders": -0.2, "body_muscle": 0.1, "face_eye_size": 0.4},
 "parts": {"top": "linen-shirt", "cloak": "sky-cloak", "hair": "crest-01"},
 "dyes": {"top": {"primary": "dye.sky", "secondary": "dye.bone", "accent": "dye.gold"}}}
```
Clamp every slider to `peoples[people].clamp` (default `[-1, 1]`) on load and on edit; start from `peoples[people].defaults`. `locked` entries can't be changed or removed. Gear only carries the keys that move it; skip keys a mesh doesn't have.

## Bodies and gear share one skeleton

- Load `peoples/<people>.body.glb`. Its skeleton is the character's skeleton.
- Each gear GLB carries a copy of the skeleton. **Bind the gear mesh to the body's skeleton**:
  - three.js: build a skeleton from the body's bones in the **gear's joint order** (match by name) and bind with inverses = `inverse(body bone rest world) × gear dequantisation`, where the dequantisation is `gearBone[0].matrixWorld × gear.boneInverses[0]`. meshopt web builds quantise positions and fold the dequantisation into each file's inverse bind matrices, so the body's own inverses can't be reused. Reference: `ForgeCharacter.equip` in `demos/creator/src/forge.ts`.
  - Godot: reparent the gear `MeshInstance3D` under the body's `Skeleton3D`, set `skeleton = ".."` and `skin = body_mesh.skin`, so it uses the people's bind poses.
- Sort gear by `.part.json` `order` (under 1 → cloak 4). Apply `hides` (another slot's piece is hidden while this one is worn) and the cloak-while-gliding style rules in game code.

## Body hiding by mask (exact) and by region (coarse)

Each piece that hugs the body ships `<piece>.mask.png` in the shared body UV space (white = hidden). Combine the masks of every visible piece (max) into one texture and discard body fragments where it is white (three.js: a canvas with `lighten` compositing, NearestFilter, flipY false; Godot: blend the Images, sample in `fragment()` with `UV`). The mask only covers skin the piece hugs, eroded away from its edges, so it never opens see-through gaps. Region bits below are the coarse fallback.

## Body hiding by region

Body vertices carry their region in TEXCOORD_1 (`u = (index + 0.5) / 32`). The covered mask is the OR of `1 << index` for every region in every worn piece's `covers`.
- Godot: `UV2` in the shader. `varying flat float region; void vertex() { region = floor(UV2.x * 32.0); }` and in `fragment()`: `if (((covered >> int(region)) & 1) != 0) discard;` with `uniform int covered`.
- three.js: at load, copy `uv1.x * 32` into a `region` float attribute; in `onBeforeCompile` add `attribute float region; flat varying float vRegion;` to the vertex shader, and `uniform int covered;` with the same `discard` in the fragment shader.

## Sliders

Clips only key bone **rotations** (and Hips translation), so bone sliders can be set once on the bones' rest transforms, and they survive animation.
- `uniformScale`: bone scale × `(1 + v·amount)`. Height scales the `Root` bone, so feet stay on the ground and clips need no correction.
- `translateOut`: shoulder bones move along ±X (glTF +X is the character's left): left `+v·amount`, right `−v·amount`.
- `translateUp`: `+v·amount` on Y.
- `translateAlongLimb`: along the bone's rest offset direction from its parent, `v·amount`.
- Godot: change `Skeleton3D.set_bone_rest()`/`set_bone_pose_*` once after loading; avoid scaling bones that carry spring chains (SpringBoneSimulator3D warns on scale). three.js: change `bone.position`/`bone.scale` before the first `mixer.update`.

Morph sliders are pairs: `<name>_pos = max(v, 0)`, `<name>_neg = max(−v, 0)`. Set them on the **body and every gear mesh** (gear has the same key names). The people's `people_<id>` key is 1 by default and never changes.
- three.js: `mesh.morphTargetInfluences[mesh.morphTargetDictionary[name]]`.
- Godot: `mesh_instance.set_blend_shape_value(mesh_instance.find_blend_shape_by_name(name), w)`.

## Clips

`anims/<set>.glb` holds clips for the family. Every body shares rest rotations, so clips play directly:
- Never adjust animated bones per frame after the mixer: three.js's mixer skips writing values that didn't change, so per-frame scaling or offsets compound and the character shakes. Bake adjustments into per-character copies of the clips once (and again only when the inputs change).
- Scale the Hips translation track of each copy by `body Hips rest height / library Hips rest height`.
- Pose offsets (`peoples[id].pose`, `sliderPose`): rotate the listed bones' tracks about the character's front axis expressed in the bone's parent frame, **after** the clip's rotation (`q' = off · q`), so the clip's own twist can't turn an outward spread inwards. Rebuild the copies when a slider that feeds `sliderPose` changes.
- three.js: clone each `AnimationClip` per people and multiply the `Hips.position` track values; play with an `AnimationMixer` on the body root.
- Godot: import the library as an `AnimationLibrary`; scale the Hips position track at load, or use root motion with `root_motion_track` on Hips.
- Hands on two-handed props: TwoBoneIK3D (Godot 4.6+) to the prop's off-hand marker. Feet on slopes: foot IK.

## Sockets

Socket bones (`Socket_Grip_R`, `Socket_Back`, …) are non-deforming bones. Attach props at the socket with the prop's `Grip` empty at the socket origin.
- three.js: `body.skeleton.getBoneByName("Socket_Grip_R").add(prop)`, offset by the inverse of the Grip transform.
- Godot: `BoneAttachment3D` with `bone_name = "Socket_Grip_R"`.

## Dyes and the painterly look

`<asset>.dye.png` (R primary, G secondary, B accent) sits next to every dyeable GLB. Dye colours come from dye items.
```glsl
// shared logic, Godot spatial shader and three.js onBeforeCompile
vec3 base = texture(albedo, uv).rgb;
vec3 m = texture(dyeMask, uv).rgb;
float l = dot(base, vec3(0.299, 0.587, 0.114));
vec3 c = base;
c = mix(c, l * dyePrimary * 1.6, m.r);
c = mix(c, l * dyeSecondary * 1.6, m.g);
c = mix(c, l * dyeAccent * 1.6, m.b);
```
Lighting: toon ramp (Godot: a `light()` function sampling a ramp texture by `dot(NORMAL, LIGHT)`; three.js: `MeshToonMaterial` with a `gradientMap`, patched with the dye code above).

## Faces and secondary motion

- Expressions: ARKit 52 key names on the body; any ARKit source (lip sync from Rhubarb visemes mapped to ARKit, emotes) drives them on every people.
- Spring bones on the contract chains (`Mantle_*`, `Tail_*`, `Ear_*`, hair and cape chains): Godot `SpringBoneSimulator3D` with sphere/capsule colliders on the body; three.js: a small spring-chain solver (three-vrm's spring bone code works on any bone chain).
