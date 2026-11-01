# Shared family bases, not generators, make assets customisable

The tool that decides whether game0 can make "any customisable 3D asset" is not the generator. It is a **per-family contract**: one base mesh topology, one canonical skeleton, named sockets, and a dye-mask convention that every generated asset is forced onto. AI generators (Meshy, Tripo, TRELLIS.2, Hunyuan3D) only supply *shape and texture input*. glTF morph targets must share the base's vertex count and order, so a slider, a body morph or a fitted garment can only work across peoples if each people is **wrapped onto one shared base** rather than generated as its own mesh. game0's current Meshy pipeline (a separate Meshy base and Mixamo-named rig per people, with attachments placed by hand) cannot share morphs or conforming clothing across Galeborne, Anchorkin and Rootwardens until that wrap step exists. On an Apple Silicon Mac, a mostly free stack now exists for every stage. It is built from three kinds of part. The heavy ML steps are TRELLIS.2 via an MPS port (MIT), SkinTokens weight prediction via an MPS port (MIT) and Hunyuan3D-Paint via MLX, which is region-restricted. The bulk of the work runs as deterministic Blender Python: wrapping by non-rigid ICP, robust weight transfer, Surface Deform morph baking and glTF export. The base assets are MakeHuman/MPFB2 (CC0), Quaternius UAL (CC0) and Godot's SkeletonProfileHumanoid. Paid services are worth it in three places: Meshy (already connected) as the default generator, rigger and texturer for cents per asset; Tripo for named-part segmentation and non-humanoid rig types; and pay-per-run cloud GPUs (fal, Replicate) for the CUDA-only research models. The single biggest licensing fork is the user's country. Tencent's Hunyuan3D, Hunyuan3D-Part and HY-Motion licences exclude the EU, UK and South Korea, and the exclusion extends to their outputs.

## One contract per body family is what makes everything else automatic

