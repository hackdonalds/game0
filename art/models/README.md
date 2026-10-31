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
```

Each `.glb` has a `.json` sidecar with the Meshy task ID, input images and credits used, and a `.thumb.png` preview.

## Pipeline

1. **Concept:** generate a base-body turnaround with `bun run art:image`, using the people's turnaround sheet as the reference. The base body wears plain underclothes, with no gear, props or swappable features. Locked features stay on (bark, shell, tail).
2. **Views:** crop the sheet into front, side and back images in `art/concept/views/`.
3. **Base model:**
   ```sh
   bun run art:3d model art/models/<people>/base <front> <side> <back> --polycount 20000 --pose a-pose
   ```
4. **Rig:** `bun run art:3d rig art/models/<people>/base-rigged --task <base task id> --height <metres>`
5. **Parts and props:** one concept image each, then `bun run art:3d model <out> <image> --polycount 3000-5000 --pose none`.

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

Attachment offsets live in `<people>/attachments.json`: for each slot, the bone and each option's position (metres), rotation (degrees) and scale relative to that bone. Tune them in the creator demo's Fit panel and paste the copied JSON back.
