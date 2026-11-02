# Detailed Rootwarden kit: textured, hand-shaped pieces built from kit.json on the blockout's sizes and sockets,
# joined prefabs from each prefab's layout, a demo catalogue, and contact-sheet renders.
# Textures are the painted swatches in art/textures/rootwarden (mirrored tiling hides their seams).
# Usage: Blender --background --python scripts/kit/rootwarden.py
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402  (kit, PIECES, V, frames, hermite, cut_openings, render helpers)

V = B.V
TEX = os.path.join(B.ROOT, "art/textures/rootwarden")
OUT = B.KIT_DIR
PREFAB_OUT = os.path.join(OUT, "prefabs")

# Material slots, in order; every object carries the full list so joined prefabs keep one material set
MATS = [("RW_Bark", "bark.png", 0), ("RW_Heartwood", "heartwood.png", 0), ("RW_Moss", "moss.png", 0),
        ("RW_FlowerMoss", "flowering-moss.png", 0), ("RW_Lattice", "lattice.png", 0), ("RW_Stone", "lichen-stone.png", 0),
        ("RW_Fungus", "fungus.png", 2.5), ("RW_Earth", "earth.png", 0), ("RW_Amber", (1.0, 0.6, 0.22), 3.0)]
BARK, HEART, MOSS, FLOWER, LATTICE, STONE, FUNGUS, EARTH, AMBER = range(len(MATS))


def make_materials():
    out = []
    for name, tex, emit in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 1.0
        if isinstance(tex, str):
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
            t.extension = "MIRROR"
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
            if emit:
                nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = emit
        else:
            bsdf.inputs["Base Color"].default_value = (*tex, 1)
            bsdf.inputs["Emission Color"].default_value = (*tex, 1)
            bsdf.inputs["Emission Strength"].default_value = emit
        out.append(m)
    return out


def reset():
    B.reset()
    return make_materials()


