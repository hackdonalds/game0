# Meshy API and MCP server: credit costs, cost/quality parameters, MCP-to-API mapping

Researched 2026-10-31. Primary sources: the Meshy API docs (docs.meshy.ai, .md versions and llms.txt / llms-full.txt), the published npm tarball of `@meshy-ai/meshy-mcp-server@0.6.7` (latest; 0.6.5 published 2026-10-22, 0.6.6 on 2026-10-26, 0.6.7 on 2026-10-30, per `npm view`), and the repo CHANGELOG on GitHub.

## Full API credit price list per endpoint and option

### Takeaway
All API prices are fixed credits per request and are listed on one page. The main cost drivers are the AI model (20 for meshy-7.1/meshy-6 vs 5 for meshy-6-lite/meshy-t2/meshy-t2.5), whether texturing happens (+10, or +15 at 8K), and Ultra geometry (+5). Post-processing is cheap: remesh 5, UV unwrap 5, convert 1, resize 1. Rigging costs 5 and includes free walk and run clips. Animation costs 3 per action.

### Cited Findings
**3D generation** (credits per request, including the selected texture option) — [API Pricing](https://docs.meshy.ai/api/pricing.md)

| API | Configuration | meshy-7.1 (`latest`) | meshy-6 | meshy-6-lite | meshy-t2 | meshy-t2.5 |
|---|---|---|---|---|---|---|
| Text to 3D (Preview) | Mesh only | 20 | 20 | 5 | 5 | 5 |
| Image to 3D | Mesh only | 20 | 20 | 5 | 5 | 5 |
| | + 2K textures | 30 | 30 | 15 | 15 | 15 |
| | + 4K textures | 30 | 30 | not supported | 15 | 15 |
| | + 8K textures | 35 | 35 | not supported | 20 | 20 |
| Multi-Image to 3D | Mesh only | 20 | 20 | 5 | not supported | not supported |
| | + 2K textures | 30 | 30 | 15 | n/s | n/s |
| | + 4K textures | 30 | 30 | n/s | n/s | n/s |
| | + 8K textures | 35 | 35 | n/s | n/s | n/s |
| Ultra geometry surcharge | `geometry_resolution: "2k"` or `"4k"` | +5 | n/s | n/s | n/s | n/s |

- Legacy `meshy-7` costs the same as `meshy-7.1`. — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- **Texturing**: Text to 3D Refine costs 10 at 2K/4K and 15 at 8K. Preview and Refine are separate requests, billed separately. Retexture also costs 10 at 2K/4K and 15 at 8K. — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- So a full Text to 3D run on meshy-7.1 costs 20 (preview) + 10 (refine) = 30, or 35 with Ultra geometry. The doc's goal table says "Textured model from text … 20 + 10" and "Highest geometry detail … 20 + 5". — [llms.txt](https://docs.meshy.ai/llms.txt)
- **Image generation** — [API Pricing](https://docs.meshy.ai/api/pricing.md):
  - Text to Image: nano-banana 3, nano-banana-2 6, nano-banana-2-lite 3, nano-banana-2-1 4, nano-banana-pro 9, GPT Image models 9.
  - Image to Image: the same, except GPT Image models cost 12.
- **Rigging and animation** — [API Pricing](https://docs.meshy.ai/api/pricing.md):
  - Rigging: 5 per request.
  - Animation: 3 per action, up to 10 actions per request.
  - Text to Motion: `prime` 10, `swift` 3.
- **Post-processing** (fixed price per request): Remesh 5, UV Unwrap 5, Convert 1, Resize 1. — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- **3D printing**: Analyze Printability is free. Multi-Color Print, Repair Printability and Auto Split cost 10 each. — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- With Auto Split `keep_texture: true`, the task "takes about twice as long, and the credit cost doesn't change". — [Auto Split](https://docs.meshy.ai/api/auto-split.md)
- **Creative Lab** (Prototype / Build stages, billed separately) — [API Pricing](https://docs.meshy.ai/api/pricing.md):
  - Keychain, Fridge Magnet, Figure, Vinyl Figure, Brick Figure and Fidget Pixel: 6 / 30.
  - Keycap: 12 / 50.
  - Lamp: 30 / 6.
  - Collapsible Fidget: a single stage at 6.
- **Image to Image multi-view**: `generate_multi_view: true` returns "one URL per view, usually three". The pricing page lists no separate multi-view price, so it is billed at the model's per-request price. — [Image to Image](https://docs.meshy.ai/api/image-to-image.md); [API Pricing](https://docs.meshy.ai/api/pricing.md)
- **Text to Motion**: `duration` runs from 2 to 10 s in 0.5 s steps. `prime` returns FBX and `swift` returns BVH. — [Text to Motion](https://docs.meshy.ai/api/text-to-motion.md)
- **Rigging** returns "basic walking and running animations" (walking/running GLB and FBX URLs) with the rig. Input must be at most 380,000 triangles. — [Rigging](https://docs.meshy.ai/api/rigging.md)
- **Animation**: `action_ids` takes 1–10 preset IDs and returns one file with one clip per action. "Meshy charges for each action in the list." Listing the animation library "costs no credits". — [Animation](https://docs.meshy.ai/api/animation.md)
- **UV Unwrap** costs 5 credits, takes meshes of at most 40,000 faces, and outputs a "UV white model" with no real texture. — [UV Unwrap](https://docs.meshy.ai/api/uv-unwrap.md)

**Parameters that control cost and quality**
- `geometry_resolution`: `standard` (default), `2k` (Ultra pass at 2048³) or `4k` (Ultra pass at 4096³). It applies to preview only (on refine it returns 400). `2k` needs meshy-7.1/latest/meshy-7, and `4k` needs meshy-7.1/latest. `ultra_mode: true` is deprecated and equals `"2k"`. — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)
- Multi-Image to 3D rejects `geometry_resolution: "4k"`. — [Multi-Image to 3D](https://docs.meshy.ai/api/multi-image-to-3d.md)
- `texture_resolution`: `2k` (default), `4k` or `8k`. 4K and 8K need meshy-6, meshy-7.1 or latest. At 8K there is no emission map. `hd_texture` is deprecated and equals `4k`. — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md); [Image to 3D](https://docs.meshy.ai/api/image-to-3d.md)
- `enable_pbr` (default false) adds metallic, roughness and normal maps at no listed extra cost. An emission map comes only with meshy-6, and not at 8K. — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md); [API Pricing](https://docs.meshy.ai/api/pricing.md)
- Image to 3D `should_texture` defaults to **true**. The default call is therefore 30 credits on meshy-7.1, not 20. — [Image to 3D](https://docs.meshy.ai/api/image-to-3d.md); [llms.txt](https://docs.meshy.ai/llms.txt)
- `should_remesh` defaults to true on meshy-6-lite and false on other models. "For the highest-quality 3D model, send `false`." — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)
- `target_polycount` ranges [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md):
  - Remesh: 100–300,000, default 30,000.
  - meshy-t2: 100–15,000, default 4,000.
  - meshy-t2.5: 100–30,000, default 15,000.
  - `decimation_mode` (1 ultra to 4 low) overrides `target_polycount`.
- Smart Topology output is triangle-only, and `topology: quad` with meshy-t2/t2.5 returns 400. — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)
- Other Image to 3D parameters: `image_enhancement` (default true), `remove_lighting` (default true), `pose_mode`, `save_pre_remeshed_model`, `target_formats`, `auto_size`, `origin_at`, `multi_view_thumbnails`. — [Image to 3D](https://docs.meshy.ai/api/image-to-3d.md)
- Multi-Image to 3D `texture_image_urls`: 1–4 views drive the texture. It needs meshy-7.1/latest/meshy-7 and cannot be combined with `texture_prompt` or `texture_image_url`. — [Multi-Image to 3D](https://docs.meshy.ai/api/multi-image-to-3d.md)
- Retexture parameters: `text_style_prompt` / `image_style_url` / `multiview_image_urls`, `ai_model` (newest is meshy-7; meshy-7.1 is rejected), `enable_original_uv`, `enable_pbr`, `texture_resolution`, `remove_lighting`. — [Retexture](https://docs.meshy.ai/api/retexture.md); [llms.txt](https://docs.meshy.ai/llms.txt)

**Typical processing times** [Task Lifecycle](https://docs.meshy.ai/api/task-lifecycle.md)
- Text to 3D preview (mesh only): meshy-7.1 75 s, meshy-6 90 s, meshy-6-lite 45 s, meshy-t2 10 s.
- Image to 3D with 2K textures: meshy-7.1 2 min, meshy-6 3 min, meshy-6-lite 75 s, meshy-t2 60 s.
- Refine: 80 s at 2K/4K, 3.5 min at 8K.
- Rigging 40 s, Animation 15 s, Remesh 2 min, UV Unwrap 35 s, Convert 7 s.

### Inferences
- The cheapest textured asset is Image to 3D with meshy-6-lite or meshy-t2/t2.5 at 2K: 15 credits.
- The most expensive single generation is Image to 3D on meshy-7.1 with 8K textures and Ultra geometry: 35 + 5 = 40 credits.
- A typical game-character pipeline on meshy-7.1 costs about 46 credits: Image to 3D textured (30), plus rigging (5), plus 3 extra animations (9), plus 2 converts (2). Walk and run come free with the rig.
- PBR costs nothing extra in the API, so enabling it seems advisable whenever maps are useful.

### Gaps
- The docs give no separate price for Text to Image or Image to Image with `generate_multi_view: true`. The pricing table only varies by model.
- With `pose_mode` set, `nano-banana` requests are generated with `nano-banana-pro` and read back as nano-banana-pro ([Text to Image](https://docs.meshy.ai/api/text-to-image.md)). The docs do not say whether that task is billed at 3 or at 9 credits.
- I did not open the Convert, Resize, Multi-Color, Repair or Creative Lab endpoint pages individually. Their prices come from the Pricing page.

## Which tools does @meshy-ai/meshy-mcp-server expose, and what does each cost?

### Takeaway
The official MCP server (0.6.x, MIT, `github.com/meshy-dev/meshy-mcp-server`) has 28 tools, each a thin wrapper over one REST endpoint. Meshy states it costs exactly the same as the REST API and has no free tier or surcharge of its own. It needs a paid-plan API key. It downloads results locally to `./meshy_output/` by default.

### Cited Findings
- "MCP tool calls make the same REST calls and use credits at the same rate." MCP calls also count toward the same rate limits. — [AI Integration](https://docs.meshy.ai/api/ai.md)
- The README lists 28 tools and says a Meshy API key "requires Pro plan or above". — [npm package README, 0.6.7](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server)
- Tool-to-endpoint map and credits. Sources: the package source `dist/utils/endpoints.js`, the tool descriptions in `dist/tools/*.js`, and `dist/constants.js` ([package source](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/)); prices are confirmed against [API Pricing](https://docs.meshy.ai/api/pricing.md).

| MCP tool | REST call | Credits |
|---|---|---|
| `meshy_text_to_3d` | POST /openapi/v2/text-to-3d (mode preview) | 20 (meshy-7.1/latest/6); 5 (6-lite, t2, t2.5); +5 Ultra geometry |
| `meshy_text_to_3d_refine` | POST /openapi/v2/text-to-3d (mode refine) | 10 (15 at 8K) |
| `meshy_image_to_3d` | POST /openapi/v1/image-to-3d | 20/30/35 (7.1, 6); 5/15 (6-lite); 5/15/20 (t2, t2.5); +5 Ultra |
| `meshy_multi_image_to_3d` | POST /openapi/v1/multi-image-to-3d | 20/30/35; 6-lite 5/15; +5 Ultra (2k only) |
| `meshy_remesh` | POST /openapi/v1/remesh | 5 |
| `meshy_retexture` | POST /openapi/v1/retexture | 10 (15 at 8K) |
| `meshy_rig` | POST /openapi/v1/rigging | 5 (walk + run included free) |
| `meshy_animate` | POST /openapi/v1/animations | 3 per action (action_id, action_ids up to 10, or motion_task_id) |
| `meshy_text_to_motion` | POST /openapi/v1/text-to-motion | 10 prime / 3 swift |
| `meshy_list_animations` | GET animation library | free |
| `meshy_convert` | POST /openapi/v1/convert | 1 |
| `meshy_resize` | POST /openapi/v1/resize | 1 |
| `meshy_uv_unwrap` | POST /openapi/v1/uv-unwrap | 5 (at most 40k faces) |
| `meshy_text_to_image` | POST /openapi/v1/text-to-image | 3/6/3/4/9/9 by model |
| `meshy_image_to_image` | POST /openapi/v1/image-to-image | 3/6/3/4/9/12 by model |
| `meshy_creative_lab` | prototype + build POSTs under /openapi/creative-lab/<product>/v1/... | 36 (6+30); lamp 36 (30+6); keycap 62 (12+50); fidget-collapsible 6 |
| `meshy_analyze_printability` | POST /openapi/v1/print/analyze | free |
| `meshy_repair_printability` | POST /openapi/v1/print/repair | 10 |
| `meshy_process_multicolor` | POST /openapi/v1/print/multi-color | 10 |
| `meshy_auto_split` | POST /openapi/v1/print/split | 10 |
| `meshy_send_to_slicer` | none (local slicer detection only) | free |
| `meshy_get_task_status`, `meshy_list_tasks`, `meshy_list_models` | GET task routes | free |
| `meshy_cancel_task` | DELETE task | free (refunds a PENDING task) |
| `meshy_download_model` | GET signed asset URLs | free |
| `meshy_check_balance` | GET /openapi/v1/balance | free |
| `meshy_list_usage` | usage endpoint (Studio/Enterprise only) | free |

- The server's built-in instructions tell the agent: "Before calling ANY tool that costs credits, ask which ai_model to use … present the cost and wait for user confirmation." They also list "analyze printability, balance, usage, animation library, status, list, download" as free. — [package source, dist/instructions.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/instructions.js)
- `meshy_creative_lab` runs the whole prototype-then-build pipeline in one call and reports the summed `consumed_credits`. If the prototype fails, the build is not started. — [package source, dist/tools/creative-lab.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/creative-lab.js)
- The MCP `meshy_text_to_3d` description steers agents toward an image route instead: text_to_image (3–9 credits), then image_to_3d. — [dist/tools/generation.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/generation.js)
- **Local downloads**: `meshy_download_model` saves output under `meshy_output/` in the server's working directory, with project folders, metadata and history, or at a `save_to` path. It asks the agent to pick ONE format, never all. Rigging and animation tasks are not saved, and their URLs are returned instead. — [dist/tools/tasks.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/tasks.js); [AI Integration FAQ](https://docs.meshy.ai/api/ai.md)
- The key stays in memory and is never written to disk. — [AI Integration FAQ](https://docs.meshy.ai/api/ai.md)
- **Safe retries since 0.6.3**: "a create request is never resent after a timeout or server error, so a task is never created and billed twice". — [README](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server)
- **0.6.x changes relevant to cost** [CHANGELOG](https://github.com/meshy-dev/meshy-mcp-server/blob/main/CHANGELOG.md):
  - 0.6.0 added meshy-7.1, `geometry_resolution`, meshy-6-lite and smart-topology on text-to-3d.
  - 0.6.3 added text-to-motion, auto_split, list_usage and fidget products.
  - 0.6.4 added meshy-t2.5.
  - 0.6.5 added the `MESHY_CLIENT` User-Agent tag and a 400 MB `model_url` limit.
  - 0.6.6 marked rig `texture_image_url` as deprecated.
  - 0.6.7 refuses meshy-t1 and `lowpoly` locally "before any request or charge".
- Config env vars: `MESHY_API_KEY` (required), `MESHY_API_HOST`, `TRANSPORT` (stdio or http), `PORT`, `CHARACTER_LIMIT` (25000), `MESHY_CLIENT`. — [README](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server)

### Inferences
- The MCP adds no credit overhead. Status polling, listing and downloading are free API reads, though every read counts toward the 20 requests/second limit.
- Default MCP behaviors that differ from the raw API, and could affect cost or outcome:
  - `meshy_image_to_3d` hard-codes `moderation: false` ([generation.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/generation.js)).
  - With `model_type: "smart-topology"` and no `ai_model`, the MCP uses meshy-t2 ([CHANGELOG 0.6.4](https://github.com/meshy-dev/meshy-mcp-server/blob/main/CHANGELOG.md)). The API docs say meshy-t2.5 is the default ([Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)). The price is the same, but output detail and polycount range differ.
  - The `meshy_auto_split` description says "The texture is not kept", and I found no `keep_texture` in the MCP printing schema. The API's `keep_texture: true` option may therefore not be exposed in 0.6.7 (verified only by grep of dist/schemas/printing.js).

### Gaps
- I read the 0.6.7 tarball, not 0.6.5 itself. Per the CHANGELOG, 0.6.5 through 0.6.7 changed no prices, only the User-Agent tag, rig `texture_image_url` deprecation and T1 removal.

## Shared credit pool, failed-task refunds, rate limits and concurrency

### Takeaway
API, web app and Playground spend from the same account credit balance (monthly plus permanent credits; a team pool for teams). FAILED tasks are refunded automatically, and so are PENDING tasks that you delete. IN_PROGRESS tasks cannot be cancelled and are charged. Every plan gets 20 requests/second except Enterprise (100). Concurrency is 10 on Pro, 30 on Premium, 100 on Ultra, 60 on Studio and 100+ on Enterprise.

### Cited Findings
- Balance returns `balance`, `monthly_credits` (expire at the monthly refresh), `permanent_credits` (credit packs and rewards, never expire) and `monthly_resets_at`. "On a team with a shared credit pool, the values are those of the pool. Calling this endpoint is free." — [Balance](https://docs.meshy.ai/api/balance.md)
- Playground requests run on your own account and use "your plan credits", counting toward your rate limits like any other API call. — [Developer Platform](https://docs.meshy.ai/api/developer-platform.md)
- "Each plan includes monthly credits that you spend across all generation tools." Monthly credits reset at 00:00 UTC on the 1st, and purchased credits don't expire. — [Web app Pricing and credits](https://docs.meshy.ai/webapp/pricing)
- The API pricing page tells developers to "buy API credits in your subscription settings". — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- **Web app and API prices differ for the same action.** In the web app [Web app Pricing](https://docs.meshy.ai/webapp/pricing):
  - Text to 3D: 20 (Meshy 6) or 10 (6 Lite). In the API, a 6-lite preview costs 5.
  - Image to 3D: 25 with Ultra 2K/4K, which is the default on paid plans.
  - Smart Topology with T2: 5.
  - Remesh: **0**. Rigging: **0**. Animate: **0** per clip (beyond the free set this needs a paid plan).
  - In the API, the same remesh, rigging and animation calls cost 5, 5 and 3 per action. — [API Pricing](https://docs.meshy.ai/api/pricing.md)
- **Refunds**:
  - "Only `FAILED` means the task failed; its credits are refunded. Credits are charged when a task is created." — [llms.txt](https://docs.meshy.ai/llms.txt)
  - `consumed_credits` is 0 for a FAILED task. — [Image to 3D](https://docs.meshy.ai/api/image-to-3d.md)
  - Deleting a PENDING task refunds it. DELETE on an IN_PROGRESS task returns `409`, the task keeps running, and its credits "are not refundable". — [Errors](https://docs.meshy.ai/api/errors.md)
  - Timeouts and queue timeouts are failed and refunded by Meshy. — [Errors](https://docs.meshy.ai/api/errors.md)
  - An Auto Split `textured_split_refused` failure is refunded. — [Errors](https://docs.meshy.ai/api/errors.md)
  - A request refused by the IP allowlist uses no credits. — [Authentication](https://docs.meshy.ai/api/authentication.md)
- **Rate limits** [Rate Limits](https://docs.meshy.ai/api/rate-limits.md):

| Plan | Requests/s | Concurrent tasks | Priority |
|---|---|---|---|
| Pro | 20 | 10 | Default |
| Premium | 20 | 30 | Higher than Pro |
| Ultra | 20 | 100 | Highest |
| Studio | 20 | 60 (20 on some earlier Studio plans) | Higher than Pro |
| Enterprise | 100 | 100 default or custom | Highest |

- How the limits work [Rate Limits](https://docs.meshy.ai/api/rate-limits.md):
  - Concurrent tasks are those PENDING or IN_PROGRESS.
  - Get, list and stream requests count toward requests/second but not toward concurrency.
  - A team's API keys share one set of limits.
  - Too many requests/second returns 429 "Rate limit exceeded" with a Retry-After header.
  - Too many concurrent tasks returns 429 "NoMorePendingTasks" with no Retry-After header.
- **Other spending controls and limits**:
  - Each API key can have a monthly credit limit and an IP allowlist. — [Authentication](https://docs.meshy.ai/api/authentication.md)
  - Generated assets are kept for at most 3 days, except for Enterprise customers. — [Asset Retention](https://docs.meshy.ai/api/asset-retention.md)
  - The create endpoints have no idempotency key, so a resent create call is charged again. — [llms.txt](https://docs.meshy.ai/llms.txt)

### Inferences
- There is one credit balance per account or team, spent by both the web app and the API. Some actions (remesh, rig, preset animate) are free in the web app but charged in the API, so doing them in the web UI saves credits when automation isn't needed.

### Gaps
- I found no doc that literally says "API credits and web credits are the same pool". The conclusion rests on the Balance API's single balance, the Playground "uses your plan credits" line, and "spend across all generation tools". The pricing page's "buy API credits" wording leaves a small ambiguity about whether separately purchased API credit packs exist.
- Plan prices in dollars and monthly credit amounts per plan are not covered here; the docs refer to meshy.ai/pricing.

## Is there an API test mode or free sandbox key?

### Takeaway
No longer. The shared test-mode key, which returned the same sample result for free, was retired on 2026-09-16 and now returns 401. The only free trial path is the Playground on the Free plan, which offers Image to 3D only, through a built-in key, and spends real account credits.

### Cited Findings
- The changelog originally said a test-mode key let developers test "without consuming credits. All valid requests using this key will return the same sample task results." — [Changelog (llms-full.txt)](https://docs.meshy.ai/llms-full.txt)
- "The shared **test-mode API key** has been retired; requests that still send it now return `401 Unauthorized`." It is replaced by your own key or the Playground. — [Changelog (llms-full.txt)](https://docs.meshy.ai/llms-full.txt); [Deprecations](https://docs.meshy.ai/api/deprecations.md) (announced and retired 2026-09-16)
- On the Free plan, the Playground runs only Image to 3D, through a built-in key, and "uses your account's credits like any other task". — [Changelog (llms-full.txt)](https://docs.meshy.ai/llms-full.txt); [Developer Platform](https://docs.meshy.ai/api/developer-platform.md)
- A paid plan is needed to create API keys. On the Free plan, most task-creating requests return `402`. — [Quickstart](https://docs.meshy.ai/api/quick-start.md); [Errors](https://docs.meshy.ai/api/errors.md)
- The MCP repo's `npm test` runs "offline mocked-request tests (no API key or credits required)". These are developer tests, not a sandbox. — [README](https://www.npmjs.com/package/@meshy-ai/meshy-mcp-server)

### Inferences
- To test integration code without spending, mock the API locally. Otherwise the cheapest real calls are 1 credit (convert or resize on an existing task) and 3 (nano-banana image or swift motion). The cheapest 3D generation is 5 (meshy-6-lite or meshy-t2 preview).

### Gaps
- None found.

## Which API features are free?

### Takeaway
These cost nothing: Balance, Usage, Analyze Printability, the animation library listing, and all task get/list/stream/delete calls. Rigging's walk and run clips are also free.

### Cited Findings
- Balance: "Calling this endpoint is free." — [Balance](https://docs.meshy.ai/api/balance.md)
- "Check cost before spending | GET /openapi/v1/balance … consumed_credits on every task | 0". — [llms.txt](https://docs.meshy.ai/llms.txt)
- Analyze Printability is "Free, no credits". — [llms.txt index](https://docs.meshy.ai/llms.txt); [API Pricing](https://docs.meshy.ai/api/pricing.md)
- Listing animations "costs no credits". — [Animation](https://docs.meshy.ai/api/animation.md)
- MCP `meshy_list_usage` is described as "Free" (Studio/Enterprise only; other plans get 403). `meshy_check_balance` is described as "Free". — [dist/tools/balance.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/balance.js)
- Rigging includes walking and running animations. The MCP describes them as "free walking + running animations (GLB + FBX, separate files)". — [Rigging](https://docs.meshy.ai/api/rigging.md); [dist/tools/postprocessing.js](https://unpkg.com/@meshy-ai/meshy-mcp-server@0.6.7/dist/tools/postprocessing.js)

### Inferences
- Free reads still count against the requests/second limit.

### Gaps
- None significant.

## Model lineup: meshy-7.1, meshy-6, meshy-6-lite, meshy-t2, meshy-t2.5

### Takeaway
- **meshy-7.1** (= `latest`) is the flagship standard model: 20 credits for mesh, 30 textured, 35 at 8K, and the only model with Ultra geometry (+5).
- **meshy-6** is the previous generation at the same price. It is the only model that produces emission maps and honors `remove_lighting`.
- **meshy-6-lite** is the budget model: 5 for mesh, 15 textured, 2K textures only, remesh on by default.
- **meshy-t2** and **meshy-t2.5** are Smart Topology models that generate clean triangle meshes directly at a chosen face count, for 5 credits for mesh. They are not available on Multi-Image.

### Cited Findings
- Model lifecycle status [Deprecations](https://docs.meshy.ai/api/deprecations.md):
  - Active: meshy-7.1, meshy-6, meshy-6-lite, meshy-t2.5, meshy-t2.
  - Deprecated: meshy-7 (2026-09-18, retirement date not yet announced).
  - Retired: meshy-5 (2026-10-10, replaced by meshy-6-lite) and meshy-t1 / `lowpoly` (2026-10-30, replaced by smart-topology with meshy-t2.5).
  - "`latest` resolves to `meshy-7.1`."
- On Text/Image/Multi-Image to 3D the newest model is meshy-7.1. On Retexture it is meshy-7, and Retexture rejects meshy-7.1. "Use `meshy-6-lite` for the cheapest mesh (5 credits, `2k` texture only)." — [llms.txt](https://docs.meshy.ai/llms.txt)
- meshy-t2 gives "cleaner topology, natively separated parts, triangle output". meshy-t2.5 (the API default for smart-topology) gives "sharper detail for game assets". Ranges: t2 100–15,000 faces (default 4,000), t2.5 100–30,000 (default 15,000). — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)
- meshy-6-lite is the successor to meshy-5, with "same parameters, same credit cost (5 for the mesh, 15 with texture, 10 for a retexture)". — [Changelog (llms-full.txt)](https://docs.meshy.ai/llms-full.txt)
- Only meshy-6 generates an emission map with `enable_pbr`. `remove_lighting` takes effect only on meshy-6 and returns 400 with meshy-6-lite. 4K/8K textures need meshy-6 or meshy-7.1. — [Text to 3D](https://docs.meshy.ai/api/text-to-3d.md)
- Speed (Image to 3D, 2K textures): meshy-7.1 2 min, meshy-6 3 min, meshy-6-lite 75 s, meshy-t2 60 s. — [Task Lifecycle](https://docs.meshy.ai/api/task-lifecycle.md)
- Smart Topology Image to 3D prices: 5 for mesh, 15 at 2K/4K, 20 at 8K. A Text to 3D refine of a t2/t2.5 preview is 10 (15 at 8K). — [API Pricing](https://docs.meshy.ai/api/pricing.md)

### Inferences
- For game-ready low-poly assets, meshy-t2.5 with Image to 3D at 2K textures (15 credits) is the cost-efficient choice. meshy-7.1 at 30 credits gives maximum detail but needs remeshing (+5) for game budgets.
- Pinning `ai_model` explicitly avoids silent output changes when `latest` moves ([Deprecations](https://docs.meshy.ai/api/deprecations.md) recommends this).

### Gaps
- The docs give no qualitative benchmark comparing meshy-7.1 and meshy-6 output quality beyond "newest" vs "previous generation".
