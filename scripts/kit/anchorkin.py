# Detailed Anchorkin kit: textured, hand-cut basalt pieces built from kit.json on the 3 m module, 4 m storey and
# 1 m wall battered 8 degrees inward. Walls are stacked courses of individually chamfered stones whose faces map onto
# whole painted stones of the basalt swatch; teal crystal grows in the joints, Ledger bands carry the inscription
# swatch, oath-marks are thin gold inlay, every strap, cap, ring and chain is black forged iron.
# Joined prefabs from each prefab's layout, a demo catalogue and contact-sheet renders come from kitlib.build_all.
# Textures are the painted swatches in art/textures/anchorkin.
# Usage: Blender --background --python scripts/kit/anchorkin.py -- anchorkin
import bmesh, bpy, math, os, random, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, tube  # noqa: E402

# Material slots, in order; every object carries the full list so joined prefabs keep one material set
MATS = [("ANK_Basalt", "basalt-blocks.png", 0), ("ANK_Slate", "slate-courses.png", 0), ("ANK_CrystalStone", "crystal-stone.png", 0.8),
        ("ANK_Ledger", "ledger-glyphs.png", 0), ("ANK_Iron", "black-iron.png", 0), ("ANK_Chain", "chain.png", 0),
        ("ANK_Oak", "weathered-oak.png", 0), ("ANK_Moss", "moss-stone.png", 0), ("ANK_Gold", (0.86, 0.62, 0.2), 0),
        ("ANK_Crystal", (0.18, 0.95, 0.84), 4.0), ("ANK_Glow", (1.0, 0.62, 0.22), 3.0)]
BASALT, SLATE, CSTONE, LEDGER, IRON, CHAIN, OAK, MOSS, GOLD, CRYSTAL, GLOW = range(len(MATS))
K.configure(MATS, os.path.join(B.ROOT, "art/textures/anchorkin"), cap_mat=IRON, moss=None)

_make = K.make_materials


def _make_materials():
    """kitlib's materials, plus a viewport colour on the flat ones so Workbench sheets show gold, crystal and glow."""
    out = _make()
    for m, (_, tex, _e) in zip(out, MATS):
        if not isinstance(tex, str):
            m.diffuse_color = (*tex, 1)
    return out


K.make_materials = _make_materials

T = math.tan(math.radians(8))  # wall batter: the outer face leans in 0.14 m per metre of height
Y = Vector((0, 1, 0))
X = Vector((1, 0, 0))
Z = Vector((0, 0, 1))
ROWS4 = [0, 1.0, 1.75, 2.45, 3.0, 3.5, 4.0]  # course heights shared by every 4 m wall, corner and pier
ROWS2 = [0, 0.75, 1.4, 2.0]


def _px(x0, y0, x1, y1):
    return (x0 / 500, 1 - y1 / 500, x1 / 500, 1 - y0 / 500, (x1 - x0) / (y1 - y0))


# Whole painted stones in basalt-blocks.png (u0, v0, u1, v1, aspect): a geometric stone shows exactly one of them
STONES = [_px(4, 2, 133, 138), _px(142, 2, 368, 138), _px(377, 2, 498, 138), _px(2, 152, 208, 333), _px(222, 152, 493, 333),
          _px(2, 347, 153, 498), _px(162, 347, 343, 498), _px(352, 347, 498, 498)]


# ---------- low-level geometry ----------

