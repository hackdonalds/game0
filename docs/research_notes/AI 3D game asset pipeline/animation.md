# Animation sourcing, generation and retargeting for game characters and creatures (state as of Nov 2026)

Scope: how an indie game on an Apple Silicon Mac (no NVIDIA) can build one large, consistent animation library per body family (humanoid, quadruped, flyer, etc.), then play it on many bodies with different proportions in Godot 4 and three.js. Commercial-use licensing is stated for every source. Research date: 2026-11-01. The research tool returned search summaries only, not full pages, so precise numbers should be re-checked against the primary page before anything ships.

## 1. Free and cheap animation libraries: availability and commercial licensing

### Takeaway
The libraries that are safe for commercial use and free are Quaternius UAL 1 and 2 (CC0), Kenney (CC0), Quaternius animal packs (CC0), Mixamo (royalty-free, no raw redistribution, no ML training), CMU mocap (free commercially, no resale of the data) and Rokoko's free packs (commercial use allowed, license not named). Bandai Namco's dataset (CC BY-NC 4.0) and AMASS (non-commercial, and no training for commercial use) are off the table for a commercial game unless you buy a license. A CC0 humanoid rig (Quaternius UAL) is the cleanest base for a canonical humanoid library that a public repo can also hold.

### Cited Findings
**Mixamo (Adobe)**
- Still free and still running in late 2026. A pricing index checked it on 2026-10-15 and recorded "Free tier: commercial use allowed" — [AssetForgeIndex](https://assetforgeindex.com/tools/mixamo)
- The Adobe FAQ says characters and animations are royalty-free for personal, commercial and non-profit projects, including games. You may not redistribute raw character or animation files as asset packages or templates. The one forbidden research use is training ML models. Credit is not required — [Adobe Mixamo FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html); [Rendered Influence](https://renderedinfluence.com/notes/adobe-mixamo-and-substance-3d-character-tooling-documentation/)
- Needs an Adobe ID. Not available to Enterprise or Federated IDs, or to users with a China country code. The community FAQ still calls it a "limited duration technology preview" — [Rendered Influence](https://renderedinfluence.com/notes/adobe-mixamo-and-substance-3d-character-tooling-documentation/); [Adobe community](https://community.adobe.com/mixamo-694)
- Signs of low investment. A 2025 forum reply from a support worker said "Mixamo is not supported anymore." School of Motion says the library has barely grown — [School of Motion](https://schoolofmotion.com/blog/why-mixamo-is-still-one-of-the-best-animation-resources)
- Mixamo now exports FBX only (no BVH), and Mixamo bone names carry a `mixamorig:` prefix — [Diffeomorphic issue tracker](https://bitbucket.org/Diffeomorphic/import_daz/issues/1975/pr-add-direct-fbx-mixamo-etc-import-to-bvh)

**Quaternius Universal Animation Library (UAL)**
- UAL 1 came out in March 2025. It has 120+ animations on a universal humanoid rig and is CC0 ("free to use in personal, educational and commercial projects"). It is compatible with Unreal, Godot and Unity and built for retargeting — [Quaternius](https://quaternius.com/packs/universalanimationlibrary.html); [itch.io](https://quaternius.itch.io/universal-animation-library)
- It comes in three tiers. Standard is free with 45 animations. Pro has all animations, exported and optimised for engines. Source has the .blend with rig and animations. The paid tiers are also CC0 — [itch.io](https://quaternius.itch.io/universal-animation-library); [OpenGameArt](https://opengameart.org/content/universal-animation-library)
- It is on the official Godot Asset Store as CC0 1.0, last updated 10 June 2026 — [Godot Asset Store](https://store.godotengine.org/asset/quaternius/universal-animation-library/)
- UAL 2 went up in January 2026 on OpenGameArt: 130+ animations including parkour, farming and zombie moves, CC0 — [OpenGameArt UAL 2](https://opengameart.org/content/universal-animation-library-2)

**Kenney**
- The animated character packs are CC0: Protagonists (2020), Survivors (2019), Mini Characters (2024, 12 characters × 32 animations including wheelchair use) and Blocky Characters 2.0 (June 2025, 18 characters, 27 animations) — [Kenney Protagonists](https://kenney.nl/assets/animated-characters-protagonists); [Kenney Mini Characters](https://kenney.nl/assets/mini-characters); [Kenney on X](https://x.com/KenneyNL/status/1932369466249142622)
- The older Animated Characters 1 and 2 have only idle, jump and run. Credit is optional — [OpenGameArt](https://opengameart.org/content/animated-characters)

**CMU Graphics Lab mocap**
- "Free for use in research and commercial projects worldwide". It may be copied, modified and redistributed, and included in commercially sold products, but "you may not resell this data directly, even in converted form" — [RancidMilk itch.io, quoting CMU](https://rancidmilk.itch.io/free-character-animations); [HF gbionics/cmu-fbx](https://huggingface.co/datasets/gbionics/cmu-fbx)
- The usual BVH set is cgspeed's MotionBuilder-friendly conversion of all 2548 motions. FBX conversions exist on itch.io (RancidMilk) and Hugging Face — [cgspeed](https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-motionbuilder-friendly-bvh-conversion-release-of-cmus-motion-capture-database)
- Some vendor blogs call it "public domain". That overstates it, because the no-resale clause is a real restriction. Expect to clean up jitter and foot slide — [MoCap Online](https://mocaponline.com/blogs/mocap-news/free-motion-capture-animations-guide)

**Bandai Namco Research Motion Dataset**
- Datasets 1 and 2 are now CC BY-NC 4.0 (in 2022 they were CC BY-NC-ND). The Blender visualisation script is MIT. For commercial use you have to contact them through acesinc.co.jp — [GitHub README](https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset); [CG Channel](https://www.cgchannel.com/2022/05/download-3000-free-mocap-moves-from-bandai-namco-research/)
- About 3,000 moves from three professional actors, in BVH, about 421K frames — [arXiv 2306.08861](https://arxiv.org/pdf/2306.08861)

**AMASS and SMPL**
- AMASS is only for non-commercial research, education or art. It is banned from commercial products and services, and it explicitly bans using it "to train methods/algorithms/neural networks/etc. for commercial use" — [AMASS LICENSE](https://github.com/nghorbani/amass/blob/master/LICENSE.txt)
- The SMPL model license has the same restrictions. Commercial licensing goes through Meshcapade — [SMPL license](https://smpl.is.tue.mpg.de/modellicense.html)
- One blog reports Epic Games acquired Meshcapade (announced Feb 2026, closed April), which leaves the future of SMPL commercial licensing uncertain. It names Apache-2.0 alternatives: Meta MHR and Naver Anny. This is a single-source claim — [clad.you blog](https://clad.you/blog/posts/body-pipeline/)

**Rokoko free packs**
- 263 free assets plus themed packs. Usable "in any animation, VFX, game, 3D project… including for commercial use". The Motion Library has free items and paid ones at $3–20. You need a Rokoko ID. Clips are FBX skeleton-only in Autodesk HIK naming — [Rokoko 263 assets](https://www.rokoko.com/resources/download-263-rokoko-motion-capture-assets); [Rokoko pricing](https://www.rokoko.com/pricing)

**Quaternius creatures (quadrupeds)**
- Ultimate Animated Animal Pack (2021): 12 animals (Cow, Donkey, Deer, Alpaca, Bull, Fox, Shiba Inu, Stag, Husky, Wolf, two horses), each with 12+ animations (attack, death, gallop, walk, jump…), in FBX, glTF and Blend, CC0 — [Quaternius](https://quaternius.com/packs/ultimateanimatedanimals.html)
- Farm Animal Pack: 7 animals, CC0. LowPoly Animated Animals on itch is CC0, but commenters report missing clips — [Poly Pizza](https://poly.pizza/bundle/Farm-Animal-Pack-1kUvRTPLzT); [itch.io](https://quaternius.itch.io/lowpoly-animated-animals)

**Meshy and Tripo libraries**: see section 2.

**Unity Asset Store and Fab/Unreal Marketplace assets in other engines**
- The standard Unity Asset Store EULA allows use as "embedded components of electronic games" without requiring Unity. "Restricted" assets, including Unity's own, are the exception. You may not redistribute raw assets, for example in a public repo or in an extractable mod. You must use the Unity editor to download them. Epic works the same way: general marketplace assets transfer, Epic's own do not. These are mostly community and secondary sources — [John Leonard French](https://johnleonardfrench.music/using-unity-assets-in-unreal-and-other-game-engines/); [Godot forum](https://forum.godotengine.org/t/am-i-permitted-to-use-assets-from-unity-assets-store-in-other-engines/79201)
- Unidot Importer brings .unitypackage content into Godot 4 — [Unidot](https://github.com/V-Sekai/unidot_importer)

### Inferences
- For a repo that may be public, use CC0 (Quaternius, Kenney) or CMU as the committed source. Mixamo, Rokoko and Asset Store clips can be used in a shipped game but should stay out of a public repo, because raw redistribution is banned or unclear.
- Mixamo's ban on ML training, and AMASS's ban on training for commercial use, mean neither should be fed into any fine-tuning step the agent might propose.
- UAL 1 + UAL 2 (250+ CC0 clips on one rig) is probably the largest consistent, freely redistributable humanoid set, so it makes a good canonical humanoid "body family" skeleton.

### Gaps
- I did not verify the exact clip lists or bone naming of the UAL 1 and UAL 2 rigs, or whether the two share an identical skeleton.
- No primary source said whether raw Rokoko files may be redistributed.
- I found no CC0 libraries of flyer, bird or wing animations.

## 2. Text-to-motion, AI motion and video mocap: quality, licensing, Mac hardware, cost

### Takeaway
Two open models are both commercially usable and runnable locally: Tencent HY-Motion 1.0 (open weights under a Tencent community license that excludes the EU, UK and South Korea; the repo claims macOS support) and NVIDIA Kimodo's SOMA and G1 checkpoints (NVIDIA Open Model License, commercial OK; the SMPL-X checkpoint is research-only). The academic models (MDM, MoMask, T2M-GPT, MotionGPT, Light-T2M) have MIT or Apache code, but their weights are trained on HumanML3D, which is AMASS-derived and output in SMPL, so commercial use is legally doubtful. Cloud services (Meshy, Tripo, Uthana, Rokoko Vision, DeepMotion, Move AI) are pay-per-use, and most free tiers are non-commercial or tightly capped.

### Cited Findings
**Open local models**
- **HY-Motion 1.0** (Tencent, released 2025-12-30): DiT + flow matching, 1.0B parameters, plus a 0.46B Lite. Ships a CLI and a Gradio app and claims macOS, Windows and Linux support. Outputs the SMPL-H skeleton, 22 body joints, no hands. Text encoders are Qwen3-8B + CLIP-L — [GitHub](https://github.com/Tencent-Hunyuan/HY-Motion-1.0); [MarkTechPost](https://www.marktechpost.com/2025/12/31/tencent-released-tencent-hy-motion-1-0-a-billion-parameter-text-to-motion-model-built-on-the-diffusion-transformer-dit-architecture-and-flow-matching/)
- HY-Motion license: "tencent-hunyuan-community", gated, EU disallowed. A secondary source says it excludes the EU, UK and South Korea. The SourceForge mirror's "MIT" label conflicts with the HF metadata and is probably wrong — [HF model card](https://huggingface.co/tencent/HY-Motion-1.0/blob/22f2bd01d6a4ab4bfab75142032a46acb851ce44/README.md); [The Rundown](https://www.therundown.ai/tools/hunyuan-motion-1-0)
- **NVIDIA Kimodo** (2026-03-16, arXiv 2603.15546): code is Apache-2.0. The SOMA and Unitree-G1 checkpoints (trained on Bones Rigplay / BONES-SEED) are under the NVIDIA Open Model License, "ready for commercial use". The SMPL-X checkpoint is under an NVIDIA R&D license, non-commercial only. The 700-hour training dataset is proprietary — [HF Kimodo-SOMA-RP-v1](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1); [HF Kimodo-SMPLX-RP-v1](https://huggingface.co/nvidia/Kimodo-SMPLX-RP-v1); [Pebblous](https://blog.pebblous.ai/blog/kimodo-text-to-motion/en/)
- **Academic models.** MoMask code is MIT. HumanML3D (repo MIT) is 14,616 motions taken from AMASS and HumanAct12 — [MoMask](https://github.com/EricGuo5513/momask-codes); [HumanML3D](https://github.com/EricGuo5513/HumanML3D). Light-T2M code is MIT, 4.48M parameters (about 10% of MoMask), and depends on SMPL, SMPL-X and PyTorch3D, each under its own license. It was trained on 2× RTX 3090Ti — [light-t2m](https://github.com/qinghuannn/light-t2m). MotionGPT code is MIT, built on a 220M Flan-T5 — [MotionGPT](https://github.com/OpenMotionLab/MotionGPT). T2M-GPT code is Apache-2.0, 247M — [T2M-GPT](https://github.com/Mael-zys/T2M-GPT)
- **Non-humanoid generation (research).** AnyTop (SIGGRAPH 2025) is a 2.28M-parameter diffusion model that generates motion for arbitrary skeleton topologies from the skeleton plus joint names, and generalises to unseen skeletons. It has no text control and a fixed maximum joint count — [arXiv 2502.17327](https://arxiv.org/abs/2502.17327); [UniMoGen](https://arxiv.org/pdf/2505.21837). A Dec 2025 paper adds text-to-motion for arbitrary animal skeletons (masked modelling) — [arXiv 2512.10352](https://arxiv.org/pdf/2512.10352)

**Cloud generators and services**
- **Meshy**: the Text-to-Motion API makes standalone 2–10 s clips and charges credits. You apply them through the Animation API (`motion_task_id`) within a 3-day retention window. There are 600+ library presets (FBX, GLB, USDZ), and several can go into one file. Presets and text-to-motion are humanoid only. Quadrupeds get a walk only, and `motion_task_id` rejects quadruped rigs. Some motions require a paid plan — [Meshy Text-to-Motion](https://docs.meshy.ai/en/api/text-to-motion); [Meshy Animation API](https://docs.meshy.ai/en/api/animation); [Meshy Animate guide](https://docs.meshy.ai/en/webapp/guides/animate). The game0 Meshy skill lists rig at 5 credits, animate at 3 credits per action, and text-to-motion at 10 (prime) or 3 (swift).
- **Tripo**: rig types are biped, quadruped, hexapod, octopod, avian, serpentine, aquatic and others. Rig model v2.5-20260210 covers creatures and v3.0-20260909 covers humanoids. The API's creature presets are mostly one locomotion clip each (`preset:quadruped:walk`, `hexapod:walk`, `serpentine:march`, `aquatic:march`…). Rigging is 25 credits and each retarget is 10 credits (about $0.01 per credit through inference.sh). The October 2026 update added humanoid text-to-motion and skeleton presets: UE5 Mannequin, Mixamo, VRM 1.0, Unity Humanoid, ActorCore — [Tripo docs](https://developers.tripo3d.ai/en/docs/animations-rig); [ComfyUI TripoRetargetNode](https://docs.comfy.org/es/built-in-nodes/TripoRetargetNode.md); [inference.sh](https://inference.sh/apps/tripo/tripo-rig); [Spatial Insiders](https://spatialinsiders.com/stories/tripo-rigging-animation-text-to-motion)
- **Uthana**: pay-as-you-go per generated second, no subscription. The free tier (third-party data) gives about 30 download-seconds a month under a non-commercial CC license, with API access. I found no per-second price — [Uthana blog](https://uthana.com/blog/how-uthanas-api-speeds-up-text-to-motion-animation); [aisotools](https://aisotools.com/pricing/uthana)
- **Rokoko Vision 3.0**: Starter is free with 30 s of video a month, unlimited text-to-motion and FBX. Basic is $10/mo annual (600 s, custom retargeting, BVH). Plus is $20/mo annual (3,000 s). Pro is $50/mo annual (15,000 s, CSV, API). Version 3.0 has no finger tracking and dropped the webcam and dual-camera modes — [Rokoko Vision](https://www.rokoko.com/products/vision)
- **DeepMotion**: a free test tier, plans from $9/mo, FBX/BVH/GLB. **Move AI**: pricing conflicts (pay-as-you-go from $0.012/s vs about $99/mo). Third-party sources only — [Sinfull Studios](https://sinfullstudios.com/move-ai-vs-rokoko-vs-deepmotion/); [Uthana roundup](https://uthana.com/resources/best-ai-motion-capture-tools)
- **Cascadeur 2026.2** (Aug 2026): added animation layers. The free tier is non-commercial, capped at 300 frames and 120 joints, with no FBX export. Indie is $19/mo or $96/yr for under $100k revenue. Pro is $49/mo or $396/yr. Both become perpetual after 12 months. AutoPhysics turns keyframes into physically plausible motion. Sources disagree on whether its environment-interaction part is Indie or Pro only — [CG Channel](https://www.cgchannel.com/2026/08/nekki-releases-cascadeur-2026-2-with-animation-layers/); [AWN](https://www.awn.com/news/cascadeur-ships-20262-animation-layers-and-3-new-languages); [FitGap](https://us.fitgap.com/products/009165/cascadeur)

**Video to motion, local**
- **FreeMoCap**: AGPL-3.0 since v0.0.25 (BSD before that). Markerless multi-camera capture with a Blender add-on. Current version 1.8.2. Alternative licensing is available on request — [FreeMoCap FAQ](https://docs.freemocap.org/documentation/frequently-asked-questions-faq.html); [PyPI](https://pypi.org/project/freemocap/)
- **GVHMR**: weights are non-commercial research only, and it needs the MPI-gated SMPL models. The original repo expects CUDA. The `ryanrudes/gvhmr` fork targets Apple Silicon (MPS), installs with `pip install gvhmr`, and has `gvhmr auth smpl` — [HF ryanrudes/gvhmr](https://huggingface.co/ryanrudes/gvhmr); [prompt2rig license table](https://github.com/blendi-remade/prompt2rig); [video-to-avatar-track-a](https://github.com/m-mohsin-zafar/video-to-avatar-track-a)
- Agent-oriented pipelines exist. `mixamo-llm-mocap` (MIT code) runs GVHMR, then a spec-driven retarget, then a Blender FK apply, and is built to be driven by an AI agent through MCP. `prompt2rig` runs a video model, then GVHMR, then a live Mixamo retarget — [mixamo-llm-mocap](https://github.com/squall01337/mixamo-llm-mocap); [prompt2rig](https://github.com/blendi-remade/prompt2rig)

### Inferences
- The AMASS clause banning training for commercial use plausibly taints any HumanML3D-trained checkpoint (MDM, MoMask, T2M-GPT, MotionGPT, Light-T2M) for commercial output, whatever the code license says. Treat them as prototyping tools only. This is my legal reading, not a confirmed ruling.
- The most viable local, commercially usable text-to-motion today is HY-Motion (if you are outside the EU, UK and South Korea, and the community license's commercial terms check out) or Kimodo-SOMA (if it runs on MPS). Both output human skeletons that need retargeting to the canonical rig (section 3).
- For creatures, no service gives a broad library. Tripo and Meshy give one locomotion clip per creature type. Plan on CC0 animal packs, hand or Cascadeur keying, and procedural layers (section 5).
- Video mocap on a Mac means either GVHMR-MPS (non-commercial weights) or FreeMoCap (AGPL software). Whether AGPL reaches the captured data is unclear. Rokoko Vision's paid tier is the clean commercial route.

### Gaps
- Not found: the exact commercial terms in the HY-Motion LICENSE.txt (for example user caps), and HY-Motion's training data.
- Kimodo's inference requirements (CUDA vs MPS) were not found.
- No license information was found for MDM or MotionLCM, or for WHAM and 4DHumans. Plask was not researched.
- No independent quality benchmark compares HY-Motion, Kimodo and the cloud services.

## 3. Converting SMPL / SMPL-X / BVH output to a game skeleton

### Takeaway
Typical pipeline: load SMPL params (`poses` (N,72) + `trans`) in Blender through the official SMPL-X add-on or softcat477/SMPL-to-FBX, then retarget onto the canonical rig with a Blender retargeter (section 4), then export glTF. Every step that touches SMPL model files inherits the non-commercial MPI license unless you buy a Meshcapade license.

### Cited Findings
- softcat477/SMPL-to-FBX: takes a pkl with `smpl_poses` (N,72) and `smpl_trans`. Has had a Blender add-on since 2023. Was built for AIST++ — [GitHub](https://github.com/softcat477/SMPL-to-FBX)
- The official MPI SMPL-X Blender add-on (Joachim Tesch) adds SMPL-X or SMPL+H as skinned meshes. It imports AMASS or SMPL-X animation formats and exports FBX for Unity and Unreal. The README covers Blender 4.5 extension paths. Download is gated by registration — [GitLab README](https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon/-/blob/master/README.md)
- mixamo-llm-mocap retargets SMPL-X joint rotations headlessly (`blender -b`, Blender 5.1+, `SMPLX_NEUTRAL.npz`) with scripts such as `retarget_smplx.py` — [GitHub](https://github.com/squall01337/mixamo-llm-mocap)
- Diffeomorphic BVH Retargeter supports Mixamo. One user improved bad hip transfer by deleting the target hip keys and using a Child Of constraint instead — [Diffeomorphic issue](https://bitbucket.org/Diffeomorphic/import_daz/issues/1975/pr-add-direct-fbx-mixamo-etc-import-to-bvh)

### Inferences
- An agent can script this headlessly: Blender in `-b` mode, a bone-name mapping from SMPL's 22 joints to the canonical humanoid, rotations only, plus hip translation scaled by the hip-height ratio.
- HY-Motion's SMPL-H 22-joint output needs the SMPL body model only for skinning and visualisation. Converting the joint rotations onto your own rig may not require shipping SMPL assets, but the license question remains. That is my inference.

### Gaps
- I found no maintained one-click SMPL → glTF game-rig converter.

## 4. Retargeting methods and proportion handling

### Takeaway
Godot 4 has the most complete built-in route. Import-time BoneMap + SkeletonProfileHumanoid + Rest Fixer normalises every humanoid to a shared rest, and motion scale comes from hip height. The 4.4+ RetargetModifier3D does the same at runtime while keeping the original rests. three.js `SkeletonUtils.retargetClip` is fragile when rest poses or proportions differ, so the dependable approach is to bake retargeted clips offline in Blender, or to normalise rests so a rotation-only clip works. Blender's best tool is Auto-Rig Pro Remap ($50). The free options are Expy Kit and its Blender 5 "Retarget" fork, the Rokoko plugin and KeeMap. Learned retargeting (SAN, R2ET) is research code trained on Mixamo.

### Cited Findings
**Godot 4**
- Workflow: Advanced Import → Skeleton3D → Retarget → bone_map. Set a BoneMap with SkeletonProfileHumanoid and bones auto-map. Mapping errors show magenta or red. "Remove Tracks → Unimportant Positions" keeps position tracks only on Root and Hips — [Godot docs: Retargeting 3D Skeletons](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- Rest Fixer reference: T-pose, facing +Z, right-handed Y-up, each bone's +Y pointing from parent to child. `scale_base_bone` = Hips, so Hips height becomes `motion_scale`, which handles proportion differences for root translation. "Overwrite Axis" is the key option for sharing animations, but it discards the DCC bone rests. "Fix Silhouette" is for A-pose models — [Godot docs](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- Blender glTF bones carry the edit-bone orientation as rest, so two rigs with the same names can still have different rests — [Godot docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- RetargetModifier3D (Godot 4.4, PR #97824): a parent skeleton uses the profile rest and a child skeleton keeps the original rest, which matters for IK poles and axis constraints. It also has import options to split off unmapped bones — [PR #97824](https://github.com/godotengine/godot/pull/97824); [Godot blog: IK returns in 4.6](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)
- To change the pose after retargeting, put SkeletonModifier3D children (IK, spring bones) under the target skeleton. Modifiers always run after AnimationMixer playback — [RetargetModifier3D docs via godot-rust](https://godot-rust.github.io/docs/gdext/pr-1552/godot/classes/struct.RetargetModifier3D.html)
- Godot 4.6 brought IK back (IKModifier3D, ChainIK3D, built on BoneConstraint3D and SpringBoneSimulator3D), which supports a foot- or hand-IK post-pass — [Godot blog](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)

**three.js**
- `SkeletonUtils.retargetClip(target, source, clip, options)` options: useFirstFramePosition, fps, names (bone map), getBoneName, trim. The forums mention preservePosition, preserveHipPosition and preserveMatrix — [three.js docs](https://threejs.org/docs/pages/module-SkeletonUtils.html)
- Known problems: inverted feet and backward hands even on near-identical Mixamo rigs. Shorter or taller models move strangely. Turning off preserve*Position fixes orientation but distorts skinning. The output is always one frame short (#25288). Passing SkeletonHelper inputs as documented throws errors (#25751). One user keeps a separate animation folder per character scale — [three.js forum](https://discourse.threejs.org/t/skeletonutils-retarget-doesnt-work-with-mixamorig-skeleton-inverted-feet-backward-hands/54892); [forum: fixing retarget](https://discourse.threejs.org/t/fixing-skeletonutils-retarget-and-retargetclip-functions/65149); [#25288](https://github.com/mrdoob/three.js/issues/25288)

**Blender tools**
- Auto-Rig Pro Remap: $50, supports Blender 2.93–5.2. Handles different bone names and orientations, has a Mixamo preset, and auto-scales the source. CGDive says even Rokoko's developers recommend it — [StraySpark](https://www.strayspark.studio/blog/best-blender-animation-addons-2026); [CGDive](https://addons.cgdive.com/sub-categories/blender-retargeting-addons)
- Expy Kit: free, with a $5 tier, v0.6.1. Presets for Mixamo, Mocap Online and UE5 mannequins. The "Retarget" extension by KBS-DEV is a Blender 5+ fork of Expy Kit and AnimAide with presets for Mixamo, Unreal, VRoid, MMD, Daz and ARP — [Blender Extensions: Retarget](https://extensions.blender.org/add-ons/retarget/); [BlendAtlas](https://blendatlas.com/products/expy-kit-import-convert-export-characters-in-blender)
- Rokoko plugin: free, but bone mapping is manual. KeeMap: free and open source, saves mapping files, last tested on Blender 3.3.1 — [KeeMap](https://github.com/nkeeline/Keemap-Blender-Rig-ReTargeting-Addon)
- Quadruped caution: name-based matching that assumes a humanoid sent the front and back legs (FrontUpLeg and BackUpLeg) to the same joint, so "legs move sideways". Separate front and back mappings fixed it (40° → 4.4° error) — [QtMeshEditor PR #1085](https://github.com/fernandotonon/QtMeshEditor/pull/1085)

**Learned retargeting**
- R2ET (CVPR 2023) uses a skeleton-aware module to preserve semantics, a shape-aware module to reduce interpenetration and contact loss, and a balancing gate. Single inference, trained and evaluated on Mixamo. Code at github.com/Kebii/R2ET — [arXiv 2303.08658](https://arxiv.org/abs/2303.08658)
- SAN and NKN work on skeleton-level features and show high interpenetration and weak semantics preservation — [arXiv 2312.01964](https://arxiv.org/pdf/2312.01964). (SAN is Aberman et al., SIGGRAPH 2020, deep-motion-editing repo. This is from memory and not verified in this search.)

### Inferences
- Recommended skill design: one canonical rig per body family. Normalise every incoming character to it in Blender, with the same bone names, the same rest axes and a T-pose. Then the library clips play rotation-only. Root and hip translation scales by the hip-height ratio, which is what Godot's motion_scale does and what you would hand-roll in three.js. Follow with a runtime IK pass for foot locking and hand-on-prop. In Godot use RetargetModifier3D plus IK modifiers. In three.js use a CCDIKSolver or custom two-bone IK. That is my inference.
- In three.js, avoid runtime `retargetClip` across rigs that differ. Bake per-rig clips offline in Blender, or guarantee identical rest poses so a single clip is valid on every rig.
- R2ET is trained on Mixamo data, which Mixamo's ML ban affects, and it is CUDA-centric. It is not a practical production tool here.

### Gaps
- I did not find whether three.js has added a newer official retargeting utility since r16x.
- No source benchmarked rotation-only vs scaled-root retargeting on extreme proportions such as chibi or giant characters.

## 5. Non-humanoid animation: creature libraries, generators and procedural secondary motion

### Takeaway
Creature libraries are thin: Quaternius CC0 animal packs, plus Tripo creature rigs with one preset per type. Research models (AnyTop, topology-agnostic text-to-animal) are not production tools yet. The scalable approach is a small keyed or CC0 base set per family, with procedural secondary motion layered on top. Godot 4.5+ has SpringBoneSimulator3D. three.js can drive arbitrary bone chains with three-vrm's VRMSpringBoneManager.

### Cited Findings
- Quaternius animal packs (CC0), the Tripo creature rigs and presets, and Meshy's quadruped walk-only limit: see sections 1 and 2.
- **Godot SpringBoneSimulator3D** (added in 4.5): wiggles hair, cloth and tails and returns to the original pose. One root-to-end chain per setting, with no branched (Y) chains. SpringBoneCollision3D child nodes give collisions that don't use PhysicsServer. Do not scale the parent Skeleton3D or its bones — [Godot docs](https://docs.godotengine.org/en/stable/classes/class_springbonesimulator3d.html)
- Also new in 4.5: BoneConstraint3D, AimModifier3D, CopyTransformModifier3D and ConvertTransformModifier3D. 4.4 added LookAtModifier3D. These are useful for heads, ears and eyes tracking targets — [Godot blog](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)
- Official demos are thin. An open issue says the docs are not enough to understand how to use RetargetModifier3D and SpringBoneSimulator3D — [godot-demo-projects #1170](https://github.com/godotengine/godot-demo-projects/issues/1170)
- **three-vrm spring bones**: `VRMSpringBoneManager` has a public constructor and `addJoint`, `setInitState`, `update`. `VRMSpringBoneJoint(bone, child, settings, colliderGroups)` takes plain Object3Ds, so it can probably drive non-VRM chains. Colliders are spheres and capsules. Scale stiffness, hitRadius and colliders with the model's scale — [three-vrm VRMSpringBoneManager](https://pixiv.github.io/three-vrm/docs/classes/three-vrm.VRMSpringBoneManager.html); [VRMSpringBoneJoint](https://pixiv.github.io/three-vrm/docs/classes/three-vrm.VRMSpringBoneJoint.html); [scaled models doc](https://pixiv.github.io/three-vrm/docs/documents/spring-bones-on-scaled-models.html)
- The last bone of each chain needs a child or tail, or the physics breaks — [agentskills vrm-springbone guide](https://agentskills.so/skills/project-n-e-k-o-neko-vrm-springbone-physics)
- AnyTop and its text-driven follow-up: see section 2 — [arXiv 2502.17327](https://arxiv.org/abs/2502.17327); [arXiv 2512.10352](https://arxiv.org/pdf/2512.10352)

### Inferences
- Body-family plan: give quadrupeds a canonical rig modelled on the Quaternius animal skeleton with explicit front and back leg names, a flyer rig with wing chains, and so on. Key or source about 10–15 core clips per family (idle, walk, run, attack, hit, death, jump). Then procedurally add tails, ears, wings, mantles and hair with spring chains. Optionally add procedural foot placement with IK (ChainIK3D in Godot 4.6). My inference.
- Spring chains must not be branched in Godot. Model tails, ears and mantle strips as separate linear chains.

### Gaps
- No good source was found for open procedural quadruped locomotion libraries in Godot or three.js, or for wing-flap generators.
- I found no license or weight details for the topology-agnostic animal model in arXiv 2512.10352.

## 6. Facial animation: blend shapes, ARKit 52, lip sync

### Takeaway
Standardise on ARKit 52 morph target names. glTF morph targets map straight onto three.js and Godot blend shapes. For lip sync on a Mac, Rhubarb (MIT, 9 mouth shapes, the output belongs to you) is the practical choice. NVIDIA Audio2Face-3D is open (SDK MIT, weights under the NVIDIA Open Model License, training framework Apache), but it ships as ONNX-TRT and targets NVIDIA hardware.

### Cited Findings
- ARKit 52: values run from 0 to 1. The full name list (eyeBlinkLeft…tongueOut) is in the Ready Player Me docs. In glTF these shapes are morph targets — [Ready Player Me](https://docs.readyplayer.me/ready-player-me/api-reference/avatars/morph-targets/apple-arkit); [miniface FACS reference](https://miniface.org/faces)
- VRM "Perfect Sync" means adding the 52 ARKit shapes to VRoid models. Models without ARKit shapes use VRM 0.x names (Blink_L…) — [Warudo docs](https://docs.warudo.app/docs/tutorials/3d-primer)
- Tools: `arkit-blendshape-tool` transfers 52 ARKit shapes plus 15 Oculus visemes from a reference GLB to a target GLB. `face-to-blendshape-3d` builds ARKit GLBs from MediaPipe — [arkit-blendshape-tool](https://github.com/digitalp/arkit-blendshape-tool); [face-to-blendshape-3d](https://github.com/arturwyroslak/face-to-blendshape-3d)
- Rhubarb Lip Sync: MIT with permissive dependencies. The output data belongs to the user. Outputs mouth shapes A–H and X in TSV, XML or JSON. Godot plugins exist (godot-baked-lipsync, MIT, which auto-downloads Rhubarb and excludes it from exports). A three.js/R3F tutorial maps visemes onto morph targets — [Rhubarb LICENSE](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md); [godot-baked-lipsync](https://github.com/fbcosentino/godot-baked-lipsync); [Wawa Sensei](https://wawasensei.dev/tuto/react-three-fiber-tutorial-lip-sync)
- Audio2Face-3D (open-sourced September 2025): the SDK (C++/Python) is MIT. The regression (2.3) and diffusion (3.0) weights are in ONNX-TRT format under the NVIDIA Open Model License, commercial OK. The training framework is Apache. Audio2Emotion is included, and there are UE5 and Maya plugins — [NVIDIA ACE for Games](https://developer.nvidia.com/ace-for-games); [HF Audio2Face-3D-v3.0](https://huggingface.co/nvidia/Audio2Face-3D-v3.0)

### Inferences
- Because Audio2Face ships as ONNX-TRT, it is effectively tied to NVIDIA TensorRT. Running it on Apple Silicon would need an ONNX re-export or conversion, which is unverified. Rhubarb plus a viseme-to-ARKit mapping table is the Mac-friendly default.
- Stylised creatures with no faces can skip ARKit and use a few custom shapes (blink, mouth open, snarl).

### Gaps
- I did not research the VRM 1.0 expression presets and how they map to ARKit, or how Godot's VRM addon handles them.
- No source confirmed whether Audio2Face runs on CPU or CoreML on a Mac.

## 7. Runtime: Godot AnimationTree, root motion, compression; three.js AnimationMixer and glTF animation size

### Takeaway
In Godot 4, root motion comes from `AnimationTree.root_motion_track` (a POSITION_3D or ROTATION_3D track) plus the per-frame delta and accumulator getters. In three.js, animation size is controlled offline with gltf-transform (`resample` → `meshopt`) and decoded at runtime with MeshoptDecoder.

### Cited Findings
- Godot: `root_motion_track` must point at a position, rotation or scale 3D track. That motion is cancelled visually. `get_root_motion_position()`, `get_root_motion_rotation()` and `get_root_motion_scale()` give deltas, and the `*_accumulator()` variants give blended values. They return zero or identity if the track type doesn't match. Godot 3's transform-track APIs are gone — [Godot AnimationTree docs source](https://github.com/godotengine/godot-docs/blob/master/tutorials/animation/animation_tree.rst); [AnimationTree class 4.0](https://docs.godotengine.org/en/4.0/classes/class_animationtree.html)
- Root motion is a position delta per frame, so divide by delta to get CharacterBody3D velocity. Set the root track with "Set As Root Motion Track" in AnimationPlayer — [MoCap Online Godot guide](https://mocaponline.com/blogs/mocap-news/motion-capture-godot-guide)
- With SkeletonProfileHumanoid, only Root and Hips keep position tracks. Pair this with a "Root" bone for root motion — [Godot retargeting docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
- glTF size: `gltf-transform resample` drops collinear keyframes (tolerance 1e-4, effectively lossless). Reported savings range from about 45% to nothing, depending on the file. `optimize` includes resample. Meshopt compresses animation keyframes and morph targets, which Draco does not. Gzip or Brotli on top gives the best ratio. Don McCurdy recommends resample → quantize → meshopt — [glTF Transform](https://gltf-transform.dev/); [three.js forum](https://discourse.threejs.org/t/is-there-a-tool-to-optimize-keyframes-in-gltf/28715); [Blender Artists (McCurdy)](https://blenderartists.org/t/how-to-reduce-gltf-file-size/1344466/2)
- three.js: GLTFLoader needs `MeshoptDecoder` from `three/addons/libs/meshopt_decoder.module.js` (r122+). In Meshy's cookbook, a character with idle, run and attack clips plus a WebP texture comes out at 0.59–0.68 MB after dedup, prune, resample and meshopt — [Cinevva GLB guide](https://app.cinevva.com/guides/optimize-glb-for-web); [Meshy cookbook](https://www.meshy.ai/developers/cookbook/recipes/animate-character-in-threejs/)
- gltf.report shows a per-model size breakdown, including animation — [Cinevva](https://app.cinevva.com/guides/optimize-glb-for-web)

### Inferences
- For a shared library on many three.js bodies, ship each family's clips once in an animation-only GLB with no mesh, and bind them by bone name to every rig that shares the canonical skeleton. Many AnimationMixers can reuse one AnimationClip. This only works if rests and names match, which reinforces the "normalise rigs offline" approach from section 4. My inference.
- In Godot, keep one AnimationLibrary resource per family and share it across characters after BoneMap import.

### Gaps
- Nothing was found on how Godot's import-time animation compression (`animation/compression`, page size) affects quality or root-motion drift.
- I found no three.js AnimationMixer performance numbers for many characters, such as instanced skinning or a VAT/baked-texture alternative.
