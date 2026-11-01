# Recipes

Commands use `S` for the session scratchpad and `F=art/families/humanoid`. Every Meshy call goes through the `meshy` skill (dry run, cost, user OK).

## 0. Family base (once per family)

Humanoid (done; rerun only to change sliders):
```
blender -c extension install mpfb --enable          # once; the faceunits01 pack (CC0) goes in MPFB's user data/targets
bun run art:forge mpfb_base --out $S/mpfb.raw.glb   # sliders from art/families/humanoid/mpfb-targets.json
bun run art:forge canonicalize --in $S/mpfb.raw.glb --out $F/base.glb
```
Then rerun `wrap` for every people (the base loses its `people_*` keys) and refit all gear.

## 1. A people (the Galeborne route)

1. Concept turnaround of the body in A-pose → Meshy base (meshy skill) → web rig → `art/models/<people>/base-rigged.glb`. **Gate.**
2. `canonicalize --in art/models/<people>/base-rigged.glb --out $S/<people>.canon.glb --people <people> --height <m>` (middle of `heightMetres`).
3. `wrap --base $F/base.glb --target $S/<people>.canon.glb --out $F/base.glb --key people_<people> --shrink-regions [bare-skin regions]`. Regions where the Meshy body has feathers, hair or clothes fused on stay out of the shrinkwrap; the skeleton fit gives them the right proportions. Galeborne: `["shin_l","shin_r","foot_l","foot_r","hand_l","hand_r"]`.
4. `build_people --base $F/base.glb --rest $F/base.rest.json --people <people> --out $F/peoples/<people>.body.glb`; move the `.rest.json` to `peoples/<people>.rest.json`. Sockets are re-placed on the people's surface.
5. Signature parts from the same Meshy body, with its textures and no new credits:
   ```
   extract --source $S/<p>.canon.glb --body $F/peoples/<p>.body.glb --out $S/x-crest.glb --regions '["head","neck"]' --min-distance 0.01 --skin-regions '<bare regions>' --skin-tolerance 0.1
   fit_gear --body $F/peoples/<p>.body.glb --gear $S/x-crest.glb --out $F/gear/crest/<p>-crest.glb --slot crest --rest-keys '{"people_<p>":1}' --own-shape true --covers '[]'
   ```
   Clothes cut this way are fitted against the **base** without `--own-shape`, so they fit every people.
6. Add `defaults` (slider values) for the people in the contract; the runtime applies them.
7. **Gate:** renders with gear (`render --in body --with '[gear..., anims]' --action walk --keys {...}`), then `validate`, `godot`, and the demo (`bun run --cwd demos/creator dev`).

## 2. NPC variety

No meshes. Roll an appearance inside the people's clamps:
```json
{"family": "humanoid", "people": "anchorkin", "sliders": {"height": 0.4, "body_muscle": 0.8, "face_nose_width": -0.3},
 "parts": {"top": "anchorkin-smock", "beard": "slate-fibres"}, "dyes": {"top": {"primary": "dye.ochre", "secondary": "dye.slate"}}}
```

## 3. Garment, armour, hair

1. Concept: the piece **worn on the base body**, A-pose, front/side/back, plain background. Hair and helmets: head turnaround.
2. Meshy: `meshy-7.1` for fitted clothes (multi-view), `meshy-t2.5` for rigid armour plates; mesh first, then texture. **Gate.**
3. Align to the body in rest pose (Blender MCP: scale, move, rotate until it sits; record the transform in the sidecar). Delete any body parts Meshy fused into the piece.
4. `fit_gear --body $F/base.glb --gear art/models/gear/<id>.glb --out $F/gear/<slot>/<id>.glb --slot <slot> [--hides ["cloak"]]`. Fitting against the **base with all keys** gives the garment every people and slider key at once.
5. `render --in $F/peoples/<people>.body.glb --with $F/gear/<slot>/<id>.glb --pose {...} --keys {"body_muscle_pos": 1}` for each people and both slider ends. Look for poke-through and stretched cloth. **Gate.**
6. `dye --mode analyze`, pick channels with the user, `dye --mode write`.
7. `validate --in ... --body $F/base.glb`, `godot`.

Capes and long skirts: they get smoothed weights automatically (vertices more than 3 cm off the body). Add a bone chain plus spring bones if they need to swing.

## 4. Props and held items

1. Meshy `meshy-t2.5`, 1,500–4,000 faces, one object per image.
2. Blender: scale to real size, origin at the hand-hold, add an empty `Grip` there with Y along the handle; set custom property `forge` = `{"family": "rigid", "kind": "prop", "rigidKind": "prop", "sockets": ["Socket_Grip_R"]}`; export.
3. `dye`, `validate --family rigid --kind prop`, `render`.

## 5. Animation library

Sources in order: Quaternius Universal Animation Library 1+2 (CC0), Meshy web presets (free on the web app; raw files stay out of git), Meshy text-to-motion (credits).
```
bun run art:forge retarget --source <clips.glb> --target $F/base.glb --out $F/anims/<set>.glb [--clips ["Idle","Walk"]]
bun run art:forge render --in $F/peoples/<people>.body.glb --with $F/anims/<set>.glb --action Walk --frame 8 --views '["left"]'
```
Check every clip on the shortest and the tallest people. Signature clips (Glide, Anchor, Take Root) are separate sets.

## 6. Creatures

1. Pick or add a family (`quadruped` exists; avian, serpent and so on are new contracts, see contracts.md).
2. The first species of a family becomes its base. Meshy generates the body; rig with Meshy's quadruped rig or Rigify's animal metarigs in Blender, named to the contract.
3. Same steps as peoples: `canonicalize --family quadruped`, `wrap` further species onto the base, `build_people` (species ids live under `species` in the contract).
4. Clips: Quaternius animal packs (CC0), retargeted with front and back legs mapped separately.

## 7. Ships, buildings, environment

- `rigid` family. Ships: hull, deck, mast, sail, rigging, figurehead and trim as separate meshes, so parts swap; sockets as empties (`Socket_Mast_1`, `Socket_Helm`, `Socket_Crew_1`, …).
- Procedural first for anything repeated (hull variants, planks, rope, rocks, island chunks): a deterministic `scripts/forge/procgen/<kind>.py` step taking a JSON spec and seed. Meshy for one-off hero pieces.
- Modular kits snap on the contract grid (0.5 m), pivots on grid corners.
- Sails billow with a few shape keys or a short bone chain; that's the only deformation on a ship.
- `dye` on hull and sail (house colours), `validate --family rigid`, `godot`, `web`.
