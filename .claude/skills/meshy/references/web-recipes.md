# Web app recipes (Claude in Chrome)

Use these for free web operations: rigging, preset animations, standalone remesh and downloads. The user is signed in to meshy.ai on Pro in their own Chrome and has approved free web actions.

## Rules

- Load the Chrome tools in one ToolSearch call: `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__tabs_close_mcp`.
- Work in a new tab and close it when done. Never touch the user's other tabs.
- **Read the credit label before every click** that starts a task. The cost is shown next to the button as `<time> · <credits>`. If it isn't 0 and the action isn't already approved, stop and ask.
- Human pace: one action at a time, wait for each task to finish, no loops over many assets without checking in.
- Never click Buy, Upgrade, Subscribe, plan or billing controls, or account settings.
- Downloads land in `~/Downloads`. Move them into the repo with `mv`, under the paths in `art/models/README.md`.
- Log every web action in `art/models/credit-ledger.csv` with kind `web-<action>` and its credits (0 for free ones).

## Known UI (verified read-only, 2026-10-31)

- Workspace: https://www.meshy.ai/workspace. The balance shows in the sidebar.
- The Generate panel has tabs: Image to 3D (with a multi-view toggle), Text to 3D, Image. Model sub-modes are "High Detail", "Smart Topology" and "Relief". Options are Split (+10), Texture, Pose (A / T / Custom), Image Enhancement and License (Private).
- **Paid plans default Meshy 7.1 to Ultra 2K (+5).** Switch to Standard unless it's a hero render.
- Asset tiles show "x4", the free retries left for that task.
- Animate: https://www.meshy.ai/workspace?sidebar=animate. It shows "Select Model / Textured Model to Rig", and the library tabs are Text to Motion (paid), Video to Motion, AI Motions and Preset Motions (free on Pro).

## Recipes

These steps are unverified until first use. Correct them, and mark each "verified" with the date, the first time it runs.

### Rig and animate a model (free)

1. Get the model into the web library. Web-generated assets are already there. For an API-generated GLB, use the library's model upload; check whether an upload costs credits.
2. Open the Animate sidebar, then Select Model, then the asset. Choose rig type Humanoid (Quadruped or Smart Rig for non-humanoids). Mark the joints if asked. Confirm the label reads 0, then rig.
3. In Preset Motions, add the clips the user asked for (idle, walk, run, attack…). Choose the Mixamo-compatible skeleton if offered.
4. Download as GLB (all added clips), then move it to `art/models/<people>/base-rigged.glb`.

### Remesh (free)

1. Open the asset's viewer, then Remesh.
2. Pick Triangle, Custom target (the polycount from `settings.md`), and confirm the label reads 0.
3. Download the GLB into the repo.

### Download in another format (free on Pro)

Open the asset, then Download, then pick the format. Never use the API Convert endpoint.
