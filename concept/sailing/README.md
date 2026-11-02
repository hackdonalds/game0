---
chapter:
  slug: sailing
  number: 5
  title: Sailing
  kicker: Sail, wind and wear
  summary: Ships from the one-handed skiff to the crewed galleon, trimmed against enchanted wind currents. Charted Accord lanes, wild shortcuts, and sails that wear thin.
  catalogues: [ ships, winds ]
  demo: sail
  art: a wooden sailing galleon with glowing enchanted sails heeling hard into a visible stream of wind current between floating isles, crew working the rigging, wind streaks in the air
---

# Sailing

Wooden sailships carried by enchanted sails on wind currents: the way to move groups and cargo between isles. See the [economy](../economy/README.md) for hauling and the [world](../world/README.md) for the wind lanes.

## Ships

Ships come in sizes from a skiff one person can sail to a galleon that needs a crew to steer it. Each ship's crew, steering, cargo, wear and building cost is on its entry in [`entries/ships/`](../entries/ships/).

## How sailing works

- **Realistic sail simulation.** Ships move by sail trim, heading against the wind, and hull drag. Tacking, running and reaching all feel different, and a well-trimmed ship beats a badly handled one.
- **Enchanted wind directions.** The sky has wind currents with set directions and strengths. Accord lanes have charted, steady winds. Wild routes have stronger, shifting winds: faster, but in open-PvP space.
- **Sail wear.** Sails wear from attacks, weather (storms, gusts) and distance travelled. Worn sails catch less wind, and Sailweavers re-enchant them.
- **Ship combat.** Ships can be attacked anywhere PvP is allowed. A disabled ship's cargo can be looted.

## Wind currents

- **Accord lanes** are charted, steady winds between towns and homelands, in guarded space.
- **Wild currents** are fast, gusty and shifting, in open-PvP space: shortcuts with risk.
- Outside currents, a light **ambient wind** blows across the whole shard.
- The [First Shard](../../worlds/first-shard.world.json) map defines every current's route, speed, width and gustiness.

## Open questions

- Ship combat weapons (spells, bows, boarding) and how a ship is disabled.
- Can ships themselves be destroyed or captured, or only their cargo taken?
- Cargo capacity per ship, and crafting costs.
