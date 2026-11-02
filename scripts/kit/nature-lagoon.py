# Lagoon nature kit: salt-twisted trees with flat wind-pruned crowns, bleached dead snags, reed beds, glowweed,
# shells, drift timber, chiselled basalt boulders and hexagonal column rocks with teal veins, a glowing mere edge,
# isle lip ledges and underside spires. Built from art/models/nature/lagoon/kit.json; painted swatches cropped from
# the nature sheet live in art/textures/biomes/lagoon.
# Usage: Blender --background --python scripts/kit/nature-lagoon.py -- lagoon [closeup <id,id,...> <out dir>]
import bmesh, bpy, math, os, random, sys
from mathutils import Quaternion, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
import naturelib as N  # noqa: E402
from kitlib import Mesh, V, hermite, tube  # noqa: E402

# Material slots, in order. "Foliage" sways and is double-sided in the demo, "Glow" is emissive.
MATS = [("LG_Ground", "ground.png", 0), ("LG_Path", "path.png", 0), ("LG_Cliff", "cliff.png", 0),
        ("LG_Underside", "underside.png", 0), ("LG_Bark", "salt-bark.png", 0), ("LG_SaltFoliage", "salt-foliage.png", 0),
        ("LG_SnagWood", "snag-wood.png", 0), ("LG_DriftWood", "drift-wood.png", 0), ("LG_ReedFoliage", "reeds.png", 0),
        ("LG_ReedSeedFoliage", "reed-seed.png", 0), ("LG_SaltGrassFoliage", "salt-grass.png", 0),
        ("LG_WetMoss", "wet-moss.png", 0), ("LG_Basalt", "basalt.png", 0), ("LG_Slate", "slate.png", 0),
        ("LG_GlowVein", "glowweed.png", 2.5), ("LG_GlowWeed", "glowweed.png", 3.0), ("LG_GlowWater", "mere-water.png", 1.4),
        ("LG_Shell", "shell.png", 0), ("LG_CrabShell", "crab-shell.png", 0), ("LG_WeedFoliage", "hanging-weed.png", 0),
        # alpha-cutout sprite cards (painted 2x2 atlases in art/textures/foliage)
        ("LG_SaltOlive_Foliage_Card", "../../foliage/salt-olive.png", 0), ("LG_Reed_Foliage_Card", "../../foliage/reeds.png", 0),
        ("LG_SaltGrass_Foliage_Card", "../../foliage/grass.png", 0), ("LG_Weed_Foliage_Card", "../../foliage/ivy-moss.png", 0)]
(GROUND, PATH, CLIFF, UNDER, BARK, LEAF, SNAG, DRIFT, REED, SEED, GRASS, MOSS, BASALT, SLATE, VEIN, GLOWWEED, WATER,
 SHELL, CRAB, WEED, OLIVE_C, REED_C, GRASS_C, WEED_C) = range(len(MATS))
K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/lagoon"), cap_mat=BARK, moss=None)

_render = B.render


def render(path, objs_bounds, color_type="OBJECT"):
    # Standard view transform and a lift: Workbench's studio light renders painted albedo at ~60%; no specular sheen,
    # the game's painted materials are fully rough
    bpy.context.scene.display.shading.show_specular_highlight = False
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.exposure = 0.45
    return _render(path, objs_bounds, color_type)


B.render = render
UP = Vector((0, 1, 0))
VIEW = Vector((1, 0, 1.3)).normalized()  # horizontal direction towards the contact-sheet camera


# ---------- object plumbing ----------

