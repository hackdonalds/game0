# Meshy.ai Web App Credit Costs for a Pro User (checked 2026-10-31)

Method: live inspection of the user's signed-in Chrome session (Pro plan, "Current plan" badge on pricing page; balance shown in workspace sidebar: **1,775 credits**), plus official help/docs pages read the same day. Strictly read-only: no Generate/Remesh/Rig/Animate/Download buttons were clicked. In the Model panel, form toggles (Texture, Split, Resolution, Smart Topology tab) were switched only to read the cost label next to the Generate button, then switched back to defaults. None of the pages showed a "last updated" date. The footer reads "© 2026 MESHY LLC".

## 1. Per-feature credit cost in the web app

### Takeaway
On the web app, model generation and texturing cost credits. Remesh, rigging, preset animations and downloads (Pro) are 0 credits. Text-to-motion, image generation, UV unwrap, split, retexture and print repair cost credits. The live UI label next to the Generate button is the final authority, and in places it differs from the docs tables.

### Live UI observations (workspace, https://www.meshy.ai/workspace, 2026-10-31)
The cost appears next to the Generate button in the left panel as "<time> · <credits>".

| Model panel setting (Image to 3D) | UI cost label |
|---|---|
| High Detail → "Meshy 7.1 - Flagship" ("Most detail, highest precision"), Resolution **Ultra 2K** (default), Texture off, Split off | "1 min · **25**" |
| Same, **Texture on** (Texture Resolution 2K / 4K / 8K "NEW"; 2K selected) | "2 min · **35**" |
| Resolution **Standard**, Texture off | "1 min · **20**" |
| Resolution **Standard**, Texture on (2K) | "2 min · **33**". This was read twice. It does not match the documented "+10", so treat it as an anomaly to re-verify |
| Resolution **Ultra 4K**, Texture off | "1 min · **25**" |
| Ultra 4K, **Split on**, Texture off | "1 min · **35**" (Split adds 10) |
| **Smart Topology** tab → "Meshy T2.5" ("Sharper detail for game assets"), Poly Count slider default 15000, Texture off | "10 sec · **5**" |
| Smart Topology T2.5, Texture on | "2 min · **15**" |
| Image tab → model "Nano Banana Pro", Number of images 4 (default) | "15 sec · **9 x 4 = 36**", i.e. 9 per image for this model |

