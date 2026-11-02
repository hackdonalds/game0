# Roothold nature kit: ancient landmark tree, oaks, elders, cedars, understory, ground cover, mossy granite and slate,
# the root-wrapped lip and underside. Painted swatches cropped from the biome's nature sheet live in
# art/textures/biomes/roothold. The first half of this file holds the nature generators shared with
# nature-forest.py (clumped leaf masses, leaf sprigs, fronds, mushrooms, faceted hull rocks, lips, undersides).
# Usage: Blender --background --python scripts/kit/nature-roothold.py -- roothold [--only id,id] [--out dir]
import bmesh, math, os, random, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
import naturelib as N  # noqa: E402
from kitlib import Mesh, hermite  # noqa: E402
from kitlib import tube as _tube  # noqa: E402


def tube(*a, **k):
    """kitlib.tube with a longer default texture repeat, so painted bark reads as bark rather than a kaleidoscope."""
    k.setdefault("tile", 2.4)
    return _tube(*a, **k)


def render(path, bounds, color_type="TEXTURE", d=(1, -1.3, 1.1), fit=False, res=(2400, 1500)):
    """blockout.render with matte shading (no studio specular), optionally fitting the whole height."""
    import bpy
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_cavity, sh.show_shadows = "STUDIO", color_type, True, True
    sh.show_specular_highlight = False
    sh.show_cavity = False
    sh.shadow_intensity = 0.35
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.9, 0.9, 0.88)
    lo, hi = bounds
    centre = (lo + hi) / 2
    span = max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    sc.collection.objects.link(cam)
    dv = Vector(d).normalized()
    cam.location = centre + dv * span * 2
    cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = span * 6
    # fit the projected bounding box (both width and height) into the frame
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    xs, ys = [], []
    for cx in (lo.x, hi.x):
        for cy in (lo.y, hi.y):
            for cz in (lo.z, hi.z):
                q = inv @ Vector((cx, cy, cz))
                xs.append(q.x)
                ys.append(q.y)
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cam.data.ortho_scale = max(w, h * res[0] / res[1]) * 1.04
    cam.data.shift_x = (max(xs) + min(xs)) / 2 / cam.data.ortho_scale
    cam.data.shift_y = (max(ys) + min(ys)) / 2 / cam.data.ortho_scale
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


B.render = render  # contact sheets render matte too

UP = Vector((0, 1, 0))


# =====================================================================================================================
# Shared generators (glTF coordinates, Y up). Material arguments are slot indices into the calling kit's MATS.
# =====================================================================================================================

def basis(fwd, up=UP):
    """Orthonormal frame (forward, up, side) around a direction."""
    f = Vector(fwd).normalized()
    s = f.cross(up)
    if s.length < 1e-4:
        s = f.cross(Vector((1, 0, 0)))
    s.normalize()
    return f, s.cross(f).normalized(), s


def gnarl(pts, amp, seed, keep=1):
    """Nudge a polyline sideways with smooth noise (the first `keep` points stay put) so limbs read as grown."""
    out = []
    for i, p in enumerate(pts):
        if i < keep:
            out.append(p.copy())
            continue
        q = p * 0.35 + Vector((seed, seed * 0.7, seed * 1.3))
        out.append(p + Vector((noise.noise(q), noise.noise(q + Vector((5, 0, 0)))*0.5, noise.noise(q + Vector((0, 0, 9))))) * amp)
    return out


def mass(m, c, r, mat, seed=0.0, rough=0.2, lobe=0.08, rings=6, segs=9, flat=0.6, axes=None, tile=3.0, under=None, under_y=-0.1):
    """Clumped foliage mass: a lat-long ellipsoid displaced by two octaves of noise (broad lobes and leaf clumps),
    with lat-long UVs (`tile` metres per repeat; swatches are soft so the poles do not show).
    `axes` = (x, y, z) world vectors orient it (drooping conifer pads); `flat` squashes the underside.
    `under` paints the faces below latitude `under_y` (sine) with a second material: the cool shadowed underside."""
    c = Vector(c)
    rx, ry, rz = r
    lower = under if under is not None else mat
    ax, ay, az = axes or (Vector((1, 0, 0)), UP, Vector((0, 0, 1)))
    off = Vector((seed * 1.7, seed * 0.31, seed * 0.73))
    off2 = off * 1.9 + Vector((3.1, 7.2, 1.3))

    def pt(phi, th):
        d = Vector((math.cos(phi) * math.cos(th), math.sin(phi), math.cos(phi) * math.sin(th)))
        k = 1 + rough * noise.noise(d * 1.5 + off) + lobe * noise.noise(d * 3.6 + off2)
        y = d.y * ry * k * (flat if d.y < 0 else 1)
        return c + ax * (d.x * rx * k) + ay * y + az * (d.z * rz * k)

    ur = max(1, round(2 * math.pi * max(rx, rz) / tile))
    vr = max(1, round(math.pi * ry / tile))
    rows = []
    for i in range(1, rings):
        phi = -math.pi / 2 + math.pi * i / rings
        row = [(m.vert(pt(phi, 2 * math.pi * j / segs + i * 0.4)), (j / segs * ur, i / rings * vr)) for j in range(segs)]
        rows.append(row + [(row[0][0], (ur, i / rings * vr))])
    for i, (r0, r1) in enumerate(zip(rows, rows[1:])):
        mid = math.sin(-math.pi / 2 + math.pi * (i + 1.5) / rings)
        for j in range(segs):
            wob = 0.12 * math.sin(j * 2.1 + seed * 3)
            m.face((r0[j][0], r0[j + 1][0], r1[j + 1][0], r1[j][0]), (r0[j][1], r0[j + 1][1], r1[j + 1][1], r1[j][1]),
                   lower if mid + wob < under_y else mat)
    bottom, top = m.vert(pt(-math.pi / 2, 0)), m.vert(pt(math.pi / 2, 0))
    for j in range(segs):
        a, b = rows[0][j], rows[0][j + 1]
        m.face((bottom, b[0], a[0]), ((a[1][0], 0), b[1], a[1]), lower)
        a, b = rows[-1][j], rows[-1][j + 1]
        m.face((a[0], b[0], top), (a[1], b[1], (a[1][0], vr)), mat)


def card(m, base, fwd, L, W, mat, fold=0.22, droop=0.18, uv=(0, 0, 1, 1), lobes=4):
    """A leaf-cluster card: a scalloped fan from `base` towards `fwd` (lobes triangles), cupped along its midrib."""
    f, u, s = basis(fwd)
    base = Vector(base)
    u0, v0, u1, v1 = uv
    vb = m.vert(base)
    rim = []
    for k in range(lobes + 1):
        a = -1.25 + 2.5 * k / lobes
        rr = L * (1.0 if k % 2 == 0 else 0.86) * (0.75 + 0.25 * math.cos(a))
        q = base + f * math.cos(a) * rr + s * math.sin(a) * rr * (W / L) - u * (L * droop * math.cos(a) + W * fold * abs(math.sin(a)))
        rim.append((m.vert(q), (u0 + (u1 - u0) * (0.5 + 0.5 * math.sin(a)), v0 + (v1 - v0) * math.cos(a) * 0.9 + 0.1 * (v1 - v0))))
    for k in range(lobes):
        m.face((vb, rim[k + 1][0], rim[k][0]), ((u0 + (u1 - u0) * 0.5, v0), rim[k + 1][1], rim[k][1]), mat)


def sprigs(m, c, r, n, mat, seed, size, low=-0.2, inset=0.88):
    """Leaf sprigs poking out of a mass's surface so the silhouette breaks into serrated leaf clusters."""
    rng = random.Random(seed)
    c = Vector(c)
    for _ in range(n):
        th = rng.uniform(0, 2 * math.pi)
        y = rng.uniform(low, 1.0)
        q = math.sqrt(max(0.0, 1 - y * y))
        d = Vector((q * math.cos(th), y, q * math.sin(th)))
        base = c + Vector((d.x * r[0], d.y * r[1], d.z * r[2])) * inset
        tang = d.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
        out = (d * 0.45 + tang * 0.8 + UP * 0.1).normalized()
        L = size * rng.uniform(0.75, 1.25)
        card(m, base, out, L, L * rng.uniform(0.8, 1.0), mat, fold=0.15, droop=0.25, uv=(rng.uniform(0, 0.4), rng.uniform(0, 0.4), rng.uniform(0.6, 1), rng.uniform(0.6, 1)))


def clump(m, c, s, mats, seed, rings=6, segs=10, sprig_n=4, subs=1, flat=0.7, squash=0.85, rough=0.16, sprig_mat=None, shade=None):
    """A painterly leaf clump: a mass lit on top and cool-shaded beneath, a smaller lobe bulging from its upper side,
    and a few scalloped leaf sprigs lying on top to break the silhouette. `mats` cycles leaf materials; `shade` maps
    a leaf material to its shadow swatch."""
    rng = random.Random(seed)
    c = Vector(c)
    sh = shade or {}
    mass(m, c, (s, s * squash, s), mats[0], seed, rough=rough, rings=rings, segs=segs, flat=flat, under=sh.get(mats[0]), under_y=-0.05)
    for i in range(subs):
        a = rng.uniform(0, 2 * math.pi)
        d = Vector((math.cos(a), rng.uniform(0.5, 1.0), math.sin(a))).normalized()
        ss = s * rng.uniform(0.5, 0.65)
        mt = mats[(i + 1) % len(mats)]
        mass(m, c + Vector((d.x * s * 0.6, d.y * s * squash * 0.6, d.z * s * 0.6)), (ss, ss * squash * 1.05, ss), mt,
             seed + 3.1 * (i + 1), rough=rough, rings=max(4, rings - 1), segs=max(6, segs - 2), flat=flat, under=sh.get(mt), under_y=-0.25)
    if sprig_n:
        sprigs(m, c, (s * 1.0, s * squash * 1.0, s * 1.0), sprig_n, sprig_mat if sprig_mat is not None else mats[0], seed + 11, s * 0.55, low=0.1)


def strands(m, pts, r, mat, count=2, turns=1.3, rel=0.2, seed=0.0, start=0.1, end=0.92, sides=5):
    """Thinner roots spiralling around a main root or trunk so it reads as braided and grown."""
    fr = B.frames(pts)
    n = len(pts)
    radii = r if isinstance(r, list) else [r] * n
    for j in range(count):
        sub, rr = [], []
        for i in range(int(n * start), int(n * end)):
            t = i / (n - 1)
            phi = j * 2 * math.pi / count + turns * 2 * math.pi * t + seed
            _, nn, bb = fr[i]
            sub.append(pts[i] + (nn * math.cos(phi) + bb * math.sin(phi)) * radii[i] * 0.92)
            rr.append(radii[i] * rel * (1.15 - 0.5 * (i - n * start) / max(1, n * (end - start))))
        if len(sub) > 3:
            tube(m, sub, rr, mat, sides, rough=0.15, seed=seed + j, caps=(False, False))


def root(m, start, d, reach, r0, mat, seed, sides=6, n=9, drop=0.3, rise=0.0, r1=None):
    """A buttress or surface root: leaves a trunk at `start`, arcs outward along `d` and dives into the ground."""
    d = Vector((d.x, 0, d.z)).normalized()
    start = Vector(start)
    end = Vector((start.x, 0, start.z)) + d * reach + Vector((0, -drop, 0))
    pts = hermite(start, d * reach * 0.6 + Vector((0, rise - start.y * 0.5, 0)), end, d * reach * 0.9 + Vector((0, -start.y * 0.15, 0)), n)
    pts = gnarl(pts, r0 * 0.5, seed, keep=2)
    r1 = r1 if r1 is not None else r0 * 0.15
    radii = [r0 + (r1 - r0) * (i / n) ** 0.85 for i in range(n + 1)]
    tube(m, pts, radii, mat, sides, twist=0.6, rough=0.2, seed=seed, caps=(False, False))
    return pts, radii


