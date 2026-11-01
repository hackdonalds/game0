// The search index: chapters (with their headings and text), every catalogue entry and every glossary term.
import { getCollection } from "astro:content";
import type { APIRoute } from "astro";
import { chapters } from "../data/chapters.mjs";
import { catalogues } from "../lib/catalogues";
import { base, plain } from "../lib/text";

export const GET: APIRoute = async () => {
  const docs = await getCollection("concept");
  const body = new Map(docs.map((d) => [d.id, d.body ?? ""]));
  const items = [
    ...chapters.flatMap((c) => {
      const md = c.docs.map((d) => body.get(d) ?? "").join("\n");
      const sections = md.split(/^## /m).slice(1).map((s) => {
        const head = s.split("\n")[0].trim();
        return { t: head, k: `Chapter ${c.number} · ${c.title}`, u: `${base}/${c.slug}/#${head.toLowerCase().replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-")}`, s: plain(s.slice(head.length)).slice(0, 220), x: plain(s).toLowerCase() };
      });
      return [{ t: c.title, k: `Chapter ${c.number}`, u: `${base}/${c.slug}/`, s: c.summary, x: `${c.title} ${c.kicker} ${c.summary}`.toLowerCase() }, ...sections];
    }),
    ...catalogues.flatMap((cat) => cat.cards.map((card) => ({ t: card.name, k: cat.title, u: card.href, s: card.summary.slice(0, 220), x: `${card.name.toLowerCase()} ${card.search}` }))),
  ];
  return new Response(JSON.stringify(items), { headers: { "Content-Type": "application/json" } });
};