def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def finish(ob, angle=40):
    """Crisp stone shading: sharp edges above `angle`, face-area weighted normals so facets read flat."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0) < math.radians(angle)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(ob.data)
    bm.free()
    mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.mode, mod.weight, mod.keep_sharp = "FACE_AREA", 50, True
    apply_mods(ob)
    return ob


def fit(ob, size, scale=True, floor=True):
    """Centre the piece on its bottom-center pivot and scale it uniformly to fill the manifest box."""
    vs = ob.data.vertices
    lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
    hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
    ext = hi - lo
    w, h, d = size
    s = min(w / ext.x, d / ext.y, h / ext.z) if scale else 1.0
    c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z if floor else 0))
    for v in vs:
        v.co = (v.co - c) * s
    ob.data.update()
    return ob


def all_projected(m, tile):
    m.project = [(f, tile) for f in m.bm.faces]


def chisel(m, planes, mat, tile=1.5):
    """Slice a closed lump with planes (glTF point, outward normal), cap each cut flat: crisp rock facets."""
    bm = m.bm
    for co, no in planes:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=V(*co), plane_no=V(*no), clear_outer=True, dist=1e-5)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
        if edges:
            for f in bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]:
                f.material_index = mat
    all_projected(m, tile)


def rand_dir(rng, up_bias=0.0, flat=1.0):
    d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1) * flat + up_bias, rng.uniform(-1, 1)))
    return d.normalized() if d.length > 1e-4 else Vector((0, 1, 0))


def pblob(m, centre, radii, mat, tile=1.0, **kw):
    """naturelib.blob with box-projected UVs (the lat-long UVs pinch the painted swatch into streaks at the poles)."""
    m.bm.faces.ensure_lookup_table()
    n0 = len(m.bm.faces)
    N.blob(m, centre, radii, mat, **kw)
    m.bm.faces.ensure_lookup_table()
    for f in list(m.bm.faces)[n0:]:
        m.project.append((f, tile))


def hull(m, pts, mat, tile=1.6, dissolve=4.0):
    """Convex hull of a point cloud with near-coplanar triangles merged: crisp, chunky painterly facets."""
    vs = [m.vert(q) for q in pts]
    res = bmesh.ops.convex_hull(m.bm, input=vs, use_existing_faces=False)
    junk = list({v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert) and v.is_valid})
    bmesh.ops.delete(m.bm, geom=junk, context="VERTS")
    faces = [f for f in res["geom"] if isinstance(f, bmesh.types.BMFace) and f.is_valid]
    if dissolve:
        bmesh.ops.dissolve_limit(m.bm, angle_limit=math.radians(dissolve), verts=list({v for f in faces for v in f.verts}),
                                 edges=list({e for f in faces for e in f.edges}))
    for f in m.bm.faces:
        f.material_index = mat
    all_projected(m, tile)


def cloud(rng, centre, size, n=40, rough=0.2, seed=0.0, floor=None, inner=0.82):
    """Points scattered on and just inside a noisy ellipsoid (the hull keeps the outermost)."""
    c = Vector(centre)
    w, h, d = size
    out = []
    for _ in range(n):
        u = rand_dir(rng)
        k = (1 + rough * noise.noise(u * 1.6 + Vector((seed, seed * 0.3, 0))))*rng.uniform(inner, 1.0)
        q = c + Vector((u.x * w / 2, u.y * h / 2, u.z * d / 2)) * k
        if floor is not None:
            q.y = max(q.y, floor)
        out.append(q)
    return out


def hull_rock(mats, centre, size, mat, seed, n=40, rough=0.2, moss=None, tile=1.6, name="rock", sink=0.0, inner=0.82):
    rng = random.Random(seed)
    m = Mesh()
    c = Vector(centre) + Vector((0, size[1] / 2 - sink, 0))
    hull(m, cloud(rng, c, size, n, rough, seed, floor=Vector(centre).y, inner=inner), mat, tile)
    return finish(m.object(name, mats, moss=moss, seed=seed), 32)


def compound_rock(mats, size, mat, seed, lumps=3, moss=None, tile=1.6):
    """A main hull with smaller hulls fused into its flanks, so the boulder is lumpy rather than one convex gem."""
    rng = random.Random(seed)
    w, h, d = size
    parts = [hull_rock(mats, (0, 0, 0), (w * 0.85, h * 0.95, d * 0.85), mat, seed, n=60, rough=0.3, moss=moss, tile=tile)]
    for k in range(lumps):
        a = 2 * math.pi * k / lumps + rng.uniform(-0.5, 0.5)
        s = rng.uniform(0.45, 0.6)
        c = (math.cos(a) * w * 0.25, 0, math.sin(a) * d * 0.25)
        parts.append(hull_rock(mats, c, (w * s, h * s * rng.uniform(0.9, 1.3), d * s), mat, seed + 11 * (k + 1), n=30, rough=0.25,
                               moss=moss, tile=tile))
    return K.join(parts, "rock")


def crown_union(m, centre, ells, mat, size, segs=34, rings=14, tile=2.4, seed=0.0):
    """One continuous crown surface: the outer boundary of a union of ellipsoid clumps, sampled along rays from
    the crown centre. Dips between clumps read as the clefts of a clumped painterly canopy."""
    c = Vector(centre)
    W, H, D = size
    rows = []
    for i in range(rings + 1):
        phi = -math.pi / 2 + math.pi * i / rings
        row = []
        for j in range(segs if 0 < i < rings else 1):
            th = 2 * math.pi * j / segs
            d = Vector((math.cos(phi) * math.cos(th) * W, math.sin(phi) * H, math.cos(phi) * math.sin(th) * D)).normalized()
            t = 0.0
            for e, r in ells:
                o = Vector(((c.x - e.x) / r[0], (c.y - e.y) / r[1], (c.z - e.z) / r[2]))
                dd = Vector((d.x / r[0], d.y / r[1], d.z / r[2]))
                A, Bq, C = dd.dot(dd), 2 * o.dot(dd), o.dot(o) - 1
                disc = Bq * Bq - 4 * A * C
                if disc > 0:
                    t = max(t, (-Bq + math.sqrt(disc)) / (2 * A))
            q = c + d * max(t, 0.3)
            t = max(t, 0.3) + 0.12 * noise.noise(q * 1.6 + Vector((seed, 0, 0))) + 0.05 * noise.noise(q * 4.0)
            row.append(m.vert(c + d * t))
        rows.append(row)
    for i in range(rings):
        a, b = rows[i], rows[i + 1]
        for j in range(segs):
            j1 = (j + 1) % segs
            if len(a) == 1:
                m.face((a[0], b[j1], b[j]), None, mat, tile)
            elif len(b) == 1:
                m.face((a[j], a[j1], b[0]), None, mat, tile)
            else:
                m.face((a[j], a[j1], b[j1], b[j]), None, mat, tile)


def boulder(mats, centre, size, mat, seed, moss=None, tile=1.6, name="rock", n=34, rough=0.22, **_):
    return hull_rock(mats, centre, size, mat, seed, n=n, rough=rough, moss=moss, tile=tile, name=name)


def strands(m, pts, radii, count, turns, rel, mat, seed, start=0.04, end=0.92, sides=5):
    """Thinner fibres twisting round a trunk or root so it reads gnarled and grown, not piped."""
    fr = B.frames(pts)
    n = len(pts)
    for j in range(count):
        sub, rr = [], []
        for i in range(int(n * start), max(int(n * end), int(n * start) + 4)):
            i = min(i, n - 1)
            t = i / (n - 1)
            phi = j * 2 * math.pi / count + turns * 2 * math.pi * t + seed
            _, nn, bb = fr[i]
            sub.append(pts[i] + (nn * math.cos(phi) + bb * math.sin(phi)) * radii[i] * 0.88)
            rr.append(radii[i] * rel * (1.15 - 0.5 * t))
        tube(m, sub, rr, mat, sides, rough=0.25, seed=seed + j * 3.1)


def chain(*segs):
    """Join hermite segments (p0, t0, p1, t1, n) into one polyline."""
    out = []
    for s in segs:
        pts = hermite(*s)
        out += pts if not out else pts[1:]
    return out


def taper(n, r0, r1, flare=0.0):
    return [r1 + (r0 - r1) * (1 - i / (n - 1)) ** 1.2 + flare * max(0.0, 1 - i / (n * 0.18)) for i in range(n)]


def rotate(d, axis, ang):
    return Quaternion(axis, ang) @ d


def limb(m, p, d, L, r, depth, rng, mat, sides=5, lift=0.25, spread=0.6, kids=2, segs=4, rough=0.25):
    """Recursive bare branch: a curved tapering tube with forking children (dead snags, saplings, drift twigs)."""
    d = d.normalized()
    bend = rand_dir(rng) * 0.35 + Vector((0, lift, 0))
    e = p + (d + bend * 0.5).normalized() * L
    pts = hermite(p, d * L * 0.7, e, (d + bend).normalized() * L * 0.7, segs)
    tube(m, pts, [r * (1 - 0.55 * i / segs) for i in range(segs + 1)], mat, sides, rough=rough, seed=rng.random() * 9,
         caps=(False, True))
    if depth <= 0:
        return [e]
    tips = []
    for k in range(kids):
        q = pts[rng.randint(max(1, segs - 2), segs)]
        ax = d.cross(rand_dir(rng)).normalized()
        nd = rotate(d, ax, (0.35 + 0.45 * rng.random()) * spread * (1 if k % 2 == 0 else -1))
        tips += limb(m, q, nd + Vector((0, lift * 0.6, 0)), L * rng.uniform(0.5, 0.7), r * 0.55, depth - 1, rng, mat,
                     max(3, sides - 1), lift, spread, kids, max(3, segs - 1), rough)
    return tips


def ellipse_points(rng, n, w, d, min_gap=0.5):
    """Roughly even points inside an ellipse (dart throwing), larger gaps first."""
    pts = []
    tries = 0
    while len(pts) < n and tries < 4000:
        tries += 1
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        p = (math.cos(a) * r * w / 2, math.sin(a) * r * d / 2)
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > min_gap for q in pts):
            pts.append(p)
    return pts


def crown_pad(m, rng, centre, w, d, thick, n, seed, wind=1.0, droop=0.42, density=30.0, size=(1.0, 1.7)):
    """Wind-pruned flat crown of salt-olive leaf cards over level-topped clumps that stream downwind (+X): the windward
    edge shorn short and high, the lee edge trailing longer, lower and thinner, a few clumps riding on top to break
    the line. Returns clump centres (for branches)."""
    c = Vector(centre)
    gap = math.sqrt(w * d / n) * 0.66
    lobes, out = [], []
    for i, (x, z) in enumerate(ellipse_points(rng, n, w * 0.8, d * 0.8, gap)):
        e = math.hypot(x / (w / 2), z / (d / 2))
        lee = max(0.0, x / (w / 2) * wind)  # 0 windward .. 1 at the lee tip
        s = gap * rng.uniform(0.85, 1.05) * (1.12 - 0.3 * e)
        hy = min(s * rng.uniform(0.5, 0.62), thick * 0.6) * (1 - 0.25 * lee)
        y = c.y - droop * thick * e ** 2 - 0.3 * thick * lee + rng.uniform(-0.14, 0.12) * thick
        q = Vector((c.x + x + 0.25 * s * lee * wind, y, c.z + z))
        lobes.append((q, (s * (1 + 0.4 * lee), hy, s * rng.uniform(0.85, 1.0))))
        out.append((q, s, e))
    for x, z in ellipse_points(rng, max(1, n // 3), w * 0.55, d * 0.55, gap * 0.8):
        s = gap * rng.uniform(0.6, 0.75)
        lobes.append((Vector((c.x + x - 0.08 * w * wind, c.y + thick * 0.3, c.z + z)), (s, s * 0.5, s)))
    N.card_crown(m, lobes, OLIVE_C, seed=seed, density=density, size=size, crown_centre=c - Vector((0, thick * 0.7, 0)), up_bias=0.4)
    return out


# ---------- alpha-cutout sprite cards ----------

# Painted sprite bounds inside each 2x2 atlas quadrant (u0, v0, u1, v1; v from the quadrant's bottom), measured from
# the alpha, so tufts stand on their roots and drapes hang from their top edge with no empty margin.
CROP = {
    REED_C: [(0.04, 0.10, 0.97, 0.94), (0.02, 0.10, 0.94, 0.76), (0.07, 0.05, 0.96, 0.94), (0.06, 0.05, 0.94, 0.93)],
    GRASS_C: [(0.04, 0.14, 0.98, 0.73), (0.01, 0.15, 0.96, 0.78), (0.01, 0.17, 0.95, 0.71), (0.02, 0.17, 0.97, 0.78)],
    WEED_C: [(0.15, 0.10, 0.90, 0.90), (0.09, 0.11, 0.89, 0.90), (0.14, 0.07, 0.91, 0.90), (0.10, 0.07, 0.86, 0.89)],
}


def sprite(mat, q):
    """UV rectangle of quadrant q's painted sprite and its width / height."""
    u0, v0, u1, v1 = CROP[mat][q]
    qx, qy = q % 2, q // 2
    return ((qx + u0) / 2, (qy + v0 + 0.01) / 2, (qx + u1) / 2, (qy + v1) / 2), (u1 - u0) / (v1 - v0 - 0.01)


def rcard(m, centre, right, up, w, h, mat, rect, normal):
    """One alpha-cutout card mapped to a UV rectangle, wound to face along its normal hint."""
    c = Vector(centre)
    u0, v0, u1, v1 = rect
    corners = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if right.cross(up).dot(normal) < 0:
        corners, uvs = corners[::-1], uvs[::-1]
    vs = [m.vert(p) for p in corners]
    m.keep.add(m.face(vs, uvs, mat))
    for v in vs:
        m.normals[v] = normal


def ctuft(m, base, height, mat, q, seed, planes=3, lean=0.0, normal_up=0.8, widen=1.0):
    """Grass, reed or rush clump: `planes` crossed vertical cards of one painted sprite, roots on `base`."""
    rng = random.Random(seed)
    rect, asp = sprite(mat, q)
    b = Vector(base)
    a0 = rng.uniform(0, math.pi)
    for k in range(planes):
        a = a0 + math.pi * k / planes + rng.uniform(-0.2, 0.2)
        right = Vector((math.cos(a), 0, math.sin(a)))
        face = Vector((-math.sin(a), 0, math.cos(a)))
        if face.dot(VIEW) < 0:  # the shader lights both faces alike; turn the painted front to the sheet camera
            right, face = -right, -face
        up = (UP + face * lean * rng.uniform(-1, 1)).normalized()
        n = (face * (1 - normal_up) + UP * normal_up).normalized()
        hk = height * rng.uniform(0.88, 1.08)
        rcard(m, b + up * hk / 2, right, up, hk * asp * widen, hk, mat, rect, n)


