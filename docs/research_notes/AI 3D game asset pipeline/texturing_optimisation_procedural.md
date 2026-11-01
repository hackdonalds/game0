# Texturing, Colour/Dye Masks, Optimisation/LOD and Procedural Generation for a Godot 4 + three.js (glTF) Stylized Pipeline (as of Nov 2026)

Scope: the texturing, recolour, optimisation and procedural stages of an asset pipeline. Constraints: Apple Silicon Mac only (no CUDA), mostly free/local, painterly style (sky islands, sailing ships, characters, creatures). Research budget was about 16 web searches; no full-page fetches were available, so everything below comes from search-result summaries of the cited pages. Items marked "unverified" or listed under Gaps should be checked before they go into the skill.

## AI texturing tools (cloud and local), Mac compatibility and cost

### Takeaway
On Apple Silicon, the strongest local PBR texturing option is a community MLX port of Hunyuan3D-Paint 2.1. It takes about 9 min per asset on an M2 Pro and outputs 4096² albedo plus metallic-roughness. Meshy Retexture is the cheap cloud fallback at 10 credits per call. Most of the Blender/ComfyUI texturing add-ons (StableGen) and the research methods (TEXTure, Text2Tex, Paint3D, SyncMVD, MV-Adapter) assume NVIDIA/CUDA.

