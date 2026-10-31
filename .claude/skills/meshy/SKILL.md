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
| Rigging | **Web**: upload the API GLB, then Humanoid rig (verified free; Mixamo skeleton with fingers) | 0 (API 5) |
| Preset animations | **Web** Animate library (500+) | 0 per clip (API 3) |
| Masked texture fixes, decals, seams | **Web** Texture Edit | unpublished: check the UI label first |
| Downloads and formats | **Web** download, or `target_formats` at generation | 0 (API convert 1: never use) |
| Godot import | Meshy's Godot bridge, once `apps/game` exists | 0 |

Use the API `rig` command only when the web path fails or the user asks for it. It costs 5, but it includes walk and run clips.

## Pipeline for a character people

1. **Concept sheet:** `bun run art:image` with a front, side and back turnaround of the **base body**. The body wears plain underclothes, in A-pose, with no props, capes, swappable features, tails or shells. Use the people's turnaround as `--ref` and `--aspect 21:9`.
2. **Views:** crop into thirds with `sips -c <h> <w> --cropOffset 0 <x>` into `art/concept/views/<people>-base-{front,side,back}.png`. **sips ignores an offset of 0 and crops from the centre**, so use x = 1 for the first crop. Read each crop, or compare with `md5 -q`, before sending it to Meshy. Wide figures often spill past even thirds: cut at the gaps between figures instead, keeping the full sheet height.
3. **Base model, textured in one pass:** `bun run art:3d model art/models/<people>/base <front> <side> <back> --model meshy-7.1 --texture --pose a-pose --polycount 20000` (30). Clean three-view base sheets have been accepted on the first try, and mesh-first would cost 20 + 30. Fall back to mesh-only passes (20 each) only if a base needs rerolls.
4. **Review** the `.front/.back/.left/.right.png` thumbnails before rigging.
5. **Rig and animate on the web** (free; follow `references/web-recipes.md`), and download the GLB to `art/models/<people>/base-rigged.glb`.
6. **Parts and props:** one isolated object per concept image on a plain background. Run `model --model meshy-t2.5` (or `meshy-t2` for clean separated parts) with `--polycount 300-4000`, mesh only, then `--texture`.
7. **Attach:** add each part to `art/models/<people>/attachments.json` (bone, position, rotation, scale), and tune it in the Peoples Creator demo's Fit panel (`demos/creator`). For web use, add a demo whose `models` script runs `scripts/web-models.ts`.

Details per asset type, settings and prompt templates are in `references/settings.md`.

## Fitting parts

Fit in the creator demo's dev server (`demos/creator`, `bun run dev`) with the animation set to `none`, so the character is in its bind A-pose.

- By hand: open Fit (dev), then gizmo, and pick a part. Drag it with the gizmo (W move, E rotate, R scale with uniform scale enforced, Q local/world space). The sliders and `copy attachments.json` pick up the changes.
- By script: use `fitDebug.fitWorld(slot, [x, y, z], [rx, ry, rz], scale)` in the page console. The offset and rotation are in world axes (+Y up, +Z the character's front, -X its right). The helper converts them to bone-local values, because Mixamo bones are rotated.
- Check sizes first. Parts are normalised to about 1 unit on their longest side, so scale is roughly the real size in metres: masks 0.27–0.4, helmet-sized growths 0.35, mantles 0.9, staffs and spears 1.7–2.3.
- Grip: the hand bone sits at the wrist. Hanging tools need an offset down along their length so the fist holds the end of the handle.
- In the browser pane, wait about 1 s before each screenshot; otherwise the frame can be stale.
- Save `JSON.stringify(fitDebug.cfg)` to `art/models/<people>/attachments.json` before switching peoples, because switching reloads the file. Then check the fit in the Walking clip and in the people's signature clip.

## Gotchas

- API results are deleted after 3 days. The script downloads immediately, so never rely on task URLs later.
- The API has no idempotency key. Never resend a create call after a timeout. Check `GET` on the task or the dashboard first.
- FAILED tasks are refunded. IN_PROGRESS tasks can't be cancelled.
- Queue at most 3 tasks at once across all agents. More returns 429 "NoMorePendingTasks"; nothing is created or charged, so wait and resend that one call.
- When parallel agents generate, give them one shared `MESHY_SESSION` and a `MESHY_SESSION_BUDGET` so the cap covers them all.
- Meshy GLBs come normalised to about ±0.95 units, so parts always need a scale in `attachments.json`.
- API rigging is humanoid-only and fails on tails, shells, capes and props fused to the body. That's why base bodies are bare.
- Retexture rejects `meshy-7.1`. The script uses `meshy-7`.
- Smart Topology doesn't accept multi-image input.
- Terms: Meshy's Acceptable Use Policy prohibits "unauthorized automated or scripting processes". The user accepted driving the web app at human pace. Never run fast loops or bulk uploads through the browser.
