"""Nature asset kit for demos/roam, built procedurally in headless Blender.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/kit/nature.py

Writes art/models/environment/kit/nature-*.glb, nature.json and nature-sheet.png.
Blender is Z-up while building; the glTF exporter converts to Y-up.
"""

import bpy
import bmesh
import json
import math
import os
import random
from mathutils import Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "models", "environment", "kit")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- colour

def hexc(h):
    h = h.lstrip("#")
    s = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return Vector([c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in s])


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return a.lerp(b, t)


MOSS = hexc("#4F7A3A")
MOSS_LIGHT = hexc("#7FA34A")
MOSS_DARK = hexc("#2F4F26")
GOLD = hexc("#E3B45A")
TEAL = hexc("#2FC4B2")
DEEP_TEAL = hexc("#0E5A57")
PARCH = hexc("#F3ECD9")
TERRA = hexc("#C7643A")
STONE = hexc("#B4AA96")
STONE_DARK = hexc("#7D776D")
BARK = hexc("#7A5638")
BARK_DARK = hexc("#4A3324")
BARK_LIGHT = hexc("#A07650")


# ---------------------------------------------------------------- geometry accumulation

class Part:
    """Vertex/face soup for one material; colours are per vertex, optionally per face."""

    def __init__(self, smooth=False):
        self.v, self.c, self.f, self.fc = [], [], [], []
        self.smooth = smooth

    def vert(self, p, col):
        self.v.append(Vector(p))
        self.c.append(Vector(col))
        return len(self.v) - 1

    def face(self, idx, col=None):
        self.f.append(tuple(idx))
        self.fc.append(col)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


class Asset:
    def __init__(self, id, **meta):
        self.id = id
        self.meta = meta
        self.parts = {"Kit": Part(), "Kit_Foliage": Part(smooth=False), "Kit_Glow": Part(smooth=True)}

    def __getitem__(self, k):
        return self.parts[k]


def frames(pts):
    """Parallel-transport frames along a polyline."""
    n = len(pts)
    tans = []
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tans.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (ref - tans[0] * ref.dot(tans[0])).normalized()
    out = []
    for t in tans:
        nrm = (nrm - t * nrm.dot(t)).normalized()
        out.append((t, nrm, t.cross(nrm)))
    return out


