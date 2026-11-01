# Local rig and animation (verified 2026-11-01 on the Rootwarden, 0 credits)

`bun run art:rig <in.glb> <out.glb>` turns a static Meshy base body into a rigged, animated GLB with no paid service. `bun run art:rig --check <in.glb>` only reports whether the body is rig-ready (✗ blockers, ! warnings) and exits non-zero on a blocker; the full run does the same check first. It needs Blender at `/Applications/Blender.app` (or `BLENDER=<path>`).

## What it runs

1. `scripts/rig/autorig.py` (headless Blender) finds the joints from the mesh shape, builds a 52-bone game skeleton (with three bones per finger) and skins it.
   - Joints come from evenly sampled surface points, not vertices: Meshy meshes have big faces, so vertex slices leave holes.
   - The crotch is found by scanning up the legs until the gap closes, the armpit by scanning up until the arms merge with the torso, and the shoulder by extending the arm's centre line. Beards, moss and crowns don't fool this.
   - Fingers come from slices across each hand: past the knuckles the slices split into four tracks, and the thumb is the cluster beside them nearer the wrist. With fingers closed together (no four separate tracks) it falls back to a mitten: four finger bones spread evenly across the palm and a thumb on the palm edge nearest the front. Without a separate thumb it keeps the detected fingers and places the thumb the same way.
   - Weights come from Blender's automatic (bone-heat) weights on a voxel-remeshed, watertight copy, copied back to the real mesh. Thin bits the copy loses (twigs, leaf tips) take weights from the nearest weighted vertex.
   - Finger weights are not bone heat (finger gaps are thinner than the proxy's voxels, which glues fingers together): each vertex's hand weight is shared among the hand and finger bones by distance to each bone.
   - The skeleton includes a non-deforming `carry` bone in front of the chest for props.
2. `scripts/rig/retarget.py` copies clips from Quaternius' Universal Animation Library (CC0, `art/references/anims/quaternius/`, free Standard editions of UAL1 and UAL2) onto the rig.
   - Each bone copies its source bone's world-space rotation change. The library's T-pose rest is turned onto our A-pose rest first, so the arms aren't 45° off.
   - Forearms, hands and fingers are also matched on palm facing (index-to-pinky knuckle line), not only bone direction, so fists and grips curl the right way.
   - Hip motion and ground speeds are scaled by the hip-height ratio (0.81 for the Rootwarden).
   - The clip list (`CLIPS` in the script) is Idle, Walk, Run (jog), Sprint, JumpStart/JumpLoop/JumpLand, HitChest, HitHead, HitKnockback, Punch, Hook, CarryWalk, plus CarryIdle built from Idle legs and CarryWalk arms. To add a clip, add a row there. The source names are listed by importing the library GLB in Blender.
   - Source ground speeds in `CLIPS` were measured from the root-motion exports (`*_RM.glb`, not stored). Re-measure if you add locomotion clips.
3. gltf-transform compresses it (meshopt, 1024 px WebP textures): about 1.35 MB for a 20k-poly body with 14 clips.

## Checking the result

Debug renders: `blender -b --factory-startup -P scripts/rig/render.py -- <file.blend> <out_dir> [Clip frame ...]` draws front and side views with joint markers. The `.blend` files are left in the temp folder `art:rig` prints. Check the rest pose (joints inside the body, hips at the crotch, shoulders in the deltoids), then a few clip frames for stretched spikes or collapsing joints. For fingers, render close-ups with a small orthographic scale centred on `hand.L`'s tail and check a fist (Punch) and a grip (CarryWalk).

## In three.js

- GLTFLoader strips dots from names: `hand.L` becomes `handL`.
- The jump clips are in place. Drive the height in code: launch about 0.1 s into JumpStart, loop JumpLoop while airborne, play JumpLand from 0.05 s on touchdown.
- The carry clips hold the load between the palms: place props at the hands' midpoint each frame, not on a fixed socket.
- Move characters at the `speed` in `<out>.clips.json`, or the feet skate.
- Example: `demos/rootwarden-anim/src/main.ts`.

## Limits

- Verified on the Rootwarden (open hands), Anchorkin and Galeborne (closed hands, mitten fallback).
- Humanoids in A-pose only. Use the web rig (`web-recipes.md`) for quadrupeds or anything else.
- Bulky bodies: the library was animated on a slim mannequin, so arms can pass slightly into a wide torso.
