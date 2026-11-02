# Detailed Rootwarden kit: textured, hand-shaped pieces built from kit.json on the blockout's sizes and sockets,
# joined prefabs from each prefab's layout, a demo catalogue, and contact-sheet renders.
# Textures are the painted swatches in art/textures/rootwarden.
# Usage: Blender --background --python scripts/kit/rootwarden.py -- rootwarden
import bmesh, math, os, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, V, arch, circle, disc, fill, hermite, inside, join, path_between, teardrop, tube  # noqa: E402

# Material slots, in order; every object carries the full list so joined prefabs keep one material set
MATS = [("RW_Bark", "bark.png", 0), ("RW_Heartwood", "heartwood.png", 0), ("RW_Moss", "moss.png", 0),
        ("RW_FlowerMoss", "flowering-moss.png", 0), ("RW_Lattice", "lattice.png", 0), ("RW_Stone", "lichen-stone.png", 0),
        ("RW_Fungus", "fungus.png", 2.5), ("RW_Earth", "earth.png", 0), ("RW_Amber", (1.0, 0.6, 0.22), 3.0)]
BARK, HEART, MOSS, FLOWER, LATTICE, STONE, FUNGUS, EARTH, AMBER = range(len(MATS))
# Root ends show heartwood end grain; moss settles on upward-facing bark
K.configure(MATS, os.path.join(B.ROOT, "art/textures/rootwarden"), cap_mat=HEART, moss=(BARK, MOSS, 0.62))


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






K.build_all(build_piece, extras=[("rw-fungus-lantern", "prop"), ("rw-lamp-seedpod", "hanging"),
                                 ("rw-root-arch-d1.0", "decor"), ("rw-root-flare-d1.6", "decor")], biome="roothold")
