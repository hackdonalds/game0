---
chapter:
  slug: peoples
  number: 3
  title: Peoples
  kicker: Who shares the sky
  summary: Who the playable peoples are, where they live, their innate skills, what they hold against each other, and how players shape them.
  docs:
    - art-direction/character-customization.md
  catalogues: [ peoples ]
  demo: peoples
  art: "three fantasy travellers standing together on a cliff edge at dawn seen from behind: a tall slender figure with a folded feathered mantle, a huge broad figure with grey stone skin veined with teal crystal, and a stocky bark-skinned figure with moss and small flowers on its shoulders, looking out over floating isles"
---

# Peoples

The playable peoples at launch are the [Galeborne](../entries/peoples/galeborne.md), the [Anchorkin](../entries/peoples/anchorkin.md) and the [Rootwardens](../entries/peoples/rootwarden.md). More peoples are planned for later, and everything about peoples is built so a new one can be added without changing the others (see [Adding a people](#adding-a-people)).

Characters read first by people, then by gear. There are no classes: any people can follow any path. Each people has a **homeland**, cultural affinities, and one **innate skill** that only it can learn. Each people's look, homeland, culture, first hours, relations and signature features are written on its entry in [`entries/peoples/`](../entries/peoples/).

Outfit tone for all peoples: grounded, handmade leather, cloth and forged metal, with epic details such as teal crystal, gold trim and culture motifs.

## Innate skills

Innate skills follow the same rules as every other [skill](../mechanics/README.md#skills): they start low, rise with use (0–100) and unlock techniques. The only difference is that no other people can learn them. Each one has a clear strength and a clear limit, written on its skill entry: [Glide](../entries/skills/glide.md) for the Galeborne, [Anchor](../entries/skills/anchor.md) for the Anchorkin and [Take Root](../entries/skills/take-root.md) for the Rootwardens.

## Old grudges and ties

- **Galeborne vs Rootwardens:** the Galeborne need ancient wood for masts and hulls. The Rootwardens say every old tree felled hastens the sinking. **Grudgewood**, on their shared frontier, is the oldest quarrel on the shard.
- **Rootwardens and Anchorkin:** old allies who hold the land: one with roots, the other with chains.
- **Galeborne and Anchorkin:** wary trade partners. The Galeborne carry goods across the sky and buy Anchorkin chain and stone. The Anchorkin don't trust a people who can leave any isle the moment it starts to fall.

## Adding a people

A new people is one entry file, `entries/peoples/<id>.md`, plus its innate skill as `entries/skills/<skill>.md` with `innateTo: <id>`. It needs:

- a look and a signature layer for [customization](../art-direction/character-customization.md);
- a homeland or a reason to have none (the **Garden Isles** in the east of the First Shard are unclaimed, kept for this);
- cultural affinities with existing skills (the `affinity` list of those skill entries);
- one innate skill with a strength and a limit;
- a tie or grudge with at least one existing people.

## Retired concepts

The earlier lineup of five (Rootborn, Veiled Ones, Mossbacks, Skerrin and Rillfolk) was retired in favour of this one: too many of them were beast-folk, and their player fantasy was weak. Their concept art and 3D models stay in `art/` as drafts. Pitches kept for later peoples:

- **Lanternborn:** near-humans whose veins glow. Their light reveals storm-touched creatures and hidden paths.
- **Oathbound:** masked, faceless wanderers who swear oaths for strong buffs that break if the oath is broken.

Rejected in earlier rounds: Galeborn (the old wind-folk sketch), Hearthkin, Glimmerfolk, Brushtails, Hartkin, Cindrel, Shardkin, Nimbari, Lumenwings, Tidewrought, Hollow, Windspeakers.

## Open questions

- Home towns within each homeland beyond the shrine isle.
- Male, female and body variation for each people.
- Exact numbers for each innate skill (glide distance, anchor hold time, regeneration rate).
