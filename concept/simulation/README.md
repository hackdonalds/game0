# Simulation

How a shard fills its world with thousands of NPCs and bot characters while staying fast. Prototype: [`demos/npc-lod`](../../demos/npc-lod).

## Goal

From day one, a shard should feel lived in: caravans on the wind lanes, farmers on the Garden Isles, shipwrights on the Crag Spires, traders in the Accord towns. That means about **500–2,000 simulated characters per shard** next to 50–200 real players, without the server or clients slowing down.

## Three levels of detail

Every character is always simulated, but how closely depends on how close a real player is. The shard server picks the level for each character.

| Level | When | What runs | Update rate |
| --- | --- | --- | --- |
| **Full** | Within about 120 m of a real player | Steering, avoidance, combat, reactions to players, animation state, behaviour tree | 20 Hz |
| **Light** | Within about 350 m, or on the same isle | A simple state machine (walk, work, idle) with no physics or avoidance; clients interpolate between updates | 1 Hz |
| **Abstract** | Everywhere else | A plan with a start and end time: "sailing Ironcleft → Windmarket, arrives at 14:32" or "mining at Ironcleft until 14:50". Position is calculated from the plan only when someone needs it | A batch check every few seconds; work only happens when a plan ends |

- **Promotion:** when a player comes near, the character is placed where its plan says it should be, then runs at the higher level. Players can't tell the difference.
- **Demotion:** when no player is near, the character keeps its current plan and drops back to abstract. Its local position is dropped; nobody is there to see it.
- Most characters are abstract at any moment, so the cost scales with **players**, not with characters. 5,000 characters cost about as much as the few hundred near players.

## Bots and NPCs

- **NPCs** are world characters: townsfolk, caravans, workers, monsters.
- **Bot characters** are server-side actors that play by the same rules as players: they gather, craft, haul, post market orders and fight. They have no network connection, client or rendering.
- Both go through the same action calls as players (move, gather, buy, sell, attack), so they can't cheat and they feed the real [economy](../economy/README.md): prices, routes and scarcity work from launch.
- Bot numbers scale down automatically as real players join a shard.

## Where AI fits

| How often | What decides | Examples |
| --- | --- | --- |
| Every tick | Plain code and behaviour trees | Pathing, steering, combat |
| When a plan ends | A utility planner (scores options) | "Ore sells high at Windmarket, so go mine Ironcleft" |
| Rarely | An LLM, called asynchronously, batched and cached | A bot guild leader picking a war target; dialogue when a player talks to an NPC |

- An LLM is never in the tick loop. Its calls are queued, and the character keeps following its current plan until an answer arrives.
- A small, fast model for most calls; a larger one only for rare, important decisions.

## Clients

- The server only sends each player the characters near them (area of interest). Full characters update often, light ones rarely, and abstract ones not at all.
- Distant crowds use instanced or simplified models.

## From the world file

The [world file](../../worlds/README.md) says who lives where. The server spawns characters from it:

- **Traders** travel between Accord towns.
- **Haulers** run between their homeland and the nearest town.
- **Gatherers** work wild isles and bring goods home.
- **Workers** stay on their home isle (farmers, miners, divers).

## Open questions

- Exact radii and rates per level, tuned against real server load.
- How bots pick what to do in the economy without crashing prices.
- Whether NPCs on sinking isles evacuate as part of the event.
- How bot characters present to players: named, with gear and reputation, or clearly marked as NPCs.
