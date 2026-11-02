# Local rig and animation (verified 2026-11-01 on the Rootwarden, 0 credits)

`bun run art:rig <in.glb> <out.glb>` turns a static Meshy base body into a rigged, animated GLB with no paid service. `bun run art:rig --check <in.glb>` only reports whether the body is rig-ready (✗ blockers, ! warnings) and exits non-zero on a blocker; the full run does the same check first. It needs Blender at `/Applications/Blender.app` (or `BLENDER=<path>`).

## What it runs

1. `scripts/rig/autorig.py` (headless Blender) finds the joints from the mesh shape, builds a 52-bone game skeleton (with three bones per finger) and skins it.
   - Joints come from evenly sampled surface points, not vertices: Meshy meshes have big faces, so vertex slices leave holes.
   - The crotch is found by scanning up the legs until the gap closes, the armpit by scanning up until the arms merge with the torso, and the shoulder by extending the arm's centre line. Beards, moss and crowns don't fool this.
   - Wrists are the first narrowing of the arm when walking back from the fingertips (hand lengths vary too much for a fixed fraction). The hand axis is aimed at the middle of the hand, not at the fingertip that sticks out most.
   - Fingers come from slices across the hand: the middle of the stretch where slices cross four separate fingers, traced out to the tips and back to the knuckles. The thumb is the second blob in 2D cross-sections between wrist and knuckles (it can stick out of the palm's face, not just its edge). Closed fingers fall back to a mitten. Spread fingers in the concept are what make this work: the old "fingers together" prompts produced mitten hands.
   - Weights come from Blender's automatic (bone-heat) weights on a voxel-remeshed, watertight copy, copied back to the real mesh. Thin bits the copy loses (twigs, leaf tips) take weights from the nearest weighted vertex.
   - Finger weights are not bone heat (finger gaps are thinner than the proxy's voxels, which glues fingers together): each vertex's hand weight is shared among the hand and finger bones by distance measured along the surface, so a curled finger can't grab its neighbour.
   - The skeleton includes a non-deforming `carry` bone in front of the chest for props.
2. `scripts/rig/retarget.py` plays the biped animation library (`art/anims/biped/`, 188 clips in 9 sets, built from CC0/CC BY sources by `bun run anim:build biped`; contract in `art/anims/README.md`) on the new rig. `--sets idle,locomotion,...` picks sets (default all, about 6 MB with the body).
   - Each bone copies the library skeleton's world-space rotation change. Limbs are first matched on bone direction (T-pose library, A-pose bodies); spine, neck, head and feet copy the change as is, because their bone directions are conventions (CMU's head bone points 45 degrees forward, which used to tip heads onto chests).
   - Finger motion is not played yet: the finger bones exist and are skinned, but when a thumb side is misread the palm flips and the wrist twists, so hands keep the model's open shape for now.
   - Hip motion and ground speeds are scaled by leg length. Speeds per clip land in `<out>.clips.json` with the catalog entry.
   - To add or change clips, edit `art/anims/biped/recipes.json` and rebuild the library (`art/anims/biped/README.md`), then re-rig.
3. gltf-transform compresses it (meshopt, 1024 px WebP textures): about 6 MB for a 20k-poly body with 142 clips (`--sets` trims it).

## Checking the result

Debug renders: `blender -b --factory-startup -P scripts/rig/render.py -- <file.blend> <out_dir> [Clip frame ...]` draws front and side views with joint markers. The `.blend` files are left in the temp folder `art:rig` prints. Check the rest pose (joints inside the body, hips at the crotch, shoulders in the deltoids), then a few clip frames for stretched spikes or collapsing joints. For fingers, render close-ups with a small orthographic scale centred on `hand.L`'s tail and check a fist (Punch) and a grip (CarryWalk).

## In three.js

- GLTFLoader strips dots from names: `hand.L` becomes `handL`.
- The jump clips are in place. Drive the height in code: launch about 0.1 s into JumpStart, loop JumpLoop while airborne, play JumpLand from 0.05 s on touchdown.
- Clip names are the library ids (`walk`, `jump_start`, `carry_idle`…); browse them with `bun run dev:demo anim-library`.
- The carry clips hold the load between the palms: place props at the hands' midpoint each frame, not on a fixed socket.
- Move characters at the `speed` in `<out>.clips.json`, or the feet skate.
- Example: `demos/rootwarden-anim/src/main.ts`.

## Limits

- Verified on the Rootwarden (open hands), Anchorkin and Galeborne (closed hands, mitten fallback).
- Humanoids in A-pose only. Use the web rig (`web-recipes.md`) for quadrupeds or anything else.
- Bulky bodies: most source clips were animated on slim bodies, so arms can pass slightly into a wide torso.
