# Kit reference sheets

> Draft. The one spec for every kit reference sheet. Sheets live in `art/kit/<kind>/`, paintings in `art/concept/`. Prompts are built from this page by `bun run art:kit`, so a change here changes every new prompt.

## Purpose

The concept docs say what a thing is. The paintings say how the world looks. A kit sheet says how to build it: it is the drawing a modeller (or Meshy) works from to make a game asset.

So a kit sheet is not a painting. It shows each piece alone, flat-lit, at true scale, from the views a model needs, with nothing in the way. It is drawn for a game that must run well and read clearly at low resolution and at a distance.

Where a kit sheet and a painting disagree on style, the painting wins. Where either disagrees with the concept text, the text wins.

## Decisions

| Topic | Decision |
| --- | --- |
| One spec | Every kit sheet follows this page. Prompts are composed from the templates below, not written out by hand |
| Background | Plain light neutral grey, no scene, no sky, no floating rock. Only a soft contact shadow under each piece |
| Light | Flat, even studio light with no cast shadows and no rim light. Warm gold and cool teal stay as painted colour, never as baked lighting, because textures are unlit ([art direction](README.md)) |
| Scale figure | A plain human silhouette at true scale on every sheet that shows size: 1.8 m by default, or the height of the people the kit is built for (Anchorkin 2.6 m, Galeborne 1.9 m, Rootwardens 1.6 m) |
| Labels | Reference sheets carry small neat labels and dimensions. Sheets that go straight into Meshy (base bodies, single parts) carry no text at all |
| Location | Kit sheets in `art/kit/<kind>/`, each with a `.json` sidecar of the same name |
| Textures | One trim sheet per kit; every piece of the kit maps onto it ([modular kit](modular-kit.md)) |
| Detail | Detail is painted, not modelled. Shapes stay chunky and readable as a silhouette |

## Sheet types

| Type | Use for | Views | Aspect | Labels |
| --- | --- | --- | --- | --- |
| `pieces` | Modular kit pieces: architecture, nature, ships, clothing layers | Orthographic front elevation of each piece, plus a small three-quarter view beside it, on faint module grid lines | 16:9 | Name and size under each piece |
| `assembly` | How a kit builds things: an exploded building, an isle, a ship | Exploded view with leader lines, plus three finished builds in three-quarter view | 16:9 | Piece names, build names |
| `materials` | Trim-sheet swatches, terrain textures, resource tiers | Square tiles flat-on, no perspective, seamless-looking | 16:9 | Name under each tile |
| `turnaround` | A creature or a dressed character | Front, side and back in a neutral pose, one three-quarter action pose, callouts of head, hands or feet, and one texture swatch | 16:9 | Small callout labels |
| `variants` | Swappable parts on one body: signature features, horns, masks, wear states, tiers | A grid of the same base with one part changed per cell | 16:9 | Variant name per cell |
| `body-plan` | The shared base body of a creature body plan, with its sockets | Front, side, back and top views of one neutral, featureless body in a relaxed standing pose, sockets marked as small numbered rings | 16:9 | Socket names, real size |
| `body-parts` | The swappable parts of a body plan, by socket | Each part alone in side view, in one row per socket, every part ending in the same socket cap | 16:9 | Part name under each, socket per row |
| `species` | One creature built on its body plan | Side and three-quarter views of the assembled creature, its chosen parts pulled out with leader lines to their sockets, its colour mask swatches, and the storm-touched variant if it has one | 16:9 | Part names, plan name, real size |
| `gear` | Props, weapons, tools, tack and stations | Each item three-quarter front, laid out in rows by family or tier | 16:9 | Name under each item |
| `base-body` | The rig-ready base body of a people, as Meshy input | Front, side and back, side by side with wide gaps | 21:9 | None |
| `part` | One part or prop, as Meshy input | Three-quarter front, one object only | 1:1 | None |

A `pieces`, `assembly` or `materials` sheet belongs to one kit. A style's full set is listed in [modular kit](modular-kit.md#reference-sheets-per-style); a biome's is `nature` (pieces) and `terrain` (materials).

## Layout rules