Every shipped character system the notes cover uses the same idea, with different storage. The Sims 4 mixes three morph types on one shared body. Bone deltas change proportions and are "the only acceptable way to change height". BGEO vertex deltas, matched by vertex ID, shape faces. DMaps store morphs as a bitmap read through a second UV channel, so they work on any mesh that shares that UV1, including clothing and all LODs ([Mod The Sims](https://modthesims.info/showthread.php?t=613057)). Final Fantasy XIV authors most gear once on a master body and reshapes it per race at runtime through a "pre-bone deformer" file: a 4x3 matrix per bone per race, composed along a parent chain of races ([physis docs](https://docs.rs/physis/latest/physis/pbd/struct.PreBoneDeformer.html); [XIV-Instant-Edit wiki](https://github.com/link-0402/XIV-Instant-Edit/wiki/Racial-Scaling)). Roblox gets runtime auto-fit by giving every body **one standard cage whose UVs are identical**. Garments carry an inner and an outer cage, and vertices are matched by UV coordinate, so deleting cage vertices or changing cage UVs breaks equipping ([Roblox cage meshes](https://create.roblox.com/docs/art/modeling/cage-meshes); [apply deformation](https://create.roblox.com/docs/art/modeling/cage-meshes/apply-deformation)).

The lesson for game0 is that the **body family** is the unit of design, not the asset. A family should be defined by a small set of versioned files:

| File | What it pins |
|---|---|
| `base.glb` | The shared base mesh (fixed vertex order, UV0 for texture, optional UV1 for DMap-style transfer) |
| `skeleton.json` | Canonical bone names, parents and rest pose, plus optional leaf chains (tail, wings, ears, jaw) and non-deforming `socket_*` bones |
| `morphs.json` | Slider names, which are bone-driven and which are vertex-driven, and per-people clamp ranges |
| `regions.json` | Body-region vertex groups and the bitmask used to hide body under clothing |
| `dye.json` | Mask channel meanings |

Each people then becomes a **"signature" shape key** on the shared base plus a bone-offset preset. This is FFXIV's racial deform crossed with a Sims 4 preset. Player sliders sit on top of that signature.

The split between bones and blend shapes should follow the Sims rule. **Bones carry proportions**: height, limb length, head, hand and foot size, tail length. **Blend shapes carry surface**: muscle, belly, face features. Engine evidence supports this split, with one caveat. A Godot PR argued that proportional character creators were "not currently possible in Godot without major animation artifacting", because scaling a parent bone does not correct its children's translation. Its merge status is unconfirmed ([godot #83903](https://github.com/godotengine/godot/pull/83903)). Godot's SpringBoneSimulator3D also warns against scaled skeletons and bones ([Godot docs](https://docs.godotengine.org/en/4.4/classes/class_springbonesimulator3d.html)). So proportions should be **rest-pose translation offsets** (bone length), with uniform scale only on leaf bones.

Morph count is not a hard limit in three.js. Since r133, WebGL2 stores morphs in a texture array with one layer per target ([three.js #14441](https://github.com/mrdoob/three.js/issues/14441)). That texture costs vertex count × targets in VRAM, though, and one report saw meshes with more than 241 shape keys fail on mobile ([three.js forum](https://discourse.threejs.org/t/overcoming-morph-target-limitations/14937)). The design that avoids every limit is to **bake identity sliders into the mesh when the player confirms them**, and keep only expressions (ARKit 52) and correctives as live morph targets.

Skinning constraints are the same in both engines in practice. glTF clients only have to read 4 influences, three.js uses 4 and Godot 4 supports 8. Neither ships dual-quaternion skinning in core, so weights must look right under linear blend skinning ([McCurdy gist](https://gist.github.com/donmccurdy/4cad2039360fbd7cd55d18b3f0428581); [Godot proposal #9235](https://github.com/godotengine/godot-proposals/issues/9235); [three.js #20324](https://github.com/mrdoob/three.js/issues/20324)). The canonical skeleton should therefore include **twist bones** in the forearms and upper arms, and every export should be capped at 4 influences, using Blender's exporter setting or glTF-Transform's `sortPrimitiveWeights` ([glTF-Transform](https://gltf-transform.dev/modules/functions/functions/sortPrimitiveWeights)).

For humanoid naming, Godot's **SkeletonProfileHumanoid** (56 bones, Root + Hips) is the natural contract. Its names line up with VRM 1.0's 15 required humanBones ([Godot SkeletonProfile](https://docs.godotengine.org/en/stable/classes/class_skeletonprofile.html); [VRM humanoid spec](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)). One gotcha shapes the whole skill. The Godot BoneMap is an import setting that a third-party add-on author says cannot be set from script through Godot 4.7 ([Skeleton Retarget](https://thatindiesphinx.itch.io/skeleton-retarget)). The skill must therefore **rename bones to canonical names in Blender before export**, and keep alias maps for Mixamo (`mixamorig:Hips`), Meshy, Tripo and UE input.

## Generation: Meshy stays the default, and TRELLIS.2 on MPS is the free challenger

The 2025–26 state of the art is latent 3D diffusion or flow. A 3D VAE compresses shapes into vector sets, SDF tokens or sparse voxels. A rectified-flow transformer denoises those latents conditioned on the image, and a later stage paints PBR. TRELLIS.2, for example, compresses a 1024³ asset to about 9,600 tokens on sparse "O-Voxels" that handle open surfaces ([TRELLIS.2](https://microsoft.github.io/TRELLIS.2/)). Pixal3D, a SIGGRAPH 2026 model built on the TRELLIS.2 backbone, back-projects pixel features into 3D for near-reconstruction fidelity ([Pixal3D](https://github.com/TencentARC/Pixal3D)).

No neutral current leaderboard exists. 3D Arena's last verified top dates from March 2025 ([arXiv 2506.18787](https://arxiv.org/html/2506.18787v1)), and the 2026 boards are run by vendors with a stake in the result. One VLM-scored board ranks Hunyuan 3D Pro > Rodin 2 > Meshy 6 > Tripo 2.5 > TRELLIS 2 ([Pixazo](https://www.pixazo.ai/leaderboard/ai-3d-model-generation)). None of these benchmarks tests painterly stylised input, so a **small in-house A/B on game0's own concept art is the only trustworthy ranking**.

| Rank | Option | Why | Mac / cloud | Commercial licence |
|---|---|---|---|---|
| 1 | **Meshy 7.1 / 6 / t2.5 (MCP connected)** | Multi-view input, A/T-pose control, Smart Topology from 100 to 300K faces; 5–35 credits per asset ([Meshy pricing](https://docs.meshy.ai/en/api/pricing); [3D AI Studio](https://www.3daistudio.com/blog/hitem3d-vs-meshy-vs-tripo-comparison)) | Cloud | Paid plans are "Private", you own the outputs; the free plan is CC BY 4.0 ([Meshy docs](https://docs.meshy.ai/en/webapp/pricing)) |
| 2 | **TRELLIS.2-4B via trellis-mac** | Consensus open leader; textured PBR GLB in about 3.5 min on an M4 Pro 24 GB, about 18 GB peak memory ([trellis-mac](https://github.com/shivampkumar/trellis-mac/wiki); [Show HN](https://news.ycombinator.com/item?id=47828896)) | **Runs on MPS**; fal TRELLIS 2 about $0.05 per run (another source says about $0.30) ([fal](https://fal.ai/pricing)) | MIT ([HF](https://huggingface.co/microsoft/TRELLIS.2-4B)) |
| 3 | **Tripo P1 / H3.1** | All-in smart mesh at $0.30–0.50; "generate in parts" +20 credits; quad option ([Tripo pricing](https://developers.tripo3d.ai/en/pricing)) | Cloud | Plan terms not retrieved; check before use |
| 4 | Hunyuan3D 3.1 (hosted only) | High scores on vendor boards; fal $0.225–0.375 per run ([fal](https://fal.ai/hunyuan-3d)) | Cloud | Hosted terms not researched; the open 2.x licence excludes the EU, UK and South Korea |
| 5 | Hunyuan3D 2.1 (open) | Shape plus PBR paint; MPS forks exist but run about 5–10x slower than CUDA ([Brainkeys](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md)); fal $0.05 | MPS (slow) | Tencent community licence: **excludes the EU, UK and South Korea, including outputs**; more than 1M MAU needs a separate licence ([LICENSE](https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE)) |
| 6 | Rodin Gen-2 | Quad-topology specialist (4K–50K face tiers) for hero assets; official API needs a Business plan, resellers charge about $0.30–0.40 ([Hyper3D](https://developer.hyper3d.ai/api-specification/rodin-generation-gen2); [WaveSpeed](https://wavespeed.ai/models/hyper3d/rodin-v2/image-to-3d)) | Cloud | Not retrieved |
| — | Pixal3D | Promising, but its licence is contradictory: MIT on GitHub, EU-gated on Hugging Face, called "academic-only" by a wrapper ([HF](https://huggingface.co/TencentARC/Pixal3D); [ComfyUI-Pixal3D](https://github.com/PozzettiAndrea/ComfyUI-Pixal3D)) | — | **Avoid until clarified** |
| — | TripoSG, Stable Fast 3D, SPAR3D | Lighter fallbacks. TripoSG is geometry-only (MIT). SF3D and SPAR3D are under the Stability Community licence, free under $1M revenue ([HF SF3D](https://huggingface.co/stabilityai/stable-fast-3d)) | SF3D MPS is "experimental" | As stated |

**Input quality matters more than model choice** for a painterly look. Meshy's own guide says multi-view works best for character sheets in neutral A- or T-pose with consistent style and scale ([Meshy tutorial](https://www.meshy.ai/tutorials/multi-view-image-to-3d)). MV-Adapter's character prompts call for "even lighting" with no background ([MV-Adapter](https://github.com/huanngzh/MV-Adapter)). Every generator bakes concept-art shadows into the albedo, and delighting afterwards cannot recover what a shadow covered ([3D Red Box Studio](https://www.3dredboxstudio.com/blog/your-ai-albedo-has-the-light-baked-in)). The skill should therefore generate **flat-lit turnarounds**. game0 already produces front/side/back sheets this way.

### Parts: generate attachables separately, and use segmentation for cleanup

Swappable parts need watertight, completed geometry. A plain cut leaves holes where parts used to touch. The research ranking from the CubePart paper puts **HoloPart and OmniPart** best on single-part quality. PartCrafter and PartPacker only control the number of parts ([CubePart](https://arxiv.org/html/2605.28763)).

| Rank | Option | Notes | Mac | Licence |
|---|---|---|---|---|
| 1 | **One isolated object per generation** (the current meshy skill practice) | Clean, watertight, and cheap with Meshy t2/t2.5 (5–15 credits) | Cloud | Meshy plan |
| 2 | Tripo Smart Segment | Named parts with a text hint, about $0.55 on an existing model; part names pass through to remesh ([ComfyUI docs](https://docs.comfy.org/built-in-nodes/TripoSmartSegmentNode); [fal](https://fal.ai/models/tripo3d/tripo/segment/api)) | Cloud | Not retrieved |
| 3 | Hunyuan3D-Part (P3-SAM + X-Part) | Native 3D segmentation trained on 3.7M shapes, then diffusion completes each part; the open release is "light" ([HF](https://huggingface.co/tencent/Hunyuan3D-Part)) | **CUDA 12.1 only**: rent a GPU | Tencent licence, with territory exclusions |
| 4 | fal Hunyuan part split | $0.45 per run ([fal](https://fal.ai/hunyuan-3d)) | Cloud | Tencent hosted terms |
| 5 | Meshy Auto Split | 10 credits; aimed at printing; rejects low-poly and t2/t2.5 sources ([Meshy docs](https://docs.meshy.ai/api/auto-split.md)) | Cloud | Meshy plan |

## Wrapping, rigging and skinning reduce to "fit the template, then transfer"

### Wrapping and retopology: wrap peoples, retopologise only props

None of the automatic retopology tools reliably produces deformation loops around the eyes, mouth and shoulders. A shared-topology system sidesteps the problem: people variants are **wrapped from the base onto the AI sculpt**, never retopologised, because retopology destroys vertex order. The reference commercial wrapper, Faceform Wrap, costs $570 for an indie perpetual licence but runs only on Windows and Linux ([CG Channel](https://www.cgchannel.com/2025/12/faceform-releases-wrap-2025-11-and-wrap4d-2025-11/)). The free Mac route is trimesh's `nricp_amberg`, the Amberg 2007 optimal-step non-rigid ICP, or `nricp_sumner`. Both take landmarks ([trimesh docs](https://trimesh.org/trimesh.registration.html)). The proposed sequence (an inference, built from standard features):

1. Align the sculpt rigidly with Procrustes on landmarks.
2. Run NICP with about 20–60 landmarks.
3. Refine with Blender Shrinkwrap plus Corrective Smooth.
4. Save the result as the people's signature shape key.

BWrap does the same inside Blender. Its free tier is limited and the full version is €29.99 ([BWrap](https://superhivemarket.com/products/bwrap)).

| Stage | Rank 1 (free) | Rank 2 | Paid upgrade | Avoid on Mac |
|---|---|---|---|---|
| Wrap people onto base | **trimesh NICP + bpy refine** (MIT library) | BWrap free tier | BWrap €29.99 | Faceform Wrap (no macOS) |
| Retopology of props and attachments | **QuadriFlow** (built into Blender), Instant Meshes (free) ([Mixar](https://www.mixar.app/compare/quad-remesher); [instantmeshes](https://instantmeshes.com/vs-quadriflow/)) | Meshy remesh / Smart Topology at generation time | Quad Remesher (about $79; price sources conflict) | MeshAnything V1 (non-commercial) |

The base mesh itself should be **MakeHuman/MPFB2**. Its base mesh, targets, rigs, weights and proxies are **CC0**. The FAQ explicitly allows building your own character generator from them and notes that one already exists for Godot. Only the add-on code is GPL or AGPL ([MPFB FAQ](https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html); [licence](https://static.makehumancommunity.org/about/license.html)).

The alternatives are each blocked for an in-game creator:

- **Reallusion** forbids using its base or content in "any character generation system" ([EULA](https://www.reallusion.com/Content/EULA/AP/EULA_AP.htm)).
- **SMPL / SMPL-X** are licensed for non-commercial research only ([licence](https://smpl-x.is.tue.mpg.de/modellicense.html)).
- **Daz** now sells per-product interactive add-ons ([Daz EULA](https://www.daz3d.com/eula)).
- **HumGen3D** forbids sharing raw meshes ([licence FAQ](https://help.humgen3d.com/license)).
- **MetaHuman** can now be used in Godot, but it needs a UE seat once revenue exceeds $1M, bans AI training, and does not fit a stylised look ([metahuman.com](https://www.metahuman.com/license)).

Non-humanoid families (creatures, ships) have no CC0 equivalent. They need a hand-made base per family.

### Rigging: keep one canonical skeleton per family

Most riggers, both ML and service, output **their own** skeleton. A canonical family skeleton only survives with the "skeleton given, predict weights" mode.

| Rank | Option | Fits a canonical skeleton? | Mac | Licence |
|---|---|---|---|---|
| 1 | **Template fit in bpy** (place family bones from landmarks; Rigify metarigs including cat, wolf, horse and shark; Rigodotify converts to a clean Godot rig) ([Rigodotify](https://github.com/catprisbrey/Rigodotify)) | Yes, by construction | Native | Rigify ships with Blender; Rigodotify is free / pay what you want |
| 2 | **SkinTokens/TokenRig `--use_skeleton`** (UniRig's successor; claims 98–133% better skinning than earlier work) ([GitHub](https://github.com/VAST-AI-Research/SkinTokens)) | Yes: it keeps the armature and predicts skin only | **MPS port**: about 35–55 s and 4 GB on an M4 ([chris-straka/skintokens](https://github.com/chris-straka/skintokens)) | Code MIT; verify the weight licence separately ([issue #46](https://github.com/SemperSupra/stable-character-pipeline/issues/46)) |
| 3 | Meshy rig (web free, API 5 credits) | No: Mixamo-like naming, and a tester found non-standard spine and clavicle names ([StraySpark](https://www.strayspark.studio/blog/ai-auto-rigging-showdown-2026-tripo-meshy-cascadeur-mixamo)) | Cloud | Meshy plan |
| 4 | Tripo rig (25 credits; biped, quadruped, hexapod, avian, serpentine, aquatic; Mixamo, UE, VRM and Unity naming presets) ([Ludo](https://ludo.ai/compare/best-ai-auto-rigging-tools)) | Humanoid presets map well; creature bone names are undocumented | Cloud | Not retrieved |
| 5 | UniRig, RigAnything, MagicArticulate, Puppeteer | Arbitrary skeletons; useful as **landmark finders** for odd creatures. Puppeteer's skinning stage accepts a supplied skeleton ([Puppeteer](https://raw.githubusercontent.com/Seed3D/Puppeteer/main/skinning/README.md)) | UniRig: community MPS shim only; Puppeteer needs CUDA 11.8; UniRig on Replicate ([Replicate](https://replicate.com/aaronjmars/unirig-ai)) | UniRig MIT; Puppeteer Apache-2.0 |
| 6 | Auto-Rig Pro Full ($50) | Smart auto-placement for bipeds only; the Universal glTF exporter has Godot root-motion options ([ARP docs](https://www.lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html)) | Native | Paid add-on |
| — | Mixamo, AccuRIG 2 | Biped only; AccuRIG is **Windows only** ([CG Channel](https://www.cgchannel.com/2025/07/rig-and-animate-3d-characters-for-free-with-accurig-2-0/)) | Mixamo is web-based | Mixamo royalty-free |

Two notes on creatures. A humanoid rigger turns a quadruped's front legs into arms and ignores the tail ([bake3d](https://bake3d.ai/guides/mixamo-alternatives)). AnySkel, a template-conditioned rigger for user-supplied skeletons, is the academic idea closest to "canonical skeleton per family", but no usable release was found ([Springer](https://link.springer.com/chapter/10.1007/978-981-92-3397-7_49)).

### Skinning: transfer from a hand-weighted family template

AI meshes are often non-manifold or split into islands, and those are exactly the cases where Blender's bone-heat Automatic Weights fails ([jessyleite](https://jessyleite.dev/posts/blender-bone-heat-weighting-failed/)). The strongest pattern for a family system is to **hand-weight one template body per family once**, then transfer its weights with Epic's robust skin-weight transfer, published at SIGGRAPH Asia 2023. That method copies weights only where distance and normal agree, and fills the rest by inpainting ([paper](https://www.dgp.toronto.edu/~rinat/projects/RobustSkinWeightsTransfer/preprint.pdf)). A free Blender add-on implements it ([sentfromspacevr](https://github.com/sentfromspacevr/robust-weight-transfer)), and a Godot-oriented fork exists ([V-Sekai](https://github.com/V-Sekai/godot-robust-skin-weights-transfer)).

Ranked order:

1. **Shared topology**: wrapped peoples inherit the base's weights exactly, so there is nothing to transfer.
2. **Robust weight transfer**, for gear and odd meshes.
3. **SkinTokens skin-only** prediction.
4. Blender Automatic Weights after cleanup: Merge by Distance, Delete Loose, scale up 3–10x.
5. **Voxel Heat Diffuse Skinning** (about $30), which "never fails" on multi-part or layered meshes. Its free sibling is Surface Heat Diffuse ([Superhive](https://superhivemarket.com/products/voxel-heat-diffuse-skinning)).

## Customisation is baked in Blender so the engines only set weights

### Morphs and faces

Identity sliders are vertex deltas on the shared head and body, or bone offsets. Expressions should follow **ARKit 52**: generate them once on the neutral base, then reapply the base-to-expression delta on top of each people's signature shape. For big shape changes such as snouts or beaks, the inference is to use deformation-gradient (Sumner–Popović) transfer instead of raw deltas.

The tool options, in order:

| Tool | What it does | Cost |
|---|---|---|
| **Faceit** | Landmark fitting plus the 52 ARKit shape keys ([Faceit](https://superhivemarket.com/products/faceit)) | Paid |
| ARKit Blendshape Baker | Bakes the 52 shapes from a Rigify face rig ([GitHub](https://github.com/tsikerdekis/ARKit-Creator-Blender-Addon/)) | Free |
| arkit-blendshape-tool | GLB-to-GLB transfer of the 52 shapes ([GitHub](https://github.com/digitalp/arkit-blendshape-tool)) | Free |

Lip sync on a Mac should use **Rhubarb** (MIT, and its output belongs to you) through the godot-baked-lipsync plugin ([Rhubarb](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md); [plugin](https://github.com/fbcosentino/godot-baked-lipsync)). NVIDIA Audio2Face's weights are commercially licensed but ship as ONNX-TRT, which effectively means NVIDIA only ([HF](https://huggingface.co/nvidia/Audio2Face-3D-v3.0)).

Hair, feathers and foliage on a morphing head follow the same rule. Bind each card mesh with Surface Deform and bake one **same-named shape key** per head morph ([Diffeomorphic note](https://bitbucket.org/Diffeomorphic/import_daz/issues/292/strange-morph-deformation-when-converting)). The cards can come from Daniel Bystedt's free Geometry Nodes setup ([CG Channel](https://www.cgchannel.com/2024/03/daniel-bystedts-free-blender-add-on-creates-hair-cards-from-curves/)).

### Gear fitting: the Outfit Studio loop, scripted

Clothing should be fitted at bake time, the way BodySlide/Outfit Studio does it. The garment is fitted to the base body, every body slider is conformed, clipping is fixed per slider, and bone weights are copied from the reference ([ousnius wiki](https://github.com/ousnius/BodySlide-and-Outfit-Studio/wiki/Conversion-references-and-using-them)). In Blender, the per-key loop is: Surface Deform bind at basis, set one body key to 1.0, Apply as Shape Key, reset, repeat. Community scripts already automate it ([ShapeKeyWrap](https://github.com/cgvirus/ShapeKeyWrap); [Blender manual](https://docs.blender.org/manual/id/latest/modeling/modifiers/deform/surface_deform.html)).

Each garment then ships with:

- robust-transferred weights;
- one corrective key per body key, named identically;
- a shrinkwrap "push-out" pass to remove penetration;
- `slot`, `layer`, `covers` (a region bitmask) and `hides` metadata.

Runtime is trivial. Godot and three.js set the same blend-shape weights on the body and on every garment. People differences that come from bone offsets need no garment work at all, because the skin follows the bones.

Some cases fall back to other methods:

- **Extremes**, such as a heavy Anchorkin against a slim Galeborne, get MetaHuman-style discrete sizes. Epic's own advice is to add a size rather than more interpolation points ([UE Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ChaosSizedOutfitSource?application_version=5.7)).
- **Loose cloth** needs cage coordinates. Harmonic coordinates are non-negative where mean-value coordinates go negative in concave cages ([Pixar memo](https://graphics.pixar.com/library/HarmonicCoordinates/paper.pdf)).
- **Runtime Roblox-style cage wrapping** has no open Godot or three.js implementation, so it is out of scope.

Rigid gear works differently. Armour plates, weapons, horns and masks get **100% weight to one bone, or a socket**, and are excluded from conforming. CC4 does the same for belts ([Reallusion manual](https://manual.reallusion.com/Character-Creator-4/Content/ENU/4.0/08_Cloth/Disabling_Cloth_Conforming_Feature.htm)). One socket offset only works across bodies if bone rolls are normalised. Godot's fix is the Rest Fixer with "Overwrite Axis" at import ([Godot forum](https://forum.godotengine.org/t/best-practice-for-attaching-weapons-items-to-a-characters-hand-across-many-animations-godot-4/141270)). Godot 4.6 restored TwoBoneIK3D and ChainIK3D, which handle the off hand on two-handed grips ([Godot blog](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)). In three.js, all garments should share one skeleton: either export them in one glTF, or call `garment.bind(bodySkeleton)` ([three.js docs](https://threejs.org/docs/pages/SkinnedMesh.html)).

AI garment generators are no shortcut yet. They are sewing-pattern research models (ChatGarment, GarmentCode, GarmentDiffusion) whose output is a simulation mesh, not skinned game gear ([ChatGarment](https://arxiv.org/pdf/2412.17811)). Image-to-3D generators fuse clothing into the body, so they suit **rigid accessories** better than cloth. Marvelous Designer is now subscription-only: $39/mo or $280/yr, with macOS support and glTF export ([MD support](https://support.marvelousdesigner.com/hc/en-us/articles/47358269350041-What-kind-of-licenses-does-Marvelous-Designer-offer)). Blender cloth is the free route.

### Dye masks

The standard is one RGB(A) mask: R primary, G secondary, B accent, A an optional fourth channel. The shader replaces hue but keeps the base luminance, so painted shading survives ([Feitizo devlog](https://feitizogames.itch.io/pack/devlog/87508/secondary-color-shader); [Godot forum](https://forum.godotengine.org/t/best-way-to-change-colors-on-a-character-and-access-the-shader-parameters-from-the-script/132786)). Two rules decide where the dye maths lives:

- **three.js WebGPURenderer does not support ShaderMaterial or onBeforeCompile.** The dye has to be written in TSL `colorNode` ([Utsubo](https://www.utsubo.com/blog/webgpu-threejs-migration-guide)).
- The skill should keep **identical dye and toon-ramp maths** in that TSL node and in a Godot `fragment()`, so a dye looks the same in both runtimes.

Masks can be made automatically:

1. Segment the mesh with P3-SAM or GeoSAM2. GeoSAM2 reports higher mIoU than SAMPart3D, SAMesh and PartField ([GeoSAM2](https://arxiv.org/html/2508.14036v1)). Or segment by **PartUV** charts, which average 48.6 charts against 974.8 for xatlas and 1,360 for Blender ([PartUV](https://arxiv.org/abs/2511.16659)).
2. Let a VLM assign each part to a dye slot.
3. Rasterise the face labels into UV space in Blender.

Low-poly ships and props can use vertex-colour masks instead (glTF COLOR_0). Mask textures must be linear, not sRGB, and must avoid lossy chroma compression.

## Animation comes from CC0 libraries, retargeted offline to rest-normalised rigs

Ranked sources for a commercial game:

| Rank | Source | Licence |
|---|---|---|
| 1 | **Quaternius UAL 1 + 2**: 120+ and 130+ clips on one universal humanoid rig ([Quaternius](https://quaternius.com/packs/universalanimationlibrary.html); [OpenGameArt UAL 2](https://opengameart.org/content/universal-animation-library-2)) | CC0 |
| 2 | **Meshy animate**: 600+ humanoid presets, free on the web app; quadrupeds get a walk only ([Meshy Animation API](https://docs.meshy.ai/en/api/animation)) | Meshy plan |
| 3 | **Mixamo** ([Adobe FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html)) | Royalty-free in games, but **no redistribution of raw files and no ML training**, so keep it out of a public repo |
| 4 | CMU mocap ([CMU via HF](https://huggingface.co/datasets/gbionics/cmu-fbx)) | Free for commercial use, no resale |
| 4 | Rokoko free packs ([Rokoko](https://www.rokoko.com/resources/download-263-rokoko-motion-capture-assets)) | Commercial use allowed |
| 5 | Quaternius CC0 animal packs: 12 quadrupeds with 12+ clips each ([Quaternius](https://quaternius.com/packs/ultimateanimatedanimals.html)) | CC0 |

Two sources are off the table: **Bandai Namco's dataset (CC BY-NC) and AMASS (non-commercial)**. Because AMASS forbids training models for commercial use, HumanML3D-trained text-to-motion checkpoints (MoMask, MDM, T2M-GPT, MotionGPT) are legally doubtful for shipped motion, whatever their MIT code licences say ([AMASS licence](https://github.com/nghorbani/amass/blob/master/LICENSE.txt)).

Two local text-to-motion models are commercially viable:

- **HY-Motion 1.0** claims macOS support and outputs SMPL-H. Its Tencent community licence excludes the EU, UK and South Korea ([GitHub](https://github.com/Tencent-Hunyuan/HY-Motion-1.0); [HF](https://huggingface.co/tencent/HY-Motion-1.0/blob/22f2bd01d6a4ab4bfab75142032a46acb851ce44/README.md)).
- **NVIDIA Kimodo's SOMA checkpoint** is under the NVIDIA Open Model License, "ready for commercial use". Its SMPL-X checkpoint is non-commercial, and its MPS support is unknown ([HF](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1)).

In the cloud, Meshy text-to-motion costs 3–10 credits. Tripo added humanoid text-to-motion with VRM and Mixamo skeleton presets in October 2026 ([Spatial Insiders](https://spatialinsiders.com/stories/tripo-rigging-animation-text-to-motion)). For video mocap, the clean commercial option is Rokoko Vision at $10–20/mo. GVHMR's MPS fork has non-commercial weights, and FreeMoCap is AGPL ([Rokoko Vision](https://www.rokoko.com/products/vision); [HF gvhmr](https://huggingface.co/ryanrudes/gvhmr)).

Retargeting should be **offline in Blender onto rest-normalised rigs**. That means identical bone names, identical rest axes and T-pose, so clips play rotation-only, with hip translation scaled by the hip-height ratio. Godot does this natively: its Rest Fixer normalises rests and uses Hips height as `motion_scale` ([Godot docs](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/retargeting_3d_skeletons.html)). three.js `SkeletonUtils.retargetClip` is fragile and produces inverted feet and backward hands even on near-identical Mixamo rigs ([three.js forum](https://discourse.threejs.org/t/skeletonutils-retarget-doesnt-work-with-mixamorig-skeleton-inverted-feet-backward-hands/54892)). Pre-baking clips for three.js is therefore mandatory, not optional. The Blender retargeters rank as follows: Auto-Rig Pro Remap ($50) first, then the free Expy Kit and its Blender 5 "Retarget" fork ([Blender Extensions](https://extensions.blender.org/add-ons/retarget/)). One quadruped trap: separate front and back leg mappings cut joint error from 40° to 4.4° ([QtMeshEditor PR](https://github.com/fernandotonon/QtMeshEditor/pull/1085)).

Creatures and ships get a small set of keyed or CC0 core clips per family, with procedural layers on top:

- **Godot SpringBoneSimulator3D**: linear chains only, no branches, no scaled bones ([Godot docs](https://docs.godotengine.org/en/stable/classes/class_springbonesimulator3d.html)).
- **three-vrm's VRMSpringBoneManager**, which takes plain Object3D joints ([three-vrm](https://pixiv.github.io/three-vrm/docs/classes/three-vrm.VRMSpringBoneManager.html)).
- **ChainIK3D** for foot placement.

On the web, each family's clips should ship once as an animation-only GLB run through gltf-transform `resample → quantize → meshopt`. In Meshy's cookbook, a character with three clips comes out at about 0.6 MB ([Meshy cookbook](https://www.meshy.ai/developers/cookbook/recipes/animate-character-in-threejs/)).

## Texturing, export and procedural generation favour Blender scripts over models

**Texturing**, ranked:

1. **The generator's own texture pass**: Meshy textured generation, or retexture at 10 credits ([Meshy pricing](https://docs.meshy.ai/en/api/pricing)).
2. **Hunyuan3D-Paint 2.1 on MLX**, the best local PBR on Apple Silicon: 4096² albedo plus metallic-roughness in about 9 min on an M2 Pro ([dgrauet/Hunyuan3D-2.1-mlx](https://github.com/dgrauet/Hunyuan3D-2.1-mlx)). It is under the Tencent 2.x territory licence.
3. **Hand paint-over** in ArmorPaint (zlib source, $19 binaries, macOS) or in Blender ([daily.dev](https://daily.dev/posts/armorpaint-turns-1-0-free-substance-like-3d-painting-software--ab5jea5d9)).

The diffusion texturing add-ons, StableGen and MV-Adapter texturing, assume NVIDIA ([StableGen](https://github.com/sakalond/StableGen/wiki)). For painterly art, full PBR is mostly wasted. Albedo, a constant roughness and a 2–3-band toon ramp carry the look.

**Export** must branch per engine:

| Target | Build | Reason |
|---|---|---|
| Godot | Plain or quantised GLB with PNG or KTX2 textures; **never Draco** | Godot reads KTX2 since 4.2 but cannot open Draco; Godot meshopt support is unconfirmed ([Godot PR](https://github.com/godotengine/godot/pull/76572); [Cinevva checklist](https://app.cinevva.com/guides/blender-to-godot-export-checklist)) |
| Web | `gltfpack -cc -tc` (meshopt + KTX2) | three.js decodes both ([gltfpack](https://meshoptimizer.org/gltf/)) |

Godot auto-generates LODs at import, but they "can sometimes cause rendering issues, especially in skinned meshes" ([Godot docs](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)). Characters with blend shapes should skip auto-LOD. Export hygiene:

- 1 Blender unit = 1 m;
- apply all transforms;
- character faces -Y in Blender, so it faces -Z in Godot;
- export deformation bones only.

**Procedural** generation means Blender Geometry Nodes plus bpy. Houdini Indie costs $299/yr, and no official Godot Houdini Engine plugin exists ([SideFX](https://www.sidefx.com/products/houdini-indie/)). LL3M shows that planner/coder/critic agents writing Blender Python against API-doc retrieval are viable, and the code stays editable ([arXiv 2508.08228](https://arxiv.org/abs/2508.08228)). For ships, islands and modular kits, the agent should **write versioned parametric generators**, not one-off meshes.

## The agent layer should be deterministic scripts, with the MCPs as drivers

The connected **official Blender Lab MCP** is the right driver. It has API-doc search, which fights hallucinated bpy, render and screenshot tools for critique loops, and `_for_cli` variants for headless work ([Blender Lab](https://www.blender.org/lab/mcp-server/)). Its known failure is a hard **4-minute client timeout**, because bpy runs on Blender's main thread ([StraySpark](https://www.strayspark.studio/blog/blender-mcp-not-working-fix-connection-2026)). Bakes, decimation and batch fitting should therefore run as `blender -b -P script.py` subprocesses that print JSON.

The other MCPs, ranked by usefulness:

| MCP | Status | Use |
|---|---|---|
| **Meshy MCP** | Most complete generator MCP; MIT ([Meshy docs](https://docs.meshy.ai/en/api/ai)) | Generation, retexture, rig, animate |
| Tripo official MCP | Stale alpha ([GitHub](https://github.com/VAST-AI-Research/tripo-mcp)) | Call Tripo through fal or REST from scripts instead |
| ahujasid's community Blender MCP | Adds Sketchfab, Poly Haven and Rodin, but has a reported SSRF issue ([issue #203](https://github.com/ahujasid/blender-mcp/issues/203)) | Not needed |
| Coding-Solo/godot-mcp | Free, CLI-based ([DEV](https://dev.to/orellanaed/the-best-godot-mcp-server-in-2026-depends-on-what-you-want-the-agent-to-touch-5aji)) | Optional; plain `godot --headless` is enough for import validation |

Prior art worth copying already exists. **blender-kiln** enforces 31 rules and optimises with gltf-transform and gltfpack ([GitHub](https://github.com/elithril/blender-kiln)). **majidmanzarpour/blender-game-skills** emits `asset-manifest.json` and `animation-contract.json` and grades output against references ([GitHub](https://github.com/majidmanzarpour/blender-game-skills)). BlenderAlchemy found that **pairwise "which render is closer" judgments** are more reliable than absolute VLM scores ([arXiv](https://arxiv.org/pdf/2404.17672)). Memory across attempts drove VIGA's gains ([BlenderGym](https://www.emergentmind.com/topics/blendergym)). Anthropic's skill guidance favours a short SKILL.md, references one level deep, and scripts whose output alone enters context ([best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).

Assets for kits and props should come from CC0 sources first. Poly Haven requires a credit line and a unique User-Agent ([API README](https://github.com/Poly-Haven/Public-API/blob/master/README.md)). ambientCG is keyless. Sketchfab NC and ND licences should be rejected automatically.

### Recommended end-to-end stack

| Stage | Default (free/local unless noted) | Paid or cloud fallback | Mac note |
|---|---|---|---|
| Concept views | Existing `art:image` turnaround, flat lit, A-pose | Meshy text-to-image | — |
| Generation | Meshy 7.1/t2.5 (connected) and TRELLIS.2 trellis-mac, A/B | Tripo P1; fal TRELLIS 2 / Hunyuan 3.1 if the country allows | trellis-mac about 3.5 min, about 18 GB |
| Parts | One object per generation; QuadriFlow cleanup | Tripo Smart Segment; Hunyuan3D-Part on a rented GPU | Part models need CUDA |
| Family base | MPFB2 CC0 base for humanoids; hand-built creature and ship bases | — | Native |
| Wrap | trimesh NICP + Shrinkwrap/Corrective Smooth → signature key | BWrap €29.99 | Native |
| Rig | Canonical family skeleton fitted in bpy; Rigodotify naming | Meshy or Tripo rig, then rename map | Native |
| Skin | Inherit (wrapped) → robust weight transfer → SkinTokens `--use_skeleton` | Voxel Heat ($30) | SkinTokens MPS about 45 s |
| Morphs | Bone-offset proportions + vertex sliders; ARKit 52 via the free baker | Faceit | Native |
| Gear | Surface Deform per-key bake + push-out + covers bitmask; sockets for rigid gear | Marvelous Designer $280/yr | Native |
| Animation | Quaternius UAL + Meshy web presets; offline retarget (Expy/Retarget) | ARP Remap $50; Rokoko Vision; HY-Motion if the country allows | HY-Motion claims macOS |
| Texture and dye | Generator texture → paint-over → RGB(A) mask; TSL + Godot shader pair | Meshy retexture; Hunyuan-Paint MLX if the country allows | MLX about 9 min |
| Export and QA | Two builds (Godot plain/KTX2, web meshopt+KTX2); validator; headless Godot import; turntable renders | — | EEVEE on Metal |
| Agent layer | Deterministic `scripts/*.py` run headless; Blender Lab MCP for inspection and renders; per-asset sidecar with licence, credits and hashes | — | Avoid the 4-minute MCP timeout |

## Conclusion

The research changes the framing of "a skill that creates any customisable asset". It is less an AI-generation problem than a **data-contract problem with an AI front end**. Once a family's base, skeleton, region map and dye convention are fixed, the hard stages (wrap, skin, morph-follow, gear-fit, retarget) become deterministic Blender scripts with free tools. Generators become swappable suppliers. A model that ranks first today can be replaced next quarter without touching the runtime. Two implications follow for game0. First, the existing per-people Meshy bases should become **wrap targets** rather than shipping meshes, so the peoples share one topology. Second, Mixamo-named rigs should be renamed to a canonical profile at the end of the pipeline, not used as the contract.

The remaining unknowns are concrete and testable. The notes contain no benchmark of TRELLIS.2 against Meshy on painterly input. MPS ports are community-maintained and unbenchmarked against CUDA, SkinTokens' weight licence is unverified, and Tripo and Rodin output terms were not retrieved. The skill's first milestone should be a **one-family vertical slice**: one people wrapped, skinned, morphed, dressed in one garment and animated, then validated in both engines. That slice settles these questions before any batch spend.

## Design questions to settle before building the skill

1. **Which country are you, and any co-developers or publisher, based in, and where will the game be sold?** Hunyuan3D 2.x, Hunyuan3D-Part, Hunyuan-Paint and HY-Motion exclude the EU, UK and South Korea, including outputs. Is staying under 1M MAU and $1M revenue realistic? Those thresholds trigger Hunyuan, MetaHuman and Stability terms.
2. Which body families exist, and which peoples belong to each? Do Galeborne, Anchorkin and Rootwardens share one humanoid family, or do some need their own skeleton (for example extra chains for roots or tails)?
3. Will the shipped game have an **in-game character creator**? That rules Reallusion and Daz content out, and decides between live sliders and baking sliders on confirm.
4. Should the humanoid base move to the CC0 MPFB2 mesh, with the existing Meshy bases wrapped onto it, or should one Meshy base be kept as the family master?
5. Is the canonical humanoid naming Godot SkeletonProfileHumanoid/VRM, or do you want to keep Mixamo names as the source of truth?
6. How many sliders do you want per family (body, face), and which signature features need per-people clamp ranges?
7. Are facial expressions or lip sync needed (ARKit 52 + Rhubarb), or do a few custom shapes per people suffice?
8. What is gear layering depth (underclothes, garment, armour, cloak), and are capes required to coexist with wings, tails or shells?
9. How many dye channels per asset (3 or 4), and are dyes per item, per people palette, or free colour?
10. Do you want painterly albedo only (with a toon ramp), or full PBR?
11. What are the triangle and texture budgets per asset class (hero character, NPC, creature, ship, prop) for desktop Godot and for the web?
12. Will the three.js target use WebGPURenderer (TSL dye nodes) or WebGLRenderer?
13. Which creatures and ship types are first, and should ships have animated rigging, sails or crew sockets?
14. What animation scope per family (core clip list, signature clips), and is procedural secondary motion acceptable for tails, ears and capes?
15. Is the repository, or will it become, public? That decides whether Mixamo, Rokoko or Asset Store clips may be committed.
16. What is the monthly paid budget? Meshy Pro's 1,000 credits and the current 250-per-session cap: is Tripo or fal spend acceptable, and are you willing to rent hourly cloud GPUs for CUDA-only models?
17. Which one-off add-on purchases are acceptable: Auto-Rig Pro ($50), Voxel Heat (about $30), Faceit, BWrap (€29.99), Quad Remesher?
18. Which Mac do you have (chip and unified memory)? TRELLIS.2 needs about 18–24 GB and Hunyuan about 32 GB. Can generation run in overnight batches?
19. Which Blender version is installed (the official MCP needs 5.1+), and is a pinned Godot version fixed (IK needs 4.6+, spring bones 4.5+)?
20. How much human review do you want: approval gates after generation, after wrap and after fit, or only at the end? Should the skill use pairwise render comparison against concept art automatically?
21. Should procedural generators (ships, islands, modular kit pieces) live in the repo as versioned Blender Python, and what grid or snapping standard should environment kits follow?
