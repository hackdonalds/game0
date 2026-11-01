# Gotchas (found while building the forge steps)

## Blender glTF import/export
- The importer adds an **Icosphere** object as the bones' display shape. It isn't part of the asset; `lib.load` removes it.
- The second UV layer comes back as `UVMap.001`, not `Regions`. Find it with `lib.regions_uv` (TEXCOORD_1).
- Shape keys can come back at value 1. `lib.export` sets every key to 0 unless `key_values` names it (a people body ships `people_<id>` = 1).
- With default sampling, the exporter writes translation and scale tracks for **every** bone, which would force the library rig's proportions onto every body. `lib.export` uses `export_force_sampling=False`, so only keyed channels go out. After any change to exporting, check with `bunx gltf-transform copy x.glb x.gltf` and read `animations[].channels`.
- `export_def_bones` must stay False, or the socket bones are dropped.

## Meshy rigs
- Armature scale 0.01 and bones in centimetres; `canonicalize` applies it.
- The spine names run backwards (Hips → Spine02 → Spine01 → Spine → neck). `canonical_map` assigns Spine/Chest/UpperChest by hierarchy, never by name.
- `head_end` and `headfront` carry weights; they're merged into Head.
- Weights are sloppy (the forearm region runs up the Galeborne mantle). Render `--color regions` to see it. The MPFB2 base fixes this for wrapped peoples.

## Web build
- `gltf-transform optimize` prunes unused attributes by default and would drop TEXCOORD_1 (no material uses it). The `web` step passes `--prune-attributes false`, plus no flatten, join, palette or instancing, so sockets and gear meshes survive.
- Godot can't read Draco; the Godot build stays a plain GLB.

## Fitting and wrapping
- `fit_gear` needs the garment aligned to the body at rest. Meshy garments come normalised to ±0.95, so scale and place them first.
- Thin double-sided geometry (feather cards, leaves) confuses push-out and `covers`: inside/outside is ambiguous. Keep such things as separate parts in the `skin` layer, not inside garments or bodies you fit against.
- `wrap` gets proportions and silhouette; faces need landmarks, and features the base doesn't have (beards, shells) should be parts.
- Bone heat (Blender automatic weights) fails on non-manifold meshes, loose islands, enclosed bones and tiny scales. Prefer transferring weights from the base.

## Running things
- Run steps with `bun scripts/forge.ts …` when piping the JSON (bun run adds a `$ …` line).
- Blender MCP calls block Blender's main thread and time out after about 4 minutes; anything heavy goes through a forge step.
- Retarget: if a clip looks mirrored or twisted, check `limbChild` for that bone and that the source rig mapped (the result lists source bones with no target).

## Learned in the Galeborne slice
- Meshy's `clip0` in a rigged GLB is a one-frame bind pose, not an idle.
- Generated rigs put shoulder and neck joints in odd places. `wrap` fits the torso as one smooth map (hips→head height, upper-arm width) and stretches only real limbs; bones the target lacks (fingers) follow their nearest shared ancestor.
- Meshy meshes are split at every UV seam: find islands by vertex **position**, not by shared vertices (`extract` does).
- Distance from the body can't separate a shirt from feathers; painted colour can. `extract --skin-regions` drops skin-coloured faces; a beige shirt goes with them.
- `.rest.json` from `wrap` includes the target's sockets; `build_people` re-places sockets on the surface instead, or props float off the hand.
- meshopt web builds fold position dequantisation into inverse bind matrices; see runtime.md before binding gear to another skeleton.
- A body built on a neutral base reads as gender 0.5; set per-people `defaults`.
- Gear only keeps keys that move it more than 0.5 mm (ARKit keys on shorts are dropped); `.part.json` lists `fittedKeys` so the validator knows they were considered.
- Hidden browser tabs pause `requestAnimationFrame`: a static screenshot doesn't mean animation is broken; check bone values.

## Learned fixing the shaking and the sinking shorts (2026-11-02)
- **Shaking:** exporting only keyed channels turned Bezier keys into glTF CUBICSPLINE with overshooting tangents; Blender renders on whole frames looked perfect while three.js at 60 fps jumped up to 6 cm a frame. Clips must be LINEAR (`lib.linear_keys`; `validate` reads the exported samplers). A re-export through Blender re-imports cubic keys, so every step that writes a library linearises every clip.
- Never scale or offset animated bones per frame after the mixer (it skips unchanged writes, so changes compound): bake into clip copies.
- **Sinking cloth:** pushing gear *vertices* out isn't enough when the gear is coarser than the body; body vertices bulge between them. `fit_gear` subdivides coarse pieces and pushes gear *faces* out from under poking body vertices.
- Smoothing weights on cloth only 3 cm off the body made shorts lag the thighs; only cloth over 8 cm off (capes, skirts) is treated as loose.
- Region hiding is too coarse for shorts (a thigh region is only 65% covered); the exact body mask hides just the skin the cloth hugs. A mask that reaches flared hems opens see-through notches: only hide where the cloth is within 12 mm, eroded two rings.
- Measuring poke-through: trust neither triangle winding (Meshy and MakeHuman meshes wind differently) nor nearest points at a piece's open edges. Count a body vertex only when a ray inward from it meets the cloth before leaving the body.
- `extract`: big generated triangles straddle hems and skin; drop a face if any corner sample is skin-coloured, and close small holes afterwards.
- Blender's glTF importer converts time to frames at the scene frame rate (24 by default); `lib.reset` pins 30 so frame numbers mean the same in every step, or comparisons are silently off.
- A clip made for a slimmer body clips through wider ones: arm spread from `sliderPose`, knee limits from `skeleton.limits`. A clip whose arms swing behind the back into the hips (Meshy's run) can't be fixed with offsets; replace it.

## Learned building all three peoples (2026-11-02)
- A bare-skin-only wrap leaves bulky peoples at MakeHuman proportions. Wrap twice: once to cut the parts, then again with `--exclude` parts and every region below the head, followed by a second shrinkwrap after the smoothing.
- Heads aren't shrinkwrapped; `wrap` scales the head with the torso so big-bodied peoples don't get small heads.
- Surface Deform refuses some pieces; `fit_gear` falls back to a nearest-triangle binder (clamped barycentrics, nearest corner on degenerate triangles, or vertices fly off). Unweighted gear vertices borrow the nearest weighted body vertex's weights, or they collapse to the origin in engines.
- Colour-distance can't separate olive leaves from olive-brown bark; distance from the body can (growths stand well off). Use `--drop-near` for the garment colour and skip the skin filter for such peoples.
- Meshy's web rig ("smart rig") adds Mixamo finger bones and extra `Bone_0xx` bones for some beards and feathers; canonicalize merges them into their parents.
- `retarget` with several clips in one source: the source's action slot must be set for every clip, not only when empty.
- Astro scopes component CSS by attribute, so controls created by script need `<style is:global>` under a component class.