def frond(m, base, out, length, mat, seed, segs=7, width=0.16, rise=0.9, droop=0.55, curl=0.0):
    """A fern frond: an arching spine with saw-toothed leaflets on both sides (a single double-sided sheet)."""
    rng = random.Random(seed)
    out = Vector((out.x, 0, out.z)).normalized()
    base = Vector(base)
    p1 = base + out * length * 0.85 + UP * length * (rise - droop)
    pts = hermite(base, UP * length * rise + out * length * 0.35, p1, out * length * 0.5 - UP * length * droop, segs)
    side = out.cross(UP).normalized()
    spine = [m.vert(p) for p in pts]
    for i in range(segs):
        p, q = pts[i], pts[i + 1]
        t = (q - p).normalized()
        k = (i + 0.5) / segs
        w = width * length * math.sin(math.pi * min(1.0, 0.15 + k)) ** 0.8 * rng.uniform(0.85, 1.1)
        for sgn, (u0, u1) in ((1, (0.0, 0.5)), (-1, (1.0, 0.5))):
            tipp = p + side * sgn * w + t * w * 0.7 - UP * w * (0.35 + curl)
            lv = m.vert(tipp)
            uvs = ((0.5, i / segs), (u0, (i + 0.6) / segs), (0.5, (i + 1) / segs))
            if sgn > 0:
                m.face((spine[i], lv, spine[i + 1]), uvs, mat)
            else:
                m.face((spine[i + 1], lv, spine[i]), uvs[::-1], mat)


def fern(m, c, R, H, mat, seed, count=12, segs=7, width=0.16, centre_mat=None):
    """A rosette of arching fronds around a centre."""
    rng = random.Random(seed)
    c = Vector(c)
    for k in range(count):
        a = 2 * math.pi * k / count + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), 0, math.sin(a)))
        L = R * rng.uniform(0.8, 1.1)
        rise = 1.5 * H / L * rng.uniform(0.85, 1.15)
        frond(m, c + d * R * 0.05, d, L, mat, seed + k, segs, width, rise=rise, droop=rise * 0.45 + 0.1)
    if centre_mat is not None:
        mass(m, c + Vector((0, 0.02, 0)), (R * 0.18, R * 0.12, R * 0.18), centre_mat, seed, rings=4, segs=6, rough=0.3)


def mushroom(m, base, h, cr, cap, gill, stem, seed, lean=(0.0, 0.0), sides=8):
    """Stemmed mushroom: tapered stem, domed cap with a slightly drooping rim and a gill underside."""
    rng = random.Random(seed)
    base = Vector(base)
    top = base + Vector((lean[0] * h, h, lean[1] * h))
    tube(m, [base + Vector((0, -0.05, 0)), base.lerp(top, 0.55) + Vector((lean[0] * 0.1, 0, lean[1] * 0.1)), top],
         [cr * 0.26, cr * 0.2, cr * 0.18], stem, 6, caps=(False, False))
    rings = [(0.0, 0.6), (0.55, 0.5), (0.88, 0.25), (1.0, 0.04), (0.9, -0.04), (0.3, 0.02)]
    vs = []
    for ri, (rr, yy) in enumerate(rings):
        row = []
        for j in range(sides):
            a = 2 * math.pi * j / sides + seed
            wob = 1 + 0.08 * math.sin(a * 3 + seed * 5)
            row.append(m.vert(top + Vector((math.cos(a) * cr * rr * wob, yy * cr + (0.04 * cr * math.sin(a * 2 + seed) if ri == 3 else 0), math.sin(a) * cr * rr * wob))))
        vs.append(row)
    apex = vs[0][0]
    for j in range(sides):
        j1 = (j + 1) % sides
        u0, u1 = j / sides, (j + 1) / sides
        m.face((apex, vs[1][j1], vs[1][j]), ((0.5, 1), (u1, 0.75), (u0, 0.75)), cap)
        for ri in range(1, 5):
            mat = cap if ri < 3 else gill
            m.face((vs[ri][j], vs[ri][j1], vs[ri + 1][j1], vs[ri + 1][j]),
                   ((u0, 0.75 - 0.18 * ri), (u1, 0.75 - 0.18 * ri), (u1, 0.57 - 0.18 * ri), (u0, 0.57 - 0.18 * ri)), mat)


def flower(m, c, r, mat, seed, petals=5):
    """Tiny five-petal flower, a fan of triangles facing up."""
    c = Vector(c)
    centre = m.vert(c + Vector((0, r * 0.15, 0)))
    tips = []
    for k in range(petals * 2):
        a = math.pi * k / petals + seed
        rr = r if k % 2 == 0 else r * 0.35
        tips.append(m.vert(c + Vector((math.cos(a) * rr, 0, math.sin(a) * rr))))
    for k in range(petals * 2):
        m.face((centre, tips[(k + 1) % (petals * 2)], tips[k]), ((0.5, 0.5), (1, 1), (0, 1)), mat)


def flowers(m, c, R, n, mat, seed, r=0.07, y=0.02):
    rng = random.Random(seed)
    for k in range(n):
        a, d = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.random())
        flower(m, Vector(c) + Vector((math.cos(a) * d, y + rng.uniform(0, 0.04), math.sin(a) * d)), r * rng.uniform(0.7, 1.2), mat, k + seed)


def hull(m, pts, mat, tile=1.5, bevel=0.0):
    """Convex hull of points as chunky flat facets (box-projected UVs). `bevel` chamfers every hull edge by that
    width so the stone reads as chiselled rather than as a low-poly sphere."""
    before = set(m.bm.faces)
    verts = [m.vert(p) for p in pts]
    res = bmesh.ops.convex_hull(m.bm, input=verts)
    loose = list({v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert) and v.is_valid and not v.link_faces})
    if loose:
        bmesh.ops.delete(m.bm, geom=loose, context="VERTS")
    new = [f for f in m.bm.faces if f not in before]
    if bevel > 0:
        edges = list({e for f in new for e in f.edges})
        # only chamfer the sharper edges, so big flat facets stay flat
        sharp = [e for e in edges if len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) > math.radians(25)]
        if sharp:
            bmesh.ops.bevel(m.bm, geom=sharp, offset=bevel, segments=1, affect="EDGES", clamp_overlap=True)
        new = [f for f in m.bm.faces if f not in before]
    for g in new:
        g.material_index = mat
        m.project.append((g, tile))


def boulder(m, c, size, mat, seed, n=22, round_=0.6, rot=0.0, tile=1.5, sink=0.12, bevel=None, base=-0.55):
    """Chunky boulder: hull of evenly spread points on a superellipsoid (round_ = 1 round, 0.3 blocky) with noisy
    radii and a flattened base, edges chamfered."""
    c = Vector(c)
    w, h, d = size
    ca, sa = math.cos(rot), math.sin(rot)
    golden = math.pi * (3 - math.sqrt(5))
    off = Vector((seed, seed * 0.7, seed * 1.3))
    e = max(0.25, round_)
    pts = []
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        q = math.sqrt(max(0.0, 1 - y * y))
        a = golden * i + seed
        v = Vector((math.cos(a) * q, y, math.sin(a) * q))
        v = Vector(tuple(math.copysign(abs(x) ** e, x) for x in v))
        v *= 1 + 0.16 * noise.noise(v * 1.3 + off)
        v.y = max(v.y, base)
        x, yy, z = v.x * w / 2, (v.y - base) / (1 - base) * (h + sink) - sink, v.z * d / 2
        pts.append(c + Vector((x * ca - z * sa, yy, x * sa + z * ca)))
    hull(m, pts, mat, tile, bevel if bevel is not None else min(w, h, d) * 0.06)


def plate(m, c, size, mat, seed, rot=0.0, tilt=(0.0, 0.0), chip=0.18, tile=1.5):
    """A slab of split stone: a box with chipped corners and a slight tilt."""
    rng = random.Random(seed)
    c = Vector(c)
    w, h, d = size
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            for sy in (-1, 1):
                k = 1 - chip * rng.random()
                x, z = sx * w / 2 * k, sz * d / 2 * (1 - chip * rng.random())
                y = sy * h / 2 * rng.uniform(0.8, 1.0) + x * tilt[0] + z * tilt[1]
                pts.append(c + Vector((x * ca - z * sa, y, x * sa + z * ca)))
            # chipped edge points midway along the long sides
            x = rng.uniform(-0.4, 0.4) * w
            z = sz * d / 2 * rng.uniform(0.85, 1.0)
            for sy in (-1, 1):
                y = sy * h / 2 * rng.uniform(0.7, 1.0) + x * tilt[0] + z * tilt[1]
                pts.append(c + Vector((x * ca - z * sa, y, x * sa + z * ca)))
    hull(m, pts, mat, tile, min(h, w, d) * 0.12)


def ribbon(m, top, length, width, mat, seed, segs=4, sway=0.15, out=None):
    """A hanging strand of moss (a double-sided foliage strip with a ragged edge) dropping from `top`."""
    rng = random.Random(seed)
    top = Vector(top)
    out = Vector(out) if out is not None else Vector((rng.uniform(-1, 1), 0, rng.uniform(-1, 1))).normalized()
    side = out.cross(UP).normalized()
    prev = None
    for i in range(segs + 1):
        t = i / segs
        p = top + Vector((0, -length * t, 0)) + out * (sway * length * t * t) + side * math.sin(t * 3 + seed) * sway * 0.4
        w = width * (1 - 0.75 * t) * (1 + 0.3 * rng.uniform(-1, 1))
        pair = (m.vert(p - side * w / 2), m.vert(p + side * w / 2))
        if prev:
            m.face((prev[0], prev[1], pair[1], pair[0]), ((0, (i - 1) / segs), (1, (i - 1) / segs), (1, t), (0, t)), mat)
        prev = pair


