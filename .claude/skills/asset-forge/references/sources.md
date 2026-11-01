# Sources, tools and licences

Evidence and prices: `docs/reports/AI 3D game asset pipeline.md` (November 2026). Re-check prices and licences before relying on them.

## Allowed

| Source | Use for | Licence and limits |
| --- | --- | --- |
| Meshy (API + web app) | Bodies, gear, parts, props, environment; rigging and preset clips on the web app | Paid plan: you own outputs. Free-plan outputs are CC BY 4.0. Through the `meshy` skill only |
| TRELLIS.2 (Microsoft) via `trellis-mac` | Free local alternative to Meshy for shapes; worth an A/B on game0 concept art | MIT. Needs about 18–24 GB unified memory; this Mac has 24 GB, so run it with nothing else open, ~3.5 min per textured model. Not installed yet |
| MakeHuman / MPFB2 assets | Humanoid base mesh, body and face targets, weights | **CC0**, explicitly allowed in your own in-game creator. MPFB code is GPL: use the data, not the code, in the game |
| Quaternius UAL 1+2, animal packs | Clip libraries | CC0 |
| Kenney | Placeholder props and kits | CC0 |
| Poly Haven, ambientCG | Textures, HDRIs, some models | CC0 (Poly Haven's API asks for credit and a unique User-Agent) |
| CMU mocap | Extra clips | Commercial use allowed; don't redistribute the raw data |
| Rokoko free packs, Mixamo | Clips | Commercial use allowed, **raw files never in the public repo**; retargeted clips only. Mixamo: no ML training use |
| Blender add-ons | Robust Weight Transfer (free), Rigify, Rigodotify, Expy Kit / Retarget, ARKit blendshape baker | Free |
| Godot 4.7, gltf-transform, meshoptimizer | Validation, web builds | MIT |

## Not allowed

| Source | Why |
| --- | --- |
| Hunyuan3D 2.x, Hunyuan3D-Part, Hunyuan-Paint (incl. the MLX port), HY-Motion, any Tencent model | Licence excludes the EU, UK and South Korea, including outputs |
| Reallusion Character Creator / ActorCore content | EULA forbids use in an in-game character creator |
| Daz content | Per-product interactive licences; not worth it |
| SMPL, SMPL-X, STAR, AMASS, and motion models trained on them (MDM, MoMask, T2M-GPT, MotionGPT, …) | Non-commercial without a paid licence |
| Bandai Namco motion dataset | CC BY-NC |
| Pixal3D | Licence is contradictory |
| Tripo, Rodin, cloud GPUs (fal, Replicate, RunPod) | Not in budget (decision 2026-11-01); ask before changing |

## Not usable on this Mac

UniRig, Puppeteer, MagicArticulate, Hunyuan3D-Part, PartCrafter and most part-segmentation models need CUDA. SkinTokens has an MPS port (`chris-straka/skintokens`, about 45 s per character); its weights' licence is unverified, so check it before use. It's the best option for skinning a creature onto a given skeleton when weight transfer from a base isn't possible.