def cdrape(m, top, length, mat, q, facing, seed=0, tilt=0.15, widen=1.0):
    """Hanging weed or moss: one card hanging from `top`, its face turned to the glTF angle `facing` (0 faces +Z),
    tipped out at the bottom by `tilt` so it hangs off the edge rather than through it."""
    rng = random.Random(seed)
    rect, asp = sprite(mat, q)
    a = facing + rng.uniform(-0.3, 0.3)
    right = Vector((math.cos(a), 0, math.sin(a)))
    face = Vector((-math.sin(a), 0, math.cos(a)))
    up = (UP - face * tilt).normalized()
    rcard(m, Vector(top) - up * length / 2, right, up, length * asp * widen, length, mat, rect, (face + UP * 0.5).normalized())


def tuft(m, centre, radius, height, mat, seed, count=7, width=0.035, lean=0.6, tip_mat=None):
    """Grass or reed tuft as crossed sprite cards (salt grass, or plume and cattail reeds)."""
    rng = random.Random(seed)
    if mat == REED:
        ctuft(m, centre, height, REED_C, rng.choice((2, 0, 3)), seed, planes=3 if count >= 6 else 2)
    else:
        ctuft(m, centre, height * 1.1, GRASS_C, 1 if rng.random() < 0.85 else 0, seed, planes=3 if count >= 6 else 2)


# ---------- trees ----------

TREES = {
    # trunk segments, base radius, top radius, pads (centre, w, d, thickness, clumps), extra limb (start t, end)
    "a": dict(trunk=[((-1.7, 0, 0), (0.5, 2.8, 0.1), (0.2, 3.1, 0.25), (2.6, 1.2, 0.1), 8),
                     ((0.2, 3.1, 0.25), (2.6, 1.2, 0.1), (1.9, 3.9, 0.1), (1.6, 1.0, -0.1), 5)],
              r=(0.7, 0.32), pads=[((0.5, 4.75, 0), 7.6, 6.1, 1.25, 15)], arms=[(0.55, (-2.2, 4.4, 1.0)), (0.7, (3.4, 4.4, -1.2))]),
    "b": dict(trunk=[((0.2, 0, 0), (-1.2, 2.4, 0.2), (-0.6, 3.0, 0.2), (0.4, 1.8, 0), 6),
                     ((-0.6, 3.0, 0.2), (0.4, 1.8, 0), (0.2, 5.5, -0.1), (0.5, 1.6, 0), 6)],
              r=(0.48, 0.24), pads=[((0.2, 6.15, -0.1), 4.6, 3.9, 1.05, 9), ((2.45, 3.95, 0.5), 2.3, 1.9, 0.7, 4)],
              side=(0.4, (2.3, 3.7, 0.5))),
    "c": dict(trunk=[((-2.5, 0.25, -0.3), (2.2, 0.35, 0.6), (0.1, 0.75, 0.3), (1.8, 0.7, 0), 6),
                     ((0.1, 0.75, 0.3), (1.8, 0.7, 0), (0.7, 3.0, 0.0), (0.2, 1.7, 0), 5)],
              r=(0.5, 0.26), pads=[((0.5, 3.7, 0), 6.2, 4.8, 0.95, 12)], arms=[(0.75, (-1.9, 3.4, 0.6))]),
}


def salt_tree(p, mats, seed):
    rng = random.Random(seed)
    spec = TREES[p["id"][-1]]
    m = Mesh()
    trunk = chain(*spec["trunk"])
    n = len(trunk)
    r0, r1 = spec["r"]
    radii = taper(n, r0, r1, flare=r0 * 0.6)
    tube(m, trunk, radii, BARK, 10, twist=1.4, rough=0.3, seed=seed, caps=(False, True))
    strands(m, trunk, radii, 2, 0.7, 0.4, BARK, seed, end=0.97, sides=5)
    # buttress roots: ridges that run down the flared foot of the trunk, then snake out and dive into the ground
    base = trunk[0]
    for k in range(5):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        dd = Vector((math.cos(a), 0, math.sin(a)))
        i0 = 3
        st = trunk[i0] + dd * radii[i0] * 0.55
        L = r0 * rng.uniform(2.4, 3.6)
        mid = Vector((base.x, 0.18, base.z)) + dd * r0 * 1.25
        en = Vector((base.x, -0.22, base.z)) + dd * L + Vector((dd.z, 0, -dd.x)) * rng.uniform(-0.5, 0.5)
        pts = chain((st, Vector((0, -st.y * 1.4, 0)) + dd * 0.2, mid, dd * L * 0.6 + Vector((0, -0.3, 0)), 4),
                    (mid, dd * L * 0.6 + Vector((0, -0.3, 0)), en, (en - mid) * 1.0 + Vector((0, -0.2, 0)), 4))
        tube(m, pts, [radii[i0] * f for f in (0.5, 0.52, 0.5, 0.46, 0.42, 0.36, 0.3, 0.24, 0.2)], BARK, 6, twist=0.4, rough=0.3,
             seed=seed + k, caps=(False, False))
    if "c" in p["id"]:  # the creeping trunk also roots along its length
        for k, i in enumerate((2, 4)):
            q = trunk[i]
            for sgn in (1, -1):
                en = Vector((q.x + 0.3 * sgn, -0.04, q.z + sgn * 0.9))
                tube(m, hermite(q, Vector((0, -0.6, sgn)), en, Vector((0.2, -0.3, sgn)), 4), [radii[i] * 0.4, 0.14, 0.11, 0.09, 0.07],
                     BARK, 5, rough=0.3, seed=seed + 20 + k, caps=(False, False))
    crown = Mesh()
    for j, (c, w, d, th, cn) in enumerate(spec["pads"]):
        clumps = crown_pad(crown, rng, c, w, d, th, cn, seed + 100 * j)
        # branches fan out under the crown from the trunk top (or from the side limb)
        src = trunk[-1] if j == 0 else None
        if j == 1:
            t0 = int(spec["side"][0] * (n - 1))
            st = trunk[t0]
            en = Vector(spec["side"][1])
            pts = hermite(st, Vector((1.5, 0.6, 0.2)), en, Vector((1.2, 0.9, 0)), 6)
            tube(m, pts, [radii[t0] * (0.62 - 0.32 * i / 6) for i in range(7)], BARK, 7, twist=0.6, rough=0.25, seed=seed + 7)
            src = en
        big = sorted(clumps, key=lambda q: -q[1])[: min(5, len(clumps))]
        for i, (q, s, e) in enumerate(big):
            tgt = q + Vector((0, -th * 0.25, 0))
            d0 = (tgt - src)
            pts = hermite(src, Vector((d0.x, 0.2 * d0.length, d0.z)) * 0.8, tgt, Vector((d0.x, d0.length * 0.6, d0.z)).normalized() * d0.length * 0.5, 5)
            rb = (radii[-1] if j == 0 else radii[-1] * 0.7) * 0.8
            tube(m, pts, [rb * (1 - 0.6 * k / 5) for k in range(6)], BARK, 5, rough=0.2, seed=seed + 30 + i, caps=(False, True))
    for t, end in spec.get("arms", []):
        i = int(t * (n - 1))
        en = Vector(end)
        pts = hermite(trunk[i], (en - trunk[i]) * 0.8 + Vector((0, -0.6, 0)), en, Vector((en.x - trunk[i].x, 1.2, en.z - trunk[i].z)) * 0.5, 5)
        tube(m, pts, [radii[i] * (0.5 - 0.3 * k / 5) for k in range(6)], BARK, 5, rough=0.25, seed=seed + 60, caps=(False, True))
    # grass and moss at the foot
    foot = Mesh()
    bx, bz = base.x, base.z
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        pblob(foot, (bx + math.cos(a) * r0 * 1.8, 0.0, bz + math.sin(a) * r0 * 1.8), (r0 * 1.3, 0.14, r0 * 1.0), MOSS, seed=seed + 3 + k,
              rough=0.45, rings=4, segs=9, flat_base=0.2)
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        tuft(foot, (bx + math.cos(a) * r0 * 3, 0, bz + math.sin(a) * r0 * 3), 0.35, 0.5, GRASS, seed + k, count=6)
    parts = [m.object(p["id"], mats, moss=(BARK, MOSS, 0.72), seed=seed), crown.object("crown", mats, moss=None),
             foot.object("foot", mats, moss=None)]
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        sz = rng.uniform(0.55, 0.9)
        parts.append(boulder(mats, (bx + math.cos(a) * r0 * 2.6, -0.1, bz + math.sin(a) * r0 * 2.6), (sz, sz * 0.7, sz * 0.85), BASALT,
                             seed + 70 + k, cuts=5, rings=4, segs=7, moss=(BASALT, MOSS, 0.75)))
    ob = K.join(parts, p["id"])
    return fit(ob, p["size"])


