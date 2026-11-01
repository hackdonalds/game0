# AI image-to-3D / text-to-3D generation for game assets (state as of Nov 2026)

Scope: commercial services, open models, part-segmented generation, multi-view front-ends, benchmarks, core algorithms. Target: game0 (stylized painterly, concept-art driven), Godot 4 + three.js via glTF, Apple Silicon Mac only, preference for free/local.

Research method note: ~17 web searches (search-result summaries, not full page fetches). Prices change often; per-model pages and official docs are authoritative. Several "comparison" sources are vendor blogs (Meshy, Tripo, Sloyd, 3D AI Studio, Pixazo) with a stake in the result; flagged where relevant.

## Commercial services: versions, topology options, rigging, parts, PBR, pricing, licensing

### Takeaway
Meshy (7.1 / 6 / Smart Topology T2) and Tripo (P1 smart-mesh, H3.1 with quad/low-poly/parts add-ons, segmentation) are the two most game-oriented APIs with rigging and part splitting; Rodin Gen-2 is the quad-topology specialist but its official API needs a Business plan (resellers ~$0.30-0.80/gen). Hunyuan3D 3.x is hosted-only and cheap through fal ($0.225-0.375/gen, parts $0.45). Luma Genie appears retired, Kaedim is expensive human-in-the-loop, Sloyd is parametric props only.

### Cited Findings

