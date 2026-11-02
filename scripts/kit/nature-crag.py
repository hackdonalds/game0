# Crag nature kit: wind-bent pines, clinging junipers, alpine ground cover, sharp layered cragslate rocks, wild-crag
# cinder and ore-seam rocks, isle lips, undersides and a wind-blown fall, built from art/models/nature/crag/kit.json.
# Rocks are faceted prisms (irregular outlines, chamfered edges, stacked strata) rather than round blobs; foliage is
# clumped pads swept downwind (+X). Textures are painted swatches cropped from the crag concept sheets.
# Usage: Blender --background --python scripts/kit/nature-crag.py -- crag
#        Blender --background --python scripts/kit/nature-crag.py -- crag preview <id,id,...> <out dir>
import math, os, random, sys
from mathutils import Euler, Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
import naturelib as N  # noqa: E402
from kitlib import Mesh, hermite, tube  # noqa: E402

MATS = [("CG_AlpineTurf", "ground.png", 0), ("CG_GritPath", "path.png", 0), ("CG_CragslateCliff", "cliff.png", 0),
        ("CG_CragslateUnderside", "underside.png", 0), ("CG_PineBark", "pine-bark.png", 0),
        ("CG_SilverDeadwood", "silver-deadwood.png", 0), ("CG_PineNeedleFoliage", "needles.png", 0),
        ("CG_JuniperFoliage", "juniper.png", 0), ("CG_AlpineFlowerFoliage", "alpine-flowers.png", 0),
        ("CG_CushionMoss", "cushion-moss.png", 0), ("CG_Lichen", "lichen.png", 0), ("CG_DryGrassFoliage", "dry-grass.png", 0),
        ("CG_Cragslate", "cliff.png", 0), ("CG_CinderRock", "cinder-rock.png", 0), ("CG_OreSeam", "ore-seam.png", 0),
        ("CG_WaterSpray", "water-spray.png", 0), ("CG_DryTurf", "dry-turf.png", 0),
        # alpha-cutout sprite cards (2x2 painted atlases shared by every biome)
        ("CG_PineFoliageCard", "../../foliage/pine-needles.png", 0), ("CG_JuniperFoliageCard", "../../foliage/juniper.png", 0),
        ("CG_GrassFoliageCard", "../../foliage/grass.png", 0)]
(TURF, PATH, CLIFF, UNDER, BARK, DEAD, NEEDLE, JUNIPER, FLOWER, MOSS, LICHEN, GRASS, SLATE, CINDER, ORE, SPRAY,
 DRYTURF, PINECARD, JUNICARD, GRASSCARD) = range(len(MATS))
SOFT = {NEEDLE, JUNIPER, MOSS, PINECARD, JUNICARD}
CARDS = {PINECARD, JUNICARD}  # cards take a stronger sky lift: their pads are thin and sunlit
# grass.png quadrants: 2 short meadow, 3 long meadow, 0 dry alpine, 1 salt grass
DRY, LONG, SHORT = 0, 3, 2
K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/crag"), cap_mat=BARK, moss=None)

WIND = Vector((1, 0, 0))
UP = Vector((0, 1, 0))
# alpine-flowers.png is a 2x2 atlas: gentian blue, white star, pink, leaf green
QUAD = {"blue": (0.0, 0.5), "white": (0.5, 0.5), "pink": (0.0, 0.0), "leaf": (0.5, 0.0)}


def atlas(q, u, v):
    x, y = QUAD[q]
    return (x + 0.5 * (0.06 + 0.88 * min(max(u, 0), 1)), y + 0.5 * (0.06 + 0.88 * min(max(v, 0), 1)))


def rot(x=0.0, y=0.0, z=0.0):
    return Euler((x, y, z), "XYZ").to_matrix()


# ---------- faceted rock primitives ----------

def jag(rng, n, rx, rz, irr=0.15, phase=None):
    """Irregular convex-ish polygon (x, z): angular outlines for slabs and shards."""
    phase = rng.uniform(0, 2 * math.pi) if phase is None else phase
    pts = []
    for k in range(n):
        a = phase + 2 * math.pi * (k + rng.uniform(-0.28, 0.28)) / n
        r = 1 + rng.uniform(-irr, irr)
        pts.append((math.cos(a) * rx * r, math.sin(a) * rz * r))
    return pts


def prism(m, c, outline, levels, mat, R=None, tile=2.0, caps=(None, None), bands=None):
    """Stack of rings from a 2D outline: levels are (y, scale[, (dx, dz)[, slope]]), slope tilting the ring along x.
    A scale below 0.03 closes to a point. `bands` gives a material per band between rings (chamfers, seams)."""
    c = Vector(c)
    R = R or Matrix.Identity(3)
    n = len(outline)
    cx = sum(x for x, _ in outline) / n
    cz = sum(z for _, z in outline) / n
    rings = []
    pos = {}
    h = math.sin(c.x * 12.9898 + c.y * 4.1414 + c.z * 78.233) * 43758.5453
    off = (h % 1.0, (h * 7.13) % 1.0)

    def F(vs, mm):
        P = [pos[v] for v in vs]
        nrm = Vector((0, 0, 0))
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            nrm += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        ax = max(range(3), key=lambda i: abs(nrm[i]))
        uv = [((q.x if ax else q.z) / tile + off[0], (q.y if ax != 1 else q.z) / tile + off[1]) for q in P]
        # keep each face inside one texture repeat where it fits, so mirrored tiling never shows a butterfly seam
        fixed = []
        for i in (0, 1):
            lo_, hi_ = min(t[i] for t in uv), max(t[i] for t in uv)
            shift = -math.floor(lo_)
            if hi_ + shift > 1.0 and hi_ - lo_ < 1.0:
                shift = -lo_ + (1.0 - (hi_ - lo_)) * ((off[i] * 3.7) % 1.0)
            fixed.append(shift)
        m.face(vs, [(u + fixed[0], v + fixed[1]) for u, v in uv], mm)

    def mv(q):
        v = m.vert(q)
        pos[v] = Vector(q)
        return v

    for lv in levels:
        y, s = lv[0], lv[1]
        dx, dz = lv[2] if len(lv) > 2 else (0.0, 0.0)
        slope = lv[3] if len(lv) > 3 else 0.0
        if s < 0.03:
            rings.append(mv(c + R @ Vector((cx + dx, y, cz + dz))))
        else:
            ring = []
            for x, z in outline:
                lx, lz = cx + (x - cx) * s + dx, cz + (z - cz) * s + dz
                ring.append(mv(c + R @ Vector((lx, y + slope * (lx - cx), lz))))
            rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        bm = bands[i] if bands and i < len(bands) and bands[i] is not None else mat
        if isinstance(r0, list) and isinstance(r1, list):
            for k in range(n):
                F((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]), bm)
        elif isinstance(r0, list):
            for k in range(n):
                F((r0[k], r0[(k + 1) % n], r1), bm)
        else:
            for k in range(n):
                F((r0, r1[(k + 1) % n], r1[k]), bm)
    if isinstance(rings[0], list):
        F(rings[0][::-1], caps[0] if caps[0] is not None else mat)
    if isinstance(rings[-1], list):
        F(rings[-1], caps[1] if caps[1] is not None else mat)


def slab(m, rng, c, rx, rz, t, mat, R=None, n=6, irr=0.14, taper=0.93, ch=0.3, chs=0.86, tile=2.0, top=None,
         chamfer_mat=None, slope=0.0):
    """One stratum: an angular plate with a chamfered top edge."""
    out = jag(rng, n, rx, rz, irr)
    prism(m, c, out, [(0, 1), (t * (1 - ch), taper, (0, 0), slope), (t, taper * chs, (0, 0), slope)], mat, R, tile,
          caps=(None, top), bands=[None, chamfer_mat])
    return out


def shard(m, rng, c, rx, rz, L, mat, R=None, n=5, down=False, kink=0.18, tile=2.0, mid=0.5, irr=0.2):
    """Tapering blade: spires (up) and hanging points (down)."""
    s = -1 if down else 1
    k = (rng.uniform(-kink, kink) * rx, rng.uniform(-kink, kink) * rz)
    tip = (k[0] * 2 + rng.uniform(-0.1, 0.1) * rx, k[1] * 2)
    prism(m, c, jag(rng, n, rx, rz, irr), [(0, 1), (s * L * mid, 0.72, k), (s * L, 0.0, tip)], mat, R, tile)


def chunk(m, rng, c, s, mat, R=None, tile=1.2):
    """Small sharp scree shard or pebble."""
    R = R or rot(rng.uniform(-0.5, 0.5), rng.uniform(0, 6.3), rng.uniform(-0.5, 0.5))
    prism(m, c, jag(rng, rng.choice((4, 5)), s, s * rng.uniform(0.6, 0.9), 0.2),
          [(-s * 0.35, 1), (s * 0.35, 0.82, (rng.uniform(-0.2, 0.2) * s, 0)), (s * rng.uniform(0.7, 1.0), 0.0, (rng.uniform(-0.3, 0.3) * s, 0))],
          mat, R, tile)


def block(m, rng, c, rx, rz, h, mat, R=None, n=6, slope=0.3, irr=0.12, tile=2.0, edge=None, crown=0.62, lean=(0.0, 0.0)):
    """Angular boulder block: straight sides, a sloping top with chamfered planes (crisp painted facets).
    `edge` gives the chamfer band its own material (lichen crust, an ore glint)."""
    lx, lz = lean
    prism(m, c, jag(rng, n, rx, rz, irr), [(0, 1), (h * 0.7, 0.97, (lx * 0.7, lz * 0.7), slope), (h * 0.9, 0.84, (lx, lz), slope),
                                          (h, crown, (lx * 1.1, lz * 1.1), slope)], mat, R, tile, bands=[None, edge, edge])


# ---------- plants ----------

