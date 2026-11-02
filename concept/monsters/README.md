---
chapter:
  slug: creatures
  number: 7
  title: Creatures
  kicker: The bestiary
  summary: Wildlife of the isles, the storm-touched, taming, living populations, and the world bosses that rise with the storm.
  catalogues: [ bestiary ]
  art: "a field naturalist's view of sky wildlife: a cloud whale drifting past a floating isle, a crag drake on a spire, gale hawks circling, a herd of mossy grazers below, all in soft morning light"
---

# Monsters

> Decisions approved 2026-11-01. The bestiary is a first draft.
>
> Every creature and world boss is an entry in [`entries/bestiary/`](../entries/bestiary/), with its full stat block, published as the [Bestiary](https://hackdonalds.github.io/game0/catalogue/bestiary/) on the site. Plates are generated from each entry's `art` brief with `bun run art:bestiary`.

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

Every creature is defined by the same fields; the [cliff goat](../entries/bestiary/cliff-goat.md) is a full example:

| Field | What it holds |
| --- | --- |
| Body | Model, size, animations |
| Skills | The same skills players use, at fixed levels |
| Temperament | One of the four above |
| Behaviours | Shared building blocks combined per creature (below) |
| Habitat | Region (a biome, the open sky or the storm), risk tiers, seasons, time of day |
| Population | How many live on an isle and how fast they refill |
| Drops | What it leaves when killed or gathered |
| Taming | Whether it can be tamed, as what, and at what Taming skill |
| Storm-touched variant | Its storm-twisted form, if it has one |

Behaviour building blocks: wander, graze, flee, guard, charge, hunt, swarm, ambush, climb, fly, dive at ships, migrate, sleep by day.

## Body plans

Creatures are built from shared **body plans**, not modelled one by one. A body plan is one skeleton, one base body and a kit of swappable parts that snap onto fixed sockets. A species is a choice of parts, proportions and a colour mask on its plan, so one rig and one set of animations serve every creature of that plan, and new species are mostly new combinations. Each creature entry names its plan in `bodyPlan`; the members of a plan are read from the entries, not listed here.

| Id | Body plan | Skeleton | Swappable parts (sockets) |
| --- | --- | --- | --- |
| quadruped | Four-legged | Spine, neck, four legs, tail | Head, horns or antlers, ears, tail, feet (hoof, paw, claw, digging claw), coat (smooth, shaggy, mossy, plated), gliding membrane |
| bird | Bird | Spine, neck, two legs, two feathered wings | Head and beak, crest, wings, tail fan, talons, plumage |
| winged | Membrane-winged | Spine, neck, four limbs, two membrane wings, tail | Head, horns, wings, tail tip, spines and plates, claws |
| sky-swimmer | Sky swimmer | One long flexible spine, fins | Head, fins and wings, tail fluke, lights, barnacle and cloud growths |
| shelled | Shelled | Body segments, jointed legs | Shell, claws, legs, antennae, carried growths |
| giant | Giant humanoid | Biped spine, two arms, two legs | Head, crown or mask, arms, carried ruins and storm growths |

Body-plan kit sheets live in `art/kit/bestiary/body-plans/` (`<plan>-body` and `<plan>-parts`); each species has its own sheet at `art/kit/bestiary/<id>` showing its parts on the plan. See [kit sheets](../art-direction/kit-sheets.md#sheet-types).

## The bestiary (draft)

The first creatures and the three world bosses are entries in [`entries/bestiary/`](../entries/bestiary/), grouped by region on the site. Each one has a temperament, skills, actions, drops and, where it has one, a storm-touched variant.

## Open questions

- Final names and looks, after concept art.
- The crag drake: the first bestiary draft called it a small drake, but its entry makes it large (420 health, nests on the highest spires). Which is it?
- How often storm surges happen, and how much warning players get.
- Flying mount limits (above).
- How dangerous dives into the drowned world are, and how long they last.
