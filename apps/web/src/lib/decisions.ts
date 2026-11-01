// The decision log is read straight out of the concept docs: rows of every "Decisions" table, and every open question.
import { getCollection } from "astro:content";
import { chapters, docToChapter } from "../data/chapters.mjs";

export interface DocDecisions { doc: string; title: string; chapter: string; decisions: { topic: string; decision: string }[]; open: string[] }

const clean = (s: string) => s.replace(/\*\*/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/`/g, "").trim();

export async function decisionLog(): Promise<DocDecisions[]> {
  const docs = await getCollection("concept");
  const out: DocDecisions[] = [];
  for (const d of docs) {
    const chapter = docToChapter[d.id];
    if (!chapter) continue;
    const body = d.body ?? "";
    const title = body.match(/^# (.+)$/m)?.[1] ?? d.id;
    const sections = body.split(/^## /m).slice(1).map((s) => ({ head: s.split("\n")[0].trim(), text: s }));
    const decisions = sections.filter((s) => /^decisions/i.test(s.head)).flatMap((s) =>
      s.text.split("\n").filter((l) => l.startsWith("|") && !/^\|\s*-/.test(l)).slice(1)
        .map((l) => l.split("|").slice(1, -1).map(clean)).filter((c) => c.length >= 2).map(([topic, decision]) => ({ topic, decision })));
    const open = sections.filter((s) => /^open questions/i.test(s.head)).flatMap((s) => s.text.split("\n").filter((l) => /^- /.test(l)).map((l) => clean(l.slice(2))));
    out.push({ doc: d.id, title, chapter, decisions, open });
  }
  const order = chapters.map((c) => c.slug);
  return out.sort((a, b) => order.indexOf(a.chapter) - order.indexOf(b.chapter));
}