SNAGS = {
    "a": dict(trunk=[((0, 0, 0), (0.6, 2.0, 0), (1.3, 3.4, 0.1), (0.9, 1.6, 0), 8)], r=(0.5, 0.22), top=(0.9, 1.6, 0),
              limbs=[(0.55, (-0.9, 1.0, 0.3), 1.8), (0.7, (1.2, 0.6, -0.4), 2.2), (0.85, (0.4, 1.2, 0.5), 1.5), (1.0, (0.6, 1.0, -0.1), 1.8)],
              depth=2, jag=False),
    "b": dict(trunk=[((0, 0, 0), (0.9, 1.6, 0), (1.1, 2.9, 0.1), (0.8, 1.6, 0), 7)], r=(0.48, 0.3), top=(0.8, 1.6, 0),
              limbs=[(0.45, (1.2, 0.6, 0.4), 1.3), (0.6, (-0.6, 1.0, -0.3), 0.9), (0.35, (1.0, 0.3, -0.6), 0.8)], depth=1, jag=True),
}


def dead_snag(p, mats, seed):
    rng = random.Random(seed)
    spec = SNAGS[p["id"][-1]]
    m = Mesh()
    trunk = chain(*spec["trunk"])
    n = len(trunk)
    r0, r1 = spec["r"]
    radii = taper(n, r0, r1, flare=r0 * 0.4)
    tube(m, trunk, radii, SNAG, 9, twist=0.5, rough=0.32, seed=seed, caps=(False, not spec["jag"]))
    strands(m, trunk, radii, 4, 0.18, 0.26, SNAG, seed, end=0.85)
    # split base: the trunk divides into stripped legs that spread onto the ground
    for k in range(4):
        a = 2 * math.pi * k / 4 + rng.uniform(-0.4, 0.4) + 0.4
        dd = Vector((math.cos(a), 0, math.sin(a)))
        st = trunk[2] + dd * radii[2] * 0.45
        en = dd * r0 * rng.uniform(2.4, 3.6) + Vector((0, -0.03, 0))
        pts = hermite(st, dd * 0.5 + Vector((0, -1.3, 0)), en, dd * 1.4 + Vector((0, -0.3, 0)), 6)
        tube(m, pts, [r0 * (0.62 - 0.46 * i / 6) for i in range(7)], SNAG, 6, rough=0.35, seed=seed + k, caps=(False, False))
    for t, d, L in spec["limbs"]:
        i = min(n - 1, int(t * (n - 1)))
        limb(m, trunk[i], Vector(d), L, radii[i] * 0.5, spec["depth"], rng, SNAG, sides=6, lift=0.3, spread=0.8)
    if spec["jag"]:  # snapped top: splinters of uneven length around the break
        top, tn = trunk[-1], (trunk[-1] - trunk[-2]).normalized()
        for k in range(5):
            a = 2 * math.pi * k / 5
            fr = B.frames(trunk)[-1]
            off = (fr[1] * math.cos(a) + fr[2] * math.sin(a)) * radii[-1] * 0.6
            L = rng.uniform(0.2, 0.75)
            tube(m, [top + off - tn * 0.1, top + off + tn * L * 0.5, top + off * 0.6 + tn * L], [radii[-1] * 0.42, radii[-1] * 0.25, 0.01],
                 SNAG, 4, caps=(False, False))
        tube(m, [top - tn * 0.05, top + tn * 0.02], [radii[-1] * 0.95, radii[-1] * 0.95], SNAG, 9, caps=(False, True))
    foot = Mesh()
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        pblob(foot, (math.cos(a) * r0 * 1.6, 0, math.sin(a) * r0 * 1.6), (r0 * 1.7, 0.18, r0 * 1.3), MOSS, seed=seed + k, rough=0.4,
               rings=4, segs=9, flat_base=0.2)
    tuft(foot, (r0 * 1.8, 0, -r0), 0.3, 0.45, GRASS, seed + 9, count=6)
    ob = K.join([m.object(p["id"], mats, moss=(SNAG, MOSS, 0.85), seed=seed), foot.object("foot", mats, moss=None)], p["id"])
    return fit(ob, p["size"])


# ---------- understory and ground cover ----------

def reed_bed(p, mats, seed):
    """Clumps of painted reed cards: feathery plume reeds at the back, mixed reed and cattail through the middle,
    a low rush clump in front, round a wet-moss hummock and a basalt stone."""
    rng = random.Random(seed)
    m = Mesh()
    w, h, d = p["size"]
    clumps = [((-0.2, -0.35), 1.0, 2), ((0.35, -0.2), 0.92, 2), ((-0.45, 0.15), 0.8, 0), ((0.15, 0.2), 0.86, 3),
              ((0.55, 0.3), 0.62, 0), ((-0.1, 0.55), 0.42, 1), ((0.45, 0.62), 0.36, 1), ((-0.6, -0.3), 0.85, 2),
              ((0.7, -0.15), 0.75, 2), ((0.0, 0.0), 0.95, 0)]
    for k, ((x, z), s_, q) in enumerate(clumps):
        ctuft(m, (x * w * 0.4, 0, z * d * 0.4), h * s_, REED_C, q, seed + k, planes=3, lean=0.12, widen=0.75)
    ctuft(m, (-0.55 * w * 0.4, 0, 0.6 * d * 0.4), h * 0.3, GRASS_C, 1, seed + 20, planes=2)
    pblob(m, (0, 0, 0), (w * 0.33, 0.1, d * 0.3), MOSS, seed=seed, rough=0.4, rings=3, segs=9, flat_base=0.2)
    ob = K.join([m.object(p["id"], mats, moss=None),
                 boulder(mats, (0.15, -0.08, 0.35), (0.7, 0.42, 0.55), BASALT, seed + 3, cuts=5, rings=4, segs=7, moss=(BASALT, MOSS, 0.8))], p["id"])
    return fit(ob, p["size"])


