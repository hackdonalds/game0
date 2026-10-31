# Web app recipes (Claude in Chrome)

Use these for free web operations: rigging, preset animations, standalone remesh and downloads. The user is signed in to meshy.ai on Pro in their own Chrome and has approved free web actions.

## Rules

- Load the Chrome tools in one ToolSearch call: `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__tabs_close_mcp`.
- Work in a new tab and close it when done. Never touch the user's other tabs. Only one agent drives Chrome at a time, so rig sequentially.
- **Read the credit label before every click** that starts a task (shown as `<time> · <credits>`). If it isn't 0 and the action isn't already approved, stop and ask.
- Human pace: one action at a time, wait for each task to finish.
- Never click Buy, Upgrade, Top Up, plan or billing controls, the share button (the "+800" badge), or account settings.
- Log every web action in `art/models/credit-ledger.csv` with kind `web-<action>` and its credits (0 for free ones). Reconcile the ledger total against `bun run art:3d balance` afterwards (starting balance 1,900).

## Rig and animate an API-generated model (verified 2026-10-31, 0 credits)

API models don't appear in the web library, so upload them first.

1. Open https://www.meshy.ai/workspace?sidebar=animate, then click **Upload** (top right of the asset panel).
2. Upload: use `file_upload` on the dialog's file input with `art/models/<people>/base.glb` (GLB/FBX/OBJ/STL/glTF, max 100 MB). Keep "Keep Original Texture and UV" on. **Set License to Private**; it defaults to CC BY 4.0, which is public. Click Continue. The upload costs nothing.
3. Click **Rig** (top left, "Rig the model to animate"). Choose Humanoid (Quadruped Dog and Smart Rig also exist). Click Next.
4. Alignment step: set **Height** to the people's height (Veiled 2.0, Rootborn 1.9, Skerrin 1.8, Mossback 1.5, Rillfolk 1.5). Click Next.
5. Joint markers are placed automatically. Check chin, shoulders, elbows, wrists, groin, knees and ankles, then click **Confirm**. Rigging takes about 30 s and auto-adds Walking and Running.
   - Shells (Mossback) and tails (Rillfolk) rig fine as Humanoid. The tail follows the hips and has no bones of its own.
6. Add clips: type in "Search motion", press Enter, **hover** the card, then `find` "Add button on the preset motion card named '<name>'" and click that ref. Clicking coordinates without hovering doesn't register.
   - The preset named plain "Idle" fails with a 400 error. Use **"Idle 1"** (exported as `Idle_02`).
   - Matching clips exist, such as "Spear Walk" and "Heavy Hammer Swing".
   - Check the **Added** tab after clearing the search box; the search filters that tab too.
7. Click the green download button in the viewer toolbar. If the "Download Settings" popover doesn't open, click once more. Settings: Format glb, Skeleton template Mixamo, Rigged Character off, Animation **All Added**, Single file on. Click Download.
8. The file arrives in `~/Downloads/Meshy_AI_base_All_Animations*.glb` after 20–60 s; Chrome may hold it briefly as `.com.google.Chrome.*`. Move it to `art/models/<people>/base-rigged.glb` and delete any duplicates.

The web rig exports a full Mixamo skeleton with finger bones (`mixamorig:Head`, `mixamorig:RightHand`, `mixamorig:Spine2`...). GLTFLoader strips the colon, so names become `mixamorigHead`. Keep `attachments.json` on the Meshy names (`Head`, `RightHand`, `Spine02`); the creator demo maps them.

## Remesh (free, not yet used)

1. Open the asset's viewer, then Remesh.
2. Pick Triangle, Custom target (the polycount from `settings.md`), and confirm the label reads 0.
3. Download the GLB into the repo.

## Download in another format (free on Pro)

Open the asset, then Download, then pick the format. Never use the API Convert endpoint.