- **Background:** plain light neutral grey. No scene, sky, clouds, ground plane or floating rock. A soft contact shadow is the only shadow.
- **Isolation:** every piece stands alone with clear space around it. Nothing overlaps, nothing touches the image edge.
- **Rows:** tidy rows by family, largest pieces first. One family per row where it fits.
- **Views:** orthographic front views are true elevations: no perspective, so sizes can be measured. Three-quarter views are small and sit beside the front view.
- **Grid:** kit sheets draw faint module grid lines at the kit's module ([modular kit](modular-kit.md#modules-per-style)), or 0.5 m for nature.
- **Labels:** small neat hand-lettered labels under each piece, with its size where it matters (`3 × 4 m`). A short title at the top names the kit and sheet. Labels must match the piece names in the kit's `kit.json`; where a drawn label is wrong, the manifest wins and says so in `notes`.
- **Scale figure:** a plain neutral human silhouette, labelled with its height, at true scale to every piece on the sheet. Put it beside the side view on turnarounds. State the subject's real size in the prompt (a 40 cm owl reaches the figure's knee), or the image model draws everything human-sized.
- **Consistency:** every sheet of one kit shares background, light, palette, brushwork and figure. Generate them in one chat or with the same references.
- **References:** the first attached image is always the style reference (a locked style test). Later attachments are the approved design to keep: the people's turnaround, the creature's painting, the concept sheets the kit must rebuild.

## Game-asset rules

These keep every asset cheap to draw and clear on a small screen. A sheet that breaks them is redrawn before anything is modelled.

### Shape and silhouette

- **Silhouette first.** Every asset reads as a flat black shape at its usual distance: a building at 100 m, a creature at 30 m, a weapon in the hand at 10 m.
- **Chunky shapes.** Exaggerate big forms: oversized roofs, chunky doors, big hands, thick blades. Small forms merge at low resolution, so leave them out or paint them.
- **No thin geometry.** Nothing thinner than about 5 cm on a 1.8 m figure. Ropes are solid rope, blades are thick, fingers are thick. Rigging, fringes, whiskers, chains of small links and fine lace are painted on or drawn as alpha cards.
- **Foliage as masses.** Trees and plants are a few large leaf clumps, not single leaves. Fine leaves and grass are alpha-cutout cards from the 2 × 2 sprite atlases in `art/textures/foliage/`.
- **A few silhouettes.** Two or three distinct shapes per species or piece type, not many near-copies.

### Detail and texture

- **Detail painted, not modelled.** Cracks, carvings, stitching, bark, feathers and scales are painted into the texture at broad, clumped brushwork. No tiny high-frequency noise: it shimmers when mipmapped.
- **Flat colour.** Textures are unlit. Sheets show surface colour under even light so the drawing can be read straight into a texture.
- **One trim sheet per kit.** Every piece of an architecture, nature or ship kit maps onto its kit's one trim sheet, so the kit is one material and batches. The `materials` sheet shows its swatches (6–8 tiles).
- **Texture size.** 1024 px per kit trim sheet, per creature and per base body; 512 px per gear piece, prop or part; 2048 px only for colossal creatures and hero landmarks. Meshy outputs 2K textures; they are scaled down on import.
- **Colour masks.** Characters, gear and dyeable props carry primary, secondary and accent masks ([character customization](character-customization.md)), so one texture gives many colours. Draw them in clear colour zones.

### Palette

