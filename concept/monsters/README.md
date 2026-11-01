# Monsters

> To be planned in its own session.

Monsters, creatures and world bosses.

## Design rule: built to extend

New monsters, and new peoples later in the game, must be addable without changing the game's systems.

- Every monster is **data**: a body, a set of skills (the same skill system players use), a behaviour, loot tables and where it lives.
- Behaviours are shared building blocks (wander, guard, hunt, flee, swarm) combined per monster, not one-off code.
- Habitats link to isle biomes and seasons in the [world file](../../worlds/README.md), so a new biome or monster slots in by data.

## To plan

- Monster families per biome, and the drowned world below
- World bosses: where, how often, and what they drop
- Relic sources
- How monsters react to day, night and seasons