def sweep(m, pts, widths, thick, side, mat, sides=6, uv_len=2.0):
    """Flattened tube with an explicit side axis (ribbons of falling water, flat logs)."""
    side = Vector(side).normalized()
    rings = []
    s = 0.0
    for i, (p, w) in enumerate(zip(pts, widths)):
        if i:
            s += (pts[i] - pts[i - 1]).length
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = side.cross(t).normalized()
        ring = []
        for k in range(sides + 1):
            a = 2 * math.pi * k / sides
            q = p + side * math.cos(a) * w / 2 + nrm * math.sin(a) * thick / 2
            ring.append((m.vert(q), (k / sides, s / uv_len)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            m.face((r0[k][0], r0[k + 1][0], r1[k + 1][0], r1[k][0]), (r0[k][1], r0[k + 1][1], r1[k + 1][1], r1[k][1]), mat)


def hollow_log(m, length, r, bark, inner, cap, seed, splinter=0.6, sides=10, n=8, sag=0.0, open_end=True):
    """Fallen hollow trunk along X: outer bark shell, inner wall, end-grain rim at the open end and a jagged
    splintered break at the other (+X) end."""
    rng = random.Random(seed)
    pts = [Vector((-length / 2 + length * i / n, r * 0.92 - sag * math.sin(math.pi * i / n), 0)) for i in range(n + 1)]
    radii = [r * (1.08 - 0.12 * i / n) for i in range(n + 1)]
    outer = tube(m, pts, radii, bark, sides, twist=0.3, rough=0.1, seed=seed, caps=(False, False))
    inner_r = [x * 0.72 for x in radii]
    inn = tube(m, pts[:-2], inner_r[:-2], inner, sides, caps=(False, False))
    # rim at the open end (-X): join outer ring 0 to inner ring 0 with end grain
    for k in range(sides):
        a, b = outer[0][k][0], outer[0][k + 1][0]
        c, d = inn[0][k + 1][0], inn[0][k][0]
        m.face((a, b, c, d), ((0, 0), (1, 0), (1, 0.3), (0, 0.3)), cap)
    # splintered far end: spikes of raw wood rising from the last outer ring, and a closing plug inside
    last = outer[-1]
    tipc = pts[-1]
    for k in range(sides):
        v0, v1 = last[k][0], last[k + 1][0]
        p0 = Vector(v0.co)  # Blender coords; convert back to glTF for new verts
        p0 = Vector((p0.x, p0.z, -p0.y))
        p1 = Vector((v1.co.x, v1.co.z, -v1.co.y))
        mid = (p0 + p1) / 2
        spike = mid + Vector((rng.uniform(0.2, 1.0) * splinter, 0, 0)) + (tipc - mid) * rng.uniform(0.15, 0.45)
        sv = m.vert(spike)
        m.face((v0, v1, sv), ((0, 0), (1, 0), (0.5, 1)), cap)
        ci = m.vert(tipc + Vector((-0.05, 0, 0)) + (mid - tipc) * 0.7)
        m.face((v1, v0, ci), ((0, 0), (1, 0), (0.5, 1)), cap)
    plug = m.vert(pts[-3] + Vector((r * 0.1, 0, 0)))
    ring = inn[-1]
    for k in range(sides):
        m.face((ring[k + 1][0], ring[k][0], plug), ((0, 0), (1, 0), (0.5, 0.5)), inner)
    return pts, radii


def lip_edge(m, W, D, H, turf, rim, cliff, seed, notch=None, overhang=0.55, segs=16):
    """Isle edge segment along X (-W/2..W/2): flat turf flush with the ground at y = H at the back (-Z), a rounded
    overhanging moss rim at the front (+Z) curling back under into a soil shelf; callers stack chunky rock below. Noise fades to zero at
    both X ends so neighbouring segments tile. `notch` = x position of a dip in the turf for a waterfall."""
    prof = [(-D / 2, H, turf), (-D / 4, H, turf), (0.0, H, turf), (D / 2 - 0.45, H - 0.02, turf), (D / 2 - 0.05, H - 0.12, rim),
            (D / 2 + overhang * 0.75, H - 0.38, rim), (D / 2 + overhang, H - 0.75, rim), (D / 2 + overhang * 0.6, H - 1.05, rim),
            (D / 2 + 0.05, H - 1.3, cliff), (D / 2 - 0.6, H - 1.6, cliff), (D / 2 - 1.2, H - 1.9, cliff)]
    grid = []
    for j in range(segs + 1):
        x = -W / 2 + W * j / segs
        fade = math.sin(math.pi * j / segs) ** 0.6
        row = []
        for i, (z, y, mat) in enumerate(prof):
            q = Vector((x * 0.45, y * 0.6, seed))
            n1 = noise.noise(q)
            n2 = noise.noise(q * 2.7 + Vector((4, 1, 0)))
            dz = dy = 0.0
            if i >= 4:  # rim and cliff bulge and step
                dz = (0.35 * n1 + 0.18 * n2) * fade
                if mat == cliff:
                    dz += 0.22 * (abs(n2) - 0.3) * fade
                    dy = 0.15 * n1 * fade
            elif i >= 1:
                dy = 0.04 * n2 * fade
            if notch is not None and i <= 6:
                k = max(0.0, 1 - abs(x - notch) / 0.7)
                dy -= 0.3 * k * k * (1 if i >= 2 else 0.4)
                if i >= 4:
                    dz -= 0.25 * k * k
            row.append((m.vert((x, y + dy, z + dz)), mat))
        grid.append(row)
    for j in range(segs):
        for i in range(len(prof) - 1):
            a, b, c, d = grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]
            mat = a[1] if a[1] == c[1] else (prof[i][2] if i < 4 else rim)
            m.face((a[0], d[0], c[0], b[0]), None, mat, 2.0)
    return prof


def underside_core(m, W, H, mat, seed, segs=14, tiers=7, lumps=0.22, hole=None, D=None):
    """Isle underside: an irregular inverted cone from an outline of width W at y = H down to a point at y = 0.
    `hole` = (y, radius) punches a round tunnel through along Z (faces inside it are skipped; add a lining)."""
    D = D or W
    rings = []
    for i in range(tiers + 1):
        t = i / tiers
        y = H * (1 - t)
        shrink = (1 - t) ** 0.75 if i < tiers else 0.0
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            n = 1 + lumps * noise.noise(Vector((math.cos(a) * 1.5, t * 3.5, math.sin(a) * 1.5 + seed)))
            sx = 0.5 * t * t * math.sin(seed)
            ring.append(m.vert((math.cos(a) * W / 2 * shrink * n + sx, y, math.sin(a) * D / 2 * shrink * n)))
        rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for j in range(segs):
            j1 = (j + 1) % segs
            if hole is not None:
                cs = [Vector(v.co) for v in (r0[j], r0[j1], r1[j1], r1[j])]
                cx = sum(c.x for c in cs) / 4
                cy = sum(c.z for c in cs) / 4  # Blender z = glTF y
                if (cx * cx + (cy - hole[0]) ** 2) < (hole[1] * 1.05) ** 2:
                    continue
            m.face((r0[j], r0[j1], r1[j1], r1[j]), None, mat, 2.5)
    m.face(rings[0][::-1], None, mat, 2.5)
    return rings


def post(ob, fn=None, flat=(), up=(), inward=None, facing=None):
    """Per-face material painting and shading after the object is built.
    fn(material, centre, normal) -> new material or None, in glTF coordinates. `flat` materials get flat shading
    (facets). Faces in `up` materials are turned to face up (cards lying on the ground). `inward` = (centre, axis,
    radius): faces near that tunnel axis are turned to face it."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        cg, ng = Vector((c.x, c.z, -c.y)), Vector((n.x, n.z, -n.y))
        if f.material_index in up and ng.y < 0:
            f.normal_flip()
        elif facing and f.material_index in facing and ng.dot(facing[f.material_index]) < 0:
            f.normal_flip()
        if inward is not None:
            o, ax, rad = inward
            rel = cg - o
            radial = rel - ax * rel.dot(ax)
            if radial.length < rad * 1.25 and abs(rel.dot(ax)) < 20 and ng.dot(radial) > 0:
                f.normal_flip()
        if fn:
            r = fn(f.material_index, cg, ng)
            if r is not None:
                f.material_index = r
        f.smooth = f.material_index not in flat
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def tree_paint(leaf_shade, crown_c, crown_r, bark=(), moss=None, north=True, up_moss=0.55, seed=0.0):
    """Painting rule for trees: leaf faces turned down or inward take the cool shade swatch; bark facing up (and the
    north side, -Z) takes moss."""
    cc = Vector(crown_c)

    def fn(mi, c, n):
        if mi in leaf_shade:
            rel = c - cc
            k = noise.noise(c * 0.45 + Vector((seed, 0, 0)))
            if n.y < -0.55 + 0.2 * k or (rel.y < -crown_r * 0.2 and n.dot(rel) < -0.3):
                return leaf_shade[mi]
            return None
        if moss is not None and mi in bark:
            k = noise.noise(c * 0.7 + Vector((0, seed, 0)))
            if (n.y > up_moss + 0.1 and k > 0.15) or (north and n.z < -0.7 and k > 0.3 and c.y < 6):
                return moss
        return None
    return fn


def crown_clumps(m, rng, cc, R, leaves, shade, seed, n, s, rings, segs, ends=(), squash=0.85, sprig_n=0, low=-0.35, shell=0.72):
    """Overlapping leaf clumps spread evenly over the upper part of an ellipsoid crown (and on `ends`, the branch
    tips), lit on top and shaded beneath; lower clumps take more shade."""
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    k = 0
    i = 0
    while len(pts) < n and i < n * 4:
        y = 1 - 2 * (i + 0.5) / (n * 2.2 / (1 - low) * 1.0 + 1e-6)
        i += 1
        if y < low:
            break
        q = math.sqrt(max(0.0, 1 - y * y))
        a = golden * i + seed
        d = Vector((math.cos(a) * q, y, math.sin(a) * q))
        jit = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.08
        pts.append(cc + Vector(((d.x + jit.x) * R[0] * shell, (d.y + jit.y) * R[1] * shell, (d.z + jit.z) * R[2] * shell)))
        k += 1
    pts += [Vector(e) for e in ends]
    pts.append(cc)
    for j, p in enumerate(pts):
        h = (p.y - cc.y) / R[1]
        size = s * rng.uniform(0.85, 1.15) * (1.15 if j == len(pts) - 1 else 1.0)
        mt = leaves[j % len(leaves)]
        sh = (shade or {}).get(mt)
        mass(m, p, (size, size * squash, size), mt, seed + j * 1.37, rough=0.14, lobe=0.06, rings=rings, segs=segs, flat=0.85,
             under=sh, under_y=-0.25 + 0.35 * max(0.0, -h))
        if sprig_n:
            sprigs(m, p, (size, size * squash, size), sprig_n, mt, seed + j, size * 0.5, low=0.2)
    return pts


def broad_tree(m, rng, H, W, ch, tr, bark, leaves, *, cap=None, lean=(0.0, 0.0), fork=0.45, limbs=4, subs=2, roots=5,
               reach=None, gap=None, braid=0, fill=4, mass_size=0.24, sprig_n=7, rings=6, segs=9, trunk_sides=10,
               trunk_n=10, root_sides=6, limb_sides=6, sub_sides=5, dead=0, root_bark=None, seed=0.0, crown_y=None,
               lift=0.0, squash=0.85, limb_r=0.62, root_h=0.12, flare=1.1, strand_sides=5, shade=None, sub_mass=1, clumps=6, lobe_n=4, lobe_r=0.17, top_r=0.22, root_strands=True, limb_n=9, root_n=9):
    """Broadleaf tree: flaring, gnarled trunk (optionally braided), buttress roots, limbs that split into
    sub-branches, and a crown of clumped leaf masses at the branch ends plus fill clumps over the dome.
    Returns (crown centre, crown radius, trunk points, trunk radii, crown clump centres)."""
    lean = Vector((lean[0], 0, lean[1]))
    crown_y = crown_y if crown_y is not None else H - ch * 0.55
    cc = Vector((lean.x * H, crown_y, lean.z * H))
    F = Vector((lean.x * H * 0.5, H * fork, lean.z * H * 0.5))
    tdir = (cc - F).normalized() + UP
    trunk = hermite((0, -0.4, 0), (0, H * fork * 0.9, 0), F, tdir.normalized() * H * fork * 0.7, trunk_n)
    trunk = gnarl(trunk, tr * 0.35, seed, keep=2)
    tr_r = [tr * (1 + flare * math.exp(-i / trunk_n * 9)) * (1 - 0.32 * i / trunk_n) for i in range(trunk_n + 1)]
    tube(m, trunk, tr_r, bark, trunk_sides, twist=1.2, rough=0.16, seed=seed, caps=(False, True))
    if braid:
        strands(m, trunk, tr_r, bark, braid, turns=0.9, rel=0.32, seed=seed, start=0.05, end=0.85, sides=strand_sides)
    # roots
    reach = reach or tr * 4
    rb = root_bark if root_bark is not None else bark
    for k in range(roots):
        a = 2 * math.pi * k / roots + seed + rng.uniform(-0.25, 0.25)
        if gap is not None and abs((a - gap[0] + math.pi) % (2 * math.pi) - math.pi) < gap[1]:
            continue
        d = Vector((math.cos(a), 0, math.sin(a)))
        st = Vector((0, H * root_h * rng.uniform(0.8, 1.2), 0)) + d * tr * 0.45
        pts, rr = root(m, st, d, reach * rng.uniform(0.7, 1.0), tr * rng.uniform(0.6, 0.8), rb, seed + k * 1.7, root_sides, root_n, r1=tr * 0.22)
        if braid and root_strands:
            strands(m, pts, rr, rb, 1, turns=0.7, rel=0.35, seed=seed + k, start=0.0, end=0.7, sides=4)
    # limbs: leave the upper trunk at a low angle, then turn up into the crown
    ends = []
    for k in range(limbs):
        a = 2 * math.pi * k / limbs + seed * 2.3 + rng.uniform(-0.3, 0.3)
        out = Vector((math.cos(a), 0, math.sin(a)))
        si = rng.randint(int(trunk_n * 0.7), trunk_n)
        start = trunk[si]
        rad = rng.uniform(0.6, 0.82)
        T = cc + Vector((out.x * W / 2 * rad, (0.2 - 0.6 * rad * rad + rng.uniform(-0.08, 0.08)) * ch + lift, out.z * W / 2 * rad))
        L = (T - start).length
        pts = hermite(start, (out * 0.85 + UP * 0.55).normalized() * L * 0.8, T, (out * 0.45 + UP * 0.6).normalized() * L * 0.6, limb_n)
        pts = gnarl(pts, tr * 0.45, seed + k * 3.3, keep=1)
        lr = [tr * limb_r * (1 - 0.72 * i / limb_n) for i in range(limb_n + 1)]
        is_dead = k < dead
        tube(m, pts, lr, bark, limb_sides, twist=0.6, rough=0.15, seed=seed + 10 + k, caps=(False, is_dead))
        if is_dead:
            # bare broken limb: a couple of snapped twigs, no leaves
            for j in range(2):
                b0 = pts[rng.randint(limb_n // 2, limb_n - 1)]
                T2 = b0 + (out * rng.uniform(0.5, 1.0) + UP * rng.uniform(0.2, 0.9) + Vector((rng.uniform(-0.5, 0.5), 0, rng.uniform(-0.5, 0.5)))).normalized() * W * 0.12
                tube(m, hermite(b0, (T2 - b0) * 0.8, T2, (T2 - b0) * 0.8, 4), [tr * 0.16, tr * 0.12, tr * 0.09, tr * 0.07, tr * 0.06], bark, 4,
                     rough=0.2, seed=seed + j, caps=(False, True))
            continue
        ends.append((T, 1.0))
        for j in range(subs):
            bi = rng.randint(limb_n // 2 - 1, limb_n - 2)
            b0 = pts[bi]
            side = out.cross(UP) * (1 if j % 2 else -1)
            T2 = b0 + (side * rng.uniform(0.5, 0.9) + out * rng.uniform(0.2, 0.6) + UP * rng.uniform(0.5, 0.9)).normalized() * W * rng.uniform(0.18, 0.26)
            L2 = (T2 - b0).length
            p2 = hermite(b0, (T2 - b0).normalized() * L2 * 0.6 + UP * L2 * 0.2, T2, (T2 - b0).normalized() * L2 * 0.5, 5)
            tube(m, gnarl(p2, tr * 0.2, seed + 20 + k * 5 + j, keep=1), [lr[bi] * 0.55 * (1 - 0.65 * i / 5) for i in range(6)], bark, sub_sides,
                 rough=0.15, seed=seed + 30 + j, caps=(False, False))
            ends.append((T2, 0.85))
    # crown lobes (ellipsoids the caller covers with leaf cards): a big lobe at each main limb end, smaller ones on the
    # sub-branch tips, a broad top lobe over the centre and `fill` lobes bridging between neighbouring limb lobes, so
    # the crown reads as a few clumped masses with depth rather than one ball
    crown = []
    mains = []
    for T, k in ends:
        if k >= 1.0:
            rl = W * lobe_r * rng.uniform(0.85, 1.1)
            crown.append((T + UP * rl * 0.2, (rl, rl * squash, rl)))
            mains.append(T)
        else:
            rs = W * lobe_r * rng.uniform(0.62, 0.78)
            crown.append((T + UP * rs * 0.15, (rs, rs * squash, rs)))
    rt = W * top_r
    crown.append((cc + Vector((0, ch * 0.12 + lift, 0)), (rt, rt * squash * 0.8, rt)))
    if fill and len(mains) > 1:
        mains.sort(key=lambda T: math.atan2(T.z - cc.z, T.x - cc.x))
        for i in range(min(fill, len(mains))):
            a, b = mains[i], mains[(i + 1) % len(mains)]
            mid = (a + b) / 2
            mid = cc + (mid - cc) * 0.8 + UP * (ch * 0.08 + lift)
            rf = W * lobe_r * rng.uniform(0.7, 0.85)
            crown.append((mid, (rf, rf * squash, rf)))
    return cc, max(W, ch) / 2, trunk, tr_r, crown


def conifer_tree(m, rng, H, W, tr, bark, needles, *, tiers=8, pads=(7, 3), start=0.22, droop=0.35, pad_w=0.5, pad_t=0.16,
                 rings=4, segs=8, trunk_sides=10, roots=5, reach=None, root_bark=None, bend=(0.0, 0.0), seed=0.0, sprig_n=0,
                 top_frac=0.08, clumpy=0.0, trunk_top=0.97, gaps=0.0, flare=1.0, pad_reach=1.0, shade=None, root_r=0.55):
    """Conifer with layered tiers of drooping, lobed foliage pads radiating from the trunk, narrowing to a spire.
    `pads` = (bottom count, top count) per tier; `clumpy` adds rounded lumps on each pad (pines)."""
    tip = Vector((bend[0] * H, H * trunk_top, bend[1] * H))
    n = 12
    trunk = hermite((0, -0.4, 0), (0, H * 0.6, 0), tip, Vector((bend[0] * 2, 1, bend[1] * 2)).normalized() * H * 0.5, n)
    trunk = gnarl(trunk, tr * 0.2, seed, keep=2)
    tube(m, trunk, [tr * (1 + 0.9 * flare * math.exp(-i / n * 10)) * (1.05 - 0.95 * i / n) for i in range(n + 1)], bark, trunk_sides,
         twist=0.8, rough=0.14, seed=seed, caps=(False, True))
    reach = reach or tr * 4
    rb = root_bark if root_bark is not None else bark
    for k in range(roots):
        a = 2 * math.pi * k / roots + seed + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), 0, math.sin(a)))
        root(m, Vector((0, tr * 1.6, 0)) + d * tr * 0.4, d, reach * rng.uniform(0.7, 1.0), tr * root_r, rb, seed + k, 5, 7, r1=tr * 0.15)
    for t_i in range(tiers):
        f = t_i / max(1, tiers - 1)
        y = H * (start + (1 - start - top_frac) * f)
        # trunk point at this height
        idx = min(n, max(0, int(round(y / (H * trunk_top) * n))))
        tc = trunk[idx].copy()
        tc.y = y
        R = W / 2 * (1 - 0.82 * f) * rng.uniform(0.9, 1.08) * pad_reach
        count = max(2, round(pads[0] + (pads[1] - pads[0]) * f))
        for k in range(count):
            if gaps and rng.random() < gaps:
                continue
            a = 2 * math.pi * k / count + t_i * 0.9 + rng.uniform(-0.25, 0.25)
            out = Vector((math.cos(a), -droop * rng.uniform(0.7, 1.2) * (1.3 - 0.6 * f), math.sin(a))).normalized()
            L = R * rng.uniform(0.8, 1.1)
            fwd, upv, side = basis(out)
            c = tc + out * L * 0.5 + upv * L * 0.05
            rr = (L * 0.55, max(L * pad_t, W * 0.06), max(L * pad_w * 0.5, W * 0.08))
            nm = needles[(t_i + k) % len(needles)]
            mass(m, c, rr, nm, seed + t_i * 7.1 + k, rough=0.25, lobe=0.15, rings=rings, segs=segs,
                 flat=0.55, axes=(fwd, upv, side), tile=2.5, under=(shade or {}).get(nm), under_y=-0.2)
            if clumpy:
                for j in range(int(clumpy)):
                    q = c + fwd * L * rng.uniform(-0.2, 0.35) + upv * L * pad_t * 0.6 + side * L * pad_w * rng.uniform(-0.25, 0.25)
                    s = L * rng.uniform(0.22, 0.3)
                    nm = needles[(t_i + k + j + 1) % len(needles)]
                    mass(m, q, (s, s * 0.65, s), nm, seed + t_i * 3 + k * 1.3 + j, rough=0.25,
                         lobe=0.12, rings=4, segs=7, flat=0.6, tile=2.5, under=(shade or {}).get(nm), under_y=-0.2)
            if sprig_n:
                sprigs(m, c, rr, sprig_n, needles[0], seed + t_i + k * 0.37, L * 0.3, low=-0.1)
    if not tiers:
        return trunk  # bare trunk and roots: the caller dresses it (conifer_cards)
    # spire
    top = trunk[-1] + Vector((0, H * (1 - trunk_top) + H * 0.02, 0))
    mass(m, top - Vector((0, H * 0.06, 0)), (W * 0.06, H * 0.08, W * 0.06), needles[0], seed + 99, rough=0.2, rings=5, segs=7, flat=0.8, under=(shade or {}).get(needles[0]))
    return trunk


# ---------- alpha-cutout card foliage (painted sprite atlases in art/textures/foliage, see naturelib) ----------

def tri_count(m):
    return sum(len(f.verts) - 2 for f in m.bm.faces)


def _lobe_area(r):
    rx, ry, rz = r
    return 4 * math.pi * (rx * ry + rx * rz + ry * rz) / 3


def card_lobes(m, lobes, mat, cards, size, centre, seed, up_bias=0.35, scale=1.0):
    """naturelib.card_crown spending about `cards` cards over `lobes` (scaled by `scale`)."""
    if cards <= 0 or not lobes:
        return
    lb = [(Vector(c), (r[0] * scale, r[1] * scale, r[2] * scale)) for c, r in lobes]
    area = sum(_lobe_area(r) for _, r in lb)
    # card_crown floors every lobe at 6 cards; aim a little under so rounding stays inside the budget
    dens = max(0.0, (cards - 0) * 10 / area)
    N.card_crown(m, lb, mat, seed=seed, density=dens, size=size, crown_centre=centre, up_bias=up_bias)


def crown_bumps(lobes, n, seed, k=0.5):
    """Smaller clump lobes bulging from the upper and outer surface of each crown lobe, so the crown's outline and
    lighting break into clumped leaf masses instead of smooth balls."""
    rng = random.Random(seed)
    out = []
    for c, (rx, ry, rz) in lobes:
        c = Vector(c)
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            y = rng.uniform(-0.15, 0.85)
            q = math.sqrt(max(0.0, 1 - y * y))
            s = rng.uniform(0.8, 1.15) * k
            out.append((c + Vector((math.cos(a) * q * rx * 0.85, y * ry * 0.85, math.sin(a) * q * rz * 0.85)), (rx * s, ry * s * 1.1, rz * s)))
    return out


def fill_crown(m, lobes, mat, budget, size, centre, seed, dark=None, dark_share=0.2, glow=None, glow_n=0, up_bias=0.35, bumps=0):
    """Spend what is left of the triangle `budget` on leaf cards over the crown lobes: the main sprite on every lobe,
    a share of darker cards a little deeper inside the lower lobes (depth under the sunlit masses) and optionally a
    few glowing cards over the top lobes. `bumps` clump lobes are added on every lobe's surface."""
    if bumps:
        lobes = [(c, (r[0] * 0.92, r[1] * 0.92, r[2] * 0.92)) for c, r in lobes] + crown_bumps(lobes, bumps, seed)
    free = max(0, (budget - tri_count(m)) // 2 - 8)
    if os.environ.get("CARD_DEBUG"):
        print(f"[cards] wood {tri_count(m)} tris, {free} cards over {len(lobes)} lobes")
    cy = Vector(centre).y
    low = [lb for lb in lobes if Vector(lb[0]).y <= cy + 0.05 * abs(cy)]
    nd = int(free * dark_share) if dark is not None and low else 0
    ng = glow_n if glow is not None else 0
    main = free - nd - ng
    # first pass slightly under target, then top up with whatever the 6-per-lobe floor and rounding left over
    card_lobes(m, lobes, mat, int(main * 0.93), size, centre, seed, up_bias)
    if nd:
        card_lobes(m, low, dark, nd, (size[0] * 0.9, size[1] * 0.9), centre, seed + 7, up_bias, scale=0.85)
    if ng:
        top = sorted(lobes, key=lambda lb: -Vector(lb[0]).y)[:max(2, len(lobes) // 3)]
        card_lobes(m, top, glow, ng, (size[0] * 0.8, size[1] * 0.9), centre, seed + 11, up_bias + 0.4, scale=1.02)
    left = (budget - tri_count(m)) // 2
    if left > 6:
        outer = sorted(lobes, key=lambda lb: -(Vector(lb[0]) - Vector(centre)).length)[:max(1, len(lobes) // 2)]
        card_lobes(m, outer, mat, left - 6, size, centre, seed + 13, up_bias)
    # trim any overshoot from the per-lobe floors (cards are the last faces added)
    over = tri_count(m) - budget
    if over > 0:
        faces = list(m.bm.faces)[-((over + 1) // 2):]
        for f in faces:
            m.keep.discard(f)
        bmesh.ops.delete(m.bm, geom=faces, context="FACES_ONLY")
        loose = [v for v in m.bm.verts if not v.link_faces]
        for v in loose:
            m.normals.pop(v, None)
        bmesh.ops.delete(m.bm, geom=loose, context="VERTS")


def spray_card(m, rng, at, out, s, mat, tilt, sink=0.32, normal=None, pick=None):
    """A drooping conifer spray card hanging from a branch point `at` along horizontal direction `out`: the sprite's
    twig (drawn along its top edge, base at the left in quadrants 0 and 2, at the right in 1 and 3) runs outward
    from the trunk, the needles hang below, and the card is rolled by `tilt` radians about the branch."""
    h = Vector((out.x, 0, out.z)).normalized()
    side = h.cross(UP).normalized()
    q = pick if pick is not None else rng.randrange(4)
    uv0 = N._quadrant(rng, 2, q)
    dip = Vector(out).normalized()
    right = (dip if q in (0, 2) else -dip)
    up = (UP * math.cos(tilt) + side * math.sin(tilt))
    up = (up - right * up.dot(right)).normalized()
    centre = Vector(at) + dip * s * 0.45 - up * s * sink
    N._card(m, centre, right, up, s, s, mat, uv0, normal=normal or (h * 0.6 + UP * 0.7).normalized())


def conifer_cards(m, rng, H, W, trunk, mat, budget, *, start=0.18, top_frac=0.06, tiers=9, droop=0.35, tilt=(0.3, 0.9),
                  size=0.75, seed=0.0, top_n=10, layer=0.12, ragged=0.2, dark=None, sink=0.32, inner=0.12):
    """Card conifer crown: tiers of overlapping spray cards radiating from the trunk, drooping with distance, the
    tier radius narrowing to a spire of upright cards. Card counts per tier are scaled so the whole tree spends the
    triangle budget that is left. `tilt` = (min, max) roll of the sprays off vertical (flat cedar tiers roll more)."""
    trunk_top = trunk[-1].y
    free = max(0, (budget - tri_count(m)) // 2 - top_n - 6)
    ys, Rs = [], []
    for t_i in range(tiers):
        f = t_i / max(1, tiers - 1)
        ys.append(H * (start + (1 - start - top_frac) * f))
        Rs.append(W / 2 * (1 - 0.86 * f ** 0.95) * rng.uniform(0.92, 1.06))
    wts = [R ** 1.05 + W * 0.06 for R in Rs]
    tot = sum(wts)
    for t_i, (y, R) in enumerate(zip(ys, Rs)):
        f = t_i / max(1, tiers - 1)
        n = max(10, int(free * wts[t_i] / tot))
        idx = min(len(trunk) - 1, max(0, int(round(y / trunk_top * (len(trunk) - 1)))))
        tc = trunk[idx].copy()
        tc.y = y
        golden = math.pi * (3 - math.sqrt(5))
        arms = max(5, int(n / 3))
        reach = [1 + ragged * rng.uniform(-1, 1) for _ in range(arms)]  # some branches longer: a ragged tier outline
        for k in range(n):
            a = golden * k + t_i * 1.3 + rng.uniform(-0.15, 0.15)
            arm = int((a % (2 * math.pi)) / (2 * math.pi) * arms) % arms
            h = Vector((math.cos(a), 0, math.sin(a)))
            r = R * reach[arm] * (inner + (1 - inner) * rng.random() ** 0.6)
            dropk = droop * (1.25 - 0.5 * f)
            at = tc + h * r * 0.55 + UP * (rng.uniform(-1, 1) * layer * R - dropk * r * 0.35 * (r / max(R, 1e-3)))
            out = (h - UP * dropk * 0.6).normalized()
            s = (R * size * rng.uniform(0.8, 1.1) * (0.6 + 0.4 * r / R)) + 0.25
            tl = rng.uniform(*tilt) * (1 - 0.4 * f) * (1 if rng.random() < 0.5 else -1)  # upper sprays hang steeper
            # inner sprays sit in the tier's own shade, the outer tips catch the light: each tier reads as a layer
            nrm = (h * 0.75 + UP * (-0.35 + 1.1 * r / max(R, 1e-3) - 0.2 * (1 - f))).normalized()
            spray_card(m, rng, at, out, s, mat if (dark is None or rng.random() > 0.22 or r > R * 0.7) else dark, tl, sink=sink, normal=nrm)
    # spire: upright sprays fanning round the leader
    tip = trunk[-1] + UP * H * 0.03
    for k in range(top_n):
        a = 2.4 * k + rng.uniform(-0.2, 0.2)
        h = Vector((math.cos(a), 0, math.sin(a)))
        y = tip.y - H * (top_frac + 0.04) * (k / top_n) ** 0.8
        s = W * 0.07 * (0.5 + 0.8 * k / top_n) + 0.35
        at = Vector((tip.x, y, tip.z))
        out = (h * 0.7 + UP * (0.7 - 0.5 * k / top_n)).normalized()
        spray_card(m, rng, at, out, s, mat, rng.uniform(-0.6, 0.6), sink=0.28, normal=(h * 0.5 + UP * 0.8).normalized())


def fern_cards(m, rng, c, R, H, mat, seed, count=10, inner=0, flat=0.0):
    """Fern rosette from frond cards: each card stands in a vertical plane through the centre, its frond (stem at
    the sprite's bottom, curving to the right) arching outward, leaned out and rolled a little so the rosette also
    reads from above. `inner` adds smaller upright fronds in the heart."""
    c = Vector(c)
    for k in range(count + inner):
        ring = k < count
        a = (2 * math.pi * k / count if ring else 2 * math.pi * (k - count) / max(1, inner) + 0.7) + rng.uniform(-0.25, 0.25)
        out = Vector((math.cos(a), 0, math.sin(a)))
        side = out.cross(UP)
        beta = (rng.uniform(0.35, 0.6) + flat) if ring else rng.uniform(0.1, 0.3)
        up = (UP * math.cos(beta) + out * math.sin(beta) + side * rng.uniform(-0.25, 0.25)).normalized()
        right = (out - up * out.dot(up)).normalized()
        s = (max(R, H) * rng.uniform(0.95, 1.15)) * (1.0 if ring else 0.7)
        centre = c + up * s * 0.46 + right * s * 0.12
        N._card(m, centre, right, up, s, s, mat, N._quadrant(rng, 2), normal=(UP * 0.75 + out * 0.4).normalized())


def grass_tufts(m, rng, c, R, n, h, mat, seed, pick=2, planes=2, y=0.0):
    """A few crossed grass cards scattered round a point (grass sprite roots sit ~15% above the quadrant's bottom)."""
    c = Vector(c)
    for i in range(n):
        a, d = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.random())
        hh = h * rng.uniform(0.75, 1.2)
        base = c + Vector((math.cos(a) * d, y - hh * 0.14, math.sin(a) * d))
        N.card_tuft(m, base, hh, hh * 1.25, mat, seed=int(seed * 100) + i, planes=planes, pick=pick, lean=rng.uniform(-0.1, 0.1))


def hang_moss(m, rng, lobes, n, mat, seed, length=(1.6, 3.0), width=1.5):
    """Moss curtains hanging from the undersides of crown lobes."""
    for k in range(n):
        c, (rx, ry, rz) = lobes[k % len(lobes)]
        a = rng.uniform(0, 2 * math.pi)
        q = Vector(c) + Vector((math.cos(a) * rx * 0.55, -ry * 0.55, math.sin(a) * rz * 0.55))
        moss_drape(m, rng, q, rng.uniform(*length), width, mat, seed + k, face=(math.cos(a), 0, math.sin(a)))


def moss_drape(m, rng, top, length, width, mat, seed, face=None, count=1, ivy=False):
    """Hanging moss (quadrants 1, 3) or ivy (0, 2) cards from `top`, facing horizontal direction `face`."""
    a = None
    if face is not None:
        f = Vector(face)
        a = math.atan2(-f.x, f.z)  # card_drape's face = (-sin a, 0, cos a)
    N.card_drape(m, top, length, width, mat, seed=int(seed * 100), count=count, spread=0.35,
                 pick=rng.choice((0, 2) if ivy else (1, 3, 1)), facing=a)


def granite_paint(stone, moss, up=0.55, seed=0.0, amount=-0.1):
    """Moss settles on the up-facing facets of stone."""
    def fn(mi, c, n):
        if mi == stone and n.y > up and noise.noise(c * 1.1 + Vector((seed, 0, 0))) > amount:
            return moss
        return None
    return fn


def size_report(ob, p):
    lo, hi = B.bounds([ob])
    return f"{p['id']}: built {hi.x - lo.x:.1f} x {hi.z - lo.z:.1f} x {hi.y - lo.y:.1f} (y {lo.z:.2f}..{hi.z:.2f}) vs {p['size']}, tris {K.tris(ob)}/{p['tris']}"


def preview(build_piece, ids, out):
    """Build only some pieces and render each one alone (3/4 view and eye level) for close inspection."""
    import bpy
    os.makedirs(out, exist_ok=True)
    for pid in ids:
        p = B.PIECES[pid]
        mats = K.reset()
        ob = build_piece(p, mats)
        print("[preview]", size_report(ob, p))
        fig = B.figure(Vector((p["size"][0] / 2 + 1.0, 0, 0)))
        bpy.context.view_layer.update()
        render(os.path.join(out, f"{pid}.png"), B.bounds([ob, fig]), fit=True, res=(800, 700) if os.environ.get("NOSIDE") else (1200, 1000))
        if not os.environ.get("NOSIDE"):
            render(os.path.join(out, f"{pid}-side.png"), B.bounds([ob, fig]), d=(0.3, -1, 0.15), fit=True, res=(1200, 1000))


def cli():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = args[args.index("--only") + 1].split(",") if "--only" in args else None
    out = args[args.index("--out") + 1] if "--out" in args else None
    return only, out


# =====================================================================================================================
# Roothold
# =====================================================================================================================

MATS = [("RH_Bark", "bark.png", 0), ("RH_RootBark", "root-bark.png", 0), ("RH_CedarBark", "cedar-bark.png", 0),
        ("RH_Heartwood", "heartwood.png", 0), ("RH_OakLeaf_Foliage", "oak-leaf.png", 0), ("RH_OakShade_Foliage", "oak-leaf-shade.png", 0),
        ("RH_ElderLeaf_Foliage", "elder-leaf.png", 0), ("RH_ElderBlossom_Foliage", "elder-blossom.png", 0),
        ("RH_ElderShade_Foliage", "elder-leaf-shade.png", 0),
        ("RH_CedarLeaf_Foliage", "cedar-leaf.png", 0), ("RH_CedarShade_Foliage", "cedar-leaf-shade.png", 0),
        ("RH_Fern_Foliage", "fern.png", 0), ("RH_Moss", "moss.png", 0), ("RH_MossStrand_Foliage", "moss.png", 0),
        ("RH_Granite", "granite.png", 0), ("RH_Slate", "slate.png", 0), ("RH_GlowFungus", "glow-fungus.png", 2.5),
        ("RH_Mushroom", "mushroom.png", 0), ("RH_Stem", (0.86, 0.82, 0.7), 0), ("RH_LeafLitter", "leaf-litter.png", 0),
        ("RH_Turf", "ground.png", 0), ("RH_Cliff", "cliff.png", 0), ("RH_Underside", "underside.png", 0),
        ("RH_Water", "water.png", 0), ("RH_Flower", (0.95, 0.93, 0.84), 0), ("RH_Loam", "path.png", 0),
        # alpha-cutout leaf cards (painted sprite atlases shared by every biome)
        ("RH_OakLeaf_Foliage_Card", "../../foliage/broadleaf-green.png", 0), ("RH_OakDark_Foliage_Card", "../../foliage/broadleaf-dark.png", 0),
        ("RH_ElderBlossom_Foliage_Card", "../../foliage/elder-blossom.png", 0), ("RH_CedarSpray_Foliage_Card", "../../foliage/cedar-sprays.png", 0),
        ("RH_Fern_Foliage_Card", "../../foliage/fern.png", 0), ("RH_Grass_Foliage_Card", "../../foliage/grass.png", 0),
        ("RH_MossDrape_Foliage_Card", "../../foliage/ivy-moss.png", 0)]
(BARK, ROOTB, CEDARB, HEART, OAK, OAKS, ELDER, BLOSSOM, ELDERS, CEDAR, CEDARS, FERN, MOSS, STRAND, GRANITE, SLATE, GLOW, MUSH, STEM,
 LITTER, TURF, CLIFF, UNDER, WATER, FLOWER, LOAM, OAKC, OAKDC, ELDERC, CEDARC, FERNC, GRASSC, DRAPEC) = range(len(MATS))
SHADE = {OAK: OAKS, CEDAR: CEDARS, ELDER: ELDERS}
CAP = HEART


def rh_ancient(p, m, rng, seed):
    W, H, _ = p["size"]
    # shrine clearing faces +Z (front): no buttress root there
    cc, cr, trunk, tr_r, lobes = broad_tree(
        m, rng, H, W * 0.96, H * 0.52, 3.0, BARK, [OAK], lean=(0.03, -0.02), fork=0.3, limbs=7, subs=1, roots=9,
        reach=9.0, gap=(math.pi / 2, 0.42), braid=4, fill=5, trunk_sides=20, lobe_r=0.15, top_r=0.22,
        trunk_n=18, root_sides=10, limb_sides=10, sub_sides=7, root_bark=ROOTB, seed=seed, limb_r=0.55, root_h=0.16,
        flare=1.2, strand_sides=7, squash=0.62)
    # glowing mushrooms tucked in the root pockets, moss cushions and fern rosettes on the flare
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        d = Vector((math.cos(a), 0, math.sin(a)))
        base = d * rng.uniform(4.5, 6.5)
        for j in range(2):
            mushroom(m, base + Vector((rng.uniform(-0.4, 0.4), 0, rng.uniform(-0.4, 0.4))), rng.uniform(0.25, 0.6), rng.uniform(0.18, 0.32),
                     GLOW, GLOW, STEM, seed + k * 3 + j, lean=(rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)))
        mass(m, base + d * 0.6, (1.0, 0.35, 0.8), MOSS, seed + k, rough=0.3, rings=4, segs=8, tile=1.5)
        fern_cards(m, rng, base + d * 1.6 + Vector((0, -0.05, 0)), 0.9, 0.8, FERNC, seed + k, 7, 2)
        grass_tufts(m, rng, base + d * 0.4, 1.0, 3, 0.45, GRASSC, seed + k, pick=2)
    # moss hanging beneath the crown masses
    hang_moss(m, rng, lobes, 12, DRAPEC, seed)
    fill_crown(m, lobes, OAKC, p["tris"], (W * 0.09, W * 0.14), cc, seed, dark=OAKDC, dark_share=0.18, bumps=3)
    return cc, cr


def rh_oak(p, m, rng, seed):
    W, H, _ = p["size"]
    cc, cr, trunk, tr_r, lobes = broad_tree(
        m, rng, H, W * 0.95, H * 0.5, 0.95, BARK, [OAK], lean=(0.1, 0.04), fork=0.3, limbs=5, subs=2,
        roots=5, reach=3.0, braid=2, fill=5, trunk_sides=9, trunk_n=8, limb_n=6, root_n=6, lobe_r=0.15, top_r=0.24,
        root_strands=False, root_sides=5, limb_sides=6, sub_sides=4, root_bark=ROOTB, seed=seed, strand_sides=4,
        limb_r=0.7, flare=1.4, squash=0.58)
    fill_crown(m, lobes, OAKC, p["tris"], (W * 0.1, W * 0.155), cc, seed, dark=OAKDC, dark_share=0.14, bumps=2)
    return cc, cr


def rh_elder(p, m, rng, seed, stems):
    """Multi-stem elder: stems fan from one root boss in a vase, each ending in a lobe of blossom-flecked leaf cards
    (the elder-blossom sprites carry the cream umbels)."""
    W, H, _ = p["size"]
    cc = Vector((0, H * 0.62, 0))
    ch = H * 0.55
    mass(m, (0, 0.12, 0), (0.5, 0.42, 0.5), ROOTB, seed, rough=0.3, rings=4, segs=8, tile=1.5)
    lobes = []
    for k in range(stems):
        a = 2 * math.pi * k / stems + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), 0, math.sin(a)))
        rad = rng.uniform(0.55, 0.75)
        T = cc + Vector((d.x * W / 2 * rad * 0.75, (0.15 - 0.4 * rad * rad + rng.uniform(-0.08, 0.08)) * ch, d.z * W / 2 * rad * 0.75))
        st = d * 0.2 + Vector((0, 0.1, 0))
        pts = gnarl(hermite(st, d * 1.2 + UP * H * 0.35, T, (T - st).normalized() * H * 0.3 + UP * 1.5, 7), 0.15, seed + k, keep=1)
        tube(m, pts, [0.17 * (1 - 0.55 * i / 7) for i in range(8)], BARK, 6, twist=0.8, rough=0.15, seed=seed + k, caps=(False, False))
        b0 = pts[4]
        T2 = T + Vector((rng.uniform(-1, 1) * W * 0.1, rng.uniform(0.6, 1.2), rng.uniform(-1, 1) * W * 0.1)) + d * W * 0.08
        tube(m, hermite(b0, (T2 - b0) * 0.6 + UP, T2, (T2 - b0) * 0.6, 4), [0.09, 0.075, 0.06, 0.05, 0.04], BARK, 4, caps=(False, False))
        root(m, Vector((0, 0.35, 0)) + d * 0.3, d, W * 0.16 * rng.uniform(0.7, 1.0), 0.13, ROOTB, seed + k * 2, 4, 5, r1=0.05)
        rl = W * 0.17
        lobes.append((T + UP * rl * 0.25, (rl, rl * 0.75, rl)))
        lobes.append((T2, (rl * 0.7, rl * 0.6, rl * 0.7)))
    lobes.append((cc + Vector((0, ch * 0.22, 0)), (W * 0.24, W * 0.13, W * 0.24)))
    grass_tufts(m, rng, (0, 0, 0), 0.7, 3, 0.4, GRASSC, seed, pick=2)
    fill_crown(m, lobes, ELDERC, p["tris"], (W * 0.11, W * 0.17), cc, seed, dark=OAKDC, dark_share=0.08)
    return cc, max(W, ch) / 2


def rh_cedar(p, m, rng, seed, tiers):
    W, H, _ = p["size"]
    trunk = conifer_tree(m, rng, H, W, H * 0.02 + 0.12, CEDARB, [CEDAR], tiers=0, roots=5, reach=W * 0.28, root_bark=CEDARB, seed=seed,
                         root_r=0.8, trunk_sides=8)
    grass_tufts(m, rng, (0, 0, 0), W * 0.2, 3, 0.45, GRASSC, seed, pick=2)
    conifer_cards(m, rng, H, W * 0.88, trunk, CEDARC, p["tris"], start=0.13, top_frac=0.05, tiers=tiers, droop=0.28, tilt=(0.95, 1.35),
                  size=0.55, seed=seed, top_n=12, layer=0.04, ragged=0.35)
    return Vector((0, H * 0.5, 0)), W / 2


def rh_fern(p, m, rng, seed):
    W, Hh, _ = p["size"]
    mass(m, (0, 0.02, 0), (W * 0.1, W * 0.06, W * 0.1), MOSS, seed, rings=4, segs=6, rough=0.3)
    fern_cards(m, rng, (0, 0, 0), W / 2 * 0.85, Hh * 0.9, FERNC, seed, 16, 6)
    fern_cards(m, rng, (0, 0, 0), W / 2 * 0.65, Hh * 0.75, FERNC, seed + 3, 11, 0, flat=0.15)
    fern_cards(m, rng, (0, 0, 0), W / 2 * 0.5, Hh * 0.6, FERNC, seed + 5, 7, 0, flat=-0.1)


def rh_root_arch(p, m, rng, seed):
    W, H, D = p["size"]
    a0, a1 = Vector((-W / 2 + 0.35, -0.3, 0.1)), Vector((W / 2 - 0.35, -0.3, -0.1))
    r = 0.36
    pts = hermite(a0, Vector((0.6, 6.5, 0.4)), a1, Vector((0.6, -6.5, -0.4)), 12)
    pts = gnarl(pts, 0.12, seed, keep=0)
    peak = max(q.y for q in pts)
    k = (H - r * 1.6) / peak
    pts = [Vector((q.x, -0.3 + (q.y + 0.3) * k, q.z)) for q in pts]
    radii = [r * (1.35 - 0.35 * math.sin(math.pi * i / 12)) for i in range(13)]
    tube(m, pts, radii, ROOTB, 6, twist=1.5, rough=0.18, seed=seed, caps=(False, False))
    strands(m, pts, radii, ROOTB, 1, turns=1.6, rel=0.35, seed=seed, start=0.1, end=0.9, sides=3)
    # moss blanket on the crown of the arch and strands hanging from it
    for i in range(4, 9, 2):
        q = pts[i]
        mass(m, q + Vector((0, r * 0.75, 0)), (0.5, 0.17, 0.42), MOSS, seed + i, rough=0.35, rings=4, segs=7, tile=1.2)
    for i in range(3):
        q = pts[3 + 2 * i]
        moss_drape(m, rng, q + Vector((rng.uniform(-0.1, 0.1), -r * 0.1, rng.uniform(-0.2, 0.2))), rng.uniform(0.7, 1.3), 0.7, DRAPEC, seed + i, count=2)
    for x in (a0, a1):
        mass(m, Vector((x.x * 0.92, 0.0, x.z)), (0.55, 0.22, 0.5), MOSS, seed + x.x, rough=0.3, rings=4, segs=7, tile=1.2)
        flowers(m, Vector((x.x * 0.85, 0.05, x.z + 0.3)), 0.4, 4, FLOWER, int(seed) + int(x.x * 10))
        fern_cards(m, rng, Vector((x.x * 0.8, 0, x.z - 0.35)), 0.45, 0.5, FERNC, seed + x.x, 6, 2)
        grass_tufts(m, rng, Vector((x.x * 0.9, 0, x.z + 0.2)), 0.4, 2, 0.35, GRASSC, seed + x.x, pick=2)


def rh_fallen(p, m, rng, seed):
    W, H, D = p["size"]
    r = H * 0.5
    hollow_log(m, W * 0.84, r, BARK, HEART, HEART, seed, splinter=0.6, sides=8, n=6)
    for i in range(3):
        x = -W * 0.3 + i * W * 0.24
        mass(m, (x, r * 1.75, rng.uniform(-0.1, 0.1)), (W * 0.15, 0.14, r * 0.7), MOSS, seed + i, rough=0.3, rings=4, segs=7, tile=1.2)
    for k in range(2):
        mushroom(m, Vector((rng.uniform(-1.8, 1.0), 0, D * 0.42)), rng.uniform(0.12, 0.22), rng.uniform(0.08, 0.13), MUSH, STEM, STEM, seed + k, sides=6)
    flowers(m, (0.2, r * 1.85, 0), 1.6, 5, FLOWER, int(seed))
    fern_cards(m, rng, (W * 0.3, 0, -D * 0.4), 0.55, 0.6, FERNC, seed + 5, 7, 2)
    grass_tufts(m, rng, (-W * 0.2, 0, D * 0.42), 0.6, 3, 0.35, GRASSC, seed, pick=2)
    for i in range(3):
        moss_drape(m, rng, (-W * 0.25 + i * W * 0.22, r * 1.6, D * 0.3), r * 1.2, 0.6, DRAPEC, seed + i, face=(0, 0, 1))


def rh_glow(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, 0.02, 0), (W * 0.48, 0.14, D * 0.46), MOSS, seed, rough=0.3, rings=4, segs=9, flat=0.3, tile=1.0)
    spots = [(-0.1, 0.0, 0.82, 0.3), (0.25, 0.12, 0.55, 0.22), (-0.35, 0.2, 0.42, 0.17), (0.38, -0.22, 0.3, 0.13), (-0.05, -0.3, 0.25, 0.11)]
    for i, (x, z, h, cr) in enumerate(spots):
        mushroom(m, Vector((x * W, 0.05, z * D)), h * H * 0.85, cr, GLOW, GLOW, STEM, seed + i, lean=(x * 0.25, z * 0.25))
    flowers(m, (0, 0.1, 0), W * 0.45, 3, FLOWER, int(seed))


def rh_seedling(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, 0.0, 0), (W * 0.4, 0.12, D * 0.38), MOSS, seed, rough=0.35, rings=4, segs=8, flat=0.3, tile=1.0)
    pts = gnarl(hermite((0, 0, 0), (0, 0.7, 0), (0.06, H * 0.85, 0.03), (0.1, 0.6, 0), 5), 0.03, seed, keep=1)
    tube(m, pts, [0.025, 0.022, 0.018, 0.015, 0.012, 0.01], BARK, 4, caps=(False, False))
    lobes = [(pts[-1] + UP * 0.02, (0.2, 0.16, 0.2)), (pts[3] + Vector((0.12, 0, 0.05)), (0.14, 0.11, 0.14)), (pts[2] + Vector((-0.1, 0, -0.04)), (0.12, 0.1, 0.12))]
    N.card_crown(m, lobes, OAKC, seed=int(seed * 10), density=40, size=(0.2, 0.3), crown_centre=pts[3], up_bias=0.5)
    grass_tufts(m, rng, (0, 0, 0), W * 0.3, 3, 0.25, GRASSC, seed, pick=2)


def rh_stump(p, m, rng, seed):
    W, H, D = p["size"]
    r = W * 0.27
    pts = [Vector((0, -0.2, 0)), Vector((0, H * 0.3, 0)), Vector((0.02, H * 0.6, 0)), Vector((0.03, H * 0.82, 0))]
    tube(m, pts, [r * 1.35, r * 1.08, r * 1.0, r * 0.97], BARK, 9, twist=0.6, rough=0.15, seed=seed, caps=(False, True))
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        d = Vector((math.cos(a), 0, math.sin(a)))
        root(m, Vector((0, H * 0.3, 0)) + d * r * 0.5, d, W * 0.42, r * 0.55, BARK, seed + k, 4, 5, r1=r * 0.18)
    mass(m, (0.03, H * 0.82, 0), (r * 0.8, 0.12, r * 0.8), MOSS, seed, rough=0.35, rings=4, segs=8, flat=0.2, tile=1.0)
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        mushroom(m, Vector((math.cos(a) * r * 1.5, 0, math.sin(a) * r * 1.5)), rng.uniform(0.1, 0.18), rng.uniform(0.06, 0.1), MUSH, STEM, STEM, seed + k, sides=6)
    flowers(m, (0, 0.03, 0), W * 0.5, 4, FLOWER, int(seed))
    fern_cards(m, rng, (W * 0.38, 0, -D * 0.2), 0.4, 0.5, FERNC, seed, 4, 1)
    grass_tufts(m, rng, (-W * 0.3, 0, D * 0.25), 0.3, 1, 0.3, GRASSC, seed, pick=2)


def rh_deep_moss(p, m, rng, seed):
    W, H, D = p["size"]
    lobes = [(-0.22, -0.1, 0.32, 1.0), (0.2, 0.08, 0.3, 0.85), (0.0, 0.25, 0.25, 0.7), (-0.05, -0.32, 0.22, 0.6)]
    for i, (x, z, s, h) in enumerate(lobes):
        mass(m, (x * W, 0.0, z * D), (s * W, H * h, s * W * 0.9), MOSS, seed + i, rough=0.32, lobe=0.18, rings=4, segs=8, flat=0.2, tile=1.0)
    boulder(m, (0.36 * W, 0, -0.2 * D), (0.25, 0.2, 0.22), GRANITE, seed, n=8, bevel=0.0)
    for i, (x, z, s, h) in enumerate(lobes[:3]):
        grass_tufts(m, rng, (x * W, H * h * 0.55, z * D), s * W * 0.5, 2, 0.22, GRASSC, seed + i, pick=2)
    boulder(m, (-0.42 * W, 0, 0.25 * D), (0.18, 0.14, 0.16), GRANITE, seed + 1, n=7, bevel=0.0)


def rh_litter(p, m, rng, seed, mat=LITTER, n=22):
    W, H, D = p["size"]
    for i in range(n):
        a, d = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        c = Vector((math.cos(a) * d * W * 0.42, 0.01 + rng.uniform(0, H * 0.5), math.sin(a) * d * D * 0.42))
        b = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.2, 0.3)
        f = Vector((math.cos(b), rng.uniform(-0.15, 0.25), math.sin(b)))
        card(m, c - f * L * 0.5, f, L, L * 0.7, mat, fold=-0.12, droop=-0.08, uv=(rng.uniform(0, 0.5), rng.uniform(0, 0.5), rng.uniform(0.5, 1), rng.uniform(0.5, 1)))


def rh_surface_roots(p, m, rng, seed, mat=ROOTB, moss=MOSS):
    """Sinuous roots that surface and dive again, half buried, branching off one another."""
    W, H, D = p["size"]
    mains = []
    for k in range(3):
        z0 = (k - 1) * D * 0.28 + rng.uniform(-0.08, 0.08)
        pts = []
        for i in range(8):
            t = i / 7
            x = -W / 2 + W * t
            z = z0 + math.sin(t * 5 + k * 2) * D * 0.12
            y = H * 0.55 * max(0.0, math.sin(math.pi * (t * 1.6 + k * 0.3)) ) - 0.05
            pts.append(Vector((x * 0.95, y, z)))
        r = rng.uniform(0.07, 0.11)
        tube(m, pts, [r * (1.1 - 0.5 * i / 7) for i in range(8)], mat, 4, twist=0.5, rough=0.2, seed=seed + k, caps=(False, False))
        mains.append(pts)
    for k in range(2):
        src = mains[k][rng.randint(2, 5)]
        d = Vector((rng.uniform(-0.6, 0.6), 0, 1 if k % 2 else -1)).normalized()
        end = src + d * rng.uniform(0.4, 0.6)
        end.y = -0.05
        end.x = max(-W / 2, min(W / 2, end.x))
        end.z = max(-D / 2, min(D / 2, end.z))
        tube(m, hermite(src, d * 0.5 + UP * 0.1, end, d * 0.4 - UP * 0.2, 4), [0.06, 0.05, 0.04, 0.03, 0.02], mat, 4, caps=(False, False))
    if moss is not None:
        for i in range(1):
            mass(m, (rng.uniform(-0.3, 0.3) * W, -0.02, rng.uniform(-0.3, 0.3) * D), (0.25, 0.07, 0.2), moss, seed + i, rough=0.3, rings=3, segs=6, flat=0.2, tile=1.0)


def rh_tuft(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, 0, 0), (W * 0.42, H * 0.38, D * 0.42), MOSS, seed, rough=0.32, lobe=0.18, rings=4, segs=8, flat=0.2, tile=1.0)
    fern_cards(m, rng, (0, H * 0.1, 0), W * 0.45, H * 1.0, FERNC, seed, 8, 3)
    grass_tufts(m, rng, (0, H * 0.15, 0), W * 0.35, 4, H * 0.6, GRASSC, seed, pick=2)
    flowers(m, (0, H * 0.3, 0), W * 0.35, 4, FLOWER, int(seed), r=0.05)


