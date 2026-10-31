# Mechanics

Classless, skill-based progression with action combat, open-world risk and a player-run economy. See the [vision](../vision.md) for the pillars.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Progression | Use-based skills, 0–100 each. **Soft cap with decay**: no hard total cap; unused skills decay slowly and never below half their peak, so returning to an old skill is fast |
| Skill count | About 35 skills across combat, magic, gathering, crafting and travel (list below) |
| Abilities | **Learned techniques** from trainers and scrolls, unlocked at skill thresholds. **6 technique slots**, swapped outside combat |
| Controls | **Hybrid**: free-aim attacks by default, with an optional soft lock-on toggle (good for gamepad) |
| Risk zones | **Three tiers**, see below |
| Death | Carried resources drop at the death spot for a while; equipped gear stays but loses durability. Respawn at the **nearest Accord shrine** |
| Crafting | **Simple recipes**: recipe plus materials makes an item; skill sets the success chance and quality roll |
| Group PvE | **Sinking-isle events** and **world bosses** |
| Long-term goals | Mastery and rare techniques, rare drowned-world relic gear, ships and trade empires, reputation and customization |

## Risk tiers

| Tier | Where | PvP | Death |
| --- | --- | --- | --- |
| **Safe** | Accord towns | None | — |
| **Guarded** | Accord sky lanes and each people's home isles | Consensual only (duels, flagged players) | Durability loss only |
| **Wild** | Contested, wild and sinking isles; uncharted wind routes | Open | Partial loot: carried resources drop |

## Skills

About 35 skills (approved 2026-11-01). Every skill rises by use and decays slowly when unused.

| Group | Skills |
| --- | --- |
| **Weapons (8)** | Blades, Heavy Weapons (axes, hammers), Polearms, Daggers, Bows, Thrown, Shields, Unarmed |
| **Magic (5)** | Wind (movement, gusts), Stone (wards, quakes), Tide (healing, water), Bloom (growth, roots), Oathcraft (bindings and buffs, a Veiled tradition) |
| **Defence and survival (4)** | Light Armour, Heavy Armour, Evasion, Field Medicine |
| **Gathering (6)** | Mining, Woodcutting, Herbalism, Fishing, Hunting, Salvage (diving and recovering relics) |
| **Crafting (9)** | Smithing, Carpentry, Leatherworking, Tailoring, Stonecraft, Alchemy, Cooking, Shipwright, Sailweaving (enchanting sails) |
| **Travel and lore (3)** | Sailing, Climbing, Lore (identifying relics, reading the Ledger) |

Each people has cultural affinities but no restrictions. For example, Skerrin lean towards Mining and Climbing, and Rillfolk towards Salvage and Fishing.

## Techniques

- Each weapon and magic skill has a technique tree, unlocked at skill thresholds (25 / 50 / 75 / 100), learned from trainers or found as scrolls.
- Six slots. A build is a mix, for example 3 Polearm + 2 Wind + 1 Field Medicine.
- Techniques are swapped at any time outside combat, so roles change with gear and loadout rather than a class.
- Rare and master techniques drop from world bosses and relic finds, which is part of the long-term chase.

## Core loops

- **Gather → craft → sell**: wild isles have the best nodes, so gatherers take risk and crafters pay for it.
- **Haul**: sail goods between town markets. Sailweavers keep ships running, and wild routes are faster but open PvP.
- **Fight**: world bosses and sinking-isle events drop techniques, relic gear and rare materials.
- **Sinking-isle events**: an isle's last days on a shard. Evacuate settlers, salvage relics and resources, and fight for the spoils before the isle drops into the storm layer.

## Open questions

- Exact decay rate, and whether the "half of peak" floor is per skill.
- How fast skills rise, and which actions grant gains (anti-macro rules).
- Technique counts per tree, and how weapon and magic techniques interact.
- Is stamina or mana the shared resource, or both?
- Sinking cadence: scheduled per shard, triggered by players, or slowed by Rootborn tending?
- Relic sources: with dives not chosen as group content, do relics come only from sinking isles and world bosses, or also from solo or small-group dives?
