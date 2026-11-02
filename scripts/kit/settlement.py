"""Rootholds settlement kit: Rootwarden huts, shrine, props and rope-bridge pieces.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/kit/settlement.py

Writes art/models/environment/kit/settle-*.glb, settlement.json and settle-sheet.png.
Every asset is built from lathes, tubes and noisy stones with flat per-face vertex
colour (COLOR_0); lighting comes from the engine, so nothing is baked but colour.
"""

import json
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "models", "environment", "kit")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- palette (sRGB)

def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

MOSS = hexc("#4F7A3A")
MOSS_LIGHT = hexc("#7FA34A")
GOLD = hexc("#E3B45A")
TEAL = hexc("#2FC4B2")
DEEP_TEAL = hexc("#0E5A57")
STONE = hexc("#E6DCC3")
STONE_WARM = hexc("#D4C3A0")
STONE_DARK = hexc("#A89A80")
TERRACOTTA = hexc("#C7643A")
TERRA_DARK = hexc("#9E4A2C")
PLASTER = hexc("#EFE3C6")
TIMBER = hexc("#6B4A31")
TIMBER_DARK = hexc("#4A3324")
WOOD = hexc("#9A6B43")
WOOD_LIGHT = hexc("#B9875A")
BARK = hexc("#6E5A45")
BARK_DARK = hexc("#4E4033")
STRAW = hexc("#D9B566")
STRAW_DARK = hexc("#A9853F")
ROPE = hexc("#C9A86E")
IRON = hexc("#4C4A48")
WATER = hexc("#1E7C78")


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shade(c, k):
    return tuple(max(0.0, min(1.0, v * k)) for v in c)


# ---------------------------------------------------------------- mesh builder

class Part:
    """Geometry accumulated per material; faces carry their own colour."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.cols = []

    def add(self, verts, faces, color_fn):
        base = len(self.verts)
        self.verts.extend(verts)
        for f in faces:
            self.faces.append([base + i for i in f])
            self.cols.append(color_fn(f, [verts[i] for i in f]))


class Asset:
    def __init__(self, name, seed):
        self.name = name
        self.parts = {"Kit": Part(), "Kit_Glow": Part(), "Kit_Foliage": Part()}
        self.rng = random.Random(seed)

    def jit(self, c, amt=0.07):
        k = 1 + self.rng.uniform(-amt, amt)
        return shade(c, k)

    def add(self, mat, verts, faces, color, jitter=0.06, grad=0.18, ground=0.0):
        """color: rgb or fn(face_idx, face_verts) -> rgb. Adds a gentle bottom darkening."""
        def fn(f, fv):
            c = color(f, fv) if callable(color) else color
            y = sum(v.y for v in fv) / len(fv)
            ao = 1 - grad * max(0.0, 1 - (y - ground) / 0.6)
            return shade(self.jit(c, jitter), ao)
        self.parts[mat].add([Vector(v) for v in verts], faces, fn)


def xf(verts, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    m = (Matrix.Translation(loc)
         @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X") @ Matrix.Rotation(rot[2], 4, "Z")
         @ Matrix.Diagonal((*scale, 1)))
    return [m @ Vector(v) for v in verts]


def lathe(profile, segs, center_fn=None, phase=0.0, cap_top=True, cap_bottom=True, wobble=0.0, seed=0):
    """profile: [(radius, y)] bottom→top. center_fn(t)->(dx,dz) bends the axis (roof curls)."""
    verts, faces = [], []
    n = len(profile)
    for i, (r, y) in enumerate(profile):
        t = i / max(1, n - 1)
        cx, cz = center_fn(t) if center_fn else (0, 0)
        for s in range(segs):
            a = phase + s / segs * math.tau
            w = 1 + wobble * noise.noise(Vector((math.cos(a) * 2, y * 1.3, math.sin(a) * 2 + seed)))
            verts.append((cx + math.cos(a) * r * w, y, cz + math.sin(a) * r * w))
    for i in range(n - 1):
        for s in range(segs):
            a, b = i * segs + s, i * segs + (s + 1) % segs
            faces.append((a, b, b + segs, a + segs)[::-1])
    if cap_bottom and profile[0][0] > 1e-4:
        faces.append(tuple(range(segs)))
    if cap_top and profile[-1][0] > 1e-4:
        faces.append(tuple(range((n - 1) * segs, n * segs))[::-1])
    return verts, faces


def box(sx, sy, sz, taper=1.0):
    """Box with its base at y=0; taper shrinks the top face."""
    hx, hz = sx / 2, sz / 2
    tx, tz = hx * taper, hz * taper
    v = [(-hx, 0, -hz), (hx, 0, -hz), (hx, 0, hz), (-hx, 0, hz),
         (-tx, sy, -tz), (tx, sy, -tz), (tx, sy, tz), (-tx, sy, tz)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return v, f


def tube(points, radii, segs=6, cap=True):
    verts, faces = [], []
    pts = [Vector(p) for p in points]
    up = Vector((0, 1, 0))
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = up if abs(d.dot(up)) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u).normalized()
        for s in range(segs):
            a = s / segs * math.tau
            verts.append(p + (u * math.cos(a) + w * math.sin(a)) * radii[i])
    for i in range(len(pts) - 1):
        for s in range(segs):
            a, b = i * segs + s, i * segs + (s + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    if cap:
        faces.append(tuple(range(segs))[::-1])
        faces.append(tuple(range((len(pts) - 1) * segs, len(pts) * segs)))
    return verts, faces


def stone(rx, ry, rz, subdiv=1, rough=0.22, seed=0, flat_bottom=True):
    """Noise-displaced icosphere, base at y=0."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    verts = []
    for v in bm.verts:
        p = v.co.copy()
        n = noise.noise(p * 1.7 + Vector((seed * 3.1, seed, -seed)))
        p *= 1 + rough * n
        p = Vector((p.x * rx, p.y * ry, p.z * rz))
        if flat_bottom:
            p.y = max(p.y, -ry * 0.55)
        verts.append(p)
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    miny = min(v.y for v in verts)
    return [(v.x, v.y - miny, v.z) for v in verts], faces