def clump(m, centre, radii, mat, seed=0.0, rough=0.25, rings=6, segs=10, tile=1.5, flat_base=1.0, box=True, register=True, freq=1.7):
    """naturelib.blob with top-down planar UVs (no pole pinch) or box projection (rock); same noise and shape."""
    c = Vector(centre)
    rx, ry, rz = radii
    off = Vector((seed, seed * 0.37, seed * 0.71))
    uo = (seed * 0.613) % 1.0
    if register and mat in SOFT:
        PADS.append((c, (rx, ry, rz)))

    ph = (seed * 2.399) % (2 * math.pi)

    def point(phi, th):
        th += ph
        d = Vector((math.cos(phi) * math.cos(th), math.sin(phi), math.cos(phi) * math.sin(th)))
        k = 1 + rough * noise.noise(d * freq + off)
        return c + Vector((d.x * rx * k, d.y * ry * k * (flat_base if d.y < 0 else 1), d.z * rz * k))

    def V(q):
        return (m.vert(q), (q.x / tile + uo, q.z / tile + uo * 0.7 + q.y * 0.15 / tile))

    rows = [[V(point(-math.pi / 2 + math.pi * i / rings, 2 * math.pi * j / segs)) for j in range(segs)] for i in range(1, rings)]
    bottom, top = V(point(-math.pi / 2, 0)), V(point(math.pi / 2, 0))
    f = lambda vs: m.face([v for v, _ in vs], None if box else [uv for _, uv in vs], mat, tile)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(segs):
            j1 = (j + 1) % segs
            f((r0[j], r0[j1], r1[j1], r1[j]))
    for j in range(segs):
        j1 = (j + 1) % segs
        f((bottom, rows[0][j1], rows[0][j]))
        f((rows[-1][j], rows[-1][j1], top))


def face_tris(m):
    return sum(len(f.verts) - 2 for f in m.bm.faces)


def track(m):
    m.bm.verts.ensure_lookup_table()
    return len(m.bm.verts)


def shear(m, n0, k, y0=0.0, kz=0.0):
    """Comb new vertices downwind: x += k * (height above y0). Blender coords (Z up, Y = -z)."""
    m.bm.verts.ensure_lookup_table()
    for v in m.bm.verts[n0:]:
        dy = v.co.z - y0
        v.co.x += k * dy
        v.co.y -= kz * dy


def pad(m, rng, c, rx, ry, rz, mat, seed, lumps=10, comb=0.35, tile=0.75):
    """Flat needle pad: a low flat-bottomed cushion crowded with small tufts round the rim and on top, so the
    silhouette reads clumped like the painted pads, then combed downwind."""
    c = Vector(c)
    n0 = track(m)
    PADS.append((c + Vector((comb * ry * 0.3, ry * 0.15, 0)), (rx * 1.05, ry * 1.1, rz * 1.05)))
    clump(m, c, (rx * 0.8, ry * 0.7, rz * 0.8), mat, seed=seed, rough=0.3, rings=4, segs=9, tile=tile, flat_base=0.35, register=False)
    rim = lumps - 3
    for i in range(lumps):
        if i < rim:
            a = 2 * math.pi * i / rim + rng.uniform(-0.25, 0.25)
            rr = rng.uniform(0.7, 0.92)
            off = Vector((math.cos(a) * rx * rr, ry * rng.uniform(-0.1, 0.25), math.sin(a) * rz * rr))
            s = rng.uniform(0.25, 0.36)
        else:
            off = Vector((rng.uniform(-0.4, 0.4) * rx, ry * rng.uniform(0.35, 0.55), rng.uniform(-0.35, 0.35) * rz))
            s = rng.uniform(0.3, 0.4)
        clump(m, c + off, (rx * s, max(ry * rng.uniform(0.7, 0.95), rx * s * 0.5), rx * s * rng.uniform(0.8, 1.0)), mat, seed=seed + 3.1 * (i + 1),
              rough=0.42, rings=3, segs=8, tile=tile, flat_base=0.5, register=False)
    shear(m, n0, comb, c.y)


def blade_strip(m, pts, width, mat, uv=None, taper=0.12):
    """Flat strip along a polyline, facing up/sideways; uv(u, v) maps into a texture region."""
    n = len(pts)
    prev = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(UP)
        if side.length < 1e-4:
            side = Vector((0, 0, 1))
        side.normalize()
        w = width * (1 - (1 - taper) * i / (n - 1))
        v = i / (n - 1)
        pair = ((m.vert(p - side * w), uv(0, v) if uv else (0, v)), (m.vert(p + side * w), uv(1, v) if uv else (1, v)))
        if prev:
            m.face((prev[0][0], prev[1][0], pair[1][0], pair[0][0]), (prev[0][1], prev[1][1], pair[1][1], pair[0][1]), mat)
        prev = pair


def tuft(m, rng, c, count, h, length, mat=GRASS, spread=0.55, width=0.03, segs=3, upwind=0.0):
    """Wind-flattened grass: blades rise a little then comb flat downwind (+X)."""
    c = Vector(c)
    for _ in range(count):
        a = rng.gauss(0, spread)
        d = Vector((math.cos(a), 0, math.sin(a)))
        if rng.random() < upwind:
            d = Vector((-d.x * 0.4, 0, d.z)).normalized()
        base = c + Vector((rng.uniform(-1, 1), 0, rng.uniform(-1, 1))) * length * 0.12
        hh = h * rng.uniform(0.55, 1.0)
        ln = length * rng.uniform(0.6, 1.0)
        tip = base + d * ln + Vector((0, hh * rng.uniform(0.4, 0.8), 0))
        pts = hermite(base, Vector((0, hh * 1.6, 0)) + d * ln * 0.2, tip, d * ln * 1.1 + Vector((0, -hh * 0.4, 0)), segs)
        blade_strip(m, pts, width * rng.uniform(0.8, 1.2), mat)


def star(m, c, r, q, points=5, inner=0.45, tilt=None, rng=None):
    """Flat star flower facing up (pentagon when points == 0)."""
    c = Vector(c)
    R = tilt or Matrix.Identity(3)
    ph = rng.uniform(0, 6.3) if rng else 0
    if points == 0:
        k = 5
        vs = [(math.cos(ph + 2 * math.pi * i / k), math.sin(ph + 2 * math.pi * i / k)) for i in range(k)]
    else:
        vs = []
        for i in range(points * 2):
            a = ph + math.pi * i / points
            rr = 1 if i % 2 == 0 else inner
            vs.append((math.cos(a) * rr, math.sin(a) * rr))
    m.face([m.vert(c + R @ Vector((x * r, 0, z * r))) for x, z in vs], [atlas(q, 0.5 + x * 0.45, 0.5 + z * 0.45) for x, z in vs], FLOWER)


def blob_point(c, radii, seed, rough, d):
    """Surface point of naturelib.blob along direction d (same noise), for seating flowers on cushions."""
    off = Vector((seed, seed * 0.37, seed * 0.71))
    d = Vector(d).normalized()
    k = 1 + rough * noise.noise(d * 1.7 + off)
    return Vector(c) + Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k))


