# Mechanics

Classless, skill-based progression with action combat, open-world risk and a player-run economy. **Mechanics stay simple**: few systems, each easy to grasp. See the [vision](../vision.md) for the pillars.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Progression | Use-based skills, 0–100 each. **Soft cap with decay**: no hard total cap; unused skills decay slowly and never below half their peak, so returning to an old skill is fast |
| Everything is a skill | No separation between magic and other skills. Wind magic, swordplay, cooking and sailing all work the same way |
| Resources | **No mana.** Magic uses the same resources as any other skill |
| Learning | Skills are learned at a **source**: a trainer, a book, or a place tied to the skill. At a high level a player can **become a trainer**; at an even higher level they can **write books** that teach the skill |
| Skill count | About 35 skills across combat, magic, gathering, crafting and travel (list below) |
| Abilities | **Learned techniques** from trainers and books, unlocked at skill thresholds. **6 technique slots**, swapped outside combat |
| Controls | **Hybrid**: free-aim attacks by default, with an optional soft lock-on toggle (good for gamepad) |
| Risk zones | **Three tiers**, see below |
| Death | Carried resources drop at the death spot for a while; equipped gear stays but loses durability. Respawn at the **nearest Accord shrine** |
| Crafting | **Simple recipes**: recipe plus materials makes an item; skill sets the success chance and quality roll |
| Group PvE | **Sinking-isle events** and **world bosses** |
| Sinking | Slowed by Rootborn tending the ancient trees; a sinking isle can't be saved. Rare **isle births** add new land as world events |
| Gear | Wears down with use, as well as on death. Worn gear is repaired by crafters or replaced |
| Ships | Three sizes; can be attacked and cargo looted. Sails wear from attacks, weather and distance travelled. See [sailing](#sailing) |
| Quests and achievements | Quests give direction and story; achievements record what a character has done. No endgame |
| Long-term goals | Mastery and rare techniques, rare drowned-world relic gear, ships and trade empires, reputation and customization |

## Risk tiers

| Tier | Where | PvP | Death |
| --- | --- | --- | --- |
| **Safe** | Accord towns | None | — |
| **Guarded** | Accord sky lanes and each people's home isles | Consensual only (duels, flagged players) | Durability loss only |
| **Wild** | Contested, wild and sinking isles; uncharted wind routes | Open | Partial loot: carried resources drop |

## Skills

About 35 skills (approved 2026-11-01). Every skill is learned at a source, rises by use and decays slowly when unused. The groups are only for reading the list: an arcane skill works like any other.

| Group | Skills |
| --- | --- |
| **Weapons (8)** | Blades, Heavy Weapons (axes, hammers), Polearms, Daggers, Bows, Thrown, Shields, Unarmed |
| **Arcane (5)** | Wind (movement, gusts), Stone (wards, quakes), Tide (healing, water), Bloom (growth, roots), Oathcraft (bindings and buffs, a Veiled tradition) |
| **Defence and survival (4)** | Light Armour, Heavy Armour, Evasion, Field Medicine |
| **Gathering (6)** | Mining, Woodcutting, Herbalism, Fishing, Hunting, Salvage (diving and recovering relics) |
| **Crafting (9)** | Smithing, Carpentry, Leatherworking, Tailoring, Stonecraft, Alchemy, Cooking, Shipwright, Sailweaving (enchanting sails) |
| **Travel and lore (3)** | Sailing, Climbing, Lore (identifying relics, reading the Ledger) |

Each people has cultural affinities but no restrictions. For example, Skerrin lean towards Mining and Climbing, and Rillfolk towards Salvage and Fishing.

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

## Sailing

| Ship | Aboard | Steered by |
| --- | --- | --- |
| **Skiff** | Up to 5 | 1: one person steers and trims the sails |
| **Cutter** | Up to 10 | 1: one person steers and trims the sails |
| **Galleon** | Up to 100 | 2: a helmsman steers while a sailmaster works the sails |


- **Realistic sail simulation.** Ships move by sail trim, heading against the wind, and hull drag. Tacking, running and reaching all feel different, and a well-trimmed ship beats a badly handled one.
- **Enchanted wind directions.** The sky has wind currents with set directions and strengths. Accord lanes have charted, steady winds. Wild routes have stronger, shifting winds: faster, but in open-PvP space.
- **Sail wear.** Sails wear from attacks, weather (storms, gusts) and distance travelled. Worn sails catch less wind, and Sailweavers re-enchant them.
- **Ship combat.** Ships can be attacked anywhere PvP is allowed. A disabled ship's cargo can be looted.

## Open questions

- Exact decay rate, and whether the "half of peak" floor is per skill.
- How fast skills rise, and which actions grant gains (anti-macro rules).
- Technique counts per tree.
- With no mana: is stamina the only resource, or do techniques just have cooldowns?
- Skill levels needed to become a trainer and to write books, and whether written books carry their author's name.
- Which sources teach which skills, and whether some skills can only be learned in certain places.
- Base sinking cadence per shard, and how much tending slows it.
- How often isles are born, and what triggers the birth.
- Ship combat weapons (spells, bows, boarding) and how a ship is disabled.
- Can ships themselves be destroyed or captured, or only their cargo taken?
- Relic sources: with dives not chosen as group content, do relics come only from sinking isles and world bosses, or also from solo or small-group dives?
