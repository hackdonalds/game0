# Meadow nature kit: birches, blossoming orchard trees, landmark oaks, wildflowers, hedgerows, a standing stone,
# dry-stone walls, limestone rocks, the isle lip and underside, and the sky-pond, stream and waterfall, built from
# art/models/nature/meadow/kit.json on the painted swatches in art/textures/biomes/meadow (cropped from the
# biome's nature and isle-portrait sheets).
# The generic generators here (lobed clumps, crowns, limbs, hand-cut stones, dry-stone runs, ivy, flowers, lips,
# undersides, ponds) are also used by nature-garden.py, which loads this file as a module; the build only runs
# when this file is the script Blender was started with.
# Usage: Blender --background --python scripts/kit/nature-meadow.py -- meadow [--only id,id] [--close dir]
import math, os, random, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
import naturelib as N  # noqa: E402
from kitlib import Mesh, hermite, tube  # noqa: E402

UP = Vector((0, 1, 0))


# ---------- generic generators (shared with nature-garden.py) ----------

def lobed(m, c, radii, mat, seed=0.0, lobes=6, depth=0.3, rough=0.12, rings=6, segs=10, tile=1.5, flat=0.6, up=0.35):
    """Clumped foliage mass: an ellipsoid whose surface swells into `lobes` rounded sub-clumps with creases
    between them (the max over lobe directions), plus soft noise. `flat` squashes the underside."""
    rng = random.Random(seed)
    c = Vector(c)
    rx, ry, rz = radii
    dirs = [Vector((rng.gauss(0, 1), rng.gauss(0, 1) + up, rng.gauss(0, 1))).normalized() for _ in range(lobes)]
    off = Vector((seed * 1.3, seed * 0.7, seed * 0.37))

    def point(phi, th):
        d = Vector((math.cos(phi) * math.cos(th), math.sin(phi), math.cos(phi) * math.sin(th)))
        mx = max(d.dot(q) for q in dirs)
        k = 1 - depth * (1 - ((mx + 1) / 2) ** 4) + rough * noise.noise(d * 3.2 + off)
        return c + Vector((d.x * rx * k, d.y * ry * k * (flat if d.y < 0 else 1), d.z * rz * k))

    rows = []
    for i in range(1, rings):
        phi = -math.pi / 2 + math.pi * i / rings
        rows.append([m.vert(point(phi, 2 * math.pi * j / segs + i * 0.3)) for j in range(segs)])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(segs):
            j1 = (j + 1) % segs
            m.face((r0[j], r0[j1], r1[j1], r1[j]), None, mat, tile)
    bottom, top = m.vert(point(-math.pi / 2, 0)), m.vert(point(math.pi / 2, 0))
    for j in range(segs):
        j1 = (j + 1) % segs
        m.face((bottom, rows[0][j1], rows[0][j]), None, mat, tile)
        m.face((rows[-1][j], rows[-1][j1], top), None, mat, tile)


def crown(m, centre, semi, mats, seed, n, r, rings=6, segs=10, shell=0.72, lobes=5, depth=0.32, squash=0.8,
          tile=1.5, filler=True, low=-0.35):
    """A tree crown of `n` overlapping lobed clumps spread over the upper part of an ellipsoid (semi-axes `semi`),
    lighter materials on top and darker ones underneath, with a dark filler mass so no light shows through.
    Returns the clump centres (for limbs to reach into)."""
    rng = random.Random(seed)
    centre = Vector(centre)
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        yy = 1 - (i + 0.5) / n * (1 - low)
        rad = math.sqrt(max(0.0, 1 - yy * yy))
        th = golden * i + rng.uniform(-0.35, 0.35) + seed
        d = Vector((math.cos(th) * rad, yy, math.sin(th) * rad))
        s = shell * rng.uniform(0.85, 1.08)
        p = centre + Vector((d.x * semi[0] * s, d.y * semi[1] * s, d.z * semi[2] * s))
        rr = r * rng.uniform(0.8, 1.2)
        t = (yy - low) / (1 - low) + rng.uniform(-0.15, 0.15)
        mi = mats[max(0, min(len(mats) - 1, int((1 - t) * len(mats))))]
        lobed(m, p, (rr, rr * squash, rr), mi, seed=seed + i * 1.7, lobes=lobes, depth=depth, rings=rings, segs=segs, tile=tile)
        pts.append(p)
    if filler:
        lobed(m, centre + Vector((0, -semi[1] * 0.1, 0)), (semi[0] * 0.78, semi[1] * 0.7, semi[2] * 0.78), mats[-1],
              seed=seed + 99, lobes=7, depth=0.25, rings=rings, segs=segs + 2, tile=tile * 1.5)
    return pts


def masses(m, centre, semi, mats, seed, n_mass, per, r, rings=6, segs=10, shell=0.62, lobes=7, depth=0.38, squash=0.75,
           tile=1.5, spread=0.9, low=-0.3, filler=None, top_bias=0.0):
    """A crown of clumped leaf masses: `n_mass` masses spread over the upper ellipsoid `semi`, each built from
    `per` tightly packed lobed clumps on a flat-bottomed dome, light materials on the tops and the shade
    material underneath. Returns the mass centres (limb targets)."""
    rng = random.Random(seed)
    centre = Vector(centre)
    golden = math.pi * (3 - math.sqrt(5))
    out = []
    for i in range(n_mass):
        yy = 1 - (i + 0.5) / n_mass * (1 - low) if n_mass > 1 else 1.0
        rad = math.sqrt(max(0.0, 1 - yy * yy))
        th = golden * i * 1.0 + seed + rng.uniform(-0.3, 0.3)
        s = shell * rng.uniform(0.85, 1.1)
        mc = centre + Vector((math.cos(th) * rad * semi[0] * s, yy * semi[1] * s, math.sin(th) * rad * semi[2] * s))
        out.append(mc)
        R = r * spread * rng.uniform(0.85, 1.15)
        for k in range(per):
            if k == 0:
                off = Vector((0, R * 0.15, 0))
            else:
                a = 2 * math.pi * k / (per - 1) + rng.uniform(-0.4, 0.4)
                off = Vector((math.cos(a) * R * 0.75, rng.uniform(-0.35, 0.05) * R, math.sin(a) * R * 0.75))
            rr = r * (1.15 if k == 0 else rng.uniform(0.7, 0.95))
            p = mc + off
            t = (p.y - (centre.y - semi[1])) / max(0.2, 2 * semi[1]) + top_bias + (0.25 if k == 0 else -0.05) + rng.uniform(-0.12, 0.12)
            mi = mats[max(0, min(len(mats) - 1, int((1 - t) * len(mats))))]
            lobed(m, p, (rr, rr * squash, rr), mi, seed=seed + i * 7.1 + k * 1.3, lobes=lobes, depth=depth, rings=rings, segs=segs,
                  tile=tile, flat=0.45)
    if filler is not None:
        lobed(m, centre + Vector((0, semi[1] * 0.05, 0)), (semi[0] * 0.6, semi[1] * 0.55, semi[2] * 0.6), filler, seed=seed + 99,
              lobes=7, depth=0.25, rings=rings, segs=segs + 2, tile=tile * 1.5, flat=0.5)
    return out


