# Meshy.ai models, settings and input preparation for a stylized hand-painted MMORPG (Godot 4 + Three.js)

Research date: 31 October 2026. Main sources: the official Meshy API docs (docs.meshy.ai, including the API changelog through 30 Oct 2026), the Meshy web-app docs, the Meshy help center and Meshy tutorials/blog, plus a few independent 2026 reviews. I found no usable Reddit, Discord or YouTube threads: searches for r/meshyai, r/gamedev, r/godot and r/threejs returned nothing relevant. The "community" evidence below is thin and mostly independent reviews. Almost everything is from Aug to Oct 2026, so it is current. I mark anything older or suspect where it comes up.

Important doc conflicts to know up front:
- **The web-app docs lag the API.** The web-app Text to 3D page says Meshy 7.1 is not available for Text to 3D, only for Image to 3D. It also describes Smart Topology as "Meshy T1" with T2 at 100 to 15,000 faces. The API supports `meshy-7.1` on Text to 3D. It retired T1 on 30 Oct 2026 and added `meshy-t2.5` with up to 30,000 faces. For API work, trust the API pages.
- **Rigging and textures disagree.** The API rigging page says untextured meshes are not suitable. The web-app rigging guide says "The model doesn't need textures."

---

## 1. Model differences: meshy-7.1, meshy-6, meshy-6-lite, smart-topology meshy-t2 and meshy-t2.5

### Takeaway
For textured, faithful conversions of concept art (characters, hero pieces), use `meshy-7.1` (standard). For anything that has to ship at a fixed low triangle count (props, environment, attachments), use the Smart Topology models: `meshy-t2.5` gives sharper detail up to 30k faces, and `meshy-t2` gives cleaner topology with natively separated parts up to 15k. `meshy-6` is still worth having for one reason: it is the only model on which `remove_lighting` (and an emission map) does anything. That may matter for a deliberately "painted-light" look. `meshy-6-lite` is a 5-credit draft model.