def nrm(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        n += Vector(((p.y - q.y) * (p.z + q.z), (p.z - q.z) * (p.x + q.x), (p.x - q.x) * (p.y + q.y)))
    return n.normalized() if n.length > 1e-12 else n


def addf(m, pts, mat, want, uvs=None, tile=1.0):
    pts = [Vector(p) for p in pts]
    if want is not None and nrm(pts).dot(Vector(want)) < 0:
        pts = pts[::-1]
        uvs = uvs[::-1] if uvs else uvs
    return m.face([m.vert(p) for p in pts], uvs, mat, tile)


def frame(O, A, bat=0.0):
    """Face frame: a along A, b up, n out along A x Y; the face leans in by `bat` per metre of b."""
    O, A = Vector(O), Vector(A).normalized()
    N = A.cross(Y)

    def F(a, b, n=0.0):
        return O + A * a + Y * b + N * (n - bat * b)
    F.N = N
    return F


def poly_uv(poly, rect):
    u0, v0, u1, v1 = rect[:4]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    ax, bx, ay, by = min(xs), max(xs), min(ys), max(ys)
    return [(u0 + (u1 - u0) * (x - ax) / max(bx - ax, 1e-6), v0 + (v1 - v0) * (y - ay) / max(by - ay, 1e-6)) for x, y in poly]


def stone_rect(rnd, w, h, mat=BASALT):
    if mat == CSTONE:
        su = rnd.uniform(0.3, 0.5)
        sv = min(0.9, su * h / max(w, 0.05))
        u0, v0 = rnd.uniform(0, 1 - su), rnd.uniform(0, 1 - sv)
        return (u0, v0, u0 + su, v0 + sv)
    asp = w / max(h, 0.05)
    c = rnd.choice(sorted(STONES, key=lambda s: abs(math.log(s[4] / asp)))[:3])
    return (c[2], c[1], c[0], c[3]) if rnd.random() < 0.5 else c[:4]


def slab(m, pts, depth, mat, ch=0.04, uv=None, side=None, tile=1.0, want=None, back=True):
    """Chamfered prism: front polygon `pts`, pushed back `depth` along its normal (outward = `want`)."""
    pts = [Vector(p) for p in pts]
    N = nrm(pts)
    if want is not None and N.dot(Vector(want)) < 0:
        pts, N = pts[::-1], -N
        uv = uv[::-1] if uv else uv
    k = len(pts)
    sm = mat if side is None else side
    outs = [(pts[(i + 1) % k] - pts[i]).normalized().cross(N).normalized() for i in range(k)]
    if ch > 0:
        front = []
        for i in range(k):
            n1, n2 = -outs[i - 1], -outs[i]
            front.append(pts[i] + (n1 + n2) / max(0.35, 1 + n1.dot(n2)) * ch)
        rim = [p - N * ch for p in pts]
    else:
        front = rim = pts
    addf(m, front, mat, N, uv, tile)
    if ch > 0:
        for i in range(k):
            j = (i + 1) % k
            addf(m, [front[i], front[j], rim[j], rim[i]], sm, N + outs[i], None, tile)
    bk = [p - N * depth for p in pts]
    for i in range(k):
        j = (i + 1) % k
        addf(m, [rim[i], rim[j], bk[j], bk[i]], sm, outs[i], None, tile)
    if back:
        addf(m, bk, sm, -N, None, tile)


def stone(m, F, poly, rnd, mat=BASALT, n=0.0, ch=0.045, depth=0.22, rect=None, side=None):
    """One cut stone on face F; its front shows one whole painted stone."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    if rect is None and mat in (BASALT, CSTONE, SLATE):
        rect = stone_rect(rnd, max(xs) - min(xs), max(ys) - min(ys), BASALT if mat == SLATE else mat)
    uv = poly_uv(poly, rect) if rect else None
    slab(m, [F(a, b, n) for a, b in poly], depth, mat, ch, uv, side if side is not None else (BASALT if mat == CSTONE else None), want=F.N)


def hexa(m, bot, top, mat=BASALT, tile=2.0):
    bot, top = [Vector(p) for p in bot], [Vector(p) for p in top]
    c = sum(bot + top, Vector((0, 0, 0))) / 8
    for f in [bot, top] + [[bot[i], bot[(i + 1) % 4], top[(i + 1) % 4], top[i]] for i in range(4)]:
        addf(m, f, mat, sum(f, Vector((0, 0, 0))) / 4 - c, None, tile)


def cube(m, lo, hi, mat=BASALT, tile=2.0):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    hexa(m, [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)], [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], mat, tile)


def prism(m, prof, x0, x1, mat=BASALT, tile=2.0):
    """Profile (z, y) extruded along x."""
    a = [Vector((x0, y, z)) for z, y in prof]
    b = [Vector((x1, y, z)) for z, y in prof]
    addf(m, a, mat, -X, None, tile)
    addf(m, b, mat, X, None, tile)
    sgn = 1 if sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof))) > 0 else -1
    for i in range(len(prof)):
        j = (i + 1) % len(prof)
        du, dv = prof[j][0] - prof[i][0], prof[j][1] - prof[i][1]
        addf(m, [a[i], a[j], b[j], b[i]], mat, Vector((0, -du * sgn, dv * sgn)), None, tile)


def ribbon(m, F, pts, w, n, mat):
    P, keep = [], []
    for k, p in enumerate(pts):
        if not P or (Vector(p) - Vector(P[-1])).length > 1e-4:
            P.append(tuple(p))
            keep.append(k)
    if isinstance(w, (list, tuple)):
        w = [w[k] for k in keep]
    if len(P) < 2:
        return
    L, R = [], []
    for i, p in enumerate(P):
        p = Vector(p)
        d0 = (p - Vector(P[i - 1])).normalized() if i > 0 else None
        d1 = (Vector(P[i + 1]) - p).normalized() if i < len(P) - 1 else None
        d = d1 if d0 is None else d0 if d1 is None else (d0 + d1)
        if d.length < 1e-6:
            d = d1
        d = d.normalized()
        perp = Vector((-d.y, d.x))
        s = 1.0
        if d0 is not None and d1 is not None:
            s = 1.0 / max(0.45, perp.dot(Vector((-d0.y, d0.x))))
        wi = w[i] if isinstance(w, (list, tuple)) else w
        L.append(p + perp * wi / 2 * s)
        R.append(p - perp * wi / 2 * s)
    for i in range(len(P) - 1):
        addf(m, [F(R[i].x, R[i].y, n), F(R[i + 1].x, R[i + 1].y, n), F(L[i + 1].x, L[i + 1].y, n), F(L[i].x, L[i].y, n)], mat, F.N)


def rivet(m, F, a, b, n, r=0.03):
    base = [F(a - r, b - r, n), F(a + r, b - r, n), F(a + r, b + r, n), F(a - r, b + r, n)]
    tip = F(a, b, n + r * 0.9)
    for i in range(4):
        addf(m, [base[i], base[(i + 1) % 4], tip], IRON, F.N)


def strap(m, F, a0, a1, b0, b1, n=0.0, t=0.035, rivets=2, poly=None, ch=0.012):
    pp = poly or [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
    slab(m, [F(a, b, n + t) for a, b in pp], t + 0.03, IRON, ch, want=F.N)
    r = min(0.034, (b1 - b0) * 0.28)
    for k in range(rivets):
        rivet(m, F, a0 + (a1 - a0) * (k + 0.5) / rivets, (b0 + b1) / 2, n + t, r)


def link(m, c, d, u, L, W, r, mat=CHAIN, sides=7, n=14):
    """Stadium-shaped chain link (or a ring when L == W) in the plane of d and u."""
    c, d, u = Vector(c), Vector(d).normalized(), Vector(u).normalized()
    R, s = W / 2 - r, max(0.0, L / 2 - W / 2)
    h = n // 2
    pts = [c + d * s + (d * math.cos(a) + u * math.sin(a)) * R for a in (-math.pi / 2 + math.pi * k / (h - 1) for k in range(h))]
    pts += [c - d * s + (d * math.cos(a) + u * math.sin(a)) * R for a in (math.pi / 2 + math.pi * k / (h - 1) for k in range(h))]
    tube(m, pts + [pts[0]], [r] * (len(pts) + 1), mat, sides, closed=True, tile=0.5)


def crystal(m, base, axis, r, h, tip, rnd, mat=CRYSTAL, k=6):
    axis = Vector(axis).normalized()
    b = Vector(base)
    e1 = axis.orthogonal().normalized()
    e2 = axis.cross(e1)
    a0 = rnd.uniform(0, math.pi)
    ring0 = [b + (e1 * math.cos(a0 + 2 * math.pi * i / k) + e2 * math.sin(a0 + 2 * math.pi * i / k)) * r * 0.82 for i in range(k)]
    ring1 = [b + axis * h + (e1 * math.cos(a0 + 2 * math.pi * i / k) + e2 * math.sin(a0 + 2 * math.pi * i / k)) * r for i in range(k)]
    apex = b + axis * (h + tip)
    for i in range(k):
        j = (i + 1) % k
        mid = (ring0[i] + ring1[j]) / 2
        addf(m, [ring0[i], ring0[j], ring1[j], ring1[i]], mat, mid - (b + axis * h / 2))
        addf(m, [ring1[i], ring1[j], apex], mat, (ring1[i] + ring1[j]) / 2 - (b + axis * h))
    addf(m, ring0, mat, -axis)


ANCHOR = [[(0, -0.42), (0, 0.4)], [(-0.13, 0.28), (0, 0.46), (0.13, 0.28)], [(-0.21, 0.15), (0.21, 0.15)],
          [(0.33 * math.cos(a), -0.12 + 0.32 * math.sin(a)) for a in (math.pi + math.pi * k / 8 for k in range(9))],
          [(-0.42, -0.2), (-0.33, -0.08), (-0.24, -0.2)], [(0.24, -0.2), (0.33, -0.08), (0.42, -0.2)]]


def glyph(m, F, ca, cb, s, n=0.004, sx=1.0):
    """Anchor oath-mark: thin gold inlay."""
    for line in ANCHOR:
        ribbon(m, F, [(ca + x * s * sx, cb + y * s) for x, y in line], 0.065 * s * min(1.0, sx + 0.25), n, GOLD)


# ---------- masonry ----------

def split(s, e, rnd, row, lo=0.75, hi=1.35, minw=0.42):
    cuts, x = [s], s
    w = rnd.uniform(0.38, 0.8) if row % 2 else rnd.uniform(lo, hi)
    while e - (x + w) >= minw:
        x += w
        cuts.append(x)
        w = rnd.uniform(lo, hi)
    cuts.append(e)
    return cuts


def masonry(m, F, a0, a1, rows, rnd, holes=(), n=0.0, jit=0.022, depth=0.22, cst=0.06, r0=0, ch=0.042):
    """Courses of chamfered stones on face F between a0 and a1; holes are (a0, a1, b0, b1) on course lines."""
    joints = []
    for r, (b0, b1) in enumerate(zip(rows, rows[1:])):
        spans = [(a0, a1)]
        for h0, h1, hb0, hb1 in holes:
            if hb0 < b1 - 1e-3 and hb1 > b0 + 1e-3:
                new = []
                for s, e in spans:
                    if h1 <= s + 1e-6 or h0 >= e - 1e-6:
                        new.append((s, e))
                        continue
                    if h0 - s > 0.05:
                        new.append((s, h0))
                    if e - h1 > 0.05:
                        new.append((h1, e))
                spans = new
        row = []
        for s, e in spans:
            cuts = split(s, e, rnd, r + r0)
            for x0, x1 in zip(cuts, cuts[1:]):
                g = 0.004
                mat = CSTONE if rnd.random() < cst else BASALT
                stone(m, F, [(x0 + g, b0 + g), (x1 - g, b0 + g), (x1 - g, b1 - g), (x0 + g, b1 - g)], rnd, mat,
                      n - rnd.uniform(0, jit), ch * rnd.uniform(0.85, 1.35), depth)
            row.append(cuts)
        joints.append((b0, b1, row))
    return joints


def vein(m, F, joints, rnd, n=0.004, steps=3, w=0.06, holes=()):
    """A teal crystal crack: starts low, wanders up across stones and joints, tapers, sometimes forks."""
    cuts = [c for _, _, row in joints for cs in row for c in cs]
    if not cuts:
        return
    lo, hi = min(cuts) + 0.15, max(cuts) - 0.15
    if hi <= lo:
        lo = hi = (min(cuts) + max(cuts)) / 2
    btop = joints[min(len(joints) - 1, steps)][1]
    b = joints[0][0] + rnd.uniform(0.08, 0.4)

    def blocked(a, bb):
        return any(h0 - 0.08 < a < h1 + 0.08 and hb0 - 0.08 < bb < hb1 + 0.08 for h0, h1, hb0, hb1 in holes)

    def crack(a, b, H, drift, nseg, w0):
        pts = [(a, b)]
        for k in range(1, nseg + 1):
            a = min(hi, max(lo, a + drift * H / nseg + rnd.uniform(-0.11, 0.11)))
            q = (a, b + H * k / nseg)
            if blocked(*q):
                break
            pts.append(q)
        if len(pts) > 2:
            ribbon(m, F, pts, [w0 * (1 - 0.75 * k / (len(pts) - 1)) + 0.008 for k in range(len(pts))], n, CRYSTAL)
        return pts
    for _ in range(8):
        a = rnd.uniform(lo, hi)
        if not blocked(a, b):
            break
    else:
        return
    H = max(0.6, min(btop - b, rnd.uniform(1.3, 2.3)))
    pts = crack(a, b, H, rnd.choice((-1, 1)) * rnd.uniform(0.1, 0.35), 9, w)
    if len(pts) > 5 and rnd.random() < 0.75:
        k = rnd.randrange(2, len(pts) - 2)
        crack(pts[k][0], pts[k][1], H * 0.4, rnd.choice((-1, 1)) * 0.6, 4, w * 0.55)


def core(m, F, a0, a1, b0, b1, n=-0.05, back=-1.0):
    """Wall core behind the stones: battered front on F, flat back at z = back."""
    f = [F(a0, b0, n), F(a1, b0, n), F(a1, b1, n), F(a0, b1, n)]
    bk = [Vector((p.x, p.y, back)) for p in f]
    hexa(m, [f[0], f[1], bk[1], bk[0]], [f[3], f[2], bk[2], bk[3]])


ORDER = ["front", "right", "back", "left"]


def pier(m, rnd, x0, x1, z0, z1, rows, bat, blocks, jit=0.02, depth=0.22, cst=0.05, par=0, flat=(), y0=0.0, core_n=0.06, coremat=BASALT):
    """Free-standing block of courses; `bat` leans each named face in, `blocks` names the faces dressed in stones
    (others are joints or interiors). Corners alternate which face's stone wraps them (quoins). Returns frames."""
    starts = {"front": ((x0, y0, z1), X, x1 - x0), "right": ((x1, y0, z1), -Z, z1 - z0),
              "back": ((x1, y0, z0), -X, x1 - x0), "left": ((x0, y0, z0), Z, z1 - z0)}
    # frames measure b from y = 0; rows are absolute heights
    Fs = {f: frame(Vector(starts[f][0]) - Vector((0, y0, 0)), starts[f][1], bat.get(f, 0)) for f in ORDER}
    for i, f in enumerate(ORDER):
        if f not in blocks:
            continue
        prev, nxt = ORDER[i - 1], ORDER[(i + 1) % 4]
        L = starts[f][2]
        F = Fs[f]
        bp, bn = bat.get(prev, 0), bat.get(nxt, 0)
        for r, (b0, b1) in enumerate(zip(rows, rows[1:])):
            own = (r + i + par) % 2 == 0
            ds = 0 if (prev not in blocks or own) else depth
            de = 0 if (nxt not in blocks or own) else depth
            s0, s1 = bp * b0 + ds, bp * b1 + ds
            e0, e1 = L - bn * b0 - de, L - bn * b1 - de
            cuts = split(max(s0, s1), min(e0, e1), rnd, r + i, 0.65, 1.2, 0.38)
            g = 0.004
            for k, (c0, c1) in enumerate(zip(cuts, cuts[1:])):
                l0, l1 = (s0, s1) if k == 0 else (c0 + g, c0 + g)
                q0, q1 = (e0, e1) if k == len(cuts) - 2 else (c1 - g, c1 - g)
                mat = CSTONE if rnd.random() < cst else BASALT
                jj = 0 if r in flat else rnd.uniform(0, jit)
                stone(m, F, [(l0, b0 + g), (q0, b0 + g), (q1, b1 - g), (l1, b1 - g)], rnd, mat, -jj, 0.042 * rnd.uniform(0.85, 1.3), depth)

    def ring(b):
        xl = x0 + bat.get("left", 0) * b + (core_n if "left" in blocks else 0)
        xr = x1 - bat.get("right", 0) * b - (core_n if "right" in blocks else 0)
        zf = z1 - bat.get("front", 0) * b - (core_n if "front" in blocks else 0)
        zb = z0 + bat.get("back", 0) * b + (core_n if "back" in blocks else 0)
        return [Vector((xl, b, zf)), Vector((xr, b, zf)), Vector((xr, b, zb)), Vector((xl, b, zb))]
    hexa(m, ring(rows[0]), ring(rows[-1]), coremat)
    return Fs


def paving(m, rnd, x0, x1, z0, z1, y, thick=0.15, ch=0.035, jit=0.018, mat=BASALT, rowlen=1.0):
    nz = max(1, round((z1 - z0) / rowlen))
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    for r, (za, zb) in enumerate(zip(zs, zs[1:])):
        cuts = split(x0, x1, rnd, r, 0.8, 1.3, 0.45)
        for c0, c1 in zip(cuts, cuts[1:]):
            g = 0.006
            top = y - rnd.uniform(0, jit)
            pts = [(c0 + g, top, zb - g), (c1 - g, top, zb - g), (c1 - g, top, za + g), (c0 + g, top, za + g)]
            rect = stone_rect(rnd, c1 - c0, zb - za)
            uv = poly_uv([(p[0], -p[2]) for p in pts], rect)
            slab(m, pts, thick, mat, ch * rnd.uniform(0.8, 1.3), uv, want=Y)


def arch_wedges(m, F, cx, cy, r, x0, x1, ytop, nw, rnd, depth, n=0.0, key=0.03):
    """Voussoir wedges filling the rectangle [x0, x1] x [cy, ytop] above a round arch (centre cx, cy, radius r)."""
    def hit(th):
        dx, dy = math.cos(th), math.sin(th)
        ts = []
        if dx > 1e-6:
            ts.append((x1 - cx) / dx)
        if dx < -1e-6:
            ts.append((x0 - cx) / dx)
        if dy > 1e-6:
            ts.append((ytop - cy) / dy)
        t = min(ts)
        return (cx + dx * t, cy + dy * t)
    for i in range(nw):
        t0, t1 = math.pi * i / nw, math.pi * (i + 1) / nw
        poly = [(cx + r * math.cos(t0 + (t1 - t0) * k / 3), cy + r * math.sin(t0 + (t1 - t0) * k / 3)) for k in range(4)]
        poly.append(hit(t1))
        for c in ((x1, ytop), (x0, ytop)):
            if t0 + 1e-6 < math.atan2(c[1] - cy, c[0] - cx) < t1 - 1e-6:
                poly.append(c)
        poly.append(hit(t0))
        ccx = sum(p[0] for p in poly) / len(poly)
        ccy = sum(p[1] for p in poly) / len(poly)
        poly = [(x + (ccx - x) * 0.012, y + (ccy - y) * 0.012) for x, y in poly]
        kn = key if i == nw // 2 else -rnd.uniform(0, 0.02)
        stone(m, F, poly, rnd, BASALT, n + kn, 0.04, depth)


def arch_outline(cx, spring, r, n=10):
    return [(cx - r, 0)] + [(cx + r * math.cos(math.pi - math.pi * k / n), spring + r * math.sin(math.pi - math.pi * k / n)) for k in range(n + 1)] + [(cx + r, 0)]


def fill_poly(m, pts3, mat, want):
    addf(m, pts3, mat, want, None, 1.0)


# ---------- walls ----------

FR = frame((0, 0, 0), X, T)  # battered outer face of every wall piece


def cleats(m, w, h):
    for a0 in (0.1, w - 0.38):
        strap(m, FR, a0, a0 + 0.28, h - 0.62, h - 0.02, rivets=2)
        top = h + 0.03
        z0 = -T * h + 0.03
        slab(m, [(a0, top, z0), (a0 + 0.28, top, z0), (a0 + 0.28, top, z0 - 0.38), (a0, top, z0 - 0.38)], 0.065, IRON, 0.012, want=Y)


def build_wall(p, m, rnd):
    w, h, _ = p["size"]
    pid = p["id"]
    if "endcap" in pid:
        return build_corner(p, m, rnd)
    rows = ROWS4 if h >= 4 else ROWS2
    if "door" in pid:
        jr = [0, 1.0, 1.75, 2.45, 3.2]
        masonry(m, FR, 0, 0.5, jr, rnd, n=-0.12, cst=0)
        masonry(m, FR, 2.5, 3, jr, rnd, n=-0.12, cst=0, r0=1)
        for a0, a1 in ((0, 0.5), (2.5, 3)):
            stone(m, FR, [(a0 + .004, 3.204), (a1 - .004, 3.204), (a1 - .004, 3.496), (a0 + .004, 3.496)], rnd, BASALT, 0, 0.04, 0.25)
        arch_wedges(m, FR, 1.5, 2.2, 1.0, 0.5, 2.5, 3.5, 7, rnd, 0.58, key=0.04)
        j = masonry(m, FR, 0, w, [3.5, 4.0], rnd, r0=1)
        for a0, a1 in ((0, 0.5), (2.5, 3)):
            core(m, FR, a0, a1, 0, 3.2, n=-0.3)
            core(m, FR, a0, a1, 3.2, 3.5)
        core(m, FR, 0, w, 3.5, h)
        glyph(m, FR, 1.5, 3.35, 0.24, 0.044)
    else:
        holes, cores = [], [(0, w, 0, h)]
        if "window" in pid:
            holes = [(0.5, 2.5, 1.0, 3.0), (0.3, 2.7, 3.0, 3.5)]
            cores = [(0, 0.5, 0, h), (2.5, w, 0, h), (0.5, 2.5, 0, 1.0), (0.5, 2.5, 3.0, h)]
            stone(m, FR, [(0.304, 3.004), (2.696, 3.004), (2.696, 3.496), (0.304, 3.496)], rnd, BASALT, 0.0, 0.05, 0.3)
            strap(m, FR, 0.95, 2.05, 3.17, 3.33, rivets=3)
        if "ledger" in pid:
            holes = [(0, w, 2.45, 3.5)]
            for a0, a1 in ((0, 1.5), (1.5, 3)):
                stone(m, FR, [(a0 + .004, 2.56), (a1 - .004, 2.56), (a1 - .004, 3.39), (a0 + .004, 3.39)], rnd, LEDGER, -0.005, 0.025, 0.25,
                      rect=(0, 0, 1, 1), side=BASALT)
            strap(m, FR, 0, w, 2.45, 2.56, n=-0.03, rivets=6)
            strap(m, FR, 0, w, 3.39, 3.5, n=-0.03, rivets=6)
        j = masonry(m, FR, 0, w, rows, rnd, holes)
        for c in cores:
            core(m, FR, *c)
        if rnd.random() < 0.6:
            vein(m, FR, j[:4], rnd, holes=holes)
    cleats(m, w, h)


def build_corner(p, m, rnd):
    pid = p["id"]
    if "inner" in pid:
        # Concave corner: wing along x faces +z at z = -2, wing along z faces +x at x = 1
        Fa = frame((0, 0, -2), X, T)
        Fb = frame((1, 0, 0), -Z, T)
        # each face runs on into the other wing, so the stones butt into each other along the leaning valley
        ja = masonry(m, Fa, 1.0 - 4 * T, 3.0, ROWS4, rnd)
        jb = masonry(m, Fb, 0.0, 2.0 + 4 * T, ROWS4, rnd, r0=1)
        core(m, Fa, 1.0, 3.0, 0, 4, back=-3.0)
        fb = [Fb(0, 0, -0.05), Fb(2.0, 0, -0.05), Fb(2.0, 4, -0.05), Fb(0, 4, -0.05)]
        hexa(m, [fb[0], fb[1], Vector((0, 0, -2)), Vector((0, 0, 0))], [fb[3], fb[2], Vector((0, 4, -2)), Vector((0, 4, 0))])
        hexa(m, [(0, 0, -2), (1, 0, -2), (1, 0, -3), (0, 0, -3)], [(0, 4, -2 - 4 * T), (1 - 4 * T, 4, -2 - 4 * T), (1 - 4 * T, 4, -3), (0, 4, -3)])
        vein(m, Fa, ja[:4], rnd)
        vein(m, Fb, jb[:4], rnd)
        for F, a0 in ((Fa, 2.6), (Fb, 0.1)):
            strap(m, F, a0, a0 + 0.28, 3.38, 3.98, rivets=2)
        return
    if "buttress" in pid:
        sl = 0.0375
        Fs = pier(m, rnd, 0, 1, -1, 0, [0, 1.0, 2.45, 3.0, 3.75], {"front": T, "left": sl, "right": sl}, {"front", "left", "right"}, par=1, flat=(1,))
        F = Fs["front"]
        glyph(m, F, 0.5, 1.72, 0.85, 0.006)
        for b in (0.86, 2.6):
            hb = b + 0.14
            strap(m, F, sl * b - 0.0, 1 - sl * b, b, hb, rivets=3)
            strap(m, Fs["left"], 0, 1 - T * b, b, hb, rivets=1)
            strap(m, Fs["right"], T * b, 1, b, hb, rivets=1)
        cap = 3.75
        xl, xr, zf = sl * cap - 0.05, 1 - sl * cap + 0.05, -T * cap + 0.05
        slab(m, [(xl, 4.0, zf), (xr, 4.0, zf), (xr, 4.0, -1), (xl, 4.0, -1)], 0.25, BASALT, 0.05, want=Y)
        strap_top(m, xl, xr, zf, -1, 4.0)
        return
    # outer corner and end cap: 1 m piers leaning on their two outer faces
    side = "left" if "outer" in pid else "right"
    Fs = pier(m, rnd, 0, 1, -1, 0, [0, 1.0, 2.45, 3.0, 3.5, 4.0], {"front": T, side: T}, {"front", side}, par=1, flat=(1,))
    F = Fs["front"]
    ca = (T * 1.7 + 1) / 2 if side == "left" else (1 - T * 1.7) / 2
    glyph(m, F, ca, 1.72, 0.78, 0.006)
    # iron corner cap: straps on both faces near the top, wrapping the arris
    if side == "left":
        strap(m, F, T * 3.5, T * 3.5 + 0.34, 3.55, 3.95, rivets=1)
        strap(m, Fs["left"], 1 - T * 3.5 - 0.34, 1 - T * 3.5, 3.55, 3.95, rivets=1)
    else:
        strap(m, F, 1 - T * 3.5 - 0.34, 1 - T * 3.5, 3.55, 3.95, rivets=1)
        strap(m, Fs["right"], T * 3.5, T * 3.5 + 0.34, 3.55, 3.95, rivets=1)
    j = [(b0, b1, [[0.05, 0.35, 0.6]]) for b0, b1 in zip([0, 1.0], [1.0, 2.45])]
    vein(m, Fs[side], j, rnd, steps=1)


def strap_top(m, x0, x1, z1, z0, y):
    slab(m, [(x0 + 0.02, y + 0.035, z1 - 0.02), (x1 - 0.02, y + 0.035, z1 - 0.02), (x1 - 0.02, y + 0.035, z0 + 0.02), (x0 + 0.02, y + 0.035, z0 + 0.02)],
         0.05, IRON, 0.015, want=Y)
    Ft = frame((0, y + 0.035, 0), X)
    for x, z in ((x0 + 0.1, z1 - 0.1), (x1 - 0.1, z1 - 0.1), (x0 + 0.1, z0 + 0.1), (x1 - 0.1, z0 + 0.1)):
        base = [Vector((x - 0.03, y + 0.035, z - 0.03)), Vector((x + 0.03, y + 0.035, z - 0.03)), Vector((x + 0.03, y + 0.035, z + 0.03)), Vector((x - 0.03, y + 0.035, z + 0.03))]
        tip = Vector((x, y + 0.065, z))
        for i in range(4):
            addf(m, [base[i], base[(i + 1) % 4], tip], IRON, Y)


# ---------- foundations, floors, stairs ----------

def build_foundation(p, m, rnd):
    w, h, d = p["size"]
    pid = p["id"]
    if "slope" in pid:
        lo, hi = 0.2, 1.0
        yl = lambda z: lo + (hi - lo) * (-z / d)  # noqa: E731
        th = 0.16
        prism(m, [(0, 0), (0, lo - th), (-d, hi - th), (-d, 0)], 0.02, w - 0.02)
        stone(m, frame((w, 0, -d), -X), [(0.004, 0.004), (w - 0.004, 0.004), (w - 0.004, hi - th), (0.004, hi - th)], rnd, BASALT, 0, 0.04, 0.2)
        for k in range(3):
            za, zb = -k, -(k + 1)
            cuts = split(0, w, rnd, k, 0.8, 1.3, 0.45)
            for c0, c1 in zip(cuts, cuts[1:]):
                g = 0.006
                dy = -rnd.uniform(0, 0.015)
                zA, zB = za - g, zb + g
                pts = [(c0 + g, yl(zA) + dy, zA), (c1 - g, yl(zA) + dy, zA), (c1 - g, yl(zB) + dy, zB), (c0 + g, yl(zB) + dy, zB)]
                rect = stone_rect(rnd, c1 - c0, 1.0)
                slab(m, pts, th, BASALT, 0.035, poly_uv([(c0, za), (c1, za), (c1, zb), (c0, zb)], rect)[::1], want=Y)
        for xs, F in ((0, frame((0, 0, -d), Z)), (w, frame((w, 0, 0), -Z))):
            for k in range(3):
                a0, a1 = k, k + 1
                if xs == 0:
                    ya, yb = yl(-d + a0) - th, yl(-d + a1) - th
                else:
                    ya, yb = yl(-a0) - th, yl(-a1) - th
                stone(m, F, [(a0 + .004, 0.004), (a1 - .004, 0.004), (a1 - .004, yb - .004), (a0 + .004, ya - .004)], rnd, BASALT, 0, 0.035, 0.2)
        return
    if "cliff" in pid:
        rows = [0, 1.0, 1.75, 2.45, 3.0, 3.5, 3.85]
        Fs = pier(m, rnd, 0, w, -d, 0, rows, {}, {"front"}, cst=0.1)
        paving(m, rnd, 0, w, -d, 0, h)
        F = Fs["front"]
        strap(m, F, 0, w, 3.5, 3.62, rivets=6)
        for a in (0.8, 2.2):
            anchor_plate(m, F, a, 3.15, 0.62, rnd)
        j = [(b0, b1, [[0, 0.6, 1.4, 2.3, 3]]) for b0, b1 in zip(rows[:4], rows[1:5])]
        vein(m, F, j, rnd, holes=[(0.4, 2.6, 2.7, 3.6)])
        return
    # plinth, floor tile, terrace step: a course of edge stones under a skin of flags
    top = 0.15
    if "floor" in pid:  # floor tiles sit inside terraces; their edges are plain dressed slab
        cube(m, (0.02, 0, -d + 0.02), (w - 0.02, h - top, -0.02))
        paving(m, rnd, 0, w, -d, 0, h, top)
        return
    Fs = pier(m, rnd, 0, w, -d, 0, [0, h - top], {}, {"front", "back", "left", "right"}, cst=0.04)
    paving(m, rnd, 0, w, -d, 0, h, top)
    if "plinth" in pid:
        j = [(0, h - top, [[0, 0.9, 1.9, 3]])]
        if rnd.random() < 0.8:
            vein(m, Fs["front"], j, rnd, steps=1)


def anchor_plate(m, F, a, b, s, rnd, ring=True):
    """Forged anchor: riveted plate, eye and hanging ring on face F centred at (a, b)."""
    h = s / 2
    slab(m, [F(a - h, b - h, 0.07), F(a + h, b - h, 0.07), F(a + h, b + h, 0.07), F(a - h, b + h, 0.07)], 0.1, IRON, 0.02, want=F.N)
    for da, db in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        rivet(m, F, a + da * (h - 0.07), b + db * (h - 0.07), 0.07, 0.03)
    eye = F(a, b + h * 0.35, 0.13)
    link(m, eye, Y, F.N, 0.22, 0.22, 0.04, CHAIN, 5, 8)
    if ring:
        R = s * 0.42
        link(m, eye - Y * (R - 0.04), X if abs(F.N.x) < 0.5 else Z, Y, 2 * R, 2 * R, 0.055, CHAIN, 6, 14)


def build_floor(p, m, rnd):
    if "stairs" in p["id"]:
        return build_stairs(p, m, rnd)
    build_foundation(p, m, rnd)


def build_stairs(p, m, rnd):
    w, h, d = p["size"]
    n = 6
    rise, run = h / n, d / n
    prof = []
    for k in range(1, n):
        prof += [(-k * run, (k - 1) * rise), (-k * run, k * rise)]
    prof += [(-d, (n - 1) * rise), (-d, 0)]
    clean = []
    for q in prof:
        if not clean or (abs(clean[-1][0] - q[0]) + abs(clean[-1][1] - q[1])) > 1e-6:
            clean.append(q)
    prism(m, clean, 0.03, w - 0.03)
    for k in range(n):
        cuts = [0, 1.5, w] if k % 2 == 0 else [0, 0.75, 2.25, w]
        y1 = (k + 1) * rise
        for c0, c1 in zip(cuts, cuts[1:]):
            g = 0.005
            za, zb = -k * run, -(k + 1) * run - (0.02 if k < n - 1 else 0)
            pts = [(c0 + g, y1, za - g), (c1 - g, y1, za - g), (c1 - g, y1, zb + g), (c0 + g, y1, zb + g)]
            slab(m, pts, rise + 0.02, BASALT, 0.035, poly_uv([(c0, za), (c1, za), (c1, zb), (c0, zb)], stone_rect(rnd, c1 - c0, run)), want=Y)


# ---------- roofs and crowns ----------

def build_roof(p, m, rnd):
    w, h, d = p["size"]
    pid = p["id"]
    if pid.endswith("roof-flat"):
        cube(m, (0.02, 0, -d + 0.02), (w - 0.02, 0.4, -0.02))
        paving(m, rnd, 0, w, -d, 0, 0.55)
        return
    if pid.endswith("roof-step"):
        Fs = pier(m, rnd, 0, w, -d, -d / 2, [0, 0.85], {}, {"front"})
        paving(m, rnd, 0, w, -d, -d / 2, 1.0)
        paving(m, rnd, 0, w, -d / 2, 0, 0.15, 0.15, rowlen=0.75)
        strap(m, Fs["front"], 0, w, 0.72, 0.84, rivets=6)
        for x0 in (0.08, w - 0.4):
            slab(m, [(x0, 1.03, -d / 2 - 0.02), (x0 + 0.32, 1.03, -d / 2 - 0.02), (x0 + 0.32, 1.03, -d / 2 - 0.4), (x0, 1.03, -d / 2 - 0.4)], 0.05, IRON, 0.012, want=Y)
        return
    if pid.endswith("roof-hip"):
        step, rise, base = 0.75, 0.18, 0.3
        for k in range(4):
            top = base + rise * k
            s = k * step
            strips = []
            if k < 3:
                strips.append(("f", s, w, -(s + step), -s))
                strips.append(("l", s, s + step, -d, -(s + step)))
            else:
                strips.append(("t", s, w, -d, -s))
            for kind, xa, xb, za, zb in strips:
                if kind == "l":
                    cuts = split(za, zb, rnd, k, 0.8, 1.2, 0.4)
                    segs = [(xa, xb, c0, c1) for c0, c1 in zip(cuts, cuts[1:])]
                else:
                    cuts = split(xa, xb, rnd, k, 0.8, 1.2, 0.4)
                    segs = [(c0, c1, za, zb) for c0, c1 in zip(cuts, cuts[1:])]
                for x0, x1, z0, z1 in segs:
                    g = 0.005
                    pts = [(x0 + g, top, z1 - g), (x1 - g, top, z1 - g), (x1 - g, top, z0 + g), (x0 + g, top, z0 + g)]
                    slab(m, pts, top, SLATE, 0.05, poly_uv([(x0, -z1), (x1, -z1), (x1, -z0), (x0, -z0)], stone_rect(rnd, x1 - x0, z1 - z0)), side=BASALT, want=Y)
            # iron corner cap where the step turns
            c = Vector((s, top + 0.03, -s))
            for a, b2 in (((0.34, 0.12), None), ((0.12, 0.34), None)):
                pts = [c + Vector((0.02, 0, -0.02)), c + Vector((a[0], 0, -0.02)), c + Vector((a[0], 0, -a[1])), c + Vector((0.02, 0, -a[1]))]
                slab(m, pts, 0.05, IRON, 0.012, want=Y)
            for q in ((0.1, -0.06), (0.26, -0.06), (0.06, -0.26)):
                bp = c + Vector((q[0], 0, q[1]))
                tip = bp + Vector((0, 0.03, 0))
                sq = [bp + Vector((-0.025, 0, -0.025)), bp + Vector((0.025, 0, -0.025)), bp + Vector((0.025, 0, 0.025)), bp + Vector((-0.025, 0, 0.025))]
                for i in range(4):
                    addf(m, [sq[i], sq[(i + 1) % 4], tip], IRON, Y)
        return
    if pid.endswith("parapet"):
        Ff = frame((0, 0, 0), X)
        Fb = frame((w, 0, -d), -X)
        for F in (Ff, Fb):
            masonry(m, F, 0, w, [0, 0.45], rnd, jit=0.015, depth=0.22, cst=0.04)
        cube(m, (0, 0, -d + 0.06), (w, 0.45, -0.06))
        strap(m, Ff, 0, w, 0.31, 0.42, rivets=6)
        merl = [(0, 0.75), (1.125, 1.875), (2.25, 3.0)]
        for i, (x0, x1) in enumerate(merl):
            blocks = {"front", "back"} | ({"left"} if x0 > 0 else set()) | ({"right"} if x1 < w else set())
            pier(m, rnd, x0, x1, -d, 0, [0.45, 0.88], {}, blocks, y0=0.0, cst=0.03, flat=(0,))
            slab(m, [(x0 + .005, 1.0, -0.005), (x1 - .005, 1.0, -0.005), (x1 - .005, 1.0, -d + .005), (x0 + .005, 1.0, -d + .005)], 0.12, BASALT, 0.04,
                 poly_uv([(x0, 0), (x1, 0), (x1, d), (x0, d)], stone_rect(rnd, x1 - x0, d)), want=Y)
            if i == 1:
                glyph(m, Ff, 1.5, 0.665, 0.36, 0.004)
        return
    if pid.endswith("chimney"):
        hw = w / 2
        sl = 0.06
        Fs = pier(m, rnd, -hw, hw, -hw, hw, [0, 0.55, 1.05, 1.45], {"front": sl, "back": sl, "left": sl, "right": sl}, set(ORDER), flat=(1,))
        glyph(m, Fs["front"], hw, 0.8, 0.42, 0.006)
        t = hw - sl * 1.45
        # vent course: corner posts, glowing fire slots, iron cage
        y0, y1 = 1.45, 1.85
        for sx in (-1, 1):
            for sz in (-1, 1):
                cx, cz = sx * (t - 0.14), sz * (t - 0.14)
                cube(m, (cx - 0.14, y0, cz - 0.14), (cx + 0.14, y1, cz + 0.14))
        cube(m, (-t + 0.25, y0, -t + 0.25), (t - 0.25, y1, t - 0.25), GLOW)
        for k in range(4):
            ang = k * math.pi / 2
            A = Vector((math.cos(ang), 0, -math.sin(ang)))
            Nn = A.cross(Y)
            for a in (-0.18, 0.0, 0.18):
                c = Nn * (t - 0.06) + A * a
                cube(m, (c.x - 0.025, y0, c.z - 0.025), (c.x + 0.025, y1, c.z + 0.025), IRON)
        # iron cap plate and flue collar
        slab(m, [(-t - 0.06, 1.95, t + 0.06), (t + 0.06, 1.95, t + 0.06), (t + 0.06, 1.95, -t - 0.06), (-t - 0.06, 1.95, -t - 0.06)], 0.1, IRON, 0.02, want=Y)
        tube(m, [Vector((0, 1.94, 0)), Vector((0, 2.0, 0))], [0.24, 0.24], IRON, 8, caps=(False, True), cap_mat=IRON)
        return


def build_crown(p, m, rnd, mats=None):
    pid = p["id"]
    if pid.endswith("crystal"):
        sl = 0.12
        Fs = pier(m, rnd, -1, 1, -1, 1, [0, 0.55, 1.1], {f: sl for f in ORDER}, set(ORDER), flat=(0, 1))
        glyph(m, Fs["front"], 1.0, 0.55, 0.62, 0.006)
        t = 1 - sl * 1.1
        # iron collar: eight riveted plates and teeth around a stone bed
        R = 0.72
        cube(m, (-t + 0.02, 1.1, -t + 0.02), (t - 0.02, 1.2, t - 0.02))
        for k in range(8):
            a0, a1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
            p0 = Vector((math.cos(a0) * R, 1.18, math.sin(a0) * R))
            p1 = Vector((math.cos(a1) * R, 1.18, math.sin(a1) * R))
            Fk = frame(p0, p1 - p0)
            if Fk.N.dot(p0 + p1) < 0:
                Fk = frame(p1, p0 - p1)
            L = (p1 - p0).length
            slab(m, [Fk(0, 0, 0.06), Fk(L, 0, 0.06), Fk(L, 0.36, 0.06), Fk(0, 0.36, 0.06)], 0.12, IRON, 0.015, want=Fk.N)
            rivet(m, Fk, L * 0.3, 0.18, 0.06)
            rivet(m, Fk, L * 0.7, 0.18, 0.06)
            slab(m, [Fk(L * 0.3, 0.36, 0.05), Fk(L * 0.7, 0.36, 0.05), Fk(L * 0.7, 0.52, 0.05), Fk(L * 0.3, 0.52, 0.05)], 0.1, IRON, 0.015, want=Fk.N)
        disc_y = 1.32
        K.disc(m, (0, 1.18, 0), R - 0.05, disc_y - 1.18, BASALT, BASALT, 8)
        crystal(m, (0, disc_y - 0.05, 0), (0.02, 1, 0.03), 0.27, 0.78, 0.36, rnd)
        for k, (a, r, hh, tilt) in enumerate([(0.3, 0.17, 0.48, 0.38), (2.2, 0.15, 0.4, 0.42), (3.9, 0.19, 0.55, 0.32), (5.2, 0.12, 0.3, 0.5)]):
            d = Vector((math.cos(a), 0, math.sin(a)))
            crystal(m, d * 0.32 + Vector((0, disc_y - 0.06, 0)), d * tilt + Y, r, hh, r * 1.3, rnd)
        return
    # dome segment, quarter: centre at the back-left corner so four turn into one 6 m dome
    C = Vector((0, 0, -3))
    prof = []  # (R, y, material, tag)
    prof += [(3.0, 0.0, BASALT), (3.0, 0.1, BASALT), (2.96, 0.12, LEDGER), (2.96, 0.55, BASALT), (3.0, 0.57, BASALT), (3.0, 0.64, SLATE)]
    a, b, y0 = 2.86, 0.86, 0.64
    courses = 5
    for c in range(courses):
        f0, f1 = (math.pi / 2) * c / courses, (math.pi / 2) * (c + 1) / courses * (0.999 if c == courses - 1 else 1)
        lip = 1.02 if c > 0 else 1.0
        for k in range(3):
            f = f0 + (f1 - f0) * k / 2
            R, yy = a * math.cos(f), y0 + b * math.sin(f)
            prof.append((R * (lip if k == 0 else 1.0) + (0.03 if k == 0 and c > 0 else 0), yy, SLATE))
    prof.append((0.0, y0 + b, SLATE))
    nseg = 10
    th = [math.pi / 2 * s / nseg for s in range(nseg + 1)]

    def P(R, yy, t):
        return C + Vector((R * math.cos(t), yy, R * math.sin(t)))
    acc = 0.0
    vs = [0.0]
    for i in range(len(prof) - 1):
        acc += math.hypot(prof[i + 1][0] - prof[i][0], prof[i + 1][1] - prof[i][1])
        vs.append(acc)
    for i in range(len(prof) - 1):
        (R0, y0_, mat), (R1, y1_, _) = prof[i], prof[i + 1]
        for s in range(nseg):
            q = [P(R0, y0_, th[s]), P(R0, y0_, th[s + 1]), P(R1, y1_, th[s + 1]), P(R1, y1_, th[s])]
            mid = (q[0] + q[2]) / 2
            out = Vector((mid.x - C.x, 0, mid.z - C.z)).normalized() * (1 if R1 <= R0 + 1e-6 or y1_ == y0_ else 1) + Y * 0.3
            if mat == LEDGER:
                u0 = (s % 2) * 0.5
                uv = [(u0, 0), (u0 + 0.5, 0), (u0 + 0.5, 1), (u0, 1)]
            else:
                uv = [(R0 * th[s] / 1.6, vs[i] / 1.6), (R0 * th[s + 1] / 1.6, vs[i] / 1.6), (R1 * th[s + 1] / 1.6 + 0.001, vs[i + 1] / 1.6), (R1 * th[s] / 1.6, vs[i + 1] / 1.6)]
            if (q[2] - q[1]).length < 1e-6:
                addf(m, [q[0], q[1], q[3]], mat, out, [uv[0], uv[1], uv[3]])
            else:
                addf(m, q, mat, out, uv)
    # inner shell, cut faces and bottom ring so the quarter reads solid
    inner = [(max(R * 0.9 - 0.1, 0.0), yy * 0.82) for R, yy, _ in prof[::3]] + [(0.0, (y0 + b) * 0.82)]
    for i in range(len(inner) - 1):
        (R0, y0_), (R1, y1_) = inner[i], inner[i + 1]
        for s in range(nseg):
            q = [P(R0, y0_, th[s]), P(R0, y0_, th[s + 1]), P(R1, y1_, th[s + 1]), P(R1, y1_, th[s])]
            mid = (q[0] + q[2]) / 2
            inward = -Vector((mid.x - C.x, 0, mid.z - C.z)).normalized() - Y * 0.3
            addf(m, q if (q[2] - q[1]).length > 1e-6 else [q[0], q[1], q[3]], BASALT, inward, None, 1.5)
    outer_pts = [(R, yy) for R, yy, _ in prof]
    for t, want in ((th[0], -Z), (th[-1], -X)):
        loop = [P(R, yy, t) for R, yy in outer_pts] + [P(R, yy, t) for R, yy in inner[::-1]]
        # triangulate as a strip between outer and inner profiles
        for i in range(len(inner) - 1):
            oi = min(i * 3, len(outer_pts) - 1)
            oj = min((i + 1) * 3, len(outer_pts) - 1)
            seg = [P(*outer_pts[k], t) for k in range(oi, oj + 1)]
            addf(m, seg + [P(*inner[i + 1], t), P(*inner[i], t)], BASALT, want, None, 1.5)
    for s in range(nseg):
        addf(m, [P(3.0, 0, th[s]), P(3.0, 0, th[s + 1]), P(inner[0][0], 0, th[s + 1]), P(inner[0][0], 0, th[s])], BASALT, -Y, None, 1.5)
    # iron meridian ribs and rivets over the band
    for t in (math.radians(22.5), math.radians(67.5)):
        pts = []
        for k in range(9):
            f = (math.pi / 2) * k / 8 * 0.96
            pts.append(P(a * math.cos(f) + 0.06, y0 + b * math.sin(f) + 0.02, t))
        pts = [P(3.03, 0.6, t)] + pts
        tube(m, pts, [0.07] * len(pts), IRON, 4, caps=(True, True))
    Fb = None
    for k in range(nseg):
        t = (th[k] + th[k + 1]) / 2
        base = P(2.985, 0.335, t)
        Nn = Vector((math.cos(t), 0, math.sin(t)))
        tip = base + Nn * 0.035
        A = Vector((-math.sin(t), 0, math.cos(t)))
        if k % 2 == 0:
            continue
        sq = [base - A * 0.03 - Y * 0.03, base + A * 0.03 - Y * 0.03, base + A * 0.03 + Y * 0.03, base - A * 0.03 + Y * 0.03]
        for i in range(4):
            addf(m, [sq[i], sq[(i + 1) % 4], tip], IRON, Nn)


# ---------- inserts ----------

FD = frame((0, 0, -0.2), X)  # door leaves: front of the planks 0.2 m behind the insert's front


def plank_poly(x0, x1, top, n=3):
    return [(x0, 0.0), (x1, 0.0)] + [(x1 + (x0 - x1) * k / n, top(x1 + (x0 - x1) * k / n)) for k in range(n + 1)]


def door_leaves(m, rnd, xa, xb, top, F=FD, gap=0.012):
    n = max(1, round((xb - xa) / 0.36))
    wq = (xb - xa) / n
    for k in range(n):
        x0, x1 = xa + k * wq + gap / 2, xa + (k + 1) * wq - gap / 2
        u = rnd.randrange(3) / 3
        poly = plank_poly(x0, x1, lambda x: top(x) - 0.01)
        slab(m, [F(a, b, -rnd.uniform(0, 0.012)) for a, b in poly], 0.16, OAK, 0.018, poly_uv(poly, (u + 0.02, 0.0, u + 0.31, 1.0)), want=F.N)


def door_strap(m, F, x0, x1, b, hinge="left", hw=0.065, rivets=4):
    tip = 0.16
    if hinge == "left":
        poly = [(x0, b - hw), (x1 - tip, b - hw), (x1, b), (x1 - tip, b + hw), (x0, b + hw)]
    else:
        poly = [(x0 + tip, b - hw), (x1, b - hw), (x1, b + hw), (x0 + tip, b + hw), (x0, b)]
    strap(m, F, x0 + 0.1, x1 - 0.1, b - hw, b + hw, rivets=rivets, poly=poly, ch=0.0)


def build_insert(p, m, rnd):
    w, h, _ = p["size"]
    pid = p["id"]
    if "doorpost" in pid:
        F = FR
        stone(m, F, [(0.01, 0.0), (0.49, 0.0), (0.49, 0.36), (0.01, 0.36)], rnd, BASALT, -0.01, 0.04, 0.28)
        stone(m, F, [(0.04, 0.37), (0.46, 0.37), (0.46, 2.83), (0.04, 2.83)], rnd, BASALT, -0.04, 0.035, 0.25)
        stone(m, F, [(0.0, 2.84), (0.5, 2.84), (0.5, 3.2), (0.0, 3.2)], rnd, BASALT, 0.0, 0.045, 0.3)
        glyph(m, F, 0.25, 1.6, 1.25, -0.036, sx=0.36)
        strap(m, F, 0.04, 0.46, 2.66, 2.8, n=-0.04, rivets=2)
        return
    if "door" in pid:
        top = lambda x: 2.2 + math.sqrt(max(0.0, 1 - (x - 1) ** 2))  # noqa: E731
        outline = arch_outline(1, 2.2, 1.0, 12)
        addf(m, [FD(a, b, -0.17) for a, b in outline], OAK, FD.N)
        if pid.endswith("ledger"):
            poly = arch_outline(1, 2.2, 0.99, 12)
            slab(m, [FD(a, b, 0) for a, b in poly], 0.2, SLATE, 0.05, poly_uv(poly, (0.05, 0.0, 0.95, 1.0)), side=BASALT, want=FD.N)
            for b0 in (0.32, 0.86):
                stone(m, FD, [(0.22, b0), (1.78, b0), (1.78, b0 + 0.46), (0.22, b0 + 0.46)], rnd, LEDGER, 0.012, 0.015, 0.05, rect=(0, 0, 1, 1), side=BASALT)
            glyph(m, FD, 1.0, 2.0, 1.05, 0.004)
            ribbon(m, FD, outline[1:-1], 0.09, 0.012, IRON)
            link(m, FD(1.62, 1.55, 0.1), X, Y, 0.3, 0.3, 0.035, CHAIN, 6, 12)
            slab(m, [FD(1.54, 1.62, 0.04), FD(1.7, 1.62, 0.04), FD(1.7, 1.78, 0.04), FD(1.54, 1.78, 0.04)], 0.05, IRON, 0.01, want=FD.N)
            return
        double = pid.endswith("double")
        if double:
            door_leaves(m, rnd, 0, 1.0, top)
            door_leaves(m, rnd, 1.0, 2.0, top)
            for b in (0.5, 1.15, 2.35):
                x0, x1 = 1 - math.sqrt(max(0, 1 - max(0, b - 2.2) ** 2)) + 0.06, 1 + math.sqrt(max(0, 1 - max(0, b - 2.2) ** 2)) - 0.06
                door_strap(m, FD, x0, 0.97, b, "right", rivets=2)
                door_strap(m, FD, 1.03, x1, b, "left", rivets=2)
            strap(m, FD, 0.96, 1.04, 0.08, 3.0, rivets=0)
            # locking chain bar across both leaves, between two forged staples
            yb = 1.62
            for x in (0.3, 1.7):
                slab(m, [FD(x - 0.1, yb - 0.17, 0.04), FD(x + 0.1, yb - 0.17, 0.04), FD(x + 0.1, yb + 0.17, 0.04), FD(x - 0.1, yb + 0.17, 0.04)], 0.05, IRON, 0.012, want=FD.N)
            nl = 4
            for k in range(nl):
                x = 0.42 + k * (1.16 / (nl - 1))
                link(m, FD(x, yb, 0.12), X, Y if k % 2 else Z, 0.44, 0.24, 0.04, CHAIN, 5, 8)
            cube(m, tuple(FD(0.9, yb - 0.32, 0.07)), tuple(FD(1.1, yb - 0.12, 0.2)), IRON)
        else:
            door_leaves(m, rnd, 0, 2.0, top)
            for b in (0.5, 1.5, 2.55):
                half = math.sqrt(max(0, 1 - max(0, b + 0.07 - 2.2) ** 2))
                door_strap(m, FD, 1 - half + 0.04, 1 + half - 0.04, b, "right")
            link(m, FD(1.58, 1.3, 0.1), X, Y, 0.3, 0.3, 0.035, CHAIN, 6, 12)
            slab(m, [FD(1.5, 1.38, 0.04), FD(1.66, 1.38, 0.04), FD(1.66, 1.54, 0.04), FD(1.5, 1.54, 0.04)], 0.05, IRON, 0.01, want=FD.N)
        ribbon(m, FD, outline[1:-1], 0.08, 0.03, IRON)
        return
    # windows: local origin at the 2 x 2 opening's bottom-left, 1 m above the wall's base
    FW = frame((0, 0, -T), X, T)
    if "arched" in pid:
        for x0, x1 in ((0, 0.25), (1.75, 2.0)):
            for b0, b1 in ((0, 0.5), (0.5, 1.0)):
                stone(m, FW, [(x0 + .004, b0 + .004), (x1 - .004, b0 + .004), (x1 - .004, b1 - .004), (x0 + .004, b1 - .004)], rnd, BASALT, 0.02, 0.035, 0.75)
        arch_wedges(m, FW, 1.0, 1.0, 0.75, 0.0, 2.0, 2.0, 5, rnd, 0.75, n=0.02)
        stone(m, FW, [(-0.08, -0.12), (2.08, -0.12), (2.08, 0.05), (-0.08, 0.05)], rnd, BASALT, 0.1, 0.03, 0.5)
        glass = arch_outline(1.0, 1.0, 0.75, 10)
        addf(m, [Vector((a, b, -0.62)) for a, b in glass], GLOW, Z)
        topw = lambda x: 1.0 + math.sqrt(max(0.0, 0.5625 - (x - 1.0) ** 2))  # noqa: E731
        for x in (0.75, 1.25):
            cube(m, (x - 0.025, 0, -0.6), (x + 0.025, topw(x), -0.54), IRON)
        for yb in (0.55, 1.2):
            half = math.sqrt(max(0, 0.5625 - max(0, yb - 1.0) ** 2))
            cube(m, (1 - half, yb - 0.025, -0.6), (1 + half, yb + 0.025, -0.54), IRON)
        # open oak shutters on forged hinges
        c20, s20 = math.cos(math.radians(55)), math.sin(math.radians(55))
        zh = -T * 1.8 + 0.06
        for side in ("L", "R"):
            if side == "L":
                Ao = Vector((-c20, 0, s20))
                F = frame(Vector((0.25, 0, zh)) + Ao * 0.75, -Ao)
                tp = lambda a: 1.0 + math.sqrt(max(0.0, 0.5625 - a * a))  # noqa: E731
            else:
                Ao = Vector((c20, 0, s20))
                F = frame(Vector((1.75, 0, zh)), Ao)
                tp = lambda a: 1.0 + math.sqrt(max(0.0, 0.5625 - (0.75 - a) ** 2))  # noqa: E731
            for k in range(3):
                a0, a1 = k * 0.25 + 0.006, (k + 1) * 0.25 - 0.006
                poly = [(a0, 0.05), (a1, 0.05), (a1, tp(a1) - 0.04), (a0, tp(a0) - 0.04)]
                u = rnd.randrange(3) / 3
                slab(m, [F(a, b, 0) for a, b in poly], 0.07, OAK, 0.012, poly_uv(poly, (u + 0.02, 0.05, u + 0.31, 0.75)), want=F.N)
            for b in (0.35, 1.25):
                strap(m, F, 0.04, 0.71, b - 0.05, b + 0.05, rivets=2)
        return
    if "slit" in pid:
        rows = [0, 0.35, 1.05, 1.75, 2.0]
        j = masonry(m, FW, 0, 2.0, rows, rnd, holes=[(0.8, 1.2, 0.35, 1.75)], n=0.02, depth=0.72, jit=0.015, cst=0.08)
        addf(m, [Vector((0.8, 0.35, -0.8)), Vector((1.2, 0.35, -0.8)), Vector((1.2, 1.75, -0.8)), Vector((0.8, 1.75, -0.8))], GLOW, Z)
        for x in (0.93, 1.07):
            cube(m, (x - 0.022, 0.35, -0.62), (x + 0.022, 1.75, -0.56), IRON)
        for yb in (0.7, 1.05, 1.4):
            cube(m, (0.8, yb - 0.022, -0.62), (1.2, yb + 0.022, -0.56), IRON)
        ribbon(m, FW, [(0.76, 0.33), (0.76, 1.79), (1.24, 1.79), (1.24, 0.33), (0.76, 0.33)], 0.06, 0.03, IRON)
        return
    # wide window, triple stone mullion: infill courses below a glazing band
    masonry(m, FW, 0, 2.0, [0, 0.5, 0.92], rnd, n=0.02, depth=0.72, jit=0.015)
    stone(m, FW, [(-0.06, 0.92), (2.06, 0.92), (2.06, 1.04), (-0.06, 1.04)], rnd, BASALT, 0.09, 0.025, 0.5)
    lights = [(0.2, 0.64), (0.78, 1.22), (1.36, 1.8)]
    edges = [0.0] + [x for l in lights for x in l] + [2.0]
    for x0, x1 in zip(edges[::2], edges[1::2]):
        stone(m, FW, [(x0 + .004, 1.044), (x1 - .004, 1.044), (x1 - .004, 1.746), (x0 + .004, 1.746)], rnd, BASALT, 0.02, 0.03, 0.72)
    stone(m, FW, [(0.004, 1.75), (1.996, 1.75), (1.996, 1.996), (0.004, 1.996)], rnd, BASALT, 0.03, 0.04, 0.72)
    for x0, x1 in lights:
        addf(m, [Vector((x0, 1.04, -0.62)), Vector((x1, 1.04, -0.62)), Vector((x1, 1.75, -0.62)), Vector((x0, 1.75, -0.62))], GLOW, Z)
        xm = (x0 + x1) / 2
        cube(m, (xm - 0.02, 1.04, -0.6), (xm + 0.02, 1.75, -0.55), IRON)
        cube(m, (x0, 1.38, -0.6), (x1, 1.42, -0.55), IRON)


def build_trim(p, m, rnd):
    w, h, d = p["size"]
    pid = p["id"]
    F = frame((0, 0, 0), X)
    if pid.endswith("straight"):
        for a0, a1 in ((0, 1.5), (1.5, 3.0)):
            stone(m, F, [(a0 + .004, 0.004), (a1 - .004, 0.004), (a1 - .004, 0.496), (a0 + .004, 0.496)], rnd, LEDGER, 0, 0.03, 0.5, rect=(0, 0, 1, 1), side=BASALT)
        return
    if pid.endswith("corner"):
        # the band turns over the corner pier: one block where the front and side runs meet, glyphs on both faces
        x0, x1, z0, z1 = 0.5, 1.0, -1.0, -0.5
        u0 = rnd.choice((0.0, 0.33, 0.66))
        q = lambda pts: [Vector(p_) for p_ in pts]  # noqa: E731
        addf(m, q([(x0, 0, z1), (x1, 0, z1), (x1, h, z1), (x0, h, z1)]), LEDGER, Z, [(u0, 0), (u0 + 0.25, 0), (u0 + 0.25, 1), (u0, 1)])
        addf(m, q([(x0, 0, z0), (x0, 0, z1), (x0, h, z1), (x0, h, z0)]), LEDGER, -X, [(u0 + 0.25, 0), (u0 + 0.5, 0), (u0 + 0.5, 1), (u0 + 0.25, 1)])
        addf(m, q([(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]), BASALT, Y)
        addf(m, q([(x0, 0, z1), (x1, 0, z1), (x1, 0, z0), (x0, 0, z0)]), BASALT, -Y)
        addf(m, q([(x1, 0, z1), (x1, 0, z0), (x1, h, z0), (x1, h, z1)]), BASALT, X)
        addf(m, q([(x0, 0, z0), (x1, 0, z0), (x1, h, z0), (x0, h, z0)]), BASALT, -Z)
        Ff = frame((x0, 0, z1), X)
        Fl = frame((x0, 0, z0), Z)
        strap(m, Ff, 0.0, 0.14, 0.03, 0.47, rivets=1)
        strap(m, Fl, 0.36, 0.5, 0.03, 0.47, rivets=1)
        return
    # end cap: carved block with an oath-mark
    stone(m, F, [(0.004, 0.004), (0.496, 0.004), (0.496, 0.496), (0.004, 0.496)], rnd, BASALT, 0, 0.04, 0.5)
    glyph(m, F, 0.25, 0.25, 0.36, 0.003)
    for a, b in ((0.07, 0.07), (0.43, 0.07), (0.43, 0.43), (0.07, 0.43)):
        rivet(m, F, a, b, -0.01, 0.025)


# ---------- attachments ----------

def build_attachment(p, m, rnd):
    w, h, d = p["size"]
    pid = p["id"]
    if pid.endswith("chain-run"):
        L, W, r = 0.975, 0.55, 0.075
        for i in range(4):
            link(m, (L / 2 + i * (L - 4 * r), 0.3, -0.3), X, Y if i % 2 == 0 else Z, L, W, r, CHAIN, 8, 16)
        return
    if pid.endswith("chain-bend"):
        L, W, r = 0.975, 0.55, 0.075
        c = Vector((0.45, 0.45, -0.3))
        R = 0.75
        specs = [((L / 2, 1.2, -0.3), X, Y), (c + Vector((math.cos(math.pi / 4), math.sin(math.pi / 4), 0)) * R, Vector((1, -1, 0)), Z),
                 ((1.2, L / 2, -0.3), -Y, X)]
        for cc, dd, uu in specs:
            link(m, cc, dd, uu, L, W, r, CHAIN, 8, 16)
        return
    if pid.endswith("chain-anchor"):
        F = frame((0, 0, -0.6 + T), X, T)
        anchor_plate(m, F, 0.5, 0.62, 0.86, rnd)
        return
    if pid.endswith("mooring-ring"):
        sl = 0.08
        Fs = pier(m, rnd, -0.6, 0.6, -0.6, 0.6, [0, 0.55, 1.1], {f: sl for f in ORDER}, set(ORDER), flat=(1,))
        t = 0.6 - sl * 1.1
        hexa(m, [(-t - 0.05, 1.1, t + 0.05), (t + 0.05, 1.1, t + 0.05), (t + 0.05, 1.1, -t - 0.05), (-t - 0.05, 1.1, -t - 0.05)],
             [(-t - 0.05, 1.2, t + 0.05), (t + 0.05, 1.2, t + 0.05), (t + 0.05, 1.2, -t - 0.05), (-t - 0.05, 1.2, -t - 0.05)], IRON, 1.0)
        apex = Vector((0, 1.48, 0))
        base = [Vector((-t, 1.2, t)), Vector((t, 1.2, t)), Vector((t, 1.2, -t)), Vector((-t, 1.2, -t))]
        for i in range(4):
            addf(m, [base[i], base[(i + 1) % 4], apex], IRON, (base[i] + base[(i + 1) % 4]) / 2 + Y * 0.3)
        F = Fs["front"]
        a = 0.6
        slab(m, [F(a - 0.16, 0.66, 0.05), F(a + 0.16, 0.66, 0.05), F(a + 0.16, 0.98, 0.05), F(a - 0.16, 0.98, 0.05)], 0.08, IRON, 0.015, want=F.N)
        eye = F(a, 0.86, 0.12)
        link(m, eye, Y, Z, 0.2, 0.2, 0.04, CHAIN, 6, 10)
        link(m, eye - Y * 0.33 + Z * 0.02, X, Y, 0.62, 0.62, 0.065, CHAIN, 8, 18)
        strap(m, F, sl * 0.3, 1.2 - sl * 0.3, 0.3, 0.42, rivets=4)
        return
    if "lantern" in pid:
        post = pid.endswith("post")
        if post:
            sl = 0.05
            Fs = pier(m, rnd, -0.4, 0.4, -0.4, 0.4, [0, 0.45, 0.9], {f: sl for f in ORDER}, set(ORDER), flat=(1,))
            glyph(m, Fs["front"], 0.4, 0.66, 0.36, 0.005)
            cube(m, (-0.33, 0.9, -0.33), (0.33, 1.0, 0.33), IRON, 1.0)
            cube(m, (-0.07, 1.0, -0.07), (0.07, 2.25, 0.07), IRON, 1.0)
            for yb in (1.2, 2.05):
                cube(m, (-0.1, yb, -0.1), (0.1, yb + 0.07, 0.1), IRON, 1.0)
            lc = Vector((0, 2.3, 0))
        else:
            cube(m, (-0.14, 0.82, -0.6), (0.14, 1.36, -0.53), IRON, 1.0)
            for yy in (0.9, 1.28):
                Fp = frame((0, 0, -0.53), X)
                rivet(m, Fp, 0.0, yy, 0.0, 0.03)
            cube(m, (-0.04, 1.2, -0.53), (0.04, 1.28, 0.32), IRON, 1.0)
            tube(m, [Vector((0, 0.86, -0.53)), Vector((0, 1.05, -0.3)), Vector((0, 1.2, -0.05))], [0.03] * 3, IRON, 4)
            tube(m, [Vector((0, 1.2, 0.28)), Vector((0, 1.08, 0.28))], [0.02] * 2, IRON, 4)
            lc = Vector((0, 0.28, 0.28))
        # cage: tray, four corner bars, two rings, pyramid cap and finial around a teal crystal
        s = 0.2
        cube(m, tuple(lc + Vector((-s - 0.03, 0, -s - 0.03))), tuple(lc + Vector((s + 0.03, 0.07, s + 0.03))), IRON, 1.0)
        for sx in (-1, 1):
            for sz in (-1, 1):
                cube(m, tuple(lc + Vector((sx * s - 0.025, 0.07, sz * s - 0.025))), tuple(lc + Vector((sx * s + 0.025, 0.6, sz * s + 0.025))), IRON, 1.0)
        for yy in (0.3,):
            for k in range(4):
                a = k * math.pi / 2
                A = Vector((math.cos(a), 0, -math.sin(a)))
                Nn = A.cross(Y)
                c = lc + Nn * s + Y * yy
                cube(m, tuple(c - A * s - Vector((0.012, 0.015, 0.012))), tuple(c + A * s + Vector((0.012, 0.015, 0.012))), IRON, 1.0)
        base = [lc + Vector((-s - 0.05, 0.6, s + 0.05)), lc + Vector((s + 0.05, 0.6, s + 0.05)), lc + Vector((s + 0.05, 0.6, -s - 0.05)), lc + Vector((-s - 0.05, 0.6, -s - 0.05))]
        apex = lc + Vector((0, 0.82, 0))
        for i in range(4):
            addf(m, [base[i], base[(i + 1) % 4], apex], IRON, (base[i] + base[(i + 1) % 4]) / 2 - lc)
        addf(m, base, IRON, -Y)
        link(m, apex + Y * 0.06, X, Y, 0.12, 0.12, 0.02, CHAIN, 5, 8)
        crystal(m, lc + Vector((0, 0.07, 0)), (0.05, 1, 0.0), 0.1, 0.32, 0.12, rnd)
        crystal(m, lc + Vector((0.06, 0.07, 0.04)), (0.4, 1, 0.2), 0.06, 0.18, 0.08, rnd)
        return
    if "bracket" in pid:
        roof = pid.endswith("roof")
        cx = w / 2
        top = h
        Fp = frame((cx - 0.2, 0, -d), X)
        ph = (0.0, top) if not roof else (top - 0.55, top)
        slab(m, [Fp(0, ph[0], 0.08), Fp(0.4, ph[0], 0.08), Fp(0.4, ph[1], 0.08), Fp(0, ph[1], 0.08)], 0.08, IRON, 0.015, want=Z)
        for b in (ph[0] + 0.12, ph[1] - 0.12):
            for a in (0.09, 0.31):
                rivet(m, Fp, a, b, 0.08, 0.03)
        cube(m, (cx - 0.07, top - 0.14, -d + 0.08), (cx + 0.07, top, -0.05), IRON, 1.0)
        tip = [Vector((cx - 0.07, top - 0.14, -0.05)), Vector((cx + 0.07, top - 0.14, -0.05)), Vector((cx + 0.07, top, -0.05)), Vector((cx - 0.07, top, -0.05))]
        y0b, dy, dz = ph[0] + 0.12, top - 0.14 - ph[0] - 0.12, d - 0.65
        brace = [Vector((cx, y0b + dy * math.sin(math.pi / 2 * k / 6), -d + 0.1 + dz * (1 - math.cos(math.pi / 2 * k / 6)))) for k in range(7)]
        tube(m, brace, [0.045] * len(brace), IRON, 4)
        # scroll curl at the tip and a hanging ring for loads
        tube(m, [Vector((cx, top, -0.05)), Vector((cx, top + 0.04, 0.0)), Vector((cx, top - 0.06, 0.04)), Vector((cx, top - 0.14, 0.0))], [0.04] * 4, IRON, 4)
        if not roof:
            link(m, Vector((cx, top - 0.38, -0.25)), Z, Y, 0.34, 0.34, 0.035, CHAIN, 6, 12)
        return


# ---------- dispatch ----------

def finish(m, name, mats, seed=0.0, moss=0.62):
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m.project = [(f, t) for f, t in m.project if f.is_valid]
    bm.normal_update()
    for f, tile in m.project:
        K.box_uv(f, m.uv, tile)
    if moss is not None:
        for f in bm.faces:
            if f.material_index == BASALT and f.normal.z > moss and noise.noise(f.calc_center_median() * 0.7 + Vector((seed, seed, 0))) > 0.2:
                f.material_index = MOSS
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    for poly in me.polygons:
        poly.use_smooth = poly.material_index == CHAIN
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


BUILDERS = {"wall": build_wall, "corner": build_corner, "foundation": build_foundation, "floor": build_floor, "access": build_floor,
            "roof": build_roof, "crown": build_crown, "insert": build_insert, "trim": build_trim, "attachment": build_attachment}


def build_piece(p, mats):
    s = sum(map(ord, p["id"]))
    rnd = random.Random(s * 7919)
    m = Mesh()
    BUILDERS[p["family"]](p, m, rnd)
    return finish(m, p["id"], mats, seed=(s % 97) * 0.37)


def preview(ids, path, cols=4):
    """Close-up contact sheet of a few pieces (development aid): ANK_PREVIEW=id,id ANK_OUT=file.png"""
    mats = K.reset()
    objs, x, y, row = [], 0.0, 0.0, 0.0
    for k, pid in enumerate(ids):
        p = B.PIECES[pid]
        w, _, d = p["size"]
        if k and k % cols == 0:
            x, y, row = 0.0, y - row - 1.5, 0.0
        ob = build_piece(p, mats)
        ob.location += Vector((x + (w / 2 if p["pivot"] == "bottom-center" else 0), y, 0))
        objs.append(ob)
        x += w + 1.2
        row = max(row, d)
    bpy.context.view_layer.update()
    B.render(path, B.bounds(objs), "TEXTURE")


if os.environ.get("ANK_PREFAB"):
    mats = K.reset()
    f = next(f for f in B.kit["prefabs"] if f["id"] == os.environ["ANK_PREFAB"])
    parts = K.place_layout(f["layout"], build_piece, mats)
    parts.append(B.figure(Vector((-2, 2, 0))))
    bpy.context.view_layer.update()
    B.render(os.environ["ANK_OUT"], B.bounds(parts), "TEXTURE")
elif os.environ.get("ANK_PREVIEW"):
    want = os.environ["ANK_PREVIEW"].split(",")
    preview([p["id"] for p in B.kit["pieces"] if any(w in p["id"] for w in want)], os.environ["ANK_OUT"], int(os.environ.get("ANK_COLS", 4)))
elif __name__ == "__main__" or True:
    only = os.environ.get("ANK_ONLY")
    if only:  # quick look at a few pieces: ANK_ONLY=id,id
        ids = only.split(",")
        B.kit["pieces"] = [p for p in B.kit["pieces"] if any(i in p["id"] for i in ids)]
        B.kit["prefabs"] = [] if not os.environ.get("ANK_PREFABS") else B.kit["prefabs"]
    K.build_all(build_piece, extras=[("ank-lantern-post", "prop"), ("ank-lantern-wall", "hanging"),
                                     ("ank-mooring-ring", "decor"), ("ank-crown-crystal", "decor")], biome="crag")
