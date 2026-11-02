# Detailed Accord Town kit: Anchorkin crystal-veined basalt ground floors with round arches and chains, Rootwarden
# deadwood timber framing with plaster and moss above, terracotta tile roofs, Galeborne spires, cupolas, sailcloth
# and banners. Pieces follow kit.json sizes and pivots exactly so they snap on the 2 m grid; prefabs come from each
# prefab's layout. Textures are the painted swatches in art/textures/accord (teal slate and teal wood are tinted
# from the terracotta and deadwood swatches).
# Usage: Blender --background --python scripts/kit/accord.py -- accord
import math, os, random, sys
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, arch, box, extrude, fill, hermite, inside, join, pointed_arch, tube  # noqa: E402

MATS = [("ACC_Basalt", "basalt.png", 0), ("ACC_Deadwood", "deadwood.png", 0), ("ACC_TimberJoint", "timber-joint.png", 0),
        ("ACC_Plaster", "plaster.png", 0), ("ACC_Terracotta", "terracotta.png", 0), ("ACC_Sailcloth", "sailcloth.png", 0),
        ("ACC_Banner", "banner.png", 0), ("ACC_Cobble", "cobble.png", 0), ("ACC_TealSlate", "teal-slate.png", 0),
        ("ACC_TealWood", "teal-wood.png", 0), ("ACC_BasaltBlock", "basalt-block.png", 0),
        ("ACC_Crystal", (0.2, 0.95, 0.82), 4.0), ("ACC_Glow", (1.0, 0.68, 0.28), 3.0), ("ACC_Brass", (0.78, 0.56, 0.2), 0),
        ("ACC_Iron", (0.1, 0.1, 0.11), 0), ("ACC_Teal", (0.05, 0.32, 0.31), 0), ("ACC_Leaf", (0.19, 0.34, 0.07), 0),
        ("ACC_Flower", (0.93, 0.45, 0.58), 0), ("ACC_Petal", (0.96, 0.94, 0.84), 0), ("ACC_Soil", (0.2, 0.13, 0.08), 0)]
(STONE, WOOD, JOINT, PLASTER, TILE, SAIL, BANNER, COBBLE, SLATE, TWOOD, BLOCK,
 CRYSTAL, GLOW, BRASS, IRON, TEAL, LEAF, FLOWER, PETAL, SOIL) = range(len(MATS))
# Beam ends show deadwood; moss and flowers settle on upward-facing deadwood
K.configure(MATS, os.path.join(B.ROOT, "art/textures/accord"), cap_mat=WOOD, moss=(WOOD, JOINT, 0.72))

STOREY, WALL = 3.0, 0.5


# ---------- small geometry helpers (glTF coordinates) ----------

def beam(m, a, b, w, h, mat, up=(0, 1, 0), tile=2.0, cap=None):
    """Rectangular beam along a->b, `w` across (side), `h` along `up`; grain (texture v) runs along the beam."""
    a, b = Vector(a), Vector(b)
    t = b - a
    L = t.length
    t.normalize()
    up = Vector(up)
    if abs(t.dot(up.normalized())) > 0.95:
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    s = t.cross(up).normalized()
    u = s.cross(t).normalized()
    cs = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    ra = [m.vert(a + s * x + u * y) for x, y in cs]
    rb = [m.vert(b + s * x + u * y) for x, y in cs]
    per = [w, h, w, h]
    acc = 0.0
    for k in range(4):
        k1 = (k + 1) % 4
        u0, u1 = acc / tile, (acc + per[k]) / tile
        acc += per[k]
        m.face((ra[k], ra[k1], rb[k1], rb[k]), ((u0, 0), (u1, 0), (u1, L / tile), (u0, L / tile)), mat)
    cm = mat if cap is None else cap
    cuv = [(0.5 + x, 0.5 + y) for x, y in cs]
    m.face(ra[::-1], cuv[::-1], cm)
    m.face(rb, cuv, cm)


def hbox(m, lo, hi, mat, tile=2.0, cap=None):
    """Box whose texture grain runs along its longest horizontal side (planks, sills, rails)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    cy, cx, cz = (y0 + y1) / 2, (x0 + x1) / 2, (z0 + z1) / 2
    if x1 - x0 >= z1 - z0:
        beam(m, (x0, cy, cz), (x1, cy, cz), z1 - z0, y1 - y0, mat, tile=tile, cap=cap)
    else:
        beam(m, (cx, cy, z0), (cx, cy, z1), x1 - x0, y1 - y0, mat, tile=tile, cap=cap)


def vbox(m, lo, hi, mat, tile=2.0, cap=None):
    """Box with vertical grain (posts)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    beam(m, ((x0 + x1) / 2, y0, (z0 + z1) / 2), ((x0 + x1) / 2, y1, (z0 + z1) / 2), x1 - x0, z1 - z0, mat, up=(0, 0, 1), tile=tile, cap=cap)


def prism_x(m, pts, x0, x1, mat, tile=2.0):
    """Prism from an outline in (z, y), between x0 and x1."""
    a = [m.vert((x0, y, z)) for z, y in pts]
    b = [m.vert((x1, y, z)) for z, y in pts]
    m.face(a[::-1], None, mat, tile)
    m.face(b, None, mat, tile)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        m.face((a[i], a[j], b[j], b[i]), None, mat, tile)


def poly_prism(m, pts3, n_off, mat, tile=2.0, uvs=None):
    """Thicken a planar polygon (3D points) along vector n_off."""
    n_off = Vector(n_off)
    a = [m.vert(Vector(p)) for p in pts3]
    b = [m.vert(Vector(p) + n_off) for p in pts3]
    m.face(a[::-1], None if uvs is None else uvs[::-1], mat, tile)
    m.face(b, uvs, mat, tile)
    for i in range(len(pts3)):
        j = (i + 1) % len(pts3)
        m.face((a[i], a[j], b[j], b[i]), None, mat, tile)


def gem(m, c, rx, ry, rz, mat, axis=(0, 1, 0), spin=0.0):
    c = Vector(c)
    rot = Vector((0, 1, 0)).rotation_difference(Vector(axis).normalized()).to_matrix() @ Matrix.Rotation(spin, 3, "Y")
    ring = [m.vert(c + rot @ Vector(p)) for p in ((rx, 0, 0), (0, 0, -rz), (-rx, 0, 0), (0, 0, rz))]
    top, bot = m.vert(c + rot @ Vector((0, ry, 0))), m.vert(c + rot @ Vector((0, -ry, 0)))
    for i in range(4):
        j = (i + 1) % 4
        m.face((ring[i], ring[j], top), ((0, 0), (1, 0), (0.5, 1)), mat)
        m.face((ring[j], ring[i], bot), ((0, 0), (1, 0), (0.5, 1)), mat)


