# Detailed Galeborne kit: silvered timber frames, overlapping shingle rows, cream sailcloth on curved ribs, rope
# lashings and brass fittings, built from kit.json on the 2 m module / 3 m storey grid. Exports every piece, joined
# prefabs from each prefab's layout, a demo catalogue and contact-sheet renders.
# Textures are the painted swatches in art/textures/galeborne.
# Usage: Blender --background --python scripts/kit/galeborne.py -- galeborne
import math, os, random, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, tube  # noqa: E402

# Material slots, in order; every object carries the full list so joined prefabs keep one material set
MATS = [("GB_Timber", "timber.png", 0), ("GB_Shingles", "shingles.png", 0), ("GB_Slate", "slate.png", 0),
        ("GB_Sailcloth", "sailcloth.png", 0), ("GB_Trim", "trim.png", 0), ("GB_Rope", "rope.png", 0),
        ("GB_Brass", "brass.png", 0), ("GB_Stone", "stone.png", 0), ("GB_Teal", "teal.png", 0),
        ("GB_Glow", (1.0, 0.7, 0.28), 3.5)]
TIMBER, SHINGLE, SLATE, SAIL, TRIM, ROPE, BRASS, STONE, TEAL, GLOW = range(len(MATS))
K.configure(MATS, os.path.join(B.ROOT, "art/textures/galeborne"), cap_mat=TIMBER, moss=None)

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
SKIN = 0.3            # real wall skin, from the grid line inward (-z)
EAVE, APEX = 0.3, 2.6  # roof slope: eave height and ridge height inside a 3 m roof module
PITCH_RUN = 1.0        # horizontal run from eave to ridge (2 m span)


# ---------- geometry helpers (all glTF coordinates) ----------

class G:
    """Three meshes per piece: hard timber (bevelled, flat shaded), flat detail (planks, shingles, plates) and soft
    (ropes, cloth, round posts; smooth shaded)."""

    def __init__(self, seed):
        self.h, self.f, self.s = Mesh(), Mesh(), Mesh()
        self.r = random.Random(seed)


def obox(m, c, axes, half, mat, tile=0.7, off=None, win=None, r=None):
    """Oriented box. UVs per face: grain (longest axis) runs along texture v; `win` maps each face onto a texture
    window (u0, v0, u1, v1) with the long axis along u (for trim bands)."""
    c = Vector(c)
    ax = [Vector(a).normalized() for a in axes]
    if off is None:
        rr = r or random
        off = (rr.random(), rr.random())
    g = max(range(3), key=lambda i: half[i])
    cs = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                cs[(sx, sy, sz)] = m.vert(c + ax[0] * half[0] * sx + ax[1] * half[1] * sy + ax[2] * half[2] * sz)
    for k in range(3):
        for s in (-1, 1):
            i, j = [q for q in range(3) if q != k]
            if g in (i, j):
                along, across = g, (j if g == i else i)
            else:
                along, across = j, i
            verts, uvs = [], []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]
                key[k], key[i], key[j] = s, a, b
                verts.append(cs[tuple(key)])
                ca = {i: a, j: b}
                pa, pc = ca[along] * half[along], ca[across] * half[across]
                if win:
                    u0, v0, u1, v1 = win
                    uvs.append((u0 + (pa + half[along]) / (2 * half[along]) * (u1 - u0),
                                v0 + (pc + half[across]) / (2 * half[across]) * (v1 - v0)))
                else:
                    uvs.append((off[0] + pc / tile, off[1] + pa / tile))
            m.face(verts, uvs, mat)


def abox(m, lo, hi, mat=TIMBER, **kw):
    lo, hi = Vector(lo), Vector(hi)
    obox(m, (lo + hi) / 2, (X, Y, Z), [abs(hi[i] - lo[i]) / 2 for i in range(3)], mat, **kw)


def beam(m, a, b, w, t, mat=TIMBER, nrm=(0, 0, 1), **kw):
    """Box beam from a to b: `w` across, `t` along the (orthogonalised) `nrm` direction."""
    a, b = Vector(a), Vector(b)
    L = b - a
    x = L.normalized()
    n = Vector(nrm)
    n = n - x * n.dot(x)
    if n.length < 1e-6:
        n = x.orthogonal()
    n.normalize()
    obox(m, (a + b) / 2, (x, n.cross(x), n), (L.length / 2, w / 2, t / 2), mat, **kw)


def sweep(m, pts, w, t, side, mat=TIMBER, tile=0.7, caps=True, off=0.0):
    """Rectangular section swept along a polyline; `side` fixes the width direction (e.g. the plane normal)."""
    pts = [Vector(p) for p in pts]
    side = Vector(side)
    n = len(pts)
    rings, s = [], 0.0
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        S = (side - T * side.dot(T)).normalized()
        N = T.cross(S)
        if i:
            s += (p - pts[i - 1]).length
        q = [p + S * w / 2 + N * t / 2, p - S * w / 2 + N * t / 2, p - S * w / 2 - N * t / 2, p + S * w / 2 - N * t / 2]
        rings.append(([m.vert(v) for v in q], s))
    acc = [0, w, w + t, 2 * w + t, 2 * w + 2 * t]
    for (r0, s0), (r1, s1) in zip(rings, rings[1:]):
        for k in range(4):
            k1 = (k + 1) % 4
            m.face((r0[k], r0[k1], r1[k1], r1[k]),
                   [(off + acc[k] / tile, s0 / tile), (off + acc[k + 1] / tile, s0 / tile),
                    (off + acc[k + 1] / tile, s1 / tile), (off + acc[k] / tile, s1 / tile)], mat)
    if caps:
        m.face(rings[0][0][::-1], None, mat, tile)
        m.face(rings[-1][0], None, mat, tile)


def rope(m, pts, r=0.035, sides=5, caps=True):
    tube(m, pts, [r] * len(pts), ROPE, sides, tile=0.3, caps=(caps, caps), cap_mat=ROPE)


def swag(a, b, sag, n=6):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / n) - Y * sag * math.sin(math.pi * i / n) for i in range(n + 1)]


def ring(m, c, R, nrm, r=0.03, mat=BRASS, seg=8, sides=4):
    c, nrm = Vector(c), Vector(nrm).normalized()
    u = nrm.orthogonal().normalized()
    v = nrm.cross(u)
    pts = [c + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * R for k in range(seg + 1)]
    tube(m, pts, [r] * len(pts), mat, sides, closed=True, caps=(False, False))


def spike(m, base, h, r, mat=BRASS, sides=6, ball=True):
    """Turned brass finial: collar, ball and point."""
    b = Vector(base)
    prof = [(0.0, r * 1.2), (0.12 * h, r * 1.2), (0.18 * h, r * 0.6)]
    if ball:
        prof += [(0.3 * h, r * 1.5), (0.42 * h, r * 0.5)]
    prof += [(h, 0.004)]
    tube(m, [b + Y * y for y, _ in prof], [rr for _, rr in prof], mat, sides, cap_mat=mat)


