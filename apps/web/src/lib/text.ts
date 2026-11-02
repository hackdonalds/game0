export const base = import.meta.env.BASE_URL.replace(/\/$/, "");
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** Sort key that ignores a leading "The " */
export const sortName = (s: string) => s.replace(/^The /, "");
/** Strip markdown to plain text for search and excerpts */
export const plain = (md: string) =>
  md.replace(/```[\s\S]*?```/g, "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_`>#|]/g, " ").replace(/-{3,}/g, " ").replace(/\s+/g, " ").trim();
const NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];
/** A count in words for prose ("three"), so text that counts content follows the content */
export const count = (n: number) => NUMBER_WORDS[n] ?? String(n);
