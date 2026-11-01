# Worlds

Shard maps in the `game0-world` JSON format (`*.world.json`). The format is defined in [`demos/world-editor/src/world.ts`](../demos/world-editor/src/world.ts).

| File | Shard |
| --- | --- |
| [`first-shard.world.json`](first-shard.world.json) | The First Shard: the four homelands around the Accord ring, with a wild rim |

## Editing

1. Run `bun run dev:demo world-editor`, or open the [published editor](https://hackdonalds.github.io/game0/demos/world-editor/).
2. In the World panel, pick a file under **Repo worlds** and click **Open**, or use **Import**.
3. Edit, then **Export** and save the file here, replacing the old one. Commit it.

Every file in this folder is bundled into the editor, so new worlds show up under **Repo worlds** after the next build.
