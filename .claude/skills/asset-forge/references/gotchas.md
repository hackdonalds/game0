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
