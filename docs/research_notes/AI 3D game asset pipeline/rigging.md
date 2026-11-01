# Automatic Rigging & Skin Weighting for Game Characters/Creatures (state as of Nov 2026)

Scope: auto-rigging AI-generated or sculpted meshes onto a canonical skeleton per body family, with good skin weights, for Godot 4 and three.js (glTF). Constraints: Apple Silicon Mac only, free/local preferred, Blender MCP available.

Research notes: about 20 web searches. Search snippets were checked against primary repos and docs where they were available. Items marked "(unverified)" or listed under Gaps could not be confirmed.

## ML auto-rigging models: which output arbitrary vs template skeletons, can they target a canonical skeleton, licenses, hardware

### Takeaway
The open-source front runner in late 2026 is VAST's SkinTokens/TokenRig (MIT), the successor to UniRig. Its `--use_skeleton` mode keeps an existing armature and predicts only the skin weights, which is exactly the "target my canonical skeleton" mode. It also has a community Apple Silicon (MPS) port at about 35-55 s and 4 GB per character. UniRig, RigAnything, MagicArticulate and Puppeteer all predict their *own* arbitrary skeletons. Make-It-Animatable and HumanRig are fixed humanoid templates; MIA outputs Mixamo bone format. AnyTop is a *motion* generator for arbitrary skeletons, not a rigger.

