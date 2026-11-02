# Character Customization

Players build distinct characters within each of the [peoples](../world/peoples.md). The system uses one shared skeleton and layered, modular parts. Each people has a **signature layer** that gives the most creative freedom but can never be removed, so every character still reads as its people at a glance.

## Layers

| Layer | What players change | How it's built |
| --- | --- | --- |
| 1. Body | Height, build, shoulder width, belly, age, limb length, hands, feet | Bone sliders and blend shapes on one shared base body |
| 2. Head and face | Face shape, eyes, nose, mouth, ears, brow, expression | Face sliders on the shared base, ARKit 52 expressions |
| 3. Signature features | Race-defining traits (see below) | Swappable parts on race-specific slots |
| 4. Hair, feathers, foliage | Hairstyle, beard, crest, moss | Swappable meshes and texture masks |
| 5. Clothes and armor | Outfit pieces in four layers: under, garment, armour, cloak | One kit, fitted to every people and slider by script |
| 6. Props | Trinkets, lanterns, feather charms, chain links | Attachment points on the skeleton |

**Colour** runs across all layers. Every texture carries primary, secondary and accent masks. Skin, feathers, stone and bark use a curated, muted palette per people so characters stay on-style; clothes use dyes.

## Signature features

Each people's signature layer, what players can change and what is locked, is written on its people entry in [`entries/peoples/`](../entries/peoples/) (the `signature` field), for example the [Anchorkin](../entries/peoples/anchorkin.md) brow Ledger line and shoulder oath-marks.

## Design rules

1. **One skeleton and one base mesh per body family.** All peoples share the humanoid family: one skeleton (Godot humanoid bone names, with optional mantle, tail and ear chains) and one base mesh (MakeHuman's CC0 base). Each people is a signature shape on that base, plus its own joint positions. Every bone points straight up at rest, so one animation library plays on every people, tall and light or huge and heavy.
2. **Gear is made once and fitted by script.** A piece is modelled once on the base body. The fitting step copies skin weights from the body and bakes one shape key for every body slider and every people, so it follows them all. Pieces declare which body regions they cover (the body hides those) and which other slots they hide (a cape hides on a Galeborne while they glide). A per-people variant is only needed where a signature breaks the shared fit, such as the Galeborne mantle.
3. **Appearance is separate from stats.** Players save outfit looks (transmog), so their identity survives gear swaps. This matters in a classless game with partial-loot PvP.
4. **Customization ties into the economy and progression.**
   - Dyes are crafted items and act as a gold sink.
   - Anchorkin oath-marks are added as a character keeps posts and swears vows (see [Anchorkin](../entries/peoples/anchorkin.md)); the brow Ledger line is set at creation and doesn't change.
   - Galeborne mantles grow longer as Glide rises.
   - Rootwarden growth changes with the seasons.

   Characters become more distinct the longer people play.
5. **Signatures always read.** Sliders are clamped: a Galeborne can't lose its mantle and a Rootwarden can't become smooth-skinned. Open-world PvP needs peoples to be recognisable at a distance.

## Pipeline

The research behind the choices is in `docs/reports/AI 3D game asset pipeline.md`.

- **Meshy:** shapes and paint for bodies, gear, parts, props and environment pieces (the `meshy` skill).
- **Engines:** live sliders (bone offsets and shape key pairs), body regions hidden under gear, dye shaders with a toon ramp, ARKit 52 expressions, and spring bones for mantles, tails, ears and capes.

## Open questions

- How many preset heads and slider ranges per people?
- Can appearance be changed after creation, and at what cost (a barber or mask-maker as a gold sink)?
- Gender and body variation per people: one base with sliders, or a second base per family?
- Which signature traits are tied to progression, and which are free from the start?