def limb(m, p0, d0, p1, d1, r0, r1, mat, sides=8, n=8, seed=0.0, rough=0.15, twist=0.5, caps=(False, True), k=0.6):
    """A tapering branch on a Hermite curve from p0 (leaving along d0) to p1 (arriving along d1)."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    pts = hermite(p0, Vector(d0).normalized() * L * k, p1, Vector(d1).normalized() * L * k, n)
    tube(m, pts, [r0 + (r1 - r0) * (i / n) ** 0.8 for i in range(n + 1)], mat, sides, twist=twist, rough=rough, seed=seed, caps=caps)
    return pts


def trunk(m, base, top, lean_dir, r0, r1, mat, sides=10, n=10, seed=0.0, flare=1.4, rough=0.18, twist=0.8, wiggle=0.0):
    """Main trunk from just below the ground up to `top`, flaring at the foot; `wiggle` gives a gnarled S-curve."""
    base, top = Vector(base), Vector(top)
    L = (top - base).length
    pts = hermite(base, Vector((0, 1, 0)) * L * 0.6, top, Vector(lean_dir).normalized() * L * 0.6, n)
    if wiggle:
        side = Vector((1, 0, 0.3)).normalized()
        pts = [p + side * wiggle * math.sin(i / n * math.pi * 1.6 + seed) * math.sin(i / n * math.pi) for i, p in enumerate(pts)]
    radii = [r1 + (r0 - r1) * (1 - i / n) ** 1.3 for i in range(n + 1)]
    radii[0] *= flare
    radii[1] *= 1 + (flare - 1) * 0.4
    tube(m, pts, radii, mat, sides, twist=twist, rough=rough, seed=seed, caps=(False, True))
    return pts


def roots(m, centre, r, count, reach, mat, seed=0.0, sides=6, rise=0.5, thick=0.45):
    """Buttress roots spreading from the trunk foot into the ground."""
    rng = random.Random(seed)
    c = Vector(centre)
    for k in range(count):
        a = 2 * math.pi * k / count + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), 0, math.sin(a)))
        start = c + d * r * 0.55 + Vector((0, rise, 0))
        end = c + d * reach * rng.uniform(0.75, 1.1) + Vector((0, -0.25, 0))
        pts = hermite(start, d * reach * 0.5 + Vector((0, -rise * 1.5, 0)), end, d * reach * 0.6 + Vector((0, -0.2, 0)), 7)
        tube(m, pts, [r * thick * (1 - 0.85 * i / 7) + 0.03 for i in range(8)], mat, sides, rough=0.25, seed=seed + k)


def stone(m, lo, hi, mat, rng, xf=None, pillow=0.035, taper=0.03, tile=0.9, bottom=False, back=True):
    """Hand-cut block between local corners lo/hi (u along, v up, w across), slightly tapered, with pillowed
    front, back and top faces (a raised centre vertex) and its own random texture offset.
    `xf(u, v, w)` maps local to piece coordinates."""
    xf = xf or (lambda u, v, w: Vector((u, v, w)))
    (u0, v0, w0), (u1, v1, w1) = lo, hi
    j = lambda: rng.uniform(-1, 1) * taper
    c = {}
    for i in (0, 1):
        for jj in (0, 1):
            for k in (0, 1):
                tu = (taper if i == 0 else -taper) * jj
                tw = (taper if k == 0 else -taper) * jj
                c[i, jj, k] = (u1 if i else u0) + tu + j() * 0.5, (v1 if jj else v0) + j() * 0.6, (w1 if k else w0) + tw + j() * 0.5
    ou, ov = rng.random() * 4, rng.random() * 4
    verts = {key: m.vert(xf(*p)) for key, p in c.items()}

    def uvp(p, axes):
        return (p[axes[0]] / tile + ou, p[axes[1]] / tile + ov)

    def quad(keys, axes, bulge):
        ps = [c[k] for k in keys]
        if bulge and pillow > 0:
            cen = tuple(sum(p[i] for p in ps) / 4 for i in range(3))
            cen = tuple(cen[i] + bulge[i] * pillow * (0.6 + 0.8 * rng.random()) for i in range(3))
            cv = m.vert(xf(*cen))
            for a in range(4):
                b = (a + 1) % 4
                m.face((verts[keys[a]], verts[keys[b]], cv), (uvp(ps[a], axes), uvp(ps[b], axes), uvp(cen, axes)), mat)
        else:
            m.face([verts[k] for k in keys], [uvp(p, axes) for p in ps], mat)

    quad([(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)], (0, 2), (0, 1, 0))      # top
    if back:
        quad([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], (0, 1), (0, 0, 1))  # w1 face (the far side; skipped on retaining walls)
    quad([(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)], (0, 1), (0, 0, -1))      # w0 face
    quad([(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], (2, 1), None)           # u0 end
    quad([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], (2, 1), None)           # u1 end
    if bottom:
        quad([(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], (0, 2), None)


def frame_xf(origin, u_dir, w_dir):
    o, ud, wd = Vector(origin), Vector(u_dir), Vector(w_dir)
    return lambda u, v, w: o + ud * u + UP * v + wd * w


def drystone(m, rng, length, height, depth, courses, mat, xf, core=None, gap=0.03, lmin=0.3, lmax=0.6, batter=0.06,
             start_v=0.0, ragged=0.0, pillow=0.035, tile=0.9, back=True):
    """A dry-stone run along local u (0..length), courses of irregular hand-cut blocks with staggered joints,
    narrowing slightly towards the top (batter). Ends stay flush at u = 0 and u = length so runs butt together.
    `core` fills the joints behind with a dark material. `ragged` drops random top-course stones (broken walls)."""
    ch = (height - start_v) / courses
    for ci in range(courses):
        v0 = start_v + ci * ch
        v1 = v0 + ch * rng.uniform(0.92, 1.0)
        inset = batter * (ci / courses)
        u = 0.0
        first = True
        while u < length - 1e-3:
            ln = rng.uniform(lmin, lmax) * (0.55 if (first and ci % 2) else 1)
            first = False
            u1 = min(length, u + ln)
            if length - u1 < lmin * 0.6:
                u1 = length
            if not (ragged and ci == courses - 1 and rng.random() < ragged):
                g0 = gap / 2 if u > 1e-3 else 0.0
                g1 = gap / 2 if u1 < length - 1e-3 else 0.0
                out = rng.uniform(-0.03, 0.015)
                stone(m, (u + g0, v0 + gap / 2, inset + out), (u1 - g1, v1 - gap / 2, depth - inset - out * 0.5), mat, rng, xf,
                      pillow=pillow, tile=tile, back=back)
            u = u1
    if core is not None:
        stone(m, (0.02, 0, 0.08), (length - 0.02, height * 0.92 - ch * 0.4, depth - 0.08), core, rng, xf, pillow=0, taper=0)


def head(m, c, r, mat, seed=0.0, petals=5, cup=0.25):
    """A flower head: a small petal star (one n-gon fan) tipped to face up and slightly out."""
    rng = random.Random(seed)
    c = Vector(c)
    tilt = Vector((rng.uniform(-0.35, 0.35), 1, rng.uniform(-0.35, 0.35))).normalized()
    a = tilt.orthogonal().normalized()
    b = tilt.cross(a)
    n = petals * 2
    ring = []
    for k in range(n):
        t = 2 * math.pi * k / n
        rr = r if k % 2 == 0 else r * 0.55
        ring.append(m.vert(c + (a * math.cos(t) + b * math.sin(t)) * rr + tilt * (cup * r if k % 2 == 0 else 0)))
    m.face(ring, [(0.5 + 0.5 * math.cos(2 * math.pi * k / n), 0.5 + 0.5 * math.sin(2 * math.pi * k / n)) for k in range(n)], mat)


def spike(m, base, h, r, mat, stem=None, seed=0.0, sides=5, bend=0.15):
    """A lupin or lavender spike: a short stem then a tapering, slightly bent flower cone."""
    rng = random.Random(seed)
    base = Vector(base)
    lean = Vector((rng.uniform(-bend, bend), 1, rng.uniform(-bend, bend))).normalized()
    top = base + lean * h
    pts = hermite(base, UP * h * 0.6, top, lean * h * 0.6, 4)
    radii = [r * 0.25, r * 0.9, r, r * 0.7, r * 0.12]
    tube(m, pts, radii, mat, sides, caps=(False, False), tile=h)


def tuft(m, centre, radius, height, mat, seed=0.0, count=10, width=0.05, lean=0.6, tip=None):
    if mat == GRASS:  # meadow grass is a painted card tuft now; other blade crops (leeks, straw) stay geometry
        grass(m, centre, radius, height, seed=seed, count=max(1, round(count / 7)))
        return
    N.blades(m, centre, radius, height, mat, seed=seed, count=count, width=width, lean=lean, tip_mat=tip)


def grass(m, centre, radius, height, seed=0.0, count=1, quad=None, planes=3):
    """`count` crossed-card grass tufts scattered within `radius` of `centre`, painted blades about `height` tall.
    The sprite's blades fill roughly the lower two thirds of its quadrant above a small root margin, so cards are
    taller than the grass they show and sink a little into the ground."""
    rng = random.Random(seed)
    c = Vector(centre)
    for k in range(count):
        a, r = rng.uniform(0, 2 * math.pi), (math.sqrt(rng.random()) * radius * 0.6 if count > 1 else 0.0)
        hh = height * rng.uniform(0.85, 1.15)
        ch = hh / 0.62
        q = quad if quad is not None else (3 if height > 0.45 else 2)
        cw = max(ch * 1.05, radius * 1.6 if count == 1 else ch)
        N.card_tuft(m, c + Vector((math.cos(a) * r, -ch * 0.14, math.sin(a) * r)), ch, cw, CARDS["grass"], seed=int(seed * 100) + k,
                    planes=planes, pick=q, lean=rng.uniform(-0.12, 0.12))


# Colour grade for the shared sprite atlases: (red multiplier on yellow-green pixels, blue lift on them, saturation).
# The painted broadleaf, birch, grass and ivy sprites lean lemon-yellow; the meadow concept is a softer sap green.
GRADE = {"broadleaf-green.png": (0.88, 0.03, 0.92), "birch.png": (0.82, 0.04, 0.88), "grass.png": (0.88, 0.03, 0.92),
         "ivy-moss.png": (0.86, 0.03, 0.9), "blossom.png": (0.9, 0.02, 1.0), "elder-blossom.png": (0.9, 0.02, 0.97)}


def grade_cards(mats):
    """Swap each card material's sprite for a colour-graded copy (built once per Blender session): yellow-green
    pixels lose some red and gain a little blue, then everything is slightly desaturated. Pinks and whites keep
    their colour. The graded image is packed into the exported GLB."""
    import bpy
    import numpy as np
    for mat in mats:
        if "Card" not in mat.name or not mat.use_nodes:
            continue
        node = next((n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
        if node is None:
            continue
        src = node.image
        key = os.path.basename(src.filepath)
        if key not in GRADE:
            continue
        name = "graded-" + key
        img = bpy.data.images.get(name)
        if img is None:
            rmul, blift, sat = GRADE[key]
            w, h = src.size
            px = np.empty(w * h * 4, dtype=np.float32)
            src.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            r, g, b = px[:, 0], px[:, 1], px[:, 2]
            yellow = np.clip((np.minimum(r, g) - b) * 3.0, 0, 1) * (g >= r * 0.8)
            r2 = r * (1 - (1 - rmul) * yellow)
            b2 = b + blift * yellow
            lum = 0.3 * r2 + 0.59 * g + 0.11 * b2
            out = np.stack([lum + (r2 - lum) * sat, lum + (g - lum) * sat, lum + (b2 - lum) * sat], axis=1)
            px[:, :3] = np.clip(out, 0, 1)
            img = bpy.data.images.new(name, w, h, alpha=True)
            img.pixels.foreach_set(px.ravel())
            img.pack()
        node.image = img


def crown_points(centre, semi, n, seed, shell=0.72, low=-0.6):
    """Lobe centres spread over the upper part of an ellipsoid (a golden spiral from the top down to `low`)."""
    rng = random.Random(seed)
    centre = Vector(centre)
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        yy = 1 - (i + 0.5) / n * (1 - low) if n > 1 else 1.0
        rad = math.sqrt(max(0.0, 1 - yy * yy))
        th = golden * i + seed + rng.uniform(-0.3, 0.3)
        s = shell * rng.uniform(0.85, 1.1)
        pts.append(centre + Vector((math.cos(th) * rad * semi[0] * s, yy * semi[1] * s, math.sin(th) * rad * semi[2] * s)))
    return pts


def leaf_crown(m, lobes, mats, seed, density=20.0, size=(0.9, 1.4), centre=None, up_bias=0.35, shade=None, shade_low=0.45,
               fill=0.0, deep_size=0.8, total=None):
    """Leafy crown of alpha-cutout cards (naturelib.card_crown with sprite choice): each lobe is (centre, (rx, ry, rz));
    cards gather near each lobe's surface facing outwards, normals point away from `centre` so the crown shades as one
    soft mass. `mats` is [(material, weight, quadrant weights or None)]; `shade` = (material, quadrant weights) takes
    over cards in the lower `shade_low` of the crown, more of them further down. `fill` adds that fraction of extra
    cards deep inside the lobes so no sky shows through the middle. `total` (cards before fill) overrides `density`,
    shared out by lobe area. Returns the card count."""
    rng = random.Random(seed)
    lobes = [(Vector(c), r) for c, r in lobes]
    cc = Vector(centre) if centre is not None else sum((c for c, _ in lobes), Vector()) / len(lobes)
    span = max(max(r) for _, r in lobes)
    ylo = min(c.y - r[1] for c, r in lobes)
    yhi = max(c.y + r[1] for c, r in lobes)
    weights = [w for _, w, _ in mats]
    areas = [4 * math.pi * (rx * ry + rx * rz + ry * rz) / 3 for _, (rx, ry, rz) in lobes]
    count = 0
    for (c, (rx, ry, rz)), area in zip(lobes, areas):
        n = max(4, round(total * area / sum(areas))) if total else max(6, int(area * density / 10))
        for i in range(n + int(n * fill)):
            deep = i >= n
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1) * 0.8 + 0.15, rng.gauss(0, 1))).normalized()
            depth = rng.uniform(0.55, 1.0) ** 0.5 if not deep else rng.uniform(0.2, 0.6)
            p = c + Vector((d.x * rx, d.y * ry, d.z * rz)) * depth
            t = (p.y - ylo) / max(1e-3, yhi - ylo)
            if shade and ((deep and t < shade_low + 0.25) or rng.random() < max(0.0, (shade_low - t) / shade_low) * 0.9):
                mat, qw = shade
            else:
                mat, _, qw = rng.choices(mats, weights=weights)[0]
            out = p - cc
            out = (out / span + Vector((0, up_bias, 0))).normalized() if out.length > 1e-4 else Vector((0, 1, 0))
            # mostly random facing (outward-facing cards turn edge-on along the silhouette and smear), kept
            # fairly upright so few cards lie flat and streak when seen from above
            face = d * 0.4 + Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized() * 0.8
            face = Vector((face.x, face.y * 0.55, face.z)).normalized()
            right = face.cross(Vector((0, 1, 0)))
            right = right.normalized() if right.length > 1e-3 else Vector((1, 0, 0))
            up = right.cross(face).normalized()
            roll = rng.uniform(-0.6, 0.6)
            right, up = right * math.cos(roll) + up * math.sin(roll), up * math.cos(roll) - right * math.sin(roll)
            sz = rng.uniform(*size) * (deep_size if deep else 1.0)
            q = rng.choices(range(4), weights=qw)[0] if qw else None
            N._card(m, p, right, up, sz, sz, mat, N._quadrant(rng, 2, q), normal=out)
            count += 1
    return count


def ivy(m, top, length, mat, seed=0.0, width=0.35, sides=5, n=6, outward=Vector((0, 0, 1))):
    """A hanging ivy curtain: a flattened, lumpy, tapering strand falling from `top`, bulging out a little."""
    rng = random.Random(seed)
    top = Vector(top)
    out = Vector(outward)
    end = top + Vector((rng.uniform(-0.3, 0.3), -length, 0)) + out * rng.uniform(0.0, 0.25)
    pts = hermite(top, out * length * 0.4 + Vector((0, -length * 0.2, 0)), end, Vector((0, -length, 0)), n)
    radii = [width * (1 - 0.75 * i / n) * (1 + 0.25 * math.sin(i * 2.3 + seed)) for i in range(n + 1)]
    tube(m, pts, radii, mat, sides, rough=0.35, seed=seed, flat=0.45, tile=0.8)


def pebble(m, c, size, mat, seed=0.0, rings=4, segs=6, sink=0.3):
    w, h, d = size
    N.blob(m, (c[0], c[1] + h * (0.5 - sink), c[2]), (w / 2, h / 2, d / 2), mat, seed=seed, rough=0.3, rings=rings, segs=segs, tile=1.0, flat_base=0.6)


def ring_band(m, outline, ys, insets, mat, tile=2.0, planar=False, v_span=None, close=True):
    """Lofts closed rings around an outline (list of (x, z)): one ring per (y, inset) where inset scales the
    outline towards its centroid. UVs: u along the perimeter, v by height (or planar x/z)."""
    cx = sum(p[0] for p in outline) / len(outline)
    cz = sum(p[1] for p in outline) / len(outline)
    per = [0.0]
    for a, b in zip(outline, outline[1:] + outline[:1]):
        per.append(per[-1] + math.dist(a, b))
    rows = []
    for y, s in zip(ys, insets):
        row = []
        for k, (x, z) in enumerate(outline + outline[:1]):
            p = Vector((cx + (x - cx) * s, y, cz + (z - cz) * s))
            uv = (p.x / tile, p.z / tile) if planar else (per[k] / tile, (y - ys[-1]) / (v_span or tile))
            row.append((m.vert(p), uv))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(len(outline)):
            m.face((r0[k][0], r0[k + 1][0], r1[k + 1][0], r1[k][0]), (r0[k][1], r0[k + 1][1], r1[k + 1][1], r1[k][1]), mat)
    return rows


def oval(w, d, n, seed=0.0, rough=0.08):
    return [((w / 2) * math.cos(a) * (1 + rough * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, seed)))),
             (d / 2) * math.sin(a) * (1 + rough * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, seed + 5)))))
            for a in (2 * math.pi * k / n for k in range(n))]


def lip_edge(m, width, depth, height, turf, cliff, seed=0.0, overhang=0.5, segs=16, drops=6, tile=None):
    """Isle edge along X (centred), turf top at y = height meeting the ground at the back (-Z), the outer face
    (+Z) bulging then dropping to y = 0. Cliff UVs run u along the edge and v down the face, so the painted
    swatch's grassy top band sits under the turf. Returns the top-edge points (for turf rolls and ivy)."""
    tile = tile or height
    rows = []
    for i in range(drops + 1):
        t = i / drops
        row = []
        for j in range(segs + 1):
            x = -width / 2 + width * j / segs
            n = noise.noise(Vector((x * 0.6, t * 3, seed)))
            z = depth / 2 + overhang * (1 - t) ** 0.5 + n * 0.4 - t * overhang * 0.9
            y = height * (1 - t) + n * 0.2 * t * (1 - t)
            if i == drops:
                y = 0.0
            row.append((m.vert((x, y, z)), (x / tile, (height - (height - y) * 0.95) / tile)))
        rows.append(row)
    for i in range(drops):
        for j in range(segs):
            a, b, c, d = rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]
            m.face((a[0], b[0], c[0], d[0]), (a[1], b[1], c[1], d[1]), cliff)
    back = [m.vert((-width / 2 + width * j / segs, height, -depth / 2)) for j in range(segs + 1)]
    for j in range(segs):
        m.face((back[j], rows[0][j][0], rows[0][j + 1][0], back[j + 1]), None, turf, 2.0)
    return [Vector(r[0].co) for r in rows[0]]


