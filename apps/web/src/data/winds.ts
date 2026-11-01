// Handbook notes for every wind current on the First Shard. Ids match worlds/first-shard.world.json.

import type { WindNote } from "./types";

export const windNotes: WindNote[] = [
  // Accord lanes (guarded)
  {
    id: "wind_accord-ring",
    blurb: "The steady clockwise lane that links the four Accord towns. Sailors call it the kindest wind in the sky: no tacking, no surprises, just patience.",
  },
  {
    id: "wind_tether-spoke",
    blurb: "Runs from Accord Hall out to Tetherport. Shipwrights test new hulls on it, so expect fresh paint and nervous crews.",
  },
  {
    id: "wind_market-spoke",
    blurb: "Carries the Windmarket caravans home to Accord Hall. It is crowded at dawn, and every skiff on it seems to be late for a sale.",
  },
  {
    id: "wind_lantern-spoke",
    blurb: "Blows from Accord Hall down to Lanterncross, past the Waystone. Night crews steer by the lanterns at its far end.",
  },
  {
    id: "wind_oath-spoke",
    blurb: "Brings Oathgate's travellers in to Accord Hall. Envoys bound for the Hall favour it, and sailors say a quiet tongue is wise aboard.",
  },
  {
    id: "wind_rootward",
    blurb: "Climbs from Tetherport to Elderroot in the north. It smells of leaf mould, and Rootwarden crews hum to it as they sail.",
  },
  {
    id: "wind_gardenward",
    blurb: "A slow, easy lane from Windmarket to Hearthfield. Farmers say it was made for hay carts, and nobody has argued.",
  },
  {
    id: "wind_moorward",
    blurb: "Drops from Lanterncross to Ledgerstone, the lowest of the lanes. Watch the clouds beneath you: on a bad day the storm is close.",
  },
  {
    id: "wind_spireward",
    blurb: "Climbs hard from Oathgate to High Spire. Galeborne say it is the only lane that makes you earn your arrival, then glide down it in half the time.",
  },

  // Wild currents (open PvP)
  {
    id: "wind_the-long-gale",
    blurb: "A fierce northern current from the Crag rim to the far east, past Ironreach and Hollowsky. It is the fastest way across the shard, if your sails hold and nobody is waiting for you.",
  },
  {
    id: "wind_drowned-drift",
    blurb: "A low, gusting current that skims the storm along the southern rim, past Vael's Shadow and Wreckrest. Sailors say the storm can hear you on it.",
  },
  {
    id: "wind_grudge-wind",
    blurb: "Runs up the contested west from Brokenreach past Grudgewood. Rootwarden and Galeborne crews meet on it often, and seldom politely.",
  },
];