class Mesh:
    """bmesh with a UV layer; all coordinates are glTF (Y up) and converted on the way in."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def vert(self, p):
        return self.bm.verts.new(V(*p))

    def face(self, verts, uvs, mat):
        f = self.bm.faces.new(verts)
        f.material_index = mat
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def object(self, name, mats, moss=0.62, seed=0.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)  # weld UV seams; UVs live on loops and survive
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # Moss settles on upward-facing bark, broken up by noise
        if moss is not None:
            for f in bm.faces:
                if f.material_index == BARK and f.normal.z > moss and noise.noise(f.calc_center_median() * 0.9 + Vector((seed, 0, 0))) > -0.15:
                    f.material_index = MOSS
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        for poly in me.polygons:
            poly.use_smooth = True
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# ---------- primitives ----------

def tube(m, pts, radii, mat, sides=10, twist=0.0, rough=0.0, seed=0.0, caps=(True, True), tile=1.2, closed=False, flat=1.0, planar=False):
    """Swept tube with UVs (u around, v along, `tile` metres per texture repeat), surface noise that fades out
    near both ends so socket caps stay exact, and heartwood end caps."""
    pts = [Vector(p) for p in pts]
    fr = B.frames(pts)
    seg = [0.0] + [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    s = [sum(seg[: i + 1]) for i in range(len(pts))]
    L = max(s[-1], 1e-6)
    ravg = sum(radii) / len(radii)
    urep = max(1, round(2 * math.pi * ravg / tile))
    rings = []
    for i, (p, r, (t, n, b)) in enumerate(zip(pts, radii, fr)):
        fade = 1.0 if closed else min(1.0, s[i] / (0.15 * L + 1e-6), (L - s[i]) / (0.15 * L + 1e-6))
        ring = []
        for k in range(sides + 1):
            a = 2 * math.pi * k / sides + twist * s[i] / L
            d = n * math.cos(a) * flat + b * math.sin(a)
            disp = rough * r * noise.noise(p * 1.3 + d * 0.9 + Vector((seed, seed * 0.7, 0))) * fade
            q = p + d * (r + disp)
            ring.append((m.vert(q), (q.x / tile, q.z / tile) if planar else (k / sides * urep, s[i] / tile)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            m.face((r0[k][0], r0[k + 1][0], r1[k + 1][0], r1[k][0]),
                   (r0[k][1], r0[k + 1][1], r1[k + 1][1], r1[k][1]), mat)
    for end, ring, flip in ((caps[0], rings[0], True), (caps[1], rings[-1], False)):
        if not end or closed:
            continue
        verts = [v for v, _ in ring[:-1]]
        c = sum((v.co for v in verts), Vector()) / len(verts)
        uvs = [(0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
        if flip:
            verts, uvs = verts[::-1], uvs[::-1]
        f = m.bm.faces.new(verts)
        f.material_index = HEART
        for loop, uv in zip(f.loops, uvs):
            loop[m.uv].uv = uv
    return rings


def hermite(p0, t0, p1, t1, n=20):
    return B.hermite(Vector(p0), Vector(t0), Vector(p1), Vector(t1), n)


def path_between(sa, sb, height=None, n=20):
    pa, pb = Vector(sa["pos"]), Vector(sb["pos"])
    k = (pb - pa).length
    if height is not None and sa["dir"][1] < -0.9 and sb["dir"][1] < -0.9:
        k = 4 * height
    return hermite(pa, -Vector(sa["dir"]) * k, pb, Vector(sb["dir"]) * k, n)


def strands(m, pts, r, count=2, turns=1.3, rel=0.17, seed=0.0, start=0.12, end=0.9):
    """Thinner roots spiralling around a main root, so it reads as grown rather than piped."""
    fr = B.frames(pts)
    n = len(pts)
    for j in range(count):
        sub = []
        for i in range(int(n * start), int(n * end)):
            t = i / (n - 1)
            phi = j * 2 * math.pi / count + turns * 2 * math.pi * t + seed
            _, nn, bb = fr[i]
            sub.append(pts[i] + (nn * math.cos(phi) + bb * math.sin(phi)) * r * 0.93)
        if len(sub) > 3:
            tube(m, sub, [r * rel * (1.1 - 0.6 * i / len(sub)) for i in range(len(sub))], BARK, 6, rough=0.15, seed=seed + j)


def disc(m, centre, R, h, top_mat, side_mat, sides=16, rough=0.0, seed=0.0):
    c = Vector(centre)
    top, bot = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        rr = R * (1 + rough * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, seed))))
        top.append((m.vert(c + Vector((math.cos(a) * rr, h, math.sin(a) * rr))), (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))))
        bot.append(m.vert(c + Vector((math.cos(a) * rr, 0, math.sin(a) * rr))))
    m.face([v for v, _ in top][::-1], [uv for _, uv in top][::-1], top_mat)
    m.face(bot, [(0, 0)] * sides, top_mat)
    for k in range(sides):
        k1 = (k + 1) % sides
        m.face((bot[k], bot[k1], top[k1][0], top[k][0]), ((k / sides * 3, 0), ((k + 1) / sides * 3, 0), ((k + 1) / sides * 3, h), (k / sides * 3, h)), side_mat)


def fill(m, outline, z, mat):
    """Flat glowing or wooden panel filling a 2D outline (x, y) at depth z."""
    xs = [x for x, _ in outline]
    ys = [y for _, y in outline]
    w, h = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    verts = [m.vert((x, y, z)) for x, y in outline]
    m.face(verts[::-1], [((x - min(xs)) / w, (y - min(ys)) / h) for x, y in outline][::-1], mat)


# ---------- 2D outlines for openings and inserts ----------

def arch(w, h, n=12):
    return [(-w / 2, 0)] + [(math.cos(a) * w / 2, h - w / 2 + math.sin(a) * w / 2) for a in
                            (math.pi - math.pi * k / n for k in range(n + 1))] + [(w / 2, 0)]


def circle(cx, cy, R, n=16):
    return [(cx + R * math.cos(2 * math.pi * k / n), cy + R * math.sin(2 * math.pi * k / n)) for k in range(n)]


def teardrop(w, h, n=14):
    R = w / 2
    lower = [(R * math.cos(a), R + R * math.sin(a)) for a in (math.radians(-40 - 260 * k / n) for k in range(n + 1))]
    return lower[::-1] + [(0, h)]


def inside(pt, poly):
    x, y = pt
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            hit = not hit
    return hit


def frame(m, outline, z, r, closed=True, seed=0.0):
    pts = [Vector((x, y, z)) for x, y in outline]
    if closed:
        pts.append(pts[0].copy())
        pts.append(pts[1].copy())
    tube(m, pts, [r] * len(pts), BARK, 8, rough=0.18, seed=seed, caps=(not closed, not closed))


# ---------- pieces ----------

def build_root(p, m, seed):
    s = [x for x in p["sockets"] if x["name"] != "hang"]
    r = s[0]["diameter"] / 2
    if "flare" in p["id"]:
        top = Vector(s[0]["pos"])
        w = p["size"][0] / 2
        trunk = [Vector((0, top.y * t, 0)) for t in (0, 0.2, 0.45, 0.7, 1.0)]
        tube(m, trunk, [r * 1.7, r * 1.35, r * 1.12, r * 1.02, r], BARK, 12, twist=0.8, rough=0.12, seed=seed, caps=(False, True))
        n = 5
        for k in range(n):
            a = 2 * math.pi * k / n + seed
            d = Vector((math.cos(a), 0, math.sin(a)))
            start = Vector((0, top.y * 0.6, 0)) + d * r * 0.8
            end = d * w * (0.85 + 0.15 * math.sin(k * 2.3)) + Vector((0, -0.3, 0))
            pts = hermite(start, d * 1.2 + Vector((0, -0.6, 0)), end, d * 1.5 + Vector((0, -0.4, 0)), 12)
            tube(m, pts, [r * (0.55 - 0.4 * i / 12) for i in range(13)], BARK, 7, rough=0.2, seed=seed + k)
    elif "fork" in p["id"]:
        trunk, left, right = (Vector(x["pos"]) for x in s)
        mid = Vector((0, min(left.y, right.y) * 0.5, 0))
        tube(m, [trunk, trunk.lerp(mid, 0.5), mid + Vector((0, r * 0.5, 0))], [r, r * 1.08, r * 1.2], BARK, 12, twist=0.6, rough=0.1, seed=seed, caps=(True, False))
        for b, sock in ((left, s[1]), (right, s[2])):
            pts = hermite(mid, Vector((0, 1.5, 0)), b, Vector(sock["dir"]) * 1.5, 14)
            tube(m, pts, [r * (1.15 - 0.15 * i / 14) for i in range(15)], BARK, 10, twist=0.5, rough=0.1, seed=seed + b.x)
            strands(m, pts, r, 1, 0.8, seed=seed + b.x)
    else:
        pts = path_between(s[0], s[1], p["size"][1] - r)
        r1 = s[1]["diameter"] / 2
        radii = [r + (r1 - r) * i / (len(pts) - 1) for i in range(len(pts))]
        tube(m, pts, radii, BARK, 12, twist=0.9, rough=0.12, seed=seed)
        if r >= 0.45:
            strands(m, pts, (r + r1) / 2, 2, 1.2, seed=seed)


def dome_point(r, phi, theta, lift=0.0):
    rr = r + lift
    return Vector((rr * math.cos(phi) * math.cos(theta), rr * math.sin(phi), -rr * math.cos(phi) * math.sin(theta)))


def azimuth_to_theta(a):
    return math.radians(a - 90)


def build_shell(p, mats, seed):
    """Returns the finished shell object (dome with cut openings, ribs, rim root and opening frames)."""
    if p["id"].endswith("pod"):
        return build_pod(p, mats, seed)
    r, arc = p["radius"], p["arc"]
    m = Mesh()
    rings, segs = 10, max(2, round(arc / 90 * 8))
    closed = arc >= 360
    grid = []
    for i in range(rings + 1):
        phi = (math.pi / 2) * i / rings * 0.995
        row = []
        for j in range(segs + 1):
            th = math.radians(arc) * j / segs
            q = dome_point(r, phi, th)
            q *= 1 + 0.015 * noise.noise(q * 0.7 + Vector((seed, 0, 0)))
            row.append((m.vert(q), (th * r / 4.0, phi * r / 4.0)))
        grid.append(row)
    for i in range(rings):
        for j in range(segs):
            a, b, c, d = grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]
            m.face((a[0], b[0], c[0], d[0]), (a[1], b[1], c[1], d[1]), LATTICE)
    top = m.vert(dome_point(r, math.pi / 2, 0))
    for j in range(segs):
        a, b = grid[rings][j], grid[rings][j + 1]
        m.face((a[0], b[0], top), (a[1], b[1], (a[1][0], a[1][1] + 0.2)), LATTICE)
    if closed:
        bmesh.ops.remove_doubles(m.bm, verts=m.bm.verts, dist=1e-4)
    shell = m.object(p["id"], mats, moss=None)
    B.solidify(shell, max(0.25, r * 0.05))
    B.cut_openings(shell, p)

    d = Mesh()
    openings = p.get("openings", [])
    rib_r = max(0.12, r * 0.06)
    count = max(3, round(arc / 360 * 12))
    for k in range(count):
        th = math.radians(arc) * (k + 0.5) / count
        az = math.degrees(th) + 90
        phi0 = 0.0
        for o in openings:
            span = math.degrees((o["size"][0] / 2 + rib_r * 2) / max(r * 0.8, 0.1))
            if abs((az - o["azimuth"] + 180) % 360 - 180) < span:
                phi0 = math.asin(min(0.9, (o["height"] + o["size"][1] + 0.35) / r))
        pts = []
        if phi0 == 0:
            pts.append(dome_point(r, 0, th, rib_r * 2.5) + Vector((0, -0.3, 0)))
        steps = 12
        for i in range(steps + 1):
            phi = phi0 + (math.radians(84) - phi0) * i / steps
            pts.append(dome_point(r, phi, th + 0.12 * math.sin(phi * 3 + k) * (5 / r), rib_r * 0.45))
        tube(d, pts, [rib_r * (1.25 - 0.6 * i / len(pts)) for i in range(len(pts))], BARK, 8, twist=1.0, rough=0.2, seed=seed + k)
    # Rim root around the base, broken at doors
    door_spans = [(o["azimuth"], math.degrees((o["size"][0] / 2 + 0.4) / r)) for o in openings if o["height"] <= 0.01]
    run = []
    steps = max(8, round(arc / 360 * 64))
    for i in range(steps + 1):
        th = math.radians(arc) * i / steps
        az = math.degrees(th) + 90
        blocked = any(abs((az - a + 180) % 360 - 180) < sp for a, sp in door_spans)
        if blocked or i == steps:
            if not blocked:
                run.append(dome_point(r, 0.03, th, rib_r * 0.6))
            if len(run) > 2:
                tube(d, run, [rib_r * 0.9] * len(run), BARK, 8, rough=0.2, seed=seed + i)
            run = []
        else:
            run.append(dome_point(r, 0.03, th, rib_r * 0.6))
    # Root frames around each opening, following the dome's curve
    for n_o, o in enumerate(openings):
        w, h = o["size"]
        outline = arch(w + 0.3, h + 0.15) if o["kind"] == "door" else circle(0, h / 2, min(w, h) / 2 + 0.1)
        pts = []
        for x, y in outline:
            yy = o["height"] + y
            rs = math.sqrt(max(r * r - yy * yy, 0.01)) + 0.1
            a = math.radians(o["azimuth"]) + x / rs
            pts.append(Vector((rs * math.sin(a), yy, rs * math.cos(a))))
        if o["kind"] != "door":
            pts += [pts[0].copy(), pts[1].copy()]
        tube(d, pts, [max(0.12, r * 0.035)] * len(pts), BARK, 8, rough=0.2, seed=seed + n_o, caps=(o["kind"] == "door",) * 2)
    detail = d.object(p["id"] + ".detail", mats, seed=seed)
    return join([shell, detail], p["id"])


def build_pod(p, mats, seed):
    m = Mesh()
    h, w = p["size"][1], p["size"][0] / 2
    n = 16
    body = [Vector((0, h * 0.82 * (1 - i / n), 0)) for i in range(n + 1)]
    prof = [max(0.06, w * math.sin(math.pi * (i / n) ** 0.75)) for i in range(n + 1)]
    tube(m, body, prof, LATTICE, 16, rough=0.04, seed=seed)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        pts = [Vector((math.cos(a) * (pr + 0.06), y.y, math.sin(a) * (pr + 0.06))) for y, pr in zip(body, prof)]
        tube(m, pts[1:-1], [0.09] * (len(pts) - 2), BARK, 6, rough=0.2, seed=seed + k)
    hang = Vector(p["sockets"][0]["pos"])
    tube(m, [body[0], hang * 0.9 + body[0] * 0.1, hang], [0.2, 0.26, 0.3], BARK, 8, rough=0.15, seed=seed)
    pod = m.object(p["id"], mats, seed=seed)
    B.cut_openings(pod, p)
    f = Mesh()
    for o in p.get("openings", []):
        ow, oh = o["size"]
        pts = [Vector((x, o["height"] + oh / 2 + y - oh / 2, w * 0.97)) for x, y in teardrop(ow * 0.8, oh)]
        pts += [pts[0].copy(), pts[1].copy()]
        tube(f, pts, [0.08] * len(pts), BARK, 6, rough=0.2, seed=seed, caps=(False, False))
    return join([pod, f.object(p["id"] + ".frame", mats, seed=seed)], p["id"])


def build_insert(p, m, seed):
    w, h, _ = p["size"]
    pid = p["id"]
    if "window" in pid:
        if "cluster" in pid:
            shapes = [circle(-0.62, 0.72, 0.52), circle(0.62, 0.72, 0.52), circle(0, 1.42, 0.45)]
        elif "teardrop" in pid:
            shapes = [teardrop(w * 0.8, h)]
        else:
            shapes = [circle(0, h / 2, min(w, h) / 2 - 0.05)]
        for i, sh in enumerate(shapes):
            fill(m, sh, -0.05, AMBER)
            frame(m, sh, 0.02, 0.1, seed=seed + i)
            ys = [y for _, y in sh]
            xs = [x for x, _ in sh]
            cx, cy = sum(xs) / len(xs), (max(ys) + min(ys)) / 2
            tube(m, [(cx, min(ys) + 0.05, 0.0), (cx + 0.03, cy, 0.03), (cx, max(ys) - 0.05, 0.0)], [0.04] * 3, BARK, 6)
            tube(m, [(min(xs) + 0.05, cy, 0.0), (cx, cy + 0.03, 0.03), (max(xs) - 0.05, cy, 0.0)], [0.035] * 3, BARK, 6)
        return
    outline = arch(w - 0.2, h - 0.1)
    if "lattice" in pid:
        fill(m, outline, -0.08, AMBER)
        for sgn in (1, -1):
            for c in [x * 0.42 for x in range(-8, 9)]:
                run = []
                for i in range(21):
                    t = i / 20
                    x = -w / 2 + w * t
                    y = c + sgn * (x * 1.0) + h / 2
                    pt = (x, y)
                    if inside(pt, outline):
                        run.append(Vector((x, y, 0.035 * sgn * math.sin(t * 12))))
                    elif len(run) > 2:
                        tube(m, run, [0.055] * len(run), BARK, 5, rough=0.15, seed=seed + c, caps=(True, True))
                        run = []
                    else:
                        run = []
                if len(run) > 2:
                    tube(m, run, [0.055] * len(run), BARK, 5, rough=0.15, seed=seed + c)
    elif "curtain" in pid:
        fill(m, outline, -0.1, EARTH)
        x = -w / 2 + 0.28
        k = 0
        while x < w / 2 - 0.2:
            topy = max(y for (ox, y) in [(px, py) for px, py in outline] if abs(ox - x) < 0.35) - 0.1
            low = 0.08 + 0.35 * abs(math.sin(k * 1.7))
            pts = hermite((x, topy, 0.0), (0, -1, 0.05), (x + 0.06 * math.sin(k), low, 0.04), (0, -1, 0), 8)
            tube(m, pts, [0.085] * len(pts), MOSS if k % 4 == 1 else BARK, 6, rough=0.2, seed=seed + k, flat=0.45)
            x += 0.26
            k += 1
    else:  # iris: overlapping heartwood petals closing on a knot
        fill(m, outline, -0.08, EARTH)
        c = Vector((0, h * 0.44, 0))
        R = min(w / 2, h * 0.44) * 0.92
        for k in range(9):
            a0 = 2 * math.pi * k / 9
            pts = [c + Vector((math.cos(a0 + 0.7 * t) * (0.08 + R * t), math.sin(a0 + 0.7 * t) * (0.08 + R * t), 0.02 * k / 9)) for t in (i / 6 for i in range(7))]
            tube(m, pts, [0.06 + 0.2 * (1 - abs(2 * i / 6 - 1)) for i in range(7)], HEART, 6, flat=0.35, seed=seed + k)
        tube(m, [c + Vector((0, 0, -0.05)), c + Vector((0, 0, 0.12))], [0.16, 0.13], BARK, 10)
    frame(m, outline, 0.03, 0.15, closed=False, seed=seed)


def build_misc(p, m, seed):
    pid = p["id"]
    w, h, d = p["size"]
    if "cap" in pid:
        mat = FLOWER if "flowering" in pid else MOSS
        n = 8
        pts = [Vector((0, h * 0.75 * i / n - 0.15, 0)) for i in range(n + 1)]
        radii = [max(0.05, w / 2 * math.cos(math.pi / 2 * i / n) ** 0.55) for i in range(n + 1)]
        tube(m, pts, radii, mat, 20, rough=0.22, seed=seed, tile=3.0, planar=True)
    elif "fungus" in pid:
        for k, (x, z, hh, cr) in enumerate([(0, 0, 0.9, 0.42), (0.45, 0.2, 0.6, 0.3), (-0.4, 0.25, 0.5, 0.26), (0.15, -0.35, 0.4, 0.22)]):
            tube(m, hermite((x, 0, z), (0, 1, 0), (x + 0.05, hh, z), (0.1, 1, 0), 6), [0.08 * cr / 0.3] * 7, HEART, 6)
            tube(m, [Vector((x + 0.05, hh - 0.08, z)), Vector((x + 0.05, hh + 0.02, z)), Vector((x + 0.05, hh + 0.12, z))], [cr, cr * 0.85, 0.05], FUNGUS, 12, rough=0.1, seed=seed + k)
    elif "seedpod" in pid:
        tube(m, [(0, 1.0, 0), (0.02, 0.88, 0), (0, 0.78, 0)], [0.04] * 3, BARK, 6)
        tube(m, [Vector((0, 0.78 - 0.6 * i / 8, 0)) for i in range(9)], [max(0.03, 0.2 * math.sin(math.pi * (i / 8) ** 0.7)) for i in range(9)], AMBER, 10)
        for k in range(3):
            a = 2 * math.pi * k / 3
            tube(m, hermite((0, 0.8, 0), (math.cos(a), 0.3, math.sin(a)), (math.cos(a) * 0.22, 0.6, math.sin(a) * 0.22), (0, -1, 0), 5), [0.05, 0.07, 0.07, 0.06, 0.04, 0.02], MOSS, 5, flat=0.3)
    elif "stairs" in pid:
        tube(m, [Vector((0, y, 0)) for y in (0, 0.7, 1.4, h)], [0.32, 0.28, 0.25, 0.2], BARK, 10, twist=1.5, rough=0.15, seed=seed)
        for k in range(4):
            a = math.radians(-90 * k)
            disc(m, (math.cos(a) * 0.7, 0.3 + 0.48 * k, math.sin(a) * 0.7), 0.55, 0.14, HEART, BARK, rough=0.08, seed=seed + k)
    elif "railing" in pid:
        for x in (0.1, w - 0.1):
            tube(m, [(x, 0, -d / 2), (x, h, -d / 2)], [0.09, 0.07], BARK, 8, rough=0.2, seed=seed + x)
        for y in (h * 0.45, h * 0.9):
            tube(m, hermite((0.1, y, -d / 2), (1, 0.2, 0.1), (w - 0.1, y, -d / 2), (1, -0.2, -0.1), 10), [0.05] * 11, BARK, 6, rough=0.2, seed=seed + y)
    elif "floor" in pid:
        disc(m, (0, 0, 0), w / 2, h, HEART, BARK, 20, rough=0.04, seed=seed)
    elif "curtain" in pid:
        x = -w / 2 + 0.15
        k = 0
        while x < w / 2:
            ln = h * (0.55 + 0.45 * abs(math.sin(k * 2.1)))
            pts = hermite((x, h, 0), (0, -1, 0.1), (x + 0.1 * math.sin(k), h - ln, 0.05), (0, -1, 0), 8)
            tube(m, pts, [0.06 * (1 - 0.6 * i / 8) for i in range(9)], MOSS if k % 3 == 0 else BARK, 5, rough=0.2, seed=seed + k)
            x += 0.3
            k += 1
    else:
        m.bm.free()
        m.__init__()
        bmesh.ops.create_cube(m.bm, size=1)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    fam = p["family"]
    if fam == "shell":
        return build_shell(p, mats, seed)
    m = Mesh()
    if fam == "root":
        build_root(p, m, seed)
    elif fam == "insert":
        build_insert(p, m, seed)
    else:
        build_misc(p, m, seed)
    return m.object(p["id"], mats, seed=seed)


def tris(ob):
    return sum(len(poly.vertices) - 2 for poly in ob.data.polygons)


def export(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=88)


def main():
    os.makedirs(PREFAB_OUT, exist_ok=True)
    counts = {}
    for p in B.kit["pieces"]:
        mats = reset()
        ob = build_piece(p, mats)
        counts[p["id"]] = tris(ob)
        export(ob, os.path.join(OUT, f"{p['id']}.glb"))
    json.dump(counts, open(os.path.join(OUT, "tris.json"), "w"), indent=2)

    catalogue = []
    for f in B.kit["prefabs"]:
        mats = reset()
        parts = []
        for e in f["layout"]:
            ob = build_piece(B.PIECES[e["id"]], mats)
            ob.rotation_euler = (0, 0, math.radians(e.get("rotY", 0)))
            ob.location = V(*e["pos"])
            parts.append(ob)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="DESELECT")
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        ob = join(parts, f["id"])
        lo, hi = B.bounds([ob])
        export(ob, os.path.join(PREFAB_OUT, f"{f['id']}.glb"))
        catalogue.append({"id": f["id"], "file": f"{f['id']}.glb", "category": "building", "biomes": ["roothold"],
                          "radius": round(max(hi.x - lo.x, hi.y - lo.y) / 2, 2), "height": round(hi.z - lo.z, 2),
                          "minScale": 0.9, "maxScale": 1.1, "collide": True, "tris": tris(ob)})
    for pid, cat in (("rw-fungus-lantern", "prop"), ("rw-lamp-seedpod", "hanging"), ("rw-root-arch-d1.0", "decor"), ("rw-root-flare-d1.6", "decor")):
        p = B.PIECES[pid]
        catalogue.append({"id": pid, "file": f"{pid}.glb", "category": cat, "biomes": ["roothold"], "radius": round(p["size"][0] / 2, 2),
                          "height": p["size"][1], "minScale": 0.9, "maxScale": 1.2, "collide": cat == "decor"})
        mats = reset()
        export(build_piece(p, mats), os.path.join(PREFAB_OUT, f"{pid}.glb"))
    json.dump(catalogue, open(os.path.join(PREFAB_OUT, "rootwarden.json"), "w"), indent=2)

    # Contact sheets in textured workbench shading
    for name, items in (("sheet-pieces", None), ("sheet-prefabs", "prefabs")):
        mats = reset()
        objs = []
        x = y = row = 0.0
        if items is None:
            for p in B.kit["pieces"]:
                w, _, d = p["size"]
                if x + w > 60:
                    x, y, row = 0.0, y - row - 3, 0.0
                ob = build_piece(p, mats)
                ob.location += Vector((x + w / 2, y, 0))
                objs.append(ob)
                B.label(p["id"].removeprefix("rw-"), Vector((x + w / 2, y - d / 2 - 1.2, 0)), 0.45)
                x += w + 2.5
                row = max(row, d)
        else:
            for f in B.kit["prefabs"]:
                group = []
                for e in f["layout"]:
                    ob = build_piece(B.PIECES[e["id"]], mats)
                    ob.rotation_euler = (0, 0, math.radians(e.get("rotY", 0)))
                    ob.location = V(*e["pos"])
                    group.append(ob)
                bpy.context.view_layer.update()
                lo, hi = B.bounds(group)
                for o in group:
                    o.location.x += x - lo.x
                bpy.context.view_layer.update()
                lo, hi = B.bounds(group)
                objs += group
                objs.append(B.figure(Vector((hi.x + 1, lo.y, 0))))
                B.label(f["name"], Vector(((lo.x + hi.x) / 2, lo.y - 3, 0)), 1.0)
                x = hi.x + 6
        objs.append(B.figure(Vector((-3, 0, 0))))
        bpy.context.view_layer.update()
        B.render(os.path.join(OUT, f"{name}.png"), B.bounds(objs), "TEXTURE")
    print("[rootwarden] built", len(counts), "pieces,", len(catalogue), "catalogue entries")
    over = {k: v for k, v in counts.items() if v > B.PIECES[k]["tris"]}
    print("[rootwarden] over manifest tris:", json.dumps(over))


main()
