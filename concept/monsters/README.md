# Monsters

> Decisions approved 2026-11-01. The bestiary below is a first draft.

Creatures of the isles and the sky, the storm-touched, and world bosses.

## Decisions

| Topic | Decision |
| --- | --- |
| Tone | Mostly **natural creatures** that behave like animals. **Storm-touched** versions, twisted by the [storm below](../world/README.md#premise), are more dangerous |
| Temperament | Each creature has one: **passive** (flees), **neutral** (fights back), **territorial** (attacks if you come close) or **hostile** (hunts you). Storm-touched creatures are always hostile |
| Difficulty | Set by **risk tier**: weaker creatures on safe and guarded isles, the strongest on wild isles and the rim. A creature's strength is fixed by its kind, since characters have no levels |
| Readability | Danger is readable: size, look and a danger mark show how strong a creature is compared to your skills. Storm surges are the only surprise |
| Day and night | Some creatures only come out at night, or behave differently after dark |
| Seasons | Flocks and herds migrate between isles with the seasons |
| Flying creatures | Some attack ships in the air, not just players on isles |
| Populations | Each isle has a population of each creature that refills over time. Overhunting thins it out for a while, so hunters move on |
| Taming | A **Taming** skill turns some creatures into **ground mounts**, **pack animals** or **flying mounts** |
| World bosses | Rise from the storm during **storm surges** at wild isles, announced shortly before. They **scale with how many players are nearby** |
| Boss loot | **Everyone who helped** gets their own reward. A bonus drop lands on the ground for players to fight over |
| Relics | From **sinking isles**, **world bosses**, solo and small-group **dives** into the drowned world, and ruins on newborn isles |

## Flying mounts and ships

Flying mounts must not replace ships. Proposed limits, to confirm:

- One rider, no passengers and little cargo.
- They tire: flight uses the mount's stamina, so long crossings need rests on isles.
- They can't fly through wild currents or near the storm layer.
- Only rare creatures can be tamed for flight, at high Taming skill.

Ships stay the way to move groups and cargo.

## Built to extend

New creatures, and new peoples later, are added as data without changing the game's systems.

Every creature is defined by:

| Field | Example (cliff goat) |
| --- | --- |
| Body | Model, size, animations |
| Skills | The same skills players use, at fixed levels: Unarmed 30, Climbing 70 |
| Temperament | Neutral |
| Behaviours | Shared building blocks combined per creature: graze, flee, charge, climb |
| Habitat | Crag biome, guarded and wild tiers, all seasons, day and night |
| Population | 12 per isle, refills in 2 hours |
| Drops | Meat, hide, horn |
| Taming | Ground mount, Taming 40 |
| Storm-touched variant | Stormhorn goat: hostile, adds a lightning charge |

Behaviour building blocks: wander, graze, flee, guard, charge, hunt, swarm, ambush, climb, fly, dive at ships, migrate, sleep by day.

## First bestiary (draft)

| Where | Creature | Temperament | Notes |
| --- | --- | --- | --- |
| Meadows and forests | **Burrow boar** | Neutral | Meat and hide. Tameable ground mount |
| | **Glider squirrel** | Passive | Fur. Glides between trees |
| Rootholds | **Rootcrawler** | Territorial | Beetles in the roots. Chitin |
| | **Bark owl** | Passive | Night only. Feathers |
| Garden Isles | **Moss grazer** | Passive | Slow herd beast. Tameable pack animal |
| | **Burrow mole** | Neutral | Digs up crops. A job-board favourite |
| Crag Spires | **Cliff goat** | Neutral | Tameable ground mount |
| | **Crag drake** | Territorial | Small drake that nests on spires. Flies |
| | **Stonewing bat** | Territorial | Night swarms in caves |
| Glimmer Lagoons | **Lantern eel** | Territorial | Glows at night. Prized by cooks |
| | **Shellback crab** | Neutral | Shell and meat |
| Open sky | **Cloud whale** | Passive | Huge, migrates with the seasons. Ships follow its wake |
| | **Gale hawk** | Hostile | Flocks that harass skiffs on wild routes |
| | **Skyray** | Territorial | Attacks ships. Rare flying mount at high Taming |
| Wild rim and ruins | **Ruin stalker** | Hostile | Ambushes in old-world ruins |
| Storm surges | **Stormspawn** | Hostile | Storm-touched versions of local creatures |

## World bosses (draft)

| Boss | Where | Fight |
| --- | --- | --- |
| **The Tempest Serpent** | Rises during surges on the sky lanes near the rim | Coils around isles and attacks ships. Fought from decks and isle edges |
| **The Drowned Colossus** | Climbs onto a sinking isle | An old-world construct, walking ruins. Carries relics |
| **The Stormmother** | Rare surge at the deepest wild isles | Calls stormspawn waves. Drops rare techniques and relics |

## Open questions

- Final names and looks, after concept art.
- How often storm surges happen, and how much warning players get.
- Flying mount limits (above).
- How dangerous dives into the drowned world are, and how long they last.
