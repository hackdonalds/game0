---
name: meshy
description: Create, retexture, rig, animate and download 3D models with Meshy for game0, at the lowest credit cost. Use whenever work involves Meshy, generating 3D models from concept art, character base bodies, attachable parts (horns, masks, shells), props, environment pieces, rigging or animation, or the art/models folder.
---

# Meshy for game0

Meshy's web app and API share **one credit pool** (Pro, 1,000 credits a month), but they price work differently. Generation is equal or cheaper on the API. Remesh, rigging, preset animations and downloads are **free on the web app** and charged on the API. Route every operation with the table below. The full evidence is in `docs/reports/Meshy pricing and usage.md`.

## Guardrails (always)

1. **State the cost before any paid call** and get the user's OK. `scripts/meshy.ts` dry-runs by default: run it without `--yes` first, show the user the printed cost, then rerun with `--yes`.
2. **Session budget: 250 credits.** The script refuses past the cap. Only pass `--over-budget` after the user approves more spend in chat.
3. **Pilot before batch.** Generate one item, check it, then do the rest of a set.
4. **Credit ledger.** The script appends every paid task to `art/models/credit-ledger.csv`. Web-app actions that cost credits must be added there by hand, with kind `web-<action>`. Free web actions are logged with 0.
5. **Free first.** If an operation is free on the web app, do it there with Claude in Chrome (see `references/web-recipes.md`). Use the API only when there is no free web path, or for scripted generation.

## Routing

| Operation | Where | Credits |
| --- | --- | --- |
| Concept image | `bun run art:image` (OpenRouter Sunburst), not Meshy | 0 Meshy |
| First generation, all asset types | **API** `bun run art:3d model`, mesh only | 5 Smart Topology / 20 Meshy 7.1 or 6 |
| Texture accepted geometry | **API**: rerun `model` with `--texture` (keeps the 7.1 texture path for characters), or `retexture` for variants | +10 |
| Polycount | Bake into generation (`--polycount`) | 0 |
| Standalone remesh | **Web** Remesh | 0 (API 5: never use) |
| Rigging + animations, humanoids | **Local** `bun run art:rig` (headless Blender + CC0 Quaternius clips, see `references/local-rig.md`) | 0 |
| Rigging, non-humanoids | **Web**: upload the API GLB, then Quadruped Dog or Smart Rig | 0 (API 5) |
| Extra clips the library lacks | **Web** Animate library (500+), on a web-rigged copy | 0 per clip (API 3) |
| Masked texture fixes, decals, seams | **Web** Texture Edit | unpublished: check the UI label first |
| Downloads and formats | **Web** download, or `target_formats` at generation | 0 (API convert 1: never use) |
| Godot import | Meshy's Godot bridge, once `apps/game` exists | 0 |

Use the web rig only when the local pipeline can't handle the body (not a humanoid in A-pose), and the API `rig` command only when the user asks for it (5 credits).

## Pipeline for a character people

The order is built around rigging: every step checks the body is rig-ready before the next one costs more.

1. **Concept sheet, rig-ready:** `bun run art:image` with the **rig-ready base-body template** in `references/settings.md` (front, side and back; plain underclothes; no props, capes, swappable features, tails or shells). Use the people's turnaround as `--ref` and `--aspect 21:9`, and save it as a kit sheet with `--out art/kit/peoples/<people>/base-turnaround`.
2. **Rig-ready review of the sheet (free):** read the image and check every point of the rig-ready checklist in `references/settings.md`: gap under each arm, gap between the legs, five spread fingers with the thumb apart, straight limbs, nothing bridging a gap. Regenerate the sheet on any miss; a concept reroll is far cheaper than a model.
3. **Views:** crop into thirds with `sips -c <h> <w> --cropOffset 0 <x>` into `art/kit/views/<people>-base-{front,side,back}.png`. That folder is ignored by git: crops are remade from the sheet when needed, never committed. **sips ignores an offset of 0 and crops from the centre**, so use x = 1 for the first crop. Read each crop, or compare with `md5 -q`, before sending it to Meshy. Wide figures often spill past even thirds: cut at the gaps between figures instead, keeping the full sheet height.
4. **Base model, textured in one pass:** `bun run art:3d model art/models/<people>/base <front> <side> <back> --model meshy-7.1 --texture --pose a-pose --polycount 20000` (30). Clean three-view base sheets have been accepted on the first try, and mesh-first would cost 20 + 30. Fall back to mesh-only passes (20 each) only if a base needs rerolls.
5. **Review** the `.front/.back/.left/.right.png` thumbnails.
6. **Rig check (free, seconds):** `bun run art:rig --check art/models/<people>/base.glb`. ✗ lines are blockers: arms touching the torso, no gap between the legs, arms not in an A-pose, feet not forward. Fix the concept (step 1) and regenerate rather than forcing. ! lines are warnings: closed fingers rig as a mitten (the four fingers are placed by proportion and bend as one), which is fine at game distance.
7. **Rig and animate locally:** `bun run art:rig art/models/<people>/base.glb <out>.glb` (about 15 s, free). It runs the check again and stops on a blocker (`--force` overrides). It writes the rigged, animated, compressed GLB plus `<out>.clips.json` with each clip's ground speed. Check the debug renders before using it (`references/local-rig.md`).
8. **Parts and props:** one isolated object per concept image on a plain background, saved as a kit sheet under `art/kit/<kind>/` (paintings and scenes go in `art/concept/`, see `art/README.md`). Run `model --model meshy-t2.5` (or `meshy-t2` for clean separated parts) with `--polycount 300-4000`, mesh only, then `--texture`.
Details per asset type, settings and prompt templates are in `references/settings.md`.

## Gotchas

- API results are deleted after 3 days. The script downloads immediately, so never rely on task URLs later.
- The API has no idempotency key. Never resend a create call after a timeout. Check `GET` on the task or the dashboard first.
- FAILED tasks are refunded. IN_PROGRESS tasks can't be cancelled.
- Queue at most 3 tasks at once across all agents. More returns 429 "NoMorePendingTasks"; nothing is created or charged, so wait and resend that one call.
- When parallel agents generate, give them one shared `MESHY_SESSION` and a `MESHY_SESSION_BUDGET` so the cap covers them all.
- Rigging (local, web or API) wants a bare humanoid: tails, shells, capes and props fused to the body break it. That's why base bodies are bare, in A-pose.
- Retexture rejects `meshy-7.1`. The script uses `meshy-7`.
- Smart Topology doesn't accept multi-image input.
- Terms: Meshy's Acceptable Use Policy prohibits "unauthorized automated or scripting processes". The user accepted driving the web app at human pace. Never run fast loops or bulk uploads through the browser.
