# Art

Every image lives in exactly one place, by what it is for. Each generated image has a `.json` sidecar with its prompt, model and references. Binaries are in Git LFS.

| Folder | What it holds | Test |
| --- | --- | --- |
| `references/` | Style anchors: the images every prompt attaches to lock the look (`world-tree-floating-isle.webp`, the three `style-test-*` images) | Would you attach it to a new prompt as "the locked style"? |
| `concept/<kind>/` | Paintings, the source of truth for style: scenes, environment paintings, isle portraits, effect sheets, architecture concept sheets, and the painted entry plates of the handbook | Is it a picture of the world? |
| `kit/<kind>/` | Kit reference sheets for 3D modelling: isolated pieces on a plain background, orthographic or turnaround views, scale figure, labels, swatches | Would a modeller build pieces from it? |
| `models/` | 3D models (`.glb`) with sidecars and their thumbnails; `models/*/<x>/sheet-*.png` are renders of built kits | |
| `textures/` | Textures, trim sheets and painted leaf cards | |
| `anims/` | Animation clips | |
| `retired/` | Everything retired, in one place: `retired/peoples/<people>/` (concept art and plates of peoples dropped from the cast), `retired/models/` (old models and props) | Kept for history; nothing live points here |
| `handbook/` | **Generated, not committed.** Web plates for the site, made by `bun run art:sheets` | Never edit or commit |

`<kind>` is a catalogue: `architecture`, `biomes`, `bestiary`, `chapters`, `isles`, `materials`, `peoples`, `ships`, `skills`, `winds`, `world`.

## Naming

- **Painted entry plates:** `concept/<kind>/<id>.webp`, where `<id>` is the entry's id in `apps/web/src/data/` (chapter slug for `chapters`). `bun run art:handbook` paints the missing ones. They are the only `.webp` files directly in a `concept/<kind>/` folder.
- **Concept and kit sheets:** `.png`, named for their subject: `concept/isles/<isle>-portrait.png`, `concept/architecture/<style>/<sheet>.png`, `kit/architecture/<style>/kit-<part>.png`, `kit/biomes/<biome>/{nature,terrain}.png`, `kit/bestiary/<id>.png`, `kit/peoples/<people>/{base-turnaround,outfits,signatures}.png`, `kit/peoples/gear/<sheet>.png`, `kit/ships/{<ship>,kit-<part>}.png`.
- **Drafts:** `bun run art:image` without `--out` saves to `concept/drafts/`. Move a keeper to its folder; the handbook ignores drafts.
- **Meshy crops:** `kit/views/<people>-base-{front,side,back}.png` are cut from the base turnaround when needed and are not committed.
- A name must be unique within its layer and kind, so a concept sheet and a kit sheet of the same kind never share a name: they would make the same plate, and `art:sheets` stops with an error.

## How the handbook uses it

`bun run art:sheets` (`scripts/handbook-sheets.ts`, also run first by `bun run build` and the web dev server) makes `handbook/` from the sources, and the site reads only `handbook/<kind>/<name>.webp`:

| Source | Plate |
| --- | --- |
| `concept/<kind>/<id>.webp` | `handbook/<kind>/<id>.webp` (copied) |
| `{concept,kit}/architecture/<style>/<sheet>.png`, `models/architecture/<style>/sheet-<s>.png` | `handbook/architecture/<style>-<sheet>.webp`, `<style>-built-<s>.webp` |
| `{concept,kit}/biomes/<biome>/<sheet>.png`, `models/nature/<biome>/sheet-<s>.png` | `handbook/biomes/<biome>-<sheet>.webp`, `<biome>-built-<s>.webp` |
| `textures/foliage/<name>.png` | `handbook/foliage/<name>.webp` |
| `{concept,kit}/<kind>/…/<sheet>.png` for ships, bestiary, peoples, materials, isles, skills, winds, world | `handbook/sheets/<kind>-…-<sheet>.webp` |

`bun run handbook:check` fails when a plate is missing, stale or orphaned, so a new sheet needs no other step than `art:sheets` (and a gallery entry in `apps/web/src/data/concept-sheets.ts` if it should appear on a page).