- Use the [palette](README.md#palette) at lower saturation. One main hue and one secondary per piece, plus at most one accent.
- Keep large surfaces soft and muted so characters and effects read against them.
- Saturated colour and glow are kept for points of interest: teal crystal, glowweed, lit channels, flowers. Glow is emissive in the engine, so draw it as a clear separate zone.

### Budgets and LOD

Triangle budgets live with the thing they budget; this page does not repeat them.

| Asset class | Budget |
| --- | --- |
| Architecture pieces | Per family in [the kit manifest docs](../../art/models/architecture/README.md#families-and-budgets), with the shared rule in [modular kit](modular-kit.md#shared-rules) |
| Nature pieces | Per family in [the kit manifest docs](../../art/models/architecture/README.md#nature-kits); each piece's `tris` in its `kit.json` |
| Base bodies, parts, props, weapons | Face counts per asset type in the Meshy settings (`.claude/skills/meshy/references/settings.md`) |
| Creatures | Small (up to 1 m) 3k, medium (up to 3 m) 8k, large 15k, colossal 30k |
| Ship kit pieces | Hull sections 1.5k, sails and rigging 800, fittings 400 |

LOD-friendly drawing:

- Big forms and small attachments are drawn as separate pieces, so a lower LOD can drop the attachments and keep the silhouette.
- Nothing important depends on a small modelled detail. If a detail matters at distance, make it a big shape; if not, paint it.
- Repeated pieces (shingles, planks, chain links) are one strip on the trim sheet, not many modelled parts.

### Separable parts

- **Openings are inserts.** Doors, windows and shutters are drawn as their own pieces beside the walls they fit ([modular kit](modular-kit.md#shared-rules)).
- **Gear is layered.** Clothing is drawn by layer (under, garment, armour, cloak), each piece on its own, so it can be fitted once and worn by every people.
- **Swappable features apart.** Horns, masks, crests, tails, shells, growths and tack are drawn on their own `variants` or `part` sheets, never fused to a base body.
- **Attachment shown.** A piece that sits on another (overgrowth on a block, a saddle on a creature) is drawn alone, with a dotted outline or simple silhouette of what it attaches to.

### Rig-ready rules

For characters and creatures that will be rigged.

- **Base bodies are bare.** Plain fitted underclothes only: no props, capes, belts, tails, shells or swappable features. Those break rigging when fused to the body.
- **A-pose with gaps.** The auto-rig finds joints from the gaps at the armpits, crotch and fingers. Bridged or closed gaps give misplaced joints, fused fingers and arms that drag the torso skin. Keep the pose sentence of the `base-body` template word for word.
- **Same in every view.** The figure is mirror-symmetric and identical in front, side and back.
- **Creatures:** neutral standing pose with legs apart and straight, wings spread clear of the body, tail clear of the legs, mouth closed. Fins, tails and wings are thick enough to skin.

Rig-ready checklist, checked on the image before any Meshy credit is spent:

- Gap under each arm, all the way up to the armpit; arms 30–60° from vertical, elbows straight.
- Five fingers per hand with visible gaps, thumb apart from the palm. Closed fingers still rig, but as a mitten.
- Gap between the thighs; legs straight; feet flat, pointing forward, shoulder-width apart.
- Nothing bridges a gap: no hair, beard, feathers, moss, cloth or tail joining an arm to the body or the legs to each other.
- The figure is mirror-symmetric and the same in all three views.

## Naming and location

Kit sheets live under `art/kit/`, by the same kinds as the catalogues. Paintings stay in `art/concept/`.

| Kind | Folder | Sheets |
| --- | --- | --- |
| Architecture | `art/kit/architecture/<style>/` | `kit-structure`, `kit-roofs` (or `kit-rings`, `kit-shells`, `kit-roots`), `kit-details`, `kit-assembly`, `materials` |
| Nature | `art/kit/biomes/<biome>/` | `nature`, `terrain` |
| Ships | `art/kit/ships/` | `<ship>` (the ship's own sheet), shared kit `kit-hulls`, `kit-deck`, `kit-sails`, `kit-rigging` |
| Creatures | `art/kit/bestiary/` | `<creature>` (a `species` sheet, or a `turnaround` for older sheets), `mount-tack` |
| Body plans | `art/kit/bestiary/body-plans/` | `<plan>-body` (`body-plan`), `<plan>-parts` (`body-parts`); plans are listed in [monsters](../monsters/README.md#body-plans) |
| Peoples | `art/kit/peoples/<people>/` | `base-turnaround` (a `base-body` sheet), `signatures`, `outfits`, single parts as `<part>` |
| Shared gear | `art/kit/peoples/gear/` | `clothing-kit`, `armour-tiers`, `weapons-melee`, `weapons-ranged` |
| Skills, materials | `art/kit/skills/`, `art/kit/materials/` | `gathering-tools`, `crafting-stations-<n>`, `woods`, `metals` |
| Meshy views | `art/kit/views/` | `<subject>-front`, `-side`, `-back`: crops of a `base-body` sheet |

- File names are lowercase kebab-case. The stem is the sheet id that `kit.json` refers to in `ref.sheet`.
- Every image has a `.json` sidecar with the same stem: `prompt`, `kit` (sheet type, subject, figure height), `refs`, and either `model` and `generationId` (`art:image`) or `chat_url` and `tool` (chatgpt.com).
- A redrawn sheet replaces the old file in place. Git keeps the history.

## Making a sheet

1. Pick the sheet type and write the subject: what is on the sheet, in rows, with real sizes and materials. Take names and sizes from the concept doc and the kit's `kit.json`. For a creature, give its real size. For a `base-body`, give the people, its body and what it is drawn without (its swappable feature). One sentence or several; the builder adds the final full stop.
2. Build the prompt: `bun run art:kit <type> "<subject>" [--figure 2.6] [--title "Anchorkin kit: structure"]` prints it. Paste it into chatgpt.com with the references attached, or generate directly with `bun run art:image --kit <type> "<subject>" --ref <style ref> --ref <design ref> --out art/kit/<kind>/<sheet>`.
3. Review the image against the checklist below. Redraw on any miss; a sheet reroll is far cheaper than a model.
4. Update the kit's `kit.json` (piece names, sizes, `ref`) to match the accepted sheet.

## Prompt templates

The builder reads this section. Each `###` heading is a block; its fenced text is the block. `{name}` pulls in another block, `{subject}` is the subject, `{figure}` the scale figure height in metres, `{title}` an optional title line. Sheet types also carry an **Aspect** line. Edit the words here, not in scripts.

### style

```text
Locked painterly style: hand-painted stylized game art, chunky readable shapes, detail painted not modelled, mid-level detail, softer muted colours with gentle saturation, epic and luminous, never grim. The palette's warm gold and cool teal are painted into the surfaces, but the light is flat, even studio light: no strong key light, no cast shadows, no rim light.
```

### refs

```text
Use the attached images only as reference as described: the first attachment is always the style reference for palette and brushwork; later attachments are the approved designs to keep.
```

### sheet

```text
Game-asset reference sheet for 3D modelling, wide landscape 16:9. Plain light neutral grey background, no scene, no sky, no clouds, no floating rock, no ground plane, a soft contact shadow only. Every piece fully isolated with clear space around it, nothing overlapping, nothing touching the edge, arranged in tidy rows, each with a small neat hand-lettered label underneath.
```

### scale

```text
One plain neutral {figure} m human silhouette labelled "{figure} m" stands on the sheet once, for scale, with everything at true scale to it. A piece too small to read at true scale is drawn enlarged as an inset, with a small true-scale copy beside the figure and "enlarged" in its label. Write a size in a label only when the subject gives that size; never invent one.
```

### meshy

```text
Hand-painted stylized game art, mid-level detail, chunky readable shapes, softer muted colours. Plain light grey background, even soft lighting, no cast shadows, no text, no labels.
```

### pieces

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} MODULAR KIT PIECES sheet: {subject}. Show each piece as an orthographic front elevation (no perspective) with a small three-quarter view beside it, on faint module grid lines, with its name and size (for example "3 x 4 m") in the label. Thick, solid forms, no thin parts. {scale} {title}
```

### assembly

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} KIT ASSEMBLY sheet: {subject}. Left half: an exploded view of one build, its kit pieces pulled apart along the module lines with thin leader lines and small piece labels. Right half: three finished builds made only from the same kit pieces, each in three-quarter view, isolated on a faint grid footprint and labelled. Use only pieces from the kit's other sheets. {scale} {title}
```

### materials

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} Material swatch sheet, wide landscape 16:9, plain light neutral grey background. Square swatch tiles in a neat grid, evenly spaced, each flat-on (orthographic, no perspective, no horizon, no shadows from outside the tile), a seamless tileable painterly texture with edges that would wrap, broad clumped brushwork, no tiny high-frequency noise, a short neat label under each. Swatches: {subject}. {title}
```

### turnaround

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} TURNAROUND sheet: {subject}. Keep the exact design in the second attachment. Show front, side and back views in a neutral standing pose with limbs apart and clear of the body, one three-quarter action pose, close-up callouts of the head and of the hands, feet or claws, and one square texture swatch of its skin, fur, feathers or scale. {scale} Place it beside the side view, at TRUE scale to the stated size. {title}
```

### variants

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} VARIANTS sheet: {subject}. Keep the exact base design in the second attachment. Show the same base in a neat grid, one part changed per cell, everything else identical, each cell labelled with the variant name. Swappable parts are shown clearly separate from the body where they attach. {title}
```

### gear

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} GEAR AND PROPS sheet: {subject}. Each item alone in three-quarter front view, in rows by family or tier, with thick chunky proportions: thick blades, solid rope, chunky grips, no thin parts. {scale} {title}
```

### base-body

**Aspect:** 21:9

```text
Character base-body turnaround sheet for 3D modeling and rigging: the same character shown three times side by side, evenly spaced with wide gaps, not overlapping: front view, side view, back view. The character: {subject}. Rigging A-pose: standing straight, arms straight and angled 45 degrees down and out from the body with a clear gap between each arm and the torso all the way to the armpit, elbows straight, hands open and flat with palms facing forward, all five fingers spread wide apart with a visible gap between every finger, the thumb clearly separated and pointing away from the palm, slightly oversized hands with thick fingers, legs straight with feet shoulder-width apart and a clear gap between the thighs, feet flat pointing forward, head facing forward. Hair, beard and growths stay clear of the armpits and the gap between the legs and never join an arm to the body. Wearing only simple plain fitted undershirt and short trousers, no harness, no belts, no tools, no accessories, no cape, no tail. Full body, fully visible. {meshy}
```

### body-plan

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} BODY PLAN BASE BODY sheet for a modular creature kit: {subject}. Draw one neutral, featureless base body (no head detail, no horns, no ears, no tail tip, smooth plain skin) in a relaxed standing pose with the limbs apart and clear of the body, shown as front, side, back and top views in orthographic projection. Mark every socket where a swappable part attaches as a small numbered ring with a short label (for example "1 head", "2 horns", "3 tail"). Thick, solid forms; even proportions that can be stretched to make larger or smaller species. Only the base body and its socket labels: no parts, heads, horns, coats or tails anywhere on this sheet, because the parts have their own sheet. {scale} {title}
```

### body-parts

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} BODY PLAN PARTS sheet for a modular creature kit: {subject}. One row per socket, labelled with the socket name at the left. Each part alone in side view, all parts in a row ending in the same round socket cap so any of them fits the same base body. Chunky readable shapes, nothing thin, colour kept to soft greyscale with painted texture so species colour can be applied as a mask. {title}
```

### species

**Aspect:** 16:9

```text
Please generate an image. {style} {refs} {sheet} SPECIES sheet for a creature built from a shared body-plan kit: {subject}. Keep the base body and parts from the attached kit sheets and the creature's design from the attached plate. Show the assembled creature in side view and three-quarter view at the centre; around it, each part it uses pulled out with a thin leader line to its socket and a small label naming the part. Below: a row of four square colour mask swatches (main, secondary, accent, pattern). Show a storm-touched variant, small at the right in side view and labelled, only when the subject names one; otherwise draw no variant at all. Show only the parts this creature uses, and no description text. {scale} Place it beside the side view, at TRUE scale to the stated size. {title}
```

### part

**Aspect:** 1:1

```text
A single object shown alone as a game asset, three-quarter front view: {subject}. Thick chunky proportions, nothing thin. {meshy}
```

## Review checklist

A sheet is accepted only when every line holds. Read the image; don't trust the prompt.

- [ ] Plain light grey background; no scene, sky or ground; only contact shadows.
- [ ] Flat even light; no cast shadows or rim light painted into the surfaces.
- [ ] Every piece isolated, nothing overlapping or cut off by the edge.
- [ ] Matches the locked style and the approved design it was given (same people, same creature, same materials).
- [ ] The scale figure is there (where the type needs one), labelled, and every piece is at true scale to it.
- [ ] Views are the ones the type asks for; front views are orthographic.
- [ ] Labels are legible and match the names and sizes in the concept doc and `kit.json`. Meshy-input sheets have no text.
- [ ] Silhouettes read as black shapes at thumbnail size (shrink the image to 256 px wide and look).
- [ ] No thin geometry; detail is painted, not modelled; no fine noise.
- [ ] Colours stay muted; glow only on points of interest.
- [ ] Swappable parts are apart from the body; inserts apart from walls.
- [ ] Rig-ready sheets pass the rig-ready checklist.
- [ ] Saved in `art/kit/<kind>/` with a `.json` sidecar.

## Open questions

- Are the creature and ship budgets right? Check them against the first rigged creature and the first ship in the engine.
- Is 1024 px enough for a kit trim sheet seen up close in towns, or do Accord towns need 2048 px?
- Should every piece sheet also carry a small silhouette row (pieces as black shapes) to check readability on the sheet itself?
- Do dressed characters need their own turnaround type, separate from creatures, once outfits are modelled?

## Related

- [Art direction](README.md) for the style, palette and pipeline
- [Modular kit](modular-kit.md) for grids, snapping and the sheet set per style
- [Architecture](architecture.md), [biomes](biomes.md) and [character customization](character-customization.md) for what the sheets must show