def rh_boulder(p, m, rng, seed, round_=0.65, mat=GRANITE, flowers_n=0, n=40):
    W, H, D = p["size"]
    boulder(m, (0, 0, 0), (W * 0.92, H, D * 0.92), mat, seed, n=n, round_=round_, rot=0.3)
    boulder(m, (W * 0.38, 0, D * 0.3), (W * 0.3, H * 0.28, D * 0.3), mat, seed + 1, n=12, round_=0.4)
    if flowers_n:
        flowers(m, (W * 0.1, 0.02, D * 0.48), 0.35, flowers_n, FLOWER, int(seed))


def rh_slate_slab(p, m, rng, seed, mat=SLATE, moss=MOSS):
    W, H, D = p["size"]
    y = 0.0
    for i in range(3):
        h = H / 3 * rng.uniform(0.85, 1.05)
        s = 1 - 0.17 * i
        plate(m, (rng.uniform(-0.08, 0.08) * W, y + h / 2 - 0.04, rng.uniform(-0.08, 0.08) * D), (W * s, h, D * s), mat, seed + i,
              rot=rng.uniform(-0.25, 0.25), tilt=(rng.uniform(-0.04, 0.04), rng.uniform(-0.05, 0.05)))
        y += h * 0.92
        if i < 2:
            mass(m, (rng.uniform(-0.3, 0.3) * W, y - 0.02, D * s * 0.42), (0.28, 0.06, 0.12), moss, seed + i, rough=0.3, rings=3, segs=6, tile=1.0)