def glowweed(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    w, h, d = p["size"]
    for k in range(6):  # slender glowing stalks fanning out, each ending in a bulb
        a = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        out = Vector((math.cos(a), 0, math.sin(a)))
        base = out * rng.uniform(0.02, 0.1)
        hh = h * rng.uniform(0.65, 0.95)
        tip = base + out * w * rng.uniform(0.18, 0.36) + Vector((0, hh, 0))
        pts = hermite(base, Vector((0, hh, 0)), tip, out * 0.6 + Vector((0, 0.5, 0)), 4)
        tube(m, pts, [0.03, 0.026, 0.022, 0.018, 0.015], GLOWWEED, 4, caps=(False, False))
        pblob(m, tip + Vector((0, 0.03, 0)), (0.045, 0.07, 0.045), GLOWWEED, seed=seed + k, rough=0.1, rings=3, segs=5)
    ctuft(m, (0, 0, 0), h * 0.42, GRASS_C, 2, seed + 2, planes=3, widen=0.8)
    pblob(m, (0, 0, 0), (w * 0.3, 0.14, d * 0.28), MOSS, seed=seed, rough=0.45, rings=4, segs=8, flat_base=0.2)
    parts = [m.object(p["id"], mats, moss=None)]
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        sz = rng.uniform(0.2, 0.32)
        parts.append(boulder(mats, (math.cos(a) * w * 0.32, -0.04, math.sin(a) * d * 0.32), (sz, sz * 0.6, sz * 0.8), BASALT, seed + k,
                             cuts=4, rings=3, segs=6))
    return fit(K.join(parts, p["id"]), p["size"])


def drift_timber(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    logs_pts = []
    logs = [((-1.6, 0.18, -0.35), (1.5, 0.2, 0.3), 0.2), ((-1.3, 0.2, 0.45), (1.2, 0.55, -0.4), 0.17),
            ((-0.6, 0.45, -0.7), (1.6, 0.3, 0.5), 0.15), ((-1.0, 0.1, 0.8), (0.4, 0.12, 0.9), 0.09),
            ((0.2, 0.08, -0.9), (1.4, 0.1, -0.5), 0.08)]
    for k, (a, b, r) in enumerate(logs):
        a, b = Vector(a), Vector(b)
        mid = (a + b) / 2 + Vector((0, 0.06, 0))
        pts = hermite(a, (b - a) * 0.8 + Vector((0, 0.1, 0)), b, (b - a) * 0.8 + Vector((0, -0.1, 0)), 5)
        tube(m, pts, [r * (1.05 - 0.25 * i / 5) for i in range(6)], DRIFT, 7 if r > 0.1 else 5, twist=0.5, rough=0.35,
             seed=seed + k, cap_mat=DRIFT)
        logs_pts.append((pts, r))
        if r > 0.12:  # broken-off branch stubs
            for j in range(2):
                q = pts[rng.randint(1, 4)]
                dd = rand_dir(rng, 0.6)
                tube(m, [q, q + dd * 0.25, q + dd * 0.45], [r * 0.4, r * 0.3, r * 0.18], DRIFT, 4, cap_mat=DRIFT, caps=(False, True))
    # olive weed slung over the logs, hanging down their sides to the sand
    for k, (li, t, side, L, q) in enumerate(((2, 0.8, 1, 0.5, 3), (2, 0.45, -1, 0.42, 0), (1, 0.7, 1, 0.38, 3), (0, 0.3, 1, 0.3, 0),
                                             (2, 0.15, 1, 0.55, 3), (1, 0.25, -1, 0.3, 3))):
        pts, r = logs_pts[li]
        q0 = pts[int(t * (len(pts) - 1))]
        ax = pts[-1] - pts[0]
        fa = math.atan2(ax.z, ax.x) + (0 if side > 0 else math.pi)
        out = Vector((-math.sin(fa), 0, math.cos(fa)))
        for j, sgn in enumerate((1, -1)):  # one card down each flank, so the weed reads slung over the log
            o = out * sgn
            cdrape(m, q0 + Vector((0, r * 0.95, 0)) + o * r * 0.45, (L + r) * (1 if j == 0 else 0.75), WEED_C, q, fa + (0 if sgn > 0 else math.pi),
                   seed + k + j, tilt=0.4, widen=1.3)
    ob = m.object(p["id"], mats, moss=(DRIFT, MOSS, 0.9), seed=seed) if "mossy" in p.get("variants", []) else m.object(p["id"], mats, moss=None)
    return fit(ob, p["size"])


def conch(m, base, size, ang, seed):
    """Spiral shell: a tube wound round a cone, swelling towards the mouth."""
    pts, rr = [], []
    for i in range(7):
        t = i / 6
        a = ang + t * 3.4 * math.pi
        rad = size * 0.35 * t
        pts.append(Vector(base) + Vector((math.cos(a) * rad + (1 - t) * size * 0.9 * math.cos(ang), size * 0.25 + 0.15 * size * (1 - t),
                                          math.sin(a) * rad + (1 - t) * size * 0.9 * math.sin(ang))))
        rr.append(0.01 + size * 0.42 * t ** 1.4)
    tube(m, pts, rr, SHELL, 5, caps=(False, True), cap_mat=SHELL)


def scallop(m, c, R, ang, seed):
    """Ribbed fan shell: radial ridges on a shallow bowl."""
    c = Vector(c)
    hinge = m.vert(c + Vector((math.cos(ang), 0.02, math.sin(ang))) * 1 * R * -0.5)
    ring = []
    k = 9
    for i in range(k + 1):
        a = ang - 1.1 + 2.2 * i / k
        lift = 0.06 * R if i % 2 else 0.0
        ring.append(m.vert(c + Vector((math.cos(a) * R, R * 0.28 + lift, math.sin(a) * R))))
    for i in range(k):
        m.face((hinge, ring[i + 1], ring[i]), ((0.5, 0), (i / k + 1 / k, 1), (i / k, 1)), SHELL)


def shells(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    conch(m, (-0.45, 0, -0.2), 0.16, 0.4, seed)
    conch(m, (0.55, 0, 0.3), 0.1, 2.3, seed + 1)
    scallop(m, (-0.1, 0, 0.3), 0.14, 1.2, seed)
    scallop(m, (0.35, 0, -0.32), 0.1, -0.6, seed)
    # empty shellback crab carapace, spiked rim, with loose legs and a claw
    pblob(m, (0.05, 0.0, -0.05), (0.26, 0.13, 0.2), CRAB, seed=seed, rough=0.12, rings=4, segs=8, flat_base=0.1)
    for k in range(4):
        a = -0.3 + k * 0.7
        q = Vector((0.05 + math.cos(a) * 0.24, 0.05, -0.05 + math.sin(a) * 0.19))
        tube(m, [q, q + Vector((math.cos(a) * 0.12, 0.03, math.sin(a) * 0.12))], [0.025, 0.004], CRAB, 3, caps=(False, False))
    for k, (x, z, a) in enumerate(((-0.55, 0.25, 0.8), (0.6, -0.1, 2.6))):
        q = Vector((x, 0.03, z))
        dd = Vector((math.cos(a), 0.0, math.sin(a)))
        tube(m, [q, q + dd * 0.07, q + dd * 0.16 + Vector((0, 0.02, 0))], [0.025, 0.04, 0.01], CRAB, 4, cap_mat=CRAB)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


def salt_grass(p, mats, seed):
    """Blue-green salt grass in crossed sprite cards, a dry tuft tucked in."""
    m = Mesh()
    w, h, _ = p["size"]
    if "-a" in p["id"]:
        for k, (x, z, s_, q) in enumerate(((0, -0.05, 1.0, 1), (-0.17, 0.12, 0.72, 1), (0.18, 0.1, 0.62, 0))):
            ctuft(m, (x * w, 0, z * w), h * s_, GRASS_C, q, seed + k, planes=3, widen=0.6)
    else:
        ctuft(m, (0, 0, 0), h, GRASS_C, 1, seed, planes=3, widen=0.6)
        ctuft(m, (0.1 * w, 0, 0.15 * w), h * 0.65, GRASS_C, 0, seed + 1, planes=2, widen=0.6)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


def moss_wet(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    w, h, d = p["size"]
    pblob(m, (0, 0, 0), (w * 0.4, h * 0.8, d * 0.38), MOSS, seed=seed, rough=0.45, rings=4, segs=12, tile=0.8, flat_base=0.1)
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        pblob(m, (math.cos(a) * w * 0.32, 0, math.sin(a) * d * 0.3), (w * 0.17, h * 0.55, d * 0.16), MOSS, seed=seed + k + 1,
               rough=0.4, rings=3, segs=8, tile=0.8, flat_base=0.1)
    for k in range(5):  # fleshy succulent rosettes round the edge
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        c = Vector((math.cos(a) * w * 0.43, 0.02, math.sin(a) * d * 0.42))
        ctr = m.vert(c + Vector((0, 0.06, 0)))
        for j in range(5):
            b = 2 * math.pi * j / 5 + k
            o = Vector((math.cos(b), 0, math.sin(b)))
            s = Vector((-o.z, 0, o.x))
            tip = m.vert(c + o * 0.12 + Vector((0, 0.08, 0)))
            l, r = m.vert(c + o * 0.06 + s * 0.04 + Vector((0, 0.05, 0))), m.vert(c + o * 0.06 - s * 0.04 + Vector((0, 0.05, 0)))
            m.face((ctr, r, tip, l), ((0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)), MOSS)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


# ---------- rocks ----------

def vein(m, pts, r=0.022):
    tube(m, pts, [r] * len(pts), VEIN, 3, caps=(False, False))


def surface_path(ob, a, b, n=8, wig=0.12, seed=0.0, out=0.01):
    """Points across an object's surface from glTF direction a to b (ray cast inward from outside)."""
    bpy.context.view_layer.update()
    lo = Vector(ob.bound_box[0])
    hi = Vector(ob.bound_box[6])
    c = (lo + hi) / 2
    R = (hi - lo).length
    pts = []
    for i in range(n + 1):
        t = i / n
        d = Vector(a).lerp(Vector(b), t)
        d += Vector((noise.noise(Vector((t * 4, seed, 0))), noise.noise(Vector((seed, t * 4, 3))), 0)) * wig
        dB = V(*d).normalized()
        ok, loc, nor, _ = ob.ray_cast(c + dB * R, -dB)
        if ok:
            q = loc + nor * out
            pts.append(Vector((q.x, q.z, -q.y)))
    return pts


def add_veins(mats, ob, paths, seed):
    m = Mesh()
    for k, (a, b) in enumerate(paths):
        pts = surface_path(ob, a, b, 9, seed=seed + k)
        if len(pts) > 2:
            vein(m, pts)
    return m.object("veins", mats, moss=None)


def hex_columns(m, cols, mat, seed, tile=1.2, bevel_top=0.05, sides=6):
    """Basalt columns: [(x, z, r, y0, y1, tilt(x, z))]. Tops are tilted planes; returns the top-ring edges for bevelling."""
    rng = random.Random(seed)
    tops = []
    for k, (x, z, r, y0, y1, tilt) in enumerate(cols):
        rot = rng.uniform(0, math.pi)
        lo, hi = [], []
        for j in range(sides):
            a = rot + 2 * math.pi * j / sides
            rr = r * rng.uniform(0.9, 1.05)
            dx, dz = math.cos(a) * rr, math.sin(a) * rr
            lo.append(m.vert((x + dx, y0, z + dz)))
            hi.append(m.vert((x + dx, y1 + tilt[0] * dx + tilt[1] * dz, z + dz)))
        f = m.face(hi[::-1], None, mat, tile)
        for j in range(sides):
            j1 = (j + 1) % sides
            m.face((lo[j], lo[j1], hi[j1], hi[j]), None, mat, tile)
        tops.append(f)
    if bevel_top:
        edges = list({e for f in tops for e in f.edges})
        bmesh.ops.bevel(m.bm, geom=edges, offset=bevel_top, offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
    all_projected(m, tile)


def rock_a(p, mats, seed):
    w, h, d = p["size"]
    ob = compound_rock(mats, (w, h, d), BASALT, seed, moss=(BASALT, MOSS, 0.55))
    veins = add_veins(mats, ob, [((1, 0.6, 0.6), (0.2, 0.1, 1)), ((0.9, 0.2, 0.8), (1, 0.7, -0.2)), ((0.4, 0.4, 1), (-0.3, 0.2, 1))], seed)
    return fit(K.join([ob, veins], p["id"]), p["size"])


def rock_b(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    cols = []
    r = 0.26
    for i in range(-3, 4):
        for j in range(-2, 2):
            x = i * r * 1.55 + (j % 2) * r * 0.78
            z = j * r * 1.35
            if abs(x) > 0.95 or abs(z) > 0.62:
                continue
            top = 0.75 - 0.32 * abs(x) - 0.12 * abs(z) + rng.uniform(-0.12, 0.08)
            tilt = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)) if rng.random() < 0.45 else (0, 0)
            cols.append((x, z, r * rng.uniform(0.85, 0.98), -0.02, max(0.18, top), tilt))
    hex_columns(m, cols, BASALT, seed, tile=1.0, bevel_top=0.035)
    ob = finish(m.object(p["id"], mats, moss=(BASALT, MOSS, 0.85), seed=seed), 40)
    moss = Mesh()
    for k in range(4):  # moss gathered in the joints
        x, z = rng.uniform(-0.8, 0.8), rng.uniform(-0.5, 0.5)
        pblob(moss, (x, 0.35 - 0.2 * abs(x), z), (0.22, 0.08, 0.16), MOSS, seed=seed + k, rough=0.4, rings=3, segs=7)
    return fit(K.join([ob, moss.object("moss", mats, moss=None)], p["id"]), p["size"])


def rock_c(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    cols = []
    r = 0.25
    heights = {}
    for i in range(-2, 3):
        for j in range(-2, 3):
            x = i * r * 1.55 + (j % 2) * r * 0.78
            z = j * r * 1.35
            dist = math.hypot(x / 0.75, z / 0.62)
            if dist > 1.05:
                continue
            top = 3.0 * (1 - 0.55 * dist ** 1.6) * rng.uniform(0.78, 1.0) - 0.3 * max(0, x)
            top = max(0.4, top)
            # stacked drums: a joint part way up, the upper drum slightly offset
            mid = top * rng.uniform(0.35, 0.6)
            tilt = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3))
            rr = r * rng.uniform(0.86, 0.98)
            if top > 1.4:
                cols.append((x, z, rr, -0.02, mid, (0, 0)))
                cols.append((x + rng.uniform(-0.03, 0.03), z + rng.uniform(-0.03, 0.03), rr * 0.97, mid + 0.025, top, tilt))
            else:
                cols.append((x, z, rr, -0.02, top, tilt))
            heights[(x, z)] = top
    hex_columns(m, cols, BASALT, seed, tile=1.1, bevel_top=0.03)
    ob = finish(m.object(p["id"], mats, moss=(BASALT, MOSS, 0.7), seed=seed), 40)
    moss = Mesh()
    for (x, z), top in sorted(heights.items(), key=lambda q: -q[1])[:4]:  # moss caps on the high tops
        pblob(moss, (x, top + 0.02, z), (0.25, 0.08, 0.25), MOSS, seed=seed + x, rough=0.45, rings=3, segs=7, flat_base=0.3)
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        tuft(moss, (math.cos(a) * 0.7, 0, math.sin(a) * 0.6), 0.25, 0.4, GRASS, seed + k, count=5)
    return fit(K.join([ob, moss.object("moss", mats, moss=None)], p["id"]), p["size"])


def box_cloud(rng, lo, hi, n=26, jit=0.06, top=None, corner=0.12):
    """Points on a box with jittered, clipped corners; `top(x, z)` reshapes the top face (slanted breaks)."""
    lo, hi = Vector(lo), Vector(hi)
    ext = hi - lo
    pts = []
    for _ in range(n):
        q = Vector((rng.uniform(lo.x, hi.x), rng.uniform(lo.y, hi.y), rng.uniform(lo.z, hi.z)))
        ax = rng.randrange(3)
        q[ax] = lo[ax] if rng.random() < 0.5 else hi[ax]
        pts.append(q)
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                q = Vector((hi.x if i else lo.x, hi.y if j else lo.y, hi.z if k else lo.z))
                inward = Vector(((-1 if i else 1) * ext.x, (-1 if j else 1) * ext.y, (-1 if k else 1) * ext.z))
                for ax in range(3):
                    r = q.copy()
                    r[ax] += inward[ax] * corner * rng.uniform(0.4, 1.2)
                    pts.append(r)
    out = []
    for q in pts:
        q = q + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jit
        if top and q.y > lo.y + ext.y * 0.5:
            q.y = lo.y + (q.y - lo.y) * top(q.x, q.z)
        out.append(q)
    return out


def slab_stack(mats, p, seed, layers, lean, mat, veins, tall=False):
    """Layered slate: hull-cut slabs, either stacked on a tilted bedding plane or standing as leaning leaves."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    parts = []
    for k in range(layers):
        m = Mesh()
        t = k / max(1, layers - 1)
        if tall:
            hh = h * (1.0 - 0.3 * t) * rng.uniform(0.92, 1.02)
            ww = w * 0.42 * rng.uniform(0.85, 1.0)
            z0 = (t - 0.5) * d * 0.62
            x0 = -0.25 * t * w
            pts = box_cloud(rng, (x0 - ww / 2, 0, z0 - d * 0.2), (x0 + ww / 2, hh, z0 + d * 0.2), 36, 0.09,
                            top=lambda x, z, x0=x0, ww=ww: 1.0 - 0.45 * ((x - x0) / ww + 0.5))
            pts = [Vector((q.x + q.y * math.tan(lean), q.y, q.z)) for q in pts]
        else:
            th = h / layers * 1.1
            ww = w * (1 - 0.18 * k) * rng.uniform(0.9, 1.0)
            dd = d * (0.95 - 0.15 * k)
            ox = rng.uniform(-0.1, 0.1) * w + k * 0.06
            y0 = k * h / layers * 0.92
            pts = box_cloud(rng, (ox - ww / 2, y0, -dd / 2), (ox + ww / 2, y0 + th, dd / 2), 34, 0.1, corner=0.22)
            pts = [Vector((q.x, q.y + (q.x - ox) * math.tan(lean), q.z)) for q in pts]
        pts = [Vector((q.x, max(q.y, 0.0), q.z)) for q in pts]
        hull(m, pts, mat, 1.5)
        parts.append(finish(m.object(f"slab{k}", mats, moss=(mat, MOSS, 0.78), seed=seed + k), 32))
    ob = K.join(parts, p["id"])
    out = [ob]
    if veins:
        out.append(add_veins(mats, ob, veins, seed))
    return K.join(out, p["id"])


def rock_d(p, mats, seed):
    w, h, d = p["size"]
    rng = random.Random(seed)
    ob = slab_stack(mats, p, seed, 3, math.radians(26), SLATE, [((1, 0.3, 0.7), (0.6, 0.6, 1)), ((0.2, 0.5, 1), (0.5, 0.2, 1))])
    moss = Mesh()
    pblob(moss, (-0.5, h * 0.5, 0.0), (0.45, 0.1, 0.35), MOSS, seed=seed, rough=0.4, rings=3, segs=8, flat_base=0.3)
    tuft(moss, (0.7, 0, 0.5), 0.25, 0.35, GRASS, seed, count=5)
    return fit(K.join([ob, moss.object("m", mats, moss=None)], p["id"]), p["size"])


def rock_e(p, mats, seed):
    ob = slab_stack(mats, p, seed, 3, math.radians(22), SLATE, [((0.6, 0.0, 1), (0.1, 1, 1)), ((0.2, -0.3, 1), (-0.2, 0.8, 1)),
                                                               ((1, 0.2, 0.5), (0.5, 0.9, 0.6))], tall=True)
    moss = Mesh()
    rng = random.Random(seed)
    for k in range(3):
        tuft(moss, (rng.uniform(-0.8, 0.8), 0, rng.uniform(0.3, 0.7)), 0.25, 0.35, GRASS, seed + k, count=5)
    pblob(moss, (0.3, 0, 0.5), (0.5, 0.12, 0.3), MOSS, seed=seed, rough=0.4, rings=3, segs=8, flat_base=0.2)
    return fit(K.join([ob, moss.object("m", mats, moss=None)], p["id"]), p["size"])


# ---------- water, lips and undersides ----------

def mere_edge(p, mats, seed):
    """One eighth of a round mere: stepped basalt blocks down to still teal water (8 pieces close the circle;
    the water side faces +Z, the mere centre sits 7.6 m in front of the bank's back edge)."""
    rng = random.Random(seed)
    A = math.radians(45)
    R_in, R_step, R_top, R_bank = 4.1, 5.15, 6.35, 7.6
    zc = R_bank  # mere centre at +z; the arc bulges towards -z
    water_y, step_y, top_y = 0.3, 0.6, 1.0

    def at(r, a, y):
        return Vector((math.sin(a) * r, y, zc - math.cos(a) * r))

    parts = []
    # stepped blocks: a low course at the waterline and a top course of the bank
    for course, (r0, r1, y0, y1, n) in enumerate(((R_in + 0.55, R_step + 0.25, -0.02, step_y, 6), (R_step, R_top + 0.15, -0.02, top_y, 5))):
        cuts = sorted([-A / 2] + [(-A / 2 + A * (k + rng.uniform(0.35, 0.65)) / n) for k in range(n - 1)] + [A / 2])
        for k, (a0, a1) in enumerate(zip(cuts, cuts[1:])):
            m = Mesh()
            g = 0.03
            ys = y1 + rng.uniform(-0.08, 0.06)
            ring = [at(r, a, 0) for r, a in ((r0, a0 + g / r0), (r1, a0 + g / r1), (r1, a1 - g / r1), (r0, a1 - g / r0))]
            lo = [m.vert(q + Vector((0, y0, 0))) for q in ring]
            hi = [m.vert(q + Vector((0, ys + (0.05 if i in (1, 2) else 0), 0))) for i, q in enumerate(ring)]
            m.face(hi[::-1], None, BASALT, 1.2)
            m.face(lo, None, BASALT, 1.2)
            for i in range(4):
                j = (i + 1) % 4
                m.face((lo[i], lo[j], hi[j], hi[i]), None, BASALT, 1.2)
            bmesh.ops.bevel(m.bm, geom=list(m.bm.edges), offset=0.05, offset_type="OFFSET", segments=1, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
            all_projected(m, 1.2)
            for v in m.bm.verts:
                q = Vector((v.co.x, v.co.z, -v.co.y))
                v.co += V(*(Vector((noise.noise(q * 1.7), 0, noise.noise(q * 1.7 + Vector((5, 0, 0))))) * 0.05))
            parts.append(finish(m.object(f"blk{course}{k}", mats, moss=(BASALT, MOSS, 0.85), seed=seed + k), 40))
    m = Mesh()
    # still glowing water (UVs planar so the painted swirl lies flat), lily pads
    nseg, nr = 8, 3
    grid = []
    for i in range(nr + 1):
        r = 2.4 + (R_in + 0.75 - 2.4) * i / nr
        grid.append([(m.vert(at(r, -A / 2 + A * j / nseg, water_y)), None) for j in range(nseg + 1)])
    for i in range(nr):
        for j in range(nseg):
            vs = (grid[i][j][0], grid[i][j + 1][0], grid[i + 1][j + 1][0], grid[i + 1][j][0])
            m.face(vs, [(v.co.x / 4.5, v.co.y / 4.5) for v in vs], WATER)
    for k in range(4):
        a, r = rng.uniform(-A / 2.6, A / 2.6), rng.uniform(3.0, 4.2)
        c = at(r, a, water_y + 0.02)
        rr = rng.uniform(0.18, 0.3)
        ctr = m.vert(c)
        ring = [m.vert(c + Vector((math.cos(b) * rr, 0, math.sin(b) * rr))) for b in (0.35 + 2 * math.pi * j / 7 * 0.92 for j in range(8))]
        for j in range(7):
            m.face((ctr, ring[j + 1], ring[j]), ((0.5, 0.5), (0.5 + 0.5 * math.cos(j + 1), 0.5), (0.5, 0.5 + 0.5 * math.sin(j))), MOSS)
    # the bank behind the top course
    bank = []
    for i in range(3):
        r = R_top - 0.1 + (R_bank - R_top + 0.1) * i / 2
        bank.append([m.vert(at(r, -A / 2 + A * j / nseg, top_y - 0.05 - 0.08 * i)) for j in range(nseg + 1)])
    for i in range(2):
        for j in range(nseg):
            m.face((bank[i][j], bank[i][j + 1], bank[i + 1][j + 1], bank[i + 1][j]), None, GROUND, 2.5)
    for k, (t, rr, hh, q) in enumerate(((0.12, 0.3, 1.25, 3), (0.32, 0.55, 0.55, 1), (0.5, 0.25, 1.1, 2), (0.7, 0.5, 0.5, 1),
                                         (0.88, 0.3, 1.15, 0))):  # reeds and salt grass on the bank
        a = -A / 2 + A * t + rng.uniform(-0.04, 0.04)
        ctuft(m, at(R_top + rr, a, top_y - 0.08), hh, GRASS_C if q == 1 else REED_C, q, seed + k, planes=3, widen=0.8)
    parts.append(m.object("water", mats, moss=None))
    ob = K.join(parts, p["id"])
    return fit(ob, p["size"], scale=False)


def hanging(m, rng, top, length, mat, sides=4, r=0.07, curl=0.2):
    """A hanging strand of weed or moss: a flattened tapering tube that droops from an edge."""
    top = Vector(top)
    end = top + Vector((rng.uniform(-curl, curl), -length, rng.uniform(0, curl)))
    pts = hermite(top, Vector((0, -0.3, 0.6)), end, Vector((0, -length, 0)), 5)
    tube(m, pts, [r * (1.1 - 0.7 * i / 5) for i in range(6)], mat, sides, flat=0.4, rough=0.2, seed=rng.random() * 9, caps=(False, False))


def lip_ledge(p, mats, seed):
    """Isle edge segment along X: ground on top at y = h meets the isle at the back (-Z); slick basalt column ledges
    step out over the front (+Z) and hang down to y = 0; olive weed hangs over the face."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    trickle = "trickle" in p["id"]
    notch = 0.6
    parts = []
    # a row of columns hanging under the top slab, longest at the back, broken and stepped at the front
    m = Mesh()
    cols = []
    r = 0.42
    r = 0.55
    for i in range(-8, 9):
        for j in range(0, 3):
            x = i * r * 1.5 + (j % 2) * r * 0.75
            z = d / 2 - 0.35 - j * r * 1.3
            if abs(x) > w / 2 - 0.3:
                continue
            if trickle and abs(x - notch) < 0.5 and j == 0:
                continue
            # front columns hang longest and ragged; the rows behind end higher, so the face steps back as it drops
            y0 = [rng.uniform(0.0, 1.6), rng.uniform(0.6, 2.2), rng.uniform(1.6, 2.6)][j]
            y1 = h - 0.45 if (j > 0 or rng.random() < 0.7) else h - rng.uniform(0.9, 1.3)
            cols.append((x, z, r * rng.uniform(0.85, 0.98), y0, y1, (rng.uniform(-0.25, 0.25), rng.uniform(0.0, 0.4))))
    hex_columns(m, cols, BASALT, seed, tile=1.3, bevel_top=0.0, sides=5)
    # broken lower ends: drop the bottom rings unevenly so no two columns end alike
    for v in m.bm.verts:
        g = Vector((v.co.x, v.co.z, -v.co.y))
        if g.y < h - 1.4:
            g.y = max(0.0, g.y - 0.35 * (noise.noise(g * 2.3 + Vector((seed, 0, 0))) + 0.5))
            v.co = V(*g)
    body = finish(m.object("cols", mats, moss=(BASALT, MOSS, 0.8), seed=seed), 40)
    parts.append(body)
    # slick top slabs: thick chiselled plates that overhang the column heads, with a notch for the trickle
    xs = [-w / 2, -w / 2 + w * 0.36 + rng.uniform(-0.3, 0.3), (notch - 0.35) if trickle else w * 0.1, (notch + 0.35) if trickle else w * 0.1 + 0.02, w / 2]
    spans = [(xs[0], xs[1]), (xs[1] + 0.05, xs[2])] + ([(xs[3], xs[4])] if trickle else [(xs[2] + 0.05, xs[4])])
    for k, (x0, x1) in enumerate(spans):
        m = Mesh()
        front = d / 2 - 0.1 + rng.uniform(0.0, 0.2)
        K.box(m, (x0, h - 0.6 - rng.uniform(0, 0.15), -d / 2), (x1, h - 0.12, front), BASALT, 1.3)
        bmesh.ops.subdivide_edges(m.bm, edges=list(m.bm.edges), cuts=1, use_grid_fill=True)
        for v in m.bm.verts:
            g = Vector((v.co.x, v.co.z, -v.co.y))
            g += Vector((0, noise.noise(g * 0.9 + Vector((seed, 0, k))) * 0.08, noise.noise(g * 0.7 + Vector((0, seed, k))) * 0.25))
            v.co = V(*g)
        pl = [((x1, h, front), Vector((0.35, 0.3, 1)).normalized()), ((x0, h, front), Vector((-0.4, 0.2, 1)).normalized()),
              ((x0 + (x1 - x0) * 0.5, h - 0.6, front - 0.1), Vector((0, -0.6, 1)).normalized())]
        chisel(m, pl, BASALT, 1.3)
        parts.append(finish(m.object(f"slab{k}", mats, moss=None, seed=seed + k), 40))
    # ground on top, meeting the isle at the back
    m = Mesh()
    nx, nz = 12, 4
    grid = []
    for i in range(nz + 1):
        z = -d / 2 + (d / 2 - 0.1) * i / nz
        row = []
        for j in range(nx + 1):
            x = -w / 2 + w * j / nx
            y = h - 0.08 + 0.06 * noise.noise(Vector((x * 0.8, z * 0.8, seed))) * (i / nz)
            if trickle and abs(x - notch) < 0.4 and i == nz:
                y -= 0.25
            row.append(m.vert((x, y, z)))
        grid.append(row)
    for i in range(nz):
        for j in range(nx):
            m.face((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]), None, GROUND, 3.0)
    # tufted salt grass and reeds along the top, weed and moss hanging over the face
    for k in range(5):
        x = -w / 2 + w * (k + 0.5) / 5 + rng.uniform(-0.3, 0.3)
        if trickle and abs(x - notch) < 0.6:
            x += 1.0
        reeds = k % 2 == 0
        tuft(m, (x, h - 0.08, d / 2 - 0.4 - rng.uniform(0, 1.0)), 0.45, 1.3 if reeds else 0.7, REED if reeds else GRASS, seed + k,
             count=6, width=0.035, lean=0.25 if reeds else 0.7)
    for k in range(14):  # curtains of olive weed and moss hanging over the face, a few long trailers
        x = -w / 2 + 0.4 + (w - 0.8) * (k + rng.uniform(0.1, 0.9)) / 14
        if trickle and abs(x - notch) < 0.55:
            continue
        L = rng.uniform(0.7, 1.6) if k % 4 else rng.uniform(2.0, 2.8)
        cdrape(m, (x, h - 0.06, d / 2 + 0.22), L, WEED_C, (3, 0, 3, 1)[k % 4], 0.0, seed + k, tilt=0.12, widen=0.7)
    # a soft roll of moss along the top edge so the slab never reads as a table top
    run = []
    for j in range(15):
        x = -w / 2 + 0.2 + (w - 0.4) * j / 14
        if trickle and abs(x - notch) < 0.45:
            if len(run) > 2:
                tube(m, run, [0.16] * len(run), MOSS, 5, rough=0.5, seed=seed + j, flat=0.7, cap_mat=MOSS)
            run = []
            continue
        run.append(Vector((x, h - 0.1 + 0.05 * noise.noise(Vector((x, seed, 0))), d / 2 + 0.02 + 0.08 * noise.noise(Vector((x * 1.3, 0, seed))))))
    if len(run) > 2:
        tube(m, run, [0.16] * len(run), MOSS, 5, rough=0.5, seed=seed, flat=0.7, cap_mat=MOSS)
    if trickle:  # thin falling ribbon of glowing water from the notch, splitting near the bottom
        top = Vector((notch, h - 0.3, d / 2 + 0.05))
        pts = hermite(top, Vector((0, 0, 0.8)), top + Vector((0.05, -h + 0.5, 0.45)), Vector((0, -2, 0)), 8)
        tube(m, pts, [0.14 + 0.03 * i / 8 for i in range(9)], WATER, 6, flat=0.3, caps=(False, False))
        for k in (-1, 1):
            tube(m, [q + Vector((0.12 * k, 0, -0.03)) for q in pts[4:]], [0.04, 0.05, 0.05, 0.04, 0.02], WATER, 4, caps=(False, False))
    parts.append(m.object("top", mats, moss=None))
    ob = K.join(parts, p["id"])
    veins = add_veins(mats, ob, [((0.4, -0.3, 1), (0.1, -0.8, 1)), ((-0.5, -0.2, 1), (-0.3, -0.9, 1))], seed)
    return fit(K.join([ob, veins], p["id"]), p["size"], scale=False)


def underside(p, mats, seed):
    """Inverted spire of near-vertical basalt columns whose broken lower ends trace a tapering cone; weed hangs from the
    rim, teal veins fleck the columns and glowing drips gather at the point."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    big = "-a" in p["id"]
    m = Mesh()
    r = 0.62 if big else 0.55
    cols = []
    for i in range(-8, 9):
        for j in range(-8, 9):
            x = i * r * 1.5 + (j % 2) * r * 0.75
            z = j * r * 1.3
            e = math.hypot(x / (w / 2), z / (d / 2))
            if e > 0.97:
                continue
            ex = e + 0.08 * noise.noise(Vector((x, z, seed)))
            y0 = h * min(1.0, max(0.0, ex)) ** 1.35 * rng.uniform(0.9, 1.05)
            y0 = min(y0, h - 0.6)
            cols.append((x, z, r * rng.uniform(0.86, 0.98), h, max(0.0, y0), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4))))
    # columns hang from the top: their "top" in hex_columns is the bottom point here (y1 < y0)
    hex_columns(m, [(x, z, rr, y0, y1, t) for x, z, rr, y0, y1, t in cols], SLATE, seed, tile=2.2, bevel_top=0.0)
    # taper each column's lower drum towards its end so the spire narrows like the sheet
    for v in m.bm.verts:
        g = Vector((v.co.x, v.co.z, -v.co.y))
        if g.y < h - 0.01:
            g.y += 0.0
        v.co = V(*g)
    body = finish(m.object("spire", mats, moss=None, seed=seed), 40)
    # top cap so the isle ground has a lid
    m = Mesh()
    ring = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        ring.append(m.vert((math.cos(a) * w / 2 * 0.99, h + 0.01, math.sin(a) * d / 2 * 0.99)))
    m.face(ring[::-1], None, GROUND, 3.0)
    for k in range(18 if big else 13):  # weed and moss hanging from the rim
        a = 2 * math.pi * k / (18 if big else 13) + rng.uniform(-0.1, 0.1)
        q = (math.cos(a) * w / 2 * 0.97, h + 0.05, math.sin(a) * d / 2 * 0.97)
        cdrape(m, q, rng.uniform(1.2, h * 0.3), WEED_C, (3, 0, 3, 1)[k % 4], a - math.pi / 2, seed + k, tilt=0.1, widen=0.75)
    for k in range(4):  # glowing drips hanging from the point
        x, z = rng.uniform(-0.5, 0.5) * r * 2, rng.uniform(-0.5, 0.5) * r * 2
        L = rng.uniform(0.4, 1.2)
        tube(m, [Vector((x, 0.4, z)), Vector((x, 0.1 - L * 0.5, z)), Vector((x, -L, z))], [0.04, 0.03, 0.01], WATER, 4, caps=(False, False))
        pblob(m, (x, -L - 0.08, z), (0.05, 0.08, 0.05), WATER, seed=seed + k, rings=3, segs=5, rough=0.0)
    ob = K.join([body, m.object("rim", mats, moss=None)], p["id"])
    paths = [((math.cos(a), 0.2, math.sin(a)), (math.cos(a + 0.2), -0.6, math.sin(a + 0.2))) for a in (0.6, 2.2, 4.0)]
    veins = add_veins(mats, ob, paths, seed)
    return fit(K.join([ob, veins], p["id"]), p["size"], scale=False, floor=False)


# ---------- dispatch ----------

def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    pid = p["id"]
    if "salt-tree" in pid:
        return salt_tree(p, mats, seed)
    if "dead-snag" in pid:
        return dead_snag(p, mats, seed)
    fn = {"lg-reed-bed": reed_bed, "lg-glowweed": glowweed, "lg-drift-timber": drift_timber, "lg-shells": shells,
          "lg-moss-wet": moss_wet, "lg-rock-a": rock_a, "lg-rock-b": rock_b, "lg-rock-c": rock_c, "lg-rock-d": rock_d,
          "lg-rock-e": rock_e, "lg-mere-edge": mere_edge}.get(pid)
    if fn:
        return fn(p, mats, seed)
    if "salt-grass" in pid:
        return salt_grass(p, mats, seed)
    if "lip-ledge" in pid:
        return lip_ledge(p, mats, seed)
    if "underside" in pid:
        return underside(p, mats, seed)
    raise ValueError(pid)


CATEGORY = {"tree": "tree", "plant": "bush", "ground": "ground", "rock": "rock", "lip": "lip", "underside": "underside", "water": "water"}


def closeup_render(path, objs):
    lo, hi = B.bounds(objs)
    centre, span = (lo + hi) / 2, max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light, sc.display.shading.color_type = "STUDIO", "TEXTURE"
    sc.display.shading.show_cavity = sc.display.shading.show_shadows = True
    sc.display.shading.show_specular_highlight = False
    sc.view_settings.view_transform, sc.view_settings.exposure = "Standard", 0.45
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.9, 0.9, 0.88)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type, cam.data.ortho_scale = "ORTHO", span * 1.5
    sc.collection.objects.link(cam)
    d = Vector((1, -1.3, 0.75)).normalized()
    cam.location = centre + d * span * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = span * 10
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def closeups(ids, out):
    os.makedirs(out, exist_ok=True)
    for pid in ids:
        p = B.PIECES[pid]
        mats = K.reset()
        ob = build_piece(p, mats)
        bpy.context.view_layer.update()
        print(f"[closeup] {pid}: {K.tris(ob)} tris (manifest {p['tris']}), dims {tuple(round(x, 2) for x in ob.dimensions)}")
        closeup_render(os.path.join(out, f"{pid}.png"), [ob, B.figure(Vector((-p["size"][0] / 2 - 1, 0, 0)))])


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) >= 3 and args[1] == "closeup":
    closeups(args[2].split(","), args[3] if len(args) > 3 else os.path.join(B.KIT_DIR, "closeups"))
else:
    K.build_all(build_piece, extras=[(p["id"], CATEGORY[p["family"]]) for p in B.kit["pieces"]], biome="lagoon")
