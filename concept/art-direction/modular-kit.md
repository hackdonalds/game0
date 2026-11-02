# Modular architecture kit

> Draft. How every building in [architecture](architecture.md) is assembled from a small set of snapping pieces. Reference sheets live in `art/concept/architecture/<style>/kit/`.

## Shared rules

- **Units:** metres. Y up, buildings face +Z (glTF). Every piece sits on a **0.5 m base grid**, so pieces from different styles can meet (Accord towns mix them).
- **Pivot:** bottom-left-front corner of the piece's grid cell, on the floor plane. A wall's thickness extends inward (−Z) from the grid line, so walls and floors meet cleanly.
- **Snap edges:** every piece's open edges land exactly on module lines. Ornaments overhang freely, but never past half a module.
- **Openings are inserts:** doors, windows and shutters are separate pieces that drop into a standard opening, so one wall piece gives many looks.
- **Materials:** each style has one hand-painted trim sheet (stone courses, timber, roof, trims, signature details). Pieces are UV-mapped onto it, so the whole kit shares one material and batches well.
- **Wear:** variants come from the trim sheet (moss, cracks, repairs) and from a sinking variant (tilted, cracked) of the key pieces.
- **Budgets:** wall or roof piece ≤ 600 triangles, corner or insert ≤ 400, signature or landmark pieces ≤ 3k.

## Modules per style

| Style | Horizontal module | Storey | Wall | Character of the grid |
| --- | --- | --- | --- | --- |
| Anchorkin | 3 m | 4 m | 1 m thick, battered 8° inward | Wide and low; doors 2 × 3.2 m for huge folk |
| Galeborne | 2 m | 3 m | 0.3 m timber or stone skin | Narrow and tall; stacks of 3–5 storeys, cantilevered decks |
| Accord | 2 m | 3 m | 0.5 m | Anchorkin-style stone ground floor, timber upper floors, sail awnings |
| Rootwardens | No rectilinear grid | — | — | Sockets instead: root segments end in standard round caps (0.6, 1.0, 1.6 m, and 2.5 m great roots), tapers step between sizes, dome shells come in radii 3, 5 and 8 m with root anchors on their surface, openings are cut by azimuth and take burl inserts |
| Old world | 4 m | 6 m | 1 m, razor-clean | Monumental and exact; rings come in radii 4, 8 and 16 m, with one standard inset channel width |

## Piece families

Built styles (Anchorkin, Galeborne, Accord):

1. **Foundations:** plinth, slope step, cliff-edge foundation, cantilever deck bracket.
2. **Walls:** plain, window, door, half-height, end cap, and the style's signature wall (Ledger band, sail panel, timber frame).
3. **Corners:** outer, inner, column or buttress.
4. **Floors and access:** floor or deck tile, stairs (straight and spiral), balcony, railing.
5. **Roofs:** straight run, hip corner, gable end, ridge cap, spire or cupola crown.
6. **Inserts and details:** doors, windows, shutters, cornice and trim strips, lanterns.
7. **Signature attachments:** chains and mooring rings (Anchorkin), sails, masts and rigging (Galeborne), awnings and banners (Accord).

Rootwardens: root segments (straight, bend, fork, flare-to-ground), dome shells (quarter, half, full), door and window burls, moss and flower caps, pod shell, hanging roots, lantern fungus.

Old world: monolith blocks, wall slabs, arch and ring segments (90° and 45°), floor slabs with channels, column, steps, broken and tilted variants of each.

## Reference sheets per style

| Sheet | Shows |
| --- | --- |
| `kit-structure` | Foundations, walls, corners, floors and stairs: orthographic front views on a grid with module lines, plus one three-quarter view each |
| `kit-roofs` (Old world: `kit-rings`, Rootwardens: `kit-shells`) | Roof pieces and crowns, or ring/arch segments, or dome shells |
| `kit-details` | Inserts, trims and signature attachments |
| `kit-assembly` | An exploded view of one building being assembled from the kit, plus three buildings from the concept sheets rebuilt only from kit pieces |
| `materials` | The trim-sheet swatches: 6–8 painted tiles |
