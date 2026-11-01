# Dye masks: which parts of an asset take the primary, secondary and accent dye colours.
#   1. analyze: cluster the painted albedo per face (k-means) and write <in>.dye-clusters.png, a UV-space map of
#      the clusters, plus each cluster's colour and share. Look at it next to the texture or a render.
#   2. write: map clusters to channels and write <in>.dye.png (R primary, G secondary, B accent, black undyed).
#   bun run art:forge dye --in <asset.glb> --mode analyze [--k 6]
#   bun run art:forge dye --in <asset.glb> --mode write --k 6 --channels {"0": "primary", "3": "secondary", "5": "accent"}
#     [--size 1024]
# Same --k gives the same clusters (fixed seed), so analyze then write is repeatable.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, done, fail, load, path, reset  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

a = args()
reset()
meshes = [o for o in load(a["in"]) if o.type == "MESH"]
k = int(a.get("k", 6))
size = int(a.get("size", 1024))
base = Path(path(a["in"])).with_suffix("")


def albedo(material):
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            link = next(iter(node.inputs["Base Color"].links), None)
            n = link.from_node if link else None
            while n and n.type != "TEX_IMAGE" and n.inputs and n.inputs[0].links:
                n = n.inputs[0].links[0].from_node
            return n.image if n and n.type == "TEX_IMAGE" else None
    return None


# Per-triangle UVs and albedo samples (mean of the 3 corners and the centre)
tri_uv, tri_rgb = [], []
for m in meshes:
    m.data.calc_loop_triangles()
    uv = m.data.uv_layers[0].data
    images = {}
    for t in m.data.loop_triangles:
        mat = m.data.materials[t.material_index] if m.data.materials else None
        if mat not in images:
            img = albedo(mat)
            images[mat] = (np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], -1)[..., :3], img.size) if img else None
        corners = np.array([uv[li].uv[:] for li in t.loops], dtype=np.float32)
        tri_uv.append(corners)
        data = images[mat]
        if data is None:
            col = np.array(mat.diffuse_color[:3] if mat else (0.8, 0.8, 0.8), dtype=np.float32)
        else:
            px, (w, h) = data
            pts = np.vstack([corners, corners.mean(0)]) % 1.0
            col = px[(pts[:, 1] * (h - 1)).astype(int), (pts[:, 0] * (w - 1)).astype(int)].mean(0)
        tri_rgb.append(col)
if not tri_uv:
    fail("no triangles")
tri_uv = np.array(tri_uv)
tri_rgb = np.array(tri_rgb)

# k-means with a fixed seed, k-means++ start
rng = np.random.default_rng(7)
centres = [tri_rgb[rng.integers(len(tri_rgb))]]
for _ in range(1, k):
    d = np.min([((tri_rgb - c) ** 2).sum(1) for c in centres], axis=0)
    centres.append(tri_rgb[rng.choice(len(tri_rgb), p=d / d.sum())])
centres = np.array(centres)
for _ in range(30):
    label = ((tri_rgb[:, None, :] - centres[None]) ** 2).sum(2).argmin(1)
    centres = np.array([tri_rgb[label == i].mean(0) if (label == i).any() else centres[i] for i in range(k)])
order = np.argsort(-np.bincount(label, minlength=k))  # cluster 0 is the largest
remap = np.empty(k, dtype=int)
remap[order] = np.arange(k)
label, centres = remap[label], centres[order]


def rasterise(colours: np.ndarray) -> np.ndarray:
    """Paint each triangle's colour into UV space, then grow islands by 4 px so seams don't bleed black."""
    img = np.zeros((size, size, 3), dtype=np.float32)
    filled = np.zeros((size, size), dtype=bool)
    for tri, col in zip(tri_uv * (size - 1), colours):
        lo = np.floor(tri.min(0)).astype(int).clip(0, size - 1)
        hi = np.ceil(tri.max(0)).astype(int).clip(0, size - 1)
        xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        p = np.stack([xs.ravel() + 0.5, ys.ravel() + 0.5], 1)
        a0, b0, c0 = tri
        v0, v1, v2 = c0 - a0, b0 - a0, p - a0
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-9:
            continue
        u = (v2[:, 0] * v1[1] - v1[0] * v2[:, 1]) / den
        v = (v0[0] * v2[:, 1] - v2[:, 0] * v0[1]) / den
        inside = (u >= -0.01) & (v >= -0.01) & (u + v <= 1.02)
        img[ys.ravel()[inside], xs.ravel()[inside]] = col
        filled[ys.ravel()[inside], xs.ravel()[inside]] = True
    for _ in range(4):
        grow = img.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            shifted = np.roll(np.roll(img, dy, 0), dx, 1)
            sf = np.roll(np.roll(filled, dy, 0), dx, 1)
            take = ~filled & sf
            grow[take] = shifted[take]
            filled = filled | take
        img = grow
    return img


def save(img: np.ndarray, file: Path):
    im = bpy.data.images.new(file.stem, size, size, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    rgba = np.concatenate([img, np.ones((size, size, 1), dtype=np.float32)], 2)
    im.pixels = rgba.ravel().tolist()
    im.filepath_raw = str(file)
    im.file_format = "PNG"
    im.save()
    return str(file)


hexes = ["#%02x%02x%02x" % tuple(int(x * 255) for x in np.clip(c, 0, 1)) for c in centres]
shares = np.bincount(label, minlength=k) / len(label)
if a.get("mode", "analyze") == "analyze":
    out = save(rasterise(centres[label]), Path(f"{base}.dye-clusters.png"))
    done(clusters=[{"id": i, "colour": hexes[i], "share": round(float(shares[i]), 3)} for i in range(k)], preview=out,
         next="map clusters to channels and rerun with --mode write --channels")
else:
    channel = {"primary": (1, 0, 0), "secondary": (0, 1, 0), "accent": (0, 0, 1)}
    table = np.zeros((k, 3), dtype=np.float32)
    for cid, ch in a.get("channels", {}).items():
        if ch not in channel:
            fail(f"unknown channel {ch}")
        table[int(cid)] = channel[ch]
    out = save(rasterise(table[label]), Path(f"{base}.dye.png"))
    done(mask=out, channels={ch: [i for i in range(k) if tuple(table[i]) == v] for ch, v in channel.items()})
