---
chapter:
  slug: play
  number: 4
  title: How You Play
  kicker: Everything is a skill
  summary: Classless skills learned at their source, six technique slots, stamina and cooldowns, risk tiers, death and loot, quests and the first hours.
  catalogues: [ skills, materials ]
  art: an open old book of skills on a wooden table in a trainer's workshop, glowing wind runes rising from its pages, surrounded by a sword, a pickaxe, a cooking pot, a coil of rope and a sailmaker's needle, warm window light
---

# Mechanics

Classless, skill-based progression with action combat, open-world risk and a player-run economy. **Mechanics stay simple**: few systems, each easy to grasp. See the [vision](../vision.md) for the pillars.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Progression | Use-based skills, 0–100 each. **Soft cap with decay**: no hard total cap; unused skills decay slowly and never below half their peak, so returning to an old skill is fast |
| Everything is a skill | No separation between magic and other skills. Wind magic, swordplay, cooking and sailing all work the same way |
| Resources | **No mana.** One **stamina** bar for everything (swinging, casting, dodging, sprinting), refilling quickly at rest. Strong techniques also have their own **cooldowns** |
| Learning | Skills are learned at a **source**: a trainer, a book, or a place tied to the skill. At **75** a player can **become a trainer**; at **100** they can **write books** that teach the skill |
| Skill count | A fixed list of shared skills across combat, magic, gathering, crafting and travel (see [skills](#skills)), plus one innate skill per people |
| Abilities | **Learned techniques** from trainers and books, unlocked at skill thresholds. **6 technique slots**, swapped outside combat |
| Controls | **Hybrid**: free-aim attacks by default, with an optional soft lock-on toggle (good for gamepad) |
| Risk zones | **Three tiers**, see below |
| Death | Carried resources drop at the death spot for a while; equipped gear stays but loses durability. Respawn at the **nearest Accord shrine** |
| Crafting | **Simple recipes**: recipe plus materials makes an item; skill sets the success chance and quality roll |
| Group PvE | **Sinking-isle events** and **world bosses** from storm surges. See [monsters](../monsters/README.md) |
| Sinking | Slowed by **Treetending** the ancient trees (a skill anyone can learn); a sinking isle can't be saved. Rare **isle births** add new land as world events |
| Gear | Wears down with use, as well as on death. Worn gear is repaired by crafters or replaced |
| Ships | Three sizes; can be attacked and cargo looted. Sails wear from attacks, weather and distance travelled. See [sailing](../sailing/README.md) |
| Quests and achievements | Quests give direction and story; achievements record what a character has done. No endgame. See [quests](#quests) |
| Gear tiers | Set by **material**; crafting skill sets the **quality** within a tier. See [economy](../economy/README.md) |
| First hours | Start in your people's homeland. See [first hours](#first-hours) |
| Long-term goals | Mastery and rare techniques, rare drowned-world relic gear, ships and trade empires, reputation and customization |

## Risk tiers

| Tier | Where | PvP | Death |
| --- | --- | --- | --- |
| **Safe** | Accord towns | None | — |
| **Guarded** | Accord sky lanes and each people's home isles | Consensual only (duels, flagged players) | Durability loss only |
| **Wild** | Contested, wild and sinking isles; uncharted wind routes | Open | Partial loot: carried resources drop |

## Skills

Approved 2026-11-01 (Treetending added 2026-11-01). Every skill is learned at a source, rises by use and decays slowly when unused. Each skill, with its sources, affinities and what it unlocks at 25, 50, 75 and 100, is an entry in [`entries/skills/`](../entries/skills/). The groups (weapons, arcane, defence and survival, gathering, crafting, travel and lore) are only for reading the list: an arcane skill works like any other.

Each people has cultural affinities but no restrictions: a skill entry's `affinity` lists the peoples known for it, and any people can learn it. Each people also has one **innate skill** only it can learn (see [peoples](../world/peoples.md#innate-skills)).

## Techniques

- Each combat and arcane skill has a technique tree, unlocked at skill thresholds (25 / 50 / 75 / 100), learned from trainers or books.
- Players who become trainers can teach techniques they know, and book-writers can put them into books that others buy and trade.
- Six slots. A build is a mix, for example 3 Polearm + 2 Wind + 1 Field Medicine.
- Techniques are swapped at any time outside combat, so roles change with gear and loadout rather than a class.
- Rare and master techniques drop from world bosses and relic finds, which is part of the long-term chase.

## Core loops

- **Gather → craft → sell**: wild isles have the best nodes, so gatherers take risk and crafters pay for it.
- **Haul**: sail goods between town markets. Sailweavers keep ships running, and wild routes are faster but open PvP.
- **Fight**: world bosses and sinking-isle events drop techniques, relic gear and rare materials.
- **Sinking-isle events**: an isle's last days on a shard. Evacuate settlers, salvage relics and resources, and fight for the spoils before the isle drops into the storm layer.

## Quests

Four kinds, all simple to pick up:

- **Story quests** for each people: hand-written chains about their history and grudges.
- **Town job boards**: repeatable jobs from NPCs and the world, such as hauling, gathering, hunting and escorting.
- **Player-posted jobs**: players post paid jobs on the same boards, for example "bring 50 iron to Windmarket".
- **World event quests**: appear with sinkings, isle births, storm surges and seasons.

## First hours

- New characters start on their people's **home isles**, in guarded space.
- Short quests teach movement, gathering, learning a first skill from a trainer, crafting, and a skiff ride to the nearest Accord town.
- From the town, the job boards and story quests take over.

## Open questions

- Exact decay rate, and whether the "half of peak" floor is per skill.
- How fast skills rise, and which actions grant gains (anti-macro rules).
- Technique counts per tree.
- Whether written books carry their author's name.
- Which sources teach which skills, and whether some skills can only be learned in certain places.
- Base sinking cadence per shard, and how much tending slows it.
- How often isles are born, and what triggers the birth.
