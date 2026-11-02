// Fill the animation source cache for a family from art/anims/<family>/sources.json.
// Usage: bun run anim:fetch <family> [--source <id>] [--list <id>]
//   --list prints the entries of a zip-range source's archive instead of fetching
import { parseArgs } from "node:util";
import { cachePath, readSources, save, sha256, zipEntries, zipEntry, type Source } from "./cache";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: { source: { type: "string" }, list: { type: "string" } },
});
const family = positionals[0];
if (!family) throw new Error("Usage: bun run anim:fetch <family> [--source <id>] [--list <id>]");
const sources = await readSources(family);

if (values.list) {
  const s = sources.find((x) => x.id === values.list);
  if (!s?.archive) throw new Error(`${values.list}: not a zip-range source`);
  for (const e of await zipEntries(s.archive)) console.log(e.name, e.size);
  process.exit(0);
}

let fetched = 0;
let bytes = 0;
const missing: string[] = [];
for (const s of sources.filter((x) => !values.source || x.id === values.source)) {
  const entries = s.fetch === "zip-range" ? await zipEntries(s.archive!) : [];
  for (const file of s.files) {
    const path = cachePath(s, file);
    const cached = Bun.file(path);
    if (await cached.exists()) {
      if (file.sha256 && (await sha256(new Uint8Array(await cached.arrayBuffer()))) !== file.sha256)
        throw new Error(`${path}: checksum mismatch`);
      continue;
    }
    const data = await download(s, file.path, file.url, file.entry, entries);
    if (!data) {
      missing.push(`${s.id}/${file.path}: download it by hand from ${s.url} into ${path}`);
      continue;
    }
    if (file.sha256 && (await sha256(data)) !== file.sha256) throw new Error(`${s.id}/${file.path}: checksum mismatch`);
    await save(path, data);
    fetched++;
    bytes += data.length;
  }
}
console.log(`${family}: fetched ${fetched} files (${(bytes / 1e6).toFixed(1)} MB)`);
if (missing.length) {
  console.log("Manual downloads needed:\n  " + missing.join("\n  "));
  process.exit(1);
}

async function download(s: Source, path: string, url?: string, entry?: string, entries: Awaited<ReturnType<typeof zipEntries>> = []) {
  if (s.fetch === "manual") return null;
  if (s.fetch === "zip-range") {
    const e = entries.find((x) => x.name === entry);
    if (!e) throw new Error(`${s.id}: no entry ${entry} in ${s.archive}`);
    return zipEntry(s.archive!, e);
  }
  const res = await fetch(url!);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}
