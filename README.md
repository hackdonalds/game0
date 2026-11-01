# game0

A sky-island MMORPG, in the concept stage. This monorepo holds the game concept, concept art, 3D assets, the Godot game, and the marketing site with its playable Three.js demos.

**Handbook:** https://hackdonalds.github.io/game0/

## Layout

| Path | What lives there |
| --- | --- |
| `concept/` | Game concept docs: vision, world, mechanics, economy, art direction |
| `art/references/` | Mood and reference images |
| `art/concept/` | Generated and painted concept art (each image has a `.json` prompt sidecar) |
| `art/models/` | Meshy and hand-made 3D models (`.glb`) |
| `art/textures/` | Textures and HDRIs |
| `apps/web/` | The handbook site (Astro + Three.js): chapters rendered from `concept/`, catalogues from `apps/web/src/data/`, mini demos |
| `apps/game/` | Godot client (not started yet) |
| `worlds/` | Shard maps (`*.world.json`) made with the world editor demo |
| `demos/<name>/` | Standalone playable Three.js demos (Vite), published under `/demos/<name>/` |
| `scripts/` | Build and asset pipeline scripts |

Binary assets (images, models, audio) are stored with Git LFS. Run `git lfs install` once before cloning.

## Setup

```sh
bun install
bun run dev                 # marketing site at localhost:4321/game0
bun run dev:demo floating-isle
bun run build && bun run preview   # full Pages build at localhost:4321/game0
```

## Asset pipeline

Export the API keys in your shell (see `.env.example`):

```sh
export MESHY_API_KEY=msy_...
export OPENROUTER_API_KEY=sk-or-v1-...
```

MCP servers (`.mcp.json`):

- **meshy**: text/image to 3D through `@meshy-ai/meshy-mcp-server`. Save outputs to `art/models/`.
- **openrouter**: OpenRouter's hosted MCP (OAuth). Authenticate once with `claude mcp login openrouter` or via `/mcp`.

The OpenRouter MCP returns images inline. To save concept art into the repo, use the script, which defaults to `openai/gpt-image-2.5-sunburst`:

```sh
bun run art:image "sky-island market town at dawn, painterly" --ref art/references/world-tree-floating-isle.webp --out art/concept/market-town
```

## Adding a demo

Copy `demos/floating-isle`, rename the package, and edit `demo.json`. The Vite `base` comes from the folder name, the build script picks the demo up automatically, and the site lists it on the home page.

## Deploy

Every push to `main` builds with `.github/workflows/pages.yml` and deploys to GitHub Pages.