def sweep(m, pts, widths, thick, mat, sides=6, tile=2.0, hint=Vector((1, 0, 0))):
    """Flattened tube whose wide axis follows `hint` (water ribbons)."""
    s_acc = 0.0
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if i:
            s_acc += (pts[i] - pts[i - 1]).length
        sd = (hint - t * hint.dot(t))
        sd = sd.normalized() if sd.length > 1e-4 else Vector((0, 0, 1))
        nn = t.cross(sd)
        rings.append([(m.vert(p + sd * math.cos(2 * math.pi * k / sides) * widths[i] + nn * math.sin(2 * math.pi * k / sides) * thick[i]),
                       (k / sides, s_acc / tile)) for k in range(sides + 1)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            m.face((r0[k][0], r0[k + 1][0], r1[k + 1][0], r1[k][0]), (r0[k][1], r0[k + 1][1], r1[k + 1][1], r1[k][1]), mat)
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        vs = [v for v, _ in ring[:-1]]
        m.face(vs[::-1] if flip else vs, [(0.5, 0.5)] * len(vs), mat)


# ---------- alpha-cutout cards ----------

def spray(m, rng, c, rx, ry, rz, n, mat, size, yaw=1.0, tilt=(0.7, 1.3), lift=0.0, flip=0.25, rim=0.6, pick=None, down=0.1):
    """Flat wind-combed foliage mass from sprite cards laid like shingles: each card's right edge points downwind
    (+X, yaw-jittered) so the painted sprays stream with the wind; rim cards stand near upright and hang their
    ragged sprays below the pad, cards towards the middle lie back until they are almost flat on top. The pad is
    registered for soft normals so every card shades with the whole mass (sunlit top, cool underside). `rim` < 1 crowds
    cards towards the rim (ragged edge), `flip` is the share of cards leaning the other way so no view sees them all edge-on."""
    c = Vector(c)
    PADS.append((c + Vector((rx * 0.05, ry * 0.1, 0)), (rx * 1.1, ry * 1.8, rz * 1.1)))
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.random() ** rim
        h = math.sqrt(max(0.0, 1 - r * r))  # 1 in the middle, 0 at the rim
        y = ry * (h * rng.uniform(0.25, 1.0) - down * (1 - h))
        p = c + Vector((math.cos(a) * rx * r + rx * 0.12 * r * max(0.0, math.cos(a)), y + lift, math.sin(a) * rz * r))
        yw = max(-yaw, min(yaw, rng.gauss(0, yaw * 0.55)))
        right = Vector((math.cos(yw), rng.uniform(-0.12, 0.12), math.sin(yw))).normalized()
        side = right.cross(UP).normalized()
        out = p - c
        sgn = (1 if out.dot(side) >= 0 else -1) * (-1 if rng.random() < flip else 1)
        th = min(1.35, max(0.05, tilt[0] + (tilt[1] - tilt[0]) * h + rng.uniform(-0.25, 0.25)))
        up = (UP * math.cos(th) - side * sgn * math.sin(th)).normalized()
        right = (right - up * right.dot(up)).normalized()
        q = Vector((out.x / rx, out.y / ry, out.z / rz))
        nrm = (q + Vector((0, 0.6, 0))).normalized()
        s = rng.uniform(*size)
        p.y = min(p.y, c.y + lift + ry * 1.05 - s * 0.5 * up.y)  # nothing pokes up out of the flat top
        N._card(m, p, right, up, s, s, mat, N._quadrant(rng, 2, pick), normal=nrm)


def grass(m, rng, base, h, w=None, pick=DRY, planes=3, spread=1.5, sink=0.12, lean=0.12):
    """Crossed grass cards rooted at `base`, every plane's right edge downwind so the painted wind-combed sprite
    keeps streaming +X; normals lean up so a tuft lights like the turf it stands on."""
    b = Vector(base)
    w = w or h * 1.35
    uv0 = N._quadrant(rng, 2, pick)
    a0 = rng.uniform(-0.25, 0.25)
    for k in range(planes):
        a = a0 + spread * ((k + 0.5) / planes - 0.5) + rng.uniform(-0.15, 0.15)
        right = Vector((math.cos(a), 0, math.sin(a)))
        face = right.cross(UP)
        up = (UP + WIND * lean + face * rng.uniform(-0.15, 0.15)).normalized()
        hh = h * rng.uniform(0.85, 1.1)
        N._card(m, b + up * hh * (0.5 - sink) + right * w * 0.08, right, up, w * rng.uniform(0.9, 1.1), hh, GRASSCARD, uv0,
                normal=(face * 0.3 + UP * 0.8).normalized())


# ---------- wood ----------

def gnarl(m, pts, r, mat, count=2, turns=1.4, seed=0.0, rel=0.3, cap=None):
    """Twisting secondary strands wound round a trunk, so it reads twisted and grown."""
    fr = B.frames(pts)
    n = len(pts)
    for j in range(count):
        sub = []
        for i in range(1, int(n * 0.8)):
            phi = j * 2 * math.pi / count + turns * 2 * math.pi * i / n + seed
            _, nn, bb = fr[i]
            sub.append(pts[i] + (nn * math.cos(phi) + bb * math.sin(phi)) * r[i] * 0.82)
        if len(sub) > 3:
            tube(m, sub, [r[0] * rel * (1 - 0.6 * i / len(sub)) for i in range(len(sub))], mat, 6, rough=0.2, seed=seed + j,
                 cap_mat=cap)


def limb(m, start, end, t0, t1, r0, r1, mat, sides=6, n=6, rough=0.2, seed=0.0, twist=0.5, cap=None):
    pts = hermite(start, t0, end, t1, n)
    tube(m, pts, [r0 + (r1 - r0) * i / n for i in range(n + 1)], mat, sides, twist=twist, rough=rough, seed=seed, cap_mat=cap)
    return pts


def deadwood(m, rng, start, d, L, r, depth, mat=DEAD, sides=5, lift=0.25, wind=0.35):
    """Bleached forking branch reaching up and downwind."""
    d = Vector(d).normalized()
    end = Vector(start) + d * L
    t1 = (d + WIND * wind + UP * lift).normalized() * L
    pts = limb(m, start, end, d * L, t1, r, max(0.018, r * 0.55), mat, sides, 4, 0.25, seed=start[0] * 3.1, cap=mat)
    if depth > 0:
        for k in range(2 if depth > 1 or rng.random() < 0.7 else 1):
            axis = d.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
            nd = (Matrix.Rotation(rng.uniform(0.35, 0.75) * (1 if k else -1), 3, axis) @ d + WIND * 0.3 + UP * 0.15).normalized()
            at = pts[-1] if k == 0 else pts[rng.randint(2, 3)]
            deadwood(m, rng, at, nd, L * rng.uniform(0.5, 0.7), max(0.018, r * 0.6), depth - 1, mat, max(4, sides - 1), lift, wind)
    return pts


def roots(m, rng, base, r, count, reach, mat=BARK, seed=0.0, y0=0.5):
    """Root flare: roots leave the trunk, drop to the ground, snake along it and dive in."""
    ends = []
    for k in range(count):
        a = 2 * math.pi * k / count + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), 0, math.sin(a)))
        side = Vector((-d.z, 0, d.x)) * rng.uniform(-0.4, 0.4)
        L = reach * rng.uniform(0.7, 1.15)
        st = Vector(base) + Vector((0, y0 * rng.uniform(0.8, 1.2), 0)) + d * r * 0.3
        mid = Vector(base) + (d + side * 0.5) * L * 0.55 + Vector((0, -0.2, 0))
        en = Vector(base) + (d + side) * L + Vector((0, -0.55, 0))
        p1 = hermite(st, d * L * 0.3 + Vector((0, -0.6, 0)), mid, (d + side) * L * 0.6, 4)
        p2 = hermite(mid, (d + side) * L * 0.6, en, (d + side) * L * 0.4 + Vector((0, -0.5, 0)), 4)
        pts = p1 + p2[1:]
        tube(m, pts, [r * 0.55 * (1 - 0.75 * i / (len(pts) - 1)) for i in range(len(pts))], mat, 5, twist=0.8, rough=0.25, seed=seed + k)
        ends.append(mid)
    return ends


# ---------- piece assembly ----------

class Piece:
    """Hard (flat-shaded rock) and soft (smooth wood, foliage) meshes joined into one object, fitted to the manifest."""

    def __init__(self, p):
        self.p = p
        self.seed = (sum(map(ord, p["id"])) % 97) * 0.37
        self.rng = random.Random(p["id"])
        self.hard, self.soft = Mesh(), Mesh()
        PADS.clear()

    def done(self, mats, lichen=None, fit=True):
        obs = []
        if self.hard.bm.faces:
            ob = self.hard.object(self.p["id"] + ".hard", mats, moss=None, smooth=False)
            if lichen:
                spot(ob, *lichen, seed=self.seed)
            obs.append(ob)
        else:
            self.hard.bm.free()
        if self.soft.bm.faces:
            obs.append(self.soft.object(self.p["id"] + ".soft", mats, moss=None, smooth=True))
        else:
            self.soft.bm.free()
        ob = K.join(obs, self.p["id"])
        xf = fit_size(ob, self.p) if fit else (lambda q: q)
        soft_normals(ob, [(xf(B.V(*c)), r) for c, r in PADS])
        return ob


def spot(ob, src, dst, up, thr=0.0, freq=0.9, seed=0.0):
    """Lichen and moss patches: upward faces of `src` where smooth noise exceeds `thr` become `dst`."""
    for poly in ob.data.polygons:
        if poly.material_index == src and poly.normal.z > up and noise.noise(Vector(poly.center) * freq + Vector((seed, 2.0, 0))) > thr:
            poly.material_index = dst


def fit_size(ob, p, lo=0.75, hi=1.3):
    """Centre the footprint on the pivot and scale each axis to the manifest size (above-ground part)."""
    w, h, d = p["size"]
    vs = ob.data.vertices
    above = [v.co for v in vs if v.co.z > 0.02] or [v.co for v in vs]
    x0, x1 = min(c.x for c in above), max(c.x for c in above)
    y0, y1 = min(c.y for c in above), max(c.y for c in above)
    z1 = max(c.z for c in above)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sx = min(hi, max(lo, w / max(x1 - x0, 1e-3)))
    sy = min(hi, max(lo, d / max(y1 - y0, 1e-3)))
    sz = min(hi, max(lo, h / max(z1, 1e-3)))
    for v in vs:
        v.co.x = (v.co.x - cx) * sx
        v.co.y = (v.co.y - cy) * sy
        v.co.z = v.co.z * sz
    ob.data.update()
    FITS[p["id"]] = (round(sx, 2), round(sz, 2), round(sy, 2))
    return lambda q: Vector(((q.x - cx) * sx, (q.y - cy) * sy, q.z * sz))


PADS = []  # (centre glTF, (rx, ry, rz)) of every foliage mass in the piece being built


def soft_normals(ob, pads):
    """Foliage lumps take the normal of the whole pad they belong to (ellipsoid gradient, lifted towards the sky),
    so overlapping lumps shade as one soft painted mass instead of a heap of pebbles. Everything else keeps its
    own shading (faceted rock stays flat)."""
    me = ob.data
    if not pads:
        return
    me.update()
    corner = [Vector(n.vector) for n in me.corner_normals]
    out = []
    for poly in me.polygons:
        soft = poly.material_index in SOFT
        for li in poly.loop_indices:
            if not soft:
                out.append(corner[li] if poly.use_smooth else Vector(poly.normal))
                continue
            p = me.vertices[me.loops[li].vertex_index].co
            best, bn = 1e9, None
            for c, (rx, ry, rz) in pads:
                q = Vector(((p.x - c.x) / rx, (p.y - c.y) / rz, (p.z - c.z) / ry))
                if q.length < best:
                    best = q.length
                    bn = Vector(((p.x - c.x) / rx ** 2, (p.y - c.y) / rz ** 2, (p.z - c.z) / ry ** 2))
            n = bn.normalized() if bn.length > 1e-6 else Vector((0, 0, 1))
            out.append((n + Vector((0, 0, 0.75 if poly.material_index in CARDS else 0.45))).normalized())
    me.normals_split_custom_set(out)


FITS = {}


# ---------- trees ----------

