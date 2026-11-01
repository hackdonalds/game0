---
name: asset-forge
description: Make customisable, animated 3D game assets for game0 that fit the shared body-family system: peoples and NPC bodies with sliders and faces, gear, clothes and armour that fit every body, props with sockets, creatures, ships and environment pieces, dye masks, animation clips, and Godot/three.js exports. Use whenever work involves creating or converting a character, creature, garment, prop, ship or environment asset, rigging, skin weights, shape keys or sliders, gear fitting, retargeting animations, dye colours, sockets, art/families, or the art:forge scripts.
---

# asset-forge

Assets are customisable because they follow a **family contract**, not because of the generator. Each body family (`art/families/<family>/contract.json`) fixes one base mesh topology, one skeleton with sockets, body regions, gear layers, dye channels, slider names and per-people clamps. Generators (Meshy, TRELLIS.2) only supply *shapes and paint*; the deterministic `art:forge` steps turn them into contract assets. So any gear fits any body, any clip plays on any body, and new peoples or creatures plug in without touching existing assets.

Research behind every choice: `docs/reports/AI 3D game asset pipeline.md`.

## Decisions (agreed with the user, 2026-11-01)

| Topic | Decision |
| --- | --- |
| Licensing | User is in the EU/UK/KR: **never use Tencent models** (Hunyuan3D, Hunyuan-Paint, HY-Motion, Hunyuan3D-Part) or their outputs. Repo is **public**: never commit raw Mixamo, Rokoko or Asset Store files; only retargeted clips |
| Humanoid base | MakeHuman **MPFB2 CC0** base mesh; every people is a wrapped signature shape key on it |
| Families | One humanoid family for Galeborne, Anchorkin, Rootwardens and humanoid NPCs; mantle, tail and ears are optional bone chains |
| Customisation | **Live sliders in the game**: bone sliders + paired morphs, clamped per people; **ARKit 52** expressions for faces |
| Materials | Painterly albedo + toon ramp; no PBR maps |
| Secondary motion | Procedural spring bones (Godot SpringBoneSimulator3D, three-vrm style springs) for tails, ears, capes, mantles, hair |
| Gear | 4 layers: under → garment → armour → cloak, with covers/hides |
| Dyes | 3 channels (primary, secondary, accent); colours come from crafted dye items |
| Paid | Meshy credits only (through the `meshy` skill and its budget). No Tripo, no cloud GPUs |
| Engines | Godot 4.7 (installed) and three.js WebGLRenderer |
| First slice | Galeborne end to end |

## Guardrails

1. **Approval gates.** Stop for the user's OK (a) before spending credits (the `meshy` skill's dry run), (b) after generation, with renders next to the concept, (c) after wrap/rig/fit, with posed renders, before animation and export.
2. **Scripts, not ad-hoc Blender code.** Every stage is a step in `scripts/forge/`, run headless with `bun run art:forge <step>`. Use the Blender MCP only to inspect or debug interactively; long work through the MCP times out after about 4 minutes. If a step is missing, add a new script in the same style (JSON args in, one `FORGE_RESULT` line out) rather than pasting code into the MCP.
3. **Look at renders.** After every geometry step run `art:forge render` (posed, `--color regions` for bodies, `--color dye` for masks) and read the PNGs before going on.
4. **Validate before anything ships**: `art:forge validate`, `art:forge godot`, then `art:forge web` for the site.
5. **Licences.** Every source asset gets a line in its `.json` sidecar: origin, licence, credits. See `references/sources.md` for what is allowed.
6. **Pilot before batch**, as in the meshy skill.

## Steps

`bun run art:forge` with no arguments lists them. All paths are repo-relative or absolute; outputs are GLB.

