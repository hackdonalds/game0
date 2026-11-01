# Family contracts

`art/families/<family>/contract.json` is read by every forge step and by the runtime. Change it deliberately: renaming a bone, region, slot or key breaks every existing asset of the family.

## Fields

| Field | Meaning |
| --- | --- |
| `rest` | Rest pose and the bone-axis rule: **every bone points straight up (+Z in Blender), roll 0**. All bodies then share identical local rest rotations, so clips need no runtime retargeting |
| `skeleton.core` / `optional` | Bone names (humanoid: Godot SkeletonProfileHumanoid). Core must exist; optional may |
| `skeleton.chains` / `chainParents` | Optional chains (`Mantle_L_01..04`, `Tail_01..08`, …) and the bone each hangs from |
| `skeleton.limbChild` | Which child a bone "points at"; used by retarget (limb direction matching) and wrap (limb stretching) |
| `sockets` | Non-deforming socket bones: parent bone, vertices whose centroid places it (`from`), optional ray to the surface and offset |
| `regions`, `boneRegion`, `chainRegion` | Body regions for hiding under gear; a vertex's region is that of its heaviest bone. Max 32 |
| `gearLayers`, `slots` | Layer order and push-out offset; every gear slot names its layer (`skin` for hair, beard, brows and signature parts) |
| `dye` | Channels and encoding |
| `sliders.bone` | Bone sliders: bones, op (`uniformScale`, `translateOut`, `translateUp`, `translateAlongLimb`), range, amount in metres or scale |
| `sliders.morph` | Morph slider names; each is a `_pos`/`_neg` shape key pair |
| `sliders.expressions` | ARKit 52 names |
| `peoples` (or `species`) | Per people: height range, chains it uses, slider clamps, locked features, palettes |
| `budgets` | Triangles and texture size per asset kind |
| `skeleton.limits` | Max bend per joint (degrees between parent limb and limb); retarget clamps clips to it |
| `sliderPose`, `poseOffsets`, `peoples[id].pose` | Additive pose offsets (arm spread) for wider bodies, per slider unit or per people; runtime, check_fit and renders apply them |
| `peoples[id].defaults` | Slider values a new character of that people starts with |

## Adding a people

1. Add an entry under `peoples` with `heightMetres`, `chains`, `clamp`, `locked: ["people_<id>", ...]` and palettes. Clamps keep signatures readable (`concept/art-direction/character-customization.md`, rule 5).
2. Follow recipes.md §1. Existing gear gets the new `people_<id>` key by refitting against the updated base (`fit_gear` again per piece; it's cheap and scripted).
3. Add the people to `concept/world/peoples.md` and the site's peoples data.

## Adding a slider

1. Bone slider: add to `sliders.bone`; no asset work.
2. Morph slider: add the name to `sliders.morph`, sculpt or export the `_pos`/`_neg` keys on the base, then refit gear so it gets the keys.

## Adding a gear slot, socket or chain

- Slot: add to `slots` with its layer. Existing gear is unaffected.
- Socket: add to `sockets`, rerun `canonicalize` for the base and `build_people` for each people.
- Chain: add to `chains`, `chainParents` and `chainRegion`; rig it on the base; peoples that use it list it in `chains`.

## Adding a family

Copy the closest contract (`humanoid`, `quadruped`, `rigid`), then:
1. Define core and optional bones, `limbChild`, chains, sockets and regions for the body plan. Keep the "bones point up" rest rule.
2. Add name aliases for any external rig you will import to `aliases()` in `scripts/forge/lib.py` (Meshy, Tripo and Rigify animal rigs use their own names).
3. Make the base (first species), its clip library, and one fitted gear piece, and validate all three in Godot before generating more.
