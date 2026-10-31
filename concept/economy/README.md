# Economy

A single-gold, player-driven economy. Local markets and airship hauling create trade routes, and partial-loot PvP keeps goods leaving the world.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Gear source | Mixed: monster drops and player crafting are both viable sources of gear |
| Currency | Single gold currency |
| Markets | Local order books per town. Goods must be physically hauled, and prices differ between towns |
| Gold sinks | Gear durability and repair, town plot rent and upkeep, airship fuel and upkeep |

## Flows

**Faucets** (gold and items entering the world)
- Monster gold drops and quest rewards
- Monster loot: materials, recipes, and some finished gear
- Gathering nodes on the isles

**Sinks** (gold and items leaving the world)
- Repairs, and gear broken beyond repair
- Plot rent and upkeep
- Airship fuel and upkeep
- Resources lost on death (partial loot): some are picked up by other players, and the rest decay
- Crafting inputs consumed

## Loops

- **Gather → craft → sell → repair.** Durability keeps demand for crafted gear steady even when bosses drop gear.
- **Haul.** Buy cheap in one town and sell high in another. Airship fuel is the cost, and PvP risk on the route is the margin.
- **Risk.** Carried resources drop on death in open-world PvP, which feeds looters and keeps raw materials scarce.

## Open questions

- How do crafted and dropped gear stay balanced? Options include drops needing crafted upgrades, or drops having lower durability.
- Should there be any market tax? Not chosen yet; the sinks above are expected to carry the load.
- Can airship cargo be lost or looted, and how much?
- Which item tiers exist, and how fast does gear churn through durability?