def disc(r, segs, depth=0.06):
    return lathe([(r, 0), (r, depth)], segs)


# ---------------------------------------------------------------- shared pieces

def stone_base(a, r0, h, segs=18, rings=5, seed=1):
    """Rounded fieldstone plinth: bulging rings, colour blotched per stone."""
    prof = []
    for i in range(rings + 1):
        t = i / rings
        r = r0 * (1.02 + 0.07 * math.sin(t * math.pi) - 0.08 * t)
        prof.append((r, h * t))
    prof.append((r0 * 0.86, h + 0.04))
    v, f = lathe(prof, segs, wobble=0.05, seed=seed)
    rng = random.Random(seed)
    stones = [rng.choice([STONE, STONE_WARM, STONE, STONE_DARK, PLASTER]) for _ in f]
    idx = {tuple(face): i for i, face in enumerate(f)}
    def col(face, fv):
        i = idx[tuple(face)]
        c = stones[i]
        if (i // segs) % 2 and rng.random() < 0.25:
            c = mix(c, MOSS, 0.45)
        return c
    a.add("Kit", v, f, col, jitter=0.05)


def roof_shingles(a, r_eave, y0, y1, bands, segs, curl, colors, lip=0.18):
    """Conical roof of stepped shingle bands; tip curls toward +x."""
    prof = []
    for b in range(bands):
        t0, t1 = b / bands, (b + 1) / bands
        r0 = r_eave * (1 - t0) ** 0.9
        r1 = r_eave * (1 - t1) ** 0.9
        ya, yb = y0 + (y1 - y0) * t0, y0 + (y1 - y0) * t1
        prof.append((r0 + lip * (1 - t0) * 0.5, ya - lip * 0.35))
        prof.append((r0, ya))
        prof.append((r1 + (r0 - r1) * 0.15, yb - 0.02))
    prof.append((0.06, y1 + 0.15))
    prof.append((0.0, y1 + 0.25))
    cf = lambda t: (curl * t ** 3, 0.0)
    v, f = lathe(prof, segs, center_fn=cf, cap_top=False, phase=0.13)
    # underside so the eave reads thick from below
    def col(face, fv):
        ring = min(face) // segs
        band = ring // 3
        c = colors[band % len(colors)]
        if ring % 3 == 0:
            c = shade(c, 0.72)  # lip shadow line
        s = (min(face) % segs)
        if s % 3 == 0:
            c = shade(c, 0.92)
        return c
    a.add("Kit", v, f, col, grad=0, jitter=0.08)


def timber_posts(a, r, y0, y1, count, phase=0.0, size=0.2):
    for i in range(count):
        ang = phase + i / count * math.tau
        v, f = box(size, y1 - y0, size, taper=0.9)
        v = xf(v, loc=(math.cos(ang) * r, y0, math.sin(ang) * r), rot=(0, -ang, 0))
        a.add("Kit", v, f, TIMBER_DARK if i % 2 else TIMBER)


def round_door(a, base_r, h_center, r, ang=math.pi / 2):
    """Round plank door with a stone ring frame, set into a curved wall facing angle ang."""
    # local frame: x right, y up, z out of the wall; then turned to face ang
    m = (Matrix.Translation((math.cos(ang) * base_r, h_center, math.sin(ang) * base_r))
         @ Matrix.Rotation(math.pi / 2 - ang, 4, "Y"))
    face_out = Matrix.Rotation(math.pi / 2, 4, "X")  # lathe axis y -> z
    v, f = lathe([(r, -0.25), (r, 0.06)], 16)
    v = [m @ face_out @ Vector(p) for p in v]
    a.add("Kit", v, f, lambda face, fv: WOOD if int((fv[0].x + fv[0].z + 9) * 3.5) % 2 else WOOD_LIGHT, jitter=0.04, grad=0)
    segs = 11
    for s in range(segs):
        t = -0.35 + (s + 0.5) / segs * (math.pi + 0.7)  # arch over the top, feet in the ground
        sv, sf = stone(0.19, 0.1, 0.15, subdiv=0, rough=0.12, seed=s)
        loc = Matrix.Translation((math.cos(t) * (r + 0.13), math.sin(t) * (r + 0.13), 0.02))
        sv = [m @ loc @ Matrix.Rotation(t - math.pi / 2, 4, "Z") @ face_out @ (Vector(p) - Vector((0, 0.05, 0))) for p in sv]
        a.add("Kit", sv, sf, STONE_WARM if s % 2 else STONE, jitter=0.06, grad=0)
    kv, kf = stone(0.06, 0.06, 0.06, subdiv=0, rough=0.0)
    kv = [m @ Matrix.Translation((r * 0.55, -0.05, 0.08)) @ Vector(p) for p in kv]
    a.add("Kit", kv, kf, GOLD, grad=0)


def glow_window(a, wall_r, y, r, ang, frame_col=TIMBER_DARK):
    out = Vector((math.cos(ang), 0, math.sin(ang)))
    m = Matrix.Translation(out * wall_r + Vector((0, y, 0))) @ Matrix.Rotation(-(ang - math.pi / 2), 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "X")
    v, f = lathe([(r, -0.02), (r, 0.06)], 12)
    a.add("Kit_Glow", [m @ Vector(p) for p in v], f, GOLD, jitter=0.0, grad=0)
    # frame ring + cross mullions
    v, f = lathe([(r + 0.09, -0.01), (r + 0.09, 0.1), (r + 0.01, 0.1), (r + 0.01, -0.01)], 12, cap_top=False, cap_bottom=False)
    a.add("Kit", [m @ Vector(p) for p in v], f, frame_col, grad=0)
    for rz in (0, math.pi / 2):
        bv, bf = box(0.06, 2 * r, 0.06)
        bv = xf(bv, loc=(0, -r, 0.0), rot=(0, 0, 0))
        mm = m @ Matrix.Translation((0, 0.08, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Rotation(rz, 4, "Z")
        a.add("Kit", [mm @ Vector(p) for p in bv], bf, frame_col, grad=0)


def wrap_root(a, base_r, h, start_ang, turns, r0, seed, branches=2, rising=1.0):
    """A bark root that grips the wall: spirals up from the ground, hugging the surface."""
    rng = random.Random(seed)
    pts, rad = [], []
    n = 14
    for i in range(n):
        t = i / (n - 1)
        ang = start_ang + turns * t * math.tau
        rr = base_r + r0 * (1 - t) * 0.55 + 0.35 * (1 - t) ** 4 - 0.04 * t
        y = h * rising * (t ** 1.1) + 0.02
        pts.append((math.cos(ang) * rr, y, math.sin(ang) * rr))
        rad.append(r0 * (1 - t) ** 0.9 + 0.035)
    # flare into the ground
    pts.insert(0, (pts[0][0] * 1.25, -0.05, pts[0][2] * 1.25))
    rad.insert(0, r0 * 1.4)
    v, f = tube(pts, rad, segs=7)
    a.add("Kit", v, f, lambda face, fv: BARK_DARK if (min(face) % 7) in (0, 3) else BARK, jitter=0.06, grad=0.25)
    # side rootlets
    for b in range(branches):
        k = rng.randint(3, 8)
        p = Vector(pts[k])
        d = Vector((p.x, 0, p.z)).normalized()
        tang = Vector((-d.z, 0, d.x)) * rng.choice((-1, 1))
        q = [p, p + tang * 0.5 + Vector((0, -0.25, 0)) + d * 0.1, p + tang * 0.9 + Vector((0, -0.7, 0)) + d * 0.05,
             p + tang * 1.1 + Vector((0, -p.y - 0.05, 0)) + d * 0.25]
        v, f = tube(q, [rad[k] * 0.6, rad[k] * 0.45, rad[k] * 0.3, 0.03], segs=5)
        a.add("Kit", v, f, BARK, jitter=0.06, grad=0.25)
    return pts


def moss_tuft(a, p, s, seed):
    v, f = stone(s, s * 0.55, s, subdiv=1, rough=0.35, seed=seed)
    v = xf(v, loc=p)
    a.add("Kit_Foliage", v, f, lambda face, fv: MOSS_LIGHT if fv[0].y > p[1] + s * 0.3 else MOSS, jitter=0.08, grad=0)


# ---------------------------------------------------------------- assets

def hut_a():
    a = Asset("settle-hut-a", 11)
    stone_base(a, 2.25, 1.15, segs=20, seed=3)
    # plaster drum and timber frame
    v, f = lathe([(2.02, 1.1), (2.0, 2.0), (1.94, 3.05)], 20, cap_bottom=False, wobble=0.015)
    a.add("Kit", v, f, PLASTER, jitter=0.04, grad=0)
    timber_posts(a, 2.03, 0.95, 3.2, 8, phase=0.2)
    v, f = lathe([(2.1, 2.98), (2.12, 3.14), (1.9, 3.18)], 20)  # wall plate
    a.add("Kit", v, f, TIMBER, grad=0)
    roof_shingles(a, 3.0, 3.05, 6.1, 5, 22, curl=0.9, colors=[TERRACOTTA, TERRA_DARK, TERRACOTTA, hexc("#D2774A"), TERRACOTTA])
    # the signature curl: the roof tip rolls over into a little hook
    v, f = tube([(0.85, 6.2, 0), (1.05, 6.55, 0), (1.4, 6.75, 0), (1.72, 6.6, 0), (1.78, 6.32, 0), (1.58, 6.2, 0)],
                [0.2, 0.17, 0.14, 0.11, 0.08, 0.06], segs=7)
    a.add("Kit", v, f, lambda face, fv: TERRA_DARK if (min(face) // 7) % 2 else TERRACOTTA, grad=0, jitter=0.05)
    fv, ff = stone(0.1, 0.1, 0.1, subdiv=1, rough=0.1)
    a.add("Kit", xf(fv, loc=(1.56, 6.1, 0)), ff, GOLD, grad=0)
    round_door(a, 2.27, 0.85, 0.72, ang=math.pi / 2)
    step, sf = stone(0.9, 0.12, 0.5, subdiv=1, rough=0.15, seed=7)
    a.add("Kit", xf(step, loc=(0, 0, 2.75)), sf, STONE_WARM)
    glow_window(a, 2.0, 2.2, 0.38, math.pi / 2 + 1.05)
    glow_window(a, 2.0, 2.25, 0.3, math.pi / 2 - 1.3)
    pts = wrap_root(a, 2.1, 3.0, start_ang=-0.45, turns=0.4, r0=0.32, seed=5)
    for i, k in enumerate((4, 9, 13)):
        moss_tuft(a, pts[k], 0.22 - i * 0.04, seed=i + 2)
    # chimney pot
    cv, cf = lathe([(0.32, 0), (0.3, 1.2), (0.36, 1.25), (0.36, 1.4), (0.24, 1.42)], 8, wobble=0.06)
    a.add("Kit", xf(cv, loc=(-1.2, 4.0, -0.7)), cf, STONE_DARK)
    return a


def hut_b():
    a = Asset("settle-hut-b", 22)
    stone_base(a, 2.55, 0.9, segs=20, seed=9)
    v, f = lathe([(2.3, 0.85), (2.28, 1.8), (2.2, 2.55)], 20, cap_bottom=False, wobble=0.02)
    a.add("Kit", v, f, mix(PLASTER, STONE_WARM, 0.3), jitter=0.04, grad=0)
    timber_posts(a, 2.3, 0.7, 2.75, 10, phase=0.5, size=0.22)
    # thatch: thick drooping rim then a bulb that curls back over at the top
    prof = [(2.55, 2.05), (3.1, 2.12), (3.3, 2.4), (3.2, 2.8), (2.9, 3.3), (2.5, 3.85), (2.0, 4.4),
            (1.5, 4.85), (1.0, 5.25), (0.6, 5.55), (0.32, 5.78), (0.14, 5.95), (0.0, 6.05)]
    cf = lambda t: (-1.1 * t ** 2.5, 0.35 * t ** 2.5)
    segs = 28
    v, f = lathe(prof, segs, center_fn=cf, wobble=0.03, seed=4, cap_top=False)
    # scallop the eave: bundles of straw droop between bindings
    for s_ in range(segs):
        for ring, amt in ((0, 0.22), (1, 0.12)):
            k = ring * segs + s_
            x, y, z = v[k]
            v[k] = (x, y - amt * abs(math.sin(s_ / segs * math.pi * 7)), z)
    streak = [random.Random(s_).random() for s_ in range(segs)]
    def thatch(face, fv):
        s_ = min(face) % segs
        ring = min(face) // segs
        c = mix(STRAW, STRAW_DARK, streak[s_] * 0.55)
        if ring <= 1:
            c = shade(c, 0.78)
        if ring in (5, 9):
            c = mix(c, TIMBER, 0.5)  # binding bands
        return c
    a.add("Kit", v, f, thatch, jitter=0.03, grad=0)
    # sprouting tuft at the crown (sways)
    for i in range(3):
        moss_tuft(a, (-1.05 + i * 0.14, 5.9 + i * 0.04, 0.33 - i * 0.12), 0.26 - i * 0.05, seed=20 + i)
    round_door(a, 2.55, 0.85, 0.7, ang=math.pi / 2 - 0.3)
    step, sf = stone(0.8, 0.12, 0.45, subdiv=1, rough=0.15, seed=8)
    a.add("Kit", xf(step, loc=(0.85, 0, 2.95), rot=(0, 0.3, 0)), sf, STONE)
    glow_window(a, 2.28, 1.85, 0.36, math.pi / 2 + 0.9)
    glow_window(a, 2.25, 1.9, 0.3, -0.6)
    # stone chimney stack against the back wall
    cv, cf = box(0.75, 4.6, 0.75, taper=0.75)
    a.add("Kit", xf(cv, loc=(-0.5, 0, -2.55)), cf, lambda face, fv: STONE_DARK if int(fv[0].y * 2.2) % 2 else STONE_WARM)
    pts = wrap_root(a, 2.4, 2.3, start_ang=0.3, turns=-0.4, r0=0.36, seed=12, branches=3)
    moss_tuft(a, pts[7], 0.2, seed=31)
    # lantern hook by the door
    lv, lf = lathe([(0.12, 0), (0.15, 0.12), (0.12, 0.26)], 6)
    a.add("Kit_Glow", xf(lv, loc=(1.95, 1.35, 2.25)), lf, GOLD, grad=0)
    return a


def shrine():
    a = Asset("settle-shrine", 33)
    # two-tier dais
    v, f = lathe([(2.0, 0), (2.05, 0.18), (1.9, 0.26)], 18, wobble=0.04, seed=2)
    a.add("Kit", v, f, lambda face, fv: STONE if (min(face) // 18) else STONE_DARK, jitter=0.07)
    v, f = lathe([(1.2, 0.24), (1.22, 0.45), (1.1, 0.5)], 14, wobble=0.04, seed=3)
    a.add("Kit", v, f, STONE_WARM, jitter=0.06)
    # rune ring
    v, f = lathe([(1.5, 0.27), (1.5, 0.29), (1.42, 0.29), (1.42, 0.27)], 18, cap_top=False, cap_bottom=False)
    a.add("Kit_Glow", v, f, TEAL, jitter=0.0, grad=0)
    # centre stone: faceted shard, glowing teal
    sv, sf = lathe([(0.32, 0.5), (0.42, 0.9), (0.36, 1.7), (0.22, 2.25), (0.0, 2.5)], 6, phase=0.3, wobble=0.12, seed=5)
    a.add("Kit_Glow", sv, sf, lambda face, fv: TEAL if fv[0].y > 1.0 else mix(TEAL, DEEP_TEAL, 0.4), jitter=0.05, grad=0)
    # ring of standing stones, each leaning a little, mossy tops
    n = 7
    for i in range(n):
        ang = i / n * math.tau + 0.2
        h = 1.6 + 0.6 * ((i * 37) % 5) / 4
        v, f = stone(0.32, h / 2, 0.24, subdiv=2, rough=0.18, seed=i + 10)
        v = xf(v, loc=(math.cos(ang) * 2.45, -0.05, math.sin(ang) * 2.45), rot=(0.08 * math.sin(i * 2.1), -ang, 0.07 * math.cos(i * 1.3)))
        top = max(p.y for p in v)
        a.add("Kit", v, f, lambda face, fv, top=top: mix(STONE_DARK, MOSS, 0.7) if fv[0].y > top - 0.25 else (STONE if fv[0].y > 0.5 else STONE_WARM), jitter=0.07)
        # glowing carved mark facing the centre
        mv, mf = box(0.08, 0.32, 0.03)
        mv = xf(mv, loc=(math.cos(ang) * 2.2, h * 0.45, math.sin(ang) * 2.2), rot=(0, -ang + math.pi / 2, 0))
        a.add("Kit_Glow", mv, mf, TEAL, jitter=0, grad=0)
    # offering bowls
    for k, ang in enumerate((0.9, 2.6, 4.4)):
        bv, bf = lathe([(0.1, 0.5), (0.22, 0.58), (0.24, 0.66)], 8)
        a.add("Kit", xf(bv, loc=(math.cos(ang) * 0.85, 0, math.sin(ang) * 0.85)), bf, TERRACOTTA)
    return a


def lantern(a, loc, color=GOLD, scale=1.0):
    x, y, z = loc
    s = scale
    cv, cf = lathe([(0.04 * s, 0.32 * s), (0.22 * s, 0.22 * s), (0.2 * s, 0.17 * s)], 6, phase=0.26)
    a.add("Kit", xf(cv, loc=(x, y, z)), cf, IRON, grad=0)
    gv, gf = lathe([(0.1 * s, -0.24 * s), (0.15 * s, -0.12 * s), (0.15 * s, 0.08 * s), (0.11 * s, 0.17 * s)], 6, phase=0.26)
    a.add("Kit_Glow", xf(gv, loc=(x, y, z)), gf, color, jitter=0, grad=0)
    bv, bf = lathe([(0.17 * s, -0.3 * s), (0.17 * s, -0.24 * s), (0.04 * s, -0.22 * s)], 6, phase=0.26)
    a.add("Kit", xf(bv, loc=(x, y, z)), bf, IRON, grad=0)


def hook_post(a, height, arm, color, seed):
    sv, sf = stone(0.32, 0.22, 0.3, subdiv=1, rough=0.2, seed=seed)
    a.add("Kit", sv, sf, STONE_WARM)
    pts = [(0, 0.1, 0), (0.02, height * 0.5, 0.01), (-0.02, height * 0.85, 0), (0.05, height, 0),
           (arm * 0.45, height + 0.18, 0), (arm * 0.85, height + 0.08, 0), (arm, height - 0.12, 0)]
    v, f = tube(pts, [0.12, 0.1, 0.09, 0.08, 0.06, 0.05, 0.035], segs=6)
    a.add("Kit", v, f, lambda face, fv: TIMBER if fv[0].y < height else TIMBER_DARK, grad=0.1)
    lantern(a, (arm, height - 0.45, 0), color)


def lantern_post():
    a = Asset("settle-lantern-post", 44)
    hook_post(a, 2.3, 0.55, GOLD, 3)
    return a


def bridge_post():
    a = Asset("settle-bridge-post", 45)
    sv, sf = stone(0.45, 0.3, 0.42, subdiv=1, rough=0.2, seed=6)
    a.add("Kit", sv, sf, STONE)
    v, f = tube([(0, 0.1, 0), (0.03, 1.2, 0), (-0.02, 2.2, 0.02), (0, 2.5, 0)], [0.17, 0.15, 0.14, 0.12], segs=7)
    a.add("Kit", v, f, TIMBER)
    # rope lashing bands
    for y in (1.0, 1.15):
        rv, rf = lathe([(0.175, y), (0.175, y + 0.07)], 7)
        a.add("Kit", rv, rf, ROPE, grad=0)
    # cap and arm with teal lantern
    cv, cf = lathe([(0.2, 2.48), (0.05, 2.75)], 7)
    a.add("Kit", cv, cf, TERRACOTTA, grad=0)
    v, f = tube([(0, 2.25, 0), (0.35, 2.33, 0), (0.6, 2.25, 0)], [0.06, 0.05, 0.04], segs=5)
    a.add("Kit", v, f, TIMBER_DARK, grad=0)
    lantern(a, (0.6, 1.88, 0), TEAL)
    return a


def fence():
    a = Asset("settle-fence", 55)
    for i, x in enumerate((-1.0, 1.0)):
        v, f = box(0.16, 1.15, 0.16, taper=0.85)
        v = xf(v, rot=(0, 0.3 * i, 0.04 * (1 - 2 * i)), loc=(x, 0, 0))
        a.add("Kit", v, f, TIMBER)
        tv, tf = lathe([(0.1, 0), (0.0, 0.2)], 4, phase=math.pi / 4)
        a.add("Kit", xf(tv, loc=(x, 1.14, 0)), tf, TIMBER_DARK, grad=0)
    for y, wob in ((0.45, 0.03), (0.88, -0.04)):
        pts = [(-1.08, y, 0.0), (-0.3, y + wob, 0.03), (0.4, y - wob, -0.02), (1.08, y + 0.02, 0.0)]
        v, f = tube(pts, [0.06, 0.07, 0.065, 0.06], segs=5)
        a.add("Kit", v, f, WOOD, grad=0)
    # rope lashings on the posts
    for x in (-1.0, 1.0):
        for y in (0.45, 0.88):
            rv, rf = lathe([(0.11, y - 0.05), (0.11, y + 0.05)], 6)
            a.add("Kit", xf(rv, loc=(x, 0, 0)), rf, ROPE, grad=0)
    return a


def crate():
    a = Asset("settle-crate", 66)
    s = 0.8
    v, f = box(s - 0.04, s - 0.04, s - 0.04)
    a.add("Kit", xf(v, loc=(0, 0.02, 0)), f, lambda face, fv: WOOD_LIGHT, jitter=0.05)
    # plank seams as darker inset slats on each side
    for side in range(4):
        rot = side * math.pi / 2
        for k in (-0.2, 0.2):
            sv, sf = box(0.02, s * 0.88, 0.02)
            a.add("Kit", xf(sv, loc=(math.sin(rot) * (s / 2 - 0.015) + math.cos(rot) * k, 0.05, math.cos(rot) * (s / 2 - 0.015) - math.sin(rot) * k)), sf, TIMBER_DARK, grad=0)
    # frame: edge beams
    e = 0.1
    for x in (-1, 1):
        for z in (-1, 1):
            bv, bf = box(e, s, e)
            a.add("Kit", xf(bv, loc=(x * (s - e) / 2, 0, z * (s - e) / 2)), bf, TIMBER)
    for y in (0, s - e):
        for (sx, sz, x, z) in ((s, e, 0, -1), (s, e, 0, 1), (e, s, -1, 0), (e, s, 1, 0)):
            bv, bf = box(sx + 0.01, e, sz + 0.01)
            a.add("Kit", xf(bv, loc=(x * (s - e) / 2, y, z * (s - e) / 2)), bf, TIMBER)
    # diagonal brace on the front
    bv, bf = box(0.08, s * 1.15, 0.03)
    a.add("Kit", xf(bv, loc=(-0.3, 0.1, s / 2 + 0.01), rot=(0, 0, -0.78)), bf, TIMBER, grad=0)
    return a


def barrel():
    a = Asset("settle-barrel", 77)
    prof = [(0.3, 0), (0.36, 0.2), (0.39, 0.45), (0.36, 0.7), (0.3, 0.9), (0.27, 0.92)]
    v, f = lathe(prof, 14)
    a.add("Kit", v, f, lambda face, fv: (WOOD if (min(face) % 14) % 2 else WOOD_LIGHT) if len(face) == 4 else TIMBER, jitter=0.05)
    for y, r in ((0.12, 0.345), (0.75, 0.35)):
        hv, hf = lathe([(r, y), (r + 0.02, y + 0.03), (r, y + 0.07)], 14, cap_top=False, cap_bottom=False)
        a.add("Kit", hv, hf, IRON, grad=0)
    hv, hf = lathe([(0.392, 0.42), (0.405, 0.45), (0.392, 0.49)], 14, cap_top=False, cap_bottom=False)
    a.add("Kit", hv, hf, ROPE, grad=0)
    return a


def cart():
    a = Asset("settle-cart", 88)
    # bed with plank sides
    v, f = box(1.3, 0.12, 2.0)
    a.add("Kit", xf(v, loc=(0, 0.55, 0)), f, WOOD)
    for x in (-0.62, 0.62):
        v, f = box(0.08, 0.38, 2.0)
        a.add("Kit", xf(v, loc=(x, 0.67, 0)), f, WOOD_LIGHT)
    for z in (-0.97, 0.97):
        v, f = box(1.3, 0.36, 0.08)
        a.add("Kit", xf(v, loc=(0, 0.67, z)), f, WOOD_LIGHT)
    # wheels: rim, hub, spokes
    for x in (-0.78, 0.78):
        m = Matrix.Translation((x, 0.5, -0.2)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        rv, rf = lathe([(0.5, -0.06), (0.5, 0.06), (0.4, 0.06), (0.4, -0.06)], 12, cap_top=False, cap_bottom=False)
        a.add("Kit", [m @ Vector(p) for p in rv], rf + [], TIMBER_DARK, grad=0)
        hv, hf = lathe([(0.1, -0.1), (0.1, 0.1)], 6)
        a.add("Kit", [m @ Vector(p) for p in hv], hf, IRON, grad=0)
        for k in range(3):
            sv, sf = box(0.06, 0.82, 0.05)
            mm = m @ Matrix.Rotation(k * math.pi / 3, 4, "Y") @ Matrix.Translation((0, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Translation((0, -0.41, 0))
            a.add("Kit", [mm @ Vector(p) for p in sv], sf, TIMBER, grad=0)
    # axle and handles
    v, f = tube([(-0.85, 0.5, -0.2), (0.85, 0.5, -0.2)], [0.05, 0.05], segs=5)
    a.add("Kit", v, f, TIMBER_DARK, grad=0)
    for x in (-0.45, 0.45):
        v, f = tube([(x, 0.6, 0.9), (x * 0.9, 0.5, 1.6), (x * 0.8, 0.42, 2.0)], [0.05, 0.045, 0.04], segs=5)
        a.add("Kit", v, f, TIMBER, grad=0)
    # cargo: a sack and a small crate
    sv, sf = stone(0.32, 0.24, 0.28, subdiv=1, rough=0.15, seed=4)
    a.add("Kit", xf(sv, loc=(-0.25, 0.65, 0.4)), sf, hexc("#CDB88E"))
    cv, cf = box(0.45, 0.4, 0.45)
    a.add("Kit", xf(cv, loc=(0.25, 0.66, -0.45), rot=(0, 0.3, 0)), cf, WOOD_LIGHT)
    return a


def signpost():
    a = Asset("settle-signpost", 99)
    sv, sf = stone(0.28, 0.16, 0.26, subdiv=1, rough=0.2, seed=2)
    a.add("Kit", sv, sf, STONE_WARM)
    v, f = tube([(0, 0.05, 0), (0.03, 1.2, 0), (-0.01, 2.1, 0.01)], [0.09, 0.08, 0.07], segs=6)
    a.add("Kit", v, f, TIMBER)
    cv, cf = lathe([(0.14, 2.08), (0.0, 2.32)], 6)
    a.add("Kit", cv, cf, TERRACOTTA, grad=0)
    # arrow boards: 5-gon prisms
    for y, ang, ln, col in ((1.75, 0.3, 0.95, WOOD_LIGHT), (1.42, 2.6, 0.8, WOOD), (1.12, -1.2, 0.7, WOOD_LIGHT)):
        h = 0.11
        prof = [(0, -h), (ln - 0.18, -h), (ln, 0), (ln - 0.18, h), (0, h)]
        verts = [(x, yy, -0.03) for x, yy in prof] + [(x, yy, 0.03) for x, yy in prof]
        faces = [(0, 1, 2, 3, 4)[::-1], (5, 6, 7, 8, 9)] + [(i, (i + 1) % 5, (i + 1) % 5 + 5, i + 5) for i in range(5)]
        verts = xf(verts, loc=(0, y, 0), rot=(0, ang, 0.05))
        a.add("Kit", verts, faces, lambda face, fv, c=col: c, grad=0)
        # carved rune dot
        dv, df = disc(0.035, 5, 0.01)
        a.add("Kit", xf([(p[0], p[2], p[1]) for p in dv], loc=(0, y, 0), rot=(0, ang, 0.05)), df, TIMBER_DARK, grad=0)
    return a


def well():
    a = Asset("settle-well", 111)
    segs = 12
    prof = [(1.0, 0), (1.05, 0.35), (1.0, 0.8), (1.06, 0.86), (0.72, 0.9), (0.68, 0.84), (0.66, 0.6)]
    v, f = lathe(prof, segs, cap_top=False, wobble=0.04, seed=3)
    rng = random.Random(4)
    a.add("Kit", v, f, lambda face, fv: rng.choice([STONE, STONE_WARM, STONE_DARK]) if fv[0].y < 0.85 else STONE, jitter=0.05)
    wv, wf = lathe([(0.67, 0.6), (0.0, 0.6)], segs, cap_top=False, cap_bottom=False)
    a.add("Kit", wv, wf, WATER, grad=0)
    # posts, beam, windlass rope, bucket
    for x in (-0.9, 0.9):
        pv, pf = box(0.14, 2.1, 0.14, taper=0.9)
        a.add("Kit", xf(pv, loc=(x, 0.6, 0)), pf, TIMBER)
    bv, bf = tube([(-1.05, 2.2, 0), (1.05, 2.2, 0)], [0.07, 0.07], segs=6)
    a.add("Kit", bv, bf, TIMBER_DARK, grad=0)
    rv, rf = tube([(0, 2.2, 0), (0, 1.35, 0)], [0.02, 0.02], segs=4, cap=False)
    a.add("Kit", rv, rf, ROPE, grad=0)
    kv, kf = lathe([(0.12, 1.05), (0.15, 1.35)], 7)
    a.add("Kit", kv, kf, WOOD, grad=0)
    # little shingle roof
    for sgn in (-1, 1):
        sv, sf = box(2.5, 0.08, 0.95)
        a.add("Kit", xf(sv, loc=(0, 2.48, sgn * 0.4), rot=(sgn * 0.62, 0, 0)), sf, lambda face, fv: TERRACOTTA if face[0] < 4 or True else TERRA_DARK, grad=0)
    rv2, rf2 = tube([(-1.3, 2.75, 0), (1.3, 2.75, 0)], [0.06, 0.06], segs=5)
    a.add("Kit", rv2, rf2, TERRA_DARK, grad=0)
    return a


def stair_stones():
    a = Asset("settle-stair-stones", 122)
    path = [(-0.3, 0.0), (0.35, 0.75), (-0.2, 1.5), (0.3, 2.2), (-0.1, 2.95)]
    for i, (x, z) in enumerate(path):
        v, f = stone(0.42 - 0.03 * (i % 2), 0.12 + 0.02 * i, 0.34, subdiv=1, rough=0.2, seed=i + 40)
        top = max(p[1] for p in v)
        v = xf(v, loc=(x, -0.04, z - 1.45), rot=(0, i * 0.9, 0))
        a.add("Kit", v, f, lambda face, fv, t=top: (mix(STONE, MOSS, 0.55) if fv[0].x < -0.25 else STONE) if fv[0].y > t * 0.5 else STONE_DARK, jitter=0.07)
    for i, (x, z) in enumerate(path[1::2]):
        moss_tuft(a, (x + 0.45, 0, z - 1.45), 0.13, seed=50 + i)
    return a


def bridge_plank():
    a = Asset("settle-bridge-plank", 133)
    W, L = 2.4, 2.0
    n = 7
    rng = random.Random(6)
    for i in range(n):
        z = (i + 0.5) * L / n
        w = W * (0.94 + rng.uniform(-0.04, 0.04))
        v, f = box(w, 0.08, L / n * 0.82)
        v = xf(v, loc=(rng.uniform(-0.05, 0.05), -0.08, z), rot=(0, rng.uniform(-0.04, 0.04), 0))
        a.add("Kit", v, f, WOOD_LIGHT if i % 2 else WOOD, jitter=0.07, grad=0)
    # stringers under the planks
    for x in (-0.95, 0.95):
        v, f = box(0.14, 0.12, L)
        a.add("Kit", xf(v, loc=(x, -0.2, L / 2)), f, TIMBER_DARK, grad=0)
    # rope hand rails: same height at both ends so segments chain; slight mid sag
    for x in (-1.12, 1.12):
        pts = [(x, 1.0 - 0.06 * math.sin(t / 4 * math.pi), t / 4 * L) for t in range(5)]
        v, f = tube(pts, [0.035] * 5, segs=5, cap=False)
        a.add("Kit", v, f, ROPE, grad=0)
        # low rope and drop lines
        pts2 = [(x, 0.45 - 0.04 * math.sin(t / 4 * math.pi), t / 4 * L) for t in range(5)]
        v, f = tube(pts2, [0.025] * 5, segs=4, cap=False)
        a.add("Kit", v, f, ROPE, grad=0)
        for z in (0.5, 1.0, 1.5):
            v, f = tube([(x, -0.04, z), (x, 0.95, z)], [0.018, 0.018], segs=4, cap=False)
            a.add("Kit", v, f, ROPE, grad=0)
        # post at the start of the segment
        pv, pf = tube([(x, -0.25, 0.08), (x, 0.8, 0.08), (x, 1.12, 0.08)], [0.08, 0.07, 0.06], segs=6)
        a.add("Kit", pv, pf, TIMBER, grad=0)
        kv, kf = lathe([(0.085, 0.95), (0.085, 1.05)], 6)
        a.add("Kit", xf(kv, loc=(x, 0, 0.08)), kf, ROPE, grad=0)
    return a


ASSETS = [
    (hut_a, "building", 3.1, 6.4, 0.9, 1.15, True),
    (hut_b, "building", 3.3, 5.9, 0.9, 1.15, True),
    (shrine, "landmark", 2.8, 2.6, 0.9, 1.2, True),
    (lantern_post, "prop", 0.4, 2.6, 0.9, 1.15, True),
    (fence, "prop", 1.1, 1.35, 0.95, 1.1, True),
    (crate, "prop", 0.5, 0.8, 0.8, 1.3, True),
    (barrel, "prop", 0.4, 0.92, 0.85, 1.2, True),
    (cart, "prop", 1.1, 1.0, 0.95, 1.1, True),
    (signpost, "prop", 0.35, 2.3, 0.9, 1.1, True),
    (well, "prop", 1.1, 2.8, 0.95, 1.1, True),
    (stair_stones, "prop", 1.6, 0.25, 0.8, 1.3, False),
    (bridge_plank, "bridge", 1.2, 1.1, 1.0, 1.0, False),
    (bridge_post, "bridge", 0.45, 2.75, 0.95, 1.1, True),
]

BUDGET = {"building": 4000, "landmark": 3000, "prop": 600, "bridge": 600}

# ---------------------------------------------------------------- blender plumbing

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    m.use_backface_culling = True
    return m


def build_objects(asset):
    objs = []
    for mat, p in asset.parts.items():
        if not p.faces:
            continue
        me = bpy.data.meshes.new(f"{asset.name}-{mat}")
        me.from_pydata([tuple(v) for v in p.verts], [], p.faces)
        me.validate()
        # glTF is Y-up; Blender is Z-up. Our coordinates are Y-up, so swap to Z-up here.
        me.transform(Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
        col = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for poly, c in zip(me.polygons, p.cols):
            for li in poly.loop_indices:
                col.data[li].color_srgb = (*c, 1.0)
        me.color_attributes.active_color = col
        me.update()
        me.materials.append(material(mat))
        for poly in me.polygons:
            poly.use_smooth = False
        ob = bpy.data.objects.new(f"{asset.name}-{mat}", me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    return objs


def tri_count(objs):
    n = 0
    for ob in objs:
        ob.data.calc_loop_triangles()
        n += len(ob.data.loop_triangles)
    return n


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True,
        export_apply=True, export_texcoords=False, export_normals=True,
        export_vertex_color="ACTIVE", export_materials="EXPORT", export_cameras=False, export_lights=False,
    )


def contact_sheet(ids, path):
    reset()
    scene = bpy.context.scene
    cols = 5
    cell = 8.0
    for i, aid in enumerate(ids):
        bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, f"{aid}.glb"))
        r, c = divmod(i, cols)
        big = aid in ("settle-hut-a", "settle-hut-b", "settle-shrine")
        for ob in bpy.context.selected_objects:
            if ob.type == "MESH" and ob.active_material and ob.active_material.name.startswith("Kit_Glow"):
                nt = ob.active_material.node_tree
                bsdf = nt.nodes["Principled BSDF"]
                vc = nt.nodes.new("ShaderNodeVertexColor")
                nt.links.new(vc.outputs["Color"], bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = 2.0
            if ob.parent is None:
                if not big:
                    ob.scale *= 2.0
                if aid == "settle-bridge-plank":
                    ob.location.z += 0.6  # walking surface is y=0; lift it off the sheet's ground
                ob.location.x += c * cell
                ob.location.y -= r * cell
        txt = bpy.data.curves.new(f"label-{aid}", "FONT")
        txt.body = aid.replace("settle-", "") + ("" if aid in ("settle-hut-a", "settle-hut-b", "settle-shrine") else " x2")
        txt.size = 0.55
        txt.align_x = "CENTER"
        to = bpy.data.objects.new(f"label-{aid}", txt)
        to.location = (c * cell, -r * cell - 3.6, 0.01)
        scene.collection.objects.link(to)
    # props are tiny next to huts: scale prop cells up so they read
    ground = bpy.data.meshes.new("ground")
    rows = math.ceil(len(ids) / cols)
    gw, gh = cols * cell, rows * cell
    ground.from_pydata([(-cell, cell, 0), (gw, cell, 0), (gw, -gh, 0), (-cell, -gh, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("ground", ground)
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.36, 0.26, 1)
    ground.materials.append(gm)
    scene.collection.objects.link(g)

    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = cols * cell * 1.02
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    center = Vector(((cols - 1) * cell / 2, -(rows - 1) * cell / 2, 1.5))
    direction = Vector((1.0, -1.15, 0.95)).normalized()
    cam.location = center + direction * 60
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    pts = [inv @ (ob.matrix_world @ Vector(c)) for ob in scene.objects
           if ob.type in ("MESH", "FONT") and ob.name != "ground" for c in ob.bound_box]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    cam.location = cam.matrix_world @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    aspect = 16 / 10
    cam_d.ortho_scale = max(x1 - x0, (y1 - y0) * aspect) * 1.06

    sun = bpy.data.lights.new("key", "SUN")
    sun.color = (1.0, 0.86, 0.66)
    sun.energy = 3.2
    sun.angle = math.radians(8)
    so = bpy.data.objects.new("key", sun)
    so.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    scene.collection.objects.link(so)
    fill = bpy.data.lights.new("fill", "SUN")
    fill.color = (0.45, 0.85, 0.82)
    fill.energy = 0.9
    fo = bpy.data.objects.new("fill", fill)
    fo.rotation_euler = (math.radians(60), 0, math.radians(150))
    scene.collection.objects.link(fo)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.68, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    scene.world = world

    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1250
    scene.view_settings.view_transform = "Standard"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    manifest, report = [], []
    for fn, cat, radius, height, mn, mx, collide in ASSETS:
        reset()
        asset = fn()
        objs = build_objects(asset)
        tris = tri_count(objs)
        path = os.path.join(OUT, f"{asset.name}.glb")
        export(objs, path)
        flag = "" if tris <= BUDGET[cat] else "  OVER BUDGET"
        report.append(f"{asset.name:24s} {tris:5d} tris (≤{BUDGET[cat]}){flag}")
        manifest.append({
            "id": asset.name, "file": f"{asset.name}.glb", "category": cat,
            "biomes": ["roothold"], "radius": radius, "height": height,
            "minScale": mn, "maxScale": mx, "collide": collide,
        })
    with open(os.path.join(OUT, "settlement.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print("\n".join(report))
    if "--no-sheet" not in sys.argv:
        contact_sheet([m["id"] for m in manifest], os.path.join(OUT, "settle-sheet.png"))


main()