def rh_steps(p, m, rng, seed):
    W, H, D = p["size"]
    for i in range(3):
        h = H * (i + 1) / 3
        dd = D - i * D / 3
        plate(m, (0, h / 2 - 0.03, -i * D / 6), (W * rng.uniform(0.95, 1.0), h, dd), SLATE, seed + i, chip=0.05,
              rot=rng.uniform(-0.03, 0.03), tile=1.2)
        mass(m, (rng.uniform(-0.3, 0.3) * W, h - 0.01, D / 2 - i * D / 3 - 0.1), (0.35, 0.06, 0.12), MOSS, seed + i, rough=0.3, rings=3, segs=6, tile=1.0)
    for x in (-1, 1):
        mass(m, (x * W * 0.48, 0.02, D * 0.35), (0.22, 0.12, 0.3), MOSS, seed + x, rough=0.35, rings=3, segs=6, tile=1.0)


def rh_outcrop(p, m, rng, seed, mats=(GRANITE, SLATE, GRANITE, SLATE)):
    """Tall jagged outcrop: leaning upright blades of granite and slate of falling heights, with ledge blocks at
    their feet; moss settles on every ledge."""
    W, H, D = p["size"]
    blades_ = [(0.0, 0.0, 1.0, 0.45), (-0.3, 0.12, 0.72, 0.38), (0.3, -0.1, 0.6, 0.4), (0.12, 0.3, 0.45, 0.35), (-0.2, -0.3, 0.38, 0.35)]
    for i, (x, z, hf, wf) in enumerate(blades_):
        h = H * hf
        boulder(m, (x * W, -0.05, z * D), (W * wf, h, D * 0.36), mats[i % len(mats)], seed + i, n=16, round_=0.3, rot=rng.uniform(-0.6, 0.6),
                sink=0.0, base=-0.9, bevel=0.03)
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.5
        boulder(m, (math.cos(a) * W * 0.36, -0.05, math.sin(a) * D * 0.36), (W * 0.42, H * 0.18, D * 0.4), mats[(i + 1) % len(mats)], seed + 10 + i,
                n=12, round_=0.35, rot=a, sink=0.0, base=-0.9, bevel=0.03)