def taper_rock(m, outline, height, mat, seed=0.0, tiers=6, point=(0.0, 0.0), lumps=0.22, v_span=None, curve=0.6, top_mat=None):
    """Isle underside: rings shrinking from an outline at y = height to a point at y = 0, lumpy strata,
    UVs u around and v by height (so the swatch's teal shadow sits at the tip)."""
    cx = sum(p[0] for p in outline) / len(outline)
    cz = sum(p[1] for p in outline) / len(outline)
    per = [0.0]
    for a, b in zip(outline, outline[1:] + outline[:1]):
        per.append(per[-1] + math.dist(a, b))
    tile = per[-1] / max(1, round(per[-1] / 6))
    rows = []
    for i in range(tiers + 1):
        t = i / tiers
        y = height * (1 - t)
        s = (1 - t) ** curve
        row = []
        for k, (x, z) in enumerate(outline + outline[:1]):
            a = math.atan2(z - cz, x - cx)
            n = 1 + lumps * noise.noise(Vector((math.cos(a) * 1.7, t * 4.5, math.sin(a) * 1.7 + seed))) * (1 if 0 < i < tiers else 0)
            p = Vector((point[0] * t + (cx + (x - cx) * s * n) * (1 - t * 0) , y, point[1] * t + (cz + (z - cz) * s * n)))
            if i == tiers:
                p = Vector((cx + point[0], 0, cz + point[1]))
            row.append((m.vert(p), (per[k] / tile, y / (v_span or height))))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(len(outline)):
            m.face((r0[k][0], r0[k + 1][0], r1[k + 1][0], r1[k][0]), (r0[k][1], r0[k + 1][1], r1[k + 1][1], r1[k][1]), mat)
    m.face([r[0] for r in rows[0][:-1]][::-1], None, top_mat if top_mat is not None else mat, 2.0)
    return rows


