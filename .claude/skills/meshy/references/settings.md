# Models, settings and prompts

Source: `docs/reports/Meshy pricing and usage.md` (October 2026). Script defaults already apply the hand-painted settings: PBR off, image enhancement off, 2K textures, GLB only, pinned model.

## Models

| Model | Use for | Credits (mesh / textured) |
| --- | --- | --- |
| `meshy-t2.5` | Props, weapons, rocks, trees, most attachments. Clean triangles, 100–30,000 faces, sharper detail | 5 / 15 |
| `meshy-t2` | Attachments that should come out as separated parts. 100–15,000 faces | 5 / 15 |
| `meshy-7.1` | Character base bodies, buildings, anything with faces or anatomy. Only model with Ultra geometry | 20 / 30 (+5 Ultra) |
| `meshy-6` | Only model that honours `remove_lighting`. `--keep-lighting` bakes painted shading and highlights into the texture (verified 2026-10-31; not used, see Test results) | 20 / 30 |
| `meshy-6-lite` | Not used: cheaper but lower quality | 5 / 15 |

Retired: meshy-5, meshy-t1 / low-poly. Deprecated: meshy-7 (still the Retexture model).

## Defaults per asset type

| Asset | Command | Faces |
| --- | --- | --- |
| Base body | `model ... --model meshy-7.1 --pose a-pose` with 3 views | ~20,000 |
| Attachment (horns, mask, shell garden) | `model ... --model meshy-t2.5` (or `meshy-t2`) | 300–4,000 |
| Prop or weapon | `model ... --model meshy-t2.5` | 1,500–4,000 |
| Rock, cliff, island chunk | `model ... --model meshy-t2.5`, one shared style image per biome | 500–6,000 |
| Tree | `model ... --model meshy-t2.5`, foliage as "large leaf clumps"; expect hand fixes | 2,000–8,000 |
| Building, bridge | `model ... --model meshy-7.1`, multi-view when the back matters | 5,000–20,000 |
| Hero / marketing render | Web app, Meshy 7.1 Ultra, 4K textures, PBR on | no remesh |

Mesh first, texture second. On Smart Topology, mesh-only rerolls (5) plus one texture pass (+10) beat textured rerolls (15 each) from the first reroll. On 7.1 it wins from the second attempt.

## Input images

- PNG, 1:1 (or a cropped view), at least 1024 px, plain white or light grey background.
- Subject fills 70–90% of the frame and nothing touches the edge.
- Front-on, near-orthographic, flat even light, no cast shadows: shadows bake into the texture.
- One object per image. Several objects get merged into one distorted mesh.
- Multi-view: front first; all views share style, light and scale. Same price as single image.
- Thin parts fuse. Exaggerate thickness: thick blades, solid rope, big open hands.

## Prompt templates

Meshy's formula: subject + material + art style + technical constraints, most important words first, at most 800 characters. There is no negative-prompt field: write exclusions inline. Describe the look; don't name commercial games.

**Base-body concept sheet** (`art:image`, 21:9, `--ref` the people's turnaround):
> Character base-body turnaround sheet for 3D modeling: the same [people] shown three times side by side, evenly spaced, not overlapping: front view, side view, back view, neutral A-pose with arms angled down and away from the body, hands open. [Body description] WITHOUT [swappable feature]. Wearing only simple plain fitted undershirt and short trousers, no harness, no belts, no tools, no accessories, no cape, no tail. Full body, fully visible. Hand-painted stylized game art, mid-level detail, chunky readable shapes, softer muted colours. Plain light grey background, even soft lighting, no cast shadows, no text, no labels.

**Part or prop** (`art:image`, 1:1):
> A single [object] shown alone as a game asset, [no head / no hands], three-quarter front view, [shape and material details, thick chunky proportions]. Hand-painted stylized game art, mid-level detail, chunky readable shapes, softer muted colours. Plain light grey background, even soft lighting, no cast shadows, no text, no labels.

**Retexture style prompt** (`retexture --style`):
> Hand-painted stylized fantasy texture, soft muted colours, painted highlights and shadows, warm golden light, cool teal shadows, [material], no photorealism, no text.

## Test results

**Lighting A/B (2026-10-31, 60 credits, `art/models/tests/lighting-ab/`).** The same pickaxe concept was generated textured, PBR off, at 3,000 faces, on `meshy-7.1` and on `meshy-6 --keep-lighting`.
- `meshy-6` baked painted shading and warm highlights into the base colour.
- `meshy-7.1` gave flat colour.
- Both cost 30.
- With PBR off, each GLB has one texture and is about 4 MB (12 MB with PBR).
- Both use fragmented automatic UV layouts, so the textures are hard to repaint by hand.

**Decision (2026-10-31): keep Meshy 7.1 flat colour.** Don't use `meshy-6 --keep-lighting`. Textures stay unlit, and the painterly lighting comes from Godot and Three.js shaders.
