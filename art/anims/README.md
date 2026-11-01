# Animation library

Every creature belongs to a **body family**. Each family has one canonical skeleton. Clips are retargeted onto that skeleton once, stored small, and played on any model rigged to the family. Raw source downloads never enter the repo.

## Families

| Family | Bodies | Clips come from |
| --- | --- | --- |
| `biped` | peoples, orcs, undead, giants | retargeted CC0/CC BY libraries (Quaternius UAL, KayKit, 100STYLE, CMU) |
| `quadruped` | horse, wolf, deer, bear, big cats, dinosaurs | retargeted CC0 animal packs (Quaternius) |
| `swimmer` | fish, sharks, eels, whales | generated in code (travelling spine wave) |
| `serpent` | snakes, worms, sea serpents | generated in code |
| `winged` | birds, bats | generated flaps and glides, hand-keyed take-off and landing |
| `dragon` | dragons, wyverns | `quadruped` skeleton plus the `winged` wing module, so it reuses both libraries |

Climbing is a clip set on `biped` or `quadruped`, not a family.

## Layout

```
art/anims/
  README.md                 this contract
  CREDITS.md                generated: credit lines for every source that needs one
  families/<family>.json    skeleton contract (see below)
  <family>/sources.json     sources used by the family (see below)
  <family>/catalog.json     every built clip (see below)
  <family>/clips/<set>.glb  built clips on the canonical skeleton, one GLB per set, meshopt-compressed
  <family>/reference.glb    the canonical body the clips were built on (for previews)
scripts/anims/              Bun/TypeScript CLI (fetch, build, credits)
scripts/rig/<family>/       Python run by headless Blender (rig, retarget or generate); biped lives in scripts/rig/
```

Each family owns only its own folder and `scripts/rig/<family>/`, so families can be built in parallel without touching each other's files. Shared code changes (`scripts/rig/lib.py`, `scripts/anims/*.ts`, `scripts/rig.ts`) stay small and backwards-compatible.

## Source cache

Raw downloads go to `~/.cache/game0/anims/<source-id>/` (override with `GAME0_ANIM_CACHE`), never the repo. `bun run anim:fetch <family>` fills the cache from `sources.json`: plain HTTP files, or single entries read out of a remote zip with HTTP range requests so huge archives are never downloaded whole. Sources that need a click-through (itch.io) are `"fetch": "manual"`: the person downloads them, and `anim:fetch` checks the checksum and copies them in.

## `families/<family>.json`

```json
{
  "family": "biped",
  "description": "who uses it",
  "rest": "rest pose the rigger expects and the axes (Blender: faces -Y, +Z up; glTF: faces +Z, +Y up)",
  "rig": "script that rigs a static model to this skeleton",
  "modules": ["optional: limb modules such as wing.L/wing.R, tail, fin"],
  "bones": [{ "name": "hips", "parent": "root", "deform": true }]
}
```

Bone names use `.L` / `.R` suffixes (three.js drops the dot: `hand.L` becomes `handL`). A bone list only grows: never rename or remove a bone once clips exist for it.

## `<family>/sources.json`

```json
[
  {
    "id": "kaykit-anims",
    "name": "KayKit Character Animations 1.1",
    "url": "https://kaylousberg.itch.io/kaykit-character-animations",
    "license": "CC0-1.0",
    "credit": null,
    "fetch": "manual | http | zip-range",
    "files": [{ "path": "inside the cache folder", "url": "for http / zip-range", "entry": "zip entry for zip-range", "sha256": "...", "size": 0 }]
  }
]
```

Only commercial-use licences: CC0, CC BY (with `credit` set), or explicitly free-for-any-use (CMU). Never non-commercial or research-only data, nor anything that forbids redistributing the built clips.

## `<family>/catalog.json`

```json
[
  {
    "id": "walk_casual",
    "name": "Casual Walk",
    "set": "locomotion",
    "tags": ["walk", "npc"],
    "variantOf": "walk",
    "loop": true,
    "speed": 0.79,
    "frames": 40,
    "fps": 30,
    "source": "quaternius-ual1",
    "sourceClip": "Walk_Loop",
    "license": "CC0-1.0"
  }
]
```

- `id` is the clip's name inside its set GLB and never changes once published.
- `set` groups clips into GLBs: `locomotion`, `idle`, `social`, `combat`, `ranged`, `magic`, `reaction`, `death`, `monster`, `climb`, `swim`, `fly`.
- `variantOf` links variations (Idle 1–5) so NPCs can pick one at random.
- `speed` is ground speed in m/s for the canonical body; characters scale it by their hip-height ratio.
- Generated clips use `"source": "generated"` and add `"generator": {...}` with the parameters.

## Commands

- `bun run anim:fetch <family>`: fill the source cache.
- `bun run anim:build <family> [--set <set>]`: retarget or generate clips onto the canonical skeleton, write `clips/<set>.glb` and `catalog.json`, then regenerate `CREDITS.md`.
- `bun run art:rig <in.glb> <out.glb> [--family biped] [--sets locomotion,combat] [--check]`: rig a model to its family and attach the chosen sets.

## Checks before a family counts as done

- A test creature rigs with `art:rig --check` passing.
- Every clip plays on it in the clip browser demo without popping, foot sliding beyond its `speed`, or stretched skin.
- `catalog.json` and `CREDITS.md` are complete and every source licence is recorded.