def pine(P, trunk_ctrl, radii, pads, branches, root_count=5, stones=(), rock=None, card_size=(0.55, 0.9)):
    m, rng, sd = P.soft, P.rng, P.seed
    pts = []
    for i, (a, ta, b, tb, n) in enumerate(trunk_ctrl):
        seg = hermite(a, ta, b, tb, n)
        pts += seg if i == 0 else seg[1:]
    r = [radii[0] + (radii[1] - radii[0]) * (i / (len(pts) - 1)) ** 0.8 + radii[0] * 0.5 * max(0, 1 - i / 3) ** 2 for i in range(len(pts))]
    tube(m, pts, r, BARK, 10, twist=1.4, rough=0.22, seed=sd, caps=(False, True))
    gnarl(m, pts, r, BARK, 2, 0.9, sd, rel=0.34)
    roots(m, rng, pts[0] + Vector((0, 0.3, 0)), radii[0] * 1.2, root_count, radii[0] * 3.4, seed=sd, y0=0.35)
    for (ti, pi, rr) in branches:
        a = pts[min(ti, len(pts) - 1)]
        c, rx, ry, rz = pads[pi]
        b = Vector(c) + Vector((-rx * 0.25, -ry * 0.3, 0))
        d = b - a
        pts_b = limb(m, a, b, Vector((d.x * 0.6, d.length * 0.9, d.z * 0.6)), Vector((d.x, d.length * 0.1, d.z)) * 0.8, rr, rr * 0.4,
                     BARK, 6, 5, 0.2, seed=sd + pi, twist=0.6)
        # branchlets fanning out under the pad, so the gaps between sprays show wood rather than sky
        for j, (fx, fz) in enumerate(((0.8, rng.uniform(-0.5, 0.5)), (0.2, rng.choice((-0.75, 0.75))))):
            tw = Vector(c) + Vector((rx * fx, -ry * 0.45, rz * fz))
            limb(m, pts_b[3], tw, (tw - pts_b[3]) * 0.8 + Vector((0, 0.3, 0)), (tw - pts_b[3]) * 0.6, rr * 0.35, 0.02, BARK, 4, 3, 0.2)
    h = P.hard
    for (c, s) in stones:
        slab(h, rng, c, s, s * 0.8, s * 0.7, SLATE, rot(rng.uniform(-0.3, 0.3), rng.uniform(0, 6), rng.uniform(-0.3, 0.3)), n=5, taper=0.8)
    base = pts[0] + Vector((0, 0.3, 0))
    clump(m, base + Vector((0.3, -0.25, 0.4)), (0.8, 0.18, 0.6), TURF, seed=sd, rough=0.3, rings=4, segs=8, tile=2.5, flat_base=0.3)
    for (dx, dz, hh) in ((0.6, 0.6, 0.6), (1.0, 0.1, 0.5), (-0.6, -0.4, 0.55), (-0.2, 0.75, 0.45), (0.3, -0.7, 0.5)):
        grass(m, rng, base + Vector((dx, -0.3, dz)), hh, pick=rng.choice((DRY, DRY, LONG)))
    # needle pads last: layered pine-needle cards spending the rest of the budget, shared out by pad area
    cards = (P.p["tris"] - 30 - face_tris(m) - face_tris(h)) // 2
    area = sum(rx * rz for _, rx, _, rz in pads)
    for i, (c, rx, ry, rz) in enumerate(pads):
        k = min(1.0, (rx / 1.6) ** 0.5)
        spray(m, rng, c, rx, ry, rz, int(cards * rx * rz / area), PINECARD, (card_size[0] * k, card_size[1] * k), yaw=1.1,
              flip=0.12)
    return pts


def build_pine_a(P):
    V3 = Vector
    pine(P,
         [(V3((-1.6, -0.3, 0)), V3((0.2, 2.8, 0)), V3((-0.2, 2.6, 0.15)), V3((1.4, 2.4, 0.1)), 6),
          (V3((-0.2, 2.6, 0.15)), V3((1.4, 2.4, 0.1)), V3((1.6, 4.2, -0.1)), V3((2.4, 0.9, -0.1)), 6),
          (V3((1.6, 4.2, -0.1)), V3((2.4, 0.9, -0.1)), V3((2.8, 4.9, 0.1)), V3((1.0, 0.2, 0)), 3)],
         (0.46, 0.13),
         [(V3((1.0, 5.7, 0.0)), 2.0, 0.4, 1.5), (V3((3.3, 4.7, 0.5)), 1.4, 0.32, 1.0), (V3((-1.9, 4.3, 0.3)), 1.15, 0.32, 0.9),
          (V3((0.3, 4.7, -1.4)), 1.25, 0.3, 0.85), (V3((1.0, 4.3, 1.45)), 1.05, 0.28, 0.8)],
         [(9, 0, 0.16), (14, 1, 0.12), (5, 2, 0.15), (8, 3, 0.11), (7, 4, 0.11)],
         stones=[(V3((-2.6, 0.0, 0.6)), 0.38), (V3((-0.6, -0.05, -0.9)), 0.42), (V3((-2.4, -0.05, -0.7)), 0.3), (V3((-0.9, -0.05, 0.9)), 0.3)])


def build_pine_b(P):
    V3 = Vector
    h = P.hard
    rng = P.rng
    # low rock chunk the roots spill over
    for i, (c, rx, rz, t) in enumerate([((-1.1, -0.15, 0.1), 0.9, 0.7, 0.55), ((-0.4, -0.15, -0.5), 0.6, 0.5, 0.45), ((-1.7, -0.1, 0.5), 0.45, 0.4, 0.3)]):
        slab(h, rng, c, rx, rz, t, SLATE, rot(0.1, rng.uniform(0, 6), 0.12), n=6, taper=0.85, chamfer_mat=LICHEN if i == 0 else None)
    pine(P,
         [(V3((-1.0, 0.25, 0)), V3((-0.6, 1.6, 0)), V3((-1.2, 1.9, 0.15)), V3((0.2, 1.4, 0)), 5),
          (V3((-1.2, 1.9, 0.15)), V3((0.2, 1.4, 0)), V3((0.4, 3.3, -0.1)), V3((1.6, 1.0, 0)), 5),
          (V3((0.4, 3.3, -0.1)), V3((1.6, 1.0, 0)), V3((-0.1, 4.8, 0.0)), V3((-0.6, 1.4, 0)), 5)],
         (0.36, 0.11),
         [(V3((0.0, 5.5, 0.0)), 1.6, 0.3, 1.3), (V3((1.9, 4.4, 0.4)), 1.15, 0.26, 0.9),
          (V3((3.25, 3.15, -0.25)), 0.95, 0.24, 0.75), (V3((-1.6, 4.65, -0.35)), 0.8, 0.24, 0.65)],
         [(14, 0, 0.13), (9, 1, 0.12), (8, 2, 0.1), (12, 3, 0.09)],
         root_count=5,
         stones=[(V3((0.6, -0.05, 0.7)), 0.3), (V3((1.0, -0.05, -0.6)), 0.25)])


def build_juniper_a(P):
    m, h, rng, sd = P.soft, P.hard, P.rng, P.seed
    V3 = Vector
    for c, s_ in [((-0.7, 0, -0.55), 0.26), ((0.6, 0, 0.6), 0.2), ((-1.55, 0, 0.45), 0.22)]:
        chunk(h, rng, c, s_, SLATE)
    tops = []
    # twisted silver limbs: a gnarled base that crawls low along the ground downwind, tips lifting at the end
    for k, (z0, z1, top, r, x1) in enumerate([(0.0, 0.15, 0.5, 0.2, 1.2), (0.15, -0.5, 0.36, 0.15, 0.95), (-0.1, 0.6, 0.3, 0.12, 0.7)]):
        st = V3((-1.6, -0.15, z0))
        mid = V3((-0.5, top, (z0 + z1) * 0.4))
        en = V3((x1, top * 0.9, z1))
        p1 = limb(m, st, mid, V3((0.6, 1.0, 0.1)), V3((1.4, 0.0, 0.1)), r, r * 0.75, DEAD, 6, 5, 0.28, sd + k, 1.2, cap=DEAD)
        p2 = limb(m, mid, en, V3((1.4, 0.0, 0.1)), V3((1.2, 0.35, 0)), r * 0.75, r * 0.35, DEAD, 5, 5, 0.28, sd + k + 5, 0.8, cap=DEAD)
        gnarl(m, p1 + p2[1:], [r] * (len(p1) + len(p2) - 1), DEAD, 1, 1.0, sd + k, rel=0.4, cap=DEAD)
        tops.append((p1, p2))
        deadwood(m, rng, en, (1, 0.6 + 0.1 * k, 0.15 * (k - 1)), 0.5, max(0.03, r * 0.35), 1, sides=4, lift=0.4)
    grass(m, rng, V3((-1.4, 0, -0.5)), 0.45, pick=DRY)
    grass(m, rng, V3((0.3, 0, 0.55)), 0.35, pick=DRY)
    grass(m, rng, V3((-0.9, 0, 0.6)), 0.4, pick=LONG)
    # foliage riding on the limbs: juniper cards hugging each limb in overlapping clumps, combed downwind over small
    # dark cores; the gnarled base and the dead tips stay bare
    spots = [(0, 0.36, 1.25), (0, 0.55, 1.35), (0, 0.74, 1.25), (0, 0.9, 0.9), (1, 0.45, 1.0), (1, 0.7, 1.05), (2, 0.5, 0.9),
             (2, 0.78, 0.85)]
    seats = []
    for i, (k, t, sc) in enumerate(spots):
        p1, p2 = tops[k]
        path = p1 + p2[1:]
        q = path[int(t * (len(path) - 1))]
        s_ = 0.3 * sc
        c = q + V3((0.0, s_ * 0.7, 0))
        seats.append((c, s_))
    for c, s_ in seats:
        k = s_ / 0.3
        spray(m, rng, c, s_ * 1.25, s_ * 0.6, s_ * 0.95, int(32 * k * k), JUNICARD, (0.42 * k, 0.66 * k), yaw=0.9,
              tilt=(0.15, 0.95), down=0.0, rim=0.85)