def sheet(m, P, nu, nv, mat, uv=lambda u, v: (u, v), matf=None):
    grid = [[m.vert(P(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            mm = matf((i + 0.5) / nu, (j + 0.5) / nv) if matf else mat
            m.face([grid[b][a] for a, b in q], [uv(a / nu, b / nv) for a, b in q], mm)


def poly(m, pts, mat, uvs=None):
    verts = [m.vert(p) for p in pts]
    m.face(verts, uvs, mat, 0.7)


def feather2d(L, W, curl=0.12, n=7):
    """Feather outline along +y (quill at the origin): two vanes with a couple of splits, slight curl."""
    right, left = [], []
    for i in range(1, n + 1):
        t = i / n
        y = L * (0.12 + 0.88 * t)
        half = W / 2 * math.sin(math.pi * min(1.0, 0.15 + t * 0.95)) ** 0.7
        cx = curl * L * t * t
        right.append((cx + half * (0.55 if i == 3 else 1.0), y - (0.05 * L if i == 3 else 0)))
        left.append((cx - half * (0.6 if i == 5 else 1.0), y - (0.05 * L if i == 5 else 0)))
    tip = (curl * L, L)
    out = Outline([(0, 0)] + right[:-1] + [tip] + left[:-1][::-1])
    out.strip = ((0, 0), list(zip(left[:-1], right[:-1])), tip)
    return out


class Outline(list):
    """A 2D outline that also knows how to triangulate itself as a strip (concave feathers)."""
    strip = None


def fmap(o, fn):
    out = Outline(fn(x, y) for x, y in o)
    if o.strip:
        b, pairs, t = o.strip
        out.strip = (fn(*b), [(fn(*a), fn(*c)) for a, c in pairs], fn(*t))
    return out


def flat(m, outline, o, ax, ay, mat, thick=0.0, surf=None):
    """Lay a 2D outline in 3D at origin o with axes ax, ay (optionally onto a surface function); `thick` extrudes."""
    o, ax, ay = Vector(o or (0, 0, 0)), Vector(ax), Vector(ay)
    nz = ax.cross(ay).normalized()
    xs = [x for x, _ in outline]
    ys = [y for _, y in outline]
    w, h = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    uvs = [((x - min(xs)) / w, (y - min(ys)) / h) for x, y in outline]
    pts = [surf(x, y) if surf else o + ax * x + ay * y for x, y in outline]
    if getattr(outline, "strip", None):
        P3 = (lambda q: surf(*q)) if surf else (lambda q: o + ax * q[0] + ay * q[1])
        UV = lambda q: ((q[0] - min(xs)) / w, (q[1] - min(ys)) / h)
        b, pairs, t = outline.strip
        rows = [[b]] + [[a, c] for a, c in pairs] + [[t]]
        for side in ((1, -1) if thick else (0,)):
            off = nz * thick / 2 * side
            V3 = lambda q: m.vert(P3(q) + off)
            for r0, r1 in zip(rows, rows[1:]):
                quad = [r0[0], r1[0]] + ([r1[1]] if len(r1) > 1 else []) + ([r0[1]] if len(r0) > 1 else [])
                vs = [V3(q) for q in quad]
                m.face(vs if side >= 0 else vs[::-1], [UV(q) for q in (quad if side >= 0 else quad[::-1])], mat)
        return
    if not thick:
        poly(m, pts, mat, uvs)
        return
    front = [m.vert(p + nz * thick / 2) for p in pts]
    back = [m.vert(p - nz * thick / 2) for p in pts]
    m.face(front, uvs, mat)
    m.face(back[::-1], uvs[::-1], mat)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        m.face((back[i], back[j], front[j], front[i]), [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)], mat)


def banner(m, top_c, w, h, nrm, mat=TRIM, sway=0.05, notch=0.18, seed=0.0):
    """Hanging swallow-tail banner from a top centre point, facing `nrm` (horizontal)."""
    top_c, nrm = Vector(top_c), Vector(nrm).normalized()
    side = Y.cross(nrm).normalized()

    def P(u, v):
        y = -h * (1 - v)
        if v == 0:
            y += notch * h * (1 - abs(2 * u - 1))
        bulge = sway * math.sin(math.pi * u) + 0.03 * math.sin(3 * (1 - v) + seed) * (1 - v)
        return top_c + side * (u - 0.5) * w + Y * y + nrm * bulge

    sheet(m, P, 3, 5, mat, uv=lambda u, v: (u, v))


def pennant(m, root, L, h, along, mat=TRIM, wave=0.12, seed=0.0):
    root, along = Vector(root), Vector(along).normalized()
    side = along.cross(Y).normalized()

    def P(u, v):
        hh = h * (1 - 0.75 * u)
        return root + along * u * L + Y * (v - 0.5) * hh - Y * 0.15 * L * u * u + side * wave * math.sin(u * 6 + seed) * u

    sheet(m, P, 6, 1, mat, uv=lambda u, v: (u * 2.0, 0.3 + v * 0.4))


def plate(m, c, nrm, s=0.26, t=0.015, up=(0, 1, 0)):
    """Square brass plate lying on a face with outward normal `nrm`."""
    nrm = Vector(nrm).normalized()
    u = Vector(up)
    u = (u - nrm * u.dot(nrm))
    if u.length < 1e-6:
        u = nrm.orthogonal()
    u.normalize()
    obox(m, Vector(c) + nrm * t / 2, (u, nrm.cross(u), nrm), (s / 2, s / 2, t / 2), BRASS, tile=0.9)


def outline_top(outline, x):
    best = 0.0
    for (x1, y1), (x2, y2) in zip(outline, outline[1:] + outline[:1]):
        if min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 and abs(x2 - x1) > 1e-9:
            best = max(best, y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    return best


def planks(m, x0, x1, y0, top, z0, z1, mat=TIMBER, width=0.26, r=None, gap=0.012, skip=None, tile=0.9):
    """Vertical planks between x0 and x1 from y0 to top(x) (a function or a number), each its own slab."""
    r = r or random
    n = max(1, round((x1 - x0) / width))
    wv = (x1 - x0) / n
    for i in range(n):
        a, b = x0 + i * wv + gap / 2, x0 + (i + 1) * wv - gap / 2
        ya = top(a) if callable(top) else top
        yb = top(b) if callable(top) else top
        dz = r.uniform(-0.012, 0.012)
        if skip and skip(a, b):
            continue
        if abs(ya - yb) < 1e-4:
            obox(m, ((a + b) / 2, (y0 + ya) / 2, (z0 + z1) / 2 + dz), (Y, X, Z), ((ya - y0) / 2, (b - a) / 2, (z1 - z0) / 2), mat, tile=tile, r=r)
        else:
            K.extrude(m, [(a, y0), (b, y0), (b, yb), (a, ya)], z0 + dz, z1 + dz, mat, tile)


def shingles(m, E, S, A, N, L, span, mat, r, row=0.3, tab=0.42, lift=0.065, tile=0.9):
    """Overlapping rows of individual tabs on a slope: E eave point, S up-slope, A along the eave, N outward.
    span(t) gives the (a0, a1) extent along A at slope distance t, so triangles and trapezoids work too."""
    E, S, A, N = Vector(E), Vector(S).normalized(), Vector(A).normalized(), Vector(N).normalized()

    def P(a, t, h):
        return E + A * a + S * t + N * h

    nrows = max(1, math.ceil(L / row))
    for k in range(nrows):
        t0 = k * row
        t1 = min(L, t0 + row * 1.75)
        b0, b1 = span(t0)
        c0, c1 = span(t1)
        if b1 - b0 < 0.03:
            continue
        x = b0 - (k % 2) * tab * 0.5
        edges = [b0]
        while True:
            x += tab * r.uniform(0.8, 1.2)
            if x >= b1 - 0.08:
                break
            if x > b0 + 0.08:
                edges.append(x)
        edges.append(b1)
        for x0, x1 in zip(edges, edges[1:]):
            j = r.uniform(0, 0.035) if k else r.uniform(0, 0.01)
            lf = lift * r.uniform(0.8, 1.25)
            tx0 = min(max(x0, c0), c1 - 0.02)
            tx1 = max(min(x1, c1), tx0 + 0.02)
            ta = t0 + j
            ou, ov = r.random(), r.random()
            b_0, b_1 = m.vert(P(x0, ta, 0.0)), m.vert(P(x1, ta, 0.0))
            u_0, u_1 = m.vert(P(x0, ta, lf)), m.vert(P(x1, ta, lf))
            w_0, w_1 = m.vert(P(tx0, t1, 0.012)), m.vert(P(tx1, t1, 0.012))
            m.face((u_0, u_1, w_1, w_0), [(ou + x0 / tile, ov + ta / tile), (ou + x1 / tile, ov + ta / tile),
                                         (ou + tx1 / tile, ov + t1 / tile), (ou + tx0 / tile, ov + t1 / tile)], mat)
            m.face((b_0, b_1, u_1, u_0), [(ou + x0 / tile, ov), (ou + x1 / tile, ov), (ou + x1 / tile, ov + lf / tile),
                                         (ou + x0 / tile, ov + lf / tile)], mat)


def fix_rope(m):
    """Rope tubes: run the texture's strands along the rope, one strand around the circumference."""
    for f in m.bm.faces:
        if f.material_index == ROPE:
            for lp in f.loops:
                u, v = lp[m.uv].uv
                lp[m.uv].uv = (v, 0.25 * u + 0.1)


def finish(g, pid, mats, seed, bevel=0.022, wob=0.012):
    objs = []
    for m, kind in ((g.h, "h"), (g.f, "f"), (g.s, "s")):
        if not len(m.bm.faces):
            m.bm.free()
            continue
        fix_rope(m)
        ob = m.object(f"{pid}.{kind}", mats, moss=None, seed=seed, smooth=(kind == "s"))
        if kind == "h" and bevel:
            K.bevel(ob, bevel, 1, 40)
        if kind != "s" and wob:
            K.wobble(ob, wob, 1.3, seed)
        objs.append(ob)
    return K.join(objs, pid)


# ---------- walls ----------

def wall_frame(g, w=2.0, h=3.0, sill=True, head=True):
    r = g.r
    abox(g.h, (0, 0, -SKIN), (0.22, h, 0), r=r)
    abox(g.h, (w - 0.22, 0, -SKIN), (w, h, 0), r=r)
    if sill:
        abox(g.h, (0.22, 0, -0.28), (w - 0.22, 0.22, -0.02), r=r)
    if head:
        abox(g.h, (0.22, h - 0.22, -0.28), (w - 0.22, h, -0.02), r=r)


def corner_plates(g, w, h, y0=0.0):
    for x in (0.0, w - 0.3):
        for y in (y0, h - 0.28):
            abox(g.f, (x, y, 0), (x + 0.3, y + 0.28, 0.015), BRASS, tile=0.9)


def build_wall(p, g):
    pid = p["id"]
    w, h, _ = p["size"]
    r = g.r
    if "half" in pid:
        for x in (0.0, w - 0.2):
            abox(g.h, (x, 0, -SKIN), (x + 0.2, h - 0.12, 0), r=r)
        abox(g.h, (-0.0, h - 0.18, -SKIN - 0.02), (w, h, 0.02), r=r)  # handrail cap
        abox(g.h, (0.2, 0, -0.27), (w - 0.2, 0.18, -0.03), r=r)
        beam(g.h, (0.25, 0.22, -0.08), (w - 0.25, h - 0.24, -0.08), 0.15, 0.09, r=r)
        beam(g.h, (0.25, h - 0.24, -0.2), (w - 0.25, 0.22, -0.2), 0.15, 0.09, r=r)
        plate(g.f, (w / 2, (h - 0.02) / 2, -0.035), Z, 0.2)
        for x in (0.0, w - 0.3):
            abox(g.f, (x, h - 0.46, 0), (x + 0.3, h - 0.2, 0.015), BRASS, tile=0.9)
            abox(g.f, (x, 0.0, 0), (x + 0.3, 0.24, 0.015), BRASS, tile=0.9)
        return
    if "endcap" in pid:
        y_l, y_r = 0.55, h
        slope = lambda x: y_l + (y_r - y_l) * x / w
        abox(g.h, (w - 0.22, 0, -SKIN), (w, h - 0.15, 0), r=r)
        abox(g.h, (0, 0, -SKIN), (0.22, y_l, 0), r=r)
        abox(g.h, (0.22, 0, -0.28), (w - 0.22, 0.22, -0.02), r=r)
        d = Vector((w, y_r - y_l, 0)).normalized()
        nn = Vector((-d.y, d.x, 0))
        beam(g.h, Vector((0.0, y_l, -0.15)) - nn * 0.12, Vector((w, y_r, -0.15)) - nn * 0.12, 0.3, 0.24, nrm=nn, r=r)
        planks(g.f, 0.22, w - 0.22, 0.22, lambda x: slope(x) - 0.2, -0.21, -0.09, r=r)
        beam(g.h, (0.3, 0.25, -0.04), (w - 0.3, slope(w - 0.3) - 0.35, -0.04), 0.16, 0.08, r=r)
        for x, y in ((0.0, 0.0), (w - 0.3, 0.0), (w - 0.3, h - 0.45)):
            abox(g.f, (x, y, 0), (x + 0.3, y + 0.28, 0.015), BRASS, tile=0.9)
        spike(g.s, (w - 0.11, h - 0.15, -0.15), 0.15, 0.06)
        return

    wall_frame(g, w, h)
    op = p.get("opening")
    if "sailcloth" in pid:
        x0, x1, y0, y1 = 0.36, w - 0.36, 0.36, h - 0.36

        def P(u, v):
            return Vector((x0 + u * (x1 - x0), y0 + v * (y1 - y0), -0.15 + 0.09 * math.sin(math.pi * u) * math.sin(math.pi * v)))

        sheet(g.s, P, 6, 8, SAIL)
        surf = lambda x, y: P((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)) + Z * 0.035
        fo = fmap(feather2d(1.8, 0.6, 0.1), lambda x, y: (1.32 + x * math.cos(0.38) - y * math.sin(0.38), 0.6 + x * math.sin(0.38) + y * math.cos(0.38)))
        flat(g.s, fo, None, X, Y, TEAL, surf=lambda x, y: surf(x, y))
        # lacing to the frame, zig-zag through brass rings on the posts
        for side in (0, 1):
            xp, xc = (0.22, x0 + 0.03) if side == 0 else (w - 0.22, x1 - 0.03)
            pts = []
            for k in range(11):
                y = y0 + 0.08 + k * (y1 - y0 - 0.16) / 10
                pts.append(Vector((xp if k % 2 == 0 else xc, y, -0.1)))
            rope(g.s, pts, 0.02, 4)
        for yy in (0.22, h - 0.22):
            yc = y0 + 0.03 if yy < 1 else y1 - 0.03
            pts = [Vector((x0 + 0.1 + k * (x1 - x0 - 0.2) / 8, yy if k % 2 == 0 else yc, -0.1)) for k in range(9)]
            rope(g.s, pts, 0.02, 4)
        for x in (0.0, w - 0.22):
            for y in (0.7, 1.5, 2.3):
                abox(g.f, (x - 0.015, y, -SKIN - 0.015), (x + 0.235, y + 0.07, 0.015), BRASS, tile=0.9)
        corner_plates(g, w, h)
        return

    if op:
        ox, oy = op["offset"]
        ow, oh = op["size"]
        skip = lambda a, b: b > ox + 0.01 and a < ox + ow - 0.01
        # planks beside the opening run full height; above and below it they stop at the opening
        planks(g.f, 0.22, ox, 0.22, h - 0.22, -0.21, -0.09, r=r, width=0.28)
        planks(g.f, ox + ow, w - 0.22, 0.22, h - 0.22, -0.21, -0.09, r=r, width=0.28)
        planks(g.f, ox, ox + ow, oy + oh + 0.12, h - 0.22, -0.21, -0.09, r=r, width=0.25)
        if oy > 0.3:
            planks(g.f, ox, ox + ow, 0.22, oy - 0.1, -0.21, -0.09, r=r, width=0.25)
            abox(g.h, (ox - 0.12, oy - 0.12, -0.29), (ox + ow + 0.12, oy, 0.03), r=r)  # sill ledge
            beam(g.h, (0.24, 0.24, -0.04), (ox - 0.04, oy - 0.14, -0.04), 0.12, 0.07, r=r)
            beam(g.h, (w - 0.24, 0.24, -0.04), (ox + ow + 0.04, oy - 0.14, -0.04), 0.12, 0.07, r=r)
        else:
            # door: split the sill, add a stone threshold
            abox(g.h, (ox - 0.02, -0.0, -0.3), (ox + ow + 0.02, 0.08, 0.05), STONE, tile=1.2)
        abox(g.h, (0.22, oy + oh, -0.29), (w - 0.22, oy + oh + 0.14, 0.0), r=r)  # lintel
        for x in (0.22, w - 0.22):
            dx = 1 if x < 1 else -1
            beam(g.h, (x, oy + oh - 0.45, -0.05), (x + dx * (ox - 0.22 + 0.02), oy + oh, -0.05), 0.12, 0.08, r=r)
        if oy < 0.3:
            # the sill rail stops at the door
            pass
        plate(g.f, (w / 2, oy + oh + 0.07, 0.0), Z, 0.18)
        corner_plates(g, w, h)
        return

    planks(g.f, 0.22, w - 0.22, 0.22, h - 0.22, -0.21, -0.09, r=r)
    beam(g.h, (0.3, 0.3, -0.04), (w - 0.3, h - 0.3, -0.04), 0.18, 0.08, r=r)
    abox(g.h, (0.22, 1.42, -0.27), (w - 0.22, 1.56, -0.08), r=r)  # mid rail behind the brace
    corner_plates(g, w, h)
    plate(g.f, (w / 2, h / 2, 0.0), Z, 0.16)


# ---------- the door wall sill is split by build_wall's planks; doors and windows ----------

def arch_outline(w, h, x0=0.5, n=8):
    return [(x + x0, y) for x, y in K.pointed_arch(w, h, n)]


def arch_frame(g, w_in, h_in, depth=(-0.28, 0.03), fw=0.15, x0=0.5, top=None):
    """Pointed arch moulding inside a rectangle, with timber spandrels and a head beam."""
    r = g.r
    o = arch_outline(w_in + fw, h_in + fw / 2, x0)
    zc, t = (depth[0] + depth[1]) / 2, depth[1] - depth[0]
    sweep(g.f, [(x, y, zc) for x, y in o], fw, t, Z, TIMBER, off=r.random())
    top = top or (h_in + fw)
    apex = max(y for _, y in o)
    left = [(x, y) for x, y in o[1:] if x <= x0 + 1e-6]
    right = [(x, y) for x, y in o[:-1] if x >= x0 - 1e-6]
    xl = min(x for x, _ in o) - fw / 2
    xr = max(x for x, _ in o) + fw / 2
    K.extrude(g.f, [(xl, left[0][1])] + left + [(x0, top), (xl, top)], -0.24, -0.05, TIMBER, 0.9)
    K.extrude(g.f, right + [(xr, right[-1][1]), (xr, top), (x0, top)], -0.24, -0.05, TIMBER, 0.9)
    abox(g.h, (xl, top - 0.1, -0.3), (xr, top, 0.02), r=r)
    plate(g.f, (x0, apex + 0.02, depth[1]), Z, 0.14)
    return o


def build_insert(p, g):
    pid = p["id"]
    w, h, _ = p["size"]
    r = g.r
    if pid.endswith("door-arched") or pid.endswith("door-louvered"):
        o = arch_outline(0.78, 2.36)
        arch_frame(g, 0.78, 2.36, top=h)
        inner = arch_outline(0.8, 2.38)
        topf = lambda x: outline_top(inner, x)
        if pid.endswith("arched"):
            planks(g.f, 0.1, 0.9, 0.0, topf, -0.19, -0.07, TEAL, width=0.2, r=r, tile=1.2)
            for y in (0.45, 1.75):
                abox(g.f, (0.12, y, -0.07), (0.88, y + 0.07, -0.05), BRASS, tile=0.9)
                abox(g.f, (0.1, y - 0.03, -0.07), (0.22, y + 0.1, -0.045), BRASS, tile=0.9)
            ring(g.s, (0.72, 1.12, -0.03), 0.08, Z, 0.016, seg=8, sides=4)
            abox(g.f, (0.68, 1.17, -0.07), (0.76, 1.25, -0.05), BRASS, tile=0.9)
        else:
            planks(g.f, 0.1, 0.9, 0.0, 1.2, -0.17, -0.09, TEAL, width=0.2, r=r, tile=1.2)
            beam(g.h, (0.14, 0.12, -0.06), (0.86, 1.1, -0.06), 0.1, 0.05, r=r)
            beam(g.h, (0.14, 1.1, -0.06), (0.86, 0.12, -0.06), 0.1, 0.05, r=r)
            abox(g.h, (0.1, 1.15, -0.2), (0.9, 1.27, -0.04), r=r)
            for k in range(8):
                y = 1.38 + k * 0.11
                half = 0.4 if y < 1.76 else max(0.06, (topf(0.5) - y) * 0.42)
                if y + 0.05 > topf(0.5 + half) and half <= 0.06:
                    break
                xs = [x for x in [0.1 + 0.01 * i for i in range(81)] if topf(x) > y + 0.07]
                if not xs:
                    break
                obox(g.f, (0.5, y, -0.12), (X, Vector((0, math.cos(0.6), math.sin(0.6))), Vector((0, -math.sin(0.6), math.cos(0.6)))),
                     ((xs[-1] - xs[0]) / 2, 0.06, 0.012), TEAL, r=r)
            fill_back = [(x, y) for x, y in inner]
            K.fill(g.f, fill_back, -0.2, TIMBER)
            ring(g.s, (0.75, 1.05, -0.03), 0.06, Z, 0.014, seg=8, sides=4)
        return
    if pid.endswith("door-plank"):
        abox(g.h, (0, 0, -SKIN), (0.12, h, 0.02), r=r)
        abox(g.h, (w - 0.12, 0, -SKIN), (w, h, 0.02), r=r)
        abox(g.h, (0.12, h - 0.14, -SKIN), (w - 0.12, h, 0.02), r=r)
        n = 4
        for i in range(n):
            a = 0.12 + i * (w - 0.24) / n
            b = a + (w - 0.24) / n - 0.01
            obox(g.f, ((a + b) / 2, (h - 0.14) / 2, -0.12 + r.uniform(-0.01, 0.01)), (Y, X, Z), ((h - 0.14) / 2, (b - a) / 2, 0.05), TRIM,
                 win=(0.02, i / n, 0.98, (i + 1) / n))
        for y in (0.35, 1.95):
            abox(g.f, (0.12, y, -0.07), (0.88, y + 0.07, -0.05), BRASS, tile=0.9)
        ring(g.s, (0.72, 1.1, -0.03), 0.08, Z, 0.016)
        for x, y in ((0, 0), (w - 0.18, 0), (0, h - 0.18), (w - 0.18, h - 0.18)):
            abox(g.f, (x, y, 0.02), (x + 0.18, y + 0.18, 0.035), BRASS, tile=0.9)
        return
    if pid.endswith("window-pointed"):
        o = arch_frame(g, 0.74, 1.88, top=h)
        inner = arch_outline(0.76, 1.9)
        K.fill(g.s, inner, -0.16, GLOW)
        # brass diamond lattice clipped to the arch
        for sgn in (1, -1):
            for c in [k * 0.29 for k in range(-5, 9)]:
                pts = []
                for i in range(61):
                    x = 0.1 + 0.8 * i / 60
                    y = c + sgn * (x - 0.5) * 1.7
                    if 0.02 < y < outline_top(inner, x) - 0.02 and 0.12 < x < 0.88:
                        pts.append(Vector((x, y, -0.13)))
                if len(pts) > 3:
                    beam(g.f, pts[0], pts[-1], 0.03, 0.03, BRASS, tile=0.9)
        abox(g.h, (0.04, -0.02, -0.3), (0.96, 0.08, 0.06), r=r)
        return
    if pid.endswith("window-shuttered"):
        abox(g.h, (0, 0, -SKIN), (0.12, h, 0.02), r=r)
        abox(g.h, (w - 0.12, 0, -SKIN), (w, h, 0.02), r=r)
        abox(g.h, (0.12, h - 0.14, -SKIN), (w - 0.12, h, 0.02), r=r)
        abox(g.h, (-0.04, 0, -SKIN), (w + 0.04, 0.12, 0.07), r=r)
        K.fill(g.s, [(0.12, 0.12), (0.88, 0.12), (0.88, 1.36), (0.12, 1.36)], -0.16, GLOW)
        abox(g.h, (0.46, 0.12, -0.17), (0.54, h - 0.14, -0.09), r=r)
        abox(g.h, (0.12, 0.76, -0.17), (0.88, 0.84, -0.09), r=r)
        for sx, hx in ((-1, 0.0), (1, w)):
            ang = math.radians(115)
            d = Vector((sx * math.cos(math.pi - ang), 0, math.sin(math.pi - ang)))
            c = Vector((hx, h / 2, 0.03)) + d * 0.24
            obox(g.f, c, (d, Y, d.cross(Y)), (0.23, h / 2 - 0.08, 0.025), TEAL, r=r)
            for y in (0.3, h - 0.3):
                obox(g.f, Vector((hx, y, 0.03)) + d * 0.22 + d.cross(Y) * 0.03 * -sx, (d, Y, d.cross(Y)), (0.22, 0.03, 0.01), BRASS)
            fo = feather2d(0.75, 0.26, 0.1)
            nz = d.cross(Y).normalized() * -sx
            o3 = Vector((hx, 0.35, 0.03)) + d * 0.24 + nz * 0.03
            flat(g.s, fo, o3, d, Y, SAIL)
        return
    if pid.endswith("window-round"):
        c = Vector((0.5, 0.5, -0.12))
        pts = [c + Vector((math.cos(a), math.sin(a), 0)) * 0.39 for a in (2 * math.pi * k / 14 for k in range(15))]
        tube(g.s, pts, [0.09] * 15, TIMBER, 7, closed=True, caps=(False, False))
        ring(g.s, c + Z * 0.08, 0.4, Z, 0.035, BRASS, seg=14, sides=5)
        K.fill(g.s, K.circle(0.5, 0.5, 0.34, 14), -0.16, GLOW)
        abox(g.h, (0.46, 0.14, -0.15), (0.54, 0.86, -0.09), r=r)
        abox(g.h, (0.14, 0.46, -0.15), (0.86, 0.54, -0.09), r=r)
        for a in (0.25, 0.75, 1.25, 1.75):
            q = c + Vector((math.cos(a * math.pi), math.sin(a * math.pi), 0)) * 0.4
            abox(g.f, (q.x - 0.05, q.y - 0.05, 0.0), (q.x + 0.05, q.y + 0.05, 0.03), BRASS, tile=0.9)
        # backing panel so it sits in the opening
        K.extrude(g.f, [(0.02, 0.0), (0.98, 0.0), (0.98, 0.12), (0.02, 0.12)], -0.28, -0.05, TIMBER, 0.9)
        return


# ---------- corners, floors, foundations, access ----------

def build_corner(p, g):
    pid = p["id"]
    r = g.r
    if "mast" in pid:
        c = Vector((0.25, 0, -0.25))
        tube(g.s, [c + Y * y for y in (0, 1, 2, 3)], [0.21, 0.205, 0.2, 0.195], TIMBER, 10, rough=0.03, seed=r.random(), tile=0.8)
        for y in (0.12, 1.5, 2.85):
            tube(g.s, [c + Y * (y - 0.06), c + Y * (y + 0.06)], [0.225, 0.225], BRASS, 10, cap_mat=BRASS)
        beam(g.h, c + Y * 2.45 - X * 0.24, c + Y * 2.45 + X * 0.24, 0.09, 0.09, nrm=Y, r=r)
        for sx in (-1, 1):
            ring(g.s, c + Y * 2.33 + X * 0.21 * sx, 0.055, Z, 0.014, seg=6, sides=4)
            rope(g.s, [c + Y * 2.33 + X * 0.21 * sx, c + Y * 1.95 + X * 0.22 * sx + Z * 0.04, c + Y * 1.7 + X * 0.21 * sx], 0.018, 4)
        pts = [c + Vector((math.cos(a) * 0.22, 1.85 + 0.25 * a / (6 * math.pi), math.sin(a) * 0.22)) for a in (6 * math.pi * k / 30 for k in range(31))]
        rope(g.s, pts, 0.03, 4)
        return
    if "inner" in pid:
        abox(g.h, (0.14, 0, -0.5), (0.5, 3, -0.14), r=r)
        abox(g.h, (0.0, 0, -0.14), (0.5, 3, 0.0), r=r)
        abox(g.h, (0.0, 0, -0.5), (0.14, 3, -0.14), r=r)
        for y in (0.15, 1.5, 2.85):
            abox(g.f, (0.05, y - 0.12, 0.0), (0.45, y + 0.12, 0.015), BRASS, tile=0.9)
            abox(g.f, (-0.015, y - 0.12, -0.45), (0.0, y + 0.12, -0.05), BRASS, tile=0.9)
        rope(g.s, [Vector((-0.02, 1.0 + 0.04 * k, -0.25 + (0.27 if k % 2 else -0.27))) for k in range(7)], 0.025, 4)
        return
    # outer corner post: a heavy squared post wrapping the corner where two walls meet
    abox(g.h, (-0.06, 0, -0.36), (0.3, 3, 0.06), r=r)
    abox(g.h, (0.3, 0.0, -0.32), (0.44, 3, -0.04), r=r)
    abox(g.h, (-0.02, 0.0, -0.48), (0.26, 3, -0.36), r=r)
    for y in (0.15, 1.5, 2.85):
        abox(g.f, (-0.075, y - 0.13, 0.06), (0.44, y + 0.13, 0.075), BRASS, tile=0.9)
        abox(g.f, (-0.075, y - 0.13, -0.48), (-0.06, y + 0.13, 0.06), BRASS, tile=0.9)
    pts = [Vector((-0.07 if k % 2 == 0 else 0.3, 0.6 + 0.07 * k, 0.07 if k % 2 == 0 else 0.07)) for k in range(6)]
    rope(g.s, [Vector((0.12 + 0.19 * math.cos(a), 0.62 + 0.03 * a, -0.15 + 0.22 * math.sin(a))) for a in (k * 0.6 for k in range(22))], 0.028, 4)


def build_floor(p, g):
    r = g.r
    w, h, d = p["size"]
    n = 7
    for i in range(n):
        z1 = -i * d / n - 0.006
        z0 = z1 - d / n + 0.012
        obox(g.f, (w / 2 + r.uniform(-0.02, 0.02), h - 0.065 + r.uniform(-0.008, 0.008), (z0 + z1) / 2), (X, Y, Z), (w / 2 - 0.01, 0.06, (z1 - z0) / 2), TIMBER, tile=0.9, r=r)
    for z in (0.0, -d + 0.2):
        abox(g.h, (0, 0.15, z - 0.2), (w, h - 0.12, z), r=r)
    for x in (0.0, w / 2 - 0.09, w - 0.18):
        abox(g.h, (x, 0.15, -d + 0.2), (x + 0.18, h - 0.12, -0.2), r=r)
    for x, z in ((0, 0), (w - 0.3, 0), (0, -d + 0.3), (w - 0.3, -d + 0.3)):
        abox(g.f, (x, h, z - 0.3), (x + 0.3, h + 0.012, z), BRASS, tile=0.9)
        abox(g.f, (x if x == 0 else w - 0.012, 0.15, z - 0.3), ((x if x == 0 else w - 0.012) + 0.012, h, z), BRASS, tile=0.9)


def build_foundation(p, g):
    r = g.r
    w, h, d = p["size"]
    if "collar" in p["id"]:
        c = Vector((w / 2, 0, -d / 2))
        tube(g.s, [c + Y * y for y in (0.0, 0.5, 1.0, 1.28)], [1.72, 1.6, 1.52, 1.45], STONE, 12, rough=0.12, seed=r.random() * 9, tile=1.4, caps=(False, True), cap_mat=STONE)
        R = 1.72
        corners = [c + Vector((math.cos(a), 0, math.sin(a))) * R for a in (2 * math.pi * (k + 0.5) / 8 for k in range(8))]
        for k in range(8):
            a, b = corners[k], corners[(k + 1) % 8]
            rad = ((a + b) / 2 - c).normalized()
            beam(g.h, a + Y * 1.35 - (b - a).normalized() * 0.12, b + Y * 1.35 + (b - a).normalized() * 0.12, 0.3, 0.3, nrm=Y, r=r)
            # arched knee braces between posts, like an arcade
            arc = [a.lerp(b, t) + rad * 0.04 + Y * (1.22 - 0.95 * abs(2 * t - 1) ** 1.7) for t in [i / 6 for i in range(7)]]
            sweep(g.f, arc, 0.15, 0.18, rad, TIMBER, off=r.random())
        for k, q in enumerate(corners):
            rad = (q - c).normalized()
            beam(g.f, q, q + Y * h, 0.3, 0.32, nrm=rad, r=r)
            obox(g.f, q + Y * 1.35 + rad * 0.17, (Y, rad.cross(Y), rad), (0.18, 0.2, 0.012), BRASS, tile=0.9)
            obox(g.f, q + Y * 0.15 + rad * 0.17, (Y, rad.cross(Y), rad), (0.13, 0.2, 0.012), BRASS, tile=0.9)
        banner(g.s, c + Z * (R + 0.24) + Y * 1.18, 0.62, 1.05, Z, TRIM, seed=r.random())
        return
    # cliff-edge cantilever bracket: the post bears on the wall at z = -d, the arm reaches out to z = 0
    x0, x1 = 0.04, w - 0.04
    abox(g.h, (x0, 0, -d), (x1, h, -d + 0.32), r=r)
    abox(g.h, (x0 - 0.01, h - 0.3, -d), (x1 + 0.01, h, 0), r=r)
    arc = [Vector((w / 2, 0.5 + 2.2 * math.sin(t), -0.68 - 3.0 * math.cos(t))) for t in (math.pi / 2 * i / 9 for i in range(10))]
    sweep(g.h, arc, w - 0.14, 0.22, X, TIMBER, off=r.random())
    beam(g.h, (w / 2, 0.55, -d + 0.3), (w / 2, h - 0.32, -2.2), w - 0.22, 0.14, nrm=(0, 1, 1), r=r)
    abox(g.h, (x0 + 0.04, h - 0.3, -0.25), (x1 - 0.04, h - 0.1, 0.02), r=r)  # end block
    for sx in (x0 - 0.012, x1):
        abox(g.f, (sx, h - 0.45, -d + 0.02), (sx + 0.012, h - 0.02, -d + 0.6), BRASS, tile=0.9)
        abox(g.f, (sx, h - 0.32, -0.32), (sx + 0.012, h - 0.02, 0.0), BRASS, tile=0.9)
        abox(g.f, (sx, 0.02, -d + 0.02), (sx + 0.012, 0.32, -d + 0.32), BRASS, tile=0.9)
    # rope lashing where the brace meets the post
    q = arc[2]
    rope(g.s, [Vector((x0 - 0.02 if k % 2 == 0 else x1 + 0.02, q.y - 0.25 + 0.06 * k, -d + 0.36 + (0.05 if k % 2 else -0.04))) for k in range(8)], 0.025, 4)


def build_access(p, g):
    pid = p["id"]
    w, h, d = p["size"]
    r = g.r
    if "stair-straight" in pid:
        steps = 12
        rise, run = h / steps, d / steps
        dirv = Vector((0, h, -d)).normalized()
        nn = Vector((0, d, h)).normalized()
        for x in (0.04, w - 0.2):
            beam(g.h, Vector((x + 0.08, 0.0, -0.05)) + nn * 0.12, Vector((x + 0.08, h, -d + 0.05)) + nn * 0.12, 0.16, 0.34, nrm=nn, r=r)
        for i in range(steps):
            y = rise * (i + 1)
            z = -run * i
            obox(g.f, (w / 2, y - 0.04, z - run / 2 - 0.03), (X, Y, Z), (w / 2 - 0.2, 0.04, run / 2 + 0.04), TIMBER, r=r)
        for x in (0.04, w - 0.2):
            abox(g.h, (x, 0, -0.18), (x + 0.16, 1.05, -0.02), r=r)
            abox(g.h, (x, h - 0.4, -d + 0.02), (x + 0.16, h + 0.0 - 0.0, -d + 0.18), r=r)
            spike(g.s, (x + 0.08, 1.05, -0.1), 0.22, 0.07)
            rope(g.s, swag((x + 0.08, 1.0, -0.1), (x + 0.08, h - 0.05, -d + 0.1), 0.12, 8), 0.035, 5)
            abox(g.f, (x - 0.012, 0.05, -0.2), (x, 0.4, 0.0), BRASS, tile=0.9)
        return
    if "stair-spiral" in pid:
        c = Vector((w / 2, 0, -d / 2))
        tube(g.s, [c + Y * y for y in (0, 1.5, h)], [0.16, 0.15, 0.14], TIMBER, 10, tile=0.8)
        n = 12
        rail = []
        for i in range(n):
            a = -math.radians(30 * i) + math.pi / 2
            dv = Vector((math.cos(a), 0, -math.sin(a)))
            tv = Y.cross(dv)
            y = h * (i + 1) / n
            obox(g.f, c + dv * 0.55 + Y * (y - 0.04), (dv, Y, tv), (0.42, 0.04, 0.17 + 0.0), TIMBER, r=r)
            if i % 2 == 0:
                tube(g.s, [c + dv * 0.9 + Y * (y - 0.05), c + dv * 0.9 + Y * (y + 0.85)], [0.035, 0.03], TIMBER, 5)
            for k in range(3):
                aa = a - math.radians(10 * k)
                rail.append(c + Vector((math.cos(aa), 0, -math.sin(aa))) * 0.9 + Y * (y + 0.85 + h / n * k / 3))
        rope(g.s, rail, 0.03, 5)
        for y in (0.05, 1.5, h - 0.1):
            tube(g.s, [c + Y * (y - 0.05), c + Y * (y + 0.05)], [0.17, 0.17], BRASS, 10, cap_mat=BRASS)
        return
    if "balcony" in pid:
        # a 4 m jetty: open end at x = 0 against the wall, rope-railed on both long sides and the far end
        for i in range(7):
            z1 = -i * d / 7 - 0.006
            z0 = z1 - d / 7 + 0.012
            obox(g.f, (w / 2 + r.uniform(-0.03, 0.03), -0.06, (z0 + z1) / 2), (X, Y, Z), (w / 2 - 0.01, 0.06, (z1 - z0) / 2), TIMBER, tile=0.9, r=r)
        for z in (0.0, -d + 0.22):
            abox(g.h, (0, -0.5, z - 0.22), (w, -0.12, z), r=r)
        for x in (w / 3, 2 * w / 3, w - 0.2):
            abox(g.h, (x - 0.1, -0.38, -d + 0.22), (x + 0.1, -0.12, -0.22), r=r)
        posts = [(0.12, -0.11), (w / 2, -0.11), (w - 0.11, -0.11), (0.12, -d + 0.11), (w / 2, -d + 0.11), (w - 0.11, -d + 0.11), (w - 0.11, -d / 2)]
        for x, z in posts:
            abox(g.h, (x - 0.08, -0.5, z - 0.08), (x + 0.08, 0.86, z + 0.08), r=r)
            abox(g.f, (x - 0.1, 0.86, z - 0.1), (x + 0.1, 0.95, z + 0.1), BRASS, tile=0.9)
            abox(g.f, (x - 0.05, 0.95, z - 0.05), (x + 0.05, 1.0, z + 0.05), BRASS, tile=0.9)
        top = lambda i: Vector((posts[i][0], 0.82, posts[i][1]))
        for a, b in ((0, 1), (1, 2), (3, 4), (4, 5), (2, 6), (6, 5)):
            rope(g.s, swag(top(a), top(b), 0.22 if b - a == 1 and a not in (2, 6) else 0.1, 6), 0.035, 4)
        banner(g.s, (w - 0.02, -0.25, -d / 2), 0.55, 1.1, X, TRIM, seed=r.random())
        abox(g.f, (w - 0.02, -0.42, -d / 2 - 0.35), (w + 0.0, -0.12, -d / 2 + 0.35), BRASS, tile=0.9)
        return
    if "ladder-straight" in pid:
        for x in (0.2, 0.72):
            abox(g.h, (x, 0, -0.33), (x + 0.08, h, -0.2), r=r)
            abox(g.f, (x - 0.01, h - 0.2, -0.34), (x + 0.09, h - 0.12, -0.19), BRASS, tile=0.9)
        for i in range(10):
            y = 0.25 + i * 0.29
            obox(g.f, (0.5, y, -0.265), (X, Y, Z), (0.3, 0.025, 0.035), TIMBER, r=r)
        return
    if "ladder-rope" in pid:
        for x in (0.22, 0.78):
            pts = [Vector((x + 0.03 * math.sin(i * 0.9), h - h * i / 10, -0.25 + 0.03 * math.sin(i * 0.5))) for i in range(11)]
            rope(g.s, pts, 0.03, 5)
            abox(g.f, (x - 0.05, h - 0.12, -0.3), (x + 0.05, h, -0.2), BRASS, tile=0.9)
        for i in range(9):
            y = 0.25 + i * 0.3
            dx = 0.03 * math.sin((10 - (h - y) / h * 10) * 0.9)
            obox(g.f, (0.5 + dx, y, -0.25), (X, Y, Z), (0.32, 0.03, 0.045), TIMBER, r=r)
        return


# ---------- roofs ----------

def slope_frame(side, z0=0.0):
    """Eave point, up-slope, outward normal for the left (0) or right (1) slope of a 2 m run."""
    dx = 1.0 if side == 0 else -1.0
    S = Vector((dx * PITCH_RUN, APEX - EAVE, 0)).normalized()
    N = Vector((-dx * (APEX - EAVE), PITCH_RUN, 0)).normalized()
    E = Vector((0.05 if side == 0 else 1.95, EAVE, z0))
    L = (Vector((1.0, APEX, 0)) - Vector((E.x, EAVE, 0))).length
    return E, S, N, L


def rafter(g, side, z, r, proud=0.0, w=0.12, t=0.16):
    E, S, N, L = slope_frame(side)
    a = Vector((E.x, EAVE, z)) - N * (t / 2 + 0.01 - proud)
    b = Vector((1.0, APEX, z)) - N * (t / 2 + 0.01 - proud)
    beam(g.h, a - S * 0.25, b + S * 0.05, w, t, nrm=N, r=r)


def build_roof(p, g):
    pid = p["id"]
    w, h, d = p["size"]
    r = g.r
    if pid.endswith("ridge"):
        abox(g.h, (0.28, 0.16, -0.42), (w - 0.28, 0.44, -0.08), TRIM, win=(0, 0.04, 2.0, 0.96))
        for x in (0.0, w - 0.3):
            abox(g.h, (x, 0.06, -0.47), (x + 0.3, 0.5, -0.03), r=r)
            abox(g.f, (x - 0.01, 0.12, -0.035), (x + 0.31, 0.44, -0.02), BRASS, tile=0.9)
        apex = Vector((0, 0.1, -0.25))
        for sz in (1, -1):
            dv = Vector((0, -(APEX - EAVE), sz * PITCH_RUN)).normalized()
            nv = Vector((0, PITCH_RUN, sz * (APEX - EAVE))).normalized()
            obox(g.f, apex + X * w / 2 + dv * 0.16 + nv * 0.03, (X, dv, nv), (w / 2 - 0.05, 0.17, 0.025), TIMBER, r=r)
        return
    if pid.endswith("gable"):
        E0, S0, N0, L = slope_frame(0)
        abox(g.h, (0, 0, -SKIN), (w, EAVE + 0.02, 0), r=r)
        for side in (0, 1):
            E, S, N, L = slope_frame(side)
            a = Vector((E.x - S.x * 0.15, EAVE - S.y * 0.15, -0.11)) + N * 0.05
            b = Vector((1.0, APEX, -0.11)) + N * 0.05 + S * 0.12
            beam(g.h, a, b, 0.22, 0.2, nrm=N, r=r)
        abox(g.h, (0.9, EAVE, -0.28), (1.1, APEX - 0.1, -0.04), r=r)
        o = [(x + 1.0, y + EAVE) for x, y in K.pointed_arch(1.3, 1.75, 7)]
        sweep(g.h, [(x, y, -0.12) for x, y in o], 0.11, 0.14, Z, TIMBER, off=r.random())
        top = lambda x: EAVE + (APEX - EAVE) * (1 - abs(x - 1.0) / 1.0) - 0.12
        planks(g.f, 0.08, 1.92, EAVE, top, -0.26, -0.16, r=r, width=0.27)
        banner(g.s, (1.0, 1.8, 0.0), 0.42, 1.0, Z, TRIM, seed=r.random())
        spike(g.s, (1.0, APEX + 0.08, -0.11), 0.32, 0.06)
        for x in (0.0, w - 0.3):
            abox(g.f, (x, 0.0, 0), (x + 0.3, 0.3, 0.015), BRASS, tile=0.9)
        plate(g.f, (1.0, APEX - 0.08, -0.0), Z, 0.2)
        return
    if pid.endswith("run"):
        for side in (0, 1):
            E, S, N, L = slope_frame(side)
            shingles(g.f, E, S, -Z, N, L, lambda t: (0.0, d), SHINGLE, r, tab=0.46)
            poly(g.f, [E - N * 0.01, E - N * 0.01 - Z * d, E + S * L - N * 0.01 - Z * d, E + S * L - N * 0.01], TIMBER)
            for z in (-0.15, -d + 0.15):
                rafter(g, side, z, r)
            abox(g.h, (0.02 if side == 0 else 1.78, 0.0, -d), (0.22 if side == 0 else 1.98, EAVE, 0), r=r)
        abox(g.h, (0.92, APEX - 0.28, -d), (1.08, APEX - 0.1, 0), r=r)
        for z in (-0.15, -d + 0.15):
            abox(g.h, (0.45, 1.3, z - 0.06), (1.55, 1.44, z + 0.06), r=r)
            for x in (0.0, 1.8):
                abox(g.f, (x - 0.01 if x == 0 else x + 0.2, 0.02, z - 0.13), (x if x == 0 else x + 0.21, EAVE - 0.02, z + 0.13), BRASS, tile=0.9)
        return
    if pid.endswith("hip"):
        # hipped end: open A-frame on the front (z = 0) continuing a run, hipped down to the back eave
        hz = -1.0  # hip apex sits over the cell centre
        for side in (0, 1):
            E, S, N, L = slope_frame(side)
            shingles(g.f, E, S, -Z, N, L, lambda t, L=L: (0.0, d - 1.0 * t / L - 0.05 * (1 - t / L)), SHINGLE, r, tab=0.56)
            poly(g.f, [E - N * 0.01, E - N * 0.01 - Z * (d - 0.05), Vector((1.0, APEX, hz)) - N * 0.01, Vector((1.0, APEX, 0)) - N * 0.01], TIMBER)
            rafter(g, side, -0.15, r)
            abox(g.h, (0.02 if side == 0 else 1.78, 0.0, -d), (0.22 if side == 0 else 1.98, EAVE, 0), r=r)
        Eb = Vector((0.05, EAVE, -d + 0.05))
        Sb = Vector((0, APEX - EAVE, 1.0 - 0.05)).normalized()
        Nb = Vector((0, 1.0, -(APEX - EAVE))).normalized()
        Lb = (Vector((0, APEX, hz)) - Vector((0, EAVE, -d + 0.05))).length
        shingles(g.f, Eb, Sb, X, Nb, Lb, lambda t: (0.95 * t / Lb, 1.9 - 0.95 * t / Lb), SHINGLE, r, tab=0.56)
        poly(g.f, [Eb - Nb * 0.01, Eb + X * 1.9 - Nb * 0.01, Vector((1.0, APEX, hz)) - Nb * 0.01], TIMBER)
        abox(g.h, (0.0, 0.0, -d), (w, EAVE, -d + 0.2), r=r)
        for cx in (0.0, 2.0):
            a = Vector((cx, EAVE, -d))
            b = Vector((1.0, APEX + 0.02, hz))
            beam(g.h, a + (a - b).normalized() * 0.1, b, 0.16, 0.16, nrm=Vector((cx - 1.0, 1.0, -1.0)), r=r)
        abox(g.h, (0.92, APEX - 0.28, hz), (1.08, APEX - 0.1, 0), r=r)
        abox(g.h, (0.88, APEX - 0.06, hz - 0.05), (1.12, APEX + 0.16, 0), TRIM, win=(0.0, 0.05, 1.0, 0.95))
        spike(g.s, (1.0, APEX + 0.12, hz), 0.28, 0.07)
        return


# ---------- crowns ----------

def pyramid_roof(g, c, R, y0, y1, n, mat, r, flare=0.0, rot=0.0, row=0.24, tab=0.32, hips=True):
    """n-sided shingled pyramid from radius R at y0 to an apex at y1, with timber hip rafters."""
    c = Vector(c)
    pts = [c + Vector((math.cos(rot + 2 * math.pi * k / n), 0, math.sin(rot + 2 * math.pi * k / n))) * R + Y * y0 for k in range(n)]
    apex = c + Y * y1
    for k in range(n):
        a, b = pts[k], pts[(k + 1) % n]
        mid = (a + b) / 2
        A = (b - a).normalized()
        S = (apex - mid).normalized()
        N = A.cross(S).normalized()
        if N.dot(mid - c) < 0:
            N = -N
        L = (apex - mid).length
        half = (b - a).length / 2
        E = mid - A * half
        shingles(g.f, E, S, A, N, L, lambda t, L=L, half=half: (half * t / L, 2 * half - half * t / L), mat, r, row=row, tab=tab, lift=0.05)
        poly(g.f, [a - N * 0.01, b - N * 0.01, apex - N * 0.01], TIMBER)
        if hips:
            beam(g.h, a + (a - apex).normalized() * 0.05, apex, 0.09, 0.09, nrm=(a - c).normalized() + Y, r=r)
    return pts


def build_crown(p, g):
    pid = p["id"]
    w, h, d = p["size"]
    r = g.r
    if pid.endswith("spire"):
        c = Vector((0, 0, 0))
        for sx in (-1, 1):
            for sz in (-1, 1):
                abox(g.h, (sx * 0.38 - 0.07, 0, sz * 0.38 - 0.07), (sx * 0.38 + 0.07, 1.25, sz * 0.38 + 0.07), r=r)
        for k in range(4):
            a = math.pi / 2 * k
            dv = Vector((math.cos(a), 0, math.sin(a)))
            sv = Y.cross(dv)
            obox(g.h, dv * 0.38 + Y * 1.15, (sv, Y, dv), (0.46, 0.1, 0.08), TIMBER, r=r)
            o = [(x, y + 0.15) for x, y in K.pointed_arch(0.62, 0.95, 5)]
            sweep(g.h, [dv * 0.38 + sv * x + Y * y for x, y in o[1:-1]], 0.06, 0.08, dv, TIMBER, off=r.random())
        # flared eave then a tall slender spire
        for k in range(4):
            a0 = math.pi / 4 + math.pi / 2 * k
            a1 = a0 + math.pi / 2
            pa = Vector((math.cos(a0), 0, math.sin(a0)))
            pb = Vector((math.cos(a1), 0, math.sin(a1)))
            lo = [pa * 0.68 + Y * 1.25, pb * 0.68 + Y * 1.25]
            hi = [pa * 0.42 + Y * 1.75, pb * 0.42 + Y * 1.75]
            A = (lo[1] - lo[0]).normalized()
            mid = (lo[0] + lo[1]) / 2
            midh = (hi[0] + hi[1]) / 2
            S = (midh - mid).normalized()
            N = A.cross(S).normalized()
            if N.dot(mid) < 0:
                N = -N
            L = (midh - mid).length
            hl0 = (lo[1] - lo[0]).length / 2
            hl1 = (hi[1] - hi[0]).length / 2
            shingles(g.f, mid - A * hl0, S, A, N, L, lambda t, L=L, a=hl0, b=hl1: ((a - b) * t / L, 2 * a - (a - b) * t / L), SLATE, r, row=0.2, tab=0.3, lift=0.05)
            poly(g.f, [lo[0] - N * 0.01, lo[1] - N * 0.01, hi[1] - N * 0.01, hi[0] - N * 0.01], TIMBER)
        pyramid_roof(g, c, 0.42, 1.75, 5.3, 4, SLATE, r, rot=math.pi / 4, row=0.38, tab=0.32)
        spike(g.s, (0, 5.25, 0), 0.75, 0.05)
        tube(g.s, [Vector((0, 5.5, 0)), Vector((0, 5.95, 0))], [0.012, 0.012], BRASS, 4)
        pennant(g.s, (0.0, 5.8, 0), 0.48, 0.16, X, TRIM, seed=r.random())
        return
    if pid.endswith("cupola"):
        c = Vector((w / 2, 0, -d / 2))
        K.disc(g.h, c, 0.98, 0.22, TIMBER, TIMBER, 8)
        n = 8
        R = 0.84
        posts = [c + Vector((math.cos(2 * math.pi * (k + 0.5) / n), 0, math.sin(2 * math.pi * (k + 0.5) / n))) * R for k in range(n)]
        for k, q in enumerate(posts):
            rad = (q - c).normalized()
            beam(g.h, q + Y * 0.22, q + Y * 2.45, 0.13, 0.13, nrm=rad, r=r)
            a, b = q, posts[(k + 1) % n]
            beam(g.f, a + Y * 0.95, b + Y * 0.95, 0.07, 0.08, TIMBER, nrm=Y, r=r)
            beam(g.h, a + Y * 2.38, b + Y * 2.38, 0.14, 0.16, nrm=Y, r=r)
            sv = (b - a)
            L = sv.length
            sv.normalize()
            o = K.pointed_arch(L - 0.12, 0.75, 4)
            mid = (a + b) / 2
            sweep(g.f, [mid + sv * x + Y * (1.55 + y) for x, y in o[1:-1]], 0.06, 0.07, (mid - c).normalized(), TIMBER, off=r.random())
            abox(g.f, (q.x - 0.08, 2.15, q.z - 0.08), (q.x + 0.08, 2.3, q.z + 0.08), BRASS, tile=0.9)
        pyramid_roof(g, c, 1.08, 2.46, 3.85, 8, SLATE, r, rot=0.0, row=0.26, tab=0.34)
        spike(g.s, c + Y * 3.8, 0.6, 0.06)
        tube(g.s, [c + Y * 4.2, c + Y * 4.5], [0.012, 0.012], BRASS, 4)
        pennant(g.s, c + Y * 4.4, 0.85, 0.24, X, TRIM, seed=r.random())
        tube(g.s, [c + Y * 2.38, c + Y * 2.0], [0.01, 0.01], BRASS, 4)
        tube(g.s, [c + Y * 2.0, c + Y * 1.95, c + Y * 1.75, c + Y * 1.65], [0.04, 0.11, 0.11, 0.03], GLOW, 6, cap_mat=GLOW)
        return
    if pid.endswith("sail-arc"):
        corners = [Vector((0.3, 0.0, -0.3)), Vector((w - 0.3, 0.0, -0.3)), Vector((w - 0.3, 0.0, -d + 0.3)), Vector((0.3, 0.0, -d + 0.3))]
        ctr = Vector((w / 2, h - 0.25, -d / 2))
        edge_h = 2.5

        def edge(k, u):
            a, b = corners[k], corners[(k + 1) % 4]
            q = a.lerp(b, u) + Y * (0.3 + (edge_h - 0.3) * math.sin(math.pi * u) ** 0.8)
            out = (a.lerp(b, 0.5) - Vector((w / 2, 0, -d / 2))).normalized()
            return q + out * 0.12 * math.sin(math.pi * u)

        def rib(k, v):
            return corners[k].lerp(ctr, v) + Y * (0.3 * (1 - v) + 0.54 * math.sin(math.pi * v))

        for k in range(4):
            sweep(g.h, [edge(k, i / 12) for i in range(13)], 0.16, 0.2, (corners[(k + 1) % 4] - corners[k]).cross(Y).normalized(), TIMBER, off=r.random())
            sweep(g.h, [rib(k, i / 8) for i in range(9)], 0.12, 0.14, (ctr - corners[k]).cross(Y).normalized(), TIMBER, off=r.random())

            def P(u, v, k=k):
                sag = 0.4 * math.sin(math.pi * u) * math.sin(math.pi * v) * (1 - v)
                return edge(k, u).lerp(ctr, v) + Y * (0.54 * math.sin(math.pi * v) - sag)

            sheet(g.s, P, 8, 5, SAIL, uv=lambda u, v: (u * 2, v * 1.5), matf=lambda u, v: TRIM if v < 0.3 and 0.2 < u < 0.8 else SAIL)
            q = corners[k] + Y * 0.3
            tube(g.h, [corners[k], q + Y * 0.1], [0.14, 0.13], TIMBER, 8)
            tube(g.s, [corners[k] + Y * 0.05, corners[k] + Y * 0.2], [0.16, 0.16], BRASS, 8, cap_mat=BRASS)
            out = (corners[k] - Vector((w / 2, 0, -d / 2))).normalized()
            hang = edge(k, 0.18) + out * 0.08
            rope(g.s, [hang, hang - Y * 0.5], 0.015, 4)
            tube(g.s, [hang - Y * 0.5, hang - Y * 0.58, hang - Y * 0.66], [0.02, 0.05, 0.02], BRASS, 6, cap_mat=BRASS)
            flat(g.s, feather2d(0.45, 0.14, 0.05), hang - Y * 0.66, out.cross(Y), -Y, TEAL)
        spike(g.s, ctr + Y * 0.0, 0.3, 0.06)
        return
    if pid.endswith("beacon"):
        c = Vector((w / 2, 0, -d / 2))
        tube(g.s, [c + Y * y for y in (0.0, 0.2, 0.36)], [0.8, 0.76, 0.66], STONE, 10, rough=0.1, seed=r.random(), tile=1.2, cap_mat=STONE)
        tube(g.s, [c + Y * y for y in (0.36, 1.0, 1.7, 2.25)], [0.52, 0.44, 0.38, 0.34], TIMBER, 8, tile=0.8)
        for y in (0.45, 1.25, 2.1):
            tube(g.s, [c + Y * (y - 0.06), c + Y * (y + 0.06)], [0.46 - 0.05 * y, 0.46 - 0.05 * y], BRASS, 8, cap_mat=BRASS)
        beam(g.h, c + Y * 2.25 - X * 0.95, c + Y * 2.25 + X * 0.95, 0.12, 0.12, nrm=Y, r=r)
        for sx in (-1, 1):
            spike(g.s, c + Y * 2.31 + X * 0.93 * sx, 0.18, 0.05)
            a = c + Y * 2.19 + X * 0.15 * sx
            b = c + Y * 2.19 + X * 0.88 * sx

            def P(u, v, a=a, b=b, sx=sx):
                top = a.lerp(b, u)
                drop = 0.95 * (1 - u) ** 0.6 + 0.25
                return top - Y * drop * v + Z * 0.08 * math.sin(math.pi * v) * math.sin(math.pi * u) + X * sx * 0.05 * v

            sheet(g.s, P, 4, 3, SAIL)
            hang = c + Y * 2.2 + X * 0.93 * sx
            rope(g.s, [hang, hang - Y * 0.55], 0.015, 4)
            tube(g.s, [hang - Y * 0.55, hang - Y * 0.62, hang - Y * 0.7], [0.02, 0.05, 0.02], BRASS, 6, cap_mat=BRASS)
            flat(g.s, feather2d(0.55, 0.17, 0.05), hang - Y * 0.7, Z, -Y, TEAL if sx < 0 else BRASS)
        tube(g.s, [c + Y * y for y in (2.3, 2.45, 2.62, 2.7)], [0.2, 0.32, 0.46, 0.44], BRASS, 10, cap_mat=BRASS)
        tube(g.s, [c + Y * y for y in (2.55, 3.0, 3.65, 4.25)], [0.05, 0.3, 0.3, 0.02], GLOW, 6, cap_mat=GLOW)
        for k in range(6):
            a = 2 * math.pi * k / 6
            dv = Vector((math.cos(a), 0, math.sin(a)))
            pts = [c + dv * (0.45 + 0.2 * math.sin(math.pi * t)) * (1 - 0.7 * t ** 2) + Y * (2.7 + 1.65 * t) for t in (i / 9 for i in range(10))]
            tube(g.s, pts, [0.025] * 10, BRASS, 4, cap_mat=BRASS)
        ring(g.s, c + Y * 3.4, 0.64, Y, 0.03, BRASS, seg=16, sides=4)
        for sx in (-1, 1):
            pts = [c + X * sx * (0.45 + 0.5 * math.sin(math.pi / 2 * t)) + Y * (2.65 + 1.4 * t ** 1.5) for t in (i / 8 for i in range(9))]
            tube(g.s, pts, [0.05 * (1 - 0.7 * i / 8) for i in range(9)], BRASS, 5, cap_mat=BRASS)
        spike(g.s, c + Y * 4.32, 0.68, 0.06)
        banner(g.s, c + Y * 2.0 + Z * 0.42, 0.5, 1.4, Z, TRIM, seed=r.random())
        return


# ---------- attachments ----------

def build_attachment(p, g):
    pid = p["id"]
    w, h, d = p["size"]
    r = g.r
    if pid.endswith("sail-furled"):
        tube(g.s, [Vector((x, 0.46, 0)) for x in (-2, -1, 0, 1, 2)], [0.075] * 5, TIMBER, 8, tile=0.8)
        for sx in (-1, 1):
            tube(g.s, [Vector((sx * 1.9, 0.46, 0)), Vector((sx * 2.0, 0.46, 0))], [0.09, 0.09], BRASS, 8, cap_mat=BRASS)
        pts = [Vector((-1.75 + 3.5 * i / 12, 0.3 - 0.02 * math.sin(i * 1.7), 0.02 * math.sin(i))) for i in range(13)]
        radii = [0.06 + 0.17 * math.sin(math.pi * i / 12) ** 0.4 * (1 + 0.15 * math.sin(i * 2.3)) for i in range(13)]
        tube(g.s, pts, radii, SAIL, 10, rough=0.15, seed=r.random(), tile=1.5, cap_mat=SAIL)
        flat(g.s, feather2d(0.5, 0.16, 0.1), Vector((0.2, 0.26, 0.205)), Vector((0.2, -1, 0)).normalized(), X, TEAL)
        for x in (-1.2, -0.4, 0.4, 1.2):
            pts = [Vector((x, 0.46 + 0.1 * math.sin(a), 0.21 * math.cos(a))) if math.sin(a) > 0 else Vector((x, 0.3 + 0.22 * math.sin(a), 0.21 * math.cos(a))) for a in (2 * math.pi * k / 8 for k in range(9))]
            rope(g.s, pts, 0.022, 4, caps=False)
        rope(g.s, [Vector((-0.8, 0.5, 0)), Vector((0, 0.58, 0)), Vector((0.8, 0.5, 0))], 0.018, 4)
        ring(g.s, (0, 0.56, 0), 0.04, Z, 0.012)
        return
    if pid.endswith("sail-spread"):
        A0, A1, T = Vector((-1.85, 0.12, 0)), Vector((1.85, 0.12, 0)), Vector((0.35, 2.85, 0))
        ctr = (A0 + A1 + T) / 3

        def P(u, v):
            base = A0.lerp(A1, u)
            q = base.lerp(T, v)
            belly = 0.12 * math.sin(math.pi * u) * math.sin(math.pi * min(1, v * 1.2)) * (1 - v)
            inward = (ctr - q) * 0.06 * math.sin(math.pi * u) * (1 - v) if v < 0.05 else Vector()
            return q + Z * belly + inward

        sheet(g.s, P, 8, 6, SAIL, uv=lambda u, v: (u * (1 - v) + v * 0.6, v))
        for a, b in ((A0, A1), (A1, T), (T, A0)):
            pts = [a.lerp(b, i / 8) + (ctr - a.lerp(b, i / 8)) * 0.05 * math.sin(math.pi * i / 8) for i in range(9)]
            rope(g.s, pts, 0.025, 5)
        for q in (A0, A1, T):
            ring(g.s, q, 0.07, Z, 0.02, BRASS, seg=8, sides=4)
        fo = feather2d(1.15, 0.38, 0.12)
        dv = Vector((0.35, 1, 0)).normalized()
        ax = dv.cross(Z) * -1

        def belly(x, y):
            q = Vector((-0.35, 0.6, 0)) + ax * x + dv * y
            u, v = (q.x + 1.85) / 3.7, (q.y - 0.12) / 2.73
            return q + Z * (0.12 * math.sin(math.pi * u) * math.sin(math.pi * min(1, v * 1.2)) * (1 - v) + 0.035)

        flat(g.s, fo, None, ax, dv, TEAL, surf=belly)
        return
    if pid.endswith("sail-arc"):
        def rib(u):
            return Vector((-1.9 + 3.75 * u, 0.25 + 2.65 * math.sin(math.pi / 2 * u) ** 1.3, -0.55 + 0.9 * u * (1 - u) * 1.5 + 0.2 * u))

        def low(u):
            return Vector((-1.9 + 3.6 * u, 0.25 + 1.3 * u ** 1.6, -0.55 + 0.7 * u))

        def P(u, v):
            q = low(u).lerp(rib(u), v)
            return q + Z * 0.28 * math.sin(math.pi * v) * math.sin(math.pi * u)

        sheet(g.s, P, 9, 5, SAIL, uv=lambda u, v: (u * 2.5, v), matf=lambda u, v: TRIM if v < 0.35 else SAIL)
        sweep(g.h, [rib(i / 12) for i in range(13)], 0.12, 0.14, Z, TIMBER, off=r.random())
        rope(g.s, [low(i / 8) for i in range(9)], 0.025, 5)
        for q in (rib(0), rib(1)):
            spike(g.s, q - Y * 0.05, 0.2, 0.06)
        rope(g.s, [rib(1), Vector((rib(1).x, 0.05, rib(1).z))], 0.012, 4)
        return
    if pid.endswith("boom-straight"):
        tube(g.s, [Vector((x, 0.15, 0)) for x in (-1, 0, 1)], [0.12, 0.115, 0.1], TIMBER, 8, tile=0.8)
        for x in (-0.97, -0.55, 0.55, 0.97):
            tube(g.s, [Vector((x - 0.04, 0.15, 0)), Vector((x + 0.04, 0.15, 0))], [0.135, 0.13], BRASS, 8, cap_mat=BRASS)
        ring(g.s, (0.75, 0.27, 0), 0.04, Z, 0.012)
        return
    if pid.endswith("boom-angled"):
        abox(g.h, (-1.0, 0.0, -0.13), (-0.78, 1.5, 0.13), r=r)
        beam(g.h, (-0.78, 1.38, 0), (1.0, 1.38, 0), 0.22, 0.2, nrm=Y, r=r)
        beam(g.h, (-0.85, 0.2, 0), (0.25, 1.32, 0), 0.16, 0.16, nrm=Z, r=r)
        abox(g.f, (-1.01, 1.18, 0.13), (-0.6, 1.5, 0.145), BRASS, tile=0.9)
        abox(g.f, (0.86, 1.26, -0.11), (1.0, 1.5, 0.11), BRASS, tile=0.9)
        rope(g.s, [Vector((0.15 + 0.06 * (k % 2), 1.18 + 0.03 * k, 0.12 * (1 if k % 2 else -1))) for k in range(7)], 0.022, 4)
        ring(g.s, (0.85, 1.22, 0), 0.05, Z, 0.014)
        return
    if "pulley" in pid:
        double = pid.endswith("double")
        bw = 0.26 if not double else 0.44
        tube(g.s, [Vector((0, h - 0.02, 0)), Vector((0, h - 0.15, 0))], [0.02, 0.025], BRASS, 5, cap_mat=BRASS)
        ring(g.s, (0, h - 0.24, 0), 0.08, Z, 0.022, seg=8)
        for sx in ((0,) if not double else (-0.11, 0.11)):
            ring(g.s, (sx, 0.62, 0), 0.12, X, 0.03, BRASS, seg=10, sides=4)
            tube(g.s, [Vector((sx - 0.035, 0.62, 0)), Vector((sx + 0.035, 0.62, 0))], [0.1, 0.1], TIMBER, 8)
        obox(g.h, (0, 0.62, 0), (X, Y, Z), (bw / 2, 0.24, 0.09), TIMBER, r=r)
        for sz in (-1, 1):
            obox(g.f, (0, 0.66, sz * 0.1), (X, Y, Z), (bw / 2 - 0.02, 0.27, 0.01), BRASS)
        tube(g.s, [Vector((0, 0.95, 0)), Vector((0, 0.86, 0))], [0.04, 0.04], BRASS, 6, cap_mat=BRASS)
        hook = [Vector((0.07 * math.sin(a), 0.22 - 0.1 * math.cos(a) + 0.02, 0)) for a in (math.pi * 1.4 * k / 8 for k in range(9))]
        tube(g.s, [Vector((0, 0.38, 0)), Vector((0, 0.3, 0))] + hook[::-1][:1], [0.03, 0.03, 0.025], BRASS, 5, cap_mat=BRASS)
        tube(g.s, hook, [0.025] * len(hook), BRASS, 5, cap_mat=BRASS)
        rope(g.s, [Vector((-0.12, 0.45, 0.0)), Vector((-0.13, 0.0, 0.0))], 0.02, 4)
        return
    if pid.endswith("chime"):
        ring(g.s, (0, h - 0.06, 0), 0.06, Z, 0.015)
        beam(g.h, (-0.68, 1.42, 0), (0.68, 1.42, 0), 0.06, 0.06, nrm=Y, r=r)
        for sx in (-1, 1):
            spike(g.s, (sx * 0.7, 1.39, 0), 0.12, 0.04, ball=False)
            rope(g.s, [Vector((0, h - 0.12, 0)), Vector((sx * 0.62, 1.45, 0))], 0.012, 4)
        items = [(-0.55, 0.85, "teal"), (-0.27, 0.6, "tube"), (0.0, 0.5, "gold"), (0.27, 0.75, "bell"), (0.55, 0.95, "teal")]
        for x, ln, kind in items:
            top = Vector((x, 1.39, 0))
            bot = top - Y * ln
            rope(g.s, [top, bot], 0.008, 4)
            if kind == "bell":
                tube(g.s, [bot, bot - Y * 0.06, bot - Y * 0.2], [0.02, 0.06, 0.1], BRASS, 8, cap_mat=BRASS)
            elif kind == "tube":
                tube(g.s, [bot, bot - Y * 0.45], [0.03, 0.03], BRASS, 6, cap_mat=BRASS)
            else:
                tube(g.s, [bot, bot - Y * 0.05, bot - Y * 0.1], [0.015, 0.035, 0.015], BRASS, 6, cap_mat=BRASS)
                flat(g.s, feather2d(0.5 if kind == "teal" else 0.42, 0.13, 0.05), bot - Y * 0.1, X, -Y, TEAL if kind == "teal" else BRASS, thick=0.01)
        return
    if pid.startswith("gal-weathervane"):
        tube(g.s, [Vector((0, y, 0)) for y in (0, 0.08, 0.16)], [0.12, 0.09, 0.05], BRASS, 8, cap_mat=BRASS)
        tube(g.s, [Vector((0, 0.1, 0)), Vector((0, h - 0.05, 0))], [0.025, 0.02], BRASS, 6, cap_mat=BRASS)
        yb = 0.5
        tube(g.s, [Vector((-0.78, yb, 0)), Vector((0.62, yb, 0))], [0.018, 0.018], BRASS, 5, cap_mat=BRASS)
        flat(g.s, [(0, -0.09), (0.18, 0), (0, 0.09)], Vector((0.6, yb, 0)), X, Y, BRASS, thick=0.02)
        flat(g.s, [(0, -0.07), (0.16, -0.03), (0.16, 0.03), (0, 0.07), (0.05, 0)], Vector((-0.8, yb, 0)), X, Y, BRASS, thick=0.02)
        tube(g.s, [Vector((0, yb, -0.35)), Vector((0, yb, 0.35))], [0.015, 0.015], BRASS, 5, cap_mat=BRASS)
        if pid.endswith("sail"):
            def P(u, v):
                return Vector((0.03 + 0.55 * u * (1 - v), 0.85 + 0.75 * v, 0.06 * math.sin(math.pi * u) * (1 - v)))

            sheet(g.s, P, 4, 4, SAIL)
            tube(g.s, [Vector((0.0, 0.85, 0)), Vector((0.6, 0.85, 0))], [0.012, 0.012], BRASS, 4)
            pennant(g.s, (0.0, h - 0.12, 0), 0.6, 0.14, X, TRIM, seed=1.0)
            spike(g.s, (0, h - 0.08, 0), 0.08, 0.025, ball=False)
        else:
            fo = feather2d(1.05, 0.3, 0.14)
            o = Vector((-0.35, 0.95, 0))
            dv = Vector((math.cos(0.75), math.sin(0.75), 0))
            flat(g.s, fo, o, dv.cross(Z) * -1, dv, BRASS, thick=0.03)
            tube(g.s, [Vector((0, 0.6, 0)), Vector((0, 0.95, 0))], [0.03, 0.03], BRASS, 6, cap_mat=BRASS)
        return
    if pid.endswith("finial-feather"):
        tube(g.s, [Vector((0, y, 0)) for y in (0, 0.06, 0.12, 0.2, 0.3, 0.38)], [0.14, 0.12, 0.06, 0.1, 0.05, 0.04], BRASS, 8, cap_mat=BRASS)
        flat(g.s, feather2d(1.02, 0.26, 0.08), Vector((0, 0.36, 0)), X, Y, BRASS, thick=0.035)
        return
    if "lantern" in pid:
        large = pid.endswith("large")
        s = 1.0 if large else 0.62
        cy = 0.75 if large else 0.52
        ring(g.s, (0, h - 0.06, 0), 0.05 * s + 0.01, Z, 0.014)
        if large:
            tube(g.s, [Vector((0, y, 0)) for y in (h - 0.12, 1.3, 1.18, 1.1)], [0.03, 0.1, 0.2, 0.18], BRASS, 8, cap_mat=BRASS)
            tube(g.s, [Vector((0, cy + 0.3 * math.cos(a), 0)) for a in (math.pi * k / 6 for k in range(7))], [max(0.02, 0.29 * math.sin(math.pi * k / 6)) for k in range(7)], GLOW, 8, cap_mat=GLOW)
            for k in range(4):
                a = math.pi / 4 + math.pi / 2 * k
                dv = Vector((math.cos(a), 0, math.sin(a)))
                pts = [dv * 0.33 * math.sin(math.pi * t) + Y * (cy + 0.36 - 0.72 * t) for t in (i / 8 for i in range(9))]
                tube(g.s, pts, [0.022] * 9, BRASS, 4, cap_mat=BRASS)
            ring(g.s, (0, cy, 0), 0.34, Y, 0.025, seg=12)
            tube(g.s, [Vector((0, y, 0)) for y in (0.42, 0.34, 0.3)], [0.18, 0.12, 0.05], BRASS, 8, cap_mat=BRASS)
            tube(g.s, [Vector((0, y, 0)) for y in (0.3, 0.22, 0.06, 0.0)], [0.02, 0.07, 0.04, 0.005], TEAL, 6, cap_mat=TEAL)
        else:
            tube(g.s, [Vector((0, y, 0)) for y in (h - 0.1, 0.86, 0.76, 0.72)], [0.02, 0.06, 0.18, 0.17], BRASS, 6, cap_mat=BRASS)
            tube(g.s, [Vector((0, 0.36, 0)), Vector((0, 0.72, 0))], [0.12, 0.12], GLOW, 6, cap_mat=GLOW)
            for k in range(4):
                a = math.pi / 4 + math.pi / 2 * k
                dv = Vector((math.cos(a), 0, math.sin(a)))
                tube(g.s, [dv * 0.15 + Y * 0.33, dv * 0.15 + Y * 0.74], [0.016, 0.016], BRASS, 4, cap_mat=BRASS)
            tube(g.s, [Vector((0, y, 0)) for y in (0.38, 0.32, 0.26)], [0.17, 0.15, 0.04], BRASS, 6, cap_mat=BRASS)
            tube(g.s, [Vector((0, y, 0)) for y in (0.26, 0.2, 0.06, 0.0)], [0.02, 0.05, 0.03, 0.005], TEAL, 6, cap_mat=TEAL)
        return
    if pid.endswith("lashing-cross"):
        abox(g.h, (-0.1, 0, -0.15), (0.1, 0.6, 0.03), r=r)
        abox(g.h, (-0.3, 0.2, -0.05), (0.3, 0.4, 0.13), r=r)
        for sgn in (1, -1):
            for k in range(3):
                o = (k - 1) * 0.05
                a = Vector((-0.17 * sgn + o, 0.13 + o * sgn, 0.0))
                b = Vector((0.17 * sgn + o, 0.47 + o * sgn, 0.0))
                pts = [a.lerp(b, t) + Z * (0.14 + 0.05 * math.sin(math.pi * t)) for t in (i / 5 for i in range(6))]
                rope(g.s, pts, 0.03, 4)
        return
    if pid.endswith("lashing-wrap"):
        tube(g.s, [Vector((0, y, 0)) for y in (0, 0.3, 0.6)], [0.13, 0.125, 0.12], TIMBER, 8, tile=0.8)
        pts = [Vector((math.cos(a) * 0.155, 0.1 + 0.38 * a / (10 * math.pi), math.sin(a) * 0.155)) for a in (10 * math.pi * k / 40 for k in range(41))]
        rope(g.s, pts, 0.035, 4)
        rope(g.s, [pts[-1], pts[-1] + Vector((0.08, -0.15, 0.1)), pts[-1] + Vector((0.12, -0.32, 0.12))], 0.03, 4)
        return
    if pid.endswith("lashing-knot"):
        abox(g.h, (-0.08, 0, -0.15), (0.08, 0.4, 0.0), r=r)
        tube(g.s, [Vector((x, 0.22, 0.08)) for x in (-0.3, 0, 0.3)], [0.08, 0.085, 0.08], TIMBER, 8, tile=0.8)
        for k in range(3):
            x = -0.06 + 0.06 * k
            pts = [Vector((x + 0.02 * math.sin(a), 0.22 + 0.12 * math.sin(a), 0.08 + 0.12 * math.cos(a))) for a in (2 * math.pi * i / 8 for i in range(9))]
            rope(g.s, pts, 0.028, 4, caps=False)
        rope(g.s, [Vector((0.06, 0.12, 0.17)), Vector((0.15, 0.04, 0.2)), Vector((0.24, 0.02, 0.16))], 0.026, 4)
        return
    # anything unforeseen: a plain timber block so the kit never has holes
    abox(g.h, (-w / 2, 0, -d / 2), (w / 2, h, d / 2), r=r)


BUILDERS = {"wall": build_wall, "insert": build_insert, "corner": build_corner, "floor": build_floor,
            "foundation": build_foundation, "access": build_access, "roof": build_roof, "crown": build_crown,
            "attachment": build_attachment}


def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    mats[GLOW].diffuse_color = (1.0, 0.72, 0.3, 1.0)
    g = G(seed)
    BUILDERS.get(p["family"], build_attachment)(p, g)
    fam = p["family"]
    bev = 0.012 if fam in ("insert", "attachment") else 0.022
    return finish(g, p["id"], mats, seed, bevel=bev, wob=0.0 if fam == "attachment" else 0.012)


if __name__ == "__main__":
    K.build_all(build_piece, extras=[("gal-lantern-large", "hanging"), ("gal-lantern-small", "hanging"), ("gal-chime", "hanging"),
                                     ("gal-sail-furled", "decor"), ("gal-weathervane-feather", "prop"), ("gal-crown-beacon", "decor")],
                biome="galeborne")