### Cited Findings
**Hunyuan3D-Paint 2.1 (Tencent, open weights)**
- It is a PBR texture model for existing meshes, built on RomanTex and MaterialMVP. Settings go from 6 to 12 views at 512 or 768 resolution. Upstream recommends at least 21 GB VRAM for 6 views at 512 and builds CUDA pieces (custom_rasterizer, DifferentiableRenderer) — [Tencent hy3dpaint](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/tree/main/hy3dpaint); [Hunyuan3D-2.1 repo](https://github.com/tencent-hunyuan/hunyuan3d-2.1)
- **dgrauet/Hunyuan3D-2.1-mlx**: the PBR texture stage is fully ported to Apple MLX (UNet matches PyTorch within 1.17e-5). It outputs textured.glb with 4096² albedo plus metallic-roughness baked to the mesh UVs, in about 9 min for 6 views at 512 px on an M2 Pro. The UV rasterizer is tiled to stay within Metal command-buffer limits — [Hunyuan3D-2.1-mlx](https://github.com/dgrauet/Hunyuan3D-2.1-mlx)
- **VladimirTalyzin/hunyuan3d-2.1-mac-rocm**: PyTorch on MPS. PBR texturing is verified end to end, but only at 256 px, and texturing is "markedly slower" on Mac. A related fork fixed a `torch.isin` call in MeshRender.back_project that on MPS asked Metal for a single 111 GB buffer — [mac-rocm fork](https://github.com/VladimirTalyzin/hunyuan3d-2.1-mac-rocm); [intel fork](https://github.com/thehunterofshadows/hunyuan3d-2.1-intel)
- Weights are about 15 GB for shape and about 6.5 GB for paint — [CPU3D](https://cpu3d.com/en/ai3d/hunyuan3d-mac/)
- Brainkeys/Hunyuan3D-2.1-mac covers shape only; texturing is limited or disabled (`--disable_tex`) — [Brainkeys README_macOS](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md)

**Meshy (cloud)**
- Retexture costs 10 credits at 2K/4K and 15 credits at 8K. 8K base colour (`texture_resolution` 2k/4k/8k) was added in July 2026. meshy-5 was retired in October 2026; use meshy-6-lite at the same cost — [Meshy API pricing](https://docs.meshy.ai/en/api/pricing); [Meshy changelog](https://docs.meshy.ai/en/api/changelog); [Meshy help: API credits](https://help.meshy.ai/en/articles/16815622-how-many-credits-does-each-meshy-api-task-cost)
- Other prices: Image-to-3D on Meshy 7 is 20 credits for the mesh only, 30 with texture and 35 with an 8K texture. Remesh is 5, rig 5, animate 3, convert/resize 1 — [Meshy help](https://help.meshy.ai/en/articles/16815622-how-many-credits-does-each-meshy-api-task-cost). The project's Meshy MCP lists UV unwrap at 5 credits (tool documentation in this environment, prices stated as of 2026-10-12).
- Pro plan: about $20/mo for 1,000 credits, with API access. Failed tasks are refunded — [Meshy credits guide](https://www.meshy.ai/tutorials/meshy-credits-guide); [StackSheriff](https://stacksheriff.com/ai-tools/meshy-ai-pricing/). Sources disagree on whether API credits share a pool with web credits. Meshy's own guide says they do; a third-party site says they are separate.

**StableGen (Blender add-on, GPL-3.0)**
- It does multi-view diffusion texturing inside Blender through a ComfyUI backend (SDXL, FLUX.1-dev, Qwen Image Edit) with ControlNet depth and IPAdapter style guidance. It also supports PBR map extraction and baking, TRELLIS.2 mesh generation, a batch Scene Queue and GLB batch texturing. Modes: Separately, Sequentially, Grid, Refine, Local/Masked Edit and UV Inpaint. The wiki was last edited 28 Oct 2026 — [StableGen wiki](https://github.com/sakalond/StableGen/wiki); [xugj520 overview](https://www.xugj520.cn/en/archives/stablegen-blender-texture-generation.html)
- Stated requirements are Blender 4.2+, Windows/Linux and an NVIDIA GPU (recommended). macOS is not listed — [StableGen summaries](https://digialps.com/stablegen-ai-textures-your-3d-models-in-seconds-with-blender/)
- ComfyUI-BlenderAI-node is a general bridge that runs ComfyUI graphs as Blender nodes. It is not texturing-specific — [AIGODLIKE](https://github.com/AIGODLIKE/ComfyUI-BlenderAI-node)

**Research texturing methods (benchmarks)**
- MV-Adapter (ICCV 2025) Table 3, FID/KID/time on an RTX 4090: TEXTure 56.44/61.16/90 s, Paint3D 44.38/47.06/60 s, SyncMVD 36.13/42.28/50 s. MV-Adapter claims the best quality and the fastest time; its own row was not captured. The full text-to-texture and image-to-texture pipeline was released 2025-05-15 — [MV-Adapter arXiv](https://arxiv.org/html/2412.03632v1); [MV-Adapter GitHub](https://github.com/huanngzh/MV-Adapter)
- Paint3D's performance depends heavily on UV wrapping and texture complexity (MVPaint paper) — [MVPaint](https://www.researchgate.net/publication/385560255_MVPaint_Synchronized_Multi-View_Diffusion_for_Painting_Anything_3D)
- 3D-Adapter vs SyncMVD: about 26.40 vs 25.65 CLIP and 1.5 vs 1.9 min. Column labels were inferred by the search summary — [3D-Adapter](https://arxiv.org/pdf/2410.18974)

**Substance 3D / ArmorPaint**
- Substance 3D Painter 2026 on Steam is a $199.99 one-time purchase for that year's release only. Substance Indie on Steam is $24.99/mo (Painter, Designer and Modeler) and excludes Adobe's generative AI features. Adobe direct: Substance 3D Texturing $24.99/mo, Collection $59.99/mo — [Steam](https://store.steampowered.com/app/4329260/Substance_3D_Painter_2026/); [Photutorial](https://photutorial.com/adobe-substance3d-price/)
- ArmorPaint 1.0: source is free (zlib; build it yourself), binaries cost $19 one-time with lifetime updates, and macOS is supported. It has node materials, layers, masks, decals, UDIM and PBR export presets. A reviewer reports bugs — [Meshy blog alternatives](https://www.meshy.ai/blog/substance-painter-alternatives); [daily.dev ArmorPaint 1.0](https://daily.dev/posts/armorpaint-turns-1-0-free-substance-like-3d-painting-software--ab5jea5d9)

### Inferences
- For a painterly style, full PBR is mostly wasted: albedo plus a roughness constant usually suffices. Hunyuan-MLX output can be reduced to albedo, then stylised (posterise or hand-paint over) and recoloured with masks.
- Recommended local path on Mac: Hunyuan3D-Paint MLX. Cloud path: Meshy Retexture (10 credits). Manual paint-over: ArmorPaint or Blender texture paint.
- StableGen would need a remote ComfyUI (cloud GPU) to be practical. ComfyUI itself runs on MPS, but StableGen's model set (FLUX, TRELLIS.2) is heavy.

### Gaps
- Tripo texturing, Adobe Firefly 3D, Dream Textures (Mac status), ComfyUI-3D-Pack Mac support, Text2Tex/TEXTure Mac viability and cloud GPU hourly costs were not researched (budget ran out).
- MV-Adapter's own Table 3 numbers were not captured.
- No independent quality comparison of Meshy and Hunyuan-Paint PBR output was found.

## Delighting, UV automation and high-to-low baking

### Takeaway
Every AI generator bakes lighting into its base colour. Use the generator's own delight option (Meshy "Remove Lighting"; automatic at 8K) or a post tool, but delighting cannot recover detail hidden by shadows. For UVs on noisy AI meshes, PartUV (Nov 2025) produces about 20x fewer charts than xatlas or Blender in comparable time, and its part-aligned charts suit mask painting.

### Cited Findings
- AI base colours carry baked light. Meshy's fix is a "Remove Lighting" toggle, and at 8K delighting runs automatically. Delighting is subtraction and cannot restore what a shadow covered — [3D Red Box Studio](https://www.3dredboxstudio.com/blog/your-ai-albedo-has-the-light-baked-in)
- Neural4D uses intrinsic image decomposition during texture generation — [Neural4D](https://www.neural4d.com/how-tos/how-to-solve-baked-shadows-and-lighting-issues)
- Open-source ai-texture-delighter takes lit RGB, an object-space normal, AO and an alpha mask, and needs a GPU with at least 6 GB VRAM — [GitHub](https://github.com/vdmrcll/ai-texture-delighter)
- Older free tools: Unity Labs De-Lighting Tool (needs AO, normal and bent normal) and Agisoft De-Lighter (removes cast shadows and AO) — [CGChannel Unity](https://www.cgchannel.com/2017/07/download-unity-labs-free-texture-de-lighting-tool/); [CGChannel Agisoft](https://www.cgchannel.com/2019/07/download-free-texture-de-lighting-tool-agisoft-de-lighter/)
- Substance 3D Sampler has a parameter-free "Delight (AI Powered)" filter — [3D Red Box Studio](https://www.3dredboxstudio.com/blog/your-ai-albedo-has-the-light-baked-in)
- Make-A-Character treats neural delighting as image-to-image translation trained on lights baked into ground-truth albedo — [arXiv 2312.15430](https://arxiv.org/pdf/2312.15430)
- PartUV (arXiv 2511.16659) segments with PartField and then recursively refines charts under a distortion threshold. It handles non-manifold and degenerate triangles. On Common Shapes it averages 48.6 charts, compared with 1360.3 for Blender and 974.8 for xatlas, at similar distortion and xatlas-comparable runtime (tens of seconds). It works with UVPackmaster — [arXiv](https://arxiv.org/abs/2511.16659); [GameDev.net](https://gamedev.net/news/1731-partuv-part-based-uv-unwrapping-of-3d-meshes/)

### Inferences
- For stylised assets, a cleaner approach than delighting is to generate the texture under flat, even lighting, or to repaint the albedo by mask region (see the dye section).
- PartUV charts follow semantic parts, so a per-chart fill can produce a dye mask almost for free.

### Gaps
- Blender headless baking specifics (`blender -b -P`, `bpy.ops.object.bake` with Cycles on Metal, selected-to-active cage settings) and Meshy UV-unwrap quality were not researched in this pass. PartUV's Mac and MPS compatibility is unknown.

## Customisable colour: dye masks, palette shaders, Godot and three.js implementation, AI mask generation

### Takeaway
Standard practice is one RGB(A) mask texture: R = primary, G = secondary, B = accent, A = optional fourth. The shader blends each dye colour into the base by channel weight while keeping the base's luminance so painted shading survives. In Godot this is a ShaderMaterial with uniforms. In three.js WebGPU it must be TSL `colorNode`, because `onBeforeCompile` is not supported under WebGPURenderer. Masks can be auto-generated from 3D part segmentation (P3-SAM, SAMesh, GeoSAM2) by rasterising per-face labels into UV space.

### Cited Findings
- Godot pattern: uniforms `red_color`, `green_color` and `blue_color`, each multiplied by the matching mask channel and summed. Set them at runtime with `material.set_shader_parameter("name", value)` — [Godot Forum](https://forum.godotengine.org/t/best-way-to-change-colors-on-a-character-and-access-the-shader-parameters-from-the-script/132786)
- Spatial-shader variant: `ALBEDO = mix(mix(color_1, color_2, color.r), color_3, color.g)` sampling a packed mask — [Godot Forum](https://forum.godotengine.org/t/masking-color-with-a-packed-image/138959)
- The Six Channel Colour Shader (R/M/G/Y/B/C) uses channel intensity to carry shading (1.0 bright, 0.5 mid, 0.1 dark). It is Godot 3 syntax — [godotshaders](https://godotshaders.com/shader/six-channel-shader/)
- Luminance-preserving formula: `c.rgb = c.rgb*(1-mask) + secondary*mask*value`, where value is the base brightness — [Feitizo devlog](https://feitizogames.itch.io/pack/devlog/87508/secondary-color-shader)
- three.js WebGPURenderer does not support ShaderMaterial, RawShaderMaterial or onBeforeCompile on either backend. Built-in materials map to node equivalents, and custom work should be ported to TSL, which compiles to WGSL or GLSL — [Utsubo WebGPU migration](https://www.utsubo.com/blog/webgpu-threejs-migration-guide); [three.js llms.txt](https://threejs.org/docs/llms.txt)
- TSL tint example: `material.colorNode = materialColor.mul(color(0xff0000))`, importing from `three/webgpu` and `three/tsl` — [TypeGPU three docs](https://docs.swmansion.com/TypeGPU/ecosystem/typegpu-three)
- Mesh part segmentation: SAMesh lifts SAM2 masks from multi-view renders (about 7 min per mesh, tends to over-segment). Its ComfyUI wrapper exports per-segment GLB objects with `keep_texture` — [ComfyUI-Sam-Mesh](https://github.com/3dmindscapper/ComfyUI-Sam-Mesh)
- SAMPart3D distils SAM masks into 3D with a scale parameter (about 15 min per object). Its applications include part material editing — [alphaXiv](https://www.alphaxiv.org/abs/2411.07184)
- P3-SAM (Tencent Hunyuan) is a native 3D, fully automatic part segmenter trained on 3.7M meshes. Its point masks are projected to faces — [arXiv 2509.06784](https://arxiv.org/html/2509.06784v3)
- GeoSAM2 renders 12 untextured views, lets the user click or box a part, uses a LoRA SAM2 and back-projects the result. It reports higher mIoU than SAMPart3D, SAMesh and PartField — [arXiv 2508.14036](https://arxiv.org/html/2508.14036v1)
- All of these label faces or points, not texels. A UV mask requires rasterising face labels into the UV layout — [search synthesis of the above]

### Inferences
- Suggested TSL dye node (sketch, not sourced): `colorNode = mix(base, lum(base)*dyeR, m.r)`, then `mix(..., dyeG, m.g)` and `mix(..., dyeB, m.b)` on `MeshToonNodeMaterial`, with `m = texture(maskTex)`. Use the same maths in the Godot `fragment()` so dye results match across both runtimes.
- Vertex-colour masks (COLOR_0 in glTF) avoid an extra texture, suit low-poly ships and props, and survive gltfpack. Texture masks are better for characters with fine detail.
- Mask auto-generation pipeline: segment the mesh (P3-SAM or PartField) → assign parts to slots (an LLM or VLM picks sail = primary, hull trim = secondary, metal = accent) → bake face IDs to a UV mask in Blender (vertex colour → bake emit). Mask textures need linear (non-sRGB) colour space and no lossy chroma compression. Use KTX2 UASTC, or keep them uncompressed.

### Gaps
- Dye systems in shipped games (FFXIV dyes, WoW, Guild Wars 2) were not researched. Gradient-map and palette-LUT shaders were not specifically sourced.

## Stylised and painterly rendering in Godot and three.js

### Takeaway
Godot has many free MIT/open toon and stylised water/sky shaders (godotshaders.com, GDQuest). True "painterly" (Kuwahara or brush-stroke) post-effects were not found in this pass. three.js has MeshToonMaterial and its node equivalent, MeshToonNodeMaterial, for WebGPU.

### Cited Findings
- Stylized Toon Water (Godot 4) does colour banding by the angle between normal and camera, with flow and banding bias — [godotshaders](https://godotshaders.com/shader/stylized-toon-water/)
- Stylized Water for Godot 4.x (MIT, updated for 4.3) has depth fade and foam — [godotshaders](https://godotshaders.com/shader/stylized-water-for-godot-4-x/)
- GDQuest godot-4-stylized-sky: 3-input gradient sky, stars and scrolling clouds — [GitHub](https://www.Github.com/gdquest-demos/godot-4-stylized-sky). The GDQuest godot-shaders repo has an advanced toon shader, waterfall, cloud shadows and pointillism — [GitHub](https://github.com/GDQuest/godot-shaders)
- Toon Forge 3D (itch.io, Godot 4.3+) has 18 shaders: toon, outlines, halftone, hatching, water, sky, clouds — [itch.io](https://inkharbor.itch.io/toon-forge-3d)
- Toon materials have WebGPU node-material and TSL equivalents in three.js, and WebGLRenderer can draw node materials through the WebGLNodesHandler addon — [Tessl threejs-materials skill](https://tessl.io/registry/skills/github/cloudai-x/threejs-skills/threejs-materials)

### Inferences
- A painterly look comes mostly from the texture (hand-painted albedo, baked soft AO, no specular). Combine it with a 2–3 band toon ramp, rim light and optional outline. Keep the ramp and dye maths identical in Godot and three.js.

### Gaps
- Hand-painted style transfer (IP-Adapter or LoRA in the texturing step), Kuwahara post-processing and three.js painterly examples were not researched.

## Optimisation: gltf-transform, gltfpack, Draco, KTX2, Godot import, LOD

### Takeaway
three.js loads everything (Draco, meshopt and KTX2 through decoders). Godot 4 natively reads KTX2/Basis (since 4.2) and quantised meshes but, per a 2026 checklist, cannot open Draco. Meshopt support in Godot is unconfirmed. So the pipeline should ship two outputs: one uncompressed or quantised GLB (plus KTX2 or PNG) for Godot, whose importer auto-generates LODs with meshoptimizer, and one meshopt+KTX2 GLB for the web. Auto-LOD is risky on skinned and blend-shape meshes.

### Cited Findings
- By default gltfpack writes KHR_mesh_quantization, which three.js r111+ reads. `-cc` adds EXT_meshopt_compression (three.js r122+ with `setMeshoptDecoder`). `-tc` gives KTX2/BasisU (KHR_texture_basisu), `-tw` gives WebP, and `-mi` gives GPU instancing. gltfpack does not write Draco — [gltfpack docs](https://meshoptimizer.org/gltf/)
- KHR_meshopt_compression is the successor to EXT_meshopt_compression and uses a changed bitstream that EXT decoders may not read. gltfpack lists support for it — [Khronos PR #2517](https://github.com/KhronosGroup/glTF/pull/2517); [gltfpack](https://meshoptimizer.org/gltf/)
- three.js GLTFLoader supports KHR/EXT meshopt, KHR_texture_basisu (needs `setKTX2Loader`), Draco, EXT_mesh_gpu_instancing and EXT_texture_webp — [three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)
- gltf-transform can decode Draco (via draco3d) to decompress assets for engines that lack it — [glTF Transform extensions](https://gltf-transform.dev/extensions)
- Godot: KTX/KTX2 and KHR_texture_basisu support was merged for 4.2 (PR #76572) — [Godot PR](https://github.com/godotengine/godot/pull/76572)
- Godot: turn off Draco on export, because Godot cannot open Draco glTF (third-party 2026 checklist) — [Cinevva](https://app.cinevva.com/guides/blender-to-godot-export-checklist)
- Godot LOD: auto-generated at import with meshoptimizer for glTF, .blend and FBX (not OBJ), on by default. It "can sometimes cause rendering issues, especially in skinned meshes" and can be disabled per mesh. Normal split and merge angles are tunable. Shadow rendering uses LODs — [Godot docs mesh_lod](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)
- In Godot 4.6, `ImporterMesh::generate_lods` reportedly halves the target each step and uses Sparse, LockBorder, Prune and Regularize for skinned surfaces simplified in rest pose (from a third-party engine port, not Godot docs) — [SlashEngine PR #199](https://github.com/zerojunz/SlashEngine/pull/199)
- Decentraland's Godot runtime LOD skips skinned and blend-shape surfaces because simplification breaks them — [godot-explorer #2074](https://github.com/decentraland/godot-explorer/issues/2074)
- Blend shapes: use the Blender glTF export option "Export Deformation Bones Only" — [Cinevva](https://app.cinevva.com/guides/blender-to-godot-export-checklist)
- Godot's ResourceImporterScene has a per-mesh option to disable mesh compression — [Godot 4.2 class docs](https://docs.godotengine.org/en/4.2/classes/class_resourceimporterscene.html)

### Inferences
- Web build: `gltfpack -cc -tc` (or gltf-transform `meshopt` + `ktx2`). Godot build: plain GLB with PNG textures (Godot recompresses to VRAM formats on import) or KTX2. Never ship Draco or meshopt to Godot unless Godot meshopt support is confirmed.
- For skinned characters with blend shapes, make LODs manually in Blender (Decimate with shape-key preservation is limited) or skip LOD. Characters are few, so the triangle budget matters less than for scattered props.

### Gaps
- Godot's support for EXT/KHR_meshopt_compression was not confirmed. Concrete triangle and texture budgets for web vs desktop were not sourced. gltf-transform CLI command specifics (simplify, weld, resize, palette) were not fetched.

## Procedural generation: Geometry Nodes, Houdini, LLM-written procedural code

### Takeaway
Houdini Indie costs $299/yr (revenue under $100K), and Houdini Engine Indie is free but only for the official Unity, Unreal, Maya and 3ds Max plugins. No official Godot Houdini Engine plugin exists, and a custom one needs a commercial Engine licence. Blender (Geometry Nodes plus bpy) is therefore the practical free procedural core. LLM-agent research (LL3M, MeshCoder) shows Blender-Python code generation is viable and editable.

### Cited Findings
- Houdini Indie: $299 for 1 yr or $449 for 2 yrs. It has all FX features, requires revenue at or below $100K and funding under $1M, and allows at most 3 licences — [SideFX Indie](https://www.sidefx.com/products/houdini-indie/). Apprentice is free; Core is $1,475 and FX $3,505 per year — [Shade 2026](https://shade.inc/blog/sidefx-houdini-pricing-2026-fx-core-indie-license-costs)
- Houdini Engine Indie works with the official Unity, Unreal, Maya and 3ds Max plug-ins. Custom plug-ins built on the Engine API need a commercial Engine licence (about $499–525/yr). That FAQ may be dated — [SideFX Engine FAQ](https://www.sidefx.com/faq/houdini-engine-faq/)
- LL3M (arXiv 2508.08228): planner, retriever, coder, critic and verifier agents write and debug Blender Python, using a BlenderRAG knowledge base built from the API docs. No fine-tuning. Code is at threedle/ll3m and runs as a client-server Blender add-on — [EmergentMind](https://www.emergentmind.com/papers/2508.08228); [GitHub](https://github.com/threedle/ll3m)
- MeshCoder (NeurIPS 2025): point cloud → part-structured, editable Blender Python, trained on a 10M part-level Infinigen dataset. L2 Chamfer 0.06×10⁻² — [arXiv 2508.14879](https://arxiv.org/abs/2508.14879)
- Related prior work cited by LL3M: L3GO, 3D-GPT, SceneCraft, BlenderAlchemy (VLM material editing) and BlenderMCP — [Pith review](https://pith.science/paper/2508.08228)
- LLM-Blender-Agent controls Blender with natural language on top of BlenderMCP — [GitHub](https://github.com/saofund/LLM-Blender-Agent)
- A Blender MCP server (execute_blender_code, render_thumbnail_to_path, API and manual docs search) is already available in this project's environment (observed tool list).

### Inferences
- Skill design: the agent writes parametric bpy/Geometry Nodes generators (hull from spline profiles, mast and sail rigs, plank arrays; islands = displaced noise base + cliff skirt + scatter). It renders thumbnails through Blender MCP, then critiques and iterates in an LL3M-style loop. Generators are stored as versioned .py files, not as one-off meshes.
- Modular kit snapping: use socket empties (named `SOCKET_*`) exported as glTF nodes, which Godot imports as Node3D. That convention is standard but was not sourced here.

### Gaps
- Specific Geometry Nodes ship builders, scatter add-ons, community Godot Houdini plugins, 3D-GPT and SceneCraft details, and Infinigen on Mac were not researched.

## Asset validation and QA

### Takeaway
Not covered in depth in this pass. The available pieces are the Khronos glTF validator (CLI and npm), Godot headless import (`godot --headless --import`), and Blender MCP and headless renders for turntables.

### Cited Findings
- The Blender MCP in this environment exposes `render_thumbnail_to_path` and `render_viewport_to_path` (observed tool list).
- gltf-transform has an `inspect`-style toolchain, and its extensions page lists supported extensions — [glTF Transform](https://gltf-transform.dev/extensions)

### Inferences
- Suggested QA gate: run gltf-validator (zero errors), check the triangle and texture-size budget with gltf-transform inspect, run a Godot headless import and parse its errors, render a 4–8-view turntable in Blender EEVEE (Metal), and check dye-mask coverage (no texels outside the R/G/B slots unless intended).

### Gaps
- The glTF-Validator repo and CLI, Godot `--import` headless flags and their exit-code behaviour, and turntable scripts were not sourced in this pass (out of research budget). Verify them before relying on them.