def build_juniper_b(P):
    m, h, rng, sd = P.soft, P.hard, P.rng, P.seed
    V3 = Vector
    # blocky lichen-spotted rock, strata near vertical
    R = rot(0, 0.3, 0.12)
    for c, rx, rz, t in [((-0.75, -0.1, 0.0), 0.8, 0.7, 1.15), ((-1.1, -0.1, 0.45), 0.5, 0.45, 0.8), ((-0.2, -0.1, -0.35), 0.5, 0.5, 0.75),
                         ((-1.3, -0.1, -0.35), 0.45, 0.4, 0.55)]:
        slab(h, rng, c, rx, rz, t, SLATE, R, n=6, taper=0.82, ch=0.22, chs=0.8, slope=rng.uniform(-0.25, 0.1))
    # trunk bursting sideways out of the rock top, then a fan of bleached deadwood
    st = V3((-0.65, 0.85, 0.05))
    p = limb(m, st, V3((0.15, 1.75, -0.05)), V3((0.9, 0.7, 0)), V3((0.5, 1.0, 0)), 0.2, 0.13, DEAD, 8, 7, 0.25, sd, 1.2, cap=DEAD)
    gnarl(m, p, [0.2] * len(p), DEAD, 2, 1.1, sd, rel=0.35, cap=DEAD)
    limb(m, st + V3((0.05, 0, 0.1)), V3((-0.25, 1.0, 0.45)), V3((0.6, 0.2, 0.4)), V3((0.2, -0.4, 0.2)), 0.1, 0.04, DEAD, 5, 4, cap=DEAD)
    deadwood(m, rng, p[-1], (0.55, 1, 0.1), 0.9, 0.11, 2, lift=0.2)
    deadwood(m, rng, p[-2], (1, 0.55, -0.25), 0.95, 0.09, 2, lift=0.25)
    deadwood(m, rng, p[-3], (0.9, 0.4, 0.4), 0.7, 0.07, 1, lift=0.3)
    # the one living clump, upwind, plus a scrap of turf on the rock
    clump(m, (-0.55, 1.05, 0.1), (0.45, 0.1, 0.35), MOSS, seed=sd, rough=0.3, rings=4, segs=7, tile=0.6, flat_base=0.3)
    grass(m, rng, V3((0.1, 0, 0.5)), 0.5, pick=DRY)
    grass(m, rng, V3((-1.5, 0, 0.0)), 0.4, pick=DRY)
    grass(m, rng, V3((-0.55, 1.08, 0.2)), 0.3, pick=SHORT, planes=2)
    clumps = [((-0.25, 2.0, 0.15), 0.6, 0.36, 0.5), ((0.2, 1.72, -0.35), 0.4, 0.26, 0.32)]
    for i, (c, rx, ry, rz) in enumerate(clumps):
        spray(m, rng, c, rx, ry * 0.85, rz, 60 if i == 0 else 22, JUNICARD, (0.38, 0.6) if i == 0 else (0.3, 0.48), yaw=0.9,
              tilt=(0.15, 0.95), down=0.0, rim=0.85)


# ---------- plants and ground ----------

def build_cushion(P):
    m, h, rng, sd = P.soft, P.hard, P.rng, P.seed
    # one tight dome with a high-frequency lumpy surface
    c, radii, rough, fq = Vector((0, 0.0, 0)), (0.47, 0.36, 0.42), 0.14, 3.2
    clump(m, c, radii, MOSS, seed=sd, rough=rough, rings=7, segs=14, tile=0.5, flat_base=0.15, register=False, freq=fq)
    off = Vector((sd, sd * 0.37, sd * 0.71))
    for i in range(22):
        th = rng.uniform(0, 2 * math.pi)
        phi = rng.uniform(0.3, 1.3)
        d = Vector((math.cos(phi) * math.cos(th), math.sin(phi), math.cos(phi) * math.sin(th)))
        k = 1 + rough * noise.noise(d * fq + off)
        q = c + Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k)) + d * 0.008
        star(m, q, rng.uniform(0.022, 0.032), "white" if i % 3 else "pink", points=0, rng=rng,
             tilt=Matrix.Rotation(-(math.pi / 2 - phi) * 0.8, 3, Vector((-math.sin(th), 0, math.cos(th)))))
    for k in range(5):
        a = rng.uniform(0, 6.3)
        chunk(h, rng, Vector((math.cos(a) * 0.48, 0.0, math.sin(a) * 0.42)), rng.uniform(0.05, 0.09), SLATE)
    # a fringe of short grass round the foot softens the dome's silhouette
    for k in range(11):
        a = 2 * math.pi * k / 11 + rng.uniform(-0.2, 0.2)
        grass(m, rng, (math.cos(a) * 0.44, 0, math.sin(a) * 0.4), rng.uniform(0.2, 0.3), pick=DRY if k % 3 == 0 else SHORT, planes=2)


def build_flowers(P):
    m, h, rng = P.soft, P.hard, P.rng
    V3 = Vector
    # leaf rosette
    for k in range(10):
        a = 2 * math.pi * k / 10 + rng.uniform(-0.2, 0.2)
        d = V3((math.cos(a), 0, math.sin(a)))
        L = rng.uniform(0.16, 0.26)
        pts = hermite(d * 0.02, d * 0.1 + V3((0, 0.18, 0)), d * L + V3((0, 0.05, 0)), d * 0.2 + V3((0, -0.06, 0)), 3)
        blade_strip(m, pts, 0.035, FLOWER, lambda u, v: atlas("leaf", u, v), taper=0.25)

    def stem(base, top, lean):
        pts = hermite(base, V3((0, 0.2, 0)), top, V3((lean, 0.15, 0)), 2)
        blade_strip(m, pts, 0.008, FLOWER, lambda u, v: atlas("leaf", u * 0.3 + 0.4, v), taper=0.6)

    # gentian bells (blue), cupped upward
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.4
        base = V3((math.cos(a) * 0.08 - 0.08, 0.0, math.sin(a) * 0.08))
        top = base + V3((rng.uniform(-0.04, 0.06), rng.uniform(0.13, 0.2), rng.uniform(-0.03, 0.03)))
        stem(base, top, 0.05)
        R = Matrix.Rotation(rng.uniform(-0.45, 0.45), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.35, 0.35), 3, "X")
        sides = 6
        rings = []
        for j, (y, r) in enumerate(((0.0, 0.008), (0.035, 0.026), (0.07, 0.04))):
            rings.append([(m.vert(top + R @ V3((math.cos(2 * math.pi * s / sides) * r * (1 + 0.25 * (s % 2) * (j == 2)), y,
                                                     math.sin(2 * math.pi * s / sides) * r))), atlas("blue", s / sides, j / 2)) for s in range(sides + 1)])
        for r0, r1 in zip(rings, rings[1:]):
            for s in range(sides):
                m.face((r0[s][0], r0[s + 1][0], r1[s + 1][0], r1[s][0]), (r0[s][1], r0[s + 1][1], r1[s + 1][1], r1[s][1]), FLOWER)
    # white star flowers
    for k in range(5):
        a = 2 * math.pi * k / 5 + 1.2
        base = V3((math.cos(a) * 0.1 + 0.08, 0.0, math.sin(a) * 0.1))
        top = base + V3((rng.uniform(-0.03, 0.06), rng.uniform(0.2, 0.3), rng.uniform(-0.03, 0.03)))
        stem(base, top, 0.06)
        star(m, top, rng.uniform(0.04, 0.055), "white", 6, 0.38, tilt=Matrix.Rotation(rng.uniform(-0.5, 0.5), 3, "Z"), rng=rng)
    # pink sprays
    for k in range(3):
        base = V3((rng.uniform(-0.05, 0.12), 0.0, rng.uniform(-0.12, 0.12)))
        top = base + V3((0.04, rng.uniform(0.33, 0.43), 0))
        stem(base, top, 0.1)
        for j in range(4):
            star(m, top + V3((rng.uniform(-0.04, 0.04), rng.uniform(-0.05, 0.01), rng.uniform(-0.04, 0.04))), 0.02, "pink", points=0, rng=rng)
    slab(h, rng, (0.25, -0.05, -0.18), 0.11, 0.09, 0.1, SLATE, rot(0.2, 0.5, 0.15), n=5, taper=0.8, tile=0.5)
    chunk(h, rng, V3((-0.28, 0, 0.15)), 0.05, SLATE)


def build_grass(P):
    m, h, rng = P.soft, P.hard, P.rng
    # one big wind-combed tussock of dry alpine grass streaming downwind, long seed-headed grass behind, low tufts in front
    for (x, z, hh, w, q) in ((-0.15, -0.05, 0.62, 1.15, DRY), (-0.3, 0.12, 0.5, 0.95, DRY), (0.0, -0.18, 0.55, 1.0, LONG),
                             (-0.35, -0.22, 0.42, 0.8, DRY), (0.25, 0.15, 0.36, 0.75, DRY), (-0.5, 0.25, 0.3, 0.6, LONG),
                             (0.35, -0.25, 0.28, 0.55, DRY)):
        grass(m, rng, (x, 0, z), hh, w, pick=q, planes=3, spread=1.3)
    chunk(h, rng, (-0.6, 0.0, 0.18), 0.14, SLATE, rot(0.1, 0.6, 0.15))


def ragged(rng, n, rx, rz, seed):
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 1 + 0.22 * noise.noise(Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, seed))) + (rng.uniform(-0.12, 0.05) if k % 2 else 0)
        out.append((math.cos(a) * rx * r, math.sin(a) * rz * r))
    return out


def turf_mat(m, rng, c, rx, rz, t, seed, top=TURF, edge=PATH, n=16, uvwin=(0.02, 0.38, 0.5, 0.42)):
    """Thin ragged turf mat: domed planar-UV top, torn soil edge."""
    c = Vector(c)
    out = ragged(rng, n, rx, rz, seed)
    u0, v0, us, vs = uvwin
    uv = lambda x, z: (u0 + us * (x + rx) / (2 * rx), v0 + vs * (z + rz) / (2 * rz))
    centre = m.vert(c + Vector((0, t, 0)))
    mid = [m.vert(c + Vector((x * 0.55, t * 0.85, z * 0.55))) for x, z in out]
    rim = [m.vert(c + Vector((x, t * 0.35, z))) for x, z in out]
    bot = [m.vert(c + Vector((x * 0.97, -0.03, z * 0.97))) for x, z in out]
    for k in range(n):
        k1 = (k + 1) % n
        x0, z0 = out[k]
        x1, z1 = out[k1]
        m.face((centre, mid[k1], mid[k]), (uv(0, 0), uv(x1 * 0.55, z1 * 0.55), uv(x0 * 0.55, z0 * 0.55)), top)
        m.face((mid[k], mid[k1], rim[k1], rim[k]), (uv(x0 * 0.55, z0 * 0.55), uv(x1 * 0.55, z1 * 0.55), uv(x1, z1), uv(x0, z0)), top)
        m.face((rim[k], rim[k1], bot[k1], bot[k]), None, edge, 0.6)
    m.face(bot, None, edge, 0.6)
    return out


def build_turf(P):
    m, rng, sd = P.soft, P.rng, P.seed
    out = turf_mat(m, rng, (0, 0, 0), 0.9, 0.7, 0.1, sd)
    for k in range(0, 16, 2):
        x, z = out[k]
        f = rng.uniform(0.55, 0.85)
        grass(m, rng, (x * f, 0.1 - 0.06 * f, z * f), rng.uniform(0.16, 0.26), pick=rng.choice((DRY, SHORT, DRY)), planes=2)
    for i in range(8):
        a, r = rng.uniform(0, 6.3), rng.uniform(0.1, 0.6)
        star(m, (math.cos(a) * r * 0.9, 0.1 - 0.06 * r, math.sin(a) * r * 0.7), 0.025, "white", points=0, rng=rng)