def cliff_face(m, rng, W, D, H, stone, seed, top=1.3, rows=3, inset=0.35, under=None):
    """Chunky rock face under a lip: rows of chiselled blocks along X stepping inward as they go down to y = 0,
    blocks kept inside -W/2..W/2 so segments tile. `under` adds a core sheet of that material behind the blocks."""
    y = H - top
    for r in range(rows):
        h = y / (rows - r) * rng.uniform(0.95, 1.15)
        n = max(3, round(W / (1.7 - 0.25 * r)))
        z = D / 2 - 0.15 - r * inset
        for k in range(n):
            w = W / n
            x = -W / 2 + w * (k + 0.5) + rng.uniform(-0.15, 0.15) * w
            size = (w * rng.uniform(1.05, 1.25), h * rng.uniform(1.0, 1.2), rng.uniform(1.1, 1.6))
            boulder(m, (x, y - size[1], z - size[2] * 0.4), size, stone, seed + r * 13 + k, n=12, round_=0.4, rot=rng.uniform(-0.2, 0.2), tile=2.0,
                    sink=0.0, base=-0.9, bevel=0.0)
        y -= h * 0.95
        if y <= 0.2:
            break


def lip_roots(m, rng, W, D, H, xs, mat, seed, r=0.3, sides=6, n=10, depth=4.6):
    """Thick roots that leave the turf, spill over the rim and run down the face, trailing below it."""
    for k, x in enumerate(xs):
        pts = [Vector((x, H - 0.15, -D / 2 + 0.4)), Vector((x + 0.2, H + 0.05, 0.3)), Vector((x + 0.3, H - 0.15, D / 2 + 0.55)),
               Vector((x + 0.4, H - 0.85, D / 2 + 0.75)), Vector((x + 0.2, H - 1.7, D / 2 + 0.35)), Vector((x - 0.1, H - 2.6, D / 2 + 0.25)),
               Vector((x - 0.2, H - 3.5, D / 2 + 0.05)), Vector((x, H - depth, D / 2 - 0.3))]
        pts = gnarl(pts, 0.1, seed + k, keep=0)
        fine = []
        for a_, b_ in zip(pts, pts[1:]):
            fine += [a_.lerp(b_, t) for t in (0, 0.5)]
        fine.append(pts[-1])
        rr_ = r * rng.uniform(0.75, 1.1)
        rr = [rr_ * (1 - 0.75 * i / len(fine)) for i in range(len(fine))]
        tube(m, fine, rr, mat, sides, twist=1.0, rough=0.2, seed=seed + k, caps=(False, False))


