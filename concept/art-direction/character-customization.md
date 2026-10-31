# Character Customization

Players build distinct characters within each of the five [peoples](../world/peoples.md). The system uses one shared skeleton and layered, modular parts. Each people has a **signature layer** that gives the most creative freedom but can never be removed, so every character still reads as its people at a glance.

## Layers

| Layer | What players change | How it's built |
| --- | --- | --- |
| 1. Body | Height, build, shoulder width, belly, age | Blend shapes on one base body per people |
| 2. Head and face | Face shape, eyes, snout or beak, ears, brow, expression | 6–8 preset heads per people, with sliders on top |
| 3. Signature features | Race-defining traits (see below) | Swappable parts on race-specific slots |
| 4. Hair, fur, foliage | Hairstyle, beard, fur pattern, moss | Swappable meshes and texture masks |
| 5. Clothes and armor | Outfit pieces | One modular kit, with fitting variants per people |
| 6. Props | Trinkets, lanterns, shell shrines, horn rings | Attachment points on the skeleton |

**Colour** runs across all layers. Every texture carries primary, secondary and accent masks. Skin, fur and bark use a curated, muted palette per people so characters stay on-style; clothes use dyes.

## Signature features

| People | Customizable | Locked |
| --- | --- | --- |
| **Rootborn** | Wood type (oak, birch, cedar, ashen), bark pattern, growth (moss, lichen, flowers, mushrooms), beard foliage, crystal inlays | Bark skin, plant growth |
| **Veiled Ones** | The mask is the face: shape, engraving, material, eye-glow colour through the slits. Oath markings on the cloth, drape style, height | Mask always on, face never shown |
| **Mossbacks** | Shell shape and pattern, shell garden (plants and shrine type), scale pattern, beak shape | Shell, shell garden |
| **Skerrin** | Horn shape (ram, ibex, spiral, broken), horn rings and carvings, fur colour and pattern, beard, ear tags | Horns, hooves |
| **Rillfolk** | Fur colour and pattern, whisker style, facial markings, tail shape and ornaments | Tail, otter head |

## Design rules

1. **One skeleton with optional extras.** All peoples share one humanoid rig:
   - tail bones for Rillfolk;
   - a digitigrade leg variant (knees bending backward, like an animal's hind legs) for Skerrin, built on the same skeleton;
   - a shell attachment point for Mossbacks.

   Animations and gear are shared and adjusted to each body's proportions.
2. **Gear is fitted per body, not per piece.** Each armor piece needs fitting variants for the five bodies:
   - helmets: horn cutouts for Skerrin, fitting over masks for the Veiled;
   - capes and backpacks: shell-aware versions for Mossbacks;
   - trousers: a tail opening for Rillfolk.

   Hide rules are explicit, for example a helmet hides hair but never horns. This is the biggest cost driver, so the kit is designed for all five bodies from day one.
3. **Appearance is separate from stats.** Players save outfit looks (transmog), so their identity survives gear swaps. This matters in a classless game with partial-loot PvP.
4. **Customization ties into the economy and progression.**
   - Dyes are crafted items and act as a gold sink.
   - Mossback shell gardens grow, tied to farming.
   - Veiled oath markings unlock as players complete oaths.
   - Rootborn growth changes with the seasons.

   Characters become more distinct the longer people play.
5. **Signatures always read.** Sliders are clamped: a Skerrin can't lose its horns and a Rootborn can't become smooth-skinned. Open-world PvP needs peoples to be recognisable at a distance.

## Pipeline

- **Meshy:** static pieces such as props, horn and mask variants, shell gardens, and armor starting points.
- **Blender (3D artist):** rigged base bodies, blend shapes, and gear fitting variants. Meshy can't produce these.
- **Godot:** blend shapes, a Skeleton3D, meshes attached to bones (BoneAttachment3D), and shader-based colour masks.
- **Web demo candidate:** a small character creator for one people, such as Skerrin horns and fur or a Veiled mask.

## Open questions

- How many preset heads and slider ranges per people?
- Can appearance be changed after creation, and at what cost (a barber or mask-maker as a gold sink)?
- Gender and body variation per people: separate bodies, or one body with sliders?
- Which signature traits are tied to progression, and which are free from the start?