def lathe(m, c, prof, sides, mat, tile=1.0, a0=0.0, sx=1.0, sz=1.0, rough=0.0, seed=0.0):
    """Surface of revolution around a vertical axis at c from (radius, height) points, bottom to top.
    Zero-radius ends close to a point; other ends are capped flat."""
    c = Vector(c)
    L = [0.0]
    for i in range(1, len(prof)):
        L.append(L[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    rmax = max(r for r, _ in prof)
    urep = max(1, round(2 * math.pi * rmax / tile))
    rings = []
    for (r, y), l in zip(prof, L):
        if r < 1e-4:
            rings.append((m.vert(c + Vector((0, y, 0))), l))
            continue
        ring = []
        for k in range(sides):
            a = a0 + 2 * math.pi * k / sides
            rr = r * (1 + rough * noise.noise(Vector((math.cos(a) * 1.7, y * 1.3, seed))))
            ring.append(m.vert(c + Vector((math.cos(a) * rr * sx, y, -math.sin(a) * rr * sz))))
        rings.append((ring, l))
    for (r0, l0), (r1, l1) in zip(rings, rings[1:]):
        v0, v1 = l0 / tile, l1 / tile
        for k in range(sides):
            k1 = (k + 1) % sides
            u0, u1 = k / sides * urep, (k + 1) / sides * urep
            if isinstance(r0, list) and isinstance(r1, list):
                m.face((r0[k], r0[k1], r1[k1], r1[k]), ((u0, v0), (u1, v0), (u1, v1), (u0, v1)), mat)
            elif isinstance(r0, list):
                m.face((r0[k], r0[k1], r1), ((u0, v0), (u1, v0), ((u0 + u1) / 2, v1)), mat)
            else:
                m.face((r1[k1], r1[k], r0), ((u1, v1), (u0, v1), ((u0 + u1) / 2, v0)), mat)
    for ring, flip in ((rings[0][0], True), (rings[-1][0], False)):
        if isinstance(ring, list):
            uv = [(0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
            m.face(ring[::-1] if flip else ring, uv[::-1] if flip else uv, mat)
    return rings


def ball(m, c, r, mat, sides=7):
    prof = [(r * math.sin(math.pi * i / 4), -r * math.cos(math.pi * i / 4)) for i in range(5)]
    lathe(m, c, prof, sides, mat)


def loop(m, pts, r, mat, sides=6, rough=0.0, seed=0.0, tile=1.0):
    """Closed tube through points."""
    pts = [Vector(p) for p in pts]
    pts = pts + [pts[0].copy(), pts[1].copy()]
    tube(m, pts, [r] * len(pts), mat, sides, rough=rough, seed=seed, caps=(False, False), tile=tile)


def chain(m, a, b, mat, link=0.11, r=0.016, sag=0.0):
    """Chain of alternating links from a to b (sagging by `sag` at the middle)."""
    a, b = Vector(a), Vector(b)
    n = max(2, round((b - a).length / (link * 0.78)))
    pts = [a.lerp(b, i / n) + Vector((0, -sag * 4 * (i / n) * (1 - i / n), 0)) for i in range(n + 1)]
    for i in range(n):
        p, q = pts[i], pts[i + 1]
        d = (q - p).normalized()
        side = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
        if i % 2:
            side = d.cross(side).normalized()
        c = (p + q) / 2
        ring = [c + d * math.cos(2 * math.pi * k / 5) * link * 0.62 + side * math.sin(2 * math.pi * k / 5) * link * 0.36 for k in range(5)]
        loop(m, ring, r, mat, sides=3)


def ribbon(m, pts, width, z, mat):
    """Flat strip on a plane facing +Z (crystal veins on stone faces)."""
    pts = [Vector((x, y)) for x, y in pts]
    L = []
    R = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        d = (b - a).normalized()
        n = Vector((-d.y, d.x)) * width * (0.5 + 0.5 * math.sin(i * 1.7) ** 2)
        L.append(m.vert((p.x + n.x, p.y + n.y, z)))
        R.append(m.vert((p.x - n.x, p.y - n.y, z)))
    for i in range(len(pts) - 1):
        m.face((R[i], R[i + 1], L[i + 1], L[i]), ((0, 0), (1, 0), (1, 1), (0, 1)), mat)


def surface(m, fn, nu, nv, mat, uvfn=None):
    """Grid surface from fn(u, v) -> glTF point; used for cloth (solidified later)."""
    g = [[m.vert(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            uv = [(a / nu, b / nv) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if uvfn:
                uv = [uvfn(u, v) for u, v in uv]
            m.face((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]), uv, mat)


def u_outline(w, h, y0, cx, shape):
    """Wall outline from y0 to h with an opening notch (arch outline whose base sits on y0)."""
    pts = [(cx + x, y0 + y) for x, y in shape]
    return [(0, y0)] + pts + [(w, y0), (w, h), (0, h)]


def tiles(m, A, B, D, C, rows, tw, R, t=0.045, lift=0.05, base=0.0, mat=TILE, overlap=1.5, round_tip=True, uvcell=(0.22, 0.24)):
    """Overlapping roof tiles on the quad A-B (eave, left to right seen from outside) to D-C (top)."""
    A, B, C, D = (Vector(v) for v in (A, B, C, D))
    N = (B - A).cross(D - A).normalized()
    for r in range(rows):
        s0, s1 = r / rows, min(1.0, (r + overlap) / rows)
        L0, R0, L1, R1 = A.lerp(D, s0), B.lerp(C, s0), A.lerp(D, s1), B.lerp(C, s1)
        n = max(1, round((R0 - L0).length / tw))
        off = 0.5 if r % 2 else 0.0
        cuts = sorted({0.0, 1.0} | {(k + off) / n for k in range(n + 1) if 0 < (k + off) / n < 1})
        for f0, f1 in zip(cuts, cuts[1:]):
            if (f1 - f0) * (R0 - L0).length < 0.08:
                continue
            g = 0.012 / max((R0 - L0).length, 0.1)
            bl, br = L0.lerp(R0, f0 + g), L0.lerp(R0, f1 - g)
            tl, tr = L1.lerp(R1, f0 + g), L1.lerp(R1, f1 - g)
            jl = lift + R.uniform(-0.02, 0.02)
            if round_tip:
                outline = [(bl.lerp(br, 0.14), 0.0, 0.14), (bl.lerp(br, 0.86), 0.0, 0.86), (br.lerp(tr, 0.1), 0.1, 1.0),
                           (tr, 1.0, 1.0), (tl, 1.0, 0.0), (bl.lerp(tl, 0.1), 0.1, 0.0)]
            else:
                outline = [(bl, 0.0, 0.0), (br, 0.0, 1.0), (tr, 1.0, 1.0), (tl, 1.0, 0.0)]
            u0, v0 = R.uniform(0, 0.75), R.uniform(0, 0.72)
            top, bot, uvs = [], [], []
            for p, q, fu in outline:
                o = base + t * 0.3 + (t * 0.7 + jl) * (1 - q)
                top.append(m.vert(p + N * o))
                bot.append(m.vert(p + N * (o - t)))
                uvs.append((u0 + fu * uvcell[0], v0 + q * uvcell[1]))
            m.face(top, uvs, mat)
            m.face(bot[::-1], uvs[::-1], mat)
            k = len(top)
            for i in range(k):
                j = (i + 1) % k
                m.face((bot[i], bot[j], top[j], top[i]), (uvs[i], uvs[j], uvs[j], uvs[i]), mat)


def deck(m, A, B, D, C, th, top_mat, under_mat):
    """Roof deck slab on the plane A-B-C-D, thickness th outward."""
    A, B, C, D = (Vector(v) for v in (A, B, C, D))
    N = (B - A).cross(D - A).normalized() * th
    lo = [m.vert(p) for p in (A, B, C, D)]
    hi = [m.vert(p + N) for p in (A, B, C, D)]
    m.face(hi, None, top_mat, 2.0)
    m.face(lo[::-1], None, under_mat, 2.0)
    for i in range(4):
        j = (i + 1) % 4
        m.face((lo[i], lo[j], hi[j], hi[i]), None, under_mat, 2.0)


def deck_tri(m, A, B, C, th, top_mat, under_mat):
    A, B, C = (Vector(v) for v in (A, B, C))
    N = (B - A).cross(C - A).normalized() * th
    lo = [m.vert(p) for p in (A, B, C)]
    hi = [m.vert(p + N) for p in (A, B, C)]
    m.face(hi, None, top_mat, 2.0)
    m.face(lo[::-1], None, under_mat, 2.0)
    for i in range(3):
        j = (i + 1) % 3
        m.face((lo[i], lo[j], hi[j], hi[i]), None, under_mat, 2.0)


# ---------- living details ----------

def clump(m, c, r, R, mat=LEAF):
    """Low mound of moss or leaves."""
    h = r * R.uniform(0.28, 0.45)
    lathe(m, c, [(r * 0.9, -0.01), (r, h * 0.3), (r * 0.7, h * 0.75), (r * 0.25, h)], 6, mat, a0=R.uniform(0, 6), sx=R.uniform(0.7, 1.3), rough=0.4, seed=R.uniform(0, 9))


def flowers(m, c, spread, n, R, up=(0, 1, 0)):
    c = Vector(c)
    for _ in range(n):
        p = c + Vector((R.uniform(-spread, spread), R.uniform(0, spread * 0.4), R.uniform(-spread, spread) * 0.6))
        s = R.uniform(0.03, 0.05)
        gem(m, p, s, s * 0.55, s, FLOWER if R.random() < 0.7 else PETAL, axis=up, spin=R.uniform(0, 3))


def leaves(m, pts, R, size=0.06, every=0.16):
    pts = [Vector(p) for p in pts]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        acc += (b - a).length
        if acc > every:
            acc = 0.0
            d = (b - a).normalized()
            side = d.cross(Vector((0, 0, 1))).normalized() * R.choice((-1, 1))
            gem(m, a + side * size * 0.8 + Vector((0, 0, 0.02)), size, size * 0.35, size * 0.7, LEAF, axis=side + Vector((0, 0, 0.6)), spin=R.uniform(0, 3))


def vine(m, start, length, R, drift=0.25, z=0.03):
    s = Vector(start)
    pts = [s]
    for i in range(1, 7):
        pts.append(s + Vector((math.sin(i * 1.3 + R.uniform(0, 1)) * drift * i / 6, -length * i / 6, z)))
    tube(m, pts, [0.018] * len(pts), LEAF, 3, caps=(False, True), cap_mat=LEAF)
    leaves(m, pts, R)


def veins(m, x0, x1, y0, y1, z, R, n=2):
    """Glowing crystal veins wandering across a stone face."""
    for _ in range(n):
        x, y = R.uniform(x0, x1), R.uniform(y0, y0 + (y1 - y0) * 0.4)
        pts = [(x, y)]
        for k in range(R.randint(4, 6)):
            x = min(x1, max(x0, x + R.uniform(-0.22, 0.22)))
            y = min(y1, y + R.uniform(0.12, 0.3))
            pts.append((x, y))
        ribbon(m, pts, 0.022, z, CRYSTAL)


def shards(m, c, R, n=3, scale=1.0, axis=(0, 0.6, 1)):
    c = Vector(c)
    for k in range(n):
        ax = Vector(axis) + Vector((R.uniform(-0.5, 0.5), R.uniform(-0.2, 0.4), 0))
        s = scale * R.uniform(0.6, 1.0)
        gem(m, c + Vector((R.uniform(-0.06, 0.06), R.uniform(-0.04, 0.04), 0)), 0.035 * s, 0.11 * s, 0.035 * s, CRYSTAL, axis=ax, spin=R.uniform(0, 3))


def flowerbox(P, x0, x1, y0, zb, depth, R, height=0.28):
    """Deadwood trough with soil, leaf mounds, flowers and trailing vines; back face at zb, projecting `depth`."""
    m = P.hard
    zf = zb + depth
    hbox(m, (x0, y0, zf - 0.05), (x1, y0 + height, zf), WOOD)
    hbox(P.flat, (x0, y0, zb), (x1, y0 + height, zb + 0.05), WOOD)
    hbox(P.flat, (x0, y0 - 0.02, zb), (x1, y0 + 0.04, zf), WOOD)
    for x in (x0, x1 - 0.05):
        vbox(P.flat, (x, y0 - 0.04, zb), (x + 0.05, y0 + height + 0.03, zf + 0.01), WOOD)
    box(P.flat, (x0 + 0.05, y0 + 0.03, zb + 0.05), (x1 - 0.05, y0 + height - 0.04, zf - 0.05), SOIL)
    n = max(2, round((x1 - x0) / 0.22))
    for k in range(n):
        x = x0 + (k + 0.5) * (x1 - x0) / n
        clump(P.soft, (x + R.uniform(-0.04, 0.04), y0 + height - 0.05, (zb + zf) / 2), R.uniform(0.11, 0.15), R)
        flowers(P.soft, (x, y0 + height + 0.06, (zb + zf) / 2), 0.08, 3, R)
    for k in range(max(1, n // 3)):
        vine(P.soft, (x0 + R.uniform(0.1, x1 - x0 - 0.1), y0 + height - 0.02, zf + 0.02), R.uniform(0.25, 0.45), R, 0.08, 0.0)


# ---------- piece context ----------

class Parts:
    """flat: hard-edged, no bevel (slabs that meet neighbours exactly); hard: bevelled detail; soft: smooth;
    cloth: smooth surfaces thickened by solidify."""

    def __init__(self):
        self.flat, self.hard, self.soft, self.cloth = Mesh(), Mesh(), Mesh(), Mesh()


def hand(ob, amp, size, pivot, scale=1.6, seed=0.0):
    """Handmade irregularity that leaves every vertex on the piece's snap planes untouched."""
    w, h, d = size
    if pivot == "bottom-left-front":
        planes = ((0, w), (0, d), (0, h))  # Blender x, y (= -glTF z), z
    else:
        planes = ((None, None), (None, None), (0, None))
    for v in ob.data.vertices:
        if any(lim is not None and abs(v.co[i] - lim) < 1e-4 for i, pair in enumerate(planes) for lim in pair):
            continue
        q = v.co * scale + Vector((seed, seed * 1.3, 0))
        v.co += Vector((noise.noise(q), noise.noise(q + Vector((7, 0, 0))), noise.noise(q + Vector((0, 13, 0))) * 0.6)) * amp


def finish(P, p, mats, seed, amp=0.018, bevel=0.022):
    obs = []
    if len(P.flat.bm.faces):
        obs.append(P.flat.object(p["id"] + ".flat", mats, seed=seed, smooth=False))
    if len(P.hard.bm.faces):
        ob = P.hard.object(p["id"] + ".hard", mats, seed=seed, smooth=False)
        if bevel:
            K.bevel(ob, bevel, 1, 35)
        hand(ob, amp, p["size"], p["pivot"], seed=seed)
        obs.append(ob)
    if len(P.soft.bm.faces):
        ob = P.soft.object(p["id"] + ".soft", mats, moss=None, seed=seed)
        hand(ob, amp * 0.6, p["size"], p["pivot"], seed=seed)
        obs.append(ob)
    if len(P.cloth.bm.faces):
        ob = P.cloth.object(p["id"] + ".cloth", mats, moss=None, seed=seed)
        B.solidify(ob, 0.018)
        obs.append(ob)
    return join(obs, p["id"])


# ---------- Anchorkin basalt ----------

def voussoirs(P, cx, spring, r, R, n=9, t=0.27, z0=-0.06, z1=0.07, key_gem=False, key_extra=0.1):
    for k in range(n):
        a0 = math.pi * k / n + 0.012
        a1 = math.pi * (k + 1) / n - 0.012
        key = k == n // 2
        ro = r + t + (key_extra if key else R.uniform(-0.03, 0.03))
        zz1 = z1 + (0.03 if key else R.uniform(-0.02, 0.01))
        pts = []
        for a in (a0, (a0 + a1) / 2, a1):
            pts.append((cx + math.cos(a) * r, spring + math.sin(a) * r))
        for a in (a1, a0):
            pts.append((cx + math.cos(a) * ro, spring + math.sin(a) * ro))
        pts = pts[::-1]  # anticlockwise
        extrude(P.hard, pts, z0, zz1, BLOCK, 1.2)
        if key and key_gem:
            ym = spring + r + (t + key_extra) * 0.55
            gem(P.soft, (cx, ym, zz1 + 0.02), 0.08, 0.13, 0.05, CRYSTAL)
            for s in (-1, 1):
                gem(P.soft, (cx + s * 0.07, ym, zz1 + 0.005), 0.018, 0.07, 0.015, BRASS)


def jambs(P, xl, xr, y0, y1, R, z1=0.06):
    y = y0
    k = 0
    while y < y1 - 0.12:
        hgt = min(y1 - y, 0.42 if k % 2 else 0.5)
        wide = 0.34 if k % 2 else 0.24
        hbox(P.hard, (xl - wide, y + 0.01, -0.06), (xl, y + hgt - 0.01, z1 + R.uniform(-0.015, 0.01)), BLOCK, 1.2)
        hbox(P.hard, (xr, y + 0.01, -0.06), (xr + wide, y + hgt - 0.01, z1 + R.uniform(-0.015, 0.01)), BLOCK, 1.2)
        y += hgt
        k += 1


def base_course(P, w, gaps, R, h=0.32, z1=0.06):
    """Proud base stones along the foot of a wall, interrupted by door/arch openings."""
    xs = [0.0]
    while xs[-1] < w - 0.05:
        xs.append(min(w, xs[-1] + R.uniform(0.45, 0.75)))
    for a, b in zip(xs, xs[1:]):
        for g0, g1 in gaps:
            if a < g1 and b > g0:
                if a < g0:
                    hbox(P.hard, (a + 0.01, 0, -0.06), (g0 - 0.01, h, z1), BLOCK, 1.2)
                if b > g1:
                    hbox(P.hard, (g1 + 0.01, 0, -0.06), (b - 0.01, h, z1), BLOCK, 1.2)
                break
        else:
            hbox(P.hard, (a + 0.01, 0, -0.06), (b - 0.01, h + R.uniform(-0.03, 0.02), z1), BLOCK, 1.2)


def basalt_wall(p, P, R):
    w, h, d = p["size"]
    o = p.get("opening")
    pid = p["id"]
    gaps = []
    if o:
        ow, oh = o["size"]
        ox, oy = o["offset"]
        cx, r = ox + ow / 2, ow / 2
        spring = oy + oh - r
        if oy > 0:
            box(P.flat, (0, 0, -d), (w, oy, 0), STONE, 2.0)
            hbox(P.hard, (ox - 0.1, oy - 0.1, -0.3), (ox + ow + 0.1, oy + 0.02, 0.1), BLOCK, 1.2)  # sill
        else:
            gaps.append((ox - 0.02, ox + ow + 0.02))
        extrude(P.flat, u_outline(w, h, oy, cx, arch(ow, oh, 12)), -d, 0, STONE, 2.0)
        voussoirs(P, cx, spring, r, R, key_gem=o["kind"] != "window")
        jambs(P, ox, ox + ow, max(oy + 0.02, 0.32) if oy == 0 else oy + 0.02, spring, R)
        shards(P.soft, (R.choice((0.22, w - 0.22)), 0.42, 0.04), R, 2, 0.9)
    else:
        bw, bh, by = 1.1, 2.3, 0.32
        cx = w / 2
        if "endcap" in pid:
            box(P.flat, (0, 0, -d), (w, h, 0), STONE, 2.0)
            # engaged piers at both ends and a chain swag between bronze rings
            for x0, x1 in ((0.0, 0.32), (w - 0.32, w)):
                y = 0.32
                k = 0
                while y < h - 0.05:
                    hh = min(h - y, 0.62 if k % 2 else 0.74)
                    hbox(P.hard, (x0 + 0.01, y + 0.01, -0.06), (x1 - 0.01, y + hh - 0.01, 0.08 + 0.02 * (k % 2)), BLOCK, 1.2)
                    y += hh
                    k += 1
            for x in (0.5, w - 0.5):
                vbox(P.hard, (x - 0.09, 2.08, -0.02), (x + 0.09, 2.26, 0.04), BRASS)
                loop(P.soft, [(x + 0.07 * math.cos(a), 2.05 + 0.07 * math.sin(a), 0.09) for a in (2 * math.pi * k / 8 for k in range(8))], 0.02, BRASS, 5)
            chain(P.soft, (0.5, 1.98, 0.1), (w - 0.5, 1.98, 0.1), BRASS, link=0.13, r=0.02, sag=0.45)
            shards(P.soft, (w / 2, 0.36, 0.05), R, 3)
        else:
            extrude(P.flat, u_outline(w, h, by, cx, arch(bw, bh, 12)), -d, 0, STONE, 2.0)
            box(P.flat, (0, 0, -d), (w, by, 0), STONE, 2.0)
            extrude(P.flat, [(cx + x, by + y) for x, y in arch(bw, bh, 12)], -d, -0.14, STONE, 2.0)  # blind niche
            voussoirs(P, cx, by + bh - bw / 2, bw / 2, R, n=9)
            shards(P.soft, (cx + 0.25, by + 0.08, -0.1), R, 3, 1.1)
    base_course(P, w, gaps, R)
    for x in (R.uniform(0.15, 0.4), R.uniform(w - 0.4, w - 0.15)):
        clump(P.soft, (x, 0.3, 0.02), R.uniform(0.12, 0.2), R)


def plinth(p, P, R, dock=False):
    w, h, d = p["size"]
    e = 0.02
    box(P.flat, (e, 0, -d), (w - e, h - 0.1, -0.12), STONE, 2.0)
    for y0, y1 in ((0, 0.46), (0.46, 0.9)):
        xs = [e]
        off = R.uniform(0.3, 0.6) if y0 else R.uniform(0.5, 0.9)
        xs.append(off)
        while xs[-1] < w - e - 0.2:
            xs.append(min(w - e, xs[-1] + R.uniform(0.5, 0.8)))
        xs[-1] = w - e
        for a, b in zip(xs, xs[1:]):
            hbox(P.hard, (a + 0.008, y0 + 0.008, -0.16), (b - 0.008, y1 - 0.008, -R.uniform(0, 0.02)), BLOCK, 1.3)
    hbox(P.hard, (e, h - 0.1, -d), (w - e, h, 0.02), BLOCK, 1.3)
    shards(P.soft, (R.uniform(0.3, w - 0.3), 0.46, 0.0), R, 2, 0.8)
    for _ in range(2):
        clump(P.soft, (R.uniform(0.2, w - 0.2), 0.0, 0.0), R.uniform(0.14, 0.22), R)
    if dock:
        vbox(P.hard, (w / 2 - 0.1, 0.6, -0.02), (w / 2 + 0.1, 0.8, 0.05), IRON)
        loop(P.soft, [(w / 2 + 0.2 * math.sin(a), 0.42 + 0.2 * math.cos(a), 0.11) for a in (2 * math.pi * k / 14 for k in range(14))], 0.035, IRON, 6)
        loop(P.soft, [(w / 2, 0.66 + 0.05 * math.sin(a), 0.07 + 0.05 * math.cos(a)) for a in (2 * math.pi * k / 6 for k in range(6))], 0.018, IRON, 4)
        for x in (0.3, w - 0.45):
            hbox(P.hard, (x, 0.5, 0.0), (x + 0.15, h + 0.03, 0.04), BRASS)
            hbox(P.hard, (x, h, -0.45), (x + 0.15, h + 0.03, 0.04), BRASS)
            for y in (0.62, 0.85):
                gem(P.soft, (x + 0.075, y, 0.045), 0.02, 0.02, 0.02, BRASS)


def slope_step(p, P, R):
    w, h, d = p["size"]
    n = 4
    run = d / n
    for k in range(n):
        hbox(P.hard, (0.16, k * h / n, -d), (w - 0.16, (k + 1) * h / n, -k * run + R.uniform(-0.02, 0.0)), BLOCK, 1.3)
    prof = [(0, 0), (0, 0.32), (-d + 0.3, h), (-d, h), (-d, 0)]
    for x0 in (0.0, w - 0.16):
        prism_x(P.hard, prof, x0, x0 + 0.16, BLOCK, 1.3)
    clump(P.soft, (0.12, 0.0, -0.1), 0.2, R)
    clump(P.soft, (w - 0.1, 0.25, -0.6), 0.16, R)
    shards(P.soft, (w - 0.08, 0.35, -0.4), R, 2, 0.8, axis=(1, 0.6, 0.3))


def stairs(p, P, R):
    w, h, d = p["size"]
    n = 12
    run = d / n
    for k in range(n):
        hbox(P.hard, (0.2, k * h / n, -d), (w - 0.2, (k + 1) * h / n, -k * run + R.uniform(-0.02, 0)), BLOCK, 1.3)
    prof = [(0, 0), (0, 0.45), (-d + 0.45, h + 0.15), (-d, h + 0.15), (-d, 0)]
    for x0 in (0.0, w - 0.2):
        prism_x(P.hard, prof, x0, x0 + 0.2, BLOCK, 1.5)
    for z, y in ((-1.2, 1.0), (-2.8, 2.2)):
        shards(P.soft, (w - 0.02, y, z), R, 2, 0.9, axis=(1, 0.5, 0))
        clump(P.soft, (0.1, y + 0.4, z), 0.15, R)
    clump(P.soft, (w - 0.1, 0, 0), 0.22, R)


def corner_post(p, P, R, inner=False):
    w, h, d = p["size"]
    sx = 1 if inner else -1  # which side face is exterior: -x (outer) or +x (inner)
    pr = 0.06
    box(P.flat, (0, 0, -d), (w, 1.6, 0), STONE, 2.0)
    y = 0.0
    k = 0
    while y < 1.55:
        hh = 0.42 if k % 2 else 0.38
        long_front = k % 2 == 0
        lx = 0.68 if long_front and not inner else w
        if sx < 0:
            x0, x1 = -pr, (lx if long_front else w + 0.0)
        else:
            x0, x1 = (0 if long_front else 0), w + pr
        z0 = -d if long_front else (-0.72 if not inner else -d)
        hbox(P.hard, (x0, y + 0.01, z0), (x1, min(y + hh, 1.6) - 0.01, pr), BLOCK, 1.2)
        y += hh
        k += 1
    gem(P.soft, (w / 2, 0.8, pr + 0.02), 0.07, 0.12, 0.04, CRYSTAL)
    lo_x, hi_x = (-0.05, w) if sx < 0 else (0, w + 0.05)
    vbox(P.hard, (lo_x, 1.6, -d), (hi_x, h, 0.05), WOOD, 2.0)
    hbox(P.hard, (lo_x - 0.03 * (sx < 0), 1.6, -d), (hi_x + 0.03 * (sx > 0), 1.74, 0.09), BRASS)
    hbox(P.hard, (lo_x - 0.03 * (sx < 0), h - 0.16, -d), (hi_x + 0.03 * (sx > 0), h, 0.09), WOOD)
    for y in (2.1, 2.55):
        gem(P.soft, (w / 2, y, 0.07), 0.035, 0.035, 0.03, BRASS)
    clump(P.soft, (w / 2, 1.74, 0.06), 0.16, R)
    flowers(P.soft, (w / 2, 1.8, 0.08), 0.08, 3, R)
    vine(P.soft, (w * 0.3, h - 0.18, 0.07), 0.6, R, 0.1, 0.0)


def corner_tower(p, P, R):
    w, h, d = p["size"]
    c = (w / 2, 0, -d / 2)
    r = p.get("radius", 1.0)
    sides = 16
    lathe(P.flat, c, [(r - 0.02, 0), (r - 0.02, 1.6), (0, 1.6)], sides, STONE, 2.0)
    lathe(P.flat, (c[0], 1.55, c[2]), [(r, 0), (r, 0.16)], sides, BLOCK, 1.0)
    lathe(P.flat, c, [(r, 0), (r, 0.3)], sides, BLOCK, 1.0)
    lathe(P.flat, (c[0], 1.71, c[2]), [(r - 0.1, 0), (r - 0.1, h - 1.71), (0, h - 1.71)], sides, PLASTER, 2.0)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        x, z = c[0] + math.cos(a) * (r - 0.06), c[2] - math.sin(a) * (r - 0.06)
        beam(P.hard, (x, 1.71, z), (x, h - 0.15, z), 0.14, 0.12, WOOD, up=(math.cos(a), 0, -math.sin(a)))
    lathe(P.flat, (c[0], h - 0.16, c[2]), [(r, 0), (r, 0.16)], sides, WOOD, 2.0)
    for a in (math.radians(90 - 22.5), math.radians(-22.5)):  # windows facing front and right
        dx, dz = math.cos(a), -math.sin(a)
        base = Vector((c[0] + dx * (r - 0.085), 2.0, c[2] + dz * (r - 0.085)))
        side = Vector((-dz, 0, dx))
        out = Vector((dx, 0, dz))
        shape = pointed_arch(0.42, 0.75, 6)
        pts = [base + side * x + Vector((0, y, 0)) for x, y in shape]
        P.soft.face([P.soft.vert(q + out * 0.012) for q in pts], [(x + 0.5, y) for x, y in shape], GLOW)
        tube(P.soft, [q + out * 0.035 for q in pts], [0.04] * len(pts), WOOD, 5, caps=(True, True))
    for k in range(5):
        a = R.uniform(0.2, 1.4) + (k % 2) * 4.7
        shards(P.soft, (c[0] + math.cos(a) * r, R.uniform(0.4, 1.3), c[2] - math.sin(a) * r), R, 2, 0.9, axis=(math.cos(a), 0.4, -math.sin(a)))
    for k in range(3):
        a = R.uniform(0, 2 * math.pi)
        clump(P.soft, (c[0] + math.cos(a) * r, 1.71, c[2] - math.sin(a) * r), 0.18, R)


def paving(p, P, R):
    w, h, d = p["size"]
    box(P.flat, (0, 0, -d), (w, h, 0), WOOD, 2.0, mats={"top": COBBLE})
    for _ in range(3):
        clump(P.soft, (R.uniform(0.2, w - 0.2), h, R.uniform(-d + 0.2, -0.2)), R.uniform(0.08, 0.13), R)


# ---------- Rootwarden deadwood framing ----------

def joint(P, x, y, R, z=0.02, moss=0.5):
    vbox(P.flat, (x - 0.09, y - 0.09, z - 0.03), (x + 0.09, y + 0.09, z + 0.01), BRASS)
    gem(P.soft, (x, y, z + 0.02), 0.035, 0.035, 0.03, BRASS, axis=(0, 0, 1))
    if R.random() < moss:
        clump(P.soft, (x + R.uniform(-0.1, 0.1), y + 0.05, z), R.uniform(0.1, 0.15), R)
        flowers(P.soft, (x, y + 0.1, z + 0.03), 0.08, R.randint(2, 4), R)


def timber_frame(P, w, h, d, R, pattern="x", opening=None, zf=0.0):
    """Deadwood frame (posts, sill, head, braces) proud of a recessed plaster infill; zf = frame front."""
    zb = zf - 0.32
    zp = zf - 0.12  # plaster face
    pw = 0.2
    if opening:
        (ow, oh), (ox, oy) = opening["size"], opening["offset"]
        shape = pointed_arch(ow, oh, 7)
        if oy > 0:
            box(P.flat, (0, 0, zf - d), (w, oy, zp), PLASTER, 2.0)
        extrude(P.flat, u_outline(w, h, oy, ox + ow / 2, shape), zf - d, zp, PLASTER, 2.0)
    else:
        box(P.flat, (0, 0, zf - d), (w, h, zp), PLASTER, 2.0)
    hbox(P.hard, (0, 0, zb), (w, 0.24, zf), WOOD)
    hbox(P.hard, (0, h - 0.24, zb), (w, h, zf), WOOD)
    for x0 in (0.0, w - pw):
        vbox(P.hard, (x0, 0.24, zb), (x0 + pw, h - 0.24, zf - 0.01), WOOD)
    zb2, zf2 = zb + 0.03, zf - 0.04
    y0, y1 = 0.24, h - 0.24
    pts_joints = [(pw / 2, 0.12), (w - pw / 2, 0.12), (pw / 2, h - 0.12), (w - pw / 2, h - 0.12)]
    if opening:
        (ow, oh), (ox, oy) = opening["size"], opening["offset"]
        for x0 in (ox - 0.16, ox + ow):
            vbox(P.hard, (x0, y0, zb2), (x0 + 0.16, y1, zf2), WOOD)
        if oy > 0:
            hbox(P.hard, (pw, oy - 0.16, zb2), (w - pw, oy, zf2 + 0.02), WOOD)
            for xa, xb in ((pw, ox - 0.16), (ox + ow + 0.16, w - pw)):
                beam(P.hard, (xa, y0 + 0.05, (zb2 + zf2) / 2), (xb, oy - 0.2, (zb2 + zf2) / 2), 0.13, zf2 - zb2, WOOD, up=(0, 0, 1))
            pts_joints += [(ox - 0.08, oy - 0.08), (ox + ow + 0.08, oy - 0.08)]
        shape = pointed_arch(ow + 0.16, oh + 0.1, 7)
        arc = [Vector((ox + ow / 2 + x, oy + y, zf2 - 0.08)) for x, y in shape[1:-1]]
        tube(P.soft, arc, [0.08] * len(arc), WOOD, 4, rough=0.0, caps=(True, True))
        top = oy + oh + 0.1
        for xa, xb in ((pw, ox - 0.16), (ox + ow + 0.16, w - pw)):
            beam(P.hard, (xa, y1 - 0.02, (zb2 + zf2) / 2), (xb, top - 0.25, (zb2 + zf2) / 2), 0.13, zf2 - zb2, WOOD, up=(0, 0, 1))
        vbox(P.hard, (ox + ow / 2 - 0.07, top - 0.05, zb2), (ox + ow / 2 + 0.07, y1, zf2), WOOD)
    elif pattern == "x":
        for a, b in (((pw, y0), (w - pw, y1)), ((pw, y1), (w - pw, y0))):
            beam(P.hard, (a[0], a[1], (zb2 + zf2) / 2), (b[0], b[1], (zb2 + zf2) / 2), 0.17, zf2 - zb2, WOOD, up=(0, 0, 1))
        pts_joints.append((w / 2, h / 2))
    elif pattern == "chevron":
        vbox(P.hard, (w / 2 - 0.08, y0, zb2), (w / 2 + 0.08, y1, zf2), WOOD)
        for k in range(3):
            yb = y0 + 0.15 + k * 0.82
            for s in (-1, 1):
                beam(P.hard, (w / 2 + s * (w / 2 - pw), yb, (zb2 + zf2) / 2), (w / 2 + s * 0.06, yb + 0.6, (zb2 + zf2) / 2), 0.13, zf2 - zb2 - 0.02, WOOD, up=(0, 0, 1))
        pts_joints.append((w / 2, h / 2))
    else:
        hbox(P.hard, (pw, h / 2 - 0.08, zb2), (w - pw, h / 2 + 0.08, zf2), WOOD)
        for s in (0, 1):
            x = pw if s == 0 else w - pw
            beam(P.hard, (x, y1 - 0.45, (zb2 + zf2) / 2), (x + (0.45 if s == 0 else -0.45), y1, (zb2 + zf2) / 2), 0.1, zf2 - zb2, WOOD, up=(0, 0, 1))
    for x, y in pts_joints:
        joint(P, x, y, R, zf + 0.02, 0.45)
    vine(P.soft, (R.uniform(0.3, w - 0.3), h - 0.2, zf + 0.03), R.uniform(0.5, 1.1), R, 0.2, 0.0)
    clump(P.soft, (R.uniform(0.3, w - 0.3), 0.24, zp + 0.05), 0.16, R)
    flowers(P.soft, (R.uniform(0.3, w - 0.3), 0.3, zp + 0.08), 0.1, 3, R)


def oriel(p, P, R):
    w, h, d = p["size"]
    zw = -(d - WALL)  # wall front plane (-1.0)
    timber_frame(P, w, h, WALL, R, "plain", zf=zw)
    zf = -0.14
    bl, br = (0.3, zw), (w - 0.3, zw)
    fl, fr = (0.6, zf), (w - 0.6, zf)
    y0, y1 = 0.85, 2.3
    # floor and head plates of the bay
    for ya, yb in ((y0 - 0.15, y0), (y1, y1 + 0.12)):
        pts = [(bl[0], ya, bl[1]), (fl[0] - 0.05, ya, fl[1] + 0.05), (fr[0] + 0.05, ya, fr[1] + 0.05), (br[0], ya, br[1])]
        poly_prism(P.hard, pts, (0, yb - ya, 0), WOOD)
    poly_prism(P.flat, [(bl[0], y0 - 0.5, bl[1]), (fl[0], y0 - 0.5, fl[1]), (fr[0], y0 - 0.5, fr[1]), (br[0], y0 - 0.5, br[1])], (0, 0.35, 0), PLASTER)
    corners = [bl, fl, fr, br]
    for (xa, za), (xb, zb) in zip(corners, corners[1:]):
        a, b = Vector((xa, 0, za)), Vector((xb, 0, zb))
        out = Vector((b.z - a.z, 0, -(b.x - a.x))).normalized()
        if out.dot((a + b) / 2 - Vector((w / 2, 0, (zw + zf) / 2))) < 0:
            out = -out
        n = 2 if (b - a).length > 0.6 else 1
        pane = [a.lerp(b, 0.04) + Vector((0, y0 + 0.08, 0)), b.lerp(a, 0.04) + Vector((0, y0 + 0.08, 0)),
                b.lerp(a, 0.04) + Vector((0, y1 - 0.05, 0)), a.lerp(b, 0.04) + Vector((0, y1 - 0.05, 0))]
        P.soft.face([P.soft.vert(q - out * 0.03) for q in pane], [(0, 0), (1, 0), (1, 1), (0, 1)], GLOW)
        for k in range(1, n):
            q = a.lerp(b, k / n)
            vbox(P.flat, (q.x - 0.04, y0, q.z - 0.04), (q.x + 0.04, y1, q.z + 0.04), WOOD)
        mid = a.lerp(b, 0.5)
        beam(P.flat, a + Vector((0, y0 + 0.55, 0)), b + Vector((0, y0 + 0.55, 0)), 0.05, 0.05, WOOD)
        # pointed heads over each light
        for k in range(n):
            pa, pb = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
            m_ = pa.lerp(pb, 0.5)
            tube(P.soft, [pa + Vector((0, y1 - 0.3, 0)), m_ + Vector((0, y1 - 0.05, 0)), pb + Vector((0, y1 - 0.3, 0))], [0.035] * 3, WOOD, 4)
    for x, z in corners:
        vbox(P.hard, (x - 0.06, y0 - 0.15, z - 0.06), (x + 0.06, y1 + 0.12, z + 0.06), WOOD)
    # corbel brackets under the bay
    for x in (0.55, w - 0.55):
        pts = hermite((x, 0.15, zw), (0, 0.4, 0.6), (x, y0 - 0.5, zf - 0.08), (0, 0.2, 1.0), 8)
        tube(P.soft, pts, [0.07 + 0.03 * (1 - i / 8) for i in range(9)], WOOD, 5)
    flowerbox(P, fl[0] - 0.05, fr[0] + 0.05, y0 - 0.14, zf - 0.02, 0.2, R, 0.22)
    # small terracotta hood
    ht, hb = y1 + 0.12, y1 + 0.7
    A, Bv = Vector((fl[0] - 0.12, ht, fl[1] + 0.12)), Vector((fr[0] + 0.12, ht, fr[1] + 0.12))
    D, C = Vector((0.75, hb, zw)), Vector((w - 0.75, hb, zw))
    BL, BR = Vector((bl[0] - 0.12, ht, zw)), Vector((br[0] + 0.12, ht, zw))
    deck(P.flat, A, Bv, D, C, 0.04, TILE, WOOD)
    deck_tri(P.flat, BL, A, D, 0.04, TILE, WOOD)
    deck_tri(P.flat, Bv, BR, C, 0.04, TILE, WOOD)
    tiles(P.flat, A, Bv, D, C, 3, 0.32, R, base=0.04, t=0.035)
    tiles(P.flat, BL, A, D, D, 2, 0.3, R, base=0.04, t=0.035)
    tiles(P.flat, Bv, BR, C, C, 2, 0.3, R, base=0.04, t=0.035)
    ball(P.soft, ((D.x + C.x) / 2, hb + 0.08, zw + 0.06), 0.06, BRASS)


# ---------- roofs ----------

EAVE = 0.35


def roof_run(p, P, R):
    w = p["size"][0]
    A, Bv, D, C = (0, -EAVE, EAVE), (w, -EAVE, EAVE), (0, 2, -2), (w, 2, -2)
    deck(P.flat, A, Bv, D, C, 0.06, TILE, WOOD)
    tiles(P.flat, A, Bv, D, C, 6, 0.45, R, base=0.06)
    beam(P.hard, (0, -EAVE - 0.06, EAVE + 0.02), (w, -EAVE - 0.06, EAVE + 0.02), 0.05, 0.16, WOOD)
    for x in (0.5, 1.5):
        beam(P.hard, (x, 0.24, -0.3), (x, -0.36, 0.3), 0.1, 0.12, WOOD, up=(0, 1, 1))
    if R.random() < 0.7:
        clump(P.soft, (R.uniform(0.3, w - 0.3), 0.9, -0.95), 0.18, R)


def roof_hip(p, P, R):
    e = EAVE
    apex = Vector((2, 2, -2))
    deck_tri(P.flat, (-e, -e, e), (2, -e, e), apex, 0.06, TILE, WOOD)
    deck_tri(P.flat, (-e, -e, -2), (-e, -e, e), apex, 0.06, TILE, WOOD)
    tiles(P.flat, (-e, -e, e), (2, -e, e), apex, apex, 6, 0.45, R, base=0.06)
    tiles(P.flat, (-e, -e, -2), (-e, -e, e), apex, apex, 6, 0.45, R, base=0.06)
    a = Vector((-e, -e + 0.12, e))
    pts = [a.lerp(apex + Vector((0, 0.12, 0)), i / 6) for i in range(7)]
    tube(P.soft, pts, [0.11] * 7, TILE, 8, cap_mat=TILE, tile=0.5)
    lathe(P.soft, apex + Vector((0, 0.1, 0)), [(0.1, 0), (0.06, 0.15), (0.11, 0.25), (0.08, 0.35), (0, 0.5)], 8, BRASS)


def ridge(p, P, R):
    w = p["size"][0]
    n = 4
    for k in range(n):
        x0, x1 = w * k / n, w * (k + 1) / n + 0.06
        x1 = min(x1, w)
        pts = [Vector((x, 0.08, -0.25)) for x in (x0, (x0 + x1) / 2, x1)]
        tube(P.soft, pts, [0.2, 0.185, 0.17], TILE, 8, cap_mat=TILE, tile=0.6, flat=0.75)
    lathe(P.soft, (0.0, 0.2, -0.25), [(0.07, 0), (0.05, 0.08)], 8, BRASS)
    ball(P.soft, (0.0, 0.38, -0.25), 0.11, BRASS)


def gable(p, P, R):
    w, h, d = p["size"]  # 2, 2, 0.5; low at x=0, ridge at x=w
    zc = -d / 2
    prism = [(0.02, 0.0), (w, 0.0), (w, h - 0.06)]
    extrude(P.flat, prism, zc - 0.08, zc + 0.08, PLASTER, 2.0)
    for zf in (0.0, -d + 0.14):  # truss on both faces: the mirrored half shows its back outward
        z0, z1 = zf - 0.14, zf
        hbox(P.hard, (0, 0, z0), (w, 0.2, z1), WOOD)
        beam(P.hard, (0.0, -0.14, (z0 + z1) / 2), (w, h - 0.14, (z0 + z1) / 2), 0.2, z1 - z0, WOOD, up=(0, 0, 1))
        vbox(P.hard, (w - 0.1, 0.2, z0), (w, h - 0.2, z1), WOOD)
        beam(P.hard, (w - 0.1, 0.25, (z0 + z1) / 2), (0.75, 0.62, (z0 + z1) / 2), 0.13, z1 - z0 - 0.02, WOOD, up=(0, 0, 1))
        if zf == 0.0:
            pts = hermite((w - 0.1, 1.0, (z0 + z1) / 2), (-0.6, -0.3, 0), (1.05, 0.95, (z0 + z1) / 2), (-0.2, 0.5, 0), 5)
            tube(P.soft, pts, [0.06] * 6, WOOD, 4)
        # bargeboard: verge above the tile ends
        zb = z1 + 0.08 if zf == 0.0 else z0 - 0.08
        beam(P.hard, (-EAVE - 0.05, -EAVE + 0.05, (z1 + zb) / 2 if zf == 0 else (z0 + zb) / 2), (w, h + 0.05, (z1 + zb) / 2 if zf == 0 else (z0 + zb) / 2), 0.24, 0.08, WOOD, up=(0, 0, 1))
        joint(P, w - 0.05, 0.1, R, z1 + 0.01 if zf == 0 else z0 - 0.05, 0.6)
        clump(P.soft, (0.9, 0.2, (z0 + z1) / 2 + (0.08 if zf == 0 else -0.08)), 0.15, R)
        flowers(P.soft, (0.8, 0.3, (z0 + z1) / 2), 0.1, 3, R)
    lathe(P.soft, (w, h - 0.02, zc), [(0.09, 0), (0.06, 0.12), (0.1, 0.22), (0.05, 0.3), (0.025, 0.55), (0, 0.62)], 8, BRASS)
    vine(P.soft, (0.6, 0.6, 0.09), 0.5, R, 0.1, 0.0)


def dormer(p, P, R):
    zf = -0.42
    x0, x1 = 0.42, 1.58
    ye, yr = 1.32, 1.92
    box(P.flat, (x0, 0.25, -1.4), (x1, ye, zf - 0.08), PLASTER, 2.0)
    for xa in (x0, x1 - 0.12):
        vbox(P.hard, (xa, 0.3, zf - 0.12), (xa + 0.12, ye, zf), WOOD)
    hbox(P.hard, (x0, ye - 0.1, zf - 0.12), (x1, ye + 0.02, zf + 0.01), WOOD)
    hbox(P.hard, (x0 - 0.04, 0.42, zf - 0.12), (x1 + 0.04, 0.54, zf + 0.04), WOOD)
    extrude(P.flat, [(x0, ye), (x1, ye), (1.0, yr - 0.06)], -1.6, zf - 0.08, PLASTER, 2.0)
    shape = arch(0.6, 0.74, 8)
    win = [(1.0 + x, 0.55 + y) for x, y in shape]
    fill(P.soft, win, zf - 0.07, GLOW)
    tube(P.soft, [Vector((x, y, zf - 0.04)) for x, y in win[1:-1]], [0.05] * (len(win) - 2), WOOD, 4)
    vbox(P.hard, (0.98, 0.55, zf - 0.08), (1.02, 1.2, zf - 0.04), WOOD)
    hbox(P.hard, (0.7, 0.88, zf - 0.08), (1.3, 0.92, zf - 0.04), WOOD)
    # cheeks
    for xa in (x0, x1 - 0.08):
        prism_x(P.flat, [(zf - 0.08, 0.3), (zf - 0.08, ye), (-1.32, ye), (-1.32, 1.2)], xa, xa + 0.08, PLASTER)
    zt = zf + 0.2
    Ld = [(x0 - 0.14, ye - 0.05, -1.9), (x0 - 0.14, ye - 0.05, zt), (1.0, yr, -1.9), (1.0, yr, zt)]
    Rd = [(x1 + 0.14, ye - 0.05, zt), (x1 + 0.14, ye - 0.05, -1.9), (1.0, yr, zt), (1.0, yr, -1.9)]
    for A, Bv, D, C in (Ld, Rd):
        deck(P.flat, A, Bv, D, C, 0.05, TILE, WOOD)
        tiles(P.flat, A, Bv, D, C, 3, 0.36, R, base=0.05, t=0.04)
    tube(P.soft, [Vector((1.0, yr + 0.08, z)) for z in (zt + 0.02, (zt - 1.9) / 2, -1.9)], [0.1] * 3, TILE, 8, cap_mat=TILE, flat=0.75, tile=0.6)
    for s in (-1, 1):
        beam(P.hard, (1.0 + s * (1.0 - x0 + 0.16), ye - 0.1, zt + 0.06), (1.0, yr + 0.02, zt + 0.06), 0.18, 0.07, WOOD, up=(0, 0, 1))
    lathe(P.soft, (1.0, yr + 0.06, zt + 0.08), [(0.06, 0), (0.04, 0.1), (0.07, 0.18), (0, 0.38)], 8, BRASS)


def stepped_cone(m, c, r0, r1, y0, y1, courses, sides, mat, R, flare=0.08, tile=1.0):
    """Cone of overlapping courses (tile or slate rows) with a flared foot."""
    prof = []
    for i in range(courses):
        t0, t1 = i / courses, (i + 1) / courses
        ra = r0 + (r1 - r0) * t0 + (flare if i == 0 else 0.0)
        rb = r0 + (r1 - r0) * t1
        ya, yb = y0 + (y1 - y0) * t0, y0 + (y1 - y0) * t1
        prof += [(max(ra - 0.04, 0.02), ya - 0.03), (ra + 0.04, ya), (rb, yb - 0.02)]
    prof.append((0, y1))
    lathe(m, c, prof, sides, mat, tile)


def spire(p, P, R):
    w, h, d = p["size"]
    c = Vector((w / 2, 0, -d / 2))
    box(P.hard, (0.45, 0.0, -d + 0.45), (w - 0.45, 0.47, -0.45), BLOCK, 1.5)
    s = 0.62
    box(P.flat, (c.x - s + 0.06, 0.2, c.z - s + 0.06), (c.x + s - 0.06, 1.75, c.z + s - 0.06), PLASTER, 2.0)
    for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, z = c.x + dx * s, c.z + dz * s
        vbox(P.hard, (x - 0.09, 0.2, z - 0.09), (x + 0.09, 1.75, z + 0.09), WOOD)
        lathe(P.soft, (x, 1.83, z), [(0.1, 0), (0.1, 0.06), (0.07, 0.1), (0, 0.6)], 4, SLATE, 0.5, a0=math.pi / 4)
        ball(P.soft, (x, 2.45, z), 0.04, BRASS, 6)
    hbox(P.hard, (c.x - s - 0.1, 1.73, c.z - s - 0.1), (c.x + s + 0.1, 1.86, c.z + s + 0.1), WOOD)
    for k in range(4):  # a lit pointed window on each face
        a = k * math.pi / 2
        out = Vector((math.sin(a), 0, math.cos(a)))
        side = Vector((math.cos(a), 0, -math.sin(a)))
        shape = pointed_arch(0.34, 0.78, 6)
        base = c + out * (s - 0.055) + Vector((0, 0.72, 0))
        pts = [base + side * x + Vector((0, y, 0)) for x, y in shape]
        P.soft.face([P.soft.vert(q) for q in pts], [(x + 0.5, y) for x, y in shape], GLOW)
        tube(P.soft, [q + out * 0.03 for q in pts], [0.035] * len(pts), WOOD, 4)
    stepped_cone(P.soft, (c.x, 0, c.z), 0.78, 0.02, 1.86, 5.45, 7, 8, SLATE, R, 0.06, 0.8)
    for k in range(8):
        a = 2 * math.pi * k / 8
        pts = [Vector((c.x + math.cos(a) * (0.82 * (1 - t) + 0.03), 1.86 + 3.55 * t, c.z - math.sin(a) * (0.82 * (1 - t) + 0.03))) for t in (0, 0.33, 0.66, 0.95)]
        tube(P.soft, pts, [0.03, 0.026, 0.02, 0.012], BRASS, 4, cap_mat=BRASS)
    lathe(P.soft, (c.x, 5.4, c.z), [(0.06, 0), (0.04, 0.1)], 6, BRASS)
    ball(P.soft, (c.x, 5.6, c.z), 0.1, BRASS)
    lathe(P.soft, (c.x, 5.68, c.z), [(0.03, 0), (0, 0.32)], 6, BRASS)
    for x, z in ((0.3, -0.25), (w - 0.3, -d + 0.3)):
        clump(P.soft, (x, 0.45, z), 0.18, R)
        flowers(P.soft, (x, 0.52, z), 0.1, 4, R)


def cupola(p, P, R):
    w, h, d = p["size"]
    c = (w / 2, 0, -d / 2)
    lathe(P.flat, c, [(0.92, 0), (0.92, 1.25), (0, 1.25)], 8, STONE, 2.0, a0=math.pi / 8)
    lathe(P.flat, (c[0], 1.2, c[2]), [(0.98, 0), (0.98, 0.12)], 8, BLOCK, 1.0, a0=math.pi / 8)
    lathe(P.flat, c, [(0.97, 0), (0.97, 0.16)], 8, STONE, 1.0, a0=math.pi / 8)
    for k in range(8):
        a = 2 * math.pi * k / 8
        x, z = c[0] + math.cos(a) * 0.78, c[2] - math.sin(a) * 0.78
        lathe(P.soft, (x, 1.32, z), [(0.1, 0), (0.1, 0.1), (0.065, 0.16), (0.06, 0.98), (0.1, 1.06), (0.1, 1.13)], 6, PLASTER, 1.0)
        ao = a + math.pi / 8
        xo, zo = c[0] + math.cos(ao) * 0.93, c[2] - math.sin(ao) * 0.93
        gem(P.soft, (xo, 0.95, zo), 0.06, 0.1, 0.03, CRYSTAL, axis=(0, 1, 0), spin=ao)
    lathe(P.flat, (c[0], 2.45, c[2]), [(0.94, 0), (0.94, 0.2)], 16, PLASTER, 1.0)
    lathe(P.flat, (c[0], 2.63, c[2]), [(0.99, 0), (0.99, 0.05)], 16, BRASS, 1.0)
    prof = [(1.02, 0.0), (1.0, 0.06), (0.93, 0.17), (0.82, 0.34), (0.66, 0.52), (0.46, 0.69), (0.26, 0.83), (0.12, 0.93), (0.05, 0.98)]
    lathe(P.soft, (c[0], 2.68, c[2]), prof, 16, SLATE, 0.8)
    for k in range(8):
        a = 2 * math.pi * k / 8
        pts = [Vector((c[0] + math.cos(a) * (r + 0.015), 2.68 + y, c[2] - math.sin(a) * (r + 0.015))) for r, y in prof[1:]]
        tube(P.soft, pts, [0.028] * len(pts), BRASS, 4, cap_mat=BRASS)
    lathe(P.soft, (c[0], 3.62, c[2]), [(0.08, 0), (0.05, 0.08)], 8, BRASS)
    ball(P.soft, (c[0], 3.76, c[2]), 0.1, BRASS)
    lathe(P.soft, (c[0], 3.84, c[2]), [(0.03, 0), (0, 0.16)], 6, BRASS)
    chain(P.soft, (c[0], 2.45, c[2]), (c[0], 2.2, c[2]), BRASS, 0.09, 0.012)
    lathe(P.soft, (c[0], 1.55, c[2]), [(0, 0), (0.15, 0.24), (0.13, 0.44), (0, 0.64)], 6, CRYSTAL)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.5
        clump(P.soft, (c[0] + math.cos(a) * 0.93, 1.32, c[2] - math.sin(a) * 0.93), 0.17, R)
        flowers(P.soft, (c[0] + math.cos(a) * 0.95, 1.4, c[2] - math.sin(a) * 0.95), 0.1, 3, R)
        vine(P.soft, (c[0] + math.cos(a + 0.4) * 0.97, 1.3, c[2] - math.sin(a + 0.4) * 0.97), 0.45, R, 0.08, 0.0)


def tower_cap(p, P, R):
    w, h, d = p["size"]
    c = (w / 2, 0, -d / 2)
    lathe(P.flat, c, [(0.94, 0), (0.94, 0.35), (0, 0.35)], 12, STONE, 2.0)
    lathe(P.flat, (c[0], 0.3, c[2]), [(0.98, 0), (0.98, 0.1)], 12, BLOCK, 1.0)
    lathe(P.flat, (c[0], 0.4, c[2]), [(0.8, 0), (0.8, 1.15), (0, 1.15)], 12, PLASTER, 2.0)
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        x, z = c[0] + math.cos(a) * 0.83, c[2] - math.sin(a) * 0.83
        beam(P.hard, (x, 0.4, z), (x, 1.55, z), 0.13, 0.1, WOOD, up=(math.cos(a), 0, -math.sin(a)))
    lathe(P.flat, (c[0], 1.48, c[2]), [(0.88, 0), (0.88, 0.12)], 12, WOOD, 2.0)
    for a in (math.pi / 2, 0.0, math.pi, math.pi * 1.5):
        out = Vector((math.cos(a), 0, -math.sin(a)))
        side = Vector((math.sin(a), 0, math.cos(a)))
        shape = pointed_arch(0.36, 0.72, 6)
        base = Vector(c) + out * 0.81 + Vector((0, 0.6, 0))
        pts = [base + side * x + Vector((0, y, 0)) for x, y in shape]
        P.soft.face([P.soft.vert(q) for q in pts], [(x + 0.5, y) for x, y in shape], GLOW)
        tube(P.soft, [q + out * 0.03 for q in pts], [0.035] * len(pts), WOOD, 4)
    stepped_cone(P.soft, c, 1.0, 0.02, 1.58, 3.12, 6, 12, TILE, R, 0.1, 1.0)
    lathe(P.soft, (c[0], 3.05, c[2]), [(0.06, 0), (0.04, 0.12)], 8, BRASS)
    ball(P.soft, (c[0], 3.24, c[2]), 0.08, BRASS)
    lathe(P.soft, (c[0], 3.3, c[2]), [(0.025, 0), (0, 0.2)], 6, BRASS)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        clump(P.soft, (c[0] + math.cos(a) * 0.9, 0.38, c[2] - math.sin(a) * 0.9), 0.17, R)
        flowers(P.soft, (c[0] + math.cos(a) * 0.95, 0.45, c[2] - math.sin(a) * 0.95), 0.1, 3, R)


# ---------- Galeborne cloth ----------

def scallops(P, x0, x1, ytop, z, depth, n, R, zfn=None):
    """Teal scalloped valance with a brass edge."""
    def fn(u, v):
        x = x0 + (x1 - x0) * u
        lobe = abs(math.sin(math.pi * n * u))
        y = ytop - v * depth * (0.55 + 0.45 * lobe)
        zz = z + (zfn(u) if zfn else 0) + 0.015 * math.sin(u * 9)
        return Vector((x, y, zz))
    surface(P.cloth, fn, n * 3, 2, TEAL)
    edge = [fn(i / (n * 3), 1.0) + Vector((0, 0, 0.012)) for i in range(n * 3 + 1)]
    tube(P.soft, edge, [0.016] * len(edge), BRASS, 4, cap_mat=BRASS)


def awning(p, P, R):
    w, h, d = p["size"]
    zb = -d
    hbox(P.hard, (0, h - 0.2, zb), (w, h, zb + 0.16), WOOD)
    for x in (0.0, w - 0.03):
        vbox(P.flat, (x, h - 0.22, zb + 0.16), (x + 0.03, h + 0.02, zb + 0.18), BRASS)
    for x in (0.12, w - 0.12):
        beam(P.hard, (x, h - 0.15, zb + 0.1), (x, 1.0, -0.1), 0.09, 0.09, WOOD)
        beam(P.hard, (x, 0.2, zb + 0.05), (x, 0.95, -0.55), 0.08, 0.08, WOOD)
        tube(P.soft, [Vector((x, 0.97, -0.1)), Vector((x, 0.85, -0.08)), Vector((x, 0.75, -0.08))], [0.012] * 3, BRASS, 4, cap_mat=BRASS)
        lathe(P.soft, (x, 0.58, -0.08), [(0, 0), (0.04, 0.05), (0.025, 0.17), (0, 0.18)], 6, BRASS)
    hbox(P.hard, (0.05, 0.94, -0.16), (w - 0.05, 1.04, -0.06), WOOD)

    def cloth(u, v):
        x = 0.12 + (w - 0.24) * u
        y = (h - 0.12) + (1.06 - (h - 0.12)) * v - 0.14 * math.sin(math.pi * u) * (0.25 + 0.75 * v)
        z = (zb + 0.14) + (-0.08 - (zb + 0.14)) * v
        return Vector((x, y + 0.012 * math.sin(u * 23), z))
    surface(P.cloth, cloth, 10, 6, SAIL, lambda u, v: (0.04 + u * 0.72, 0.1 + v * 0.7))
    scallops(P, 0.08, w - 0.08, 1.05, -0.06, 0.32, 5, R)
    for k in range(3):
        u = (k + 0.5) / 3
        q = cloth(u, 0.0)
        q2 = cloth(u, 1.0)
        tube(P.soft, [q + Vector((0, 0.025, 0)), q.lerp(q2, 0.5) + Vector((0, 0.03, 0)), q2 + Vector((0, 0.02, 0))], [0.01] * 3, SAIL, 4, cap_mat=SAIL)


def canopy(p, P, R):
    w, h, d = p["size"]
    s = w / 2 - 0.25
    posts = [(-s, -s), (s, -s), (s, s), (-s, s)]
    for x, z in posts:
        box(P.hard, (x - 0.22, 0, z - 0.22), (x + 0.22, 0.25, z + 0.22), STONE, 1.0)
        vbox(P.hard, (x - 0.09, 0.25, z - 0.09), (x + 0.09, h - 0.35, z + 0.09), WOOD)
        lathe(P.soft, (x, h - 0.4, z), [(0.12, 0), (0.12, 0.1), (0.08, 0.14)], 8, BRASS)
        ball(P.soft, (x, h - 0.12, z), 0.09, BRASS)
        lathe(P.soft, (x, h - 0.06, z), [(0.03, 0), (0, 0.06 + 0.0)], 6, BRASS)
        clump(P.soft, (x + 0.2, 0.25, z), 0.16, R)
    for z in (-s, s):
        hbox(P.hard, (-s, h - 0.62, z - 0.06), (s, h - 0.5, z + 0.06), WOOD)
    ridge_y, eave_y = h - 0.18, h - 0.62

    def cloth(u, v):
        x = -s - 0.05 + (2 * s + 0.1) * u
        z = -s - 0.08 + (2 * s + 0.16) * v
        y = eave_y + (ridge_y - eave_y) * (1 - abs(2 * v - 1)) ** 0.9 - 0.16 * math.sin(math.pi * u) * (1 - 0.6 * (1 - abs(2 * v - 1)))
        return Vector((x, y + 0.01 * math.sin(v * 17), z))
    surface(P.cloth, cloth, 8, 8, SAIL, lambda u, v: (0.03 + u * 0.75, 0.05 + v * 0.75))
    for zz, sgn in ((s + 0.08, 1), (-s - 0.08, -1)):
        scallops(P, -s - 0.05, s + 0.05, eave_y, zz, 0.3, 6, R, zfn=lambda u, sgn=sgn: 0.0)
    # banners on the front posts and lanterns on the front beam
    for sx in (-1, 1):
        x = sx * (s + 0.13)
        hbox(P.hard, (x - 0.03, h - 0.72, s - 0.22), (x + 0.03, h - 0.67, s + 0.22), BRASS)

        def bn(u, v, x=x):
            zz = s - 0.2 + 0.4 * u
            y = (h - 0.72) - 1.25 * v - 0.18 * (1 - abs(2 * u - 1)) * (v > 0.85) * (v - 0.85) / 0.15 * -1
            return Vector((x + 0.02 * math.sin(v * 6), y, zz))
        surface(P.cloth, bn, 3, 6, BANNER, lambda u, v: (u, 1 - v))
    for x in (-0.9, 0.9):
        chain(P.soft, (x, h - 0.62, s), (x, h - 0.95, s), IRON, 0.09, 0.012)
        lantern(P, (x, h - 1.6, s), R)


# ---------- inserts ----------

def planks(P, shape, x0, x1, n, z0, z1, mat=TWOOD):
    """Vertical planks filling an outline (left to right), each clipped to the outline's top."""
    for k in range(n):
        a = x0 + (x1 - x0) * k / n + 0.006
        b = x0 + (x1 - x0) * (k + 1) / n - 0.006
        tops = []
        for i in range(4):
            x = a + (b - a) * i / 3
            y = max((yy for xx, yy in densify(shape) if abs(xx - x) < (x1 - x0) / 40), default=0)
            tops.append((x, y))
        pts = [(a, 0.0), (b, 0.0)] + tops[::-1]
        extrude(P.flat, pts, z0, z1 + 0.006 * (k % 2), mat, 1.0)


def densify(shape, step=0.01):
    out = []
    for (xa, ya), (xb, yb) in zip(shape, shape[1:]):
        n = max(1, int(math.hypot(xb - xa, yb - ya) / step))
        out += [(xa + (xb - xa) * i / n, ya + (yb - ya) * i / n) for i in range(n)]
    return out + [shape[-1]]


def door_leaf(P, w, h, pointed, R, z0=-0.34, z1=-0.22):
    shape = pointed_arch(w - 0.04, h - 0.03, 8) if pointed else arch(w - 0.04, h - 0.03, 12)
    shape = [(x + w / 2, y) for x, y in shape]
    planks(P, shape, 0.02, w - 0.02, 5, z0, z1)
    for y in (0.5, 1.7):
        hbox(P.flat, (0.06, y, z1), (w * 0.82, y + 0.08, z1 + 0.03), IRON)
        gem(P.soft, (w * 0.82 + 0.05, y + 0.04, z1 + 0.015), 0.07, 0.04, 0.02, IRON, axis=(0, 0, 1))
        for x in (0.15, 0.35, 0.55):
            gem(P.soft, (x, y + 0.04, z1 + 0.035), 0.018, 0.018, 0.018, BRASS)
    loop(P.soft, [(w * 0.7 + 0.11 * math.sin(a), 1.12 + 0.11 * math.cos(a), z1 + 0.05) for a in (2 * math.pi * k / 10 for k in range(10))], 0.018, BRASS, 5)
    vbox(P.hard, (w * 0.7 - 0.05, 1.2, z1), (w * 0.7 + 0.05, 1.3, z1 + 0.05), BRASS)
    hbox(P.hard, (-0.02, -0.02, z0 - 0.1), (w + 0.02, 0.06, 0.04), STONE if not pointed else WOOD)


def market_door(p, P, R):
    w, h, d = p["size"]
    ow, oh = 2.6, 2.75
    cx = w / 2
    r = ow / 2
    spring = oh - r
    extrude(P.flat, u_outline(w, h, 0, cx, arch(ow, oh, 16)), -d, 0, STONE, 2.0)
    voussoirs(P, cx, spring, r, R, n=11, t=0.3, key_gem=True, key_extra=0.12)
    jambs(P, cx - r, cx + r, 0.32, spring, R)
    base_course(P, w, [(cx - r - 0.02, cx + r + 0.02)], R)
    shape = [(x + cx, y) for x, y in arch(ow - 0.04, oh - 0.03, 16)]
    for side in (0, 1):
        a, b = (cx - r + 0.02, cx - 0.01) if side == 0 else (cx + 0.01, cx + r - 0.02)
        planks(P, shape, a, b, 4, -0.34, -0.22)
        rx = cx + (-0.25 if side == 0 else 0.25)
        loop(P.soft, [(rx + 0.12 * math.sin(t), 1.2 + 0.12 * math.cos(t), -0.17) for t in (2 * math.pi * k / 10 for k in range(10))], 0.02, BRASS, 5)
        # gilded tree: trunk beside the meeting stiles, branches rising outward with leaf studs
        sg = -1 if side == 0 else 1
        trunk = [Vector((cx + sg * 0.1, y, -0.19)) for y in (0.3, 1.0, 1.7, 2.3)]
        tube(P.soft, trunk, [0.04, 0.034, 0.028, 0.02], BRASS, 4, cap_mat=BRASS)
        for k, (y, ln) in enumerate(((0.95, 0.75), (1.35, 0.65), (1.75, 0.5), (2.1, 0.32))):
            a = Vector((cx + sg * 0.1, y, -0.19))
            b = a + Vector((sg * ln * 0.55, ln * 0.35, 0))
            c2 = a + Vector((sg * ln, ln * 0.62, 0))
            tube(P.soft, [a, b, c2], [0.024, 0.018, 0.012], BRASS, 3, cap_mat=BRASS)
            for q in (a.lerp(b, 0.6), b, b.lerp(c2, 0.6), c2):
                gem(P.soft, q + Vector((0, 0.05, 0.01)), 0.04, 0.025, 0.015, BRASS, axis=(sg * 0.5, 1, 0.2))
    vbox(P.hard, (cx - 0.02, 0, -0.36), (cx + 0.02, spring + r - 0.02, -0.18), BRASS)
    hbox(P.hard, (cx - r, -0.0, -d), (cx + r, 0.06, 0.04), STONE)
    # finial posts, sailcloth swag and banners
    for x in (0.18, w - 0.18):
        lathe(P.soft, (x, 2.1, 0.12), [(0.05, 0), (0.045, 1.2)], 6, BRASS)
        vbox(P.hard, (x - 0.06, 2.3, -0.02), (x + 0.06, 2.42, 0.12), BRASS)
        ball(P.soft, (x, 3.38, 0.12), 0.08, BRASS)
        lathe(P.soft, (x, 3.44, 0.12), [(0.025, 0), (0, 0.2)], 6, BRASS)

        def bn(u, v, x=x):
            return Vector((x - 0.22 + 0.44 * u, 3.0 - 1.55 * v + 0.2 * (v > 0.9) * (1 - abs(2 * u - 1)) * (v - 0.9) * 10, 0.2 + 0.02 * math.sin(v * 7)))
        surface(P.cloth, bn, 2, 5, BANNER, lambda u, v: (u, 1 - v))
        hbox(P.flat, (x - 0.27, 2.99, 0.17), (x + 0.27, 3.04, 0.23), BRASS)

    def swag(u, v):
        x = 0.3 + (w - 0.6) * u
        y = 3.22 - 0.5 * math.sin(math.pi * u) * (0.35 + 0.65 * v) - 0.08 * v
        return Vector((x, y + 0.02 * math.sin(u * 30), 0.14 + 0.12 * v * math.sin(math.pi * u)))
    surface(P.cloth, swag, 10, 2, SAIL, lambda u, v: (0.03 + u * 0.75, 0.3 + v * 0.3))


def leaded_window(p, P, R):
    w, h, d = p["size"]
    shape = [(x + w / 2, y) for x, y in arch(w - 0.02, h - 0.02, 12)]
    fill(P.soft, shape, -0.3, GLOW)
    z = -0.27
    for sgn in (1, -1):
        for c in [k * 0.24 for k in range(-6, 8)]:
            pts = []
            for i in range(41):
                x = i / 40 * w
                y = c + sgn * (x - w / 2) * 1.3 + h / 2 - 0.4
                if inside((x, y), shape):
                    pts.append((x, y))
            if len(pts) >= 2:
                beam(P.flat, (pts[0][0], pts[0][1], z), (pts[-1][0], pts[-1][1], z), 0.022, 0.02, IRON, up=(0, 0, 1))
    tube(P.soft, [Vector((x, y, z + 0.01)) for x, y in shape[1:-1]], [0.045] * (len(shape) - 2), WOOD, 4)
    vbox(P.hard, (w / 2 - 0.03, 0, z - 0.02), (w / 2 + 0.03, h - 0.06, z + 0.03), WOOD)
    shards(P.soft, (0.12, 0.05, 0.02), R, 2, 0.7)


def timber_window(p, P, R, flowerbox_too=False):
    w, h, d = p["size"]
    shape = [(x + w / 2, y) for x, y in pointed_arch(w - 0.04, h - 0.03, 7)]
    fill(P.soft, shape, -0.28, GLOW)
    z = -0.25
    vbox(P.hard, (w / 2 - 0.035, 0.02, z - 0.03), (w / 2 + 0.035, h - 0.08, z + 0.03), WOOD)
    hbox(P.hard, (0.04, 0.72, z - 0.03), (w - 0.04, 0.78, z + 0.03), WOOD)
    hbox(P.hard, (-0.06, -0.06, -0.3), (w + 0.06, 0.04, 0.08), WOOD)
    if not flowerbox_too:
        for sx in (-1, 1):  # open shutters folded flat beside the opening
            x0, x1 = (-0.47, -0.03) if sx < 0 else (w + 0.03, w + 0.47)
            planks(P, [(x0, 1.35), (x1, 1.35)], x0, x1, 3, 0.015, 0.05)
            hbox(P.flat, (x0 - 0.01, 0.12, 0.045), (x1 + 0.01, 0.2, 0.07), TWOOD)
            hbox(P.flat, (x0 - 0.01, 1.2, 0.045), (x1 + 0.01, 1.28, 0.07), TWOOD)
            q = [(x0 + 0.06, 0.38, 0.06), (x1 - 0.06, 0.38, 0.06), (x1 - 0.06, 1.0, 0.06), (x0 + 0.06, 1.0, 0.06)]
            P.soft.face([P.soft.vert(v) for v in q], [(0.2, 0.3), (0.8, 0.3), (0.8, 0.82), (0.2, 0.82)], BANNER)
            for y in (0.25, 1.1):
                hbox(P.hard, ((x1 + 0.0) if sx < 0 else x0 - 0.06, y, 0.03), ((x1 + 0.06) if sx < 0 else x0, y + 0.05, 0.06), IRON)
    else:
        for sx in (-1, 1):  # shutters half open
            hinge = Vector((0.02 if sx < 0 else w - 0.02, 0, 0.02))
            ang = math.radians(55)
            dirv = Vector((-math.cos(ang) if sx < 0 else math.cos(ang), 0, math.sin(ang)))
            wid = 0.46
            for k in range(3):
                a, b = hinge + dirv * (wid * k / 3 + 0.005), hinge + dirv * (wid * (k + 1) / 3 - 0.005)
                beam(P.flat, (a + b) / 2 + Vector((0, 0.08, 0)), (a + b) / 2 + Vector((0, 1.3, 0)), (b - a).length, 0.04, TWOOD, up=dirv.cross(Vector((0, 1, 0))))
            for y in (0.3, 1.1):
                beam(P.flat, hinge + dirv * 0.02 + Vector((0, y, 0)), hinge + dirv * wid + Vector((0, y, 0)), 0.06, 0.06, TWOOD)
            ring_c = hinge + dirv * (wid - 0.1) + Vector((0, 0.7, 0)) + dirv.cross(Vector((0, 1, 0))) * (0.04 * sx)
            loop(P.soft, [ring_c + Vector((0, 0.06 * math.cos(a), 0)) + dirv * 0.06 * math.sin(a) for a in (2 * math.pi * k / 8 for k in range(8))], 0.012, BRASS, 4)
        flowerbox(P, 0.0, w, -0.32, -0.02, 0.28, R)
    vine(P.soft, (0.1, h - 0.05, 0.06), 0.5, R, 0.08, 0.0)


# ---------- attachments ----------

def lantern(P, c, R, mat=IRON):
    c = Vector(c)
    lathe(P.soft, c, [(0, -0.05), (0.06, 0.0), (0.13, 0.08), (0.13, 0.12)], 6, mat)
    lathe(P.soft, c + Vector((0, 0.11, 0)), [(0.1, 0), (0.1, 0.3), (0, 0.3)], 6, CRYSTAL)
    for k in range(6):
        a = 2 * math.pi * k / 6
        x, z = math.cos(a) * 0.12, -math.sin(a) * 0.12
        vbox(P.flat, (c.x + x - 0.012, c.y + 0.1, c.z + z - 0.012), (c.x + x + 0.012, c.y + 0.42, c.z + z + 0.012), mat)
    lathe(P.soft, c + Vector((0, 0.4, 0)), [(0.15, 0), (0.15, 0.03), (0.06, 0.13), (0.03, 0.18), (0, 0.18)], 6, mat)
    loop(P.soft, [c + Vector((0.04 * math.sin(a), 0.62 + 0.04 * math.cos(a), 0)) for a in (2 * math.pi * k / 6 for k in range(6))], 0.01, mat, 4)


def lamp(p, P, R, scrolled=False):
    w, h, d = p["size"]
    zb = -d / 2
    metal = BRASS if scrolled else IRON
    vbox(P.hard, (-0.07, h - 0.6, zb), (0.07, h - 0.05, zb + 0.04), metal)
    for y in (h - 0.5, h - 0.15):
        gem(P.soft, (0, y, zb + 0.05), 0.025, 0.025, 0.02, BRASS)
    beam(P.hard, (0, h - 0.12, zb + 0.03), (0, h - 0.12, 0.32), 0.045, 0.045, metal)
    if scrolled:
        sp = [Vector((0, h - 0.55 + 0.38 * t + 0.07 * math.sin(t * 9), zb + 0.05 + 0.5 * t - 0.08 * math.cos(t * 9) + 0.08)) for t in (i / 14 for i in range(15))]
        tube(P.soft, sp, [0.02] * len(sp), metal, 5, cap_mat=metal)
        sc = Vector((0, h - 0.05, 0.3))
        tube(P.soft, [sc + Vector((0, 0.06 * math.sin(a) * (1 - a / 9), 0.06 * math.cos(a) * (1 - a / 9))) for a in (i * 0.6 for i in range(14))], [0.016] * 14, metal, 4, cap_mat=metal)
    else:
        beam(P.hard, (0, h - 0.55, zb + 0.03), (0, h - 0.14, 0.12), 0.035, 0.035, metal)
        ball(P.soft, (0, h - 0.12, 0.34), 0.04, metal, 6)
    chain(P.soft, (0, h - 0.14, 0.25), (0, h - 0.58, 0.25), metal, 0.09, 0.012)
    lantern(P, (0, h - 1.25, 0.25), R, IRON)


def flowerbox_piece(p, P, R):
    w, h, d = p["size"]
    flowerbox(P, -w / 2, w / 2, 0.0, -d / 2, d, R, 0.3)


def banner_piece(p, P, R):
    w, h, d = p["size"]
    beam(P.hard, (-w / 2 + 0.02, h - 0.1, 0), (w / 2 - 0.02, h - 0.1, 0), 0.04, 0.04, BRASS)
    for x in (-w / 2 + 0.02, w / 2 - 0.02):
        ball(P.soft, (x, h - 0.1, 0), 0.05, BRASS, 6)
    tube(P.soft, [Vector((-w / 2 + 0.1, h - 0.1, 0)), Vector((0, h - 0.02, 0)), Vector((w / 2 - 0.1, h - 0.1, 0))], [0.01] * 3, BRASS, 4, cap_mat=BRASS)

    def bn(u, v):
        x = -w / 2 + 0.1 + (w - 0.2) * u
        tail = 0.3 * (1 - abs(2 * u - 1))
        y = (h - 0.12) - (h - 0.22 - tail * 0) * v + tail * max(0, (v - 0.82) / 0.18)
        return Vector((x, y, 0.05 * math.sin(2 * math.pi * u * 1.2 + v * 1.5) * (0.3 + 0.7 * v)))
    surface(P.cloth, bn, 6, 10, BANNER, lambda u, v: (u, 1 - v))


def pennant(p, P, R):
    w, h, d = p["size"]
    px = -w / 2 + 0.05
    lathe(P.soft, (px, 0, 0), [(0.05, 0), (0.04, 0.1), (0.028, 0.12), (0.022, h - 0.12), (0, h - 0.12)], 6, BRASS)
    ball(P.soft, (px, h - 0.08, 0), 0.06, BRASS, 6)
    lathe(P.soft, (px, h - 0.03, 0), [(0.02, 0), (0, 0.04)], 6, BRASS)

    def fl(u, v):
        x = px + 0.02 + 1.1 * u
        half = 0.2 * (1 - 0.75 * u)
        mid = h - 0.38 - 0.1 * u * u
        y = mid + half * (1 - 2 * v)
        if u > 0.82:
            y += (0.5 - v) * -0.0
        return Vector((x, y, 0.09 * math.sin(math.pi * 2 * u * 1.1) * u))
    surface(P.cloth, fl, 10, 2, BANNER, lambda u, v: (0.05 + u * 0.25, 0.35 + v * 0.3))


def sign(p, P, R, hammers=False):
    w, h, d = p["size"]
    zb = -d / 2
    vbox(P.hard, (-0.06, h - 0.45, zb), (0.06, h, zb + 0.04), IRON)
    beam(P.hard, (0, h - 0.06, zb + 0.03), (0, h - 0.06, d / 2 - 0.04), 0.04, 0.05, IRON)
    sp = [Vector((0, h - 0.45 + 0.35 * t, zb + 0.04 + 0.35 * t + 0.07 * math.sin(t * 8))) for t in (i / 12 for i in range(13))]
    tube(P.soft, sp, [0.016] * 13, IRON, 4, cap_mat=IRON)
    ball(P.soft, (0, h - 0.06, d / 2 - 0.03), 0.035, IRON, 6)
    cz, cy, r = 0.08, 0.42, 0.3
    oct_ = [(cz + r * math.cos(a), cy + r * math.sin(a)) for a in (math.pi / 8 + math.pi * k / 4 for k in range(8))]
    prism_x(P.hard, oct_, -0.03, 0.03, TWOOD, 1.0)
    loop(P.soft, [(0, y, z) for z, y in oct_], 0.035, BRASS, 5)
    for z in (cz - 0.16, cz + 0.16):
        chain(P.soft, (0, h - 0.07, z), (0, cy + r + 0.02, z), IRON, 0.08, 0.01)
    for sx in (-1, 1):
        x = sx * 0.045
        if hammers:
            for s in (-1, 1):
                a = Vector((x, cy - 0.17, cz + s * 0.15))
                b = Vector((x, cy + 0.12, cz - s * 0.1))
                beam(P.hard, a, b, 0.03, 0.03, BRASS, up=(1, 0, 0))
                dirv = (b - a).normalized()
                perp = dirv.cross(Vector((1, 0, 0))).normalized()
                beam(P.hard, b - perp * 0.1, b + perp * 0.1, 0.03, 0.07, BRASS, up=(1, 0, 0))
        else:
            lathe(P.soft, (x, cy - 0.18, cz), [(0.09, 0), (0.09, 0.02), (0.025, 0.05), (0.025, 0.12), (0.13, 0.18), (0.14, 0.34), (0.12, 0.34)], 8, BRASS, sx=0.25)
            loop(P.soft, [(x, cy + 0.05 + 0.06 * math.sin(a), cz + 0.17 + 0.05 * math.cos(a)) for a in (2 * math.pi * k / 6 for k in range(6))], 0.012, BRASS, 4)


def cornice(p, P, R):
    w, h, d = p["size"]
    pid = p["id"]
    zb = -d
    if "basalt" in pid:
        box(P.flat, (0.0, 0.0, zb), (w, 0.12, zb + 0.18), STONE, 1.5)
        xs = [0.0]
        while xs[-1] < w - 0.05:
            xs.append(min(w, xs[-1] + R.uniform(0.42, 0.62)))
        for a, b in zip(xs, xs[1:]):
            hbox(P.hard, (a + 0.008, 0.12, zb), (b - 0.008, h, -0.08 + R.uniform(-0.02, 0.0)), BLOCK, 1.2)
            prism_x(P.hard, [(zb, 0.0), (zb + 0.2, 0.0), (-0.1, 0.12), (zb, 0.12)], a + 0.04, b - 0.04, BLOCK)
        hbox(P.flat, (0.03, 0.26, -0.072), (w - 0.03, 0.34, -0.062), CRYSTAL)
        for k in range(2):
            clump(P.soft, (R.uniform(0.2, w - 0.2), h, -0.25), 0.12, R)
    elif "deadwood" in pid:
        hbox(P.hard, (0, 0.28, zb), (w, h, -0.08), WOOD)
        for x in (0.35, w - 0.35):
            pts = hermite((x, 0.0, zb + 0.03), (0, 0.1, 0.5), (x, 0.27, -0.12), (0, 0.4, 0.3), 7)
            tube(P.soft, pts, [0.06 + 0.04 * i / 7 for i in range(8)], WOOD, 5)
            sc = Vector((x, 0.06, zb + 0.12))
            tube(P.soft, [sc + Vector((0, 0.05 * math.sin(a) * (1 - a / 10), 0.05 * math.cos(a) * (1 - a / 10))) for a in (i * 0.7 for i in range(12))], [0.03] * 12, WOOD, 4)
            joint(P, x, 0.39, R, -0.06, 0.5)
        vine(P.soft, (w / 2, 0.3, -0.06), 0.35, R, 0.06, 0.0)
    else:  # terracotta eave with sailcloth valance
        A, Bv, D, C = (0, 0.22, 0.0), (w, 0.22, 0.0), (0, h, zb), (w, h, zb)
        deck(P.flat, A, Bv, D, C, 0.04, TILE, WOOD)
        tiles(P.flat, A, Bv, D, C, 2, 0.4, R, base=0.04, t=0.04)
        for x in (0.25, w - 0.25):
            beam(P.hard, (x, 0.0, zb + 0.02), (x, 0.2, -0.05), 0.08, 0.08, WOOD)
        scallops(P, 0.0, w, 0.22, 0.02, 0.2, 4, R)


def build_piece(p, mats):
    for (name, tex, emit), mat in zip(MATS, mats):  # contact-sheet colours for untextured slots
        if not isinstance(tex, str):
            mat.diffuse_color = (*tex, 1)
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    R = random.Random(p["id"])
    pid, fam = p["id"], p["family"]
    P = Parts()
    amp, bev = 0.018, 0.022
    if fam == "foundation":
        if "slope" in pid:
            slope_step(p, P, R)
        else:
            plinth(p, P, R, dock="dock" in pid)
    elif fam == "wall":
        if "basalt" in pid:
            basalt_wall(p, P, R)
        elif "oriel" in pid:
            oriel(p, P, R)
        else:
            w, h, d = p["size"]
            timber_frame(P, w, h, d, R, "x", p.get("opening"))
    elif fam == "trim" and "infill" in pid:
        w, h, d = p["size"]
        timber_frame(P, w, h, d, R, {"xbrace": "x", "chevron": "chevron"}.get(pid.split("-")[-1], "plain"))
    elif fam == "trim":
        cornice(p, P, R)
    elif fam == "corner":
        if "tower" in pid:
            corner_tower(p, P, R)
        else:
            corner_post(p, P, R, inner="inner" in pid)
    elif fam == "floor":
        paving(p, P, R)
    elif fam == "access":
        if "stairs" in pid:
            stairs(p, P, R)
        else:
            balcony(p, P, R)
    elif fam == "roof":
        amp = 0.012
        {"run": roof_run, "hip": roof_hip, "ridge": ridge, "deadwood": gable, "dormer": dormer}[pid.split("-")[-1] if pid.split("-")[-1] != "deadwood" else "deadwood"](p, P, R)
    elif fam == "crown":
        amp = 0.01
        {"spire": spire, "cupola": cupola, "towercap": tower_cap}[pid.split("-")[2]](p, P, R)
    elif fam == "insert":
        w, h, d = p["size"]
        if "market" in pid:
            market_door(p, P, R)
        elif "door" in pid:
            door_leaf(P, w, h, "deadwood" in pid, R)
        elif "leaded" in pid:
            leaded_window(p, P, R)
        else:
            timber_window(p, P, R, flowerbox_too="flowerbox" in pid)
    else:  # attachments
        amp, bev = 0.008, 0.0
        if "awning" in pid:
            awning(p, P, R)
        elif "canopy" in pid:
            canopy(p, P, R)
        elif "lamp" in pid:
            lamp(p, P, R, scrolled=pid.endswith("-b"))
        elif "flowerbox" in pid:
            flowerbox_piece(p, P, R)
        elif "banner" in pid:
            banner_piece(p, P, R)
        elif "pennant" in pid:
            pennant(p, P, R)
        elif "sign" in pid:
            sign(p, P, R, hammers=pid.endswith("-b"))
    return finish(P, p, mats, seed, amp, bev)


def balcony(p, P, R):
    w, h, d = p["size"]
    for k in range(4):
        z0 = -d + k * d / 4
        hbox(P.flat, (0, 0, z0 + 0.008), (w, 0.1, z0 + d / 4 - 0.008), WOOD)
    hbox(P.hard, (0, -0.16, -d), (w, 0.0, -d + 0.12), WOOD)
    hbox(P.hard, (0, -0.14, -0.14), (w, 0.0, -0.02), WOOD)
    for x in (0.25, w - 0.25):
        pts = hermite((x, -0.75, -d + 0.04), (0, 0.3, 0.5), (x, -0.08, -0.12), (0, 0.1, 1.0), 7)
        tube(P.soft, pts, [0.07 - 0.02 * i / 7 for i in range(8)], WOOD, 5)
        hbox(P.hard, (x - 0.08, -0.85, -d), (x + 0.08, -0.6, -d + 0.08), WOOD)
    zr = -0.09
    posts = [0.06, w / 2, w - 0.06]
    for x in posts:
        vbox(P.hard, (x - 0.06, 0.1, zr - 0.06), (x + 0.06, h - 0.02, zr + 0.06), WOOD)
    for x in (posts[0], posts[-1]):
        ball(P.soft, (x, h + 0.06, zr), 0.07, BRASS, 8)
        lathe(P.soft, (x, h - 0.02, zr), [(0.07, 0), (0.05, 0.04)], 6, BRASS)
    hbox(P.hard, (0, h - 0.12, zr - 0.07), (w, h - 0.03, zr + 0.07), WOOD)
    hbox(P.hard, (0, 0.18, zr - 0.04), (w, 0.26, zr + 0.04), WOOD)
    for a, b in zip(posts, posts[1:]):
        for s in (0, 1):
            pa = (a + 0.06, 0.26 if s == 0 else h - 0.12, zr)
            pb = (b - 0.06, h - 0.12 if s == 0 else 0.26, zr)
            beam(P.flat, pa, pb, 0.06, 0.06, WOOD, up=(0, 0, 1))
    for _ in range(2):
        clump(P.soft, (R.uniform(0.3, w - 0.3), 0.1, R.uniform(-d + 0.2, -0.3)), 0.14, R)
    flowers(P.soft, (w / 2, h - 0.05, zr), 0.12, 3, R)
    vine(P.soft, (R.uniform(0.2, w - 0.2), h - 0.08, zr + 0.06), 0.7, R, 0.1, 0.0)


if __name__ == "__main__":
    K.build_all(build_piece, extras=[("acc-canopy-sailcloth-galeborne", "decor"), ("acc-lamp-bracket-b", "hanging"),
                                     ("acc-flowerbox-large", "prop"), ("acc-sign-shop-a", "hanging"), ("acc-sign-shop-b", "hanging"),
                                     ("acc-banner-galeborne", "hanging"), ("acc-pennant-galeborne", "decor")], biome="accord")
