// Every image the site shows is a plate under art/handbook/<kind>/<name>.webp, made by scripts/handbook-sheets.ts
// (`bun run art:sheets`) from art/concept, art/kit, art/models and art/textures. Looked up by key "<kind>/<name>".
const handbook = import.meta.glob<{ default: ImageMetadata }>("../../../../art/handbook/*/*.webp", { eager: true });

const plates = new Map<string, ImageMetadata>();
for (const [path, mod] of Object.entries(handbook)) {
  const [kind, file] = path.split("/").slice(-2);
  plates.set(`${kind}/${file.replace(".webp", "")}`, mod.default);
}

export const plate = (key: string) => plates.get(key);

/** Every plate key under a prefix, e.g. "biomes/crag-", sorted */
export const plateKeys = (prefix: string) => [...plates.keys()].filter((k) => k.startsWith(prefix)).sort();
