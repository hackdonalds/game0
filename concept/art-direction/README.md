---
chapter:
  slug: art
  number: 10
  title: Art Direction
  kicker: Painterly and luminous
  summary: Stylized painterly, epic and never grim. The palette, the visual rules, how each people builds, the modular kits and the biomes.
  docs:
    - art-direction/architecture.md
    - art-direction/modular-kit.md
    - art-direction/kit-sheets.md
    - art-direction/biomes.md
  catalogues: [ architecture, biomes ]
  art: an artist's easel on the edge of a floating isle with a half-finished painting of the sky isles, paint palette with soft muted golds teals and greens, brushes, the real vista behind it in matching colours
---

# Art Direction

Stylized painterly, epic high fantasy. Grand and luminous, never grim.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Rendering | Stylized painterly: hand-painted textures, soft lighting, gentle rim light |
| Camera | Third-person, over the shoulder |
| Characters | Heroic stylized proportions: slightly larger hands, heads and shoulders, readable silhouettes at distance |
| Reference use | The reference anchors the palette and mood; other elements stay open to exploration |
| 3D fidelity | Hand-painted, mid detail: chunky readable shapes, with detail painted into textures rather than modelled |
| Peoples | Near-human peoples, each with a signature trait that always reads (see [character customization](character-customization.md)), not beast-folk. The animal-folk look of [lineup 02](../../art/concept/peoples-lineup-02.png) was retired with the earlier peoples (see [peoples](../world/peoples.md#retired-concepts)) |
| Colour and light | Softer and more muted than the first tests: gentler saturation, painterly atmosphere. The palette below is applied at lower saturation |
| Texture lighting | Flat, unlit colour textures (Meshy 7.1). Painterly lighting comes from in-engine shaders, not baked into textures ([lighting test](../../art/models/tests/lighting-ab/compare-unlit.png)) |
| Time | Day and night cycle and four seasons, changing light, colour and foliage |
| Character concept format | Turnaround sheets (front, side, back) on a neutral background, used as input for Meshy image-to-3D |

## Starting reference

![World tree on a floating isle](../../art/references/world-tree-floating-isle.webp)

## Locked: landscape style

Approved from the first style tests: [market town](../../art/concept/style-test-01-market-town.png) and [airship](../../art/concept/style-test-03-airship.png). These two images are the reference for environments.

Characters are not locked. The [adventurer test](../../art/concept/style-test-02-adventurer.png) read as a generic young sword hero, and character design needs its own pass.

## Palette

Taken from the reference.

| Role | Colour | Hex |
| --- | --- | --- |
| Magic and water glow | Teal | `#2FC4B2` |
| Deep water and shadow | Deep teal | `#0E5A57` |
| Sunlight and highlights | Warm gold | `#E3B45A` |
| Foliage and grass | Moss green | `#4F7A3A` |
| Settlements | Terracotta roofs | `#C7643A` |
| Stone and paths | Parchment stone | `#F3ECD9` |
| Night and UI ground | Ink green | `#12261F` |

## Visual rules

- **Light:** warm golden key light with cool teal shadows and fill. Magic glows teal.
- **Shapes:** organic, twisting forms for nature, and tall gothic spires for civilisation. Isles taper into rock and root undersides.
- **Scale:** huge landmarks (world tree, spires) seen at a distance give every shard a skyline.
- **Detail:** dense detail only near the player's focal points. Surfaces far away read as soft painted mass.
- **Readability:** combat effects and enemy tells must read clearly against busy foliage, so keep effects high-contrast against the moss and stone.

## Asset pipeline

- **Concept art:** `bun run art:image` with `openai/gpt-image-2.5-sunburst`, using the reference image as a style input. Saved to `art/concept/`.
- **3D models:** generated with the Meshy MCP from concept art, saved to `art/models/` as `.glb`, then hand-tuned as needed.

## Open questions

- How each season looks, weather, and how the sky looks below the isles
- UI style: parchment and gold, or minimal glass
- Visual identity for each biome and isle type: drafted in [Biomes](biomes.md)

## Related

- [Character customization](character-customization.md)
- [Architecture](architecture.md) and the [modular kit](modular-kit.md)
- [Biomes](biomes.md)
