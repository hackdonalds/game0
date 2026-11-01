# MCP servers, agent skills and AI-agent workflows for 3D game asset creation (as of Nov 2026)

Note on sources: many 2026 "comparison" blogs (StraySpark, Summer Engine, 3daistudio, Erodenn, Cinevva) are written by vendors of competing tools; that bias is flagged inline. "Local observation" = tool list visible in this project's own Claude session (Blender MCP + Meshy MCP connected), not a web source.

## 1. Blender MCPs: ahujasid/blender-mcp, the official Blender Lab MCP, forks; tools, security, stability, headless modes

### Takeaway
Two main lines exist: the official Blender Lab MCP (projects.blender.org/lab/blender_mcp, v1.0.x, Blender 5.1+, docs-lookup + code-exec + screenshot/render tools, also what Claude's Blender connector uses) and ahujasid's community server (now "MCP for Blender", repo ahujasid/mcp-for-blender), which adds asset/generator integrations (Poly Haven, Sketchfab, Rodin, Hunyuan3D, Tripo, Meshy). Both execute arbitrary LLM Python in Blender with no sandbox; main-thread blocking and timeouts are the dominant stability problem.

### Cited Findings
- Blender Lab hosts an official MCP server at projects.blender.org/lab/blender_mcp, described as a lightweight MCP server offering a natural-language interface to Blender's Python API, improved documentation access, and help exploring complex setups; distributed as a Blender Extension (drag-drop twice: once to add the Lab repo, once to install); started from Preferences > Add-ons > MCP > Start MCP Server; .mcpb package for newer clients — [Blender Lab MCP page](https://www.blender.org/lab/mcp-server/)
- Third-party claim: v1.0.0 released 27 Apr 2026, v1.0.3 current as of Sept 2026, requires Blender 5.1+, used by Anthropic's Blender connector for Claude; recommends running it in a VM because it executes LLM code without guards against data removal/exfiltration (vendor-biased source) — [StraySpark comparison](https://www.strayspark.studio/blog/official-blender-mcp-server-comparison-2026)
- Local observation: the Blender MCP connected in this project exposes `execute_blender_code` and `execute_blender_code_for_cli`, `get_python_api_docs`, `search_api_docs`, `search_manual_docs`, `get_objects_summary`, `get_object_detail_summary`, blend-file summaries (datablocks, missing files, linked libraries, path info, usage guess, each with a `_for_cli` variant), `get_screenshot_of_window_as_image/json`, `get_screenshot_of_area_as_image`, `render_thumbnail_to_path`, `render_viewport_to_path`, and `jump_to_*` navigation tools. Server instructions bundle Blender API and manual RST files (`data/api/`, `data/manual/`) and say code exec is a "last resort", and warn about mode/active-object/selection context and bmesh flush. The `_for_cli` variants indicate a headless/background-Blender mode exists alongside the live-GUI mode. — local observation (session tool list)
- ahujasid/blender-mcp architecture: LLM client <-MCP-> server.py <-TCP:9876-> Blender addon.py; integrations Sketchfab search/download, Hyper3D Rodin and Hunyuan3D generation, Poly Haven; API keys via addon prefs or env vars (BLENDERMCP_SKETCHFAB_API_KEY, BLENDERMCP_HUNYUAN3D_SECRET_ID/SECRET_KEY); README warns `execute_blender_code` runs arbitrary Python; collects anonymous telemetry unless DISABLE_TELEMETRY=true — [ahujasid/blender-mcp README](https://github.com/ahujasid/blender-mcp/blob/main/README.md)
- Successor repo ahujasid/mcp-for-blender ("Community plugin... Not affiliated with the official Blender Foundation") consolidates into `generate_3d` (one call to generate+import via Tripo, Hunyuan3D, Hyper3D Rodin or Meshy) and `search_assets`/`import_asset` (incl. Sketchfab); still runs any Python by default — [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender)
- Per mcp.so: Poly Haven needs no key (CC0); Sketchfab and Poly Pizza need keys; Sketchfab, Poly Pizza, Hyper3D, Hunyuan3D run on your own keys, with an optional paid Premium tier; add-on MIT; tool prompt suggests Sketchfab first for specific real objects, then Poly Haven, then Hyper3D Rodin for unique items — [mcp.so blender-mcp](https://mcp.so/servers/blender-mcp)
- Security: GitHub issue #203 reports SSRF in `import_generated_asset_hunyuan` — `zip_file_url` is client-supplied, so a prompt injection can make Blender fetch an arbitrary URL; fix status unknown — [Issue #203](https://github.com/ahujasid/blender-mcp/issues/203)
- Forks: naab007/blender_mcp (92 tools, Blender 4.x, telemetry removed; Sketchfab tools get_sketchfab_status/search_sketchfab_models/get_sketchfab_model_preview/download_sketchfab_model; Hunyuan tools generate_hunyuan3d_model/poll_hunyuan_job_status/import_generated_asset_hunyuan) — [naab007/blender_mcp](https://github.com/naab007/blender_mcp); DeemosTech Rodin-integration fork v1.5.5 — [DeemosTech](https://github.com/DeemosTech/blender-mcp-rodin-integration); PoBruno/mcp-blender-agent (~216 tools, MIT, Blender 4.2+), poly-mcp/blender-mcp-server (51 tools), BlendRelay (Blender 4.5+), tahooki/unreal-blender-mcp — [PoBruno](https://github.com/PoBruno/mcp-blender-agent), [poly-mcp](https://github.com/poly-mcp/blender-mcp-server), [BlendRelay](https://pypi.org/project/blendrelay-mcp/0.7.0/); rotembab/claude-blender-integration (addon+MCP+agent layer; Rigify, bind_mesh, weight tools, experimental UniRig) — [rotembab](https://github.com/rotembab/claude-blender-integration)
- Community servers like djeada/blender-mcp-server ship their own add-on/protocol and cannot be mixed with the official one — [StraySpark](https://www.strayspark.studio/blog/official-blender-mcp-server-comparison-2026)
- Stability: README advice for timeouts is "simplify / break into smaller steps"; DeepWiki lists causes: large Poly Haven/Sketchfab downloads, heavy bpy in execute_code, polling Hyper3D/Hunyuan jobs, blocking external calls on the main thread; addon uses `client.sendall()` without message framing so large responses can fragment — [DeepWiki troubleshooting](https://deepwiki.com/ahujasid/blender-mcp/6.2-error-handling-and-troubleshooting)
- Known failure: first tools/call hangs, client cancels at exactly 4 min with "MCP error -32001: Request timed out", Blender's result arrives ~1 min later with "Incomplete JSON response received"; every bpy call runs on Blender's main thread so a heavy boolean/bake/download blocks all; some servers have a 5 s default script time limit (vendor-biased) — [StraySpark fix guide](https://www.strayspark.studio/blog/blender-mcp-not-working-fix-connection-2026)
- Calling bpy from a background thread hard-crashes Blender; workaround is dispatch via `bpy.app.timers` with a wait timeout (30 s in example) — [Medium: building an MCP inside Blender](https://medium.com/@anvilinteractivesolutions/how-i-built-a-full-mcp-server-inside-blender-and-why-it-was-harder-than-it-sounds-187535b2d576)
- A security-focused fork removed telemetry, added token auth, and set timeout=30 on external HTTP requests (many previously had none) — [AxiumForge/blender-mcp](https://github.com/AxiumForge/blender-mcp)

### Inferences
- For a pipeline skill, the official Lab MCP (already connected here) is the right "driver": it has API-doc search (combats hallucinated bpy), render/screenshot tools (enables critique loops) and CLI variants (headless batch). Generator integrations are better called directly via their own MCPs (Meshy) than through ahujasid's addon.
- Long ops (bakes, decimation of 1M-tri AI meshes, downloads) should go to background `blender -b --python script.py` subprocesses run via Bash, not the live MCP socket, to avoid the 4-minute client timeout and main-thread lock.

### Gaps
- Exact official changelog/tool list for Blender Lab MCP v1.0.3 not fetched from primary source; mapping of `_for_cli` semantics (spawns background Blender? operates on a .blend path?) not confirmed from docs.
- Whether issue #203 is fixed in mcp-for-blender.

## 2. Generator MCPs: Meshy, Tripo, Hunyuan3D, Rodin, Sketchfab/Poly Haven, ComfyUI, fal/Replicate

### Takeaway
Meshy has the most complete official MCP (24–28 tools covering generate, remesh, UV, rig, animate, text-to-motion, retexture, convert/resize). Tripo's official MCP is stale alpha. Free/local on Apple Silicon is feasible via TRELLIS.2 (trellis-mac) and Hunyuan3D 2.x Mac forks, but none ship a polished MCP for Mac; ComfyUI now has first-party MCPs (cloud and local).

### Cited Findings
- Meshy official MCP: `@meshy-ai/meshy-mcp-server`, MIT, source github.com/meshy-dev/meshy-mcp-server, local stdio only (no hosted endpoint), Node 18+, MESHY_API_KEY, `claude mcp add meshy --env MESHY_API_KEY=... -- npx -y @meshy-ai/meshy-mcp-server`; Meshy also ships a skill package `npx skills add meshy-dev/meshy-3d-agent` — [Meshy AI integration docs](https://docs.meshy.ai/en/api/ai); [npm](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server)
- Tool counts differ: npm lists 24 tools; NousResearch Hermes plugin uses v0.6.5 (2026-10-22) with 28 tools (~19K tokens of schemas) — [npm](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server); [Hermes meshy plugin](https://github.com/NousResearch/hermes-official-plugins/tree/main/meshy)
- Local observation: connected Meshy MCP exposes text_to_3d(+refine), image_to_3d, multi_image_to_3d, text_to_image, image_to_image, remesh, uv_unwrap, rig, animate, list_animations, text_to_motion, retexture, convert, resize, auto_split, printability tools, creative_lab, check_balance, list_usage, list_tasks/models, get_task_status, cancel_task, download_model. Server instructions mandate cost confirmation before credit-spending calls, "never re-create a task you are unsure about" (check list_tasks after timeout/5xx since task may have been charged), and fixing target_formats at creation. Credit table (as of 2026-10-12): text-to-3D preview 20 (meshy-6/7.1) or 5 (lite/t2); image-to-3D 5–35 depending on model/texture; remesh/rig/UV 5; animate 3 per action; text_to_motion 10/3; retexture/refine 10; convert/resize 1 — local observation (Meshy MCP server instructions)
- Tripo official MCP (VAST-AI-Research/tripo-mcp): alpha, "currently supports Tripo Blender Addon integration", MIT, created 2025-03-21, last pushed 2025-04-14, ~189 stars; `uvx tripo-mcp`; inspired by blender-mcp — [GitHub](https://github.com/VAST-AI-Research/tripo-mcp); The1Studio fork is generation-only (create_3d_model_from_text/image, get_task_status, returns pbr_model_url GLB) — [The1Studio/tripo-mcp](https://github.com/The1Studio/tripo-mcp); AgentSeal scanner gave official repo 55/100 with 7 critical/high findings (third-party automated score) — [AgentSeal](https://agentseal.org/mcp/https-githubcom-vast-ai-research-tripo-mcp)
- Hunyuan3D on Mac: alawrenceld/Hunyuan3D_Blender (Hunyuan3D-2.0, `api_server.py --device mps --port 8081`, Blender MCP integration, 16 GB RAM min/32 GB rec, 50 GB disk, 3–5 min/generation) — [GitHub](https://github.com/alawrenceld/Hunyuan3D_Blender); Brainkeys/Hunyuan3D-2.1-mac (native MPS, `--low_vram_mode --disable_tex`, PYTORCH_ENABLE_MPS_FALLBACK=1, ~5–10x slower than CUDA) — [README_macOS](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md); hunyuan3d-2.1 MPS/ROCm fork with PBR texturing (texturing 512 s "Safe" preset on M4 Pro, ~8 GB swap peak; ~30 GB weights) — [thehunterofshadows fork](https://github.com/thehunterofshadows/hunyuan3d-2.1-intel), [CPU3D](https://cpu3d.com/en/ai3d/hunyuan3d-mac/)
- TRELLIS.2 on Apple Silicon (trellis-mac): MPS port replacing CUDA ops; ~400K-vertex mesh from single photo in ~3.5 min on M4 Pro 24 GB; ~18 GB peak unified memory; GLB with base-color/metallic/roughness; ~15 GB first-run weight download — [Show HN](https://news.ycombinator.com/item?id=47828896); [trellis-mac](https://github.com/shivampkumar/trellis-mac/wiki)
- ComfyUI: hosted Comfy Cloud MCP, Partner MCP, and first-party local MCP driving your own ComfyUI via comfy-cli; can generate 3D from text/images; community servers artokun/comfyui-mcp, shawnrushefsky/comfyui-mcp, joenorton/comfyui-mcp-server, lalanikarim/comfy-mcp-server — [ComfyUI agent-tools docs](https://docs.comfy.org/agent-tools/index.md); official TRELLIS.2 ComfyUI workflow (4B params, bundled with Pixal3D), MPS support not stated — [ComfyUI TRELLIS.2 tutorial](https://docs.comfy.org/tutorials/3d/trellis2)
- Ladvien/trellis2_mcp: image → 3D → rigged-character MCP; FLUX.2 on MLX for images but TRELLIS on RTX 3090 — [glama](https://glama.ai/mcp/servers/Ladvien/trellis2_mcp/tree); trellis-mcp (PyPI) for TRELLIS v1 with self-hosted backend — [PyPI](https://pypi.org/project/trellis-mcp/)
- Rodin: integrated through DeemosTech's blender-mcp fork — [DeemosTech](https://github.com/DeemosTech/blender-mcp-rodin-integration)

### Inferences
- On Apple Silicon, a local generator path = wrap trellis-mac or Hunyuan3D-2.1-mac `api_server.py` in a tiny MCP or just call it from a skill script via Bash; expect 3–10 min per asset and ~18–32 GB RAM, so batch overnight and cache aggressively.
- Meshy's `meshy_remesh`/`meshy_rig`/`meshy_animate` (5/5/3 credits) are a cheap cloud fallback for retopo and humanoid rigging versus building local solutions.

### Gaps
- No primary source found for an official Hunyuan3D MCP (Tencent) or official Rodin standalone MCP; fal/Replicate MCP servers for 3D were not researched (out of tool budget).
- Whether ComfyUI TRELLIS.2/Hunyuan nodes run on MPS.

## 3. Engine MCPs: Godot, Unity, Unreal; three.js tooling

### Takeaway
Godot has many community MCPs; Coding-Solo/godot-mcp (free, CLI-driven, ~4.6K stars) is the simplest; GDAI MCP ($19) and Godot MCP Pro ($15) are paid editor plugins. Unity and Unreal both shipped official MCPs in 2026 (Unity has since moved it to the Unity CLI). For three.js, the relevant tooling is gltf-transform/gltfpack plus three.js skills.

### Cited Findings
- Coding-Solo/godot-mcp: launches editor, runs projects, captures debug output; `npx @coding-solo/godot-mcp`; CLI-driven (no in-editor addon); MIT; ~4,578 stars, last activity 2026-04-16; no screenshot/input tools; tugcantopaloglu fork grows it to 157 tools (screenshots, input, C#) — [DEV roundup](https://dev.to/orellanaed/the-best-godot-mcp-server-in-2026-depends-on-what-you-want-the-agent-to-touch-5aji); [Erodenn comparison (competitor)](https://github.com/Erodenn/godot-mcp-runtime/blob/main/docs/comparison.md)
- GDAI MCP (3ddelano, Godot 4.1+): paid ($19 one-time), proprietary, editor plugin, "most polished"; older Summer Engine article calling it open source is contradicted by its own later update — [Summer Engine GDAI alternatives (competitor)](https://www.summerengine.com/blog/gdai-mcp-alternative); [Summer Engine roundup](https://www.summerengine.com/blog/best-godot-mcp-server)
- Others: Godot MCP Pro ($15, most tools, runtime support), godot-ai (free, in-editor), bradypp/godot-mcp, ee0pdt/Godot-MCP (no updates since March 2025), Godot MCP Runtime, GoPeak — [DEV roundup](https://dev.to/orellanaed/the-best-godot-mcp-server-in-2026-depends-on-what-you-want-the-agent-to-touch-5aji); [3daistudio Godot MCP guide](https://www.3daistudio.com/3d-generator-ai-comparison-alternatives-guide/godot-mcp)
- Unity: Unity AI open beta (May 4, 2026) with Ask/Agent/Plan modes, an MCP server in com.unity.ai.assistant (Unity 6+), supports Claude Code/Cursor/Windsurf — [Cinevva news](https://app.cinevva.com/news/2026-05-04-unity-ai-open-beta), [Unity blog](https://unity.com/blog/unity-ai-how-to-get-started); in-Editor MCP since deprecated, replaced by `unity mcp` in Unity CLI — [Unity Docs](https://docs.unity.com/en-us/unity-cli/replace-mcp-server-unity-cli); community: CoplayDev Unity MCP (~9.7K stars), IvanMurzak/Unity-MCP — [StraySpark (vendor)](https://www.strayspark.studio/blog/unity-mcp-server-vs-unreal-godot-blender-2026)
- Unreal: UE 5.8 introduced an experimental official in-editor MCP server — [note.com](https://note.com/kagawatomo/n/na6d10e54d4ee?hl=en); community chongdashu Unreal MCP (1,200+ stars) — [StraySpark (vendor)](https://www.strayspark.studio/blog/unity-mcp-server-vs-unreal-godot-blender-2026)
- three.js: CloudAI-X/threejs-skills (GLTF loading side) — [GitHub wiki](https://github.com/CloudAI-X/threejs-skills/wiki); freshtechbro `blender-web-pipeline` SKILL.md for glTF export optimised for Three.js/Babylon — [SKILL.md](https://github.com/freshtechbro/claudedesignskills/blob/main/.claude/skills/blender-web-pipeline/SKILL.md); threenative-asset-mcp targets three.js asset search — [GitHub](https://github.com/ThreeNativeHQ/threenative-asset-mcp)

### Inferences
- For a glTF→Godot validation step, a CLI-style Godot MCP (or plain `godot --headless` via Bash) suffices: import the GLB, run a scene, read errors. Editor-plugin MCPs are only needed for interactive scene editing.

### Gaps
- Godot headless import CLI flags (`--headless --import`) and their reliability in CI not confirmed from Godot docs in this search.

## 4. Existing Claude Code skills / Agent Skills / plugins for 3D, Blender, game assets; research agents

### Takeaway
There are now several public Claude Code skills that already implement chunks of the target pipeline (blender-kiln, majidmanzarpour/blender-game-skills, setcodes/gamedev-skills, EL4CTEO/blender-skills), plus Meshy's own agent skill. Research systems (LL3M, BlenderAlchemy, SceneCraft, MeshCoder, BlenderLLM, VIGA/BlenderGym) supply proven loop designs: multi-role agents, API-doc RAG, render-based critique, pairwise visual comparison, memory.

### Cited Findings
- majidmanzarpour/blender-game-skills: `blender-image-to-3d` skill turns concept art/turnarounds into rigged game-ready assets "measured against your references"; `export_delivery.py` exports GLB/glTF/FBX with `asset-manifest.json` and `animation-contract.json`; has evals folder — [GitHub](https://github.com/majidmanzarpour/blender-game-skills)
- elithril/blender-kiln: Claude Code plugin, text/photo → production GLB via Blender; rebuilt by script, textured from CC0 scans, graded against the real object, optimised to GLB/FBX/USDZ with gltf-transform (resize, WebP, Draco) and/or gltfpack (simplify, LOD), rigged/animated by subject; enforces 31 rules (26 core + 5 batch); runs on both ahujasid's MCP and official Blender Lab MCP — [GitHub](https://github.com/elithril/blender-kiln)
- setcodes/gamedev-skills `blender-game-assets`: Meshy/AI models or refs → game-ready low-poly in live Blender (rebuild + bake, character reduction, Mixamo prep, weight fixes, GLB export) via Blender Lab MCP — [GitHub](https://github.com/setcodes/gamedev-skills)
- EL4CTEO/blender-skills: Blender 5.2 skills incl. rigging, ARKit blendshapes, game optimisation (LODs, draw calls); `/plugin marketplace add EL4CTEO/blender-skills` — [GitHub](https://github.com/EL4CTEO/blender-skills/wiki); RobLe3/cc-blender-skill: 10 chain-loadable skills for Blender 5.x incl. blender-export — [GitHub](https://github.com/RobLe3/cc-blender-skill); lovecatisgood-sudo skill covers bpy modelling, UVs, PBR, rigging, LODs, collisions, exports, audit reports — [README](https://github.com/lovecatisgood-sudo/3d-asset-generation-blender-unity-game-development-skills/blob/main/README.md); kevinbadi/blender-skills (Meshy image-to-3D via MCP) — [GitHub](https://github.com/kevinbadi/blender-skills)
- LL3M (arXiv 2508.08228, Aug 2025): multi-agent (planner, retrieval, coding, critic, verification) writing Blender Python; shared code context; BlenderRAG from 1,729 Blender 4.4 doc files reduces execution errors and enables bmesh/geometry/shader nodes; critique with code and renders; reported better than BlenderMCP — [arXiv](https://arxiv.org/abs/2508.08228); [Emergent Mind summary](https://www.emergentmind.com/papers/2508.08228)
- BlenderAlchemy (ECCV 2024, arXiv 2404.17672): visually-guided program search; edit generator proposes 8 hypotheses/iteration ("Tweak" numeric vs "Leap" structural), visual state evaluator uses pairwise image comparison; best render's program becomes next baseline; edit reversion; can use text-to-image for "visual imagination" targets — [arXiv PDF](https://arxiv.org/pdf/2404.17672); [code](https://github.com/ianhuang0630/BlenderAlchemyOfficial)
- BlenderGym/VIGA: closed loop write→run→render→compare→revise with memory and skill library; ablations attribute VIGA's gains to memory; BlenderAlchemy yields 12–23% PL improvements as memory-less baseline — [Emergent Mind BlenderGym](https://www.emergentmind.com/topics/blendergym)
- SceneCraft (arXiv 2403.01248): LLM agent synthesising 3D scenes as Blender code — [arXiv](https://arxiv.org/pdf/2403.01248)
- BlenderLLM (arXiv 2412.14203): Qwen2.5-Coder-7B fine-tuned on BlendNet with self-improvement for CAD-style bpy — [HF README](https://huggingface.co/FreedomIntelligence/BlenderLLM/blob/main/README.md)
- MeshCoder (arXiv 2508.14879): point cloud → part-decomposed editable Blender Python using a custom expressive API; resolution editable via code parameters; dataset size inconsistently reported (1M vs 100K pairs) — [arXiv](https://arxiv.org/abs/2508.14879); [HF dataset](https://huggingface.co/datasets/InternRobotics/MeshCoderDataset)
- Newer: EZBlender (Plan-and-ReAct, arXiv 2601.07143), 3DCodeBench (arXiv 2606.01057), ViSculpt (arXiv 2608.24169) — [EZBlender](https://arxiv.org/pdf/2601.07143), [3DCodeBench](https://arxiv.org/pdf/2606.01057), [ViSculpt](https://arxiv.org/pdf/2608.24169)
- Auto-rigging: UniRig (VAST, SIGGRAPH 2025); UniRigMCP runs it as an MCP step but needs NVIDIA (RTX 50-series install script); rigs only, no animation — [UniRigMCP](https://github.com/digitalblack210/UniRigMCP); raydeStar/reference-asset-compiler: concept image → rigged UE5 character via Hunyuan3D + Blender rigging (with/without Auto-Rig Pro) — [auto-rigging topic](https://github.com/topics/auto-rigging?o=desc&s=updated)

### Inferences
- blender-kiln and majidmanzarpour's skill are the closest prior art; their manifest/contract JSON and rule lists are worth copying rather than reinventing.
- UniRig is not a viable local option on Apple Silicon per available MCPs (NVIDIA-only); on Mac, rigging = Meshy rig (humanoids), Rigify/template rigs via bpy, or Mixamo (manual web step).

### Gaps
- 3D-GPT not searched. No Anthropic-official 3D/Blender skill found in the anthropics/skills repo (not verified directly). Quality/maintenance of community skills not assessed.

## 5. Agent design patterns proven in these systems

### Takeaway
Proven patterns: (a) retrieve real API docs before writing bpy; (b) render → VLM critique, preferably pairwise comparison vs reference, with memory of attempts; (c) deterministic bundled scripts for repeatable steps, free-form code only for one-offs; (d) cost confirmation + idempotent task ledger for paid APIs; (e) manifest/contract sidecars and rule-based validators at export.

### Cited Findings
- API-doc RAG (BlenderRAG) reduces execution errors — [LL3M](https://arxiv.org/abs/2508.08228); version-matched API lookup is the fix for hallucinated bpy (search_api_docs, introspection, live bpy_api_lookup) — [StraySpark (vendor)](https://www.strayspark.studio/blog/blender-mcp-not-working-fix-connection-2026)
- Pairwise "which render is closer to goal" is more reliable for VLMs than absolute scoring; multiple hypotheses per iteration with reversion — [BlenderAlchemy](https://arxiv.org/pdf/2404.17672); memory across iterations drives gains — [BlenderGym](https://www.emergentmind.com/topics/blendergym)
- Measuring outputs against references/"graded against the real object" — [blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills), [blender-kiln](https://github.com/elithril/blender-kiln)
- Asset manifest + animation contract JSON at delivery — [blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills); explicit rule set (31 rules) enforced — [blender-kiln](https://github.com/elithril/blender-kiln)
- Cost confirmation before credit calls; never re-create on timeout/5xx — check task list first; fix output formats at creation — local observation (Meshy MCP server instructions)
- Agent Skills guidance: SKILL.md loads only when relevant; body <500 lines; references one level deep; scripts executed via bash so only output enters context; metadata ~50–100 tokens/skill; "scripts solve problems rather than defer to Claude" — [Anthropic skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices); keep gotchas in SKILL.md not references; scripts for deterministic tasks with LLM-friendly stdout — [Gemini CLI skills best practices](https://geminicli.com/docs/cli/skills-best-practices/); Agent Skills open standard (Dec 2025) stewarded at agentskills.io — [Webfuse cheat sheet](https://www.webfuse.com/agent-skills-cheat-sheet)
- Run long jobs in background threads/subprocesses to avoid freezing Blender (UniRig 3-step skeleton→skin→merge in background thread) — [rotembab](https://github.com/rotembab/claude-blender-integration)
- MCP schema cost: Meshy MCP's 28 tools ≈ 19K tokens of schemas — [Hermes plugin](https://github.com/NousResearch/hermes-official-plugins/tree/main/meshy)

### Inferences
- Skill architecture suggestion: SKILL.md = stage graph + gotchas + cost rules; `scripts/` = deterministic bpy stage scripts (`retopo.py`, `fit_gear.py`, `bake.py`, `export_gltf.py`, `validate.py`) run headless with JSON stdout; `references/` = per-stage notes; per-asset `asset.json` sidecar recording source (generator task_id, licence), credits spent, stage status, hashes for caching; a project-level credit ledger; render turntable after each stage for pairwise VLM check vs concept art.
- Use free-form `execute_blender_code` only for inspection and one-off fixes; deterministic scripts for anything repeated across assets.

### Gaps
- No published quantitative comparison of deterministic-script vs free-form agents for game asset pipelines found.

## 6. Asset-library sources accessible via MCP/API with licences

### Takeaway
Poly Haven (CC0, free API with credit + User-Agent requirement) and ambientCG (CC0, keyless API) are API-friendly; Kenney and Quaternius are CC0 but have no official API (scraping/zip packs; some Quaternius under "CC0 / QAL"); Sketchfab licences vary per model and its API terms limit use to reasonable non-commercial use unless licensed.

### Cited Findings
- Poly Haven API (api.polyhaven.com): free for any purpose; assets CC0; building on the live API requires visible "Powered by Poly Haven" credit and a unique User-Agent — [Poly Haven Public-API README](https://github.com/Poly-Haven/Public-API/blob/master/README.md)
- ambientCG: anonymous read-only v3 API, CC0, searchable metadata/categories/variants — [threenative-asset-mcp](https://github.com/ThreeNativeHQ/threenative-asset-mcp); no key required — [Cinevva assets guide](https://app.cinevva.com/guides/game-assets-guide)
- Kenney, Quaternius, KayKit, Poly Haven, ambientCG publish under CC0 — [Cinevva assets guide](https://app.cinevva.com/guides/game-assets-guide); Kenney/Quaternius have no official API; Quaternius via Google Drive/itch.io and licence listed "CC0 / QAL" — [arielshad/3d-asset-server](https://github.com/arielshad/3d-asset-server)
- MCPs: threenative-asset-mcp (Fab, Poly Haven, ambientCG, Smithsonian 3D, Sketchfab, Kenney audio; Quaternius via itch.io auto-picks non-root-motion GLB; `npx -y threenative-asset-mcp`) — [GitHub](https://github.com/ThreeNativeHQ/threenative-asset-mcp); 3d-asset-server (REST + MCP; Poly Haven, ambientCG, BlenderKit, Kenney, Quaternius; returns `{"name":"CC0","commercialUse":true,"attributionRequired":false}`) — [GitHub](https://github.com/arielshad/3d-asset-server)
- Sketchfab: per-model licences (CC0, CC-BY needs attribution, some non-commercial); download needs user API token; public API terms limit to reasonable non-commercial use unless separately licensed; keep "<creator> via Sketchfab" attribution — [assetforge AGENT_GUIDE](https://docs.rs/crate/assetforge/latest/source/AGENT_GUIDE.md); Epic sold Sketchfab and ArtStation to KitBash on 10 Aug 2026, APIs still working as of Sept 2026 — [Cinevva Sketchfab vs Poly Haven vs Kenney](https://app.cinevva.com/guides/sketchfab-polyhaven-kenney)

### Inferences
- Record licence + attribution string per asset in the sidecar; reject Sketchfab NC/ND assets automatically for a commercial game; prefer CC0 sources first.

### Gaps
- Licence terms for Meshy/Tripo/Rodin generated outputs (commercial rights by plan tier) not researched here.

## 7. Limitations and failure modes practitioners report

### Takeaway
Main failure modes: version-mismatched/hallucinated bpy APIs, wrong mode/selection context, main-thread blocking and client timeouts, unframed TCP responses, scale/axis/unapplied-transform issues on export, Draco incompatibility, and security (arbitrary code exec, SSRF, telemetry).

### Cited Findings
- Hallucinated/version-mismatched bpy → give model the running version's API (vendor-biased) — [StraySpark](https://www.strayspark.studio/blog/blender-mcp-not-working-fix-connection-2026)
- Operators depend on mode, active object and selection; wrong mode fails or silently does nothing; bmesh edits lost if not flushed; update depsgraph before reading world matrices — local observation (Blender Lab MCP server instructions)
- Timeouts: 4-min client timeout (-32001), "Incomplete JSON response", 5 s script limit on some servers — [StraySpark](https://www.strayspark.studio/blog/blender-mcp-not-working-fix-connection-2026); unframed sendall fragmentation, polling/downloads on main thread — [DeepWiki](https://deepwiki.com/ahujasid/blender-mcp/6.2-error-handling-and-troubleshooting)
- Background-thread bpy calls hard-crash Blender — [Medium](https://medium.com/@anvilinteractivesolutions/how-i-built-a-full-mcp-server-inside-blender-and-why-it-was-harder-than-it-sounds-187535b2d576)
- Scale/axis: Blender Unit Scale only changes UI display; keep 1 BU = 1 m and apply scale; models should face -Y in Blender to face -Z in Godot; apply all transforms; unapplied transforms are #1 cause of broken skeletal animation imports; +Y Up on export — [Cinevva Blender→Godot checklist](https://app.cinevva.com/guides/blender-to-godot-export-checklist); [Godot forum](https://forum.godotengine.org/t/blender-3d-model-imports-are-always-facing-the-wrong-direction/117807); [bugnet](https://bugnet.io/blog/fix-godot-skeletal-animation-import-blender-breaks)
- Draco: "required extension 'KHR_draco_mesh_compression' is not supported" in some importers; fix: disable or decompress with gltf-transform — [Cinevva checklist](https://app.cinevva.com/guides/blender-to-godot-export-checklist)
- Godot .blend import converts to glTF internally and needs a Blender path; GLB recommended for CI/teams — [Godot 4.4 formats docs](https://docs.godotengine.org/en/4.4/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html); [codebycandle](https://codebycandle.com/blog/blender-godot-workflow)
- Local generators on Mac are slow (Hunyuan 5–10x slower than CUDA; texturing 512 s; TRELLIS.2 3.5 min) and memory hungry (18 GB peak, swap) — see Q2 sources
- AI meshes are dense (TRELLIS.2 ~400K vertices) so retopo/decimation is mandatory — [Show HN](https://news.ycombinator.com/item?id=47828896)
- UniRig Blender bridge "hasn't been run against a real UniRig install yet" — [rotembab](https://github.com/rotembab/claude-blender-integration)

### Inferences
- Validation script should check: applied transforms, scale ~ expected real-world bounds, Y-up/-Z forward after import, triangle budget, single skeleton, bone count limits, no Draco when targeting Godot (or confirm support), texture sizes power-of-two, material count.

### Gaps
- Reddit/HN practitioner threads specifically on Blender MCP failures not found in search; Khronos glTF-Validator CLI usage not confirmed in this pass.