def build_scree(P):
    h, rng = P.hard, P.rng
    prism(h, (0, -0.05, 0), jag(rng, 8, 0.6, 0.48, 0.12), [(0, 1), (0.4, 0.55, (0.05, 0)), (0.7, 0.0, (0.08, 0.02))], SLATE, tile=0.8)
    for i in range(16):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.random() ** 0.7
        s = 0.07 + 0.13 * r + rng.uniform(-0.02, 0.03)
        y = 0.62 * (1 - r) * rng.uniform(0.75, 1.0) - s * 0.25
        chunk(h, rng, (math.cos(a) * r * 0.78, max(-0.02, y), math.sin(a) * r * 0.62), s, SLATE)


# ---------- rocks ----------

def strata(h, rng, base, R, layers, mat=SLATE, tile=1.0, chamfer_mat=None, seams=None):
    """Stacked plates in a local frame R: layers are (rx, rz, t, dx, dz). Returns the plate top centres (world)."""
    y = 0.0
    tops = []
    for i, (rx, rz, t, dx, dz) in enumerate(layers):
        c = Vector(base) + R @ Vector((dx, y, dz))
        slab(h, rng, c, rx, rz, t, mat if not isinstance(mat, list) else mat[i % len(mat)], R, n=rng.choice((5, 6)), taper=0.95,
             ch=0.32, chs=0.9, tile=tile, chamfer_mat=chamfer_mat)
        tops.append((c + R @ Vector((0, t, 0)), R @ Vector((rx, 0, 0))))
        y += t
        if seams and i in seams:
            c2 = Vector(base) + R @ Vector((dx * 0.5 + layers[i + 1][3] * 0.5, y - 0.02, dz))
            prism(h, c2, jag(rng, 7, max(rx, layers[i + 1][0]) * 1.03, max(rz, layers[i + 1][1]) * 1.03, 0.08),
                  [(0, 1), (0.07, 1.0)], ORE, R, tile)
            y += 0.05
    return tops


def build_boulder(P):
    h, m, rng = P.hard, P.soft, P.rng
    # one big tilted wedge with its strata stepping up the slope, a broken-off plate and a leaning slab
    R = rot(0.05, 0.25, 0.32)
    block(h, rng, (-0.1, -0.35, 0), 1.15, 0.78, 1.5, SLATE, R, n=6, slope=0.42, crown=0.55, lean=(0.12, 0), edge=None)
    for i, (dx, dy, rx, rz, t) in enumerate([(-0.25, 1.05, 0.7, 0.62, 0.3), (-0.55, 0.75, 0.5, 0.55, 0.3)]):
        c = Vector((-0.1, -0.35, 0)) + R @ Vector((dx, dy + 0.42 * dx, 0.05))
        slab(h, rng, c, rx, rz, t, SLATE, R @ rot(0, 0, 0.42), n=5, taper=0.9, ch=0.35, chs=0.8)
    block(h, rng, (-1.0, -0.2, 0.25), 0.42, 0.45, 0.85, SLATE, rot(0.1, 1.1, 0.35), n=5, slope=-0.4)
    for c, s_ in [((1.05, 0, 0.45), 0.2), ((-1.1, 0, -0.4), 0.17), ((0.5, 0, -0.72), 0.13)]:
        chunk(h, rng, c, s_, SLATE)
    tuft(m, rng, (-0.75, 0, 0.55), 5, 0.22, 0.35)
    tuft(m, rng, (0.2, 1.05, 0.5), 3, 0.14, 0.25, width=0.025)
    tuft(m, rng, (0.8, 0, -0.5), 4, 0.18, 0.3)


def build_lichen_rock(P):
    h, m, rng, sd = P.hard, P.soft, P.rng, P.seed
    out = jag(rng, 8, 0.68, 0.52, 0.12)
    prism(h, (0, -0.1, 0), out, [(0, 0.92), (0.2, 1.0), (0.55, 0.96, (0.04, 0)), (0.8, 0.78, (0.08, 0.02), 0.12), (0.92, 0.45, (0.1, 0.02), 0.12)],
          SLATE, rot(0.04, 0.3, 0.06), 1.6)
    block(h, rng, (0.5, -0.05, 0.25), 0.32, 0.3, 0.45, SLATE, rot(0.1, 0.9, -0.2), n=6, slope=-0.3)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rng.uniform(-0.4, 0.4)
        clump(m, (math.cos(a) * 0.62, 0.02, math.sin(a) * 0.48), (0.2, 0.1, 0.16), MOSS, seed=sd + k, rough=0.3, rings=3, segs=7,
              tile=0.4, flat_base=0.2)
    tuft(m, rng, (-0.55, 0, 0.3), 4, 0.15, 0.25, width=0.03)


def build_split(P):
    h, m, rng = P.hard, P.soft, P.rng
    for side, x, lean in ((-1, -0.45, 0.16), (1, 0.42, -0.12)):
        R = rot(rng.uniform(-0.08, 0.08), rng.uniform(-0.2, 0.2), lean)
        for j, (dx, rx, rz, t) in enumerate([(0.0, 0.36, 0.5, 1.95), (side * 0.3, 0.2, 0.42, 1.5), (side * 0.48, 0.13, 0.36, 1.0)]):
            c = Vector((x, -0.15, 0)) + R @ Vector((dx, 0, rng.uniform(-0.05, 0.05)))
            out = jag(rng, 6, rx, rz, 0.12)
            sl = -side * rng.uniform(0.6, 0.9)
            prism(h, c, out, [(0, 1), (t * 0.62, 0.95, (side * 0.03, 0)), (t * 0.92, 0.85, (side * 0.05, 0), sl),
                              (t, 0.6, (side * 0.06, 0), sl)], SLATE, R, 1.0)
    # moss and grass in the joint
    clump(m, (0.0, 0.05, 0.0), (0.18, 0.18, 0.4), MOSS, seed=P.seed, rough=0.3, rings=4, segs=7, tile=0.4, flat_base=0.3)
    clump(m, (0.0, 0.85, 0.15), (0.1, 0.12, 0.18), MOSS, seed=P.seed + 1, rough=0.3, rings=3, segs=6, tile=0.4)
    tuft(m, rng, (0, 0.1, 0.35), 4, 0.2, 0.3, width=0.025)
    for c, s in [((0.95, 0, 0.45), 0.14), ((-1.0, 0, -0.35), 0.16)]:
        chunk(h, rng, c, s, SLATE)


def build_ledge(P):
    h, m, rng, sd = P.hard, P.soft, P.rng, P.seed
    R0 = rot(0, 0.05, 0.03)
    for (c, rx, rz, t) in [((-0.3, -0.15, 0.05), 1.25, 0.85, 0.6), ((0.35, -0.15, -0.2), 0.9, 0.7, 0.55),
                           ((-0.35, 0.42, 0.0), 1.05, 0.75, 0.42), ((0.55, 0.4, 0.1), 0.75, 0.65, 0.45),
                           ((0.15, 0.82, -0.05), 1.15, 0.78, 0.36)]:
        slab(h, rng, c, rx, rz, t, SLATE, R0 @ rot(0, rng.uniform(-0.15, 0.15), rng.uniform(-0.04, 0.04)), n=7, taper=0.94, ch=0.3, chs=0.9)
    # the standable shelf: a flat plate stepping out downwind
    top = 1.17
    out = jag(rng, 7, 1.4, 0.92, 0.1)
    prism(h, (0.2, 1.06, -0.05), out, [(0, 0.96), (0.05, 1.0), (top - 1.06 - 0.04, 1.0), (top - 1.06, 0.95)], SLATE, tile=1.0)
    turf_mat(m, rng, (-0.15, top - 0.04, -0.15), 0.9, 0.6, 0.12, sd, n=14)
    tuft(m, rng, (0.8, top, 0.3), 4, 0.14, 0.25, width=0.025)
    tuft(m, rng, (1.25, 0.35, 0.6), 3, 0.15, 0.25, width=0.025)
    for i in range(6):
        star(m, (rng.uniform(-0.8, 0.5), top + 0.07, rng.uniform(-0.55, 0.3)), 0.03, "white" if i % 2 else "pink", points=0, rng=rng)
    chunk(h, rng, (1.4, 0, 0.7), 0.18, SLATE)
    chunk(h, rng, (-1.4, 0, -0.6), 0.15, SLATE)


def build_stair(P):
    h, m, rng = P.hard, P.soft, P.rng
    rise, run = 0.3, 0.44
    for k in range(6):
        x = 1.15 - k * run
        top = rise * (k + 1)
        out = jag(rng, 6, 0.34, 0.47, 0.08, phase=rng.uniform(-0.2, 0.2))
        c = Vector((x + 0.05, -0.1, rng.uniform(-0.04, 0.04)))
        R = rot(0, rng.uniform(-0.08, 0.08), 0)
        t = top + 0.1
        prism(h, c, out, [(0, 1.05), (t - 0.08, 1.0), (t, 0.88)], SLATE, R, 1.6)
        if k % 2 == 0:
            tuft(m, rng, (x + 0.3, top - rise + 0.02, rng.choice((-0.42, 0.42))), 3, 0.12, 0.22, width=0.03)
    # low cheeks: the back one rises with the flight, the front one stays low so the treads read
    for z, k in ((-0.62, 1.0), (0.62, 0.35)):
        for j, (x, ht, rx) in enumerate([(1.0, 0.5, 0.45), (0.15, 0.95, 0.5), (-0.75, 1.45, 0.45), (-1.25, 1.85, 0.3)]):
            block(h, rng, (x, -0.1, z), rx, 0.18, ht * k * rng.uniform(0.85, 1.0) + 0.15, SLATE,
                  rot(rng.uniform(-0.08, 0.08), rng.uniform(-0.2, 0.2), -0.08), n=6, slope=-0.3, crown=0.6, tile=1.6)
    chunk(h, rng, (1.45, 0, 0.3), 0.14, SLATE)
    tuft(m, rng, (1.45, 0, -0.4), 4, 0.15, 0.3, width=0.03)