### Cited Findings
**UniRig (VAST + Tsinghua, SIGGRAPH 2025)**
- Code and weights are MIT. The training data, Articulation-XL2.0, is listed as CC-BY-4.0 by a third party. — [GitHub](https://github.com/VAST-AI-Research/UniRig); [HF model card](https://huggingface.co/VAST-AI/UniRig/blob/main/README.md); [QtMeshEditor release](https://github.com/fernandotonon/QtMeshEditor/releases/tag/3.11.0)
- A GPT-like transformer predicts the skeleton hierarchy autoregressively, using "Skeleton Tree Tokenization". A second stage predicts the skin weights with bone-point cross-attention. — [GitHub](https://github.com/VAST-AI-Research/UniRig); [arXiv 2504.12451](https://arxiv.org/abs/2504.12451)
- Release status: the skeleton checkpoint trained on Articulation-XL2.0 is released. The full Rig-XL/VRoid skeleton+skin checkpoint that reproduces the paper is still marked as not released. — [GitHub](https://github.com/VAST-AI-Research/UniRig)
- Integrations: a ComfyUI-UniRig node suite, a Replicate deployment (aaronjmars/unirig-ai, a cheap cloud option), and a native C++/ONNX port in QtMeshEditor. — [RunComfy](https://www.runcomfy.com/comfyui-nodes/ComfyUI-UniRig/uni-rig-auto-rig); [Replicate](https://replicate.com/aaronjmars/unirig-ai); [QtMeshEditor](https://github.com/fernandotonon/QtMeshEditor/releases/tag/3.11.0)
- Mac: there is no official MPS support. A community PR ("Pixal3D on Mac") runs UniRig with an spconv stand-in, MPS patches and a flash_attn shim. — [PR](https://github.com/oshricohenme/local_image_to_3d/pull/1)
- Generic flash-attention replacements on MPS: `mps-flash-attn` (offers `replace_sdpa()`) and `mtlattn`. The mtlattn page warns that PyTorch MPS SDPA silently returns wrong values when B·H·Nq·Nkv exceeds about 2^32. — [mps-flash-attn](https://pypi.org/project/mps-flash-attn/); [mtlattn](https://pypi.org/project/mtlattn/0.1.0/)

**SkinTokens / TokenRig (VAST + Tsinghua, arXiv 2602.04805, ACM TOG 2026)**
- It is UniRig's successor. Skeleton and skin weights are generated as one autoregressive token sequence (Qwen3-0.6B backbone, Michelangelo point encoder, FSQ-CVAE skin decoder) and refined with RL (GRPO). The paper claims 98-133% better skinning accuracy and 17-22% better bone prediction than SOTA baselines. — [GitHub](https://github.com/VAST-AI-Research/SkinTokens); [arXiv](https://www.arxiv.org/pdf/2602.04805)
- `--use_skeleton` (default False) means "use existing skeleton (generate skin only)", and it keeps an armature found in the input. — [GitHub](https://github.com/VAST-AI-Research/SkinTokens); [skin-tokens.cpp wiki](https://github.com/localai-org/skin-tokens.cpp/wiki)
- License: MIT for the code and the HF card. A third-party review cautions that the weight license still needs to be verified separately. — [HF](https://huggingface.co/VAST-AI/SkinTokens); [stable-character-pipeline issue #46](https://github.com/SemperSupra/stable-character-pipeline/issues/46)
- Upstream requirements: an NVIDIA GPU with at least 14 GB, CUDA 12.1 or newer, flash-attn, Python 3.11 or newer. Inference needs two checkpoints, grpo_1400.ckpt and the FSQ-CVAE last.ckpt. — [GitHub](https://github.com/VAST-AI-Research/SkinTokens)
- Non-CUDA ports:
  - skin-tokens.cpp (C++23/GGML, CPU or Vulkan, Apache-2.0) — [GitHub](https://github.com/localai-org/skin-tokens.cpp)
  - chris-straka/skintokens, an Apple Silicon CLI that outputs GLB (MIT). It reports about 35-55 s per character and about 4 GB on an M4 (MPS). — [GitHub](https://github.com/chris-straka/skintokens)
  - ComfyUI-SkinToken node — [GitHub](https://github.com/Rizzlord/ComfyUI-SkinToken)

**MagicArticulate (ByteDance Seed3D, CVPR 2025)**
- Autoregressive skeleton generation plus the large Articulation-XL dataset. Skeleton inference needs about 4.6 GB VRAM. — [GitHub](https://github.com/Seed3D/MagicArticulate); [Puppeteer skinning README](https://raw.githubusercontent.com/Seed3D/Puppeteer/main/skinning/README.md)

**Puppeteer (Seed3D, NeurIPS 2025 Spotlight, arXiv 2508.10898)**
- An autoregressive skeleton is followed by skin weights, then video-guided animation through differentiable optimization. It was benchmarked against Maya's Geodesic Voxel Binding, RigNet and MagicArticulate. — [arXiv](https://arxiv.org/pdf/2508.10898); [GitHub](https://github.com/Seed3D/Puppeteer)
- License: Apache-2.0 according to GitHub. A blog claims MIT, which conflicts. — [GitHub](https://github.com/Seed3D/Puppeteer); [BrightCoding](https://www.blog.brightcoding.dev/2025/12/17/puppeteer-ai-revolution-how-automatic-rigging-and-animation-is-transforming-3d-content-creation-forever/)
- Environment: Python 3.10, torch 2.1.1, CUDA 11.8, flash-attn 2.6.3, and bpy 4.2.0 for FBX export. Skinning needs 4.2 GB VRAM.
- The skinning stage takes a given mesh (.obj) plus a rig .txt skeleton and writes `skin [vertex] [joint] [weight]` lines. In other words, the skinning module can skin a user-supplied skeleton. — [skinning README](https://raw.githubusercontent.com/Seed3D/Puppeteer/main/skinning/README.md)

**RigAnything (SIGGRAPH 2025 / TOG 44(4))**
- Template-free and autoregressive: it predicts each next joint from the shape and the previous joints. It rigs in "under a few seconds" per shape. — [arXiv 2502.09615](https://arxiv.org/abs/2502.09615)

**Make-It-Animatable (MIA, CVPR 2025, arXiv 2411.18197)**
- Outputs a rigged GLB in **Mixamo bone format** from a mesh or Gaussian splat. Options include finger bones and reset to rest pose. Code and weights are on GitHub/HF, and ComfyUI wrappers exist. — [HF](https://huggingface.co/jasongzy/Make-It-Animatable); [ComfyUI wrapper](https://github.com/speige/ComfyUI_Make-It-Animatable); [RunComfy MIA node](https://www.runcomfy.com/comfyui-nodes/ComfyUI-UniRig/mia-auto-rig)

**HumanRig (CVPR 2025)**
- A dataset of 11,434 AI-generated T-posed humanoid meshes on one uniform skeleton topology, with baselines. — [arXiv 2412.02317](https://arxiv.org/html/2412.02317v1)
- The RigAnything authors describe MIA and HumanRig as humanoid-only and dependent on template skeletons. — [RigAnything](https://arxiv.org/html/2502.09615v1)

**AnyTop (Gat et al., Tel Aviv University, SIGGRAPH 2025)**
- A diffusion model that generates **motion** for any skeleton topology from the skeleton alone (rest pose, topology, T5-embedded joint names). It generalizes to unseen skeletons and works with as few as 3 examples per topology. It is not a rigger. — [arXiv 2502.17327](https://arxiv.org/html/2502.17327v1); [code](https://github.com/Anytop2025/Anytop)

**Other 2025-2026 work**
- **AnySkel**: template-conditioned rigging for any *user-supplied* skeleton template. The output inherits the template's topology by construction, so existing animations can be reused. It is the closest academic match to "canonical skeleton per family". — [Springer](https://link.springer.com/chapter/10.1007/978-981-92-3397-7_49)
- ASMR: skeleton-mesh rigging and skinning for arbitrary meshes and skeletons, using a 2D generative prior. — [arXiv 2503.13579](https://arxiv.org/abs/2503.13579)
- Anymate: a 230K rigged-asset dataset with baselines. — [arXiv 2505.06227](https://arxiv.org/pdf/2505.06227)
- Rigel3D (May 2026): jointly generates shape and rig, rather than rigging after the fact. — [arXiv 2605.13129](https://arxiv.org/html/2605.13129)
- ViP-Rig (Jul 2026): rigging controlled by visual prompts. — [arXiv 2607.27982](https://arxiv.org/html/2607.27982)
- Also: Auto-Connect, ARMO, DRiVE, and "Animator-Centric Skeleton Generation" (2026). — [Auto-Connect](https://arxiv.org/pdf/2506.11430); [Animator-Centric](https://arxiv.org/pdf/2604.20539)
- VAST also lists AniGen (SIGGRAPH 2026), aimed at animation-ready assets. — [VAST GitHub](https://github.com/VAST-AI-Research)

### Inferences
- Recommended local ML path: put the canonical family skeleton into the mesh, scaled and placed with landmarks in Blender, then run SkinTokens `--use_skeleton` on MPS through the chris-straka port to predict weights only. This keeps one bone naming per family, so animations stay shareable.
- The free-skeleton modes (UniRig, RigAnything, MagicArticulate, TokenRig without `--use_skeleton`) give arbitrary bone counts and names. Using them with a canonical skeleton would need an extra joint-correspondence or retargeting step, which is fragile. They are best for one-off odd creatures.
- MIA's Mixamo-format output means a humanoid lands directly on a known naming. It still needs a Mixamo-to-canonical rename map.
- Cloud fallback for CUDA-only repos: Replicate (UniRig) or any hourly GPU rental. Puppeteer skinning needs only 4.2 GB, so small GPUs work.

### Gaps
- RigNet (2020) was not re-checked. It is cited only as a baseline in Puppeteer.
- No benchmarks were found comparing the MPS port's quality to CUDA upstream.
- Whether the UniRig full checkpoint was released by Nov 2026 was not confirmed.
- No measured MPS feasibility was found for MIA or Puppeteer.

## Service auto-riggers: limits, bone names, fingers, cost, formats

### Takeaway
- Mixamo is free, biped-only, FBX/DAE, and unmaintained since 2021.
- AccuRIG 2 is free and Windows-only, with humanoid bodies and fingers.
- Meshy offers humanoid, quadruped dog and Smart Rig (beta), with Mixamo-like naming and 5 API credits per rig.
- Tripo has the widest coverage: biped, quadruped, hexapod, octopod, avian, serpentine and aquatic. Biped naming presets include Mixamo, UE, Unity and VRM. It costs 25 credits per rig.
- None of them rig onto *your own* canonical skeleton. Their output always needs renaming or retargeting.

### Cited Findings
**Mixamo**
- Adobe's FAQ restricts the auto-rigger to bipedal humanoids. It is free with an Adobe ID and royalty-free for commercial use.
- You place markers by hand (chin, wrists, elbows, knees, groin). Export is FBX/DAE, and extra helper objects break the rigger.
- There is no face rig. The FAQ was last updated on 14 Sep 2021. — [Cinevva guide](https://app.cinevva.com/guides/free-character-animations-rigging); [bake3d](https://bake3d.ai/guides/mixamo-alternatives)

**Reallusion AccuRIG 2.x**
- Free, Windows 8+ only, latest 2.1.0. Exporting requires a free ActorCore account.
- It rigs the body plus a separate finger rig, with configurable finger counts. Finger voxel volumes are shrunk so that fingers lying close together still rig.
- Exports iAvatar, FBX (presets for Blender, Unity, UE, Maya and others) and USD. A free Blender add-on converts AccuRIG armatures to Rigify. — [CG Channel](https://www.cgchannel.com/2025/07/rig-and-animate-3d-characters-for-free-with-accurig-2-0/); [FileHorse](https://www.filehorse.com/download-accurig/); [Manual](https://manual.reallusion.com/AccuRig-2/2.0/09-add-motions/export.htm); [CGDive](https://cgdive.com/accurig-easy-rigging-for-humanoid-characters/)

**Meshy**
- Rig types: Humanoid, Quadruped Dog, and Smart Rig (Beta) for unusual creatures. Quadrupeds have fewer animations. — [Ludo comparison](https://ludo.ai/compare/best-ai-auto-rigging-tools); [Meshy blog](https://www.meshy.ai/blog/best-ai-auto-rigging-tool)
- Meshy says its rigs follow Mixamo naming and offers a Mixamo skeleton template on FBX export. A UE 5.7 tester found non-standard spine and clavicle names that needed manual remapping. — [Meshy Mixamo tutorial](https://www.meshy.ai/tutorials/how-to-use-mixamo-with-meshy); [StraySpark test](https://www.strayspark.studio/blog/ai-auto-rigging-showdown-2026-tripo-meshy-cascadeur-mixamo)
- Meshy's docs advise against its rigging when you need complex custom skeletons (face, tail physics). — [Meshy docs](https://docs.meshy.ai/en/webapp/guides/3d-model/rigging)
- API pricing: rig 5 credits (including walking and running), animate 3 credits per action. This is from the Meshy MCP server instructions in this environment, dated 2026-10-12, with docs at https://docs.meshy.ai/en/api/pricing. It is unclear whether quadruped rigging is available via the API. — [Ludo](https://ludo.ai/compare/best-ai-auto-rigging-tools)

**Tripo**
- Skeleton types: biped, quadruped, hexapod, octopod, avian, serpentine, aquatic, plus "others". Biped naming presets: Tripo, Mixamo, ActorCore, Unity, Unreal, VRM. Exports GLB or FBX.
- API: 25 credits per rig, 10 per retargeted animation. Rigging model v2.5-20260210 covers the non-biped types. — [Ludo](https://ludo.ai/compare/best-ai-auto-rigging-tools); [bake3d](https://bake3d.ai/guides/mixamo-alternatives)
- In UE5 tests, Tripo's naming matched Manny/Quinn closely enough that retargeting needed only a minor foot tweak. — [StraySpark](https://www.strayspark.studio/blog/ai-auto-rigging-showdown-2026-tripo-meshy-cascadeur-mixamo)

**Anything World**
- Renamed Everything Universe as of an Oct 2026 check. No details on its quadruped rigging were found. — [bake3d](https://bake3d.ai/guides/mixamo-alternatives)

**General caveat**
- Running a quadruped through a humanoid rigger turns the front legs into arms and ignores the tail. — [bake3d](https://bake3d.ai/guides/mixamo-alternatives)
- Several of these comparison sources are vendor blogs (Meshy, Tripo, Cinevva, Ludo).

### Inferences
- For humanoids, Tripo with the VRM or Mixamo naming preset, or Meshy plus a rename map, are the cheapest "good enough" services.
- AccuRIG is not usable on a Mac-only setup unless you run a Windows VM.
- For non-humanoids, Tripo's per-type skeletons are the only service option. Their bone names are not documented, so a sample export plus a hand-built bone map per type is required.

### Gaps
- Cascadeur's auto-posing and AutoPhysics and DeepMotion were not researched. They are mainly animation tools, not riggers.
- Exact Tripo quadruped and avian bone names were not found.
- AccuRIG bone names (CC_Base_?) and ActorCore EULA terms were not found.
- Mixamo finger options were not confirmed. From recollection, the skeleton LOD runs from no fingers to full fingers (unverified).

## Blender tools: Rigify, Auto-Rig Pro, Rigodotify, Voxel Heat, bone heat failure modes, Robust Weight Transfer

### Takeaway
- Free stack: Rigify metarigs (including cat, wolf, horse and shark), Rigodotify to get a clean Godot skeleton, Blender's Automatic Weights, and the free Robust Weight Transfer add-on, which implements Abdrashitov et al. 2023.
- Auto-Rig Pro Full ($50) adds Smart biped auto-placement and a Universal glTF exporter with Godot options. Its quadrupeds are placed manually.
- Voxel Heat Diffuse Skinning (about $30) "never fails" on non-watertight or multi-part meshes. These are common in AI-generated meshes.

### Cited Findings
**Auto-Rig Pro**
- Smart is "biped body recognition". Quadrupeds and creatures are set up manually, using a 3-bone IK option for digitigrade legs.
- Smart, the exporters and Remap are Full-only ($50). Lite costs $25. — [Superhive](https://superhivemarket.com/products/auto-rig-pro); [StraySpark](https://www.strayspark.studio/blog/best-blender-rigging-addons-2026)
- Export via File > Export > Auto-Rig Pro FBX/GLTF. Skeleton types are Humanoid and Universal (any skeleton).
  - GLTF requires Blender 3.4 or newer.
  - Godot root motion: enable Export Root Bone (c_traj) and Godot Root Axes.
  - Set Sampling Interpolation to Step.
  - — [ARP docs](https://www.lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html)
- An Oct 2026 changelog for v3.78.63/64 is only seen on mirror sites, so it is unverified.

**Rigodotify** (free / pay-what-you-want, v2.2.0)
- A Rigify feature set plus a converter. It adds Godot-style metarigs ("Godot Human"), strips extra Rigify bones, fixes bone order and gives engine-friendly names. You run "Prepare/Convert rig for Godot".
- Pitfalls: the zip must be renamed to Rigodotify.zip. One user reported problems on Blender 4.5.3.
- Extra bones (hair and the like) can be added, then you regenerate and convert again. — [GitHub](https://github.com/catprisbrey/Rigodotify); [itch.io](https://felesmachina.itch.io/rigodotify); [Godot forum](https://forum.godotengine.org/t/blender-rigodotify-how-to-adding-additional-bones-to-your-rig/131959)
- Alternatives: GameRig (open source), Arigify (paid). — [GitHub topic](https://github.com/topics/rigify)
- Rigify ships Cat, Wolf, Horse and Shark metarigs that you fit by hand. — [bake3d](https://bake3d.ai/guides/mixamo-alternatives)

**Blender Automatic Weights (bone heat)**
- It solves a steady-state heat equation on the surface, with a ray-visibility test from each bone. — [Cinevva](https://app.cinevva.com/guides/blender-weight-painting-problems)
- The error "Bone Heat Weighting: failed to find solution for one or more bones" has four causes: non-manifold geometry, disconnected islands, enclosed bones, and bad scale.
- Fixes: Merge by Distance, Delete Loose, Degenerate Dissolve, or scale the mesh and rig up 3-10x. — [jessyleite](https://jessyleite.dev/posts/blender-bone-heat-weighting-failed/); [Blender T45493](https://developer.blender.org/T45493); [Blender Artists](https://blenderartists.org/t/bone-heat-weighting/1626392)

**Voxel Heat Diffuse Skinning (Mesh Online, about $30)**
- Voxelizes the mesh into a solid "statue" and diffuses heat through the volume. It handles non-watertight, multi-part and layered-clothing meshes and never fails.
- v5.1.1 skins the face, fingers and toes with iterative bone heat and blends them with voxel results.
- Tips:
  - Default voxel resolution 128 is blocky on dense meshes.
  - Solidified clothes can come out with zero weights. Flip their normals before skinning, then flip them back.
  - — [Superhive](https://superhivemarket.com/products/voxel-heat-diffuse-skinning); [FAQ](https://superhivemarket.com/products/voxel-heat-diffuse-skinning/faq); [CGDive](https://addons.cgdive.com/tools/voxel-heat-diffuse-skinning)
- Free sibling: Surface Heat Diffuse Skinning, which gives bone-heat-like results that never fail. — [GitHub](https://github.com/meshonline/Surface-Heat-Diffuse-Skinning) (via [CGDive](https://addons.cgdive.com/tools/voxel-heat-diffuse-skinning))
- Another option: Adaptive Auto Skinning, which uses winding-number voxelization. — [jessyleite FAQ](https://jessyleite.dev/posts/autoskin-faq/)

**Robust Skin Weights Transfer via Weight Inpainting**
- Abdrashitov, Raichstat, Monsen and Hill (Epic Games), SIGGRAPH Asia 2023, DOI 10.1145/3610543.3626180.
- Method: copy weights only where the match is confident, using distance and normal thresholds, then inpaint the rest. — [Preprint](https://www.dgp.toronto.edu/~rinat/projects/RobustSkinWeightsTransfer/preprint.pdf)
- Free Blender add-on by SentFromSpaceVR:
  - Point mode (default, more robust; it remeshes internally via a robust-laplacian point cloud) and Surface mode.
  - Handles flipped normals.
  - An Inpaint Mask controls the transfer.
  - Reference code: rin-23/RobustSkinWeightsTransferCode.
  - — [GitHub](https://github.com/sentfromspacevr/robust-weight-transfer); [CGDive](https://addons.cgdive.com/tools/robust-weight-transfer)
- Blender 5.2+ fork: — [protoco-jp](https://github.com/protoco-jp/robust-weight-transfer)

### Inferences
- A Robust Weight Transfer pattern fits a "canonical body per family" well. Keep one hand-weighted template body per family. Fit or shrinkwrap it to each new AI mesh (proportional edits to the armature plus Surface Deform), then transfer weights robustly. This often beats bone heat on messy AI meshes.
- AI-generated meshes are often non-manifold or multi-island. So a cleanup pass (merge by distance, delete loose, optional voxel remesh proxy) should always come before Automatic Weights, with Voxel Heat or Surface Heat as the fallback.

### Gaps
- No primary docs were fetched for Blender's Data Transfer modifier or Surface Deform specifics. Both are standard built-ins in Blender.
- The Mixamo Blender add-on was not researched.

## Skinning algorithms and runtime support (LBS/DQS, max influences)

### Takeaway
Godot 4 supports 8 influences per vertex, three.js 4 by default, and glTF loaders are only required to read 4. Plan on **4 influences**. Neither engine ships dual quaternion skinning (DQS) in core: Godot has an open PR, three.js needs community shaders. So weights must look good under linear blend skinning (LBS); Blender's "Preserve Volume" won't carry over.

### Cited Findings
- **glTF influences:** JOINTS_n/WEIGHTS_n carry 4 each. JOINTS_1 holds influences 4-7. Clients only need to support one set. — [Don McCurdy gist](https://gist.github.com/donmccurdy/4cad2039360fbd7cd55d18b3f0428581)
- **Godot vs three.js:** Godot max 8, three.js max 4. Godot 4.0+ supports 8 bones per vertex. Godot 3.4 regressed when JOINTS_1 was present. — [gist](https://gist.github.com/donmccurdy/4cad2039360fbd7cd55d18b3f0428581); [Godot #54916](https://github.com/godotengine/godot/issues/54916)
- **three.js >4 influences:** PR #26222 adds bone-weight-texture skinning for arbitrary influences, but its merge status is unconfirmed. FBXLoader drops influences beyond 4. — [PR](https://github.com/mrdoob/three.js/pull/26222); [forum](https://discourse.threejs.org/t/is-the-limit-of-4-skinning-weights-per-vertex-a-hard-limit-of-webgl/801)
- **Enforcing a 4-influence limit:** Blender's glTF exporter has a Bone Influences setting. glTF-Transform's `sortPrimitiveWeights(prim, limit)` can prune to N. — [gist](https://gist.github.com/donmccurdy/4cad2039360fbd7cd55d18b3f0428581); [glTF-Transform](https://gltf-transform.dev/modules/functions/functions/sortPrimitiveWeights)
- **DQS in Godot:** not in core. Proposal #9235 asks to match Blender's Preserve Volume. PR #123647 adds a MeshSkinningMethod enum (LBS default, DQS, scaled DQS), merge status unknown. A spatial-shader demo exists in the asset library. — [Proposal](https://github.com/godotengine/godot-proposals/issues/9235); [PR #123647](https://github.com/godotengine/godot/pull/123647); [Asset lib](https://godotengine.org/asset-library/asset/2062)
- **DQS in three.js:** not in core (issue #20324). Community options: Oito DQS, and jbcom/humanoid-kit's per-bone DQS/LBS blend for r186. — [Issue](https://github.com/mrdoob/three.js/issues/20324); [humanoid-kit PR](https://github.com/jbcom/humanoid-kit/pull/7)
- **Kavan et al.:** the original DQS paper, a GPU-friendly fix for LBS candy-wrapper artifacts. — [Paper](https://team.inria.fr/imagine/files/2014/10/skinning_dual_quaternions.pdf)
- **Geodesic Voxel Binding:** the geometry-based binder in Maya, used as a baseline by Puppeteer. — [Puppeteer](https://arxiv.org/pdf/2508.10898)
- **Voxel and surface heat diffusion:** see the Blender section above. SkinCells (sparse skinning with Voronoi cells, 2025) is a newer sparse-weights approach. — [arXiv 2506.14714](https://arxiv.org/pdf/2506.14714)

### Inferences
- Use LBS-friendly topology: extra edge loops at elbows, knees and wrists. Use twist or roll helper bones in the canonical spec, for example upper-arm and forearm twist, to avoid candy-wrapper artifacts without DQS.
- Cap at 4 influences and normalize at export so assets behave the same in Godot and three.js.

### Gaps
- Bounded biharmonic weights (Jacobson 2011) and NeuroSkinning were not re-sourced in this pass. No sources found on current tooling for them in Blender.

## Canonical skeleton spec and bone maps (Godot, VRM, Mixamo, UE), optional chains, sockets

### Takeaway
- Humanoids: build on Godot's SkeletonProfileHumanoid (56 bones, 4 groups, Root+Hips) via a BoneMap at import. VRM 1.0's 15 required and optional humanBones are a good cross-engine naming contract (three-vrm works in three.js).
- Non-humanoid families: define a custom SkeletonProfile resource per family, exported from a Skeleton3D in the editor.
- Caveat: BoneMap is only an import setting and cannot be set from script.

### Cited Findings
- **Godot BoneMap retargeting:** set in Advanced Import > Skeleton3D > Retarget > bone_map. SkeletonProfileHumanoid auto-maps bones. — [Godot docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- **Retargeting import options:**
  - "Remove Tracks" strips position tracks except root_bone and scale_base_bone (Root, Hips).
  - The "Rest Fixer" overwrites bone rests to the profile's reference pose.
  - To keep original rests, the docs point to the realtime retarget module.
  - — [Godot docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- **SkeletonProfile API:** properties bone_size, group_size, root_bone, scale_base_bone. Methods include get_bone_name, get_bone_parent, set_bone_tail and others. SkeletonProfileHumanoid has 56 bones and 4 groups. Custom profiles can be exported from a Skeleton3D via the viewport Skeleton3D menu. — [SkeletonProfile docs](https://docs.godotengine.org/en/stable/classes/class_skeletonprofile.html)
- **Scripting limit:** a third-party add-on author claims that in Godot 4.4-4.7.2 no class exposes bone_map to script; it is an import setting only. Godot ships RetargetModifier3D. The add-on saves BoneMap .tres files and writes a mirroring SkeletonProfile. — [Skeleton Retarget (itch)](https://thatindiesphinx.itch.io/skeleton-retarget)
- **VRM 1.0 humanoid:**
  - Format: `extensions.VRMC_vrm.humanoid.humanBones.{bone}.node`, with each bone used once.
  - 15 required bones: hips, spine, head, and left/right upperLeg, lowerLeg, foot, upperArm, lowerArm, hand.
  - Optional: chest, upperChest, neck, eyes, jaw, shoulders, fingers, toes.
  - VRM 0.x required 17 bones, plus T-pose, -Z facing and no local rotation.
  - — [VRM 1.0 humanoid.md](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md); [VRM 0.0](https://github.com/vrm-c/vrm-specification/blob/master/specification/0.0/README.md)
- **Naming for ML and services:** MIA outputs Mixamo names. Tripo offers Mixamo, UE, Unity and VRM presets. — [HF MIA](https://huggingface.co/jasongzy/Make-It-Animatable); [Ludo](https://ludo.ai/compare/best-ai-auto-rigging-tools)

### Inferences
- Suggested spec design, as a JSON/YAML file per family:
  - Godot profile-compatible core bone names. For humanoids, use the SkeletonProfileHumanoid names (Hips, Spine, Chest, UpperChest, Neck, Head, LeftUpperArm...), which line up 1:1 with VRM camelCase.
  - Parent list and rest-pose reference (T- or A-pose).
  - An `optional_chains` block: Tail_01..N, Wing_L/R arm-like chains (humerus, radius, hand, plus finger or feather bones), EarL/R, Jaw, Tongue.
  - Non-deforming `socket_` bones: hand_R_socket, head_socket, back_socket. These become BoneAttachment3D in Godot and bone children in three.js.
  - Alias maps from Mixamo (`mixamorig:Hips`), Tripo, Meshy and UE (`pelvis`, `spine_01`, `clavicle_l`) names.
- Because BoneMap can't be scripted, the agent should *rename bones in Blender to the canonical names before export*. Then the import BoneMap is either trivial or can be a pre-saved .tres referenced in the `.import` file. (Editing `.import` files directly is plausible but unverified.)
- Optional chains should be leaf chains under stable core bones. Core humanoid retargeting then still works, and extra chains get procedural motion (SpringBoneSimulator3D or jiggle) or family-specific clips.

### Gaps
- Exact UE5 Manny bone list and Mixamo full bone list were not fetched. They are well known but not sourced here.
- Whether `.import` file `bone_map` sub-resources can be authored by hand was not confirmed.
- Godot SpringBoneSimulator3D details were not researched.

## Non-humanoid creatures (quadruped, avian, serpent): templates and auto-rig options

### Takeaway
Few tools auto-place joints for non-humanoids.
- **Tripo**: its typed skeletons (quadruped, avian, serpentine, etc.) are the only service option.
- **Meshy**: has quadruped dog and Smart Rig beta.
- **ML**: the template-free models (TokenRig, UniRig, RigAnything, Puppeteer) handle arbitrary creatures but produce arbitrary skeletons. Their skeleton-given skinning modes, TokenRig `--use_skeleton` and Puppeteer's skinning stage, are the way to keep a canonical quadruped, avian or serpent template.
- **Blender**: templates come from Rigify animal metarigs or ARP Universal, placed manually or through landmark scripts.

### Cited Findings
- Tripo skeleton types and the v2.5-20260210 model. — [Ludo](https://ludo.ai/compare/best-ai-auto-rigging-tools); [bake3d](https://bake3d.ai/guides/mixamo-alternatives)
- Meshy Quadruped Dog and Smart Rig (beta). — [Meshy blog](https://www.meshy.ai/blog/best-ai-auto-rigging-tool)
- Rigify Cat, Wolf, Horse and Shark metarigs. ARP non-Smart manual rigs for horses and dogs, and 3-bone IK for digitigrade legs. — [bake3d](https://bake3d.ai/guides/mixamo-alternatives); [Superhive ARP](https://superhivemarket.com/products/auto-rig-pro)
- UniRig, RigAnything and Puppeteer are evaluated on diverse categories (Articulation-XL2.0, ModelsResource). — [Puppeteer](https://arxiv.org/pdf/2508.10898); [RigAnything](https://arxiv.org/abs/2502.09615)
- Topology-agnostic motion: AnyTop, and text-to-animal motion (arXiv 2512.10352). These can animate custom-family skeletons. — [AnyTop](https://anytop2025.github.io/Anytop-page/); [arXiv 2512.10352](https://arxiv.org/pdf/2512.10352)

### Inferences
- Hybrid recipe for creatures:
  1. Run UniRig or TokenRig *free mode* just to get joint-position landmarks (shoulders, hips, tail tip, wing tips).
  2. Snap the canonical family template bones to those landmarks in bpy.
  3. Re-skin with TokenRig `--use_skeleton` or with Blender heat, voxel or robust transfer.
- This hybrid is untested. It combines the documented capabilities above.

### Gaps
- No public quadruped or avian equivalent of SkeletonProfileHumanoid was found.
- No benchmark was found for wings or tails specifically.

## Headless scripting via Blender Python (bpy) and MCP

### Takeaway
Most of the pipeline is scriptable through bpy, which a Blender MCP can drive. ML models run as separate Python or CLI processes, communicating through GLB files.

### Cited Findings
- Puppeteer installs `bpy==4.2.0` as a pip module for FBX export, so bpy can run headless as a Python module. — [Puppeteer README](https://raw.githubusercontent.com/Seed3D/Puppeteer/main/README.md)
- Rigodotify, ARP and Rigify expose their actions as operators/buttons ("Generate Rig", "Prepare Rig for Godot", ARP export). These are therefore operator calls in bpy, although some need specific context. — [Rigodotify](https://github.com/catprisbrey/Rigodotify); [ARP docs](https://www.lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html)
- Robust Weight Transfer depends on Python packages (libigl, robust-laplacian) installed into Blender's Python with `pip install --no-deps --target deps`. — [GitHub](https://github.com/sentfromspacevr/robust-weight-transfer)

### Inferences
These are from general bpy knowledge, not fetched docs in this pass, so verify them via the Blender MCP's bundled API docs:
- Automatic weights: `bpy.ops.object.parent_set(type='ARMATURE_AUTO')`.
- Mesh cleanup: `bpy.ops.mesh.remove_doubles` and `delete_loose`.
- Limit influences: `bpy.ops.object.vertex_group_limit_total(limit=4)`, then `vertex_group_normalize_all`.
- Data Transfer modifier with `use_vert_data=True` and `data_types_verts={'VGROUP_WEIGHTS'}`.
- glTF export: `bpy.ops.export_scene.gltf(...)`, including export_all_influences and similar flags.
- Bone renames go through `armature.data.bones[...].name`. Vertex groups follow bone renames automatically.
- Template fitting is armature edit-mode `edit_bones[...].head/tail` assignments driven by landmark coordinates.
- Rigify generation is `bpy.ops.pose.rigify_generate()`. It needs the metarig active in pose or object context.
- Context-sensitive operators (Rigify, ARP Smart, which needs interactive marker placement) are the riskiest to drive headlessly. ARP Smart is likely the least automatable.

### Gaps
- Operator names above are not verified against current Blender 5.x docs in this pass.
- ARP Smart scripting API not researched.
- Voxel Heat add-on operator names not researched.