def rh_lip(p, m, rng, seed):
    W, H, D = p["size"]
    lip_edge(m, W, D, H, TURF, MOSS, CLIFF, seed, notch=1.6, segs=14)
    cliff_face(m, rng, W, D, H, GRANITE, seed, top=1.25, rows=3)
    lip_roots(m, rng, W, D, H, (-2.6, -0.4, 2.8), ROOTB, seed)
    for i in range(12):
        x = -W / 2 + 0.3 + i * (W - 0.6) / 11 + rng.uniform(-0.2, 0.2)
        if abs(x - 1.6) < 0.5:
            continue
        moss_drape(m, rng, (x, H - 0.45, D / 2 + 0.62), rng.uniform(1.6, 2.8), 1.5, DRAPEC, seed + i, face=(0, 0, 1), ivy=i % 4 == 0)
    for i in range(4):
        x = rng.uniform(-W / 2 + 0.6, W / 2 - 0.6)
        mass(m, (x, H - 0.02, rng.uniform(-0.8, 0.9)), (0.45, 0.14, 0.38), MOSS, seed + i, rough=0.3, rings=4, segs=7, tile=1.0)
    flowers(m, (0, H, 0.4), 3.2, 8, FLOWER, int(seed))
    fern_cards(m, rng, (-3.2, H - 0.05, 0.6), 0.6, 0.7, FERNC, seed, 7, 2)
    fern_cards(m, rng, (2.6, H - 0.05, -0.4), 0.5, 0.6, FERNC, seed + 1, 6, 2)
    for i in range(6):
        x = rng.uniform(-W / 2 + 0.5, W / 2 - 0.5)
        if abs(x - 1.6) > 0.5:
            grass_tufts(m, rng, (x, H, rng.uniform(-1.0, 1.1)), 0.3, 2, 0.4, GRASSC, seed + i, pick=2)


