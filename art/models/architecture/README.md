# Architecture kits

One modular kit per style, built to the rules in [modular-kit.md](../../../concept/art-direction/modular-kit.md) from the reference sheets in `art/kit/architecture/<style>/`.

```
art/models/architecture/
  <style>/kit.json        piece manifest: the contract for blockouts, 3D models and the runtime
  <style>/<piece-id>.glb  models, added piece by piece
```

Check every manifest with `bun scripts/kit/validate.ts` (or pass one file).

## `kit.json`

```jsonc
{
  "style": "anchorkin",                     // rootwarden | anchorkin | galeborne | accord | old-world
  "prefix": "ank",                          // every piece id starts with "<prefix>-"
  "grid": { "base": 0.5, "module": 3, "storey": 4, "wall": 1, "batter": 8 },
  "scaleFigure": 2.6,                       // height of the people the doors are sized for, metres
  "trimSheet": "ank-trim",                  // the one material every piece maps onto
  "pieces": [
    {
      "id": "ank-wall-window",
      "family": "wall",                     // see families below
      "name": "Battered wall, window",
      "size": [3, 4, 1],                    // width (x), height (y), depth (z) of the grid footprint, metres
      "pivot": "bottom-left-front",         // or "bottom-center" for free-standing pieces
      "tris": 600,                          // triangle budget
      "variants": ["intact", "mossy", "sinking"],
      "opening": { "kind": "window", "size": [1, 2], "offset": [1, 1], "accepts": "ank-window-" },
      "ref": { "sheet": "kit-structure", "label": "Battered Wall (Window)" },
      "notes": "Batter 8° inward on the outer face only."
    }
  ]
}
```

Top level, besides `pieces`:

- `materials`: the trim-sheet swatch names from the style's `materials` sheet.
- `prefabs`: buildings from the `kit-assembly` sheet as `{ "id", "name", "footprint": [modules x, modules z], "storeys", "pieces": [{ "id", "count" }] }`. Counts are estimates from the drawings until the blockouts confirm them.
- `notes`: where a drawn label contradicted the spec. The spec always wins; each piece's own `notes` say what changed.

Optional piece fields:

- `opening`: an opening in the piece (`kind` door | window | arch), its `size` [w, h] and `offset` [x, y] from the pivot, and the id prefix of the inserts it `accepts`.
- `openings`: several openings on a curved piece (Rootwarden shells), each `{ "kind", "size": [w, h], "azimuth", "height", "accepts" }`. `azimuth` is degrees around the dome (0 = front, +Z; 90 = +X), `height` is the sill above the floor. The opening is cut through the shell and the insert follows the curve.
- `sockets` (Rootwardens): round connection caps, each `{ "name", "pos": [x, y, z], "dir": [x, y, z], "diameter": 0.6 | 1.0 | 1.6 | 2.5 }`. `dir` points out of the piece; two sockets join when they meet at the same point with opposite directions and equal diameters. Shells carry root anchors on their surface, bends and arches carry a 0.6 m `hang` point underneath.
- `layout` (prefabs): `[{ "id", "pos": [x, y, z], "rotY" }]`, the placement of every piece. `scripts/kit/blockout.py` builds it and checks each socket joint.
- `radius` and `arc` (rings, arches, dome shells): radius in metres, arc in degrees.
- `free: true`: details, attachments and props that overhang or sit anywhere; their `size` is a bounding box, not a grid footprint, so it is not checked against the grid.

## Families and budgets

| Family | What | Budget (triangles) |
| --- | --- | --- |
| `foundation` | plinths, slope steps, cliff-edge and cantilever foundations | 600 |
| `wall` | wall panels, incl. openings and signature walls | 600 |
| `corner` | outer and inner corners, columns, buttresses | 400 |
| `floor` | floor and deck tiles, terraces | 300 |
| `access` | stairs, ladders, balconies, railings | 600 |
| `roof` | roof runs, hips, gables, ridges, parapets, chimneys | 600 |
| `crown` | spires, cupolas, beacon and crystal crowns, domes | 1500 |
| `insert` | doors, windows, shutters | 400 |
| `trim` | cornices, bands, infill panels | 300 |
| `attachment` | chains, sails, rigging, banners, lanterns, overgrowth | 800 |
| `root` | Rootwarden root segments | 800 |
| `shell` | Rootwarden dome and pod shells, roof caps | 1500 |
| `ring` | old-world ring and arch segments | 800 |
| `block` | old-world monoliths, slabs and columns | 600 |
| `prop` | props in the style's language | 800 |

## Nature kits

Biome nature kits use the same manifest at `art/models/nature/<biome>/kit.json` (`style` is the biome: roothold, crag, meadow, garden, forest, lagoon, ruin), with references in `art/kit/biomes/<biome>/` (`ref.sheet` `nature` or `terrain`) and `art/concept/biomes/<biome>/` (`isle-portrait`). Nature pieces sit on the ground at `bottom-center` and are usually `free: true`; scatter places them, so they have no sockets. Their families:

| Family | What | Budget (triangles) |
| --- | --- | --- |
| `tree` | trees and their silhouette variants | 3000 |
| `hero` | landmark trees (ancient tree, Grudge Tree) | 15000 |
| `plant` | understory: bushes, ferns, flowers, reeds, crops | 600 |
| `ground` | ground-cover clumps scattered by the thousand | 300 |
| `rock` | boulders, outcrops, ledges, walls | 800 |
| `lip` | isle edge pieces: overhangs, ledges, terrace edges | 1500 |
| `underside` | rock tapers, hanging roots and growth | 2000 |
| `water` | pond, mere and channel edges, falls | 800 |

A nature kit also lists its terrain textures under `terrain`: `{ "ground", "path", "cliff", "underside" }`, file names in `art/textures/biomes/<biome>/`.

Variants are named states of the same piece that share its size and sockets: `intact`, `mossy`, `broken`, `overgrown`, `sinking` (tilted and cracked), `lit` and `dead` (old-world channels).
