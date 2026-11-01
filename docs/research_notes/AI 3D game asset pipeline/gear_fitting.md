# Gear Fitting Across Body Shapes and Races (games + tools + algorithms, late 2026)

Scope: how shipped games and creator tools fit clothing, armor, props and accessories to many bodies, and which algorithms and free/local tools (Blender, Godot 4, three.js/glTF, Apple Silicon) can make "author once per body family, fit everyone" automatic. Research done 2026-11-01 via web search (snippets; full pages were not fetched, so a few details rest on search-engine summaries of primary docs).

## Shipped-game and creator-platform approaches

### Takeaway
There are four families of solution: (1) one shared skeleton plus per-race bone deforms applied to one base mesh (FFXIV, Sims 4 bone deltas); (2) shared base topology/UV with morph data that garments inherit (Sims 4 DMaps/BGEO, BodySlide/Outfit Studio, Daz Auto-Follow, CC4 conform); (3) cage-based runtime wrapping keyed by shared cage UVs (Roblox Layered Clothing, the most completely documented runtime auto-fit); (4) bake-time discrete sizes/variants and geoset toggles (MetaHuman sized outfits, WoW geosets, RPM male/female templates). Most games mix them: auto-fit for the common case, hand-made variants for outliers.

### Cited Findings

**Roblox Layered Clothing (cage-based runtime fitting): detailed**
- Cages are never-rendered meshes that define inner and outer surfaces through WrapLayer/WrapTarget; they only interact with their paired cages, unlike collision — [Roblox Cage meshes](https://create.roblox.com/docs/art/modeling/cage-meshes)
- Inner cage = surface the garment wraps over (how a T-shirt stretches over the body); outer cage = surface the next layer wraps over — [Roblox Cage meshes](https://create.roblox.com/docs/art/modeling/cage-meshes)
- WrapTarget is the first outer surface (almost always the avatar body's outer cage, `CageMeshId`). Bodies only need an outer cage; a character must have one to equip layered clothing — [Roblox Layered accessories](https://create.roblox.com/docs/avatar/layered-accessories)
- WrapLayer holds the accessory's inner cage (`ReferenceMeshId` / `ReferenceMeshContent`) and outer cage (`CageMeshId` / `CageMeshContent`); valid only when both are set. For catalog items ReferenceMeshId is expected to be one of 15 standard Roblox reference meshes. Other properties: `Order` (higher = on top), `AutoSkin`, `BindOffset`, `Enabled`, `DebugMode`, `Puffiness`, `ShrinkFactor`, `ReferenceOrigin` — [WrapLayer API ref](https://robloxapi.github.io/ref/class/WrapLayer.html); [create.roblox.com WrapLayer](https://create.roblox.com/docs/reference/engine/classes/WrapLayer.md)
- Matching rule: vertices of one cage are paired with the other cage's by UV coordinates, then the render mesh is reshaped so its cage matches the target cage. All targets and layers must share identical cage UVs; deleting cage vertices or altering cage UVs breaks import/equip — [Roblox Apply deformation](https://create.roblox.com/docs/art/modeling/cage-meshes/apply-deformation); [Cage meshes](https://create.roblox.com/docs/art/modeling/cage-meshes)
- All Roblox bodies share one standard body cage (per each of 15 body parts), so an accessory caged to that layout fits every body — [Roblox Apply deformation](https://create.roblox.com/docs/art/modeling/cage-meshes/apply-deformation)
- Naming convention: `<Mesh>_InnerCage`, `<Mesh>_OuterCage`; the whole garment must sit between the inner and outer cage (anything inside the inner cage artifacts when layered; anything outside the outer cage won't deform) — [Roblox caging best practices](https://create.roblox.com/docs/en-us/avatar/layered-accessories/caging-best-practices)
- An LC item = inner cage + outer cage + armature (15 deforming R15 bones + 1 root) + the clothing mesh with vertex weights — [Roblox Apply deformation](https://create.roblox.com/docs/art/modeling/cage-meshes/apply-deformation)
- Automatic Skinning Transfer (`WrapLayer.AutoSkin`): skinning is transferred by closest distance between the accessory and its inner cage, so editing the cage changes which body region the item follows — [Roblox Automatic Skinning Transfer](https://create.roblox.com/docs/avatar/automatic-skinning-transfer)
- Algorithm: originally RBF (radial basis function) for both cage alignment and clothing fit. 2025 update replaced cage alignment with a "linear deformer" that offsets each cage point to position the next cage, keeping RBF for the garment fit; samples both inner and outer cages to cut bulk/penetration. Three steps: (1) initial cage positions assuming every layer keeps its shape, (2) compute target outer silhouette where all layers contribute, (3) linear deformer compresses the stack so the outer silhouette matches. Several fit-tuning props (Puffiness/ShrinkFactor-type) deprecated/ignored — [DevForum: Improved Layered Clothing Fit](https://devforum.roblox.com/t/coming-soon-improved-layered-clothing-fit/3550013)
- Roblox patent: RBF-based layer conforming makes stacks look "puffy"; mitigated by adding interpolation/variance terms to the RBF; patent also covers hidden-surface removal of body/inner layers under clothing — [US 12190427](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12190427)

**Skyrim / Fallout: BodySlide and Outfit Studio**
- Conversion references = a reference shape (body mesh) plus sliders that morph it; other meshes are "conformed" to those sliders so they morph with the reference; also used to convert an outfit from body A to body B (slider 0%→100%) — [ousnius wiki: Conversion references](https://github.com/ousnius/BodySlide-and-Outfit-Studio/wiki/Conversion-references-and-using-them)
- Workflow: first fit outfit to the base reference shape; Slider → Conform All; check every slider for clipping and fix with brushes on the outfit (never the reference); then Copy Bone Weights from reference to outfit — [ousnius wiki](https://github.com/ousnius/BodySlide-and-Outfit-Studio/wiki/Conversion-references-and-using-them)
- Updating for new body sliders: load new reference, uncheck all, check only new sliders, Conform All — preserves hand-fixed data for old sliders — [ousnius wiki: Updating projects](https://github.com/ousnius/BodySlide-and-Outfit-Studio/wiki/Updating-projects-for-new-sliders)
- Recent changelog: conform respects masks on the reference shape; FAQ notes that vertices too far from the reference get no weights — [BodySlide SE Nexus](https://www.nexusmods.com/skyrimspecialedition/mods/201)

**Final Fantasy XIV: racial deform (pre-bone deformer)**
- Most gear is made once (e.g., Hyur Midlander model, path c0201) and reshaped per race at runtime — [XIV-Instant-Edit wiki: Racial Scaling](https://github.com/link-0402/XIV-Instant-Edit/wiki/Racial-Scaling)
- PBD ("pre-bone deformer") file transforms the base skeleton per race; each racial entry holds bone names and a 4x3 matrix per bone; `get_deform_matrices(from_body_id, to_body_id)` composes deforms between races via a parent/link chain — [physis PreBoneDeformer docs](https://docs.rs/physis/latest/physis/pbd/struct.PreBoneDeformer.html); [physis pbd.rs](https://docs.rs/crate/physis/latest/source/src/pbd.rs)
- EQDP (racial model edits) flags whether a race/gender gets a dedicated model/material; otherwise male races fall back to Midlander male, female races to Midlander female. EST = extra skeleton, only for face, head gear, chest gear, hair. RSP = racial scaling (height, tail length, bust sliders) — [Penumbra wiki: Advanced Editing](https://github.com/xivdev/Penumbra/wiki/Advanced-Editing)
- TexTools can apply racial scaling on export; Penumbra exports only the base model (issue open since Mar 2024) — [Penumbra issue #406](https://github.com/xivdev/Penumbra/issues/406)

**The Sims 4**
- Three morph types: Bone Delta (BOND: bone location/size/rotation; works on any mesh/LOD with correct weights; only acceptable way to change height), BGEO (per-vertex blend geometry; most precise, used for face), DMap (deformer map sampled through a second UV channel, UV1; no asymmetry) — [MTS: TS4MorphMaker DMap tutorial](https://modthesims.info/showthread.php?t=613057)
- Every CAS part that must morph needs UV1; clothing that fails to follow sliders is usually a missing/bad UV1; advice is to Data-Transfer UV1 and weights from the body rather than hand-make them. Skirts/dresses need "robe" morphs to avoid distortion — [MTS tutorial](https://modthesims.info/showthread.php?t=613057); [Sims4Studio thread](https://sims4studio.com/thread/15513/cas-body-slider-problem)

**World of Warcraft**
- Character models contain every hairstyle/thick armor variant as geosets (submeshes) toggled on/off; geoset IDs encode type (e.g., 10 = chest doublet, 23 = hands) — [wowdev Character Customization](https://wowdev.wiki/Character_Customization)
- Armor textures are composited into reserved regions of a character texture atlas; Shadowlands moved to procedurally generated textures on the fly because permutations reached millions — [Blizzard Engineer's Workshop](http://worldofwarcraft.blizzard.com/en-us/news/23564386/engineers-workshop-enhancing-character-customization)
- Data tables: ChrCustomizationElement links Geoset, SkinnedModel, Material, BoneSet; ChrModelTextureLayer defines texture layer compositing — [wowdev](https://wowdev.wiki/Character_Customization)

**Daz Studio / Character Creator 4**
- Daz Auto-Follow: conforming clothing auto-follows the base figure's morphs; Transfer Utility projects shape + weights from figure to clothing; clone shapes let clothing fit other figure generations; clothing must be converted to Weight Mapping; known distortion and frequent need for hand-made character-specific clothing morphs — [Daz docs: Modeling Against a Genesis Shape](http://docs.daz3d.com/doku.php/public/software/dazstudio/4/userguide/creating_content/rigging/tutorials/modeling_against_a_genesis_shape/start); [Daz forum](https://www.daz3d.com/forums/discussion/314076/auto-fit-my-own-content-to-genesis-8-characters)
- CC4 auto-conforms clothes and hair when body proportions change; can be disabled per item (e.g., belts with rigid parts distort) via Conform Clothing panel → Enable Conforming — [Reallusion manual](https://manual.reallusion.com/Character-Creator-4/Content/ENU/4.0/08_Cloth/Disabling_Cloth_Conforming_Feature.htm)

**MetaHuman (UE 5.6/5.7)**
- UE 5.6 added Chaos Cloth Outfit Asset with resizing/refitting; MetaHuman clothing is either a parametric (resizable) outfit or a fixed-size skeletal mesh — [UE forum: Chaos Cloth 5.6](https://forums.unrealengine.com/t/tutorial-chaos-cloth-updates-5-6/2555686); [MetaHuman docs: Tailoring wardrobe items](https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items)
- Resizable outfit = multiple authored sizes; system auto-picks best size by body measurements, then resizes via `num_resizing_interpolation_points` spread across the body; all sizes must be the same garment representation; Epic recommends adding a size rather than more points if fit is bad — [ChaosSizedOutfitSource Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ChaosSizedOutfitSource?application_version=5.7)
- Resizing is editor-only (bake time), not runtime (Epic, Sept 2025) — [UE forum: Resizing Addendum](https://forums.unrealengine.com/t/tutorial-chaos-cloth-outfit-asset-resizing-addendum/2647376)
- Pipeline write-up: Marvelous Designer 2025.2 imports MetaHuman DNA natively; Cloth Asset → Outfit Asset → Wardrobe Item; Chaos Cloth is CPU-only (secondary source) — [Medium: MetaHuman 5.6/5.7 pipeline](https://medium.com/@Jamesroha/metahuman-5-6-5-7-pipeline-reference-170d302b078e)

**VRoid**
- VRoid Studio v2.0 added dress-up + XWear format with auto-fitting to the model's body type plus manual bone move/scale/rotate; exports VRM 1.0 — [VRoid news v2.0.0](https://vroid.com/en/news/26gn98sTuPJQ53LxDQRyFg)
- Garments carry a black/white "Skin Mask" texture that hides covered skin — [VRoid help](https://vroid.pixiv.help/hc/en-us/articles/360000231641-How-to-dress-up-your-character-importing-clothing-textures)

**Ready Player Me**
- Outfits modeled around official male/female template bodies; GLB ≤ 8 MB, ≤ 15k tris, max 4 weights/vertex, metal-rough PBR; naming `outfit-partner-collection-v2-m/-f`; validated on upload — [RPM Fullbody Outfits](https://docs.readyplayer.me/ready-player-me/customizing-guides/create-custom-outfits); [RPM Requirements](https://docs.readyplayer.me/asset-creation-guide/asset-creation/modeling-guidelines/requirements-conventions)
- RPM acquired by Netflix Dec 2025 and listed as defunct for developers — [Wikipedia](https://en.wikipedia.org/wiki/Ready_Player_Me)

**Cyberpunk 2077 (as an aside)**: "Garment Support" squishes inner layers/body under outer clothing; mods add body-part hide toggles — [ArchiveXL body toggles](https://www.nexusmods.com/cyberpunk2077/mods/26627)

### Inferences
- For a small team, FFXIV's pattern (one master mesh per body family + per-race bone deform matrices) plus Sims-style bone deltas for body sliders gives the most coverage per authored asset, because it needs only shared skeleton + correct weights and is free at runtime in any engine (it's just skeleton rest pose/scale changes).
- Roblox's design shows the minimum contract for runtime auto-fit: shared cage topology+UV per body family, garments carry inner/outer cage, a layer Order, and weights transferred from the cage. That contract is portable to Godot/three.js but the RBF/linear-deformer solve would have to be reimplemented (no open-source Roblox code).
- MetaHuman's "few sizes + interpolate" is the pragmatic bake-time fallback for extreme shapes (e.g., a heavy Anchorkin vs a slim Galeborne in this project's lore).

### Gaps
- Elder Scrolls Online and Black Desert: no reliable public technical source found on their gear fitting.
- WoW's exact per-race armor authoring (whether each 3D shoulder/helm is per race-gender) is attested only by forum speculation; helms are widely known to be per race-gender but no primary source was found here.
- No primary GDC talk on Sims 4 CAS clothing fitting was located.

## Algorithms: weight transfer, shape transfer, cages, collision, masking, layering

### Takeaway
The standard bake pipeline is: fit garment to base body → transfer skin weights (closest point, or robust inpainting for loose cloth) → transfer every body shape key/slider onto the garment (Surface Deform per shape or Data Transfer/projected morphs) → fix penetration per shape → write hide-mask metadata. Cage coordinates (MVC/HC/Green) are the right tool when garments sit far from the body.

### Cited Findings
- Robust Skin Weights Transfer via Weight Inpainting (Abdrashitov et al., Epic Games, SIGGRAPH Asia 2023 TC): copy weights only where a match is high-confidence (distance + normal checks) and solve for the rest by inpainting (Laplacian), avoiding garbage weights on skirts/capes — [paper PDF](https://www.dgp.toronto.edu/~rinat/projects/RobustSkinWeightsTransfer/preprint.pdf); [official code](https://github.com/rin-23/RobustSkinWeightsTransferCode)
- Implementations: Blender add-on [sentfromspacevr/robust-weight-transfer](https://github.com/sentfromspacevr/robust-weight-transfer); Godot-oriented fork [V-Sekai](https://github.com/V-Sekai/godot-robust-skin-weights-transfer); Maya [pontya](https://github.com/pontya/maya-robust-weight-transfer). Reference Python deps: libigl, polyscope, robust_laplacian — [V-Sekai README](https://github.com/V-Sekai/godot-robust-skin-weights-transfer)
- Blender Data Transfer modifier/operator: vertex mappings Nearest Vertex, Nearest Face Vertex, Nearest Edge Interpolated, Nearest Face Interpolated; face-corner Projected Face Interpolated (rays along normals); "Generate Data Layers" creates missing vertex groups; per-vertex mix factor via vertex group — [Blender 5.2 manual: Data Transfer](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/data_transfer.html); [Transfer Mesh Data](https://docs.blender.org/manual/en/latest/scene_layout/object/editing/link_transfer/transfer_mesh_data.html)
- Surface Deform: transfers a surface's deformation to another mesh; binding in global coords; artifacts grow with distance from target surface; target must be manifold-ish to bind — [Blender manual: Surface Deform](https://docs.blender.org/manual/id/latest/modeling/modifiers/deform/surface_deform.html); [bug T69339](https://developer.blender.org/T69339)
- Shape-key transfer recipe: Surface Deform on garment targeting body, bind with body at basis, set one body key to 1.0, "Apply as Shape Key", reset, repeat per key; leaving another bound Surface Deform active stacks/corrupts results — [Blender Artists](https://blenderartists.org/t/how-do-i-transfer-shape-keys/1118802); [cynthia-omondi script](https://github.com/cynthia-omondi/Blender-shape-key-transfer-script)
- Scripts: ShapeKeyWrap (Surface Deform-based, drives garment keys from body keys) — [cgvirus/ShapeKeyWrap](https://github.com/cgvirus/ShapeKeyWrap); [TransferAllShapeKeysViaSurfaceDeform](https://github.com/konoha18537007/TransferAllShapeKeysViaSurfaceDeform)
- Users report Mesh Deform less clean than Surface Deform for close-fitting garments — [Blender Artists](https://blenderartists.org/t/how-do-i-transfer-shape-keys/1118802)
- Cage coordinates: MVC has a closed form but goes negative in concave cages; Harmonic coordinates (Pixar, Joshi et al. 2007) are non-negative but need a numerical solve and more memory, same evaluation cost after; Green coordinates use vertex positions and face normals, preserve detail (quasi-conformal in 3D) but don't interpolate the cage boundary — [Pixar HC memo](https://graphics.pixar.com/library/HarmonicCoordinates/paper.pdf); [Joshi 2007](https://www.cs.jhu.edu/~misha/Fall07/Papers/Joshi07.pdf); [Green Coordinates](https://www.wisdom.weizmann.ac.il/~ylipman/GC/gc_techrep.pdf); [shape editing survey](https://arxiv.org/pdf/2103.01694)
- Roblox uses RBF for clothing fit and a linear deformer for cage stacking (see above) — [DevForum](https://devforum.roblox.com/t/coming-soon-improved-layered-clothing-fit/3550013)
- Body masking techniques: split body into region submeshes and toggle by garment "covers" flags (piece must fully cover a region); invisible material per slot or UV-space mask in shader; painted per-garment masks with occlusion layers where outer layer hides lower layers (Unity asset); CC4 stores hidden body regions per garment via dummy picker/brush; VRoid "Skin Mask" texture — [UE forum](https://forums.unrealengine.com/t/do-video-games-hide-the-player-model-underneath-the-clothing/33335); [Arawn body culling](https://arawn-software-publishing.gitbook.io/character-creator/basics/body-culling-and-mask-painter); [Reallusion: hiding body with dummy](https://manual.reallusion.com/Character-Creator-4/Content/ENU/4.0/08_Cloth/Hiding_Body_Meshes_with_Dummy.htm); [modular character system article](https://nastyrodent.com/modular-character-system/)
- Layer ordering: Roblox `WrapLayer.Order` (higher on top), each layer's outer cage is the next layer's target — [Roblox WrapLayer](https://create.roblox.com/docs/reference/engine/classes/WrapLayer.md)

### Inferences
- Recommended for this project: body family base mesh with body-slider shape keys + race bone deforms; garments get (a) weights via robust transfer, (b) one corrective shape key per body shape key (Surface Deform bake), (c) a "push-out" pass per key (Shrinkwrap "Outside" with offset, masked by vertex group, or a custom raycast) to fix penetration, (d) a coverage bitmask (e.g., 16-32 body regions) used to hide body submeshes/discard in shader. Engines then just drive matching blend shape weights on body and garments with the same values: glTF supports morph targets natively in both Godot and three.js, so this is runtime-free.
- Bone-scale race deforms work automatically for any skinned garment; shape keys handle soft-tissue sliders; bake corrective sizes only for extremes.
- Penetration under extreme slider combos (two keys at 1.0) is not covered by per-key correction; either clamp slider ranges, add combination correctives, or rely on body masking to hide the body underneath.

### Gaps
- No open-source implementation of Roblox-style runtime cage wrapping for Godot or three.js was found.
- No primary source on standard collision push-out algorithms in shipped games (Outfit Studio brushes and Cyberpunk "garment support" are the closest).

## Rigid props and accessories (sockets, grips, IK)

### Takeaway
Rigid gear is parented to a named bone with a per-item offset (Godot BoneAttachment3D, three.js `bone.add`); the key to "one offset works on all bodies" is a normalized skeleton (consistent bone axes/rolls) and per-body-family socket offsets. Two-handed weapons use IK on the off hand to a grip marker; Godot 4.6 reintroduced IK nodes.

### Cited Findings
- Godot 4.6 re-adds 3D IK: IKModifier3D with TwoBoneIK3D, ChainIK3D (SplineIK3D, IterateIK3D: FABRIK3D, CCDIK3D, JacobianIK3D); BoneConstraint3D can reference Node3D targets in 4.6 (aim hand at target); TwoBoneIK3D and SplineIK3D deterministic — [Godot blog: IK returns in 4.6](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)
- TwoBoneIK3D requires a pole target and handles twist via pole direction; intermediate bones are treated as straight virtual bones — [Godot docs TwoBoneIK3D](https://docs.godotengine.org/en/latest/classes/class_twoboneik3d.html)
- BoneAttachment3D + per-weapon offset Transform3D; problem: Mixamo bakes differing bone rolls per animation batch; fix: import-time retarget to SkeletonProfileHumanoid with Rest Fixer "Overwrite Axis" so one calibrated mount transform works across all animations/characters — [Godot forum](https://forum.godotengine.org/t/best-practice-for-attaching-weapons-items-to-a-characters-hand-across-many-animations-godot-4/141270)
- Reported bug pattern: TwoBoneIK3D after CCDIK3D on spine reaches backward; modifier order/pole setup matter — [Godot forum](https://forum.godotengine.org/t/twoboneik3d-on-avatar-swings-arm-backwards-when-spine-bends-but-target-is-reaching-for-the-ground/134703)
- three.js: sharing a skeleton across skinned garments: `garment.bind(bodySkeleton, bindMatrix)`; DetachedBindMode is intended for sharing a skeleton across multiple SkinnedMeshes; official example binds with identity matrix; simplest reliable path is one glTF with all meshes skinned to the same skeleton — [three.js SkinnedMesh docs](https://threejs.org/docs/pages/SkinnedMesh.html); [webgl_animation_multiple](https://github.com/mrdoob/three.js/blob/master/examples/webgl_animation_multiple.html); [three.js forum](https://discourse.threejs.org/t/three-js-share-skeleton-between-skinnedmeshes-using-same-bones-structure/18536)
- gltf-avatar-threejs supports skin combination with shared skeleton or rigid bind to a node — [shrekshao/gltf-avatar-threejs](https://github.com/shrekshao/gltf-avatar-threejs)

### Inferences
- Define a socket table per body family (hand_r_grip, hand_l_grip, back_sheath, hip_l, head_top, face_front, tail_base, wing_root...) as empty child nodes in the body glTF; props carry a "grip" empty; at equip time, align prop grip to socket. Race scaling then moves sockets automatically if they are children of bones; only non-proportional differences need per-family offset overrides.
- three.js prop attach: `skeleton.getBoneByName('hand_r').add(prop)` (general knowledge; not sourced here). Note: if race deforms scale bones, child props inherit scale; compensate with inverse scale or use socket empties under unscaled helper bones. Godot's SpringBoneSimulator3D docs also warn against scaled skeleton bones (below), so prefer bone translation/rest-pose changes over scale for race deform.

### Gaps
- UE socket conventions not researched in depth (out of target engines).

## Garment creation tools (manual and AI) and making them game-ready

### Takeaway
Marvelous Designer is now subscription-only ($39/mo or $280/yr personal, macOS supported, glTF export since 2026.0); Blender cloth is the free path. AI garment research is largely sewing-pattern based (ChatGarment, DressCode, GarmentDiffusion, GarmentCode) and outputs simulation meshes, not game-ready skinned gear; any generated garment still needs retopo/decimate, UV, fit-to-base-body, weight transfer and shape-key transfer.

### Cited Findings
- Marvelous Designer pricing: Personal $39/month or $280/year prepaid; commercial use allowed for eligible Personal users; perpetual license discontinued Dec 2, 2025; 2026.x supports macOS 14+ — [MD support: licenses](https://support.marvelousdesigner.com/hc/en-us/articles/47358269350041-What-kind-of-licenses-does-Marvelous-Designer-offer); [CG Channel MD 2026.0](https://www.cgchannel.com/2026/04/clo-virtual-fashion-releases-marvelous-designer-2026-0/)
- MD 2026.0 added garment rigging/animation updates and glTF support; 2026.1 added fold/wrinkle painting, seam ripping, blendshape-based animation — [CG Channel 2026.1](https://www.cgchannel.com/2026/08/clo-virtual-fashion-releases-marvelous-designer-2026-1/); [Digital Production](https://digitalproduction.com/2026/04/15/marvelous-designer-2026-0-adds-3d-pencil-and-lacing/)
- CLO Individual $50/month or $450/year (per MD's comparison page) — [MD pricing comparison](https://www.marvelousdesigner.com/explore/guide/3d-clothing-software-pricing-licensing-models-compared)
- ChatGarment (CVPR 2025): VLM outputs JSON → GarmentCode sewing patterns → simulated 3D garment; from image or text; supports editing — [arXiv 2412.17811](https://arxiv.org/pdf/2412.17811); [project](https://chatgarment.github.io/)
- DressCode (TOG 2024): SewingGPT autoregressive pattern generator from text — cited in [GarmentDiffusion](https://arxiv.org/html/2504.21476v1)
- GarmentDiffusion: multimodal diffusion transformer for sewing patterns, ~100x faster than SewingGPT — [arXiv 2504.21476](https://arxiv.org/html/2504.21476v1)
- Garment3DGen (Meta, 2024): deforms a base garment mesh to match image/text and generates textures (mesh, not patterns) — referenced in [GarmentX arXiv 2504.20409](https://arxiv.org/pdf/2504.20409)
- GarmentDreamer (3DV 2025): 3D Gaussian Splatting-guided, simulation-ready garment meshes from text, without sewing patterns — [arXiv 2405.12420](https://arxiv.org/pdf/2405.12420)
- Others: GarmentX, GarmageNet (TOG), GarmentCode/GarmentCodeData (arXiv 2405.17609), GarmentWeaver (arXiv 2608.30550, schema-aware multimodal patterns) — [GarmentWeaver](https://arxiv.org/pdf/2608.30550); [GarmageNet](https://dl.acm.org/doi/10.1145/3763271)

### Inferences
- For an agent pipeline: cheapest high-quality route is GarmentCode-style parametric patterns (Python, open) → simulate in Blender cloth over the base body in A-pose → remesh/decimate → UV → fit/transfer. Meshy/Tripo-style image-to-3D tends to produce fused body+clothes meshes; better used for rigid accessories (helmets, pauldrons, horns, masks) that attach via sockets or rigid-weight to one bone.
- Rigid armor plates should be weighted 100% to single bones (or few) and excluded from shape-key conforming (like CC4's belt case) to avoid bending metal; only cloth/leather parts should conform.

### Gaps
- Not verified: current Meshy/Tripo "clothing"/part-split features, Style3D pricing/export, Simply Cloth current version/price, whether ChatGarment/GarmentCode run well on Apple Silicon (they are PyTorch; likely CPU/MPS but untested).
- DressCode arXiv ID unverified (possibly 2401.16465).

## Hair, beards, capes, tails/wings and secondary motion

### Takeaway
Use hide rules/variants for conflicts (helmet hides hair → swap to "helmet hair" variant; cape vs wings/tail needs a cape variant with slit or a hide rule) and spring bones for capes/hair in both engines; SoftBody3D is unreliable for character-attached cloth.

### Cited Findings
- FFXIV: only face, headgear, chest gear and hair can carry an extra skeleton (EST), and RSP controls tail length per race — [Penumbra wiki](https://github.com/xivdev/Penumbra/wiki/Advanced-Editing)
- WoW geosets handle hairstyles, capes, gloves etc. as toggleable submeshes — [wowdev](https://wowdev.wiki/Character_Customization)
- Godot SpringBoneSimulator3D: SkeletonModifier3D for hair, cloth, tails; own collision shapes (sphere, capsule, plane; capsule `inside` mode traps joints) independent of the physics server; collisions must be children; can follow bones; warns that scaled Skeleton3D/bones misbehave — [Godot 4.4 SpringBoneSimulator3D](https://docs.godotengine.org/en/4.4/classes/class_springbonesimulator3d.html); [SpringBoneCollisionCapsule3D](https://docs.godotengine.org/en/4.4/classes/class_springbonecollisioncapsule3d.html)
- Spring bones react to world motion by default (good for capes, bad for coats) — [Godot forum](https://forum.godotengine.org/t/cloth-physics-simulation-with-springbonesimulator3d/117695)
- GPU PBD cloth for Godot 4.5+ (compute shaders, bone sphere/capsule/box colliders, pinning, inertia) — [MaxYari/gpu-cloth-sim](https://github.com/MaxYari/gpu-cloth-sim)
- SoftBody3D: use Jolt; pinned points attach to Node3D; bugs with moving attachments (stretching, flipped faces, #107061) and low-mass explosions (#116058, through 4.7.dev); no native skinned-mesh support — [SoftBody3D docs](https://docs.godotengine.org/en/stable/classes/class_softbody3d.html); [#107061](https://github.com/godotengine/godot/issues/107061); [#116058](https://github.com/godotengine/godot/issues/116058); [proposal #2515](https://github.com/godotengine/godot-proposals/issues/2515)
- VRM spring bones + collider groups are the VRoid/VRM standard for swaying outfit parts — [VRoid help](https://vroid.pixiv.help/hc/en-us/articles/39513128686745-Getting-Started-with-the-Dress-up-Feature-for-3D-Creators)

### Inferences
- Spring-bone chains (authored as bones in the garment glTF) are portable: Godot SpringBoneSimulator3D natively, three.js via @pixiv/three-vrm's spring bone implementation if using VRM conventions (not verified here).
- Encode conflicts as data: each item has `slot`, `layer`, `covers_regions` bitmask, `hides` (e.g., hair_top, ears, tail), `requires_variant_for` (e.g., wings → cape_winged).

### Gaps
- three.js cloth/spring-bone libraries not specifically searched.
- Hair/beard-under-helmet best practices in shipped games: no primary source found.

## Headless automation via Blender Python (Blender MCP)

### Takeaway
Everything in the bake pipeline is scriptable in bpy: Data Transfer (weights/UVs), Surface Deform bind + apply-as-shape-key loops, Shrinkwrap push-out, vertex-group masks, decimate, glTF export with morph targets. The robust-weight-transfer add-on and libigl Python path make the higher-quality weight transfer scriptable too.

### Cited Findings
- Data Transfer modifier and Transfer Mesh Data operator expose mapping modes and layer generation used for weights/UV1 transfer — [Blender manual](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/data_transfer.html)
- Surface Deform per-shape bake loop is already scripted in community repos (bind at basis, set key 1.0, bake, tear down) — [cynthia-omondi script](https://github.com/cynthia-omondi/Blender-shape-key-transfer-script); [ShapeKeyWrap](https://github.com/cgvirus/ShapeKeyWrap)
- Robust weight transfer has a Blender add-on and a pure-Python reference implementation (libigl + robust_laplacian) — [sentfromspacevr](https://github.com/sentfromspacevr/robust-weight-transfer); [rin-23 code](https://github.com/rin-23/RobustSkinWeightsTransferCode)
- Outfit Studio's workflow (conform all sliders, then fix clipping, then copy weights) is the conceptual template — [ousnius wiki](https://github.com/ousnius/BodySlide-and-Outfit-Studio/wiki/Conversion-references-and-using-them)

### Inferences
- Proposed agent skill steps (all bpy, runnable headless `blender -b -P` or via MCP): (1) import garment + body-family master; (2) align/scale to base body; (3) Shrinkwrap/push-out pass at basis with offset; (4) weights: robust transfer (or Data Transfer Nearest Face Interpolated + smooth + limit to 4 + normalize); (5) for each body shape key: Surface Deform bind → key=1 → apply as shape key (name identical to body key) → push-out correction; (6) automated QA: raycast/closest-point penetration count per key and per race pose, render thumbnails per race; (7) compute covers bitmask by testing which body region vertex groups are within garment's inner offset; (8) export glTF with morph targets, extras (`slot`, `layer`, `covers`, `hides`, socket names). Rigid items skip (5) and get bone parenting/sockets.
- Race differences via bone deforms need no garment work if race skeletons share bone names; validate by posing each race rig in Blender and running the penetration check.

### Gaps
- Not verified: Blender 5.x API changes to `modifier_apply_as_shapekey` or glTF morph target export limits; test on the user's installed Blender before finalizing the skill.