def rh_fall(p, m, rng, seed):
    W, H, D = p["size"]
    pts = [Vector((0, H - 0.05, -0.2)), Vector((0, H - 0.2, 0.15)), Vector((0, H - 0.8, 0.3))] + [Vector((0.04 * math.sin(i), H - 0.8 - (H - 0.8) * i / 6, 0.3 + 0.05 * i / 6)) for i in range(1, 7)]
    widths = [0.42, 0.45, 0.5, 0.52, 0.55, 0.6, 0.65, 0.7, 0.75]
    sweep(m, pts, widths, 0.1, (1, 0, 0), WATER, 6, uv_len=3.0)
    mass(m, (0, H - 0.08, -0.05), (0.38, 0.1, 0.28), FLOWER, seed, rough=0.3, rings=3, segs=6, tile=0.5)  # foam lip
    mass(m, (0, 0.05, 0.35), (0.5, 0.12, 0.4), FLOWER, seed + 1, rough=0.35, rings=3, segs=7, tile=0.5)  # spray at the foot


def underside_chunks(m, rng, W, H, stone, seed, levels=4, hole=None, size=2.4):
    """Chiselled stone blocks in rings around an underside taper, smaller towards the tip; skips a round hole."""
    for i in range(levels):
        t = (i + 0.35) / levels
        y = H * (1 - t)
        R = W / 2 * 0.8 * (1 - t) ** 0.8
        count = max(2, round(2 * math.pi * R / (size * 0.95 * (1 - 0.4 * t))))
        for k in range(count):
            a = 2 * math.pi * k / count + i * 0.5 + rng.uniform(-0.15, 0.15)
            c = Vector((math.cos(a) * R, y, math.sin(a) * R))
            if hole is not None and (c.x ** 2 + (c.y - hole[0]) ** 2) < (hole[1] + 0.6) ** 2 and abs(c.z) > R * 0.5:
                continue
            sz = size * (1 - 0.5 * t) * rng.uniform(0.85, 1.1)
            boulder(m, c - Vector((0, H / levels * 0.7, 0)), (sz, H / levels * 1.5, sz * 0.8), stone, seed + i * 10 + k, n=11, round_=0.35,
                    rot=-a + math.pi / 2, tile=3.5, sink=0.0, base=-0.9, bevel=0.0)


def underside_roots(m, rng, W, H, mat, seed, count=3, r=0.42, sides=6, n=12, turn=2.2, trail=0.12):
    """Huge roots spiralling down an underside taper and trailing below the tip."""
    for k in range(count):
        a0 = 2 * math.pi * k / count + seed
        pts = []
        for i in range(n + 1):
            t = i / n
            y = H * (1.0 - (1 + trail) * t)
            R = W / 2 * 0.82 * max(0.0, 1 - t) ** 0.8 + 0.3
            a = a0 + t * turn
            pts.append(Vector((math.cos(a) * R, y, math.sin(a) * R)))
        rr = [r * (1 - 0.8 * i / n) for i in range(n + 1)]
        tube(m, pts, rr, mat, sides, twist=1.2, rough=0.2, seed=seed + k, caps=(False, False))


def rh_underside(p, m, rng, seed):
    W, H, D = p["size"]
    underside_core(m, W * 0.86, H, UNDER, seed, segs=12, tiers=6)
    underside_chunks(m, rng, W, H, GRANITE, seed)
    underside_roots(m, rng, W, H, ROOTB, seed)
    for i in range(10):
        a = rng.uniform(0, 2 * math.pi)
        t = rng.uniform(0.05, 0.5)
        R = W / 2 * 0.86 * (1 - t) ** 0.8 + 0.2
        moss_drape(m, rng, (math.cos(a) * R, H * (1 - t), math.sin(a) * R), rng.uniform(1.2, 2.6), 1.1, DRAPEC, seed + i, face=(math.cos(a), 0, math.sin(a)))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.6
        t = 0.3 + 0.12 * k
        R = W / 2 * 0.86 * (1 - t) ** 0.8 + 0.25
        base = Vector((math.cos(a) * R, H * (1 - t), math.sin(a) * R))
        for j in range(2):
            mushroom(m, base + Vector((rng.uniform(-0.3, 0.3), 0, rng.uniform(-0.3, 0.3))), rng.uniform(0.2, 0.35), rng.uniform(0.18, 0.26),
                     GLOW, GLOW, STEM, seed + k + j, lean=(math.cos(a) * 0.4, math.sin(a) * 0.4), sides=7)


def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    rng = random.Random(p["id"])
    pid = p["id"]
    m = Mesh()
    fn, flat, up, facing = None, (), (FLOWER, LITTER), None
    smooth = True
    crown = None
    if pid == "rh-ancient-tree":
        crown = rh_ancient(p, m, rng, seed)
    elif pid == "rh-oak-b":
        crown = rh_oak(p, m, rng, seed)
    elif pid == "rh-elder-a":
        crown = rh_elder(p, m, rng, seed, 6)
    elif pid == "rh-elder-b":
        crown = rh_elder(p, m, rng, seed, 4)
    elif pid == "rh-cedar-a":
        crown = rh_cedar(p, m, rng, seed, 12)
    elif pid == "rh-cedar-b":
        crown = rh_cedar(p, m, rng, seed, 10)
    elif pid == "rh-fern-clump":
        rh_fern(p, m, rng, seed)
    elif pid == "rh-root-arch":
        rh_root_arch(p, m, rng, seed)
        fn = lambda mi, c, n: MOSS if mi == ROOTB and n.y > 0.6 and noise.noise(c * 0.9) > -0.1 else None  # noqa: E731
    elif pid == "rh-fallen-trunk":
        rh_fallen(p, m, rng, seed)
        fn = lambda mi, c, n: MOSS if mi == BARK and n.y > 0.45 and noise.noise(c * 0.9) > -0.25 else None  # noqa: E731
    elif pid == "rh-glow-mushrooms":
        rh_glow(p, m, rng, seed)
    elif pid == "rh-seedling":
        rh_seedling(p, m, rng, seed)
    elif pid == "rh-lichen-stump":
        rh_stump(p, m, rng, seed)
        fn = lambda mi, c, n: MOSS if mi == BARK and n.y > 0.5 and noise.noise(c * 1.4) > 0.0 else None  # noqa: E731
    elif pid == "rh-deep-moss":
        rh_deep_moss(p, m, rng, seed)
        flat = (GRANITE,)
    elif pid == "rh-leaf-litter":
        rh_litter(p, m, rng, seed)
    elif pid == "rh-surface-roots":
        rh_surface_roots(p, m, rng, seed)
    elif pid == "rh-fern-moss-tuft":
        rh_tuft(p, m, rng, seed)
    elif pid == "rh-granite-boulder-a":
        rh_boulder(p, m, rng, seed, 0.75)
        fn, flat = granite_paint(GRANITE, MOSS, 0.6, seed), (GRANITE, MOSS)
    elif pid == "rh-granite-boulder-b":
        rh_boulder(p, m, rng, seed, 0.35, flowers_n=4, n=30)
        fn, flat = granite_paint(GRANITE, MOSS, 0.6, seed), (GRANITE, MOSS)
    elif pid == "rh-slate-slab":
        rh_slate_slab(p, m, rng, seed)
        flat = (SLATE,)
    elif pid == "rh-slate-step-block":
        rh_steps(p, m, rng, seed)
        flat = (SLATE,)
    elif pid == "rh-mossy-outcrop":
        rh_outcrop(p, m, rng, seed)
        fn, flat = granite_paint(GRANITE, MOSS, 0.5, seed, -0.3), (GRANITE, SLATE, MOSS)
        fn2 = granite_paint(SLATE, MOSS, 0.5, seed, -0.3)
        fn = (lambda f1, f2: (lambda mi, c, n: f1(mi, c, n) or f2(mi, c, n)))(fn, fn2)
    elif pid == "rh-lip-edge":
        rh_lip(p, m, rng, seed)
        flat = (GRANITE,)
        fn = granite_paint(GRANITE, MOSS, 0.6, seed, 0.0)
        facing = {TURF: UP, MOSS: Vector((0, 0.2, 1)), CLIFF: Vector((0, -1, 0.4))}
    elif pid == "rh-spring-fall":
        rh_fall(p, m, rng, seed)
    elif pid == "rh-underside-roots":
        rh_underside(p, m, rng, seed)
        flat = (GRANITE, UNDER)
        fn = granite_paint(GRANITE, MOSS, 0.55, seed, 0.1)
    else:
        raise ValueError(pid)
    ob = m.object(pid, mats, moss=None, seed=seed, smooth=smooth)
    if crown is not None:
        cc, cr = crown
        fn = tree_paint(SHADE, cc, cr, bark=(BARK, ROOTB, CEDARB), moss=MOSS, seed=seed)
    return post(ob, fn, flat, up, facing=facing)


CATEGORY = {"hero": "hero", "tree": "tree", "rock": "rock", "lip": "lip", "underside": "underside", "water": "water", "ground": "ground"}


def category(p):
    if p["family"] == "plant":
        return "bush" if p["id"] in ("rh-fern-clump", "fo-fern-clump", "fo-bramble", "fo-fireflies-fern") else "ground"
    return CATEGORY.get(p["family"], "ground")


if __name__ == "__main__":
    K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/roothold"), cap_mat=HEART, moss=None)
    only, out = cli()
    if only:
        preview(build_piece, only, out or "/tmp/rh-preview")
    else:
        K.build_all(build_piece, extras=[(p["id"], category(p)) for p in B.kit["pieces"]], biome="roothold")