def ribbon(m, pts, widths, mat, side=Vector((1, 0, 0)), v_tile=None):
    """A flat double-sided strip along `pts` (waterfalls, leaves), u across and v along."""
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + (b - a).length)
    vt = v_tile or s[-1]
    prev = None
    for p, w, si in zip(pts, widths, s):
        pair = (m.vert(p - side * w / 2), m.vert(p + side * w / 2))
        if prev:
            m.face((prev[0][0], prev[0][1], pair[1], pair[0]), ((0, prev[1]), (1, prev[1]), (1, si / vt), (0, si / vt)), mat)
        prev = (pair, si / vt)


def seed_of(pid):
    return (sum(map(ord, pid)) % 97) * 0.37


# ---------- meadow ----------

MATS = [("MD_Ground", "ground.png", 0), ("MD_Path", "path.png", 0), ("MD_Cliff", "cliff.png", 0),
        ("MD_Underside", "underside.png", 0), ("MD_BirchBark", "birch-bark.png", 0), ("MD_OakBark", "oak-bark.png", 0),
        ("MD_Foliage", "leaf.png", 0), ("MD_OakFoliage", "oak-leaf.png", 0), ("MD_OakFoliageSun", "oak-leaf-sun.png", 0),
        ("MD_OakFoliageShade", "oak-leaf-shade.png", 0), ("MD_BlossomWhiteFoliage", "blossom-white.png", 0),
        ("MD_BlossomPinkFoliage", "blossom-pink.png", 0), ("MD_RoseFoliage", "rose-bush.png", 0),
        ("MD_WildflowerFoliage", "wildflowers.png", 0), ("MD_GrassFoliage", "long-grass.png", 0),
        ("MD_CloverFoliage", "clover.png", 0), ("MD_Limestone", "limestone.png", 0), ("MD_CarvedStone", "carved-stone.png", 0),
        ("MD_Water", "water.png", 0), ("MD_Waterfall", "waterfall.png", 0.15), ("MD_PetalWhiteFoliage", "petal-white.png", 0),
        ("MD_PetalYellowFoliage", "petal-yellow.png", 0), ("MD_PetalPinkFoliage", "petal-pink.png", 0),
        ("MD_LupinFoliage", "lupin.png", 0), ("MD_Earth", (0.16, 0.12, 0.08), 0),
        # alpha-cutout sprite cards (art/textures/foliage, 2x2 atlases)
        ("MD_Oak_Foliage_Card", "../../foliage/broadleaf-green.png", 0), ("MD_OakShade_Foliage_Card", "../../foliage/broadleaf-dark.png", 0),
        ("MD_Birch_Foliage_Card", "../../foliage/birch.png", 0), ("MD_Blossom_Foliage_Card", "../../foliage/blossom.png", 0),
        ("MD_Grass_Foliage_Card", "../../foliage/grass.png", 0), ("MD_Ivy_Foliage_Card", "../../foliage/ivy-moss.png", 0),
        ("MD_Elder_Foliage_Card", "../../foliage/elder-blossom.png", 0)]
(GROUND, PATH, CLIFF, UNDER, BIRCH, OAKBARK, LEAF, OAKLEAF, OAKSUN, OAKSHADE, BLOSSOM_W, BLOSSOM_P, ROSE, WILD, GRASS,
 CLOVER, LIME, CARVED, WATER, FALL, P_WHITE, P_YELLOW, P_PINK, LUPIN, EARTH,
 C_OAK, C_DARK, C_BIRCH, C_BLOSSOM, C_GRASS, C_IVY, C_ELDER) = range(len(MATS))
PETALS = (P_WHITE, P_YELLOW, P_PINK)
# Card material slots by role; nature-garden.py swaps in its own slots (M.CARDS = {...}) before building
CARDS = {"leaf": C_OAK, "dark": C_DARK, "birch": C_BIRCH, "blossom": C_BLOSSOM, "grass": C_GRASS, "ivy": C_IVY, "elder": C_ELDER, "core": OAKSHADE}


def configure():
    # Branch ends show bark; moss (the grass swatch) settles on upward-facing limestone
    K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/meadow"), cap_mat=OAKBARK, moss=(LIME, GROUND, 0.62))


def meadow_flowers(m, rng, cx, cz, rx, rz, count, y=0.0, size=0.07, h=(0.15, 0.45), seed=0.0, mats=PETALS):
    for k in range(count):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        head(m, (cx + math.cos(a) * r * rx, y + rng.uniform(*h), cz + math.sin(a) * r * rz), size * rng.uniform(0.8, 1.3),
             mats[k % len(mats)], seed=seed + k)