Other UI observations:
- Model sub-modes: "High Detail", "Smart Topology", "Relief NEW". Model list: "Meshy 7.1 - Flagship", "Meshy 6 – High quality and stable structure", "Meshy 6 Lite – Fastest for quick iteration".
- Options: Split, Texture, Pose (A-Pose / T-Pose / Custom), Image Enhancement, License (CC BY 4.0 / Private, with Private selected for Pro). Multi-view image input is a toggle in the Image to 3D panel.
- Asset grid tiles show "**x4**", the remaining free retries per task for Pro.
- Animate panel (https://www.meshy.ai/workspace?sidebar=animate): "Select Model / Textured Model to Rig"; Library tabs "Text to Motion", "Video to Motion", "AI Motions", "Preset Motions" (several hundred named presets). No credit label is shown on preset motions until a rigged model is selected, so the per-clip cost was not seen in the UI. The docs say preset clips are free (see below).
- Not inspected in the UI because it would require opening an asset's viewer toolbar: remesh, retexture, UV unwrap, texture paint/inpaint, download format dialog, resize. Their costs below come from docs/help.

### Official cost tables

| Feature | Web-app cost | Source / exact wording | API price for comparison |
|---|---|---|---|
| Image to 3D, Meshy 7.1 | 20 (Standard), 25 (Ultra 2K/4K, the default on paid plans) | docs: "20 with Meshy 7.1 or Meshy 6, 25 with Ultra 2K or Ultra 4K, or 10 with Meshy 6 Lite… On paid plans other than Enterprise, Meshy 7.1 starts at Ultra 2K, so the default cost is 25" | 30 textured / 20 mesh-only |
| Text to 3D | 20 (Meshy 6), 10 (Meshy 6 Lite); "Meshy 7.1 isn't available in Text to 3D" | docs pricing | n/a |
| Meshy 6 Lite | 10 | docs + help | 5 |
| Model stage, help table | "25 credits(Meshy 7) / 20 credits (Meshy 6) / 10 credits (Meshy 6 Lite) / 20 credits (Relief) / 5 credit (Smart Topology T2.5) / 5 credits (Smart Topology T2)" | help 10000507 | |
| Smart Topology | 5 (T2 / T2.5); docs also list "20 with Meshy T1" | docs vs help (T1 no longer listed in help or UI) | 5 |
| Texture at generation (preview → refine/texture step) | +10 (2K/4K), 15 at 8K | docs "Texture or Split option at generation 10 each, Added to the generation cost"; help "Texture 10 credits (2k/4k) 15 credits (8K)" | refine 10 |
| Split at generation / Auto-split / Split into Parts | 10 | docs; help ("Auto-split 10 credits", Agent "Split into Parts 10 credits") | 10 |
| AI Texturing / Retexture | 10 (15 at 8K, Meshy 7 Flagship texture model) | docs "AI Texturing 10, or 15 at 8K, Per model"; help "Retexture 10 credits" | 10 |
| AI texture editing (paint/inpaint) | **Unknown.** Not listed in any cost table. The pricing page lists "AI texture editing" as a Pro feature | pricing page | n/a |
| Meshy-edit | 20 | help 10000507 | n/a |
| **Remesh / retopology / polycount change** | **0 (FREE)** | docs "Remesh 0 Per model"; remesh guide "Remesh costs no credits and takes about a minute". Targets: Fixed 3K/10K/30K/100K or Custom 100–300,000; Adaptive Low/Med/High/Ultra; Quad or Triangle. "On a free plan, only 10K is available" | 5 |
| Unwrap UV | 5 | help 10000507 | 5 |
| **Rigging** | **0 (FREE)** | docs "Rigging 0 Per model"; help (agent) "Smart-Rig · 0 credits" (per search snippet) | 5 |
| **Animation, preset clips** | **0 (FREE)** | docs "Animate 0 Per animation clip. Clips beyond the free set need a paid plan. Text to Motion costs credits."; pricing page: Pro "Unlimited animations", "Animation library Over 500" (Free: 20) | 3 / action |
| Text to Motion | 3 | help "Text to motion 3 credits" | n/a |
| Video to Motion | Unknown (tab exists in UI, no cost seen) | UI | n/a |
| **Download (GLB/FBX/OBJ/USDZ/BLEND etc.) / format conversion** | **0 (FREE), unlimited on Pro** | help FAQ: "For Pro plan and above, we offer unlimited downloads without consuming any credits"; pricing: "Unlimited 3D model downloads"; tutorial: "Downloads never consume credits" | convert 1 |
| Resize | Unknown in web app. Not listed; probably applied at download. Not verified | n/a | 1 |
| Text to Image | 3–9 (Agent); Nano Banana Pro shown as 9 per image in UI | help; UI | 3–9 |
| Image to Image | 3–9 (Image section) / 3–12 (Agent) | help | 3–12 |
| Multi-view image to 3D | Same as Image to 3D (multi-view is a toggle in the same panel); pricing lists Multi-view as a paid-plan feature | UI, pricing | 30 |
| Multi-view image generation | Unknown. A "Multi-view" toggle exists in the Image panel; its added cost was not read | UI | n/a |
| Printability repair / AI Auto-Repair | 10 | help; tutorial | n/a |
| Multi-Color 3D Print AI Optimize | 16 | help | n/a |
| Agent: Image to 3D textured / untextured | 30 / 20 (Smart Topology 15 / 5) | help (Agent section) | |
| Agent: Web Search | 2 | help | |
| Image to Video / Text to Video | 20–330 / 80–330 | help | |
| **Re-generations (free retries)** | **Pro: 4 free retries per task (web app)**; UI shows "x4" on tiles. After that, regenerations cost the full price | pricing "4 free retries per task (web app)"; tutorial "your exact count is printed right on the regenerate control (x4 on Pro)" | none |
| Failed / queued-cancelled tasks | refunded | help FAQ "we will refund the corresponding credits if the task fails"; docs "refunds credits for canceled tasks"; tutorial says tasks cancelled after processing starts are not refunded (conflict) | |

Sources: [Help: How Many Credits Does Each Generation Task Cost](https://help.meshy.ai/en/articles/10000507-how-many-credits-does-each-generation-task-cost) · [Docs: Pricing and credits (webapp)](https://docs.meshy.ai/en/webapp/pricing) · [Docs: Remesh](https://docs.meshy.ai/en/webapp/guides/3d-model/remesh) · [Meshy credits guide tutorial](https://www.meshy.ai/tutorials/meshy-credits-guide) · [Pricing](https://www.meshy.ai/pricing) · live workspace https://www.meshy.ai/workspace

### Inferences
- Remesh (API 5), rigging (API 5), preset animations (API 3/action) and download/convert (API 1) are **free on the web app but charged on the API**. The tutorial's claim that "equivalent tasks cost the same" in API and web app is contradicted by Meshy's own docs table.
- Generation on the web is cheaper or equal to the API: Meshy 7.1 mesh-only is 20–25 on web (API 20), and textured at Ultra 2K + 2K texture is 35 on web (API 30). Since the web default Ultra 2K costs 5 more than Standard, the web can actually be *more* expensive than the API for textured 7.1 output. Meshy 6 Lite is 10 on web vs 5 on API.
- Cheapest game-asset path on web: Smart Topology T2.5 at 5 credits mesh-only / 15 textured, then free rig, free preset animations, free download.

### Gaps
- No UI-verified cost for retexture, UV unwrap, texture paint/inpaint, Meshy-edit, Video to Motion, multi-view image generation or resize. These need an open asset viewer, which I did not inspect.
- Why Standard + Texture shows 33 rather than 30 is unexplained.
- The pricing page says "Unlimited AI image generation" for Pro, but the UI charges 9 credits per image for Nano Banana Pro. Whether some image models are free on Pro is unverified.
- Docs list Smart Topology T1 at 20. Help and UI show only T2/T2.5 at 5.

## 2. What Pro includes (pricing page, https://www.meshy.ai/pricing, 2026-10-31)

### Takeaway
Pro (€19/mo billed yearly, €228/yr; €19 monthly) gives 1,000 monthly credits, 10 concurrent tasks, high queue priority, 4 free retries per task, unlimited downloads/animations/image generation, and a private license.

### Cited Findings ([Pricing](https://www.meshy.ai/pricing))
- "1,000 monthly credits", "up to 100 assets" (Assets generation "Up to 100 / month").
- "10 concurrent tasks"; "High queue priority"; "60% faster generation" (Free: 1 concurrent, Low priority; Premium 30/Higher; Ultra 100/Highest).
- "4 free retries per task (web app)".
- "Unlimited 3D model downloads", "Unlimited AI image generation", "Unlimited animations", "Animation library Over 500" (Free 20), "Full & Advanced generation tools", "DCC integration and plugins", "API & MCP", "World's First 3D Agent".
- License: "Commercial-ready private license" / "Private & Customer owned" (Free: CC BY 4.0). The UI License toggle offers CC BY 4.0 / Private.
- API asset retention "3 days" for Pro; API "Requests per second 20".
- "40% OFF on Extra Credit Packs".
- Features ticked for Pro but not Free: Multi-view Image to 3D, Text to Image, Remesh, AI texture editing.
- Free allowances ([tutorial](https://www.meshy.ai/tutorials/meshy-credits-guide)): daily login rewards of up to 5 days per 30-day cycle (30, 30, 50, 50, 100 = 260 permanent credits); Pro onboarding checklist "6-task list worth 300 (50 each)"; Discord link 100 once; loyalty on Pro Monthly (500 at first renewal; yearly plans excluded).
- Monthly credits do not roll over; paid plans reset on the subscription date; permanent credits never expire and are spent last ([tutorial](https://www.meshy.ai/tutorials/meshy-credits-guide)). Docs say "Monthly credits reset at 00:00 UTC on the first day of each month" ([docs](https://docs.meshy.ai/en/webapp/pricing)). This applies to Free; there is a conflict for paid plans.

### Gaps
- The exact download format list for Pro was not read; the pricing FAQ "What 3D file formats do you support?" is collapsed and was not expanded.
- No page states a free *daily* generation allowance for Pro beyond retries and login rewards. Creative Lab free images/day apply only to Premium and Ultra.

## 3. Web-free vs API-charged features

### Takeaway
Yes. Remesh, rigging, preset animation clips and downloads/format conversion cost 0 on the web app but 5 / 5 / 3 per action / 1 on the API.

### Cited Findings
- Web: "Remesh 0", "Rigging 0", "Animate 0 Per animation clip" — [docs webapp pricing](https://docs.meshy.ai/en/webapp/pricing). Downloads free and unlimited on Pro — [help 10000507](https://help.meshy.ai/en/articles/10000507-how-many-credits-does-each-generation-task-cost).
- API: Remesh 5, Auto-Rigging 5, Animation 3, UV Unwrap 5 — [help API costs](https://help.meshy.ai/en/articles/16815622-how-many-credits-does-each-meshy-api-task-cost) (seen via search snippet only) / [API pricing](https://docs.meshy.ai/en/api/pricing).
- UV unwrap (5), retexture (10), auto-split (10) and text-to-image (3–9) are priced the same on the web and the API.

### Gaps
- The API help article was seen only as a search snippet and not opened.