**Meshy (already used via MCP)**
- Current credit costs (official API pricing, 2026-10-12, as embedded in the Meshy MCP server instructions): image/multi-image-to-3D on meshy-7.1 / meshy-6 = 20 credits mesh-only, 30 with 2K/4K texture, 35 with 8K; meshy-6-lite = 5 mesh / 15 textured; meshy-t2 / t2.5 (single-image Smart Topology) = 5 mesh / 15 textured / 20 8K; Ultra geometry +5; text-to-3D preview 20 (meshy-7.1/6) or 5 (lite/t2); refine/retexture 10; remesh, rig, UV unwrap 5 each; animate 3 per action; text-to-motion 10/3; auto-split 10 — [Meshy API pricing](https://docs.meshy.ai/en/api/pricing)
- Meshy 7.1 released Sept 10, 2026; switches between High Detail and Smart Topology meshes from 100 to 300,000 faces — [3D AI Studio blog (reseller)](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)
- Meshy-6 GA January 2026, ~600K faces, adds Low Poly Mode; Smart Remesh adjusts topology/polycount — [toolworthy review](https://www.toolworthy.ai/tool/meshy-ai-v6); [tooldirectory](https://tooldirectory.ai/tools/meshy)
- Described as having quad meshes, A/T-pose control for rigging, remesh built into generation — [3D AI Studio blog](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)
- Free plan: 100 credits/month, outputs licensed CC BY 4.0 (commercial allowed with attribution); paid plans (Pro $20/mo with 1,000 credits, Premium $40, Studio $70, Ultra $100) are "Private" license, full commercial use, you own outputs — [Meshy webapp pricing docs](https://docs.meshy.ai/en/webapp/pricing); [makerstack review](https://makerstack.co/reviews/meshy-review/)
- API access reportedly Pro tier and up — [stacksheriff](https://stacksheriff.com/ai-tools/meshy-ai-pricing/)
- Remesh shows as 0 credits in the web app vs 5 credits in the API (sources conflict) — [Meshy webapp pricing](https://docs.meshy.ai/en/webapp/pricing)
- Auto Split API: `POST /openapi/v1/print/split`; source model must be Meshy 6/7/7.1; low-poly and Smart Topology (t2/t2.5) models NOT supported; `auto` mode or a text prompt describing parts. It lives under a "print" path (aimed at 3D printing) — [Meshy Auto Split docs](https://docs.meshy.ai/api/auto-split.md)
- Vendor-sponsored blind test claims Meshy 6 preferred over Tripo 3.1 by 63.8% of 1,331 artists (vendor claim) — [3D AI Studio blog](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)
- One 2026 test: Meshy output needs retopology for hero assets but is fine for secondary props — [3D AI Studio blog](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)

**Tripo (Tripo3D)**
- Official API: 1 credit = $0.01. P1 (smart-mesh, all-in pricing): image-to-model 40 untextured / 50 textured; text-to-model 30/40; multiview 40/50 ($0.30-0.50 per asset). H2/H3 surcharges: smart_low_poly +10, quad +5. H3.1 add-ons: detailed geometry +20, quad +5, smart low-poly +10, **generate in parts +20**; with quad=true output is FBX, face limit up to 150,000. Post-processing: retopology v3.0 triangle 35, quad 40, v2.0 smart 30; Smart UV 20 — [Tripo API pricing](https://developers.tripo3d.ai/en/pricing); [Tripo docs pricing](https://docs.tripo3d.ai/get-started/pricing.html); [Tripo H3.1 model page](https://developers.tripo3d.ai/en/models/v3-1)
- Studio (separate from API credits): HD Model 15, Smart Mesh P1 35, Smart Mesh P2 100 credits — [Tripo product doc pricing](https://www.tripo3d.ai/product-doc/getting-started/pricing-credits)
- P1 previewed GDC 2026, announced 25 March 2026; Tripo claims production-ready low-poly assets in as little as 2 s — [aiwiki Tripo P1](https://aiwiki.ai/wiki/tripo_p1); [Barchart press release](https://www.barchart.com/story/news/936837/tripo-ai-introduces-smart-mesh-p1-0-defining-a-new-phase-for-ai-3d-production)
- Reseller prices: 3D AI Studio P2 200 credits, P1 60, Tripo 3.1 40; PoYo (fal-based) P1 $0.28 untextured / $0.35 textured — [3D AI Studio Tripo API](https://www.3daistudio.com/Platform/API/Tripo); [PoYo](https://poyo.ai/models/tripo-p1-3d)
- Official P2 API price not found (gap).
- Segmentation: v1 geometry-based (no params), v2 semantic with granularity, "split by connectivity", reference image to dictate breakdown — [Scenario blog](https://www.scenario.com/blog/tripo-segmentation-3d-mesh-editable-parts-scenario)
- Smart Segment (ComfyUI node): names each part, granularity default "medium", text hint (e.g. "game character with sword and armor"), GLB input only, ~180 s, ~$0.85 from image or ~$0.55 from existing model; chains into Complete Mesh Parts, Retopology, Texture, Convert — [ComfyUI docs](https://docs.comfy.org/built-in-nodes/TripoSmartSegmentNode)
- fal endpoint `tripo3d/tripo/segment` returns part names that can be passed to remesh `part_names` to preserve parts — [fal.ai](https://fal.ai/models/tripo3d/tripo/segment/api)
- Rigger handles non-humanoids since Feb 2026 (quadruped, hexapod, avian, serpentine, aquatic); style transforms (voxel, cartoon, clay, LEGO...) — [3D AI Studio blog](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)
- Tripo leads the "Top 3D AI arena" community ELO (186,939 votes) per a Sloyd blog post Aug 2026 (interested party) — [Sloyd blog](https://www.sloyd.ai/blog/ai-3d-model-generator-rankings)
- Tripo MCP server: not confirmed in my searches (gap).

**Rodin / Hyper3D (Deemos)**
- Gen-2 API: base 0.5 credit per generation; HighPack +1 credit; "no additional fees for parameters". Quad is default mesh mode; quad tiers high 50k / medium 18k / low 8k / extra-low 4k faces; quad range 1,000-200,000; HighPack only with Quad — [Hyper3D Gen-2 API spec](https://developer.hyper3d.ai/api-specification/rodin-generation-gen2)
- Official API requires Business subscription (one third-party page says ~$400/mo billed yearly) — [Hyper3D API spec](https://developer.hyper3d.ai/api-specification/rodin-generation-gen2); [empiriolabs](https://empiriolabs.ai/models/hyper3d-gen2)
- Pay-per-use resellers: WaveSpeed $0.30-0.40, ModelRunner $0.399, fal ~$0.40, Pixazo v2.5 $0.40 (Extreme-High $0.80), EmpirioLabs $0.80 — [WaveSpeed](https://wavespeed.ai/models/hyper3d/rodin-v2/image-to-3d); [ModelRunner](https://modelrunner.ai/models/hyper3d/rodin/gen-2); [Pixazo](https://www.pixazo.ai/models/hyper3d)
- Rule of thumb in 2026 comparisons: Rodin when clean quad topology on hero assets matters most — [3D AI Studio blog](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)

**Hunyuan3D cloud (Tencent, 2.5 / 3.0 / 3.1 hosted-only)**
- 3.x has no open weights as of Oct 2026; 3.1 adds higher resolution, 4K PBR, up to 8-view input — [Meshy compare page](https://www.meshy.ai/compare/meshy-vs-hunyuan3d); [Wireflow](https://www.wireflow.ai/blog/best-hunyuan3d-v3-tools-in-2026)
- 3.1 Pro: multi-view input, PBR, configurable polycount up to 1.5M faces; available via Tencent web studio, Tencent Cloud API, Replicate, 3D AI Studio — [Layer.ai](https://layer.ai/models/tencent-hunyuan3d-v3-1-pro)
- 3.1 release date conflicts: Nov 2025 (Meshy), early 2026 (Wireflow), July 2026 (Layer listing) — sources above.
- fal: Pro text/image-to-3D $0.375/gen, Rapid $0.225, PBR +$0.15, **part splitting $0.45**, smart retopology $0.75 — [fal Hunyuan 3D](https://fal.ai/hunyuan-3d)
- WaveSpeed Rapid flat $0.27 — [Replicate/Modelglass summary](https://modelglass.com.au/models/tencent--hunyuan3d)

**Others**
- Luma Genie: Meshy's comparison says Luma retired Genie Jan 1, 2026; other 2026 listicles still list it (likely stale) — [Meshy blog](https://www.meshy.ai/blog/best-ai-tools-for-3d-game-assets); [techsy](https://techsy.io/en/blog/best-ai-game-asset-generators)
- Sloyd: parametric game props; free Guest tier 1 gen/day personal-use only; Plus $15/mo (commercial use, AI rigging/animation, 4K retexture); Pro $50/mo; exports OBJ/GLB/STL — [Ludo compare](https://ludo.ai/compare/best-ai-3d-model-generators); [Meshy blog](https://www.meshy.ai/blog/best-ai-tools-for-3d-game-assets)
- Kaedim: AI + human QA; no free plan; one source lists Trial $50/7 days, Indie $400/mo (20 credits), Pro $1,200/mo; another found no public pricing in Aug 2026 — [renderahouse](https://www.renderahouse.com/blog/best-ai-3d-model-generators); [Ludo](https://ludo.ai/compare/best-ai-3d-model-generators)
- CSM (Common Sense Machines, Cube): was #1 on 3D Arena in March 2025 (old); no 2026 pricing found — [Dylan Ebert on X](https://x.com/dylan_ebert_/status/1902383506262458461)
- 3D AI Studio: an aggregator/reseller of Tripo, Hunyuan, TRELLIS.2 etc.; TRELLIS.2 ~ $0.08 cheapest, $0.15 mid with PBR — [3D AI Studio API comparison](https://www.3daistudio.com/blog/best-3d-model-generation-apis-2026)

### Inferences
- For game0's swappable parts, Tripo's semantic segmentation (named parts + text hint) and H3.1 "generate in parts" are the most game-oriented commercial part tools; Meshy Auto Split exists but is print-oriented and incompatible with its low-poly/Smart-Topology outputs, so you would split a meshy-6/7.1 high-detail model first, then remesh each part.
- Cheapest commercial per-asset path for quad/low-poly: Meshy t2 Smart Topology (5-15 credits ~ $0.10-0.30 on Pro) or Tripo P1 ($0.30-0.50 all-in); Rodin via fal (~$0.40) for hero quad meshes.

### Gaps
- Tripo MCP server details and Tripo P2 official API price not found.
- CSM 2026 pricing/model versions, Luma Genie definitive status, Meshy quad-vs-triangle API flag not verified.
- Tripo and Rodin commercial license terms (free-tier ownership) not retrieved.

## Open models: quality, VRAM, Mac (MPS/MLX/CPU) support, hosted prices

### Takeaway
TRELLIS.2-4B (MIT, Dec 2025) is the consensus open leader and now runs on Apple Silicon via community MPS ports (~3.5 min/asset on M4 Pro 24 GB, textured PBR GLB). Hunyuan3D 2.1 (shape + PBR paint) also runs on MPS via forks but its license excludes EU/UK/South Korea. Hosted runs are cents: TRELLIS on fal $0.02, Hunyuan3D 2.1 $0.05 on fal, ~$0.10-0.17 on Replicate; HF ZeroGPU Spaces give a few free runs a day.

### Cited Findings

**TRELLIS.2 (Microsoft)**
- 4B-param flow-matching transformer + sparse-voxel 3D VAE; single image in, mesh with PBR (incl. transparency) out; O-Voxel handles open surfaces/non-manifold; 16x downsampling compresses 1024^3 asset to ~9,600 tokens; trained on 500K assets; resolution 512^3-1536^3; H100 timing 3 s / 17 s / 60 s at 512/1024/1536 — [TRELLIS.2 project page](https://microsoft.github.io/TRELLIS.2/); [HF model card](https://huggingface.co/microsoft/TRELLIS.2-4B)
- MIT license, commercial OK; drops text input and Gaussian/NeRF output vs v1; weights are a base model without alignment — [triposr.org](https://triposr.org/blog/trellis-2-vs-trellis); [HF](https://huggingface.co/microsoft/TRELLIS.2-4B)
- VRAM: 24 GB+ commonly cited; CodeSOTA claims 16 GB @512, 40 GB @1024, 80 GB @1536 (conflict) — [codesota](https://www.codesota.com/news/trellis-2-3d-generation)
- Mac: shivampkumar/trellis-mac replaces flex_gemm, flash_attn, nvdiffrast, cumesh with pure PyTorch; M4 Pro 24 GB generates 400K+ vertex mesh in ~3.5 min; textured OBJ/GLB with PBR; Show HN ~April 20, 2026 — [daily.dev](https://daily.dev/posts/github---shivampkumar-trellis-mac-vayzxbmie); [aigcdev](https://aigcdev.com/en/news/2026042001); [Ship or Skip](https://shiporskip.io/tool/trellis-mac-image-to-3d-apple-silicon-mps-no-nvidia-2026)
- SUP3RMASS1VE/trellis-mac-GUI (Pinokio): Gradio UI, Metal-accelerated PBR baking, GLB/OBJ; M1+, 24 GB+ unified memory recommended — [Pinokio](https://pinokio.co/apps/github-com-sup3rmass1ve-trellis-mac-gui-pinokio)
- trellis.cpp (GGML C++): CUDA/ROCm/Vulkan, no Metal mentioned — [trellis.cpp wiki](https://github.com/pwilkin/trellis.cpp/wiki)
- Native ComfyUI support since 0.34.0 — [triposr.org](https://triposr.org/blog/trellis-2-vs-trellis)
- Hosted: fal TRELLIS (v1) $0.02/gen; fal TRELLIS 2 $0.05/unit, cloudprice lists ~$0.30/output (conflict) — [fal pricing](https://fal.ai/pricing); [cloudprice](https://cloudprice.net/models/fal-ai-trellis-2)

**Hunyuan3D 2.0 / 2.1 (open) and 2.5 / 3.x (closed)**
- 2.1 (June 13, 2025) fully open: new PBR paint model, VAE encoder, training code; latest open release; 2.5/3.0/3.1 hosted only — [Hunyuan3D-2 GitHub](https://www.github.com/Tencent-Hunyuan/Hunyuan3D-2); [Meshy compare](https://www.meshy.ai/compare/meshy-vs-hunyuan3d)
- License: Territory = worldwide **excluding EU, UK, South Korea**, applies to outputs too; >1M MAU needs separate license; outputs may not train non-Hunyuan models — [Hunyuan3D-2 LICENSE](https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE); [contrast3d](https://www.contrast3d.com/blog/hunyuan3d-licencia-union-europea/)
- Mac ports: VladimirTalyzin/hunyuan3d-2.1-mac-rocm (MPS + ROCm, PBR albedo + metallic-roughness + UV bake verified end-to-end on MPS; torch rasterizer, no compiler; texturing markedly slower on Mac; Pinokio, updated 8/9/2026) — [GitHub](https://github.com/VladimirTalyzin/hunyuan3d-2.1-mac-rocm); [Pinokio](https://pinokio.co/apps/github-com-vladimirtalyzin-hunyuan3d-2-1-mac-rocm)
- Brainkeys/Hunyuan3D-2.1-mac: `--device mps --low_vram_mode --disable_tex`; ~5-10x slower than CUDA — [README_macOS](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md)
- alawrenceld/Hunyuan3D_Blender: Hunyuan3D-2 on MPS + Blender MCP; 16 GB min (32 GB+ rec.), 3-5 min/gen — [GitHub](https://github.com/alawrenceld/Hunyuan3D_Blender)
- Original 2.0 on Mac = untextured mesh only (CUDA rasterizer) — [Codersera](https://codersera.com/blog/how-to-install-and-run-hunyuan3d-2-on-macos-a-step-by-step-guide/)
- Hosted: fal v2 $0.16 white mesh / $0.48 textured; v2 turbo $0.14; 2.1 $0.05; Replicate tencent/hunyuan3d-2 ~$0.13/run (L40S), ndreca 2.1 ~$0.17, turbo ~$0.11 — [fal pricing](https://fal.ai/pricing); [fal v2](https://fal.ai/models/fal-ai/hunyuan3d/v2); [Replicate](https://replicate.com/tencent/hunyuan3d-2); [Replicate ndreca 2.1](https://replicate.com/ndreca/hunyuan3d-2.1)
- HF ZeroGPU: official Hunyuan3D-2 and TRELLIS Spaces run on ZeroGPU; free quota a few minutes GPU/day — [triposr.org](https://triposr.org/blog/trellis-2-vs-trellis)

**Pixal3D (TencentARC, SIGGRAPH 2026) — newest 2026 SOTA candidate**
- Pixel-aligned back-projection of image features into 3D, "near-reconstruction-level fidelity" with PBR; May 2026 release; `main` branch built on TRELLIS.2 backbone, paper branch on Direct3D-S2 — [GitHub](https://github.com/TencentARC/Pixal3D); [HF](https://huggingface.co/TencentARC/Pixal3D)
- License conflict: GitHub says MIT; HF metadata MIT with `extra_gated_eu_disallowed: true`; an earlier HF commit had custom "pixal3d-license"; ComfyUI wrapper calls weights "academic-only" — [HF](https://huggingface.co/TencentARC/Pixal3D); [ComfyUI-Pixal3D](https://github.com/PozzettiAndrea/ComfyUI-Pixal3D); [HF discussion](https://huggingface.co/TencentARC/Pixal3D/discussions/2)
- A Sept 2026 OSS tracker prioritizes Pixal3D over Step1X-3D/TripoSG/Direct3D-S2 — [image2outfit issue #683](https://github.com/KAFKA2306/image2outfit/issues/683)

**Other open models**
- TripoSG: 1.5B rectified-flow transformer on SDF latent (2048 tokens), 2M image-SDF pairs, geometry only, >=8 GB VRAM, MIT — [BuilderAI](https://builderai.tools/blog/single-image-to-3d-model-pipeline-2026)
- Step1X-3D: claims top CLIP score vs TRELLIS v1, Hunyuan3D 2.0, TripoSG, Tripo 2.5, Rodin 1.5, Meshy-4 (self-reported, predates TRELLIS.2) — [arXiv 2505.07747](https://arxiv.org/pdf/2505.07747)
- Direct3D-S2: spatial sparse attention on sparse volumes, gigascale resolution; one ranking lists #5, Elo 1215, MIT, 6 GB VRAM (blog of uncertain reliability) — [arXiv 2505.17412](https://arxiv.org/pdf/2505.17412); [triposplat](https://triposplat.com/blog/best-3d-ai-generators-2026)
- Stable Fast 3D (Aug 2024, built on TripoSR) and SPAR3D (Jan 2025): Stability Community License, free commercial under $1M annual revenue; SF3D MPS support "experimental"; ~6 GB VRAM — [HF SF3D](https://huggingface.co/stabilityai/stable-fast-3d); [Stability SPAR3D](https://stability.ai/news-updates/stable-point-aware-3d); [cpu3d](https://cpu3d.com/en/ai3d/stable-fast-3d/)
- TripoSR, TRELLIS v1: MIT; SF3D/TripoSR cover the real-time/low-quality end; Hi3DGen and TRELLIS.2 have closed most of the gap with commercial — [cmarix](https://www.cmarix.com/blog/top-open-source-ai-models-for-3d-image-generation/)

### Inferences
- Best local Mac stack today: TRELLIS.2 via trellis-mac (MIT, PBR) as the default; Hunyuan3D 2.1 MPS fork as a second opinion if the user is outside EU/UK/KR (the user's locale is not established; check before relying on it). TripoSG is a lighter MIT geometry-only option if a separate texturing step is used.
- Painterly style: Open models bake lighting-free PBR from the input image; for painterly looks, the concept art itself carries the style, so input-image quality (flat lit) matters more than model choice.
- Commercial-quality gap: hosted Hunyuan 3.1 at $0.225-0.375 is cheap enough to use as a "paid where free doesn't come close" fallback.

### Gaps
- No MLX port of any 3D generator found. CraftsMan, InstantMesh, SPAR3D Mac status not checked. Modal/RunPod per-run costs not found. TRELLIS on Replicate price not found. No head-to-head of TRELLIS.2 vs Hunyuan3D 2.1 vs Pixal3D on stylized inputs.

## Part-aware / segmented generation

### Takeaway
For separable, swappable parts, the practical options are: Hunyuan3D-Part (P3-SAM segmentation + X-Part completion, open "light" version, CUDA), Tripo segmentation/parts (commercial, named parts), Hunyuan 3.1 part splitting on fal ($0.45), and Meshy Auto Split. Research models (PartCrafter, PartPacker, OmniPart, HoloPart) mostly only control part count; HoloPart and OmniPart score best on part quality.

### Cited Findings
- Hunyuan3D-Part (late Sept 2025): P3-SAM native 3D part segmentation (trained on 3.7M shapes, any input mesh, outputs semantic features, segments, bounding boxes) -> X-Part diffusion completes each part; open release is a "light" X-Part, full version in Hunyuan3D Studio; recommended input = AI-generated meshes; output GLB with parts, bboxes, exploded views; PyTorch 2.4 + CUDA 12.1; Tencent Hunyuan 3D-Part community license (territory exclusions) — [HF Hunyuan3D-Part](https://huggingface.co/tencent/Hunyuan3D-Part); [Tencent on X](https://x.com/TencentHunyuan/status/1971491034044694798); [localclaw guide](https://localclaw.io/3d/hunyuan3d-part); papers [P3-SAM arXiv 2509.06784](https://arxiv.org/abs/2509.06784), [X-Part arXiv 2509.08643](https://arxiv.org/abs/2509.08643)
- Community fork adds batch decoding and Tripo-compatible multi-node exploded GLB — [GitHub](https://github.com/santoshreddy-hash/changes-to-xpart-p3sam)
- PartCrafter: single model synthesizes multiple parts from an RGB image without pre-segmentation, part count as input; decodes each part independently, latency grows with parts — [CubePart arXiv 2605.28763](https://arxiv.org/html/2605.28763); [PartMat arXiv 2608.01825](https://arxiv.org/pdf/2608.01825)
- PartPacker: packs parts into two complementary volumes denoised jointly; merges parts until bipartite, undersegments interlocking parts — [arXiv 2609.15659](https://arxiv.org/html/2609.15659v1)
- OmniPart: 2D part masks -> 3D bounding-box planning -> TRELLIS-based spatially conditioned part generation — [CubePart](https://arxiv.org/html/2605.28763)
- HoloPart: segment an existing 3D shape then diffusion-complete occluded regions of each part (needs segmented input) — [CubePart](https://arxiv.org/html/2605.28763)
- CubePart: PartCrafter/PartPacker only control part count; image-conditioned baselines give noisier boundaries; in its table HoloPart and OmniPart (with good segmentation) score best on single-part quality — [CubePart](https://arxiv.org/html/2605.28763)
- Newer 2026 research: CubePart (open-vocabulary part control), MultiCube, UniPart, FullPart (each part at full resolution), X-Part, AutoPartGen, BANG, CoPart — [MultiCube arXiv 2608.20448](https://arxiv.org/pdf/2608.20448); [UniPart](https://arxiv.org/html/2512.09435); [FullPart](https://arxiv.org/pdf/2510.26140)
- Muses (Jan 2026): training-free composition of fantasy creatures — [arXiv 2601.03256](https://arxiv.org/pdf/2601.03256)
- Commercial part tools: see Tripo segmentation, Meshy Auto Split, fal Hunyuan part splitting above.

### Inferences
- "Swappable" parts (helmets, horns, tails) need watertight completed parts, not just cut segments: HoloPart/X-Part style completion is the right shape; plain segmentation (Tripo v1, Meshy split) leaves holes where parts met.
- Reliable alternative for game0: generate attachables separately (one horn, one helmet per generation) and attach to a shared base body, using part split only for cleanup. This is what the existing meshy skill already does ("attachable parts").
- None of these part tools were confirmed to run on Mac.

### Gaps
- SAMPart3D, PartField, BANG: no Mac/licence/quality details retrieved. No benchmark specifically on swappable game accessories.

## Multi-view front-ends and input-image best practices

### Takeaway
MV-Adapter (ICCV 2025) turns SD/SDXL (and style fine-tunes) into a 6-view orthographic generator (768 px, ~14 GB); it feeds multi-view-capable reconstructors (Meshy multi-image, Tripo multiview, Hunyuan 3.1 up to 8 views). Inputs: neutral A/T-pose, consistent style/scale, even flat lighting, clean background.

### Cited Findings
- MV-Adapter: plug-and-play adapter for T2I models and derivatives (DreamShaper, Animagine, LCM, ControlNet); trained on ~70K Objaverse with orthographic renders, 6 views, 768x768; checkpoints i2mv (SD2.1/SDXL), tg2mv/ig2mv (geometry-guided texturing), arbitrary views (8 anchor views); image-to-MV needs ~14 GB GPU memory — [GitHub](https://github.com/huanngzh/MV-Adapter); [arXiv 2412.03632](https://arxiv.org/pdf/2412.03632)
- Repo example prompt for characters uses "full body", "no background", "even lighting, clean lines, neutral colors, no contrast" — [GitHub](https://github.com/huanngzh/MV-Adapter)
- Meshy guide: multi-view works best for character sheets and stylized/anime characters; one pre-composited turnaround sheet is accepted; keep style, scale and pose consistent; neutral A-pose or T-pose gives the most accurate proportions — [Meshy tutorial](https://www.meshy.ai/tutorials/multi-view-image-to-3d)
- Tripo P1 and Hunyuan 3.1 accept multiview input (40/50 credits on Tripo P1; up to 8 views on Hunyuan 3.1) — [Tripo pricing](https://developers.tripo3d.ai/en/pricing); [Wireflow](https://www.wireflow.ai/blog/best-hunyuan3d-v3-tools-in-2026)

### Inferences
- For painterly concept art, generate a front/side/back turnaround with the image model already in the Meshy MCP (nano-banana / GPT Image) in flat, shadowless lighting, then use multi-image-to-3D. Baked shadows in concept paintings tend to end up in the albedo.

### Gaps
- Zero123++ and Era3D 2026 status, and MV-Adapter on Mac, not checked.

## Benchmarks / leaderboards and practitioner consensus

### Takeaway
No neutral, current leaderboard covers everything. 3D Arena (HF, human pairwise ELO, 123K votes) last had a verified top in Mar 2025 (CSM Cube). 2026 vendor-run boards conflict: one puts Tripo first, Pixazo's VLM board puts Hunyuan 3D Pro > Rodin 2 > Meshy 6 > Tripo 2.5 > TRELLIS 2. Practitioner rule of thumb: Tripo for stylized/volume props, Meshy for rig-ready characters, Rodin for hero quad topology, Hunyuan/TRELLIS.2 for free self-hosting.

### Cited Findings
- 3D Arena: open HF space, pairwise human preference, ELO, 123,000 votes, iso3d 100-image set — [arXiv 2506.18787](https://arxiv.org/html/2506.18787v1); [HF space](https://huggingface.co/spaces/dylanebert/3d-arena)
- Pixazo VLM-scored board: Hunyuan 3D Pro 1508, Rodin 2 1477, Meshy 6 Preview 1335, Rodin 2.5 1288, Pixal 3D (Pixazo's own) 1224, Tripo 2.5 1217, TRELLIS 2 1051 — [Pixazo](https://www.pixazo.ai/leaderboard/ai-3d-model-generation)
- Hi3DEval (NeurIPS 2025 D&B): hierarchical object/part/material scoring, 15K-asset Hi3DBench, combined leaderboard with 3DGenBench and GPTEval3D; 5 dimensions (geometry plausibility, geometry detail, texture quality, geo-texture coherence, prompt alignment); image-to-3D methods dominate; better agreement with humans than CLIP/GPTEval3D — [arXiv 2508.05609](https://arxiv.org/pdf/2508.05609); [3DGen-Leaderboard](https://huggingface.co/spaces/3DTopia/3DGen-Leaderboard)
- Consensus summary (from vendor-adjacent blogs, no Reddit threads found): Tripo for stylized / high-volume props, Meshy for characters you will rig (quad), Hunyuan for free self-hosting, Rodin for clean quad hero assets; Rodin and Tripo topology "clean enough for production" — [3D AI Studio](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)
- TRELLIS.2 "current open-source leader" — [cinevva](https://app.cinevva.com/guides/ai-3d-model-generators)

### Inferences
- Rankings measure realism-heavy object sets; stylized painterly suitability is untested by any benchmark, so a small in-house A/B on game0 concept art (TRELLIS.2 local vs Meshy vs Tripo P1) is the only trustworthy signal.

### Gaps
- Current 3D Arena standings and Hi3DEval full table not retrieved; no real Reddit practitioner threads found.

## Core algorithms (1-2 lines each)

### Takeaway
2025-26 SOTA is "latent 3D diffusion/flow": a 3D VAE compresses shapes (vecsets, SDF tokens, or sparse voxels), a DiT trained with rectified flow denoises latents conditioned on image features, then a decoder extracts a mesh and a separate or joint stage paints PBR.

### Cited Findings
- TRELLIS.2: O-Voxel sparse voxels (arbitrary topology + PBR) -> sparse compression VAE -> structured latents; flow-matching transformer — [TRELLIS.2](https://microsoft.github.io/TRELLIS.2/)
- TripoSG: rectified-flow transformer over SDF latent tokens — [BuilderAI](https://builderai.tools/blog/single-image-to-3d-model-pipeline-2026)
- Direct3D-S2: sparse SDF volumes with spatial sparse attention for gigascale resolution — [arXiv 2505.17412](https://arxiv.org/pdf/2505.17412)
- Pixal3D: back-projects pixel features into 3D for pixel-aligned conditioning — [GitHub](https://github.com/TencentARC/Pixal3D)
- MV-Adapter: multi-view attention adapter on frozen T2I models, orthographic views — [arXiv 2412.03632](https://arxiv.org/pdf/2412.03632)
- PartPacker: dual complementary volumes; OmniPart: bbox planning + TRELLIS; HoloPart / X-Part: segment then diffusion-complete parts — see Part section sources.

### Inferences (background knowledge, not sourced in this session)
- Hunyuan3D 2.x: flow-matching DiT over a ShapeVAE vector-set (3DShape2VecSet-style) latent, then a multiview-diffusion "Paint" model baked to UV PBR.
- SF3D/TripoSR: feed-forward large reconstruction models (triplane transformer); SF3D adds UV unwrap and material estimation, with mesh extraction via differentiable isosurfacing such as FlexiCubes.
- Meshy/Tripo "smart topology" likely combines generation with learned retopology; vendors do not publish details.

### Gaps
- Primary-source confirmation for the Hunyuan3D, SF3D/FlexiCubes and commercial-tool algorithm lines above.
