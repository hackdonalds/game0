# Character Customization

Players build distinct characters within each of the [peoples](../world/peoples.md). The system uses one shared skeleton and layered, modular parts. Each people has a **signature layer** that gives the most creative freedom but can never be removed, so every character still reads as its people at a glance.

## Layers

| Layer | What players change | How it's built |
| --- | --- | --- |
| 1. Body | Height, build, shoulder width, belly, age | Blend shapes on one base body per people |
| 2. Head and face | Face shape, eyes, nose, ears, brow, expression | 6–8 preset heads per people, with sliders on top |
| 3. Signature features | Race-defining traits (see below) | Swappable parts on race-specific slots |
| 4. Hair, feathers, foliage | Hairstyle, beard, crest, moss | Swappable meshes and texture masks |
| 5. Clothes and armor | Outfit pieces | One modular kit, with fitting variants per people |
| 6. Props | Trinkets, lanterns, feather charms, chain links | Attachment points on the skeleton |

**Colour** runs across all layers. Every texture carries primary, secondary and accent masks. Skin, feathers, stone and bark use a curated, muted palette per people so characters stay on-style; clothes use dyes.

## Signature features

| People | Customizable | Locked |
| --- | --- | --- |
| **Galeborne** | Feather colour and pattern, crest shape, mantle length, skin tone (sky-pale to dusk), eye colour, face markings | Feathered mantle |
| **Anchorkin** | Stone type (slate, basalt, sandstone, marble), crystal vein colour, carved marks, build, beard of stone fibres | Stone skin, great weight |
| **Rootwardens** | Wood type (oak, birch, cedar, ashen), bark pattern, growth (moss, lichen, flowers, mushrooms), beard foliage, crystal inlays | Bark skin, plant growth |

## Design rules

1. **One skeleton with optional extras.** All peoples share one humanoid rig, with mantle bones on the arms for the Galeborne. Animations and gear are shared and adjusted to each body's proportions: tall and light, huge and heavy, broad and stocky.
2. **Gear is fitted per body, not per piece.** Each armor piece needs fitting variants for the three bodies:
   - chest pieces and capes: mantle-aware versions for the Galeborne, which leave the feathers free to spread;
   - everything: larger fits for the Anchorkin.

   Hide rules are explicit, for example a cape hides on a Galeborne while they glide. This is the biggest cost driver, so the kit is designed for every body from day one, and each new people adds one fitting variant.
3. **Appearance is separate from stats.** Players save outfit looks (transmog), so their identity survives gear swaps. This matters in a classless game with partial-loot PvP.
4. **Customization ties into the economy and progression.**
   - Dyes are crafted items and act as a gold sink.
   - Anchorkin carved marks are added for deeds and kept posts.
   - Galeborne mantles grow longer as Glide rises.
   - Rootwarden growth changes with the seasons.

   Characters become more distinct the longer people play.
5. **Signatures always read.** Sliders are clamped: a Galeborne can't lose its mantle and a Rootwarden can't become smooth-skinned. Open-world PvP needs peoples to be recognisable at a distance.

## Pipeline

- **Meshy:** static pieces such as props, crests, growths, carved marks, and armor starting points.
- **Blender (3D artist):** rigged base bodies, blend shapes, and gear fitting variants. Meshy can't produce these.
- **Godot:** blend shapes, a Skeleton3D, meshes attached to bones (BoneAttachment3D), and shader-based colour masks.
- **Web demo candidate:** a small character creator for one people, such as Galeborne feathers and crest or Rootwarden growth.

## Open questions

- How many preset heads and slider ranges per people?
- Can appearance be changed after creation, and at what cost (a barber or mask-maker as a gold sink)?
- Gender and body variation per people: separate bodies, or one body with sliders?
- Which signature traits are tied to progression, and which are free from the start?