| Step | What it does |
| --- | --- |
| `inspect --in f.glb` | Objects, bones, shape keys, triangles, UV sets, forge metadata, size |
| `canonicalize --in rigged.glb --out body.glb [--people id] [--height m]` | Any rig (Meshy, Mixamo, UE, Rigify) → contract skeleton: metres, feet on 0, canonical names, Root, bones pointing up, sockets, `Regions` UV, ≤4 weights |
| `wrap --base base.glb --target people.glb --out base+key.glb --key people_<id>` | Base topology onto a people's sculpt → signature shape key + `.rest.json` joints, with a fit report |
| `build_people --base base+keys.glb --rest x.rest.json --people id --out body.glb` | The people's shipped body: signature key on, skeleton at the people's joints |
| `fit_gear --body body.glb --gear piece.glb --out fitted.glb --slot top` | Push-out by layer, skin weights, one shape key per body key, auto `covers`; writes `.part.json` |
| `retarget --source clips.glb --target body.glb --out anims.glb [--clips [..]]` | Any humanoid clips → family clip library (rotations + Hips translation only) |
| `dye --in f.glb --mode analyze --k 6` then `--mode write --channels {...}` | Colour clusters → `<asset>.dye.png` mask |
| `render --in f.glb --out prefix [--with gear.glb] [--action clip --frame n] [--pose {..}] [--keys {..}] [--color texture\|regions\|dye\|single]` | Orthographic QA renders |
| `validate --in f.glb [--kind body\|gear\|anims\|prop] [--body body.glb]` | Contract check: bones, sockets, rest axes, weights, regions, keys, slots, budgets |
| `godot --in f.glb` | Headless Godot 4.7 import into a throwaway project |
| `web --in f.glb` | three.js copy (`.web.glb`): meshopt + webp, keeps TEXCOORD_1 and the node graph |

## Routes

Full recipes with commands are in `references/recipes.md`. In short:

- **People (body):** concept turnaround → Meshy base (meshy skill) → web rig → `canonicalize` → `wrap` onto the family base → `build_people` → regions render → hair/brows/beard as `skin`-layer gear → validate.
- **NPC:** no new mesh. An appearance JSON (people, slider values, parts, dyes) rolled inside the people's clamps.
- **Garment/armour:** concept of the piece on the base body in A-pose → Meshy (`meshy-t2.5`/`7.1`) → align to the body → `fit_gear` (slot from the contract) → `dye` → posed renders with sliders at both ends → validate with `--body`.
- **Prop / held item:** Meshy `meshy-t2.5` → origin at the hand-hold with an empty named `Grip` (Y along the handle) → `dye` → validate `--kind prop`. It attaches to `Socket_Grip_R/L`, `Socket_Back`, `Socket_Hip_L/R`.
- **Animation:** CC0 Quaternius UAL or Meshy web presets → `retarget` → family library `anims/<set>.glb`.
- **Creature:** add or reuse a family contract (`quadruped` exists) → same body steps with that family; legs map front/back separately.
- **Ship / building / environment:** `rigid` family: Meshy pieces or a procedural generator (`scripts/forge/procgen/<kind>.py`, deterministic, JSON spec + seed), sockets as `Socket_*` empties, dye masks, budgets from the contract.

## Where files go

| What | Path |
| --- | --- |
| Generator outputs and their sidecars (sources) | `art/models/<people or set>/` (meshy skill layout) |
| Family contracts | `art/families/<family>/contract.json` |
| Family base, peoples, clip libraries | `art/families/<family>/base.glb`, `peoples/<id>.body.glb` + `.rest.json`, `anims/<set>.glb` |
| Fitted gear and parts | `art/families/<family>/gear/<slot>/<id>.glb` + `.part.json` + `.dye.png` |
| Rigid assets | `art/families/rigid/<kind>/<id>.glb` + `.dye.png` |
| Scratch and QA renders | the session scratchpad, never the repo |

Engines read the plain GLB (Godot) or its `.web.glb` (site). How the runtime applies sliders, regions, dyes, gear and clips: `references/runtime.md`.

## Not built yet (be honest about these)

- **MPFB2 base** (`art/families/humanoid/base.glb`): install the MPFB2 Blender extension, export the CC0 base with its targets mapped to the contract's slider names. This is step 1 of the Galeborne slice. Until it exists, canonical Meshy bodies stand in, and wraps from them are coarse.
- **Face-accurate wraps** need landmarks (eyes, mouth corners, nose tip, ears); `wrap` currently fits proportions and silhouette only.
- **ARKit 52 expression keys** on the base (free ARKit blendshape baker or by hand).
- **Runtime code** in Godot and three.js (`references/runtime.md` is the spec), `procgen/` generators, the quadruped base, and a local TRELLIS.2 install.

Lessons and gotchas from building these steps: `references/gotchas.md`. Adding a family, people, slot or socket: `references/contracts.md`.
