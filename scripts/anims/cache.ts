// Source cache and remote-zip helpers shared by the animation library commands.
import { mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { inflateRawSync } from "node:zlib";

export const CACHE = process.env.GAME0_ANIM_CACHE ?? join(homedir(), ".cache/game0/anims");
export const FAMILIES = "art/anims";

export type SourceFile = { path: string; url?: string; entry?: string; sha256?: string; size?: number };
export type Source = {
  id: string;
  name: string;
  url: string;
  license: string;
  credit: string | null;
  fetch: "manual" | "http" | "zip-range";
  /** zip-range: the archive URL; files[].entry names what to pull out of it */
  archive?: string;
  files: SourceFile[];
};

export const cachePath = (source: Source, file: SourceFile) => join(CACHE, source.id, file.path);

export async function readSources(family: string): Promise<Source[]> {
  const f = Bun.file(join(FAMILIES, family, "sources.json"));
  return (await f.exists()) ? f.json() : [];
}

export async function sha256(bytes: Uint8Array) {
  return new Bun.CryptoHasher("sha256").update(bytes).digest("hex");
}

export async function save(path: string, bytes: Uint8Array) {
  await mkdir(dirname(path), { recursive: true });
  await Bun.write(path, bytes);
}

async function range(url: string, start: number, end: number) {
  const res = await fetch(url, { headers: { Range: `bytes=${start}-${end}` } });
  if (res.status !== 206) throw new Error(`${url}: server ignored the byte range (HTTP ${res.status})`);
  return new Uint8Array(await res.arrayBuffer());
}

export type ZipEntry = { name: string; offset: number; compressed: number; size: number; method: number };

/** List a remote zip's entries by reading only its central directory. */
export async function zipEntries(url: string): Promise<ZipEntry[]> {
  const head = await fetch(url, { method: "HEAD", redirect: "follow" });
  const total = Number(head.headers.get("content-length"));
  if (!total) throw new Error(`${url}: no content-length`);
  const tail = await range(url, Math.max(0, total - 65_557), total - 1);
  const dv = new DataView(tail.buffer);
  let eocd = -1;
  for (let i = tail.length - 22; i >= 0; i--) if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw new Error(`${url}: not a zip`);
  let cdSize = dv.getUint32(eocd + 12, true);
  let cdOffset = dv.getUint32(eocd + 16, true);
  const loc = eocd - 20;
  if (loc >= 0 && dv.getUint32(loc, true) === 0x07064b50) {
    const z64 = Number(dv.getBigUint64(loc + 8, true));
    const rec = await range(url, z64, z64 + 55);
    const rv = new DataView(rec.buffer);
    cdSize = Number(rv.getBigUint64(40, true));
    cdOffset = Number(rv.getBigUint64(48, true));
  }
  const cd = await range(url, cdOffset, cdOffset + cdSize - 1);
  const cv = new DataView(cd.buffer);
  const out: ZipEntry[] = [];
  for (let p = 0; p + 46 <= cd.length && cv.getUint32(p, true) === 0x02014b50; ) {
    const method = cv.getUint16(p + 10, true);
    let compressed = cv.getUint32(p + 20, true);
    let size = cv.getUint32(p + 24, true);
    const nameLen = cv.getUint16(p + 28, true);
    const extraLen = cv.getUint16(p + 30, true);
    const commentLen = cv.getUint16(p + 32, true);
    let offset = cv.getUint32(p + 42, true);
    const name = new TextDecoder().decode(cd.subarray(p + 46, p + 46 + nameLen));
    // ZIP64 extra field carries the real sizes and offset when the 32-bit ones are maxed out
    for (let e = p + 46 + nameLen; e < p + 46 + nameLen + extraLen; ) {
      const id = cv.getUint16(e, true);
      const len = cv.getUint16(e + 2, true);
      if (id === 1) {
        let q = e + 4;
        if (size === 0xffffffff) (size = Number(cv.getBigUint64(q, true))), (q += 8);
        if (compressed === 0xffffffff) (compressed = Number(cv.getBigUint64(q, true))), (q += 8);
        if (offset === 0xffffffff) offset = Number(cv.getBigUint64(q, true));
      }
      e += 4 + len;
    }
    out.push({ name, offset, compressed, size, method });
    p += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}

/** Download one entry out of a remote zip. */
export async function zipEntry(url: string, entry: ZipEntry) {
  const local = await range(url, entry.offset, entry.offset + 29);
  const lv = new DataView(local.buffer);
  const start = entry.offset + 30 + lv.getUint16(26, true) + lv.getUint16(28, true);
  const data = await range(url, start, start + entry.compressed - 1);
  if (entry.method === 0) return data;
  if (entry.method === 8) return new Uint8Array(inflateRawSync(data));
  throw new Error(`${entry.name}: unsupported zip method ${entry.method}`);
}
