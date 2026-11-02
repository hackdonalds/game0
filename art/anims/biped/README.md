# Biped clip library

188 clips in 9 sets (`clips/<set>.glb`, 7 MB), built on the canonical body in `reference.glb` (the Rootwarden base). Browse them with `bun run dev:demo anim-library`.

## Rebuild or add a clip

1. Add a row to `recipes.json` (format in `../README.md`). For a new source file, add it to `sources.json` too.
2. `bun run anim:fetch biped` (fills `~/.cache/game0/anims`; Quaternius and KayKit are manual itch.io downloads, the rest download themselves).
3. `bun run anim:build biped` (about 5 minutes) rewrites `clips/`, `catalog.json` and `../CREDITS.md`.
4. Re-rig characters with `bun run art:rig` to pick up the new clips.

Pick CMU takes by watching them, not by their description: `111_37` is labelled "Wave" but nobody waves in it.

## Sources

| Source | Licence | Used for |
| --- | --- | --- |
| Quaternius Universal Animation Library 1 and 2 (Standard) | CC0 | core locomotion, jumps, swords, spells, sitting, zombies |
| KayKit Character Animations 1.1 (free) | CC0 | melee, blocks, dodges, bow, magic, sitting, lying, skeletons |
| 100STYLE (Ian Mason) | CC BY 4.0, credit in `../CREDITS.md` | walk styles: elderly, limp, drunk, strut, proud, penguin, zombie, heavyset, crouched, akimbo… |
| CMU motion capture | free for any use, files not for sale | waves, bows, shrugs, drinking, conversation, falls, getting up, Frankenstein walk |

## Gaps against the wished-for list

Not in the free sources, or only approximated (`note` in the catalog says which):

- **Not clips at all:** Run to Walk Transition (crossfade run into walk), Walk/Run Turn and Sword and Shield Alert Turn (rotate the character while the clip plays; `run_turn_left/right` exist as one-shots), Dodge and Counter (play `roll_dodge_*` then `counterstrike`).
- **Missing:** Scheming Hand Rub, Confused Scratch, Victory, Magic Genie, Zombie Scream, Draw and Shoot from Back.
- **Stand-ins:** Walking Woman (a KayKit walk), Finger Wag No (head shake), Kneel on One Knee and Stand (kneeling loop), Angry Ground Stomp (100STYLE angry walk), Charged Ground Slam (same motion as Heavy Hammer Swing), Hit Reaction to Waist (chest hit), Slap Reaction (mirrored hit).
- **To check by eye:** Call Gesture (`13_26`) and Crawl and Look Back (`111_03`) are whole CMU takes that may need trimming.
- **Hands:** clips carry finger motion (Quaternius), but `art:rig` doesn't play it yet; hands stay open.
- **Props:** chair and floor sits play without furniture, so place a chair under them in game.
- **Speeds:** KayKit loops have no root motion, so their speeds are estimated from the planted foot (`walk_3`, `walk_backward` look high). Run Fast 4 is a mocap jog at 1.4 m/s.

The missing ones need hand-keying in Blender (on `reference.glb`, saved as a recipe source) or a new free source.
