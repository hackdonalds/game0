// Per-people stats and lines. Stats follow concept/entries/peoples + skills: Galeborne light and quick,
// Anchorkin huge and heavy (slow, extra fall damage), Rootwardens stocky and steady.
import type { People } from "../contracts";

export interface PeopleDef {
  id: People;
  name: string;
  line: string;
  skill: { name: string; verb: string; text: string };
  speed: number; // run speed m/s
  accel: number;
  jump: number; // take-off velocity
  gravity: number;
  hp: number;
  stamina: number;
  damage: number; // per swing (third hit of a combo x1.6)
  swing: number; // seconds per swing
  push: number; // how far gusts and hits shove you (1 = normal)
  fallDamage: number; // multiplier
}

export const PEOPLES: PeopleDef[] = [
  {
    id: "galeborne",
    name: "Galeborne",
    line: "Hollow-boned, feather-mantled folk of the highest isles. They glide where others need a ship.",
    skill: { name: "Glide", verb: "Glide", text: "Hold in the air to spread your mantle: slow fall, long forward glide. Costs stamina." },
    speed: 6.6, accel: 14, jump: 8.6, gravity: 21, hp: 90, stamina: 100, damage: 10, swing: 0.36, push: 1.35, fallDamage: 0.8,
  },
  {
    id: "anchorkin",
    name: "Anchorkin",
    line: "Huge stone-skinned folk of the lowest isles. Nothing moves an Anchorkin who doesn't want to move.",
    skill: { name: "Anchor", verb: "Anchor", text: "Hold to plant your feet: no gust, charge or knockback can move you. You can't walk while anchored." },
    speed: 4.9, accel: 8, jump: 6.6, gravity: 27, hp: 150, stamina: 100, damage: 15, swing: 0.5, push: 0.75, fallDamage: 1.6,
  },
  {
    id: "rootwarden",
    name: "Rootwarden",
    line: "Bark-skinned and slow to age, they tend the ancient trees that slow the sinking.",
    skill: { name: "Take Root", verb: "Take Root", text: "Stand still and hold to take root: regain health and stamina, much faster under the old trees." },
    speed: 5.6, accel: 11, jump: 7.4, gravity: 23, hp: 115, stamina: 100, damage: 12, swing: 0.42, push: 1, fallDamage: 1,
  },
];

export const byId = (id: People) => PEOPLES.find((p) => p.id === id)!;

/** Maren's lines. Each entry is one page of the dialogue box. */
export const MAREN = {
  greet: {
    galeborne: "A Galeborne. First off any isle, your lot. Don't be first off this one, not tonight.",
    anchorkin: "An Anchorkin. Good, you won't blow away. That's more than I can say for my sails.",
    rootwarden: "A Rootwarden, out here? Then the old trees on the ridge will know you.",
  } as Record<People, string>,
  intro: [
    "Storm's rolling in off the Spoke, and the Waystone has gone dark. Without it every skiff in the lane flies blind.",
    "The stone wakes on glimmer. The surge scattered three shards across the meadow. Find them.",
  ],
  route: {
    galeborne: "Then cross the Storm Ridge your way: climb to the cliff edge, jump, and hold your skill in the air to glide down to the ledge under the stone.",
    anchorkin: "Then take the rope bridge over the Storm Ridge. The gusts will try to throw you off. When one comes, plant your feet: hold your skill until it passes.",
    rootwarden: "Then walk the ridge path. The storm drinks the life out of anyone on it, but the old trees shelter it. Stop under them and take root.",
  } as Record<People, string>,
  warn: "Something storm-born sits on the stone now. Boar-shaped, all cloud and lightning. When it rears up, step aside: it charges in a straight line.",
  reminder: {
    shards: "Three glimmer shards, scattered across the meadow. Look for the glow.",
    ridge: {
      galeborne: "The cliff edge, then glide. Hold your skill once you're in the air.",
      anchorkin: "The rope bridge. Anchor when the gusts come.",
      rootwarden: "The ridge path. Take root under the old trees.",
    } as Record<People, string>,
    boss: "The Stormspawn is still on the stone. Watch for it rearing up.",
    stone: "Set the shards in the Waystone. Go on.",
    done: "Look at the lane. Every skiff out there can see its way home now. Thank you.",
  },
};