def build_spire(P):
    h, m, rng = P.hard, P.soft, P.rng
    shard(h, rng, (0.0, -0.2, 0.0), 0.55, 0.45, 4.2, SLATE, rot(0.02, 0.3, -0.04), n=6, kink=0.12, mid=0.42, irr=0.12)
    for k, (a, r, L, s) in enumerate([(0.3, 0.45, 2.9, 0.38), (1.6, 0.5, 2.2, 0.34), (2.8, 0.5, 2.6, 0.33), (3.9, 0.55, 1.6, 0.3),
                                      (5.1, 0.45, 2.0, 0.32), (2.2, 0.7, 1.2, 0.25)]):
        d = Vector((math.cos(a), 0, math.sin(a)))
        R = Matrix.Rotation(0.12, 3, Vector((d.z, 0, -d.x))) @ rot(0, rng.uniform(0, 6), 0)
        shard(h, rng, d * r * 0.8 + Vector((0, -0.2, 0)), s, s * 0.8, L, SLATE, R, n=5, kink=0.15, mid=0.45)
    for k in range(6):
        a = rng.uniform(0, 6.3)
        chunk(h, rng, (math.cos(a) * 0.85, 0, math.sin(a) * 0.75), rng.uniform(0.1, 0.2), SLATE)
    tuft(m, rng, (-0.7, 0, 0.5), 4, 0.15, 0.3, width=0.025)
    clump(m, (0.65, 0.02, -0.55), (0.2, 0.08, 0.15), MOSS, seed=P.seed, rough=0.3, rings=3, segs=6, tile=0.4)


def build_cinder(P):
    h, rng = P.hard, P.rng
    block(h, rng, (-0.2, -0.3, 0), 0.95, 0.75, 1.9, CINDER, rot(0.05, 0.4, 0.18), n=6, slope=0.55, crown=0.5, lean=(0.15, 0), tile=2.5,
          edge=ORE)
    block(h, rng, (0.65, -0.2, 0.25), 0.55, 0.5, 1.05, CINDER, rot(-0.1, 1.2, -0.2), n=5, slope=-0.4, tile=2.5)
    block(h, rng, (-0.85, -0.2, -0.3), 0.45, 0.42, 0.75, CINDER, rot(0.1, 2.0, 0.25), n=5, slope=0.5, tile=2.5)
    for c, s_ in [((1.0, 0, -0.5), 0.15), ((-1.0, 0, 0.55), 0.12), ((0.3, 0, 0.75), 0.1)]:
        chunk(h, rng, c, s_, CINDER)


def build_ore(P):
    h, rng = P.hard, P.rng
    # dark cinder strata, alternate courses carrying the painted copper-gold veins, seam plates standing proud
    R = rot(0.05, -0.3, -0.38)
    base = Vector((0.2, -0.45, 0))
    y = 0.0
    for i, (rx, rz, t, dx) in enumerate([(1.1, 0.78, 0.55, 0.0), (1.02, 0.74, 0.5, -0.1), (0.9, 0.68, 0.45, -0.2), (0.66, 0.54, 0.4, -0.28)]):
        c = base + R @ Vector((dx, y, 0))
        if i < 3:
            block(h, rng, c, rx, rz, t, ORE if i % 2 == 0 else CINDER, R, n=6, slope=0.0, crown=0.9, tile=1.3)
        else:
            block(h, rng, c, rx, rz, t + 0.25, CINDER, R, n=6, slope=-0.4, crown=0.55, tile=1.3)
        y += t
        if i in (0, 2):
            prism(h, base + R @ Vector((dx - 0.05, y - 0.03, 0)), jag(rng, 7, rx * 1.04, rz * 1.04, 0.06), [(0, 1.0), (0.06, 1.0)], ORE, R, 0.7)
            y += 0.03
    block(h, rng, (-0.95, -0.2, 0.3), 0.45, 0.42, 0.8, CINDER, rot(0.1, 1.5, 0.3), n=5, slope=0.4, tile=1.6)
    for c, s_ in [((-1.0, 0, -0.5), 0.16), ((0.95, 0, 0.5), 0.13)]:
        chunk(h, rng, c, s_, CINDER)


# ---------- isle edges ----------

def edge_outline(rng, x0, x1, z0, z1, n=7, jagz=0.25):
    """Block outline spanning x0..x1 (clamped so lip ends tile), back at z0, ragged front around z1."""
    pts = [(x0, z0), (x1, z0)]
    for k in range(n):
        t = k / (n - 1)
        pts.append((x1 + (x0 - x1) * t + (rng.uniform(-0.15, 0.15) if 0 < k < n - 1 else 0), z1 + rng.uniform(-jagz, jagz)))
    return pts


def build_lip(P, wild=False):
    h, m, rng, sd = P.hard, P.soft, P.rng, P.seed
    W, H, D = 4.0, 5.0, 2.0
    rock = [CINDER, ORE, CINDER] if wild else [CLIFF]
    top_mat = DRYTURF if wild else TURF
    tile = 3.5
    # strata courses: each a row of blocks, front edges stepping in and out, the lowest pulled in over the points
    courses = [(H - 0.28, 1.3, 1.7), (H - 1.55, 1.2, 1.4), (H - 2.7, 1.0, 1.05)]
    for i, (ytop, t, front) in enumerate(courses):
        xs = [-W] + sorted(-W + 2.0 * (k + 1) + rng.uniform(-0.5, 0.5) for k in range(3)) + [W]
        for j in range(len(xs) - 1):
            x0, x1 = xs[j] - (0.08 if j else 0), xs[j + 1] + (0.08 if j < len(xs) - 2 else 0)
            fz = front + rng.uniform(-0.3, 0.25)
            out = edge_outline(rng, x0, x1, -D, fz, 4, 0.35 if not wild else 0.5)
            dy = rng.uniform(-0.08, 0.08)
            tilt = rot(rng.uniform(-0.04, 0.04), 0, rng.uniform(-0.05, 0.05) if 0 < j < len(xs) - 2 else 0)
            mat = rock[(i + j) % len(rock)]
            lean = rng.uniform(-0.1, 0.4)
            prism(h, (0, ytop - t + dy, 0), out, [(0, 0.86, (0, -0.1)), (0.3, 1.0), (t - 0.12, 1.0, (0, lean)), (t, 0.95, (0, lean))], mat, tilt, tile,
                  bands=[None, None, ORE if wild and (i + j) % 3 == 0 else None])
    # hanging points under the lowest courses
    count = 13 if wild else 11
    ybot = courses[-1][0] - courses[-1][1]
    for k in range(count):
        x = -W + 0.45 + (2 * W - 0.9) * (k + rng.uniform(0.15, 0.85)) / count
        z = rng.uniform(0.0, 0.7) if k % 2 else rng.uniform(-1.3, 0.0)
        y = ybot + 0.15 + (0 if k % 2 else rng.uniform(0.0, 0.5))
        L = y if k % 3 == 1 else y * rng.uniform(0.55, 0.85)
        shard(h, rng, (x, y, z), rng.uniform(0.45, 0.7) * (0.85 if wild else 1), rng.uniform(0.4, 0.6), L, rock[k % len(rock)],
              rot(rng.uniform(-0.12, 0.12), 0, rng.uniform(-0.15, 0.15)), n=5, down=True, kink=0.25 if wild else 0.15, tile=tile)
    # turf top, flush at y = H, overhanging the front edge in tongues
    out = [(-W, -D), (W, -D)] + [(W - 2 * W * k / 11, 1.85 + 0.25 * noise.noise(Vector((k * 0.7, sd, 0))) + rng.uniform(-0.1, 0.1))
                                 for k in range(12)]
    prism(m, (0, H - 0.3, 0), out, [(0, 0.98), (0.22, 1.0), (0.3, 0.995)], top_mat, None, 8.0, caps=(PATH, top_mat))
    for k in range(6):  # turf tongues draping over the edge
        x = -W + 0.7 + (2 * W - 1.4) * k / 5 + rng.uniform(-0.3, 0.3)
        z = 1.8 + rng.uniform(-0.05, 0.1)
        prism(m, (x, H - 0.55, z), jag(rng, 6, rng.uniform(0.35, 0.6), 0.2, 0.15), [(0, 0.55, (0, 0.05)), (0.2, 0.9, (0, 0.06)), (0.52, 1.0)],
              top_mat, None, 8.0, caps=(PATH, top_mat), bands=[PATH, top_mat])
    if wild:
        for k in range(3):
            chunk(h, rng, (rng.uniform(-3, 3), H + 0.1, rng.uniform(-1.4, 1.2)), rng.uniform(0.25, 0.4), CINDER)
        for k in range(9):
            grass(m, rng, (rng.uniform(-3.5, 3.5), H, rng.uniform(-1.5, 1.6)), rng.uniform(0.35, 0.55), pick=DRY)
    else:
        for k in range(26):
            star(m, (rng.uniform(-3.8, 3.8), H + 0.012, rng.uniform(-1.6, 1.75)), rng.uniform(0.04, 0.06), "pink" if k % 3 else "white",
                 points=0, rng=rng)
        for k in range(12):  # tufts thickest along the front edge, a few scattered behind
            z = rng.uniform(1.1, 1.75) if k < 8 else rng.uniform(-1.5, 1.0)
            grass(m, rng, (-3.6 + 7.2 * (k + rng.uniform(0.1, 0.9)) / 12, H, z), rng.uniform(0.35, 0.55), pick=rng.choice((DRY, SHORT, DRY)))
        for k in range(len(courses)):
            clump(m, (rng.uniform(-3.5, 3.5), courses[k][0] + 0.02, courses[k][2] - 0.05), (0.35, 0.1, 0.18), MOSS, seed=sd + 20 + k,
                   rough=0.3, rings=3, segs=6, tile=0.5)