def tube(part, pts, radii, sides, colfn, gnarl=0.0, seed=0.0, cap=True, flutes=0, flute_amp=0.0):
    """Tapered tube; colfn(u, dir, pos) -> colour where u runs 0..1 along the tube."""
    fr = frames(pts)
    rings = []
    n = len(pts)
    for i, (p, (t, nm, bn)) in enumerate(zip(pts, fr)):
        ring = []
        u = i / (n - 1)
        for k in range(sides):
            a = 2 * math.pi * k / sides + u * 1.3
            d = nm * math.cos(a) + bn * math.sin(a)
            r = radii[i]
            if gnarl:
                r *= 1 + gnarl * noise.noise(p * 0.9 + d * 0.6 + Vector((seed, seed * 0.7, 0)))
            if flutes:
                r *= 1 + flute_amp * max(0.0, math.cos(a * flutes)) * (1 - u) ** 2
            q = p + d * r
            ring.append(part.vert(q, colfn(u, d, q)))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            part.face((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    if cap:
        tip = pts[-1] + fr[-1][0] * radii[-1] * 0.6
        c = part.vert(tip, colfn(1.0, fr[-1][0], tip))
        for k in range(sides):
            part.face((rings[-1][k], rings[-1][(k + 1) % sides], c))
    return rings


def curve(p0, p1, p2, p3, steps):
    out = []
    for i in range(steps + 1):
        t = i / steps
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return out


def blob(part, center, scale, subdiv, colfn, lump=0.18, seed=0.0, smooth_out=False):
    """Lumpy squashed icosphere; colfn(normal, pos, center) -> colour."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    center = Vector(center)
    idx = {}
    for v in bm.verts:
        n = v.co.normalized()
        s = 1 + lump * noise.noise(n * 1.7 + Vector((seed, seed * 1.3, seed * 0.4)))
        p = center + Vector((n.x * scale[0], n.y * scale[1], n.z * scale[2])) * s
        idx[v.index] = part.vert(p, colfn(n, p, center))
    for f in bm.faces:
        part.face([idx[v.index] for v in f.verts])
    bm.free()


def hull_rock(part, pts, colfn, bevel=0.06):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(6), verts=bm.verts[:], edges=bm.edges[:])
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1,
                        affect="EDGES", profile=0.5, clamp_overlap=True)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    base = len(part.v)
    for v in bm.verts:
        part.vert(v.co, STONE)
    for f in bm.faces:
        c = f.calc_center_median()
        part.face([base + v.index for v in f.verts], colfn(f.normal, c))
    bm.free()


# ---------------------------------------------------------------- colour functions

def bark_col(seed=0.0, moss_base=0.6):
    def fn(u, d, q):
        n = noise.noise(q * 1.4 + Vector((seed, 0, 0)))
        c = mix(BARK_DARK, BARK, 0.45 + 0.5 * n + 0.4 * u)
        if d.z > 0.2 or q.z < moss_base:
            m = max(d.z * 0.9, (moss_base - q.z) / max(moss_base, 0.01))
            c = mix(c, MOSS, m * (0.6 + 0.4 * n))
        return c
    return fn


def leaf_col(gold=0.5, seed=0.0, base=MOSS):
    def fn(n, p, c):
        k = noise.noise(p * 0.8 + Vector((seed, 0, 0)))
        col = mix(MOSS_DARK, base, 0.55 + 0.45 * n.z + 0.2 * k)
        col = mix(col, MOSS_LIGHT, max(0.0, n.z) * 0.7 + 0.15 * k)
        tip = max(0.0, n.z - 0.45) / 0.55
        return mix(col, GOLD, tip * gold * (0.7 + 0.3 * k))
    return fn


def stone_col(seed=0.0, moss=0.62):
    def fn(nrm, c):
        k = noise.noise(c * 1.1 + Vector((seed, seed, 0)))
        col = mix(STONE_DARK, STONE, 0.55 + 0.35 * k + 0.25 * nrm.z)
        col = mix(col, PARCH, max(0.0, k) * 0.45)
        if nrm.z > moss - 0.35 * k:
            col = mix(MOSS_DARK, MOSS, 0.45 + 0.45 * k)
        return col
    return fn


# ---------------------------------------------------------------- assets

def rock_points(rng, sx, sy, sz, n, sink=0.25, taper=0.0):
    pts = []
    for _ in range(n):
        th = rng.uniform(0, 2 * math.pi)
        z = rng.uniform(-1, 1)
        r = math.sqrt(1 - z * z)
        k = rng.uniform(0.8, 1.0)
        w = 1 - taper * (z + 1) / 2
        p = Vector((r * math.cos(th) * sx * k * w, r * math.sin(th) * sy * k * w, (z + 1) / 2 * sz * k))
        p.z -= sink
        pts.append(p)
    return pts


def make_boulder_a():
    a = Asset("nature-rock-boulder-a", category="rock", biomes=["roothold", "forest", "meadow"],
              minScale=0.6, maxScale=1.8, collide=True)
    rng = random.Random(11)
    hull_rock(a["Kit"], rock_points(rng, 1.3, 1.05, 1.5, 26), stone_col(1.0), 0.09)
    return a


def make_boulder_b():
    a = Asset("nature-rock-boulder-b", category="rock", biomes=["roothold", "forest", "meadow"],
              minScale=0.6, maxScale=1.6, collide=True)
    rng = random.Random(23)
    for (ox, oy, s, h) in [(0, 0, 1.0, 1.25), (1.05, 0.35, 0.6, 0.75), (-0.45, 0.85, 0.45, 0.5)]:
        pts = [p * s + Vector((ox, oy, 0)) for p in rock_points(rng, 1.1, 0.95, h / s, 20, 0.2 / s)]
        hull_rock(a["Kit"], pts, stone_col(ox * 3 + 2), 0.07 * s)
    return a


def make_slab():
    a = Asset("nature-rock-slab", category="rock", biomes=["roothold", "meadow"],
              minScale=0.7, maxScale=1.6, collide=True)
    rng = random.Random(5)
    pts = rock_points(rng, 2.0, 1.3, 0.75, 28, 0.25)
    for p in pts:
        p.z += p.x * 0.12
    hull_rock(a["Kit"], pts, stone_col(4.0, 0.9), 0.08)
    return a


def make_spire():
    a = Asset("nature-rock-spire", category="rock", biomes=["roothold", "forest"],
              minScale=0.7, maxScale=1.5, collide=True)
    rng = random.Random(9)
    pts = rock_points(rng, 0.85, 0.75, 4.2, 26, 0.3, taper=0.75)
    for p in pts:
        p.x += 0.06 * p.z * p.z / 4
    hull_rock(a["Kit"], pts, stone_col(7.0, 0.5), 0.07)
    # a fallen shard at the foot
    pts = [p * 0.4 + Vector((0.9, -0.5, 0)) for p in rock_points(rng, 1.0, 0.8, 1.0, 14, 0.4)]
    hull_rock(a["Kit"], pts, stone_col(8.0), 0.04)
    return a


def oak(a, seed, height, lean, canopy_n, spread, gold):
    rng = random.Random(seed)
    trunk = a["Kit"]
    ang = rng.uniform(0, math.tau)
    lx, ly = math.cos(ang) * lean, math.sin(ang) * lean
    pts = []
    for i in range(10):
        u = i / 9
        z = -0.2 + u * height * 0.72
        w = 0.25 * math.sin(u * 3.2 + seed)
        pts.append(Vector((lx * u * u + w * math.cos(ang + 1.6), ly * u * u + w * math.sin(ang + 1.6), z)))
    radii = [0.42 * (1 - 0.62 * (i / 9)) + (0.18 if i == 0 else 0.0) for i in range(10)]
    tube(trunk, pts, radii, 9, bark_col(seed, 0.5), gnarl=0.22, seed=seed, flutes=4, flute_amp=0.45)
    top = pts[-1]
    # limbs out to the canopy blobs
    centers = []
    for k in range(canopy_n):
        t = k / canopy_n * math.tau + rng.uniform(-0.3, 0.3)
        r = spread * rng.uniform(0.45, 1.0) if k else 0.0
        c = Vector((top.x + math.cos(t) * r, top.y + math.sin(t) * r,
                    height * rng.uniform(0.72, 0.9) + (0.5 if k == 0 else 0)))
        centers.append(c)
        if k and k <= 4:
            start = pts[6 + k % 3]
            lim = curve(start, start.lerp(c, 0.4) + Vector((0, 0, 0.3)), c.lerp(start, 0.25), c, 4)
            tube(trunk, lim, [0.16 - 0.025 * j for j in range(5)], 6, bark_col(seed + k, -1), gnarl=0.15,
                 seed=seed + k)
    for k, c in enumerate(centers):
        s = rng.uniform(0.95, 1.35) * (1.3 if k == 0 else 1.0) * spread * 0.62
        blob(a["Kit_Foliage"], c, (s * 1.1, s, s * 0.72), 3, leaf_col(gold, seed + k), 0.22, seed + k * 3)
    return a


def make_oak_a():
    a = Asset("nature-tree-oak-a", category="tree", biomes=["roothold", "forest", "meadow"],
              minScale=0.75, maxScale=1.35, collide=True, collideRadius=0.5)
    return oak(a, 3, 6.0, 0.6, 7, 2.2, 0.6)


def make_oak_b():
    a = Asset("nature-tree-oak-b", category="tree", biomes=["roothold", "forest", "meadow"],
              minScale=0.75, maxScale=1.35, collide=True, collideRadius=0.45)
    return oak(a, 17, 4.8, 1.1, 5, 1.8, 0.9)


def make_pine():
    a = Asset("nature-tree-pine", category="tree", biomes=["forest", "roothold"],
              minScale=0.7, maxScale=1.5, collide=True, collideRadius=0.35)
    pts = [Vector((0.04 * math.sin(i), 0, -0.2 + i * 0.75)) for i in range(9)]
    tube(a["Kit"], pts, [0.3 * (1 - i / 10) + (0.08 if i == 0 else 0) for i in range(9)], 7,
         bark_col(2.0, 0.4), gnarl=0.15, seed=2.0, flutes=3, flute_amp=0.3)
    f = a["Kit_Foliage"]
    tiers = 5
    sides = 11
    for t in range(tiers):
        u = t / (tiers - 1)
        z0 = 1.3 + t * 1.05
        r = 2.0 * (1 - 0.72 * u)
        h = 1.9 - 0.6 * u
        rot = t * 0.37
        top = f.vert((0, 0, z0 + h), mix(MOSS_LIGHT, GOLD, 0.35 + 0.4 * u))
        ring, inner = [], []
        for k in range(sides):
            a_ = rot + k / sides * math.tau
            jag = 1.0 if k % 2 == 0 else 0.78
            droop = -0.25 if k % 2 == 0 else 0.05
            p = Vector((math.cos(a_) * r * jag, math.sin(a_) * r * jag, z0 + droop))
            col = mix(hexc("#2E5A34"), MOSS, 0.4 + 0.4 * u + 0.2 * noise.noise(p))
            ring.append(f.vert(p, col))
            inner.append(f.vert((p.x * 0.55, p.y * 0.55, z0 + 0.2), MOSS_DARK))
        for k in range(sides):
            k2 = (k + 1) % sides
            f.face((ring[k], ring[k2], top))
            f.face((inner[k2], ring[k2], ring[k], inner[k]))
        c = f.vert((0, 0, z0 + 0.35), MOSS_DARK)
        for k in range(sides):
            f.face((inner[(k + 1) % sides], inner[k], c))
    return a


def make_ancient():
    a = Asset("nature-ancient-tree", category="landmark", biomes=["roothold"],
              minScale=0.9, maxScale=1.15, collide=True, collideRadius=2.6)
    rng = random.Random(42)
    K = a["Kit"]
    H = 17.5
    # main trunk: thick, fluted, twisting
    pts = []
    for i in range(16):
        u = i / 15
        z = -0.3 + u * 9.5
        pts.append(Vector((0.6 * math.sin(u * 2.4), 0.5 * math.sin(u * 3.1 + 1), z)))
    radii = [2.3 * (1 - 0.5 * u) + 1.1 * (1 - u) ** 6 for u in (i / 15 for i in range(16))]
    tube(K, pts, radii, 18, bark_col(1.0, 1.4), gnarl=0.2, seed=1.0, cap=False, flutes=6, flute_amp=0.35)
    top = pts[-1]
    # major limbs splaying from the crown
    crown = []
    for k in range(5):
        t = k / 5 * math.tau + 0.4
        end = top + Vector((math.cos(t) * rng.uniform(4.5, 6.5), math.sin(t) * rng.uniform(4.5, 6.5),
                            rng.uniform(3.5, 6.0)))
        start = top + Vector((math.cos(t) * 0.5, math.sin(t) * 0.5, -0.8))
        lim = curve(start, start + Vector((math.cos(t) * 1.0, math.sin(t) * 1.0, 2.5)),
                    end - Vector((math.cos(t) * 2.0, math.sin(t) * 2.0, 0.6)), end, 10)
        tube(K, lim, [1.25 * (1 - 0.7 * j / 10) for j in range(11)], 10, bark_col(k + 3.0, -1),
             gnarl=0.2, seed=k * 2.0)
        crown.append(end)
        # secondary twig
        mid = lim[6]
        e2 = mid + Vector((math.cos(t + 0.9) * 2.5, math.sin(t + 0.9) * 2.5, 2.2))
        tube(K, curve(mid, mid.lerp(e2, 0.3) + Vector((0, 0, 0.8)), e2.lerp(mid, 0.2), e2, 4),
             [0.45 - 0.07 * j for j in range(5)], 7, bark_col(k + 9.0, -1), gnarl=0.15, seed=k + 9.0)
        crown.append(e2)
    # buttress roots
    for k in range(8):
        t = k / 8 * math.tau + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(t), math.sin(t), 0))
        reach = rng.uniform(5.0, 7.5)
        start = Vector((0, 0, rng.uniform(1.8, 3.0))) + d * 0.9
        end = d * reach + Vector((0, 0, -0.5))
        rp = curve(start, start + d * 1.6 + Vector((0, 0, 0.2)), d * (reach * 0.65) + Vector((0, 0, 0.5)), end, 10)
        tube(K, rp, [1.05 * (1 - 0.8 * j / 10) + 0.05 for j in range(11)], 9, bark_col(k + 20.0, 1.0),
             gnarl=0.25, seed=k + 20.0)
    # canopy: broad layered crown
    F = a["Kit_Foliage"]
    for k, c in enumerate(crown):
        s = rng.uniform(3.0, 4.0) if k % 2 == 0 else rng.uniform(2.2, 3.0)
        blob(F, c + Vector((0, 0, 0.6)), (s * 1.15, s * 1.15, s * 0.62), 3, leaf_col(0.7, k * 1.7), 0.22, k * 2.1)
    for k in range(4):
        t = k / 4 * math.tau + 1.0
        c = top + Vector((math.cos(t) * 2.5, math.sin(t) * 2.5, 7.0 + k * 0.3))
        blob(F, c, (4.0, 4.0, 2.4), 3, leaf_col(0.8, k + 40.0), 0.2, k + 40.0)
    # teal glow: hanging lantern pods under the canopy and shelf fungus on the trunk
    G = a["Kit_Glow"]
    for k in range(7):
        c = crown[k % len(crown)].lerp(top, 0.25) - Vector((0, 0, 1.8 + 0.4 * (k % 3)))
        blob(G, c, (0.32, 0.32, 0.5), 1, lambda n, p, cc: mix(TEAL, PARCH, max(0.0, -n.z) * 0.4), 0.1, k)
        tube(K, [c + Vector((0, 0, 0.4)), c + Vector((0, 0, 1.6))], [0.05, 0.05], 4,
             lambda u, d, q: BARK_DARK, cap=False)
    for k in range(5):
        t = k * 1.3 + 0.5
        z = 2.5 + k * 1.2
        r = 2.3 * (1 - 0.5 * (z + 0.3) / 9.5) + 0.1
        c = Vector((math.cos(t) * r + 0.6 * math.sin(z / 9.5 * 2.4), math.sin(t) * r, z))
        blob(G, c, (0.6, 0.6, 0.16), 1, lambda n, p, cc: mix(TEAL, DEEP_TEAL, max(0.0, -n.z)), 0.1, k + 70)
    return a


def make_root_arch():
    a = Asset("nature-root-arch", category="landmark", biomes=["roothold"],
              minScale=0.8, maxScale=1.4, collide=True, collideRadius=0.7)
    K = a["Kit"]
    pts = curve(Vector((-3.4, 0, -0.5)), Vector((-2.8, 0.3, 3.6)), Vector((2.4, -0.4, 3.9)),
                Vector((3.2, 0.2, -0.5)), 18)
    radii = [0.85 - 0.35 * (i / 18) + 0.3 * max(0.0, 1 - i / 3) for i in range(19)]
    tube(K, pts, radii, 11, bark_col(5.0, 0.8), gnarl=0.25, seed=5.0, cap=False, flutes=3, flute_amp=0.3)
    # rootlets diving into the ground at both feet
    for (o, d) in [(Vector((-3.0, 0, 0.8)), Vector((-1.3, 0.9, -1.1))), (Vector((-2.9, 0, 1.4)), Vector((-0.6, -1.4, -1.6))),
                   (Vector((3.0, 0, 0.6)), Vector((1.1, -0.9, -1.0)))]:
        e = o + d
        tube(K, curve(o, o + d * 0.4 + Vector((0, 0, 0.3)), e - Vector((0, 0, -0.2)), e - Vector((0, 0, 0.3)), 5),
             [0.3 - 0.04 * j for j in range(6)], 6, bark_col(o.y + 7, 0.8), gnarl=0.2, seed=o.x)
    # moss pads and glowing nubs on the crest
    F = a["Kit_Foliage"]
    for k, i in enumerate((6, 9, 12)):
        blob(F, pts[i] + Vector((0, 0, radii[i] * 0.7)), (0.8, 0.6, 0.3), 1, leaf_col(0.4, k), 0.2, k)
    G = a["Kit_Glow"]
    for k, i in enumerate((4, 8, 11, 15)):
        side = Vector((0, 1 if k % 2 else -1, 0))
        blob(G, pts[i] + side * radii[i] * 0.95, (0.22, 0.22, 0.12), 1, lambda n, p, c: TEAL, 0.1, k)
    return a


def bush(a, seed, n, size, flowers):
    rng = random.Random(seed)
    F = a["Kit_Foliage"]
    for k in range(n):
        t = k / n * math.tau
        r = size * 0.55 if k else 0.0
        s = size * rng.uniform(0.55, 0.75) * (1.25 if k == 0 else 1.0)
        c = Vector((math.cos(t) * r, math.sin(t) * r, s * 0.55 + (size * 0.25 if k == 0 else 0)))
        blob(F, c, (s, s, s * 0.8), 2, leaf_col(0.55, seed + k), 0.2, seed + k)
    if flowers:
        for k in range(flowers):
            t = rng.uniform(0, math.tau)
            z = rng.uniform(0.3, 0.9)
            r = size * (0.95 - 0.3 * z)
            c = Vector((math.cos(t) * r, math.sin(t) * r, size * 0.3 + z * size * 0.75))
            col = TERRA if k % 2 else GOLD
            blob(F, c, (0.09, 0.09, 0.07), 1, lambda n_, p, cc, col=col: mix(col, PARCH, max(0.0, n_.z) * 0.3), 0.05, k)
    return a


def make_bush_a():
    a = Asset("nature-bush-a", category="bush", biomes=["roothold", "forest", "meadow"],
              minScale=0.7, maxScale=1.5, collide=False)
    return bush(a, 31, 5, 0.8, 0)


def make_bush_b():
    a = Asset("nature-bush-b", category="bush", biomes=["meadow", "roothold"],
              minScale=0.7, maxScale=1.4, collide=False)
    return bush(a, 47, 3, 0.65, 5)


def blade(part, base, direction, length, width, bend, col_base, col_tip, segs=3):
    up = Vector((0, 0, 1))
    side = up.cross(direction).normalized() if direction.length > 0.01 else Vector((1, 0, 0))
    prev = None
    for i in range(segs + 1):
        u = i / segs
        p = base + direction * (length * u * 0.6) + up * (length * math.sin(u * 1.2) * 0.95) \
            + direction * (bend * u * u)
        w = width * (1 - u) ** 0.8
        col = mix(col_base, col_tip, u)
        if i == segs:
            tip = part.vert(p, col)
            part.face((prev[0], prev[1], tip))
        else:
            l = part.vert(p - side * w, col)
            r = part.vert(p + side * w, col)
            if prev:
                part.face((prev[0], prev[1], r, l))
            prev = (l, r)


def make_grass():
    a = Asset("nature-grass-tuft", category="ground", biomes=["meadow", "roothold", "forest"],
              minScale=0.7, maxScale=1.6, collide=False)
    rng = random.Random(3)
    F = a["Kit_Foliage"]
    for k in range(16):
        t = rng.uniform(0, math.tau)
        r = rng.uniform(0, 0.12)
        d = Vector((math.cos(t), math.sin(t), 0))
        base = d * r - Vector((0, 0, 0.03))
        tip = GOLD if k % 4 == 0 else MOSS_LIGHT
        blade(F, base, d, rng.uniform(0.35, 0.6), 0.035, rng.uniform(0.05, 0.18), MOSS_DARK, tip)
    return a


def make_fern():
    a = Asset("nature-fern", category="ground", biomes=["roothold", "forest"],
              minScale=0.7, maxScale=1.5, collide=False)
    rng = random.Random(8)
    F = a["Kit_Foliage"]
    n = 8
    for k in range(n):
        t = k / n * math.tau + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(t), math.sin(t), 0))
        side = Vector((0, 0, 1)).cross(d)
        L = rng.uniform(0.75, 1.0)
        rise = rng.uniform(0.45, 0.65)
        spine = [d * (L * u) + Vector((0, 0, rise * math.sin(u * 2.4) * (1 - 0.35 * u))) for u in
                 (i / 8 for i in range(9))]
        for i in range(1, 8):
            u = i / 8
            w = 0.2 * math.sin(u * math.pi) + 0.02
            col = mix(MOSS, MOSS_LIGHT, u)
            col = mix(col, GOLD, max(0.0, u - 0.7) * 1.5)
            for s in (-1, 1):
                p0 = F.vert(spine[i - 1], MOSS_DARK)
                p1 = F.vert(spine[i + 1], col)
                p2 = F.vert(spine[i] + side * s * w + d * 0.05 - Vector((0, 0, 0.06)), col)
                F.face((p0, p2, p1) if s > 0 else (p0, p1, p2))
        # spine strip
        prev = None
        for i, p in enumerate(spine):
            l = F.vert(p - side * 0.015, MOSS_DARK)
            r = F.vert(p + side * 0.015, MOSS_DARK)
            if prev:
                F.face((prev[0], prev[1], r, l))
            prev = (l, r)
    return a


def make_mushrooms():
    a = Asset("nature-mushroom-cluster", category="ground", biomes=["roothold", "forest"],
              minScale=0.7, maxScale=1.8, collide=False)
    rng = random.Random(14)
    K, G = a["Kit"], a["Kit_Glow"]
    specs = [(0, 0, 0.55, 0.26), (0.28, 0.12, 0.36, 0.17), (-0.2, 0.22, 0.28, 0.13),
             (0.08, -0.3, 0.22, 0.11), (-0.3, -0.15, 0.4, 0.19), (0.42, -0.2, 0.15, 0.08)]
    for (x, y, h, r) in specs:
        lean = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0))
        stem = curve(Vector((x, y, -0.05)), Vector((x, y, h * 0.4)), Vector((x, y, h * 0.7)) + lean,
                     Vector((x, y, h)) + lean, 3)
        tube(K, stem, [r * 0.42, r * 0.33, r * 0.3, r * 0.28], 6,
             lambda u, d, q: mix(PARCH, hexc("#CFC2A0"), 1 - u), cap=False)
        top = stem[-1]
        sides = 10
        ring = []
        for k in range(sides):
            ang = k / sides * math.tau
            ring.append([])
            for j, (rr, zz) in enumerate([(1.0, -0.1), (0.85, 0.35), (0.5, 0.62)]):
                p = top + Vector((math.cos(ang) * r * rr, math.sin(ang) * r * rr, r * zz))
                col = mix(TEAL, hexc("#8FF0E2"), j / 2)
                ring[-1].append(G.vert(p, col))
        apex = G.vert(top + Vector((0, 0, r * 0.75)), hexc("#B8F7EE"))
        under = G.vert(top + Vector((0, 0, -0.02)), DEEP_TEAL)
        for k in range(sides):
            k2 = (k + 1) % sides
            for j in range(2):
                G.face((ring[k][j], ring[k2][j], ring[k2][j + 1], ring[k][j + 1]))
            G.face((ring[k][2], ring[k2][2], apex))
            G.face((ring[k2][0], ring[k][0], under))
    return a


BUILDERS = [make_boulder_a, make_boulder_b, make_slab, make_spire, make_oak_a, make_oak_b, make_pine,
            make_ancient, make_root_arch, make_bush_a, make_bush_b, make_grass, make_fern, make_mushrooms]


# ---------------------------------------------------------------- blender plumbing

def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    if name == "Kit_Glow":
        bsdf.inputs["Emission Color"].default_value = (*TEAL, 1)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return m


def to_objects(asset):
    objs = []
    for mat, part in asset.parts.items():
        if not part.f:
            continue
        suffix = {"Kit": "", "Kit_Foliage": "_foliage", "Kit_Glow": "_glow"}[mat]
        me = bpy.data.meshes.new(asset.id + suffix)
        me.from_pydata([tuple(v) for v in part.v], [], part.f)
        me.validate()
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        for poly, fc in zip(me.polygons, part.fc):
            poly.use_smooth = part.smooth
            for li in poly.loop_indices:
                c = fc if fc is not None else part.c[me.loops[li].vertex_index]
                ca.data[li].color = (c[0], c[1], c[2], 1.0)
        me.materials.append(material(mat))
        ob = bpy.data.objects.new(asset.id + suffix, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    return objs


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
              export_texcoords=False, export_normals=True, export_materials="EXPORT",
              export_vertex_color="ACTIVE", export_all_vertex_colors=False, export_active_vertex_color_when_no_material=True,
              export_extras=False, export_cameras=False, export_lights=False, export_animations=False)
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})


def bounds(asset):
    vs = [v for p in asset.parts.values() for v in p.v]
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    zs = [v.z for v in vs]
    radius = max(max(abs(x) for x in xs), max(abs(y) for y in ys))
    return radius, max(zs)


def render_sheet(placed):
    sc = bpy.context.scene
    cols = 5
    cell = 4.2
    for i, (asset, objs) in enumerate(placed):
        r, h = bounds(asset)
        s = 3.2 / max(h, 2 * r * 0.85)
        cx = (i % cols - (cols - 1) / 2) * cell
        cz = -(i // cols) * cell
        for o in objs:
            o.scale = (s, s, s)
            o.rotation_euler = (0, 0, math.radians(35))
            o.location = (cx, 0, cz)
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.8, depth=0.08, location=(cx, 0, cz - 0.04))
        disc = bpy.context.active_object
        dm = bpy.data.materials.new("disc")
        dm.use_nodes = True
        dm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hexc("#8C9A6A"), 1)
        disc.data.materials.append(dm)
        cu = bpy.data.curves.new(asset.id, "FONT")
        cu.body = asset.id.replace("nature-", "")
        cu.size = 0.28
        cu.align_x = "CENTER"
        tx = bpy.data.objects.new(asset.id + "_label", cu)
        sc.collection.objects.link(tx)
        tx.location = (cx, -1.9, cz - 0.55)
        tx.rotation_euler = (math.radians(70), 0, 0)
        tm = bpy.data.materials.new("label")
        tm.use_nodes = True
        tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.03, 0.03, 1)
        cu.materials.append(tm)

    rows = (len(placed) + cols - 1) // cols
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = cols * cell + 0.6
    elev = math.radians(18)
    mid_z = -(rows - 1) * cell / 2 + 1.4
    cam.location = (0, -40 * math.cos(elev), mid_z + 40 * math.sin(elev))
    cam.rotation_euler = (math.radians(90) - elev, 0, 0)
    sc.camera = cam

    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    key.data.energy = 4.0
    key.data.color = (1.0, 0.88, 0.7)
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(50), 0, math.radians(-40))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 1.3
    fill.data.color = (0.45, 0.85, 0.85)
    fill.rotation_euler = (math.radians(60), 0, math.radians(150))
    for l in (key, fill):
        sc.collection.objects.link(l)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.66, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.world = world

    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x = 2200
    sc.render.resolution_y = int(2200 * rows * cell / (cols * cell + 0.6)) + 120
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    try:
        sc.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    sc.render.filepath = os.path.join(OUT, "nature-sheet.png")
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    catalog, placed, report = [], [], []
    for build in BUILDERS:
        asset = build()
        objs = to_objects(asset)
        export(objs, os.path.join(OUT, asset.id + ".glb"))
        r, h = bounds(asset)
        entry = {"id": asset.id, "file": asset.id + ".glb", "category": asset.meta["category"],
                 "biomes": asset.meta["biomes"], "radius": round(r, 2), "height": round(h, 2),
                 "minScale": asset.meta["minScale"], "maxScale": asset.meta["maxScale"],
                 "collide": asset.meta["collide"]}
        if "collideRadius" in asset.meta:
            entry["collideRadius"] = asset.meta["collideRadius"]
        catalog.append(entry)
        tris = {m: p.tris() for m, p in asset.parts.items() if p.f}
        report.append((asset.id, sum(tris.values()), tris))
        placed.append((asset, objs))
    with open(os.path.join(OUT, "nature.json"), "w") as fh:
        json.dump(catalog, fh, indent=2)
        fh.write("\n")
    for row in report:
        print("TRIS", *row)
    render_sheet(placed)


main()
