# Character customization: shared base meshes, topology wrapping, morph creation and transfer (late 2026)

Scope: how to give every race ("people") in a body family one mesh topology and one skeleton so player sliders work across races, and how to turn AI-generated sculpts into morph targets. Targets are Godot 4 and three.js via glTF, on an Apple Silicon Mac, using mostly free/local tools. Research was done 2026-11-01 with web search only (no full-page fetches), so every claim below rests on search-result excerpts from the linked pages. Claims marked "(inference)" or listed under Gaps are not sourced.

## 1. How shipped games and tools do it (Sims 4, MetaHuman, CC4/5, Daz, MakeHuman/MPFB2, SMPL family, HumGen3D, others) and their licenses

### Takeaway
Every working system uses one shared base topology plus a skeleton. Sliders are a mix of vertex deltas (blend shapes) and bone deltas, and the Sims 4 also uses UV-space displacement maps. For a commercial indie game, MakeHuman/MPFB2 is the only base mesh with targets found that is both CC0 and allowed in an in-game character creator. Reallusion explicitly forbids in-game character creators. MetaHuman, Daz, HumGen3D and SMPL each carry restrictions (seat-license threshold, per-product add-ons, no raw redistribution, or academic-only terms).

### Cited Findings
**The Sims 4 (CAS) uses three kinds of morph data**
- DMap (Deformer Map): morph data stored as a bitmap, looked up through the mesh's second UV map (UV1). Each morph has two DMaps, one for shape and one for normals. It works on any mesh with a correct UV1, including all LODs, but it cannot make an asymmetrical morph. On human sims, the fingers and inner mouth share UV1 space, so a DMap morph on one distorts the other — [Mod The Sims, TS4MorphMaker DMap tutorial](https://modthesims.info/showthread.php?t=613057)
- BGEO (Blend Geometry): position and normal deltas looked up by vertex ID, so vertex numbering must match exactly. Only head meshes are numbered, so BGEOs work only for heads and faces. Since a patch, one BGEO works for all ages and genders — [Mod The Sims, BGEO preset tutorial](https://modthesims.info/t/613060)
- Bone Delta (BOND): changes bone location, scale and rotation. It is preferred for fingers, and BGEO or bone morphs are used for eyeballs and the tongue. Anything that affects the neck needs a DMap or bone delta, or the neck seam splits — [Mod The Sims, MorphMaker thread](https://modthesims.info/t/594650)
- How the pieces link: a HotSpotControl (a color region in the CASHotSpotAtlas, the clickable "morph regions" on the body) points to Sim Modifiers. Each modifier can combine BGEO, DMap and Bone Delta. Presets combine Sculpts and weighted Modifiers. Bone hashes are listed, e.g. b__Head__ = 0x0F97B21B — [Mod The Sims, bonedelta and slider names](https://modthesims.info/t/556696)
- The community tool, TS4 MorphMaker (v4.3), builds morphs from a base mesh plus a morphed mesh. When exporting from Blender, Keep Vertex Order must be checked — [simscommunity.info](https://simscommunity.info/2018/07/10/learning-your-tools-the-sims-4-morphmaker/)

**MetaHuman**
- Usable outside Unreal: per the official FAQ, the UE EULA allows MetaHuman characters and animation to be used across all engines and creative software. They are "Non-Engine Products", so runtime use in non-Unreal games triggers no royalty — [metahuman.com/license](https://www.metahuman.com/license)
- A UE seat license is needed if annual gross revenue exceeds $1M and MetaHumans are rendered outside UE. CG Channel cites about $1,850/yr per seat. The change shipped with UE 5.6 (June 2025), which also brought Creator, Mesh to MetaHuman and Animator into the engine — [CG Channel, Jun 2025](https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/)
- The license includes an AI carve-out: MetaHumans may not be used to train, build, enhance or test AI/ML models. Distribution through Fab uses the .mhpkg format. The web Creator is being retired in 2026 — [Medium guide, UE 5.6/5.7](https://medium.com/@Jamesroha/a-beginners-guide-to-metahumans-in-unreal-engine-5-6-and-5-7-e9b14fadbf3d). A StraySpark blog claims cross-engine use is not allowed, which contradicts Epic's FAQ — [StraySpark](https://www.strayspark.studio/blog/metahuman-2026-web-app-shutdown-migration-guide)

**Character Creator 4/5 (Reallusion)**
- CC5 was released Aug 2025: $299 perpetual, Windows only. The HD Ultimate Morphs pack is a $149 add-on. Official export plugins cover 3ds Max, Blender, Unity, Unreal and ZBrush, not Godot — [CG Channel, Aug 2025](https://www.cgchannel.com/2025/08/reallusion-releases-character-creator-5/)
- The Software EULA (dated May 25, 2026) allows exporting to games, but Section 5 says the topology and rigs of the CC base model belong to Reallusion. Use in "any character generation system" is prohibited — [Reallusion Software EULA](https://www.reallusion.com/Content/EULA/AP/EULA_AP.htm)
- A staff answer confirms Reallusion content (hair, clothing, morphs, accessories) cannot be used in any in-game character creator — [Reallusion forum](https://forum.reallusion.com/439860/In-game-Character-Creation-EULA-Question); [2025 thread](https://discussions.reallusion.com/t/clarification-on-eula-for-using-character-creator-with-custom-assets-and-edited-morphs-in-game-with-character-customization-system/14770)
- CC Components need an Extended License for mass-distributed games — [Reallusion Content License](https://www.reallusion.com/license/content.html)

**Daz Genesis**
- The old Game Developer Licenses (Commercial was $2,500) are no longer sold. Content is now licensed per product through an "Interactive License" add-on (e.g. $35), and not every product offers one. Each asset (figure, morphs, clothes, hair) appears to need its own add-on, and these licenses are non-refundable — [Daz forum](https://www.daz3d.com/forums/discussion/229511/hello-everyone-inquiring-about-a-game-dev-license); [Daz EULA, Section 3.0 Interactive License Addendum](https://www.daz3d.com/eula)

**MakeHuman / MPFB2 (strongest fit for this project)**
- All core assets (base mesh, targets, skins, rigs, weights, proxies) are CC0 1.0. You can sell models made with them, with no attribution or fees — [MPFB FAQ: Can I sell models](https://static.makehumancommunity.org/mpfb/faq/can_i_sell_models.html); [MakeHuman license page](https://static.makehumancommunity.org/about/license.html)
- The code is under a different license: MPFB is GPL and MakeHuman is AGPL. Using only the data with your own runtime avoids those obligations — [MakeHuman license](https://static.makehumancommunity.org/about/license.html); [partwright #1151](https://github.com/kemper/partwright/issues/1151)
- The FAQ explicitly allows taking the base mesh, targets and system assets to build your own character generator, and notes one already exists for Godot — [MPFB FAQ: build other chargen](https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html)
- MPFB2 runs on Blender 4.2+ — [CG Channel, Mar 2025](https://www.cgchannel.com/2025/03/check-out-open-source-blender-character-generation-plugin-mpfb-2/)

**SMPL / SMPL-X / STAR / SUPR**
- The free license covers only non-commercial research, education or artistic use. Commercial products, services and AI training for commercial use are prohibited — [SMPL-X Model License](https://smpl-x.is.tue.mpg.de/modellicense.html); [SMPL License](https://smpl.is.tue.mpg.de/modellicense.html)
- A commercial license through Meshcapade covers SMPL+H, SMPL-X and STAR. No prices are published — [Meshcapade wiki](https://github.com/Meshcapade/wiki/blob/main/wiki/SMPL.md); [Meshcapade Blender add-on](https://github.com/Meshcapade/SMPL_blender_addon)

**Human Generator (HumGen3D)**
- The code is GPL, but the assets fall under the "Human Generator Digital Asset License". Use in games requires the Commercial license ($128). The Personal license ($68) excludes games — [HumGen3D License FAQ](https://help.humgen3d.com/license); [pricing](https://humgen3d.com/pricing)
- Assets may ship inside a closed game format. Raw meshes cannot be shared or sold, even after editing — [HumGen3D License FAQ](https://help.humgen3d.com/license)

**Godot-native creators**
- Morphara is a commercial character creator that exports GLB with blend shapes for Godot — [morphara.com](https://morphara.com/godot-character-creator)
- Open-source Godot character creators exist: [Grumoth/godot-character-creator](https://github.com/Grumoth/godot-character-creator) and [smix8 wardrobe (Godot 3.2)](https://github.com/smix8/Godot3DCharacterEditorWardrobe)

### Inferences
- Recommended base: the MPFB2/MakeHuman base mesh and targets (CC0) as the "body family" topology, driven by your own GDScript/JS runtime. Avoid copying GPL/AGPL code into the game.
- Adopt the Sims 4 split. Use bone deltas for proportions (height, limb length, fingers, eyes) and vertex morphs for shape (face features, belly, muscle). Keep morphs away from seams such as the neck, or make them cover both sides of the seam.
- The Sims 4 DMap (UV-space displacement) idea transfers morphs across meshes that share UVs but not vertex order. This is relevant for clothing that has to follow body morphs.
- Black Desert, Elden Ring, WoW and BG3 were not researched in sources (see Gaps). Public descriptions of these games generally describe a shared skeleton per body type with bone-driven face sliders. This is unsourced.

### Gaps
- No sources were gathered for Black Desert, Elden Ring, WoW, BG3, VRoid (pixiv's VRoid license allows commercial use of VRM output), or Ready Player Me. My recollection is that RPM was acquired by Netflix in late 2025 and its public services shut down in early 2026, but this was not verified.
- The Genesis 9 base-figure interactive license price was not found.
- MetaHuman DNA / RigLogic availability outside UE (the open DNA Calibration library) was not verified.
- The SMPL commercial price was not found.

## 2. Topology wrapping: commercial tools, Blender approaches, open algorithms, headless scripting

### Takeaway
R3DS/Faceform Wrap is the reference commercial tool ($570 indie perpetual), but it runs on Windows and Linux only, not macOS. On a Mac, the practical free route is landmark-guided non-rigid ICP in Python (trimesh `nricp_amberg` / `nricp_sumner`), run headless next to Blender. Blender's Shrinkwrap + Corrective Smooth or Surface Deform handle refinement and binding, and BWrap is a cheap in-Blender option.

### Cited Findings
- Faceform Wrap prices: Indie (under $100K revenue) $570 node-locked perpetual; Professional $1,070 node-locked, $1,470 floating. Each includes 1 year of updates, then maintenance costs 50% per year. There is a 30-day trial, and it is free for non-commercial education — [CG Channel, Wrap 2025.11](https://www.cgchannel.com/2025/12/faceform-releases-wrap-2025-11-and-wrap4d-2025-11/); [iTechGuides, Sept 2026](https://www.itechguides.com/best/3d-sculpting-software/r3ds-wrap/)
- Wrap runs on Windows and Linux (no macOS stated) — [CG Channel](https://www.cgchannel.com/2025/12/faceform-releases-wrap-2025-11-and-wrap4d-2025-11/)
- Wrap4D costs $7,700 node-locked or $10,970 floating. The ZWrap plugin for ZBrush is from about $99 per year — [CGRiver](https://www.cgriver.com/collections/r3ds-wrap); [Toolfarm](https://www.toolfarm.com/buy/faceform_zwrap_for_zbrush/)
- BWrap (Blender 4.5–5.2) wraps a clean template mesh onto a sculpt or scan using correspondence points and outputs a shape key. The free version allows 1 template, 1 target and limited point pairs (sources say 24 or 50). The paid version is €29.99 — [BWrap on Superhive](https://superhivemarket.com/products/bwrap); [skalin.org](https://www.skalin.org/bwrap)
- Softwrap is a free soft-body-based wrapper on GitHub, possibly stale. object_alignment (GPL) does rigid point-pick ICP only, last updated for Blender 3.2 — [Softwrap](https://blender-addons.org/softwrap-addon/); [patmo141/object_alignment](https://github.com/patmo141/object_alignment)
- trimesh has `nricp_amberg(source_mesh, target_geometry, source_landmarks=None, target_positions=None, steps=None, eps=1e-4, gamma=1, distance_threshold=0.1, use_faces=True, use_vertex_normals=True, neighbors_count=8)`, an implementation of Amberg et al. 2007 Optimal Step NICP. `nricp_sumner` solves for triangle positions (Sumner-Popović deformation transfer style), while amberg solves per-vertex affine transforms. Both accept landmarks — [trimesh.registration docs](https://trimesh.org/trimesh.registration.html)
- Default amberg steps: `[[0.01,10,0.5,10],[0.02,5,0.5,10],[0.03,2.5,0.5,10],[0.01,0,0.0,10]]`. Sumner steps are labeled `[wc, wi, ws, wl, wn]` — [trimesh issue #2047](https://github.com/mikedh/trimesh/issues/2047)
- Other NICP implementations: [charlienash/nricp (Matlab)](https://github.com/charlienash/nricp), [RhythmJnh/Non-rigid-ICP](https://github.com/RhythmJnh/Non-rigid-ICP)

### Inferences
- Headless pipeline (inference, built from standard bpy features): `blender -b -P wrap.py` imports the AI sculpt, aligns it rigidly (trimesh `icp` or `registration.procrustes` on landmarks), then runs `nricp_amberg` with about 20–60 landmarks: eye corners, mouth corners, nose tip, ear tops, chin, fingertips, tail root and tip. Write the result into a shape key on the base mesh, with the same vertex count and order. Refine with Shrinkwrap (Nearest Surface Point / Project) followed by Corrective Smooth. Both modifiers, plus Surface Deform and Data Transfer, can be configured and applied from bpy. `bpy.ops.object.modifier_apply_as_shapekey` turns a modifier result into a shape key.
- Store the wrap result as a delta from the neutral base, so the race's "signature" is one blend shape that sits under the player sliders.
- Use ARAP / Laplacian smoothing (libigl's Python bindings, or Blender's Smooth Corrective) to keep loops from collapsing in concave areas such as ears, nostrils and between fingers.
- Wrap4D and Wrap only make sense on a Windows or Linux box, so they are out of scope for Mac-only work.

### Gaps
- R3DS Wrap's Python scripting API (Wrap has a node graph plus Python) was not confirmed in sources.
- ML-based registration (e.g. learned correspondences, Deep Deformation methods) was not researched. No 2026 sources were gathered.
- Faceit's wrap capabilities are limited to face landmark fitting, not full-body wrapping. "AutoWrap" and "Wrap to Mesh" add-ons were not found in results.

## 3. Retopology tools: which preserve game-ready edge loops

### Takeaway
None of the automatic tools reliably produces deformation edge loops (eye and mouth rings, shoulder and knee loops) on a character. For a shared-topology system, retopology is unnecessary for race variants: you wrap the existing base. Retopology matters only once, for authoring the base (and MPFB2 already supplies a game-ready base) and for props and attachments. Quad Remesher with guides is the best automatic option, and QuadriFlow / Instant Meshes are the free fallbacks.

### Cited Findings
- QuadriFlow is built into Blender and free, with curvature-following quads. It has no guide-edge support, which matters on characters — [Mixar comparison](https://www.mixar.app/compare/quad-remesher); [neta.art](https://neta.art/blog/quad-remesher-blender)
- Quad Remesher has guide curves, density painting and symmetry, and gives more consistent loops on limbs and fingers. It is about $79 perpetual per one source, while another lists about $10/mo, so prices conflict — [superrendersfarm](https://superrendersfarm.com/article/quad-remesher-blender-retopology); [SelfCAD](https://www.selfcad.com/blog/ai-smart-remeshing-tools-6-best-options)
- Instant Meshes is free and open source, and lets you orient edge loops along limbs. QuadriFlow is based on its field-aligned method — [instantmeshes.com](https://instantmeshes.com/vs-quadriflow/); [savedpixel](https://savedpixel.com/blog/blender-retopology-complete-guide/)
- RetopoFlow ($59.99, Blender 4.2–5.2) is for manual retopology. Manual retopology is still recommended where deformation loops matter — [3dxdev 2026](https://3dxdev.com/best-retopology-tools-for-blender-in-2026-free-and-paid-compared/)
- AI retopology:
  - MeshAnything V2 handles up to 1,600 faces — [arXiv 2408.02555](https://arxiv.org/html/2408.02555)
  - DeepMesh code is Apache-2.0 — [GitHub](https://github.com/zhaorw02/DeepMesh)
  - In a benchmark at about 4K faces, MeshAnything V2 scored CD 0.037 and DeepMesh 0.453 with a 28.7% success rate. Meshy T2 retopology takes a median of 3 s — [Meshy T2 paper, arXiv 2607.28675](https://arxiv.org/html/2607.28675v1)
  - QuadGPT generates quads natively and rewards coherent edge loops — [arXiv 2509.21420](https://arxiv.org/pdf/2509.21420)
  - MeshAnything V1's license was described as a custom non-commercial one, and its triangles "don't follow the logical loops" artists use — [HN thread](https://news.ycombinator.com/item?id=40746310)
- Voxel Remesh, Blender's built-in remesher, produces uniform grids with no loops (general knowledge, unsourced).

### Inferences
- Do not retopologize race variants. Always wrap the base onto the AI sculpt so vertex order is preserved, which is required for glTF morph targets.
- For one-off attachments (horns, shells, masks), QuadriFlow at a target face count from bpy (`bpy.ops.object.quadriflow_remesh`) is enough because they deform rigidly with a bone.

### Gaps
- Meshtron (NVIDIA) license and availability, Tripo smart mesh, and Meshy quad-remesh edge-loop quality were not sourced.

## 4. Proportion sliders: bone scaling vs blend shapes in Godot 4 and three.js

### Takeaway
Use bones for proportions (length and scale of limbs, height, head size, hands, feet, tail length) and blend shapes for surface shape (muscle, belly, face features). Godot's bone scale handling for this was historically problematic. three.js on WebGL2 has no hard limit on morph targets, only a texture and VRAM budget.

### Cited Findings
- Godot PR #83903 ("Add inherit_scale to bones") argued that proportional-editing character creators "are not currently possible in Godot without major animation artifacting", because scaling a parent bone does not correct child translation. The merge status was not confirmed — [godot PR #83903](https://github.com/godotengine/godot/pull/83903)
- Blend trees have caused root-bone scale and skew artifacts in the past — [#55838](https://github.com/godotengine/godot/issues/55838); [#59477](https://github.com/godotengine/godot/issues/59477)
- In Godot 3 GLES3, blend shapes were updated per surface and per pass: a 90-shape model produced about 2,500 draw calls. Godot 4.0 could not reproduce the slowdown — [#53244](https://github.com/godotengine/godot/issues/53244)
- In Godot 4 Vulkan, normals or shading break when several blend shapes are at 1 at once — [#55812](https://github.com/godotengine/godot/issues/55812). A blend shape issue tracker exists at [#63198](https://github.com/godotengine/godot/issues/63198)
- three.js since r133 converts morph targets to a float DataTexture2DArray on WebGL2, one layer per target, so more than 8 targets work. WebGL1 falls back to 4–8 attribute-based active targets — [three.js #14441](https://github.com/mrdoob/three.js/issues/14441); [forum](https://discourse.threejs.org/t/having-more-than-8-morph-targets/26859)
- One report says meshes with more than 241 shape keys failed to display on mobile — [three.js forum](https://discourse.threejs.org/t/overcoming-morph-target-limitations/14937). The morph texture is sized as vertexCount × all targets and cached per geometry object, so separate geometries multiply VRAM — [three-mmd-loader #42](https://github.com/yohawing/three-mmd-loader/issues/42)
- Unity reference numbers (RTX 4090): one blend shape compute pass costs about 0.005 ms and ten cost 0.08 ms. Cost scales with the number of vertices that have a non-zero delta — [d4rkc0d3r gist](https://gist.github.com/d4rkc0d3r/f77c1e96d4aeefd0d1eaf13fb096a2de)
- Godot's blend shapes don't work with MultiMesh instancing. A crowd needs a custom compute shader (unofficial source) — [gist](https://gist.github.com/willyrgf/566c9cce37986a6eba3e09f8b0a49ce4)

### Inferences
- **Bake once, render cheap.** Player sliders change rarely, so in the creator you can combine all body and face sliders into one baked mesh: in Godot, build an ArrayMesh from the weighted sum of deltas; in three.js, write the weighted positions into the BufferGeometry. Keep live morph targets only for expressions (ARKit 52) and corrective shapes. This avoids the morph-count limits entirely.
- Non-uniform bone scale also scales the skinned children and the animation. Prefer bone *length* (translation offsets on rest pose, i.e. a modified rest/bind pose) for height and limbs, and re-skin by rebuilding the Skin's bind poses. Use uniform scale only on leaf bones such as hands, feet, eyes and tail segments.
- glTF requires that all morph targets have the same vertex count and order as the base primitive. This is why every race must wrap the same base. Godot imports glTF morph targets as blend shapes, and three.js exposes them as `morphTargetDictionary` / `morphTargetInfluences` (standard glTF behavior, unsourced here).

### Gaps
- The Godot 4.x maximum blend shape count, per-shape GPU cost, and whether inherit_scale merged (Godot 4.3+ has `Skeleton3D` modifiers; unverified) are unsourced.

## 5. Face sliders and expressions (ARKit 52, FACS, face bones vs blend shapes, auto-generation)

### Takeaway
Use the ARKit 52 blend shape set as the expression standard. It is supported by Faceit, Audio2Face (which has ARKit presets) and the free Blender bakers. Face *identity* sliders (eyes, nose, jaw, ears, brow) should be blend shapes on the shared head, or bone offsets for eye position and jaw width. Generate the 52 expressions once on the neutral base and transfer them to each race.

### Cited Findings
- Faceit (paid, Superhive) does landmark fitting, automatic weighting, and FACS or ARKit expression presets. It semi-automatically creates the 52 ARKit shape keys (since v1.8), supports shapes beyond 52 (v2.3), and bakes the modifier stack, pose and sculpt into shape keys — [Faceit on Superhive](https://superhivemarket.com/products/faceit); [Faceit target shapes docs](https://faceit-doc.readthedocs.io/en/latest/target_shapes/)
- Audio2Face exports weights as JSON. It offers ARKit 52 presets (since 2023) as well as a FACS-46 set — [Faceit mocap importers](https://faceit-doc.readthedocs.io/en/latest/mocap_importers/)
- An open-source Audio2Face add-on can add missing ARKit shape keys to any mesh by transferring them from a demo head. It needs real deformations — [Ibrahim-3d/NVIDIA-Audi2Face-Addon](https://github.com/Ibrahim-3d/NVIDIA-Audi2Face-Addon)
- ARKit Blendshape Baker (free) poses a Rigify or AutoRig Pro face and bakes each of the 52 shapes — [tsikerdekis/ARKit-Creator-Blender-Addon](https://github.com/tsikerdekis/ARKit-Creator-Blender-Addon/)

### Inferences
- Transferring expressions across races works because the topology is shared. Apply the neutral-to-expression delta from the base on top of the race shape. For large shape changes (a beak or snout), use deformation-gradient transfer (Sumner-Popović), not raw deltas.
- Polywink and Mesh-to-FLAME were not sourced. FLAME is under a non-commercial license (unverified).

### Gaps
- Polywink pricing, FLAME license, and MetaHuman DNA/RigLogic outside UE are not sourced.

## 6. Hair, beards, feathers, foliage on morphing heads

### Takeaway
For games, use hair cards, made in Blender with Tuftwork, Hair Tool 4, or Daniel Bystedt's free Geometry Nodes setup. Making cards follow head morphs is not handled by any tool found. The standard approach is to bind the cards to the head (Surface Deform) and bake one matching shape key per head morph.

### Cited Findings
- Tuftwork (beta, Blender 5.2) paints strips and regions directly on the head to make cards for hair, beards, brows and lashes — [Superhive](https://superhivemarket.com/products/tuftwork)
- Daniel Bystedt's free Geometry Nodes setup turns curves into cards aligned to the surface (Blender 3.6+) — [CG Channel](https://www.cgchannel.com/2024/03/daniel-bystedts-free-blender-add-on-creates-hair-cards-from-curves/)
- Hair Tool 4 (paid) converts curves to card meshes with UVs and texture baking — [docs](https://joseconseco.github.io/HairTool_3_Documentation/); [Hair Particle to Card Generator](https://superhivemarket.com/products/hair-particle-to-card-generator-for-blender)
- Game engines receive raw shape keys, not Blender drivers, so bake everything — [Diffeomorphic issue](https://bitbucket.org/Diffeomorphic/import_daz/issues/292/strange-morph-deformation-when-converting)

### Inferences
- Bake follower morphs. For each head blend shape, bind the hair, feathers or foliage with Surface Deform, set the head key to 1, and save the result as a same-named shape key on the attachment. At runtime, drive all meshes' blend shapes of the same name together: in Godot, iterate the MeshInstance3D nodes; in three.js, set `morphTargetInfluences` via `morphTargetDictionary` on each mesh.
- Alternatively, skin rigid attachments (horns, feathers) to head bones so bone-based sliders carry them for free.

### Gaps
- No source confirms a tool that auto-transfers head morphs to hair cards.

## 7. Signature-feature clamping per race and compact appearance data

### Takeaway
No primary sources were found. Shipped systems (the Sims 4 presets with weighted modifiers) suggest storing appearance as a small set of named weights relative to a race preset.

### Cited Findings
- Sims 4 presets are weighted sets of Sculpts and Modifiers, and Sim Modifiers combine BGEO, DMap and Bone Delta — [Mod The Sims MorphMaker thread](https://modthesims.info/t/594650)

### Inferences
- Proposed schema (inference): `{ "v":1, "family":"humanoid", "race":"galeborne", "seed":123, "sliders":{"height":0.62,"shoulders":-0.2,"jaw_width":0.1,...}, "colors":{...}, "parts":{"hair":"braids_02"} }`. A per-race range table (`race.json`: `{ "jaw_width": [-0.3, 0.8], "ear_point": [0.5, 1.0] }`) clamps on load and on slider input. The race signature shape is always applied at 1.0 underneath.
- Use 8-bit quantized sliders to pack an appearance into a share code (base64 of a byte array, roughly 40–80 bytes).

### Gaps
- No GDC or official sources were found on per-race clamping tables or appearance serialization.
