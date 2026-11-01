# Models

3D models generated with Meshy, organised for the [character customization](../../concept/art-direction/character-customization.md) system. Characters are never generated whole. Each people gets a neutral base body, and swappable parts are generated as separate models that attach to the skeleton.

## Layout

```
art/models/
  <people>/
    base.glb          # neutral base body, A-pose, ~20k triangles, unrigged
    base-rigged.glb   # Meshy auto-rig of the base body (+ `.walk.glb` and `.run.glb` sample animations)
    <part>.glb        # signature parts: horns, masks, shell gardens, growths
  props/
    <name>.glb        # held items and attachments
  environment/
    floating-island.glb   # hand-made in Blender: island, trees, river, waterfalls (vertex colours, ~130k triangles)
    sky-backdrop.glb      # distant mountains and cloud sea around it
```

Environment models are colour-baked to vertex colours, so they need no textures. Waterfall meshes keep their UVs and use the `Web_Waterfall` material, which pages replace with an animated shader. `scripts/web-environment.ts` compresses them (meshopt, GPU instancing) into a demo's `public/models/`.

Each `.glb` has a `.json` sidecar with the Meshy task ID, input images and credits used, and a `.thumb.png` preview.

## Pipeline

The step-by-step workflow, cost routing and guardrails are in the project's Meshy skill (`.claude/skills/meshy/SKILL.md`). In short:

1. **Concept:** base-body turnaround with `bun run art:image`, cropped into views in `art/concept/views/`.
2. **Mesh first:** `bun run art:3d model <out> <images...> --model <model> --polycount <n>`. It dry-runs and prints the cost; add `--yes` to spend.
3. **Texture:** rerun with `--texture` once the geometry is accepted, or `bun run art:3d retexture` for variants.
4. **Rig and animate:** on the Meshy web app (free), or `bun run art:3d rig` (5 credits).

Every paid task is logged in `credit-ledger.csv`.

## Budgets

| Asset | Triangles |
| --- | --- |
| Base body | ~20k |
| Signature part | ~5k |
| Prop | ~3k |

## Known limits

Meshy output is for prototypes and web demos, and it's the starting point for production assets. These still need a 3D artist working in Blender:

- face and body sliders (blend shapes);
- clothing fitted to each body;
- weighting the tail and shell to the skeleton;
- consistent topology across the peoples.

## Attachments

Attachment offsets live in `<people>/attachments.json`: for each slot, the bone and each option's position (metres), rotation (degrees) and scale relative to that bone. Tune them in the Peoples Creator demo's Fit panel (`demos/creator`) and paste the copied JSON back.
