# Concept

The game concept: what the game is, before how it's built. This folder is the single source of every world and game fact, and the [handbook site](https://hackdonalds.github.io/game0/) is built from it, so editing a file here updates the site. Write each fact once: rules and systems in the docs, each single thing (a people, a creature, a skill) in its entry, and link instead of repeating.

- **Docs** (the list below) render as the handbook's chapters. A chapter's title, kicker, summary, cover brief, catalogues and extra docs are in the `chapter:` frontmatter of its first doc.
- **Entries** in [`entries/<kind>/<id>.md`](entries/) are the catalogues: [peoples](entries/peoples/), [bestiary](entries/bestiary/), [skills](entries/skills/), [materials](entries/materials/), [ships](entries/ships/), [isles](entries/isles/), [winds](entries/winds/) and [architecture](entries/architecture/). The YAML frontmatter holds the structured stats and an `art:` brief for the entry's painted plate; the body holds the prose. Isle and wind files are named by their id in [`worlds/first-shard.world.json`](../worlds/first-shard.world.json), which holds their names and geometry.
- **[Glossary](glossary.md):** short definitions, or links to the doc section or entry that already defines a term.

The site reads entries with `apps/web/src/lib/concept.ts`, which fails the build on a missing or misspelt field, and `bun run handbook:check` fails when an entry is not shown on the site.


- [Vision](vision.md): pitch, pillars, target players
- [World](world/README.md): setting, regions, lore, factions
- [Mechanics](mechanics/README.md): core loop, combat, progression, social systems
- [Sailing](sailing/README.md): ships, wind currents, sail wear
- [Economy](economy/README.md): currencies, resources, crafting, trade, sinks and faucets
- [Monsters](monsters/README.md): creatures, taming and world bosses
- [Social](social/README.md): guilds, reputation and relations (to plan)
- [Simulation](simulation/README.md): NPCs and bots at three levels of detail
- [Art direction](art-direction/README.md): style, palette, shape language, references