def birch(p, mats, seed, twin=False):
    m = Mesh()
    rng = random.Random(seed)
    W, H = p["size"][0], p["size"][1]
    stems = [(Vector((0.1, 0, 0.05)), Vector((-0.3, H * 0.92, 0.1)), 0.17)]
    if twin:
        stems = [(Vector((0.08, 0, 0)), Vector((0.6, H * 0.93, 0.2)), 0.13), (Vector((-0.08, 0, 0)), Vector((-0.65, H * 0.8, -0.25)), 0.12)]
    for si, (b, t, r0) in enumerate(stems):
        lean = (t - b).normalized() + Vector((0, 0.5, 0))
        pts = trunk(m, b + Vector((0, -0.25, 0)), t, lean, r0, 0.035, BIRCH, sides=8, n=9, seed=seed + si, flare=1.4, rough=0.06, twist=0.3,
                    wiggle=0.1)
        # an airy but full crown up the upper stem: leafy lobes hung on short branches, staggered round the stem so
        # a little sky shows between them
        top = pts[-1]
        n_l = 9 if not twin else 7
        y0, y1 = H * (0.42 if not twin else 0.45), top.y - 0.3
        reach = W * (0.24 if not twin else 0.17)
        lobes = []
        for k in range(n_l):
            f = k / (n_l - 1)
            y = y0 + (y1 - y0) * f
            idx = min(len(pts) - 1, max(2, int(round((y - pts[0].y) / (top.y - pts[0].y) * (len(pts) - 1)))))
            s0 = pts[idx]
            a = k * 2.4 + seed + si * 1.3 + rng.uniform(-0.3, 0.3)
            bulge = math.sin(math.pi * (0.15 + 0.8 * f))  # an oval crown, widest a little above the middle
            out = reach * (0.45 + 0.65 * bulge) * rng.uniform(0.8, 1.1)
            q = Vector((s0.x + math.cos(a) * out, y + 0.25, s0.z + math.sin(a) * out))
            r = (0.6 + 0.4 * bulge) * (1.0 if not twin else 0.85) * rng.uniform(0.9, 1.1)
            lobes.append((q, (r, r * 0.8, r)))
            if out > 0.3:
                d = q - s0
                limb(m, s0, d.normalized() + Vector((0, 0.7, 0)), q - d * 0.2, d.normalized(), 0.045, 0.018, BIRCH, sides=4, n=4,
                     seed=seed + k, rough=0.1)
        lobes.append((top + Vector((0, 0.1, 0)), (0.5, 0.6, 0.5)))
        centre = Vector((top.x * 0.7, (y0 + y1) / 2, top.z * 0.7))
        leaf_crown(m, lobes, [(CARDS["birch"], 1, None)], seed + si * 11, total=400 if not twin else 300, size=(0.8, 1.25), centre=centre, up_bias=0.75,
                   shade=(CARDS["dark"], (1, 1, 2, 2)), shade_low=0.25, fill=0.15)
    tuft(m, (0, 0, 0), 0.5, 0.35, GRASS, seed=seed, count=14)
    hard = Mesh()
    pebble(hard, (0.55, 0, 0.3), (0.35, 0.22, 0.3), LIME, seed=seed)
    return K.join([m.object(p["id"], mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


WHITE_BLOSSOM = (3, 1, 3, 1)  # blossom atlas: left quadrants mostly white, right ones pink
PINK_BLOSSOM = (1, 3, 1, 2)


def orchard(p, mats, seed, leaning=False, leaves=None, crown_semi=(0.36, 0.2), cy_frac=0.66, split=1.45, cards=720, apples=None):
    """Gnarled fruit tree: a twisting trunk splitting into four limbs under a low round crown of blossom (and leaf)
    card lobes. `leaves` is the leaf_crown material list (defaults to white blossom); `apples` a fruit material."""
    m = Mesh()
    rng = random.Random(seed)
    W, H = p["size"][0], p["size"][1]
    top = Vector((0.45 if leaning else 0.12, split if not leaning else split + 0.15, 0.1))
    pts = trunk(m, (0, -0.25, 0), top, Vector((0.8 if leaning else 0.2, 1, 0.1)), 0.27, 0.19, OAKBARK, sides=8, n=8, seed=seed,
                flare=1.6, rough=0.25, twist=1.6, wiggle=0.22)
    roots(m, (0, 0, 0), 0.27, 3, 0.75, OAKBARK, seed=seed, sides=4, rise=0.25, thick=0.6)
    cy = H * cy_frac
    semi = (W * crown_semi[0], H * crown_semi[1], W * crown_semi[0])
    centre = Vector((top.x * 0.8, cy, 0))
    ends = crown_points(centre, semi, 9, seed, shell=0.85, low=-0.45)
    r = W * 0.17
    lobes = [(q, (r * rng.uniform(0.85, 1.1), r * 0.78, r * rng.uniform(0.85, 1.1))) for q in ends]
    lobes.append((centre + Vector((0, semi[1] * 0.6, 0)), (r * 1.2, r * 0.9, r * 1.2)))
    leaves = leaves or [(CARDS["blossom"], 5, WHITE_BLOSSOM), (CARDS["leaf"], 1, None)]
    leaf_crown(m, lobes, leaves, seed, total=cards, size=(0.85, 1.25), centre=centre, up_bias=0.8,
               shade=(CARDS["dark"], (1, 1, 2, 2)), shade_low=0.25, fill=0.15)
    # four twisting limbs into the lower lobes
    low = sorted(ends, key=lambda q: q.y)[:6]
    for k in range(4):
        e = low[k] + Vector((0, -0.25, 0))
        d = (e - top)
        d.y = 0
        limb(m, top, d.normalized() + Vector((0, 0.8, 0)), e, d.normalized() * 0.3 + UP, 0.15, 0.05, OAKBARK, sides=5, n=7,
             seed=seed + k, rough=0.25, twist=1.0)
    if apples is not None:
        for k in range(14):
            c, (rx, ry, rz) = lobes[k % (len(lobes) - 1)]
            a = rng.uniform(0, 2 * math.pi)
            q = c + Vector((math.cos(a) * rx * 0.85, -ry * rng.uniform(0.2, 0.6), math.sin(a) * rz * 0.85))
            N.blob(m, q, (0.09, 0.09, 0.09), apples, seed=seed + k, rough=0.05, rings=3, segs=5, tile=0.3)
    tuft(m, (0, 0, 0), 0.6, 0.3, GRASS, seed=seed, count=14)
    hard = Mesh()
    for k, (x, z, s) in enumerate([(0.6, 0.4, 0.35), (-0.5, 0.5, 0.28), (0.2, -0.6, 0.22)]):
        pebble(hard, (x, 0, z), (s * 1.3, s * 0.8, s), LIME, seed=seed + k)
    return K.join([m.object(p["id"], mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def oak(p, mats, seed, three=False):
    m = Mesh()
    rng = random.Random(seed)
    W, H, Dp = p["size"]
    top = Vector((0.3, 4.6 if not three else 4.0, 0.2))
    pts = trunk(m, (0, -0.4, 0), top, Vector((0.1, 1, 0.05)), 1.05 if not three else 0.9, 0.72, OAKBARK, sides=14, n=10, seed=seed,
                flare=1.5, rough=0.22, twist=1.4, wiggle=0.25)
    roots(m, (0, 0, 0), 1.0, 7, 3.6 if not three else 3.0, OAKBARK, seed=seed, sides=7, rise=1.0, thick=0.5)
    # mound with stones
    lobed(m, (0, -0.3, 0), (4.4, 0.75, 4.0), GROUND, seed=seed, lobes=6, depth=0.25, rings=5, segs=16, tile=3.0, flat=0.2)
    hard = Mesh()
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(1.8, 3.6)
        s = rng.uniform(0.35, 0.85)
        pebble(hard, (math.cos(a) * r, 0.1, math.sin(a) * r), (s * 1.4, s * 0.9, s * 1.1), LIME, seed=seed + k, rings=4, segs=7)
    # crown: broad leafy lobes at the limb ends, a big shaded inner mass, sunlit broadleaf outside and dark
    # broadleaf low down and deep inside
    semi = (W * 0.5, H * 0.22, Dp * 0.5) if not three else (W * 0.48, H * 0.26, Dp * 0.48)
    centre = Vector((0.3, H * 0.7 if not three else H * 0.68, 0.2))
    ends = crown_points(centre, semi, 14 if not three else 12, seed, shell=0.8, low=-0.4)
    R = W * (0.14 if not three else 0.15)
    lobes = [(q, (R * rng.uniform(0.85, 1.15), R * rng.uniform(0.62, 0.75), R * rng.uniform(0.85, 1.15))) for q in ends]
    lobes.append((centre + Vector((0, semi[1] * 0.8, 0)), (R * 1.25, R * 0.75, R * 1.25)))
    lobes.append((centre + Vector((0, semi[1] * 0.2, 0)), (semi[0] * 0.45, semi[1] * 0.5, semi[2] * 0.45)))
    leaf_crown(m, lobes, [(CARDS["leaf"], 5, None), (CARDS["dark"], 1, None)], seed, density=24, size=(1.6, 2.4), centre=centre,
               up_bias=0.8, shade=(CARDS["dark"], None), shade_low=0.35, fill=0.2)
    # low wide-spreading limbs (A) or three main limbs (B), each feeding secondary branches into the lower lobes
    low = sorted(ends, key=lambda q: q.y)
    n_l = 3 if three else 6
    for k in range(n_l):
        a = 2 * math.pi * k / n_l + rng.uniform(-0.25, 0.25) + seed
        d = Vector((math.cos(a), 0, math.sin(a)))
        start = pts[-2] if three else pts[rng.randint(5, 8)]
        cand = sorted(low[:max(4, len(low) * 2 // 3)], key=lambda q: -Vector((q.x, 0, q.z)).normalized().dot(d))
        e = cand[0] + Vector((0, -0.4, 0))
        if three:
            e = centre + d * semi[0] * 0.4 + Vector((0, -semi[1] * 0.25, 0))
        lp = limb(m, start, d * 0.9 + Vector((0, 0.5 if not three else 1.0, 0)), e, d + Vector((0, 0.5, 0)), 0.62 if not three else 0.6, 0.25,
                  OAKBARK, sides=10, n=10, seed=seed + k, rough=0.22, twist=1.2, k=0.7)
        near = sorted(low, key=lambda q: (q - e).length)[1:3 if three else 2]
        for j, q in enumerate(near):
            s0 = lp[rng.randint(5, 9)]
            limb(m, s0, (q - s0).normalized() + Vector((0, 0.6, 0)), q, (q - s0).normalized(), 0.22, 0.07, OAKBARK, sides=6, n=6,
                 seed=seed + k * 5 + j, rough=0.2)
    if three:
        # small hollow knot on the trunk
        kp = pts[5] + Vector((0, 0, 0.82))
        tube(m, [kp + Vector((0, 0, -0.15)), kp + Vector((0, 0, 0.12)), kp + Vector((0, 0, 0.1))], [0.32, 0.26, 0.12], OAKBARK, 10,
             rough=0.25, seed=seed, caps=(False, False))
        lobed(m, kp + Vector((0, 0, 0.02)), (0.2, 0.28, 0.08), EARTH, seed=seed, rings=4, segs=8)
    for k, (x, z) in enumerate([(1.8, 1.5), (-2.0, 0.9), (0.6, -2.4), (-1.2, -1.8), (2.6, -0.6), (-3.0, 0.2)]):
        grass(m, (x, 0.15, z), 0.7, 0.4, seed=seed + k, count=2)
    return K.join([m.object(p["id"], mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def wildflower_drift(p, m, seed, mound=None, heads=(None,), spikes=None, n_heads=18, n_spikes=5):
    """A drift of long and short meadow grass cards with flower heads and lupin spikes standing out of it."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    for k in range(9):
        a = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
        rr = 0.0 if k == 0 else rng.uniform(0.45, 0.9)
        grass(m, (math.cos(a) * rr * w * 0.36, 0.0, math.sin(a) * rr * d * 0.34), 0.5, h * (0.5 if rr > 0.6 else 0.62), seed=seed + k,
              quad=3 if k % 3 else 2)
    hm = (P_WHITE, P_YELLOW, P_PINK, P_WHITE) if heads == (None,) else heads
    for k in range(n_heads):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.9
        x, z = math.cos(a) * r * w * 0.42, math.sin(a) * r * d * 0.4
        y = h * (0.42 * (1 - r * r) + rng.uniform(0.12, 0.3))
        head(m, (x, y, z), rng.uniform(0.07, 0.11), hm[k % len(hm)], seed=seed + k)
    for k in range(n_spikes):
        spike(m, (-w * 0.3 + w * 0.6 * k / max(1, n_spikes - 1) + rng.uniform(-0.1, 0.1), 0.0, -d * 0.2 + rng.uniform(-0.12, 0.08)),
              h * rng.uniform(0.7, 0.92), 0.07, LUPIN if spikes is None else spikes, seed=seed + k, sides=5)


def clover_patch(p, m, seed, leaf=None, bloom=None):
    rng = random.Random(seed)
    w, h, d = p["size"]
    lobed(m, (0, -0.04, 0), (w * 0.42, h * 0.45, d * 0.42), CLOVER if leaf is None else leaf, seed=seed, lobes=5, depth=0.3, rings=3, segs=8,
          tile=0.3, flat=0.2)
    for k in range(16):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        head(m, (math.cos(a) * r * w * 0.45, h * 0.35 * (1 - r * 0.6) + 0.02, math.sin(a) * r * d * 0.45), rng.uniform(0.05, 0.07),
             CLOVER if leaf is None else leaf, seed=seed + k, petals=3, cup=0.1)
    for k in range(6):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.7
        head(m, (math.cos(a) * r * w * 0.4, h * 0.85, math.sin(a) * r * d * 0.4), 0.035, P_WHITE if bloom is None else bloom, seed=seed + k + 20,
             petals=4, cup=0.6)
    for k in range(3):  # short grass fringing the patch
        a = 2 * math.pi * k / 3 + 0.5
        grass(m, (math.cos(a) * w * 0.4, 0.0, math.sin(a) * d * 0.4), 0.18, max(0.12, h * 0.9), seed=seed + k, quad=2, planes=2)


def flower_clump(p, m, seed, mound=None, heads=(P_YELLOW, P_WHITE, P_YELLOW, P_PINK), spikes=None):
    rng = random.Random(seed)
    w, h, d = p["size"]
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        grass(m, (math.cos(a) * w * 0.15, 0.0, math.sin(a) * d * 0.15), 0.3, h * 0.5, seed=seed + k, quad=(2, 3, 2)[k])
    for k in range(12):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        head(m, (math.cos(a) * r * w * 0.38, rng.uniform(0.16, 0.36), math.sin(a) * r * d * 0.38), rng.uniform(0.05, 0.07), heads[k % len(heads)],
             seed=seed + k)
    for k in range(2):
        spike(m, (-0.08 + 0.16 * k, 0.0, -0.1), h * (0.8 + 0.15 * k), 0.05, LUPIN if spikes is None else spikes, seed=seed + k, sides=5)


def flowering_bush(p, mats, seed, leaf=(None,), heads=(P_WHITE, P_PINK), stone_mat=None):
    """Rose-like flowering shrub: a dark hidden core under blossom cards, a few branches showing at the foot."""
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    lobed(m, (0, h * 0.4, 0), (w * 0.28, h * 0.28, d * 0.28), CARDS["core"], seed=seed, lobes=6, depth=0.3, rings=3, segs=8, tile=0.55, flat=0.6)
    lobes = [((0, h * 0.62, 0), (w * 0.3, h * 0.26, d * 0.3))]
    for k in range(5):
        a = 2 * math.pi * k / 5 + seed
        lobes.append(((math.cos(a) * w * 0.2, h * rng.uniform(0.36, 0.48), math.sin(a) * d * 0.2), (w * 0.2, h * 0.2, d * 0.2)))
    leaf_crown(m, lobes, [(CARDS["blossom"], 4, (2, 3, 2, 3)), (CARDS["leaf"], 1, None)], seed, total=200, size=(0.6, 0.85),
               centre=(0, h * 0.35, 0), up_bias=0.8, shade=(CARDS["dark"], None), shade_low=0.15)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        limb(m, (math.cos(a) * 0.05, 0, math.sin(a) * 0.05), (math.cos(a) * 0.4, 1, math.sin(a) * 0.4),
             (math.cos(a) * w * 0.2, h * 0.32, math.sin(a) * d * 0.2), (math.cos(a), 1, math.sin(a)), 0.04, 0.02, OAKBARK, sides=4, n=3,
             seed=seed + k)
    grass(m, (0.3, 0, 0.35), 0.3, 0.3, seed=seed, quad=2)
    hard = Mesh()
    pebble(hard, (0.55, 0, 0.55), (0.4, 0.25, 0.32), LIME if stone_mat is None else stone_mat, seed=seed)
    return K.join([m.object(p["id"], mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def hedge_leg(m, rng, origin, along, L, h, dep, core, seed, leaves, n_lobes=None, flowers=(), spikes=(), cards=120):
    """One straight hedge run from `origin` along unit `along` for L metres, `dep` deep (centred on origin's line):
    a hidden dark body carded over with leafy sprites in overlapping lobes, flowers tucked into the faces."""
    o, u = Vector(origin), Vector(along)
    side = Vector((-u.z, 0, u.x))
    c = o + u * (L / 2) + UP * (h * 0.4)
    rad = Vector((abs(u.x), 0, abs(u.z))) * (L / 2 - 0.15) + Vector((abs(side.x), 0, abs(side.z))) * dep * 0.32 + UP * h * 0.34
    lobed(m, c, (rad.x, rad.y, rad.z), core, seed=seed, lobes=9, depth=0.25, rings=3, segs=10, tile=0.8, flat=0.3, up=0.0)
    n = n_lobes or max(2, round(L / 0.8))
    lobes = []
    for k in range(n):
        t = (k + 0.5) / n
        q = o + u * (L * t + rng.uniform(-0.08, 0.08)) + side * dep * rng.uniform(-0.08, 0.08) + UP * (h * rng.uniform(0.54, 0.6))
        r = L / n * 0.62
        lobes.append((q, (r * abs(u.x) + dep * 0.5 * abs(side.x), h * rng.uniform(0.42, 0.48), r * abs(u.z) + dep * 0.5 * abs(side.z))))
    leaf_crown(m, lobes, leaves, seed, total=cards, size=(0.7, 1.0), centre=c, up_bias=0.6, shade=(CARDS["dark"], None),
               shade_low=0.3)
    for k, fm in enumerate(flowers):
        t = rng.uniform(0.08, 0.92)
        sd = rng.choice((-1, 1)) * dep * 0.55
        head(m, o + u * (L * t) + side * sd + UP * rng.uniform(0.45, 1.25), 0.08, fm, seed=seed + k)
    for k, fm in enumerate(spikes):
        t = rng.uniform(0.08, 0.92)
        spike(m, o + u * (L * t) - side * dep * 0.56 + UP * 0.05, 0.42, 0.05, fm, seed=seed + k, sides=4)


def hedgerow(p, mats, seed, corner=False, leaves=None, flowers=(), spikes=(LUPIN, LUPIN), stone_mat=None):
    """Modular hedge, bottom-left-front pivot: x 0..w, z -d..0, soft rounded ends that reach the piece boundary
    so runs butt together. `corner` builds an L with 2 m legs (front along +x, left leg back along -z)."""
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    dep = 1.0
    leaves = leaves or [(CARDS["leaf"], 6, None), (CARDS["elder"], 1, None)]
    core = CARDS["core"]
    if corner:
        hedge_leg(m, rng, (0, 0, -dep / 2), (1, 0, 0), w, h, dep, core, seed, leaves, n_lobes=3, flowers=flowers[:len(flowers) // 2],
                  spikes=spikes[:1], cards=100)
        hedge_leg(m, rng, (dep / 2, 0, -dep), (0, 0, -1), w - dep, h, dep, core, seed + 5, leaves, n_lobes=2, flowers=flowers[len(flowers) // 2:],
                  spikes=spikes[1:2], cards=65)
    else:
        hedge_leg(m, rng, (0, 0, -dep / 2), (1, 0, 0), w, h, dep, core, seed, leaves, n_lobes=5, flowers=flowers, spikes=spikes, cards=185)
    for k in range(3):
        grass(m, (rng.uniform(0.3, w - 0.3), 0, 0.05), 0.3, 0.3, seed=seed + k, quad=2)
    hard = Mesh()
    for k in range(2):
        pebble(hard, (rng.uniform(0.4, w - 0.4), 0, rng.uniform(-0.1, 0.02)), (0.32, 0.2, 0.26), LIME if stone_mat is None else stone_mat,
               seed=seed + k, rings=3, segs=5)
    return K.join([m.object(p["id"], mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def grass_tuft(m, w, h, seed, long=True):
    """Ground grass piece: a long flowing tuft (three crossed cards plus a shorter one at its foot) or a low short
    meadow tuft."""
    if long:
        grass(m, (0, 0, 0), w * 0.55, h, seed=seed, quad=3, planes=3)
        grass(m, (0.08, 0, 0.05), w * 0.4, h * 0.55, seed=seed + 1, quad=2, planes=2)
    else:
        grass(m, (0, 0, 0), w * 0.5, h, seed=seed, quad=2, planes=3)
        grass(m, (0.12, 0, -0.08), w * 0.35, h * 0.8, seed=seed + 1, quad=2, planes=2)


def standing_stone(p, mats, seed):
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    # cross-section: a flat carved front face (+Z) with chamfered sides
    sec = [(-0.48, 0.32), (0.48, 0.32), (0.5, 0.0), (0.38, -0.36), (-0.36, -0.38), (-0.5, -0.02)]
    n = 6
    rows = []
    for i in range(n + 1):
        t = i / n
        y = -0.25 + (h + 0.25) * t * 0.96
        sc = (1 - 0.35 * t ** 1.2) * (1 + 0.04 * math.sin(t * 7 + seed))
        lean = Vector((0.18 * t * t, 0, -0.08 * t * t))
        row = []
        for j, (x, z) in enumerate(sec):
            jit = 0.03 * noise.noise(Vector((x * 3, t * 5, z * 3 + seed)))
            row.append(m.vert(Vector((x * w * 0.98 * sc + jit, y, z * d * 1.1 * sc + jit)) + lean))
        rows.append(row)
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        for j in range(len(sec)):
            j1 = (j + 1) % len(sec)
            a, b, c, e = rows[i][j], rows[i][j1], rows[i + 1][j1], rows[i + 1][j]
            if j == 0:  # carved front face: the sigil swatch fitted once over the face
                m.face((a, b, c, e), ((0.08, 0.05 + 0.9 * t0), (0.92, 0.05 + 0.9 * t0), (0.92, 0.05 + 0.9 * t1), (0.08, 0.05 + 0.9 * t1)), CARVED)
            else:
                m.face((a, b, c, e), None, LIME, 1.1)
    # rounded, slightly ridged top
    tip = Vector((0.18 * 0.96, h * 0.96 - 0.25 * 0.04 + 0.16, -0.08 * 0.96))
    cap = m.vert(tip)
    for j in range(len(sec)):
        m.face((rows[-1][j], rows[-1][(j + 1) % len(sec)], cap), None, LIME, 1.1)
    stone_ob = m.object(p["id"], mats, seed=seed, smooth=False)
    s = Mesh()
    for k in range(3):  # ivy climbing the left side
        x0 = -0.42 + 0.05 * k
        pts = [Vector((x0 + 0.06 * math.sin(i * 1.3 + k), 0.02 + i * (1.7 - 0.35 * k) / 6, 0.12 - 0.12 * k + 0.06 * math.cos(i))) for i in range(7)]
        tube(s, pts, [0.12 * (1 - 0.6 * i / 6) for i in range(7)], LEAF, 5, rough=0.4, seed=seed + k, flat=0.5, tile=0.6)
    tuft(s, (0.2, 0, 0.35), 0.55, 0.4, GRASS, seed=seed, count=8)
    tuft(s, (-0.35, 0, -0.2), 0.45, 0.3, GRASS, seed=seed + 2, count=5)
    meadow_flowers(s, rng, 0.1, 0.45, 0.5, 0.2, 4, y=0.0, size=0.06, h=(0.12, 0.25), seed=seed)
    hard = Mesh()
    for k, (x, z, sz) in enumerate([(0.62, 0.3, 0.22), (-0.6, 0.35, 0.16), (0.35, 0.55, 0.12)]):
        pebble(hard, (x, 0, z), (sz * 1.3, sz * 0.8, sz), LIME, seed=seed + k)
    return K.join([stone_ob, s.object(p["id"] + ".ivy", mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def dry_wall(p, mats, seed, corner=False, stone_mat=None, core=EARTH, courses=4, tufts=GRASS, ragged=0.0):
    """Modular dry-stone wall, bottom-left-front pivot (x 0..w, z -d..0). Corners add a leg back along -z."""
    rng = random.Random(seed)
    m = Mesh()
    w, h, _ = p["size"]
    dep = 0.5
    sm = LIME if stone_mat is None else stone_mat
    drystone(m, rng, w, h * 0.92, dep, courses, sm, frame_xf((0, 0, 0), (1, 0, 0), (0, 0, -1)), core=core, ragged=ragged)
    if corner:
        drystone(m, rng, w - dep, h * 0.92, dep, courses, sm, frame_xf((0, 0, -dep), (0, 0, -1), (1, 0, 0)), core=core, ragged=ragged)
        # the corner post stands one block higher
        stone(m, (0.02, h * 0.92, -dep + 0.03), (dep - 0.02, h * 1.12, -0.03), sm, rng, frame_xf((0, 0, 0), (1, 0, 0), (0, 0, 1)))
    # fallen stones
    for k in range(1):
        x = rng.uniform(0.3, w - 0.6)
        a = rng.uniform(-0.5, 0.5)
        stone(m, (0, 0, 0), (0.28, 0.17, 0.22), sm, rng, frame_xf((x, 0, 0.02), (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a))),
              taper=0.04)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    for k in range(3):
        tuft(g, (rng.uniform(0.2, w - 0.2), 0, rng.uniform(-0.02, 0.06)), 0.3, 0.3, tufts, seed=seed + k, count=4, width=0.04)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def limestone_rock(p, mats, seed):
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    pid = p["id"]
    if pid.endswith("-a"):   # big rounded boulder with a smaller one leaning on it
        N.rock(m, (w * 0.78, h, d * 0.8), LIME, seed=seed, rough=0.3, rings=6, segs=10, sink=0.2)
        sm = Mesh()
        N.rock(sm, (w * 0.42, h * 0.5, d * 0.45), LIME, seed=seed + 3, rough=0.32, rings=5, segs=8, sink=0.1)
        for v in sm.bm.verts:
            v.co += K.V(w * 0.3, 0, d * 0.25)
        ob1 = m.object(pid + ".a", mats, seed=seed, smooth=False)
        ob2 = sm.object(pid + ".b", mats, seed=seed, smooth=False)
        g = Mesh()
        tuft(g, (-w * 0.35, 0, d * 0.3), 0.35, 0.3, GRASS, seed=seed, count=5)
        return K.join([ob1, ob2, g.object(pid + ".g", mats, seed=seed)], pid)
    if pid.endswith("-b"):   # low layered slabs
        N.slabs(m, (w, h, d), LIME, seed=seed, layers=3, tilt=0.15)
        for k in range(2):
            stone(m, (0, 0, 0), (0.45, 0.22, 0.35), LIME, rng, frame_xf((w * 0.32 - k * w * 0.75, 0, d * 0.32), (1, 0, 0.2 * k), (-0.2 * k, 0, 1)),
                  pillow=0.05, taper=0.05)
    elif pid.endswith("-c"):  # upright shards around one tall spike
        for k, (x, z, hh, r) in enumerate([(0, 0, h, 0.42), (0.42, 0.25, h * 0.55, 0.3), (-0.45, 0.18, h * 0.45, 0.28),
                                            (0.15, -0.4, h * 0.38, 0.26), (-0.25, -0.3, h * 0.6, 0.27)]):
            lean = Vector((x * 0.25, 1, z * 0.25)).normalized()
            pts = [Vector((x, -0.2, z)) + lean * (hh + 0.2) * t for t in (0, 0.35, 0.7, 1.0)]
            tube(m, pts, [r, r * 0.82, r * 0.5, 0.03], LIME, 5, twist=0.6, rough=0.18, seed=seed + k, caps=(False, False), tile=1.0)
    elif pid.endswith("-d"):  # low mossy dome
        N.rock(m, (w, h * 1.1, d), LIME, seed=seed, rough=0.28, rings=5, segs=10, sink=0.25)
        ob = m.object(pid, mats, seed=seed, smooth=False, moss=(LIME, GROUND, 0.25))
        g = Mesh()
        tuft(g, (w * 0.4, 0, d * 0.2), 0.3, 0.25, GRASS, seed=seed, count=4)
        return K.join([ob, g.object(pid + ".g", mats, seed=seed)], pid)
    else:  # flat cluster of small blocks half sunk in turf
        for k, (x, z, sw, sh, sd, a) in enumerate([(-0.35, 0.1, 0.6, 0.45, 0.5, 0.2), (0.3, -0.1, 0.55, 0.38, 0.45, -0.4),
                                                    (0.55, 0.35, 0.35, 0.25, 0.3, 0.8), (-0.05, 0.42, 0.4, 0.3, 0.3, -0.2),
                                                    (0.0, -0.4, 0.42, 0.28, 0.35, 0.5)]):
            stone(m, (-sw / 2, -0.12, -sd / 2), (sw / 2, sh, sd / 2), LIME, rng,
                  frame_xf((x, 0, z), (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a))), pillow=0.06, taper=0.07)
        lobed(m, (0, -0.15, 0), (w * 0.5, 0.2, d * 0.5), GROUND, seed=seed, rings=3, segs=10, tile=1.5, flat=0.2)
    ob = m.object(pid, mats, seed=seed, smooth=False)
    g = Mesh()
    tuft(g, (w * 0.3, 0, d * 0.35), 0.3, 0.25, GRASS, seed=seed, count=4)
    return K.join([ob, g.object(pid + ".g", mats, seed=seed)], pid)


def lip_piece(p, mats, seed, turf=GROUND, cliff=CLIFF, ivy_mat=LEAF, flowers=PETALS, blocks=None, overhang=0.55):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    edge = lip_edge(m, w, d, h, turf, cliff, seed=seed, overhang=overhang, segs=16, drops=6)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    s = Mesh()
    # rounded turf roll over the edge
    roll = [Vector((q.x, h + 0.02, q.z - 0.15)) for q in [Vector((v.x, 0, -v.y)) for v in edge]]
    tube(s, roll, [0.3 + 0.08 * math.sin(i * 1.7 + seed) for i in range(len(roll))], turf, 7, rough=0.3, seed=seed, caps=(False, False), tile=1.5)
    for k in range(9):  # ivy and moss hanging over the edge (painted drapes facing out)
        q = roll[1 + k * (len(roll) - 2) // 8]
        N.card_drape(s, q + Vector((rng.uniform(-0.2, 0.2), 0.12, 0.3)), rng.uniform(1.0, h * 0.75), 0.9, CARDS["ivy"], seed=int(seed * 10) + k,
                     count=2, spread=0.4, pick=(0, 2, 0)[k % 3], facing=0.0)
    for k in range(9):
        x = -w / 2 + 0.5 + (w - 1.0) * k / 8
        grass(s, (x + rng.uniform(-0.25, 0.25), h, d / 2 - 0.35 - rng.uniform(0, 0.3)), 0.4, 0.3, seed=seed + k, quad=(2, 3, 2)[k % 3])
    meadow_flowers(s, rng, 0, d / 2 - 0.6, w * 0.45, 0.4, 10, y=h, size=0.07, h=(0.08, 0.2), seed=seed, mats=flowers)
    return K.join([ob, s.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def underside_piece(p, mats, seed, rock=UNDER, turf=GROUND, ivy_mat=LEAF, root=OAKBARK, extra=None, rock_top=None, inset=1.0):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    outline = oval(w, d, 16, seed=seed, rough=0.12)
    taper_rock(m, [(x * inset, z * inset) for x, z in outline], rock_top or h, rock, seed=seed, tiers=6, point=(0.4, 0.2), lumps=0.22, curve=0.55, top_mat=turf)
    for k, (x, z, s) in enumerate([(-2.0, 1.0, 0.45), (2.1, -0.6, 0.38), (0.6, 1.6, 0.3)]):
        sub = oval(w * s, d * s, 8, seed=seed + k)
        sub = [(px + x, pz + z) for px, pz in sub]
        hh = h * s * 1.3
        rows = taper_rock(m, sub, hh, rock, seed=seed + k, tiers=4, lumps=0.25, v_span=h, curve=0.7)
        for row in rows:  # lift the cone so its top tucks into the main mass
            for v, _ in row:
                v.co.z += h * 0.72 - hh * 0.62
    if extra:
        extra(m, rng)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    s = Mesh()
    rim = [Vector((x * 1.02, h + 0.05, z * 1.02)) for x, z in outline]
    rim += rim[:2]
    tube(s, rim, [0.32] * len(rim), turf, 6, rough=0.3, seed=seed, caps=(False, False), tile=1.5)
    for k in range(8):
        x, z = outline[(k * 2 + 1) % len(outline)]
        ivy(s, Vector((x, h, z)) * 1.0 + Vector((0, -0.05, 0)), rng.uniform(2.0, 4.5), ivy_mat, seed=seed + k, width=0.35,
            outward=Vector((x, 0, z)).normalized() * 0.4)
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        st = Vector((math.cos(a) * w * 0.25, h * rng.uniform(0.35, 0.6), math.sin(a) * d * 0.25))
        st = Vector((math.cos(a) * w * 0.32 * 0.75, st.y, math.sin(a) * d * 0.32 * 0.75))
        end = st + Vector((math.cos(a) * 0.6, -rng.uniform(2.0, 3.5), math.sin(a) * 0.6))
        limb(s, st, Vector((math.cos(a), -0.3, math.sin(a))), end, Vector((0, -1, 0)), 0.1, 0.02, root, sides=5, n=7, seed=seed + k, rough=0.3)
    return K.join([ob, s.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def pond(p, mats, seed, rim_mat=GROUND, water=WATER, stone_mat=LIME, reeds=GRASS, pads=CLOVER, outline=None, n_stones=8, extra=None):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    outline = outline or oval(w, d, 28, seed=seed, rough=0.07)
    # soft grass rim: from the surrounding ground (y 0) up over a low bank and down to the waterline
    ring_band(m, outline, [0.0, 0.22, 0.12, -0.15], [1.0, 0.9, 0.82, 0.74], rim_mat, tile=2.0, planar=True)
    # water surface, a separate flat plane
    wl = [m.vert((x * 0.8, 0.1, z * 0.8)) for x, z in outline]
    m.face(wl[::-1], [(x * 0.8 / w + 0.5, z * 0.8 / d + 0.5) for x, z in outline][::-1], water)
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi)
        x, z = math.cos(a) * w * 0.25, math.sin(a) * d * 0.22
        head(m, (x, 0.12, z), rng.uniform(0.18, 0.28), pads, seed=seed + k, petals=4, cup=0.0)
    ob = m.object(p["id"], mats, seed=seed)
    hard = Mesh()
    idx = rng.sample(range(len(outline)), n_stones)
    for k, i in enumerate(idx):
        x, z = outline[i]
        s = rng.uniform(0.25, 0.5)
        pebble(hard, (x * 0.86, 0.05, z * 0.86), (s * 1.3, s * 0.7, s), stone_mat, seed=seed + k, rings=4, segs=6)
    g = Mesh()
    for k in range(2):
        x, z = outline[(7 + k * 2) % len(outline)]
        tuft(g, (x * 0.8, 0.05, z * 0.8), 0.35, 1.0, reeds, seed=seed + k, count=9, width=0.035, lean=0.25)
    if extra:
        extra(hard, rng)
    return K.join([ob, hard.object(p["id"] + ".st", mats, seed=seed, smooth=False), g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def stream(p, mats, seed, bank=GROUND, bed=PATH, water=WATER, stone_mat=LIME):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    prof = [(-d / 2, 0.0), (-d * 0.33, 0.12), (-d * 0.2, -0.05), (0.0, -0.1), (d * 0.2, -0.05), (d * 0.33, 0.12), (d / 2, 0.0)]
    n = 12
    rows = []
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        zc = 0.12 * math.sin(i / n * math.pi * 2 + seed)
        rows.append([(m.vert((x, y, zc + z)), (x / 1.5, (z + d / 2) / 1.5)) for z, y in prof])
    for i in range(n):
        for j in range(len(prof) - 1):
            a, b, c, e = rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]
            m.face((a[0], e[0], c[0], b[0]), (a[1], e[1], c[1], b[1]), bank if j in (0, 5) else bed)
    for i in range(n):
        x0, x1 = -w / 2 + w * i / n, -w / 2 + w * (i + 1) / n
        z0, z1 = 0.12 * math.sin(i / n * math.pi * 2 + seed), 0.12 * math.sin((i + 1) / n * math.pi * 2 + seed)
        hw = d * 0.27
        vs = [m.vert((x0, 0.05, z0 - hw)), m.vert((x0, 0.05, z0 + hw)), m.vert((x1, 0.05, z1 + hw)), m.vert((x1, 0.05, z1 - hw))]
        m.face(vs, [(x0 / 2, 0), (x0 / 2, 1), (x1 / 2, 1), (x1 / 2, 0)], water)
    ob = m.object(p["id"], mats, seed=seed)
    hard = Mesh()
    for k in range(12):
        side = 1 if k % 2 else -1
        x = -w / 2 + 0.2 + (w - 0.4) * k / 11
        s = rng.uniform(0.28, 0.45)
        pebble(hard, (x, 0.05, side * d * rng.uniform(0.3, 0.4) + 0.12 * math.sin(k / 11 * math.pi * 2 + seed)), (s * 1.3, s * 0.7, s), stone_mat,
               seed=seed + k, rings=4, segs=6)
    return K.join([ob, hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def waterfall(p, mats, seed, fall=FALL, stone_mat=LIME, rock=CLIFF):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    for k, (wd, off, dz) in enumerate([(w * 0.7, 0.0, 0.0), (w * 0.4, -0.35, 0.1), (w * 0.35, 0.38, 0.06)]):
        pts = []
        n = 14
        for i in range(n + 1):
            t = i / n
            y = h - (h + 0.2) * t
            z = d * 0.45 * math.sin(min(1.0, t * 4) * math.pi / 2) + dz - 0.2
            pts.append(Vector((off + 0.05 * math.sin(t * 9 + k), y, z)))
        ribbon(m, pts, [wd * (0.8 + 0.6 * i / n) for i in range(n + 1)], fall, v_tile=3.0 + k)
    # spray and mist at the foot
    for k in range(4):
        r = rng.uniform(0.45, 0.7)
        lobed(m, (rng.uniform(-0.5, 0.5), 0.15 + 0.1 * k, d * 0.35 + rng.uniform(-0.2, 0.2)), (r, r * 0.6, r * 0.8), fall, seed=seed + k,
              rings=5, segs=8, tile=1.0)
    ob = m.object(p["id"], mats, seed=seed)
    hard = Mesh()
    for k, (x, y) in enumerate([(-0.75, h - 0.1), (0.75, h - 0.15), (-0.6, 0.05), (0.7, 0.0)]):
        s = rng.uniform(0.3, 0.45)
        pebble(hard, (x, y, 0.0 if y > 1 else d * 0.3), (s * 1.3, s * 0.8, s), stone_mat, seed=seed + k, rings=4, segs=6)
    return K.join([ob, hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def build_piece(p, mats):
    import bpy
    bpy.context.scene.display.shading.show_specular_highlight = False  # painted swatches, no plastic sheen
    grade_cards(mats)
    pid = p["id"]
    seed = seed_of(pid)
    if pid.startswith("md-birch"):
        return birch(p, mats, seed, twin=pid.endswith("-b"))
    if pid == "md-orchard-a":
        return orchard(p, mats, seed)
    if pid == "md-orchard-b":
        return orchard(p, mats, seed, leaning=True, leaves=[(CARDS["blossom"], 5, PINK_BLOSSOM), (CARDS["leaf"], 1, None)])
    if pid.startswith("md-oak"):
        return oak(p, mats, seed, three=pid.endswith("-b"))
    if pid == "md-flowering-bush":
        return flowering_bush(p, mats, seed)
    if pid == "md-hedgerow-4m":
        return hedgerow(p, mats, seed)
    if pid == "md-standing-stone":
        return standing_stone(p, mats, seed)
    if pid.startswith("md-wall"):
        return dry_wall(p, mats, seed, corner=pid.endswith("corner"))
    if pid.startswith("md-rock"):
        return limestone_rock(p, mats, seed)
    if pid == "md-lip-ledge":
        return lip_piece(p, mats, seed)
    if pid == "md-underside":
        return underside_piece(p, mats, seed)
    if pid == "md-pond":
        return pond(p, mats, seed)
    if pid == "md-stream":
        return stream(p, mats, seed)
    if pid == "md-waterfall":
        return waterfall(p, mats, seed)
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    if pid == "md-wildflower-drift":
        wildflower_drift(p, m, seed)
    elif pid == "md-grass-long":
        grass_tuft(m, w, h, seed, long=True)
    elif pid == "md-grass-short":
        grass_tuft(m, w, h, seed, long=False)
    elif pid == "md-clover":
        clover_patch(p, m, seed)
    elif pid == "md-flower-clump":
        flower_clump(p, m, seed)
    else:
        raise ValueError(f"no builder for {pid}")
    return m.object(pid, mats, seed=seed)


CATEGORY = {"tree": "tree", "hero": "hero", "plant": "bush", "ground": "ground", "rock": "rock", "lip": "lip", "underside": "underside",
            "water": "water"}


def catalogue_category(p):
    pid = p["id"]
    if "wall" in pid:
        return "wall"
    if pid.endswith(("standing-stone",)):
        return "rock"
    return CATEGORY.get(p["family"], "prop")


def closeups(build_piece, ids, out_dir):
    """Render single pieces at close range (for iteration), textured, one PNG each."""
    os.makedirs(out_dir, exist_ok=True)
    for pid in ids:
        mats = K.reset()
        ob = build_piece(B.PIECES[pid], mats)
        objs = [ob, B.figure(Vector((-B.PIECES[pid]["size"][0] / 2 - 0.6, 0, 0)))]
        import bpy
        bpy.context.view_layer.update()
        print(f"[close] {pid}: {K.tris(ob)} tris")
        render_close(os.path.join(out_dir, f"{pid}.png"), B.bounds(objs))


def render_close(path, bounds):
    import bpy
    B.render(path, bounds, "TEXTURE")
    sc = bpy.context.scene
    lo, hi = bounds
    span = max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    sc.camera.data.ortho_scale = span * 1.2
    sc.render.resolution_x, sc.render.resolution_y = 1200, 1200
    bpy.ops.render.render(write_still=True)


def main(build_piece, biome, category):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--only" in args:
        ids = args[args.index("--only") + 1].split(",")
        out = args[args.index("--close") + 1] if "--close" in args else os.path.join(K.OUT, "close")
        closeups(build_piece, ids, out)
        return
    K.build_all(build_piece, extras=[(p["id"], category(p)) for p in B.kit["pieces"]], biome=biome)


if __name__ == "__main__":
    configure()
    main(build_piece, "meadow", catalogue_category)
