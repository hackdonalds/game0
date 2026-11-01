// Short card data for the peoples stage, derived from the handbook entries.
import { peopleEntries } from "./peoples-handbook";

export const peoples = peopleEntries.map((p) => ({
  id: p.id,
  name: p.name,
  homeland: p.homeland,
  blurb: p.blurb,
  known: p.knownFor.replace(/\.$/, ""),
}));