def build_underside(P, wild=False):
    h, m, rng, sd = P.hard, P.soft, P.rng, P.seed
    H = 10.0
    rock = [CINDER, ORE, CINDER, CINDER] if wild else [UNDER, CLIFF, UNDER]
    tile = 3.5
    # stepped strata, each tier three overlapping blocks shrinking downwards
    tiers = [(H, 1.25, 4.0, 3.0), (H - 1.25, 1.2, 3.5, 2.6), (H - 2.45, 1.15, 2.9, 2.15), (H - 3.6, 1.1, 2.2, 1.7),
             (H - 4.7, 1.05, 1.5, 1.2)]
    tips = []
    for i, (ytop, t, rx, rz) in enumerate(tiers):
        for j, (ox, sx) in enumerate(((-0.45, 0.62), (0.4, 0.66), (0.0, 0.8))):
            if i == 0:
                out = jag(rng, 8, rx * 0.98, rz * 0.98, 0.06) if j == 2 else jag(rng, 7, rx * sx, rz * 0.9, 0.12)
            else:
                out = jag(rng, 7, rx * sx, rz * (0.85 + 0.1 * j), 0.16 if not wild else 0.24)
            c = (ox * rx, ytop - t, rng.uniform(-0.25, 0.25) * rz if i else 0)
            lv = [(0, 0.7), (t * 0.5, 0.94), (t - 0.08, 1.0), (t, 0.97 if i else 1.0)]
            prism(h, c, out, lv, rock[(i + j) % len(rock)], rot(rng.uniform(-0.04, 0.04), 0, rng.uniform(-0.05, 0.05)) if i else None, tile,
                  caps=(None, None), bands=[ORE if wild and (i + j) % 4 == 1 else None])
            if i:
                for k in range(3):
                    px, pz = out[rng.randrange(len(out))]
                    tips.append((Vector((c[0] + px * 0.7, c[1] + 0.15, c[2] + pz * 0.7)), rx * 0.18))
    # hanging points: one long central tip down to y = 0, and a fringe off every tier's underside
    shard(h, rng, (0, H - 5.75, 0), 1.0, 0.85, H - 5.75, rock[0], None, n=6, down=True, kink=0.1, tile=tile, mid=0.45)
    for k, (c, s) in enumerate(tips):
        L = min(c.y - 0.6, rng.uniform(1.0, 2.2) * (1.3 if wild else 1.0) + s)
        shard(h, rng, c, max(0.35, s * 1.2), max(0.3, s), L, rock[k % len(rock)], rot(rng.uniform(-0.1, 0.1), 0, rng.uniform(-0.12, 0.12)),
              n=5, down=True, kink=0.25 if wild else 0.15, tile=tile)
    if wild:
        for k in range(6):  # splinters
            a = rng.uniform(0, 6.3)
            shard(h, rng, (math.cos(a) * 2.2, rng.uniform(5.0, 7.5), math.sin(a) * 1.6), 0.2, 0.18, rng.uniform(0.8, 1.6), CINDER,
                  rot(rng.uniform(-0.3, 0.3), 0, rng.uniform(-0.3, 0.3)), n=4, down=True)
    else:
        # small juniper clinging sideways out of the face
        st = Vector((2.4, 6.9, 0.9))
        p = limb(m, st, st + Vector((1.0, 0.25, 0.3)), Vector((0.8, -0.3, 0.2)), Vector((0.8, 0.6, 0)), 0.12, 0.07, DEAD, 6, 5, 0.25, sd,
                 cap=DEAD)
        deadwood(m, rng, p[-1], (1, 0.3, 0.1), 0.5, 0.05, 1, sides=4)
        spray(m, rng, p[-2] + Vector((0.05, 0.25, 0.05)), 0.6, 0.28, 0.45, 26, JUNICARD, (0.45, 0.7), yaw=0.9,
              tilt=(0.15, 0.95), down=0.0, rim=0.85)
        for k in range(3):
            clump(m, (rng.uniform(-3, 3), tiers[k + 1][0] + 0.02, -tiers[k + 1][3] * 0.85), (0.4, 0.1, 0.2), MOSS, seed=sd + k,
                   rough=0.3, rings=3, segs=6, tile=0.5)


def build_spray(P):
    m, rng = P.soft, P.rng
    V3 = Vector
    top = V3((-1.0, 10.0, 0))
    mid = V3((-0.1, 5.4, 0.05))
    pts = hermite(top, V3((0.8, -1.0, 0)), mid, V3((0.9, -4.0, 0)), 8)
    sweep(m, pts, [0.55 + 0.45 * i / 8 for i in range(9)], [0.03 + 0.03 * i / 8 for i in range(9)], SPRAY, 5, 3.0)
    for k, (dx, dz, end_y, w) in enumerate([(1.2, 0.35, 0.8, 0.45), (2.0, -0.3, 2.0, 0.4), (0.5, -0.45, 2.8, 0.35)]):
        en = V3((mid.x + dx, end_y, dz))
        p2 = hermite(mid + V3((0, 0.3, 0)), V3((0.4, -2.0, dz * 0.5)), en, V3((dx * 0.9, -1.4, dz * 0.3)), 5)
        sweep(m, p2, [w + 0.2 * i / 5 for i in range(6)], [0.03] * 6, SPRAY, 4, 3.0)
        clump(m, en + V3((0.2, 0.05, 0)), (0.55 + 0.1 * k, 0.3, 0.35), SPRAY, seed=P.seed + k, rough=0.4, rings=3, segs=7, tile=2.0)
    for k in range(2):
        clump(m, V3((0.9 + 0.7 * k, 3.9 - 1.6 * k, 0.1)), (0.35, 0.2, 0.25), SPRAY, seed=P.seed + 9 + k, rough=0.4, rings=3, segs=6, tile=2.0)


# ---------- dispatch ----------

BUILDERS = {
    "cg-pine-a": build_pine_a, "cg-pine-b": build_pine_b, "cg-juniper-a": build_juniper_a, "cg-juniper-b": build_juniper_b,
    "cg-cushion-plant": build_cushion, "cg-alpine-flowers": build_flowers, "cg-grass-clump": build_grass,
    "cg-turf-patch": build_turf, "cg-scree-pile": build_scree, "cg-rock-lichen": build_lichen_rock,
    "cg-rock-boulder": build_boulder, "cg-rock-split": build_split, "cg-rock-ledge": build_ledge, "cg-rock-stair": build_stair,
    "cg-rock-spire": build_spire, "cg-rock-cinder": build_cinder, "cg-rock-ore": build_ore,
    "cg-lip": build_lip, "cg-lip-wild": lambda P: build_lip(P, True),
    "cg-underside": build_underside, "cg-underside-wild": lambda P: build_underside(P, True), "cg-fall-spray": build_spray,
}
LICHEN_RULE = {"cg-rock-lichen": (SLATE, LICHEN, 0.25, -0.2, 2.2), "cg-rock-boulder": (SLATE, LICHEN, 0.6, 0.15, 1.6),
               "cg-rock-split": (SLATE, LICHEN, 0.5, 0.1, 1.6), "cg-rock-ledge": (SLATE, LICHEN, 0.7, 0.25, 1.4),
               "cg-rock-stair": (SLATE, MOSS, 0.75, 0.2, 1.4), "cg-rock-spire": (SLATE, LICHEN, 0.4, 0.2, 1.5),
               "cg-juniper-b": (SLATE, LICHEN, 0.5, 0.2, 2.0), "cg-pine-b": (SLATE, LICHEN, 0.5, 0.0, 2.0),
               "cg-lip": (CLIFF, MOSS, 0.8, 0.2, 0.8), "cg-underside": (CLIFF, MOSS, 0.85, 0.3, 0.8)}
CATEGORY = {"tree": "tree", "plant": "bush", "ground": "ground", "rock": "rock", "lip": "lip", "underside": "underside", "water": "water"}


def build_piece(p, mats):
    P = Piece(p)
    BUILDERS[p["id"]](P)
    return P.done(mats, LICHEN_RULE.get(p["id"]))


def preview(path, objs, res=(1200, 750), low=False):
    """Close-up render with the sheets' look, framed on the projected bounds (the sheet camera crops tall pieces)."""
    bpy = B.bpy
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_cavity = True
    sc.display.shading.show_shadows = True
    sc.display.shading.show_specular_highlight = False  # the game's painterly materials are fully rough
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.9, 0.9, 0.88)
    lo, hi = B.bounds(objs)
    centre = (lo + hi) / 2
    d = Vector((1, -1.3, -0.35 if low else 1.1)).normalized()
    q = (-d).to_track_quat("-Z", "Y")
    right, up = q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0))
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    us = [p.dot(right) for p in pts]
    vs = [p.dot(up) for p in pts]
    centre = right * (max(us) + min(us)) / 2 + up * (max(vs) + min(vs)) / 2 + d * centre.dot(d)
    w, h = max(us) - min(us), max(vs) - min(vs)
    print("[frame]", round(w, 2), round(h, 2))
    span = (hi - lo).length
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(w, h * res[0] / res[1]) * 1.06
    sc.collection.objects.link(cam)
    cam.location = centre + d * span * 2
    cam.rotation_euler = q.to_euler()
    cam.data.clip_end = span * 6
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(_args) > 1 and _args[1] == "preview":
    out_dir = _args[3] if len(_args) > 3 else os.path.join(B.KIT_DIR, "preview")
    os.makedirs(out_dir, exist_ok=True)
    ids = [p["id"] for p in B.kit["pieces"]] if _args[2] == "all" else _args[2].split(",")
    for pid in ids:
        mats = K.reset()
        ob = build_piece(B.PIECES[pid], mats)
        print(f"[preview] {pid}: {K.tris(ob)} tris (manifest {B.PIECES[pid]['tris']}), fit {FITS.get(pid)}")
        objs = [ob] + ([B.figure(Vector((-B.PIECES[pid]["size"][0] / 2 - 0.8, 0, 0)))] if B.PIECES[pid]["size"][1] > 1.5 else [])
        B.bpy.context.view_layer.update()
        low = len(_args) > 4 and _args[4] == "low"
        preview(os.path.join(out_dir, f"{pid}{'-low' if low else ''}.png"), objs, low=low)
else:
    K.build_all(build_piece, extras=[(p["id"], CATEGORY[p["family"]]) for p in B.kit["pieces"]], biome="crag")
    print("[crag] fit scales (x, y, z):", FITS)
