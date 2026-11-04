# Waystone: playable demo plan

A 5–10 minute browser demo on **Waystone**, the small rest isle off the Lantern Spoke (`concept/entries/isles/isle_waystone.md`). Published as `demos/waystone/` at `/demos/waystone/` and listed on the site like the other demos.

## Player experience

1. **Pick a people:** Galeborne, Anchorkin or Rootwarden. A turntable of the three models with one line each and their innate skill.
2. **Arrive** by skiff at the jetty at dusk. A storm surge is gathering over the isle; the Waystone has gone dark.
3. **Talk to Maren**, an Accord skiff warden at the campfire. Quest: *Relight the Waystone*.
4. **Gather 3 glimmer shards** scattered around the meadow (teaches movement, camera, interaction).
5. **Cross the Storm Ridge** to the Waystone, one route per people, each built on its innate skill:
   - Galeborne, **Glide:** jump from the cliff and glide across the broken ridge to the stone's ledge.
   - Anchorkin, **Anchor:** cross the rope bridge; storm gusts knock you off unless you hold Anchor while they pass.
   - Rootwarden, **Take Root:** the storm drains health on the ridge; stop and root under the old trees to recover.
6. **Defeat the Stormspawn** (a storm-twisted boar) guarding the stone: simple attack, dodge, health bars.
7. **Relight the Waystone:** set the shards, the storm breaks, the lane lights up across the cloud sea, end card.

Controls: WASD/mouse, Space jump, E interact, left click attack, Shift for the innate skill. On touch: left joystick, drag to look, and buttons for jump, attack, skill and interact. Quality scales down on phones.

## Model set: 15 new models, no reuse

Every model goes OpenAI image (gpt-image-2.5, `bun run art:image`) → my visual review → Meshy image-to-3D (`bun run art:3d`). Characters get a front/side/back sheet for multi-image to 3D in A-pose.

| # | Model | Meshy | Credits |
|---|---|---|---|
| 1–3 | Galeborne, Anchorkin, Rootwarden player characters | meshy-7.1 multi-image, 2K texture, A-pose | 90 |
| 4 | Maren, Accord skiff warden (NPC) | meshy-7.1 multi-image, 2K texture, A-pose | 30 |
| 5 | Stormspawn boar (cloud-wrapped, lightning eyes) | meshy-7.1, 2K texture | 30 |
| 6 | The Waystone (carved standing stone, glowing lanes) | meshy-7.1, 2K texture | 30 |
| 7 | Campfire camp (fire ring, logs, drying patched sail) | meshy-7.1, 2K texture | 30 |
| 8 | Jetty with tied-up skiff | meshy-7.1, 2K texture | 30 |
| 9 | Rope bridge segment (tiled for the ridge) | meshy-7.1, 2K texture | 30 |
| 10 | Old tree (hero tree, the rooting spot) | meshy-7.1, 2K texture | 30 |
| 11 | Isle underside (hanging rock and roots below the meadow) | meshy-7.1, 2K texture | 30 |
| 12–13 | Meadow tree, wind-bent pine | meshy-6-lite, 2K texture | 30 |
| 14 | Rock cluster | meshy-6-lite, 2K texture | 15 |
| 15 | Glimmer shard (collectible crystal) | meshy-6-lite, 2K texture | 15 |

New credits: about **420**, leaving about **180** of the 600 cap for re-rolls. OpenAI images: about 40 at high quality, roughly **$8** of the $15 cap.

Not models (made in code): the meadow terrain and paths, instanced grass and flowers, the cloud sea, sky and storm, water, fire and lightning effects, UI.

## Animation

The four humanoids are rigged **locally** (`bun run art:rig`, headless Blender, CC0 clip library; no Meshy rig credits): idle, walk, run, jump, fall, attack, hit, death, talk; plus a glide pose, an anchor brace and a kneel for Take Root. The Stormspawn is a cloud creature: whole-body motion (hover, charge, recoil) plus shader effects, no skeleton.

## How the work runs in parallel

| Lane | Runs as | Owns |
|---|---|---|
| A. Characters | its own session; one subagent per character for images | models 1–4: sheets → review → Meshy → local rig → clips |
| B. World models | its own session; subagents per model | models 5–15: images → review → Meshy → optimise (gltf-transform, Draco/KTX2) |
| C. Game code | its own session | `demos/waystone/src/game/*`: race select, controller, camera, touch input, skills, combat, quest, NPC dialogue, UI, audio hooks; capsule stand-ins until models land |
| D. Isle and look | its own session | `demos/waystone/src/world/*`: terrain, layout, sky, cloud sea, storm, lighting, quality tiers |
| E. Integration (this session) | here | asset manifest, wiring, playtests on desktop and phone sizes, perf, site listing, `bun run build` + handbook check, deploy |

Lanes A–D start together. C and D work against a shared `assets.json` manifest so models drop in without code changes.

## Review gates (done by me, no user input)

- Every concept image is checked against `concept/art-direction/` before any Meshy credit is spent.
- Every Meshy model gets a turntable render check; one re-roll allowed per model from the reserve.
- The finished demo must hit 60 fps on desktop and 30 fps at phone size, load under ~25 MB, and be played end to end with each of the three peoples.
