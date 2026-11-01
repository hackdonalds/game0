# Economy

A single-gold, player-driven economy. Local markets and sailship hauling create trade routes, and partial-loot PvP keeps goods leaving the world.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Gear source | **Crafting first.** Monsters mostly drop materials, recipes and books. Finished gear drops are rare and still need crafters to repair |
| Gear tiers | Set by material (copper, iron, skysteel, relic and so on); crafting skill sets quality within a tier |
| Housing | Town plots are **rented weekly** with gold. If rent stops, after a warning the plot is freed and its contents go to storage |
| Currency | Single gold currency |
| Markets | Local order books per town. **Each town's book is the same on every shard**: Windmarket's orders are shared by Windmarket on all shards. Goods still have to be hauled there on the shard you're on. Prices differ between towns, not between shards |
| Gear wear | Gear wears down with use, which keeps crafters in demand |
| Knowledge | Player trainers and player-written books are traded like goods |
| Gold sinks | Gear durability and repair, town plot rent and upkeep, sail wear from attacks, weather and distance |
| Cargo | Ship cargo can be looted when a ship is attacked |

## Flows

**Faucets** (gold and items entering the world)
- Monster gold drops and quest rewards
- Monster loot: materials, recipes, and some finished gear
- Gathering nodes on the isles

**Sinks** (gold and items leaving the world)
- Repairs, and gear broken beyond repair
- Weekly plot rent
- Sails wear from attacks, weather and distance travelled, and need re-enchanting by crafters
- Ship cargo looted in attacks
- Resources lost on death (partial loot): some are picked up by other players, and the rest decay
- Crafting inputs consumed

## Loops

- **Gather → craft → sell → repair.** Durability keeps demand for crafted gear steady even when bosses drop gear.
- **Haul.** Buy cheap in one town and sell high in another. Sail re-enchanting is the cost, and PvP risk on the route is the margin.
- **Risk.** Carried resources drop on death in open-world PvP, which feeds looters and keeps raw materials scarce.

## Open questions

- How are skill books priced and copied: one book per copy, written by hand?
- Should there be any market tax? Not chosen yet; the sinks above are expected to carry the load.
- The exact material tiers, and how fast gear wears through durability.