### Cited Findings
**Status and lineup (October 2026)**
- Active 3D models: `meshy-7.1`, `meshy-6`, `meshy-6-lite` and `meshy-t2.5`. `meshy-7` was deprecated on 18 Sep 2026, with retirement "to be announced". `meshy-5` retired on 10 Oct 2026 and `meshy-4` on 20 Mar 2026. — [Meshy Deprecations](https://docs.meshy.ai/api/deprecations)
- `meshy-7.1` was added on 18 Sep 2026 with "same parameters and credit cost as `meshy-7`, higher geometry detail", and `latest` now resolves to it. — [API Changelog](https://docs.meshy.ai/api/changelog)
- Meshy T1 (`model_type: "lowpoly"`, `meshy-t1`) retired on 30 Oct 2026. Smart Topology `meshy-t2.5` replaces it. — [API Changelog](https://docs.meshy.ai/api/changelog)
- `meshy-t2.5` was added on 15 Oct 2026 as "the newest Smart Topology model, with sharper detail for game assets". It outputs triangles only, `target_polycount` runs 100 to 30,000 (default 15,000), and it is priced like `meshy-t2`. — [API Changelog](https://docs.meshy.ai/api/changelog)
- `meshy-t2` gives "cleaner topology and natively separated parts" with `target_polycount` from 100 to 15,000 (default 4,000). `meshy-t2.5` is the default Smart Topology model. With `smart-topology`, Meshy ignores `should_remesh` and `decimation_mode` and accepts only triangle topology. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- Retexture's newest model is `meshy-7`. Retexture rejects `meshy-7.1`. — [llms.txt](https://docs.meshy.ai/llms.txt)
- Meshy's own advice: pin `ai_model` to a specific model such as `meshy-7.1` if you need consistent output, because `latest` changes when a new model ships. — [Deprecations](https://docs.meshy.ai/api/deprecations)

**Quality and positioning**
- Meshy 7.1 targets geometric detail. Ultra 4K runs at 4096³, and raw meshes reach up to 80 million triangles before simplification. "Engravings, stitches, weaves and scales" are built into the mesh. On Meshy's own Detail Richness benchmark it ranks first (53.5% at 1024 render resolution vs Rodin 2.5 at 51.4% and Tripo 3.1 at 44.8%). This is a vendor benchmark. — [Meshy 7.1 launch blog](https://www.meshy.ai/blog/meshy-7-1-launch)
- Meshy 7.1 handles "organic characters with expression, anatomy, and skin folds" and "multi-part objects, where each part keeps its position and neighboring parts stay separate". — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)
- Smart Topology "generates meshes for game development, real-time rendering, and web 3D". Its benefits are native part segmentation, about 2 seconds per generation on T2, and poly-count control. "Cleaner topology deforms more predictably, so rigging and animation behave better." — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)
- Meshy's low-poly guidance: "Direct generation covers most real-time low-poly work, decimation stays the correct route for dense-first deliverables, and manual retopology earns its cost only where deformation or close-ups demand hand-placed edge flow." — [Meshy topic: generate or decimate (29 Sep 2026)](https://www.meshy.ai/topics/ai-low-poly-generate-or-decimate)
- Independent review (FrameSixty, Oct 2026): Meshy is "a pipeline accelerator, not a pipeline replacement". It "still fuses fine detail such as hair strands and window grids". Tripo 3.1 is faster (about 10 s vs about 60 s) and often gives cleaner hard-surface topology. FrameSixty suggests reserving Ultra 4K for assets that go into a retopology pass. — [FrameSixty review](https://framesixty.com/meshy-ai-3d-review/)
- An independent dev.to test of a Meshy image-to-3D knight (standard, unremeshed) found 2,230,028 triangles, 74 MB and 3 embedded textures, with "730,454 extra triangles into cape folds nobody orbits". — [dev.to review](https://dev.to/tessamori/meshy-ai-character-review-2026-3-textures-74-mb-one-blue-crest-301d)
- I found no independent hands-on review of T2 or T2.5 quality. Quality claims come from Meshy. — search result summary; see [glbgpt Meshy V7 review](https://www.glbgpt.com/hub/meshy-v7-review/) (did not test T2 directly)

**Speed (median, Sep 2026)**
- Image to 3D mesh only: 7.1 75 s, meshy-6 90 s, 6-lite 40 s, T2 4 s. With 2K textures: 7.1 2 min, 6 3 min, 6-lite 75 s, T2 60 s. PBR adds 30 to 60 s, and Ultra geometry adds up to 1 min. Retexture takes 55 s at 2K and 90 s at 4K. Rigging takes about 40 s. — [Task Lifecycle](https://docs.meshy.ai/api/task-lifecycle)

**Credits (API)**
- Text to 3D preview (mesh): 20 on 7.1 or 6, 5 on 6-lite, T2 or T2.5. Image to 3D: mesh only 20/20/5/5/5. With 2K or 4K textures: 30 on 7.1 or 6, 15 on 6-lite (2K only), T2 or T2.5. With 8K textures: 35 on 7.1 or 6, 20 on T2 or T2.5. Multi-Image to 3D is the same as Image to 3D but has no T2 or T2.5. The Ultra geometry surcharge (`2k`/`4k`) is +5, on 7.1 only. — [API Pricing](https://docs.meshy.ai/api/pricing)
- Text to 3D refine: 10 (2K/4K), 15 (8K). Retexture: 10 (2K/4K), 15 (8K). Remesh: 5. UV Unwrap: 5. Convert or Resize: 1. Rigging: 5. Animation: 3 per action, up to 10 per request. Text to Image: 3 to 9 depending on model. — [API Pricing](https://docs.meshy.ai/api/pricing)
- Note: the web-app Remesh guide says "Remesh costs no credits", while the API charges 5. — [Web-app Remesh guide](https://docs.meshy.ai/en/webapp/guides/3d-model/remesh) vs [API Pricing](https://docs.meshy.ai/api/pricing)

**Mesh-only plus separate texture**
- Text to 3D is always a two-step process: preview (mesh), then a refine task (texture, 10 credits) that inherits the preview's model unless overridden. — [Text to 3D API](https://docs.meshy.ai/api/text-to-3d)
- Retexture takes `input_task_id` or `model_url`. Style comes from `text_style_prompt`, `image_style_url`, or `multiview_image_urls` (1 to 4 views, first is front, requires an explicit `ai_model: "meshy-7"`). `enable_original_uv: true` reuses a Meshy model's optimized UV layout. — [Retexture API](https://docs.meshy.ai/api/retexture)
- "Texturing from an image might not work well when the image's shape differs a lot from the 3D model's geometry." — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)

### Inferences
- **Split vs single pass, by cost alone.** On 7.1, textured Image to 3D costs 30, while mesh-only (20) plus Retexture (10) also costs 30. The split saves credits only on geometry rerolls. With N geometry attempts, single-pass costs 30·N and split costs 20·N + 10. They tie at N = 1 and the split wins from N = 2. On T2 or T2.5 it is 15·N vs 5·N + 10, so the split wins as soon as you reroll once. **Default to mesh-only first for anything you expect to reroll** (characters, stylized creatures). Inspect the mesh, then texture the winner.
- **Split vs single pass, by quality.** Retexture's best model is `meshy-7`, not 7.1. A single-pass Image to 3D on 7.1 textures directly from the input image(s). For characters whose texture should match the concept art closely, single-pass textured generation (or Multi-Image with `texture_image_urls`) is probably more faithful than a later `image_style_url` retexture. I have not verified this; no source compares them.
- Separate retexture is clearly better when (a) you want several palette or faction variants of one mesh (10 credits each), (b) the mesh came from T2 or T2.5 and you want to drive the texture with a text style prompt, or (c) you edited or remeshed the mesh outside Meshy.
- **Ultra geometry probably works against a hand-painted look.** 7.1 Ultra puts small surface detail into the geometry ("engravings, stitches, weaves and scales"). A hand-painted look puts that detail in the texture on simple, chunky forms, and the micro-geometry is thrown away when you decimate to game budgets anyway. Use `geometry_resolution: "standard"` for all in-game assets and reserve `4k` for marketing.

### Gaps
- No independent side-by-side of T2 vs T2.5 vs 7.1-plus-remesh on stylized assets. Run a small in-house test (5 credits per T2/T2.5 attempt makes this cheap).
- No source compares Retexture (meshy-7) fidelity against single-pass 7.1 texturing for stylized concept art.

---

## 2. Settings: remesh/topology/polycount, geometry and texture resolution, PBR, remove_lighting, image_enhancement, pose_mode, symmetry

### Takeaway
Meshy's flags fall into three groups. Some are ignored on current models: `remove_lighting` on 7.1, `symmetry_mode` and `art_style` everywhere. Some go stale with the model: `pose_mode` and `image_enhancement`. Polycount is controlled two different ways. For stylized hand-painted assets: base color only (`enable_pbr: false`), 2K textures, `image_enhancement: false` for clean concept art, `pose_mode: "a-pose"` for anything you rig, and either Smart Topology `target_polycount` or `should_remesh: true` with an explicit `target_polycount`.

### Cited Findings
**Remesh and polycount**
- `should_remesh` defaults to true on meshy-6-lite and false on other models. "For the highest-quality 3D model, set it to `false`." `topology` is `quad` or `triangle`. `decimation_mode` 1 to 4 (ultra/high/medium/low) overrides `target_polycount`. `save_pre_remeshed_model` also keeps the dense GLB. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- `target_polycount` ranges: Remesh 100 to 300,000 (default 30,000), `meshy-t2` 100 to 15,000 (default 4,000), `meshy-t2.5` 100 to 30,000 (default 15,000). "The result can differ from the target." — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- Web-app Remesh guidance: quad gives "evenly spaced faces that are easier to edit, with less detail", while triangle "keeps more detail at a given face count and suits game engines". Small accessories can disappear because the "face budget is spread unevenly", so remesh complex models one part at a time. Remesh doesn't support T2 models or split parts. — [Web-app Remesh guide](https://docs.meshy.ai/en/webapp/guides/3d-model/remesh)
- Meshy's polygon budget table for PC or console: character 20k to 50k, prop 5k to 15k, environment piece 10k to 50k. Mobile AAA: character 10k to 20k, prop 2k to 5k, environment 5k to 15k. — [Web-app Game Assets guide](https://docs.meshy.ai/en/webapp/guides/use-cases/game-assets)
- UV Unwrap (5 credits) supports meshes of up to 40,000 faces (run Remesh first if larger). — [API Changelog](https://docs.meshy.ai/api/changelog)

**Geometry resolution**
- `standard`, `2k` (Ultra pass at 2048³) or `4k` (4096³). `2k` needs 7.1 (or deprecated 7). `4k` needs 7.1 and is not available on Multi-Image to 3D. +5 credits. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d); [API Changelog](https://docs.meshy.ai/api/changelog)
- In the web app, "Ultra 2K is selected by default" on paid non-Enterprise plans, so a 7.1 generation costs 25 unless you pick Standard. Resolution "affects geometry only, not textures". — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)

**Texture resolution and PBR**
- `texture_resolution` is `2k`, `4k` or `8k` (not 4k/8k on 6-lite). `enable_pbr` adds metallic, roughness and normal maps. Emission maps come only from `meshy-6` (not at 8k). — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- At 8K, PBR maps are generated at 4K. — [API Changelog (21 Jul 2026)](https://docs.meshy.ai/api/changelog)
- AI Texturing tradeoff: "Off gives the base color only." 4K and 8K files are large, so if you don't need high resolution, pick a lower one. — [Web-app AI Texturing guide](https://docs.meshy.ai/en/webapp/guides/3d-model/ai-texturing)
- Meshy's game-character guide nonetheless recommends PBR maps by default ("Texture the character with PBR maps"). That is aimed at PBR engines, not hand-painted looks. — [Web-app Game Assets guide](https://docs.meshy.ai/en/webapp/guides/use-cases/game-assets)

**remove_lighting**
- `remove_lighting` (default true) "takes effect only with `meshy-6`". `meshy-7.1` and `latest` accept and ignore it, and on Retexture it applies only with meshy-6 at 2K or 4K. At 8k, lighting is always removed. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d); [Retexture API](https://docs.meshy.ai/api/retexture); [Multi-Image to 3D API](https://docs.meshy.ai/api/multi-image-to-3d)
- The web-app texturing guide says Meshy 7 Flagship "removes baked lighting automatically". — [Web-app AI Texturing guide](https://docs.meshy.ai/en/webapp/guides/3d-model/ai-texturing)
- An independent reviewer concluded Meshy "has essentially solved the 'baked lighting' issue", with native PBR preserving a "slightly painterly, stylized aesthetic". — [Medium review (Illumination), 2026](https://medium.com/illumination/meshy-ai-3d-generator-review-2026-full-production-pipeline-tested-298b006b4a42) (via search summary; not fetched in full)

**image_enhancement**
- `image_enhancement` (default true): "`false` keeps the exact look of the input image, with no style processing." It works only on meshy-6 and 7.1/latest, and returns 400 on 6-lite or Smart Topology. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- Web app: it "redraw[s] your image for a cleaner, more complete model… helps most with uneven lighting or a busy background. Details can change, and generation takes longer." Off "keeps the original, which is best for high-quality inputs." — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)

**pose_mode and symmetry**
- `pose_mode` is `a-pose`, `t-pose` or `""`, and is available on Text, Image and Multi-Image to 3D. `symmetry_mode` is deprecated and "doesn't affect the output" (since 11 May 2026). `art_style` on Text to 3D is deprecated and ignored. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d); [Text to 3D API](https://docs.meshy.ai/api/text-to-3d); [API Changelog](https://docs.meshy.ai/api/changelog)
- Meshy's rigging tutorial: "T-pose works best for rigging; an A-pose gives more natural shoulder skinning." In the web app, Pose Control costs 0 credits but needs Pro or above. — [Meshy auto-rigging tutorial (22 Jul 2026)](https://www.meshy.ai/tutorials/character-auto-rigging-workflow)
- Because `symmetry_mode` is gone, Meshy's rigging checklist fixes asymmetry with "add 'symmetrical' to your prompt and regenerate". — [Meshy auto-rigging tutorial](https://www.meshy.ai/tutorials/character-auto-rigging-workflow)

**Other useful flags**
- `target_formats: ["glb"]` generates only the formats you list, which can shorten the task. `auto_size` with `origin_at: bottom` sets real-world height. `multi_view_thumbnails` returns front, right, back and left renders for automated QA. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- Generated assets are kept for at most 3 days for non-Enterprise customers. — [llms.txt](https://docs.meshy.ai/llms.txt)

### Inferences
- **PBR for hand-painted.** Use `enable_pbr: false`. A hand-painted look usually comes from albedo with painted shading under unlit, toon or simple lambert shading (Godot `unshaded` or a custom toon shader, Three.js `MeshBasicMaterial`/`MeshToonMaterial`). AI metallic, roughness and normal maps fight that look. They also add 30 to 60 s and two extra textures. If you want subtle normal detail, try it on one hero asset only. The project's "3 textures at about 10 MB each" are consistent with `enable_pbr` having been on, or with base color plus metallicRoughness plus normal. Check what `enable_pbr: false` actually embeds; I could not verify the exact texture count.
- **Painted-in light.** Meshy 7.x always strips lighting from base color. If the style wants painted highlights and shadows (classic hand-painted MMO look), the only API path to keep them is `meshy-6` with `remove_lighting: false`, where the concept art carries painted light. Test this; it is untested by any source I found. Otherwise, paint the lighting in during post (Blender or Substance) or with a shader (gradient ramps, AO bake).
- **Texture resolution.** 2K is enough for game assets. Hand-painted textures are low-frequency, so downscale to 1024 (characters, hero props) or 512 (props, rocks) and compress (KTX2/Basis for Three.js, VRAM-compressed for Godot). 8K is a waste outside marketing.
- **image_enhancement.** Set it to `false` when you feed clean, on-model concept art (white background, even light). Enhancement "redraws" the image and "details can change", which risks drifting off-style. Leave it `true` only for messy references, photos or busy backgrounds.
- **Remesh for characters.** Use `should_remesh: true`, `topology: "triangle"`, `target_polycount` 15k to 25k. This matches the project's observation that about 20k targets are honoured. Use `quad` only if you plan to hand-edit or sculpt in Blender. The rigging tutorial says quad remesh helps joints tear less, so quad at about 10k quads (about 20k tris) is a reasonable rig-quality test.

### Gaps
- No source documents exactly which glTF texture slots are embedded with `enable_pbr: false` vs `true`.
- No source tests `meshy-6` with `remove_lighting: false` on painted concept art.
- No measured data on whether image enhancement changes stylized art proportions or palette, only Meshy's "details can change" wording.

---

## 3. Inputs: multi-image vs single image, views, order, background, cropping, resolution; A-pose vs T-pose; rigging failure causes

### Takeaway
One clean, front-facing, orthographic-looking 1:1 image (≥1024 px, PNG, white or transparent background, subject filling 70 to 90% with a small margin, even flat light) fixes most rerolls. Add up to 3 extra views (side, back, ¾) when the back matters, as with characters, creatures and buildings. Put the front image first. For rigging, generate in A-pose with limbs clear of the body, open hands, no held items, and no tails, capes or shells fused to the body. Meshy's API rigger is humanoid-only, so tails and quadrupeds are a known failure area.

### Cited Findings
**Single image preparation**
- Checklist: at least 512 × 512 px, ideally 1024 × 1024 or higher. Sharp, no JPEG artifacts. Plain white or transparent background. Avoid reflective or gradient backgrounds (they "bleed into the model's texture"). Subject fills 70 to 90% of the frame. Front-facing or slightly angled. Avoid extreme top-down or bottom-up angles. Even diffused light ("shadows bake into the texture"). Opaque materials. PNG preferred. — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- "No part of the object should touch or extend beyond the image boundary." — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- For AI-generated references, add "white background, studio lighting, front view, product photography style" to the image prompt. — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- Proportions get distorted by "strong perspective distortion", so use a telephoto or near-orthographic view. Black patches come from shadows or dark areas. A cluttered multi-object scene makes "the AI merge the objects into one distorted mesh". — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)
- The API accepts JPG, JPEG, PNG and WebP up to 20 MB, as a URL or base64 data URI. — [Image to 3D API](https://docs.meshy.ai/api/image-to-3d)
- Use 1:1 aspect ratio for images intended for Image to 3D. For humanoids, use A-pose or T-pose. — [Meshy Help: Creating Images](https://help.meshy.ai/en/articles/12005614-creating-images) (via search summary)
- Meshy's Text to Image and Image to Image endpoints support `generate_multi_view: true` (a multi-angle image, can't be combined with `aspect_ratio`) and `remove_background: true` (transparent RGBA PNG). Their output chains into Image or Multi-Image to 3D via `input_task_id`. — [Image to Image API](https://docs.meshy.ai/api/image-to-image); [API Changelog](https://docs.meshy.ai/api/changelog); [Multi-Image to 3D API](https://docs.meshy.ai/api/multi-image-to-3d)

**Multi-view**
- 1 to 4 images. "With `meshy-7.1` or `latest`, Meshy uses the first image as the front view, and the order of the others doesn't matter." `texture_image_urls` (1 to 4) can guide texture independently of the geometry images. — [Multi-Image to 3D API](https://docs.meshy.ai/api/multi-image-to-3d)
- Ideal angles: front, side, back, optional ¾. "Keep all reference images consistent in style, lighting, and scale… Mixing… can… produce mismatched seams." — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- Multi-view ranks "Highest" for precision, consistency and back-side accuracy, but "limited" for batch production because each model needs its own set of views. — [Web-app: Choose a generation method](https://docs.meshy.ai/en/webapp/guides/choosing/generation-method)
- In the web app, Meshy can generate the missing views from your main image. — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)
- Multi-view reduces face and hand artifacts. "Use Multi-view Image to 3D when a single-image result produces flat faces, inaccurate proportions, or artifacts on the back or sides." — [Meshy Help: Fix Character Pose, Face, and Hand Issues](https://help.meshy.ai/en/articles/16102152-fix-character-pose-face-and-hand-issues-in-meshy)

**Pose and rigging**
- "Simply typing 'T-pose' into a Text to Model prompt is not a reliable way to control pose — generate a reference image first, then use Image to 3D with the pose toggle enabled." "Keep limbs separated and avoid overlapping arms/legs." — [Meshy Help: Fix Character Pose, Face, and Hand Issues](https://help.meshy.ai/en/articles/16102152-fix-character-pose-face-and-hand-issues-in-meshy)
- API rigging "works well only with standard humanoid (bipedal) characters that have a clearly defined limb and body structure". It is not suitable for untextured meshes, non-humanoids, or humanoids with unclear limb structure. Limits: at most 380,000 triangles, GLB up to 400 MB by URL, the face must point to +Z (glTF forward), and `height_meters` defaults to 1.7. Error 422 means pose estimation failed. — [Rigging API](https://docs.meshy.ai/api/rigging)
- The rigging `texture_image_url` parameter was deprecated on 23 Oct 2026. If you send it, the model loses its PBR maps. — [API Changelog](https://docs.meshy.ai/api/changelog)
- The web app offers Humanoid, Quadruped Dog and Smart Rig (Beta) for other creatures. "Smart Rig models can't use the animation library and download as GLB only." Facial bones and tail physics are not supported: "rig it by hand in a DCC tool". — [Web-app Rigging guide](https://docs.meshy.ai/en/webapp/guides/3d-model/rigging)
- After rigging, humanoids get walking and running animations and quadrupeds get walking. Download Settings offer a skeleton template (Mixamo by default). — [Web-app Rigging guide](https://docs.meshy.ai/en/webapp/guides/3d-model/rigging)
- Rig failure checklist: shoulders or hips collapse means the pose is wrong, so regenerate in A or T pose. One side breaks means asymmetric geometry, so add "symmetrical". Tearing at joints means bad topology, so remesh with quad. **"Props or clothing move as one block" means self-intersection: "a cape drags the spine, a sword generated in-hand deforms with the arm"**, so prompt "arms away from body, hands open, no held items" and attach props to bones after rigging. Floating or sunk feet mean bad grounding. Extreme proportions (a head three times the body) can still rig if markers sit on the real joints. — [Meshy auto-rigging tutorial](https://www.meshy.ai/tutorials/character-auto-rigging-workflow)
- "Limbs deform badly: … proportions are far from a standard body." — [Web-app Rigging guide](https://docs.meshy.ai/en/webapp/guides/3d-model/rigging)
- An independent review says "chunky cartoon proportions break the auto rig". — [Techraisal](https://www.techraisal.com/blog/meshy-ai-builds-a-game-ready-3d-character-in-60-seconds/) (via search summary)

### Inferences
- **A-pose vs T-pose.** Prefer A-pose for this game. Meshy's own guidance says A-pose gives more natural shoulder skinning, and MMO idle, run and attack loops spend most time with arms down. Use T-pose only if a model's arms fuse to the torso in A-pose (bulky shells, wide sleeves).
- **Animal-folk.** Treat each as a humanoid biped and generate it **without tail, wings or shell**. Generate those as separate parts (section 4), parent them to the Hips or Spine bone, and add your own tail bones in Blender or Godot. Long tails touching the legs will be weighted to the legs, the "move as one block" failure.
- **Robes and long skirts.** These hide the leg gap that pose estimation and binding need. Use a split or short robe on the base body and add the long robe as cloth or a separate skinned mesh later.
- **Hooves, digitigrade legs, big heads.** These are "far from a standard body". Expect bad limb deformation and plan manual marker or weight fixes, or a manual Blender rig for those races.
- **Orientation for `model_url`.** Make sure GLBs you re-upload after Blender edits face +Z, or rigging returns 422.

### Gaps
- No public data on rigging success rates for digitigrade or animal-headed humanoids.
- The API exposes no quadruped or Smart Rig mode; the rigging API docs only describe humanoid.

---

## 4. Per-asset-type recommendations (synthesis)

### Takeaway
Use 7.1 where faithfulness to concept art and silhouette matter most (characters, hero pieces). Use Smart Topology T2 or T2.5 where triangle budget and throughput matter (props, environment, attachments). Keep textures base-color-only at 2K and generate geometry at standard resolution.

### Cited Findings
(All parameters and credits come from [Image to 3D API](https://docs.meshy.ai/api/image-to-3d), [Text to 3D API](https://docs.meshy.ai/api/text-to-3d), [Multi-Image to 3D API](https://docs.meshy.ai/api/multi-image-to-3d), [Rigging API](https://docs.meshy.ai/api/rigging), [Retexture API](https://docs.meshy.ai/api/retexture) and [API Pricing](https://docs.meshy.ai/api/pricing). Budgets come from the [Web-app Game Assets guide](https://docs.meshy.ai/en/webapp/guides/use-cases/game-assets).)
- T2 produces "natively separated parts", so you can "select, retexture, or animate each part on its own". — [Web-app Image to 3D docs](https://docs.meshy.ai/en/webapp/image-to-3d)
- Remesh can make small accessories disappear on complex models, so remesh one part at a time. — [Web-app Remesh guide](https://docs.meshy.ai/en/webapp/guides/3d-model/remesh)
- Stylized or fantasy subjects produce more artifacts "on hands, faces, and thin features (weapons, accessories)". — [Meshy Help: Fix Character Pose, Face, and Hand Issues](https://help.meshy.ai/en/articles/16102152-fix-character-pose-face-and-hand-issues-in-meshy)
- Meshy fuses fine detail "such as hair strands and window grids". — [FrameSixty review](https://framesixty.com/meshy-ai-3d-review/)
- Auto Split (10 credits) splits Meshy 6 or 7 models into parts automatically, by named parts or by color. `keep_texture: true` keeps the texture (added 30 Oct 2026). — [API Changelog](https://docs.meshy.ai/api/changelog)
- Meshy Edit (web app, 16 Oct 2026, 20 credits) adds, removes or replaces a region. It works on high-poly Meshy 6 and 7.1 (not Ultra 4K, low-poly, uploaded or rigged models) and returns that region untextured. — [FrameSixty review](https://framesixty.com/meshy-ai-3d-review/)

### Inferences — recommended recipes (please validate with a 3 to 5 asset pilot per type)

| Asset | Endpoint and model | Key parameters | Polycount | Textures | Credits per accepted asset (typical) |
|---|---|---|---|---|---|
| **1. Rigged humanoid / animal-folk base body** | Image to 3D (or Multi-Image with front, side and back from the same concept sheet), `ai_model: "meshy-7.1"` pinned | `pose_mode: "a-pose"`, `image_enhancement: false` (clean art), `geometry_resolution: "standard"`, `should_remesh: true`, `topology: "triangle"` (or `quad` if hand-editing), `target_formats: ["glb"]`. Then Rigging with `input_task_id` and `height_meters` set per race, then Animation with `action_ids` (up to 10) | 15k to 25k tris (matches the observed 20k) | Geometry pass first with `should_texture: false` (20). Once accepted, texture via Retexture (`meshy-7`, `image_style_url` = concept, `enable_original_uv: true`, `enable_pbr: false`, 2k) or redo single-pass textured. Optionally try `meshy-6` with `remove_lighting: false` for painted light | 1 try: 30 (or 20 + 10) + 5 rig + 3 per animation. With 2 geometry rerolls: about 60 + 5 + 3n |
| **2. Modular attachments (horns, masks, shells, tails)** | Image to 3D, `model_type: "smart-topology"`, `ai_model: "meshy-t2"` (separated parts, cleaner) or `meshy-t2.5` if detail is lacking | One object per image, isolated on white, shown at the angle it attaches. Masks are front-facing; shells are shown from back and side via 7.1 Multi-Image if T2 misreads them | 300 to 3k tris (horns 300 to 800, masks 1 to 2k, shells 2 to 4k) | `should_texture: true` at 2k (15) or mesh (5) + Retexture (10) for faction variants | 5 to 15 each. Variants +10 each |
| **3. Handheld props and weapons** | Image to 3D, smart-topology `meshy-t2.5` | Weapon laid flat or upright, full length in frame, side or ¾ view. Prompt chunky proportions ("thick blade, oversized pommel") to avoid thin-part loss | 1k to 5k (Meshy table: prop 2k to 5k mobile AAA, 5k to 15k PC). For a stylized MMO, 1.5k to 4k | 2k base color only | 15 (single pass) or 5·N + 10 with rerolls |
| **4a. Rocks, cliffs, floating-island chunks** | Text to 3D or Image to 3D, smart-topology `meshy-t2.5` | Prompt "stylized hand-painted rock, chunky faceted planes, simple silhouette". Batch several via text (5 credits each) and keep the best | 500 to 6k | Retexture with one shared style image across the set for consistency | 5 to 15 |
| **4b. Trees** | `meshy-t2.5` (or 7.1 plus remesh if T2.5 gives lumps) | Prompt foliage as "large stylized leaf clumps/canopy blobs", not leaves. Expect fine branches to fuse; alpha-card foliage likely needs hand work | 2k to 8k | Base color 2k. Consider replacing foliage with alpha cards in Blender | 15 to 30 |
| **4c. Buildings, bridges** | Image to 3D `meshy-7.1` with `should_remesh: true` (better part separation and alignment). Multi-Image when the back or sides matter. T2 if you want separated parts (doors, roofs) | Exaggerate thickness: "thick chunky planks", "solid rope". Avoid window grids and lattice (they fuse). One building per image, no ground clutter | 5k to 20k (Meshy env table 5k to 15k mobile AAA) | 2k (4k for large landmarks), base color only | 30 to 35 |
| **5. Hero / marketing models** | Image to 3D or Multi-Image, `meshy-7.1` | `geometry_resolution: "4k"` (single image only) or `2k` (multi-image), `should_remesh: false` or `save_pre_remeshed_model: true`, `texture_resolution: "4k"`/`"8k"`, `enable_pbr: true` optional for offline renders | Dense, millions of tris possible. Decimate for any real-time use | 4k to 8k | 35 to 40 per try (30/35 + 5 Ultra) |

Further inferences:
- **Asset-set consistency.** Drive all textures of one biome or faction with the same style image (Retexture `image_style_url`) or the same texture prompt prefix. Meshy recommends its 3D Agent for "a set of assets that share one art style" ([Game Assets guide](https://docs.meshy.ai/en/webapp/guides/use-cases/game-assets)). In an API pipeline, the equivalent is a fixed style-reference image plus a fixed prompt prefix.
- **Scale.** The project sees GLBs normalized to about ±0.95 units. Either set `auto_size: true` (with `origin_at: "bottom"`), use the 1-credit Resize API, or rescale on import per asset class. Rigging uses `height_meters`, so pass the race's real height.
- **Web size.** The project's about 10 MB per texture is normal for 2K PNG maps. Turning off PBR drops two of the three maps. Then downscale and compress (KTX2 for Three.js, Godot VRAM compression), and run gltf-transform or Draco/meshopt on geometry after Meshy (note that Meshy rejects Draco-compressed GLBs over 100 MB as input).
- **Download immediately.** Outputs expire after 3 days.

### Gaps
- No source gives Meshy-specific success rates per asset type. The "credits per accepted asset" figures assume 1 to 2 tries and should be replaced with pilot data.
- No source covers how well T2 or T2.5 handles trees or foliage specifically.

---

## 5. Prompting: text-to-3D prompts, texture_prompt, negative prompts, failure modes and fixes

### Takeaway
Use Meshy's formula [Subject] + [Material/Texture] + [Art Style] + [Technical Constraints], most important words first, one object per prompt, at most 800 characters. Express exclusions as plain negative phrases inside the prompt; there is no separate negative-prompt field. Control pose with `pose_mode`, not text. Fix fused fingers, merged accessories and thin parts upstream: clear, large hands; separated limbs; props generated separately; exaggerated thickness.

### Cited Findings
- Formula and example: "A medieval knight's helmet with scratched iron surface in dark fantasy art style, low-poly, game-ready asset." "Put the most important details first, because the first words carry the most weight." — [Web-app Prompting best practices](https://docs.meshy.ai/en/webapp/guides/prompting)
- For stylized work: "Name the style, for example 'Pixar style', 'Studio Ghibli', or 'flat shading cel-shaded'. Describe the shape language… 'round', 'exaggerated proportions', or 'chibi'." For game assets: Smart Topology, "game-ready", "clean edges", "minimal geometry", and avoid long fine-detail descriptions. Do: "low-poly cartoon style, 5,000 faces". Don't: empty adjectives, or "stone and wood and metal and glass" (too many materials). — [Web-app Prompting best practices](https://docs.meshy.ai/en/webapp/guides/prompting)
- Negative prompts: "add a negative phrase to the prompt", e.g. "no background elements", "without floating particles", "no text or labels". — [Web-app Prompting best practices](https://docs.meshy.ai/en/webapp/guides/prompting); [Web-app Text to 3D](https://docs.meshy.ai/en/webapp/text-to-3d)
- "'Realistic' produces high detail. 'Stylized' or 'cartoon' yields cleaner topology." Floating fragments come from "the prompt describes several separate objects", so describe one subject per prompt. — [Web-app Text to 3D](https://docs.meshy.ai/en/webapp/text-to-3d)
- With an image input, prompts can specify style, describe unseen sides ("the back of the character has a cape") and clarify material. "Overly long prompts can dilute the influence of your reference image." — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- `prompt` and `texture_prompt` are each at most 800 characters. If both `texture_prompt` and `texture_image_url` are sent, `texture_prompt` wins. — [Text to 3D API](https://docs.meshy.ai/api/text-to-3d); [llms.txt](https://docs.meshy.ai/llms.txt)
- Texture prompts: add "material, era, wear level, and colors" if the style doesn't match. Visible seams come from poor UVs, so run Unwrap UV and texture again. — [Web-app AI Texturing guide](https://docs.meshy.ai/en/webapp/guides/3d-model/ai-texturing)
- Meshy claims Meshy 7 texturing "holds the art style of the input rather than converting everything to a photoreal look" for "anime, hand-drawn, flat color, line art". This is a vendor claim. — [Meshy AI Texture Generator page](https://www.meshy.ai/features/ai-texture-generator)
- Independent 7.1 review of hand-drawn input: soft brush edges and low-contrast neighbouring colours get blended "a few pixels across every boundary". Painted features did land on their sculpted bumps. — [3DPrinting.com Meshy 7.1 review (22 Sep 2026)](https://3dprinting.com/reviews/meshy-7-1-review/) (via search summary)
- Fused fingers are "more likely when hands are small, partially occluded, or blurry". Fix with large, unobstructed hands and "regenerating a few times, as results can vary". Stylized subjects show more artifacts on hands, faces and thin features. Fix localized defects in Blender, ZBrush or 3D Builder. — [Meshy Help: Fix Character Pose, Face, and Hand Issues](https://help.meshy.ai/en/articles/16102152-fix-character-pose-face-and-hand-issues-in-meshy)
- Thin features (hair strands, jewelry chains, intricate patterns) are hard from a single image. — [Meshy Help: Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy)
- Separation language for rig-ready characters: "arms away from body, hands open, no held items." — [Meshy auto-rigging tutorial](https://www.meshy.ai/tutorials/character-auto-rigging-workflow)
- Low-poly models sometimes come out "lumpy instead of faceted"; regenerate with Smart Topology. — [Meshy topic: generate or decimate](https://www.meshy.ai/topics/ai-low-poly-generate-or-decimate) (via search summary)

### Inferences — prompt templates for this project
- **Concept image prompt** (for Meshy Text to Image or any image model; then Image to 3D): `"[race] [class] character base body, full body, A-pose, arms slightly away from body, hands open with fingers spread, feet apart, symmetrical, stylized hand-painted fantasy MMO style, chunky readable proportions, flat even lighting, no cast shadows, front view, orthographic, centered, plain white background, no props, no cape, no tail"`. Use `remove_background: true` and 1:1, or `generate_multi_view: true` for multi-view.
- **Text-to-3D prop prompt:** `"stylized hand-painted wooden round shield with iron rim, chunky thick proportions, simple bold shapes, game-ready, clean edges, minimal geometry, single object, no background elements, no text"`.
- **Texture prompt / text_style_prompt:** `"hand-painted stylized texture, soft painted gradients, warm saturated palette, subtle brush strokes, painted ambient occlusion in crevices, no photographic detail, no noise, no text"`. Keep a fixed prefix across a biome or faction. Note: on 7.x the painted AO request may be partly cancelled by automatic lighting removal (untested).
- **Thin-part fixes:** exaggerate thickness in prompt and concept (horn bases, sword blades, bridge ropes, fingers). Generate held weapons, capes, tails and shells separately. Show hands large and open in the concept image.
- **Avoid trademarked game names** in prompts sent to a vendor. Meshy's own examples use "Studio Ghibli" and "Pixar style", so describe the look instead ("hand-painted MMO style, painterly"). This is a project-policy inference, not a Meshy rule.

### Gaps
- No official guidance on how strongly `texture_prompt` steers style relative to the input image on 7.1.
- No community-sourced prompt libraries for hand-painted MMO assets were found (no Reddit, Discord or YouTube material surfaced).

---

## 6. Community tips and independent reviews

### Takeaway
Independent community discussion of Meshy for stylized game pipelines is sparse in what is indexable (no Reddit, Discord or YouTube results surfaced). The independent reviews agree on four points. Meshy speeds up asset creation but does not replace artists. Raw meshes are heavy and need decimation or compression. Hands, faces and thin parts still need fixing. Rigging stylized proportions is fragile.

### Cited Findings
- "Pipeline accelerator, not a pipeline replacement". Fuses hair strands and window grids. Ultra 4K is best saved for assets going to retopology. A typical textured generation is about 20 to 30 credits. — [FrameSixty review (Oct 2026)](https://framesixty.com/meshy-ai-3d-review/)
- An unremeshed 7.x knight: 2.23M triangles, 74 MB, 3 textures. Detail is spent on unseen cape folds. Meshy kept colour and inlay detail better than a competitor but read darker and flatter on metal. — [dev.to review (2026)](https://dev.to/tessamori/meshy-ai-character-review-2026-3-textures-74-mb-one-blue-crest-301d)
- An itch.io user said the models "aren't perfect, but you can import them into Blender, make the necessary small adjustments". The thread also notes game jams that ban AI assets. — [itch.io forum post](https://itch.io/post/13367301/view-in-topic) (via search summary)
- Meshy's own job posting asks its community manager to post in 3D subreddits, so treat Reddit praise with caution. — [Meshy job posting](https://job-boards.greenhouse.io/meshy/jobs/4804996008) (via search summary)
- Meshy publishes an MCP server and agent skills for Claude Code and Cursor (`npx -y @meshy-ai/meshy-mcp-server`). — [llms.txt](https://docs.meshy.ai/llms.txt); [FrameSixty review](https://framesixty.com/meshy-ai-3d-review/)
- Older advice (possibly outdated): Meshy 6 Preview launched 16 Oct 2025. Pre-2026 guides that mention `art_style`, `symmetry_mode`, `ultra_mode`, `hd_texture`, `is_a_t_pose`, `meshy-4`/`meshy-5` or T1 "lowpoly" mode are outdated. Those parameters are now deprecated or ignored and those models are retired. — [Barchart press release](https://www.barchart.com/story/news/35500572/meshy-launches-meshy-6-preview-a-sculpting-level-ai-3d-modeling-platform); [API Changelog](https://docs.meshy.ai/api/changelog)

### Inferences
- A practical reroll-reduction loop for an API pipeline:
  1. Generate a cheap concept image (3 to 9 credits) and QA it.
  2. Run a mesh-only pass (5 on T2/T2.5, 20 on 7.1) with `multi_view_thumbnails: true` for automated or visual QA.
  3. Texture only the accepted geometry.
  4. Rig and animate.
  5. Post-process in Blender or gltf-transform.

  This front-loads cheap rejection.
- Budget for some manual Blender time on hands, joints and part separation for every rigged character. Every source, Meshy's help center included, assumes some manual cleanup.

### Gaps
- No Reddit, Discord or YouTube content was retrievable, so community consensus on stylized or hand-painted settings is unverified.
- No Godot- or Three.js-specific community posts about Meshy assets were found.
