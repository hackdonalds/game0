# Ruin nature kit: the natural layer that reclaims the old-world stone. Slab-splitter trees whose roots split and grip
# pale ruinstone slabs, a root-gripped toppled cube, saplings in cracks, ivy, joint grass and moss, precise ruinstone
# rubble (perfect cubes, sheared slabs, fallen ring segments, cracked paving, shard piles), crumbling and paved lips
# over grey rock, and underside spires. Stone matches the old-world kit: pale ruinstone, crisp chamfers, channels cut
# into the stone; in ruin pieces every channel is dead (dull, unlit dark teal, never emissive).
# Built from art/models/nature/ruin/kit.json; painted swatches live in art/textures/biomes/ruin.
# Usage: Blender --background --python scripts/kit/nature-ruin.py -- ruin [closeup <id,id,...> <out dir>]
import bmesh, bpy, math, os, random, sys
from mathutils import Matrix, Quaternion, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
import naturelib as N  # noqa: E402
from kitlib import Mesh, V, hermite, tube  # noqa: E402

# Material slots, in order. "Foliage" sways and is double-sided in the demo; nothing here glows.
MATS = [("RU_Ground", "ground.png", 0), ("RU_Path", "path.png", 0), ("RU_Cliff", "cliff.png", 0), ("RU_Underside", "underside.png", 0),
        ("RU_Stone", "ruinstone.png", 0), ("RU_StoneSheared", "ruinstone-sheared.png", 0),
        ("RU_StoneWeathered", "ruinstone-weathered.png", 0), ("RU_DeadChannel", "dead-channel.png", 0), ("RU_Bark", "ruin-bark.png", 0),
        ("RU_TreeFoliage", "ruin-foliage.png", 0), ("RU_TreeFoliageDark", "ruin-foliage-dark.png", 0), ("RU_IvyFoliage", "ivy.png", 0),
        ("RU_Moss", "moss.png", 0), ("RU_GrassFoliage", "grass.png", 0), ("RU_WiltedGrassFoliage", "wilted-grass.png", 0),
        ("RU_GreyRock", "grey-rock.png", 0), ("RU_Flower", (0.95, 0.94, 0.86), 0),
        # alpha-cutout sprite cards (painted 2x2 atlases in art/textures/foliage)
        ("RU_Broadleaf_Foliage_Card", "../../foliage/broadleaf-green.png", 0),
        ("RU_BroadleafDark_Foliage_Card", "../../foliage/broadleaf-dark.png", 0),
        ("RU_Ivy_Foliage_Card", "../../foliage/ivy-moss.png", 0), ("RU_Grass_Foliage_Card", "../../foliage/grass.png", 0)]
(GROUND, PATH, CLIFF, UNDER, STONE, SHEAR, WEATH, DEAD, BARK, LEAF, LEAF2, IVY, MOSS, GRASS, WILT, GREY, FLOWER,
 LEAF_C, DARK_C, IVY_C, GRASS_C) = range(len(MATS))
GLOW = DEAD          # old-world's channel() defaults to its lit inlay; here the inlay is always the dead channel
CH, CD = 0.5, 0.1    # old-world standard channel width and depth
BEV = 0.045          # crisp chamfer on every stone edge
K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/ruin"), cap_mat=BARK, moss=None)

_make_materials = K.make_materials


def make_materials():
    out = _make_materials()
    for m, (_, tex, _) in zip(out, MATS):  # Workbench shows untextured slots by their viewport colour
        if not isinstance(tex, str):
            m.diffuse_color = (*tex, 1)
    return out


K.make_materials = make_materials
_render = B.render


def render(path, objs_bounds, color_type="OBJECT"):
    bpy.context.scene.display.shading.show_specular_highlight = False  # the game's painted materials are fully rough
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.exposure = 0.45
    return _render(path, objs_bounds, color_type)


B.render = render


# ---------- shared nature helpers (same as nature-lagoon.py) ----------

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


# ---------- alpha-cutout sprite cards (same as nature-lagoon.py) ----------

UP = Vector((0, 1, 0))
VIEW = Vector((1, 0, 1.3)).normalized()  # horizontal direction towards the contact-sheet camera

# Painted sprite bounds inside each 2x2 atlas quadrant (u0, v0, u1, v1; v from the quadrant's bottom), measured from
# the alpha, so tufts stand on their roots and drapes hang from their top edge with no empty margin.
CROP = {
    GRASS_C: [(0.04, 0.14, 0.98, 0.73), (0.01, 0.15, 0.96, 0.78), (0.01, 0.17, 0.95, 0.71), (0.02, 0.17, 0.97, 0.78)],
    IVY_C: [(0.15, 0.10, 0.90, 0.90), (0.09, 0.11, 0.89, 0.90), (0.14, 0.07, 0.91, 0.90), (0.10, 0.07, 0.86, 0.89)],
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
    """Grass clump: `planes` crossed vertical cards of one painted sprite, roots on `base`."""
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
    """Hanging ivy or moss: one card hanging from `top`, its face turned to the glTF angle `facing` (0 faces +Z),
    tipped out at the bottom by `tilt` so it hangs off the edge rather than through it."""
    rng = random.Random(seed)
    rect, asp = sprite(mat, q)
    a = facing + rng.uniform(-0.3, 0.3)
    right = Vector((math.cos(a), 0, math.sin(a)))
    face = Vector((-math.sin(a), 0, math.cos(a)))
    up = (UP - face * tilt).normalized()
    rcard(m, Vector(top) - up * length / 2, right, up, length * asp * widen, length, mat, rect, (face + UP * 0.5).normalized())


def card_mound(m, lobes, mat, picks, seed=0, density=14.0, size=(0.3, 0.5), crown_centre=None, up_bias=0.35, min_cards=6):
    """naturelib.card_crown restricted to some atlas quadrants (pure ivy, not the hanging moss beside it), and with
    as few as `min_cards` cards on a small lobe (a sapling's twig-tip tufts)."""
    rng = random.Random(seed)
    cc = Vector(crown_centre) if crown_centre is not None else sum((Vector(c) for c, _ in lobes), Vector()) / len(lobes)
    span = max(max(r) for _, r in lobes)
    for c, (rx, ry, rz) in lobes:
        c = Vector(c)
        area = 4 * math.pi * (rx * ry + rx * rz + ry * rz) / 3
        for _ in range(max(min_cards, int(area * density / 10))):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1) * 0.8 + 0.15, rng.gauss(0, 1))).normalized()
            p = c + Vector((d.x * rx, d.y * ry, d.z * rz)) * rng.uniform(0.55, 1.0) ** 0.5
            out = p - cc
            out = (out / span + Vector((0, up_bias, 0))).normalized() if out.length > 1e-4 else UP
            face = (d * 0.6 + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.2, 0.4), rng.uniform(-0.4, 0.4)))).normalized()
            right = face.cross(UP)
            right = right.normalized() if right.length > 1e-3 else Vector((1, 0, 0))
            up = right.cross(face).normalized()
            roll = rng.uniform(-0.6, 0.6)
            right, up = right * math.cos(roll) + up * math.sin(roll), up * math.cos(roll) - right * math.sin(roll)
            q = rng.choice(picks)
            sz = rng.uniform(*size)
            rcard(m, p, right, up, sz, sz, mat, ((q % 2) / 2, (q // 2) / 2, (q % 2 + 1) / 2, (q // 2 + 1) / 2), out)


def tuft(m, centre, radius, height, mat, seed, count=7, width=0.035, lean=0.6, tip_mat=None):
    """Grass tuft as crossed sprite cards: green meadow grass, or dry alpine grass where it has wilted."""
    rng = random.Random(seed)
    q = 0 if mat == WILT else rng.choice((2, 3))
    ctuft(m, centre, height * 1.1, GRASS_C, q, seed, planes=3 if count >= 6 else 2, widen=0.8)


def hanging(m, rng, top, length, mat, sides=4, r=0.07, curl=0.2):
    """A hanging strand of weed or moss: a flattened tapering tube that droops from an edge."""
    top = Vector(top)
    end = top + Vector((rng.uniform(-curl, curl), -length, rng.uniform(0, curl)))
    pts = hermite(top, Vector((0, -0.3, 0.6)), end, Vector((0, -length, 0)), 5)
    tube(m, pts, [r * (1.1 - 0.7 * i / 5) for i in range(6)], mat, sides, flat=0.4, rough=0.2, seed=rng.random() * 9, caps=(False, False))


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


# ---------- old-world stone helpers (copied from old-world.py so the rubble matches its ashlar) ----------

def to_object(m, name, mats, recalc=True):
    """Mesh.object without moss or smoothing; recalc=False keeps hand-wound single-sided sheets facing out."""
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f, t in m.project:
        if f.is_valid:
            K.box_uv(f, m.uv, t)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def boolean(ob, cutter):
    mod = ob.modifiers.new("cut", "BOOLEAN")
    mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
    mod.use_self = True
    apply_mods(ob)


def uv_stone(ob, off=(0.0, 0.0), tu=4.0, tv=2.0, mats=(STONE, WEATH)):
    """Box-project stone faces (the grain swatch is 2:1, so 4 x 2 m per repeat), offset per block for variety."""
    me = ob.data
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        if p.material_index not in mats:
            continue
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[a] / tu + off[0], co[b] / tv + off[1])


def bevel_bm(bm, w=BEV):
    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=w, offset_type="OFFSET", segments=1,
                    profile=0.5, affect="EDGES", clamp_overlap=True)


class Frame:
    """A face of a piece: origin, in-plane axes u and v and outward normal n (glTF), and its size (W, H)."""

    def __init__(self, o, u, v, n, W, H):
        self.o, self.u, self.v, self.n = Vector(o), Vector(u), Vector(v), Vector(n)
        self.W, self.H = W, H
        assert self.u.cross(self.v).dot(self.n) > 0.99

    def p(self, a, b, d=0.0):
        return self.o + self.u * a + self.v * b + self.n * d


def prism(m, f, quad_pts, d0, d1, mat=STONE):
    """Closed prism over a 2D outline in frame f between depths d0 < d1 (along the outward normal)."""
    lo = [m.vert(f.p(a, b, d0)) for a, b in quad_pts]
    hi = [m.vert(f.p(a, b, d1)) for a, b in quad_pts]
    m.face(hi, None, mat)
    m.face(lo[::-1], None, mat)
    n = len(quad_pts)
    for i in range(n):
        j = (i + 1) % n
        m.face((lo[i], lo[j], hi[j], hi[i]), None, mat)


def arc_prism(m, f, cu, cv, r0, r1, a0, a1, d0, d1, seg):
    full = a1 - a0 >= 2 * math.pi - 1e-6
    n = seg
    rows = []
    for i in range(n if full else n + 1):
        a = a0 + (a1 - a0) * i / n
        ca, sa = math.cos(a), math.sin(a)
        rows.append([m.vert(f.p(cu + r * ca, cv + r * sa, d)) for r, d in ((r0, d0), (r1, d0), (r1, d1), (r0, d1))])
    for i in range(n):
        A, Bq = rows[i], rows[(i + 1) % len(rows)]
        for k in range(4):
            k1 = (k + 1) % 4
            m.face((A[k], A[k1], Bq[k1], Bq[k]), None, STONE)
    if not full:
        m.face(rows[0], None, STONE)
        m.face(rows[-1][::-1], None, STONE)


def segs_for(r, w):
    return max(12, int(2 * math.pi * r / (0.5 if w >= 0.5 else 0.45)))


def channel(cm, im, f, shapes, w=CH, d=CD, mat=GLOW, both_ends_out=0.3):
    """Cut a channel pattern into face f (cutters into cm) and lay the lit inlay just above the channel floor (im).
    shapes: ("line", u0, v0, u1, v1) along u or v, ("ring", cu, cv, r[, a0, a1]) as centrelines."""
    h = w / 2
    mg = 0.08 if w >= 0.5 else 0.055
    for i, s in enumerate(shapes):
        sd = d - 0.006 - 0.0015 * i  # inlay depth, staggered so overlapping inlays never z-fight
        if s[0] == "line":
            _, u0, v0, u1, v1 = s
            horiz = abs(v1 - v0) < 1e-6
            lo, hi = (min(u0, u1), max(u0, u1)) if horiz else (min(v0, v1), max(v0, v1))
            lim = f.W if horiz else f.H
            clo = lo - both_ends_out if lo <= 1e-6 else lo
            chi = hi + both_ends_out if hi >= lim - 1e-6 else hi
            ilo, ihi = max(lo, 0.0), min(hi, lim)
            c = v0 if horiz else u0
            if horiz:
                prism(cm, f, [(clo, c - h), (chi, c - h), (chi, c + h), (clo, c + h)], -d, 0.4)
                q = [(ilo, c - h + mg), (ihi, c - h + mg), (ihi, c + h - mg), (ilo, c + h - mg)]
            else:
                prism(cm, f, [(c - h, clo), (c + h, clo), (c + h, chi), (c - h, chi)], -d, 0.4)
                q = [(c - h + mg, ilo), (c + h - mg, ilo), (c + h - mg, ihi), (c - h + mg, ihi)]
            vs = [im.vert(f.p(a, b, -sd)) for a, b in q]
            L = ihi - ilo
            uvs = [(0, 0), (L / 3, 0), (L / 3, 1), (0, 1)] if horiz else [(0, 0), (0, 1), (L / 3, 1), (L / 3, 0)]
            im.face(vs, uvs, mat)
        else:
            cu, cv, r = s[1], s[2], s[3]
            a0, a1 = (s[4], s[5]) if len(s) > 4 else (0.0, 2 * math.pi)
            n = max(4, round(segs_for(r, w) * (a1 - a0) / (2 * math.pi)))
            arc_prism(cm, f, cu, cv, r - h, r + h, a0, a1, -d, 0.4, n)
            ring = []
            for k in range(n + 1):
                a = a0 + (a1 - a0) * k / n
                ca, sa = math.cos(a), math.sin(a)
                ring.append((im.vert(f.p(cu + (r - h + mg) * ca, cv + (r - h + mg) * sa, -sd)),
                             im.vert(f.p(cu + (r + h - mg) * ca, cv + (r + h - mg) * sa, -sd)), r * a / 3))
            for (i0, o0, u0), (i1, o1, u1) in zip(ring, ring[1:]):
                im.face((i0, o0, o1, i1), [(u0, 0), (u0, 1), (u1, 1), (u1, 0)], mat)


def spline(ctrl, n=5):
    P = [Vector(c) for c in ctrl]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


# ---------- ruinstone: chamfered blocks, dead channels, clean shears ----------

def xform(ob, rot=(0, 0, 0), loc=(0, 0, 0)):
    """Bake a glTF-space rotation (degrees about X, Y, Z; Y is up) and translation into the mesh."""
    rx, ry, rz = (math.radians(a) for a in rot)
    R = Matrix.Rotation(ry, 4, "Z") @ Matrix.Rotation(-rz, 4, "Y") @ Matrix.Rotation(rx, 4, "X")
    ob.data.transform(Matrix.Translation(V(*loc)) @ R)
    ob.data.update()
    return ob


def box_frames(lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    W, H, D = hi - lo
    return {"front": Frame((lo.x, lo.y, hi.z), (1, 0, 0), (0, 1, 0), (0, 0, 1), W, H),
            "back": Frame((hi.x, lo.y, lo.z), (-1, 0, 0), (0, 1, 0), (0, 0, -1), W, H),
            "right": Frame((hi.x, lo.y, hi.z), (0, 0, -1), (0, 1, 0), (1, 0, 0), D, H),
            "left": Frame((lo.x, lo.y, lo.z), (0, 0, 1), (0, 1, 0), (-1, 0, 0), D, H),
            "top": Frame((lo.x, hi.y, hi.z), (1, 0, 0), (0, 0, -1), (0, 1, 0), W, D)}


def shear(ob, co, no, fill=True, mat=SHEAR):
    """Slice a piece clean through (removing the +normal side) and cap the cut flat, like cut glass."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V(*co), plane_no=V(*Vector(no).normalized()),
                           clear_outer=True, dist=1e-5)
    if fill:
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            for f in bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]:
                f.material_index = mat
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def stone(mats, lo, hi, seed, chans=(), shears=(), bev=BEV, cw=0.22, cd=0.06, name="blk", tu=2.0, tv=1.0, mat=STONE):
    """A chamfered ruinstone block with dead channels cut in (`chans`: [(face, shapes)]) and optional clean shears."""
    m = Mesh()
    K.box(m, lo, hi, mat)
    bevel_bm(m.bm, bev)
    ob = to_object(m, name, mats)
    inlay = None
    if chans:
        fr = box_frames(lo, hi)
        cm, im = Mesh(), Mesh()
        for face, shapes in chans:
            channel(cm, im, fr[face], shapes, cw, cd, DEAD, both_ends_out=0.3)
        cutter = to_object(cm, "cutter", mats)
        boolean(ob, cutter)
        bpy.data.objects.remove(cutter)
        inlay = to_object(im, name + ".inlay", mats, recalc=False)
    for co, no in shears:
        shear(ob, co, no)
        if inlay:
            shear(inlay, co, no, fill=False)
    rng = random.Random(seed)
    uv_stone(ob, (rng.random() * 3, rng.random() * 2), tu, tv, mats=(STONE, WEATH, SHEAR))
    parts = [ob] + ([inlay] if inlay is not None and len(inlay.data.polygons) else [])
    return finish(K.join(parts, name), 50)


def split(mats, make, co, no, a, b):
    """Build a block twice and shear it into two halves along one plane; a and b are (rot, loc) for each half."""
    out = []
    for sgn, (rot, loc) in ((1, a), (-1, b)):
        ob = make([(co, Vector(no) * sgn)])
        out.append(xform(ob, rot, loc))
    return out


def ground_clip(ob):
    return shear(ob, (0, 0, 0), (0, -1, 0))


def grow_moss(m, rng, pts, size=0.3, seed=0.0):
    for k, q in enumerate(pts):
        s = size * rng.uniform(0.7, 1.2)
        pblob(m, q, (s, s * 0.35, s * 0.8), MOSS, tile=0.9, seed=seed + k, rough=0.45, rings=3, segs=7, flat_base=0.2)


# ---------- leaves, ivy, saplings ----------

IVY_LEAF = [(0, 0), (0.42, 0.2), (0.3, 0.42), (0.34, 0.7), (0, 1.0), (-0.34, 0.7), (-0.3, 0.42), (-0.42, 0.2)]
OVAL_LEAF = [(0, 0), (0.3, 0.18), (0.36, 0.48), (0.22, 0.8), (0, 1.0), (-0.22, 0.8), (-0.36, 0.48), (-0.3, 0.18)]


def leaf(m, base, along, up, L, mat=IVY, shape=IVY_LEAF, fold=0.12, uv=(0.18, 0.08, 0.82, 0.92)):
    """A shaped leaf card (fan round a raised mid-rib point), mapped onto the painted leaf in the swatch."""
    base = Vector(base)
    v = Vector(along).normalized()
    u = v.cross(Vector(up))
    if u.length < 1e-4:
        u = v.orthogonal()
    u.normalize()
    n = u.cross(v).normalized()
    if n.dot(Vector(up)) < 0:
        n = -n
    c = m.vert(base + v * L * 0.45 + n * L * fold)
    vs = [m.vert(base + u * x * L + v * y * L) for x, y in shape]
    u0, v0, u1, v1 = uv
    uvs = [(u0 + (x + 0.5) * (u1 - u0), v0 + y * (v1 - v0)) for x, y in shape]
    cuv = (u0 + 0.5 * (u1 - u0), v0 + 0.45 * (v1 - v0))
    for i in range(len(vs)):
        j = (i + 1) % len(vs)
        m.face((c, vs[i], vs[j]), (cuv, uvs[i], uvs[j]), mat)


def ivy_strand(m, rng, top, length, nleaves=0, out=Vector((0, 0, 1)), r=0.025, sway=0.25, widen=0.7):
    """A curtain of trailing ivy hanging from an edge: a painted ivy card facing out from the wall."""
    o = Vector(out)
    cdrape(m, Vector(top) + o * 0.05, length, IVY_C, rng.choice((2, 2, 0)), math.atan2(-o.x, o.z), seed=rng.random() * 99, tilt=0.1,
           widen=widen)


def sapling(m, rng, base, height, seed, leaf_len=0.15, shape=OVAL_LEAF, per_tip=2, limbs=3, lean=(0.0, 0.0), r=0.045):
    base = Vector(base)
    top = base + Vector((lean[0] * height, height * 0.72, lean[1] * height))
    trunk = hermite(base, Vector((0, height * 0.8, 0)), top, Vector((rng.uniform(-0.3, 0.3), height * 0.7, rng.uniform(-0.3, 0.3))), 5)
    tube(m, trunk, [r * (1 - 0.6 * i / 5) for i in range(6)], BARK, 5, rough=0.15, seed=seed, caps=(False, True))
    tips = [trunk[-1]]
    for k in range(limbs):
        i = 2 + k * 3 // max(1, limbs)
        a = 2 * math.pi * k / limbs + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), 0.9, math.sin(a)))
        tips += limb(m, trunk[min(i, 5)], d, height * 0.3, r * 0.45, 1, rng, BARK, sides=3, lift=0.5, spread=0.7, kids=2, segs=3, rough=0.1)
    # a small leafy card crown on every twig tip, shading as one soft mass round the sapling's heart
    lobes = [(t + Vector((0, leaf_len * 0.3, 0)), (leaf_len * 0.8, leaf_len * 0.6, leaf_len * 0.8)) for t in tips]
    card_mound(m, lobes, LEAF_C, (0, 1, 2, 3), seed=seed, density=0.0, size=(leaf_len * 1.7, leaf_len * 2.4),
               crown_centre=base + Vector((0, height * 0.45, 0)), up_bias=0.5, min_cards=per_tip + 1)


# ---------- trees ----------

def crown_pad(m, rng, centre, w, d, thick, n, mats_, seed, droop=0.45, tile=1.25, round_=0.75, density=14.0):
    """Clumped crown of broadleaf cards over rounded masses: sunlit yellow-green cards over every clump, a deeper
    layer of dark green cards under the lower and outer clumps, a few clumps riding on top. Returns clump centres."""
    c = Vector(centre)
    gap = math.sqrt(w * d / n) * 0.66
    lobes, low, out = [], [], []
    for i, (x, z) in enumerate(ellipse_points(rng, n, w * 0.8, d * 0.8, gap)):
        e = math.hypot(x / (w / 2), z / (d / 2))
        s = gap * rng.uniform(0.78, 0.98) * (1.08 - 0.25 * e)
        hy = min(s * round_ * rng.uniform(0.85, 1.05), thick * 0.7)
        y = c.y - droop * thick * e ** 2 + rng.uniform(-0.12, 0.12) * thick
        q = Vector((c.x + x, y, c.z + z))
        lobes.append((q, (s, hy, s * rng.uniform(0.85, 1.05))))
        low.append((q - Vector((0, hy * 0.45, 0)), (s * 0.95, hy * 0.7, s * 0.95)))
        out.append((q, s, e))
    for x, z in ellipse_points(rng, max(1, n // 4), w * 0.5, d * 0.5, gap * 0.9):
        s = gap * rng.uniform(0.6, 0.75)
        lobes.append((Vector((c.x + x, c.y + thick * 0.35, c.z + z)), (s, s * 0.65, s)))
    cc = c - Vector((0, thick * 0.8, 0))
    size = (gap * 0.85, gap * 1.45)
    N.card_crown(m, low, DARK_C, seed=seed + 5, density=density * 0.5, size=size, crown_centre=cc, up_bias=0.15)
    N.card_crown(m, lobes, LEAF_C, seed=seed, density=density, size=size, crown_centre=cc, up_bias=0.4)
    return out


def branches(m, src, clumps, th, rb, seed, count=5):
    big = sorted(clumps, key=lambda q: -q[1])[:count]
    for i, (q, s, e) in enumerate(big):
        tgt = q + Vector((0, -th * 0.25, 0))
        d0 = tgt - src
        pts = hermite(src, Vector((d0.x, 0.25 * d0.length, d0.z)) * 0.8, tgt,
                      Vector((d0.x, d0.length * 0.6, d0.z)).normalized() * d0.length * 0.5, 5)
        tube(m, pts, [rb * (1 - 0.6 * k / 5) for k in range(6)], BARK, 5, rough=0.2, seed=seed + 30 + i, caps=(False, True))


def root_path(m, ctrl, r0, r1, seed, sides=5):
    pts = spline(ctrl, 2)
    n = len(pts) - 1
    tube(m, pts, [r0 + (r1 - r0) * (i / n) ** 0.8 for i in range(n + 1)], BARK, sides, twist=0.5, rough=0.25, seed=seed, caps=(False, False))


SPLITTERS = {
    "a": dict(slabs=[((-2.0, 0, -1.5), (2.0, 0.7, 1.5), (0.1, 0, 0), (1, 0, 0.3), 5.0, 0.28)],
              trunk=[((0.1, 0, 0), (0.1, 2.0, 0), (-0.35, 2.6, 0.3), (-0.7, 1.5, 0.2), 6),
                     ((-0.35, 2.6, 0.3), (-0.7, 1.5, 0.2), (0.3, 4.7, 0), (0.9, 1.6, -0.2), 6)],
              r=(0.66, 0.3), pad=((0.1, 6.0, 0), 9.4, 7.0, 1.9, 13), roots=7),
    "b": dict(slabs=[((-1.9, 0, -1.2), (-0.1, 0.55, 1.0), (-0.8, 0, 0), (1, 0, -0.4), 4.0, 0.15),
                     ((0.1, 0, -1.0), (1.8, 0.5, 1.2), (0.95, 0, 0), (1, 0, 0.5), 4.0, 0.15)],
              trunk=[((0.0, 0, 0.1), (0.6, 2.0, 0), (0.5, 2.6, -0.2), (0.7, 1.5, 0), 6),
                     ((0.5, 2.6, -0.2), (0.7, 1.5, 0), (1.3, 4.9, -0.1), (0.4, 1.4, 0), 6)],
              r=(0.5, 0.24), pad=((1.3, 5.9, -0.1), 6.0, 4.8, 1.5, 11), roots=6),
}


def slab_top(slabs, x, z):
    """Approximate top height of the tilted slab halves at (x, z) (0 off the slabs)."""
    best = 0.0
    for lo, hi, co, no, tilt, gap in slabs:
        if lo[0] - gap - 0.1 <= x <= hi[0] + gap + 0.1 and lo[2] - 0.1 <= z <= hi[2] + 0.1:
            cx = co[0]
            best = max(best, hi[1] * math.cos(math.radians(tilt)) + 0.04 - abs(x - cx) * math.sin(math.radians(tilt)) * 0.9 + 0.03)
    return best


def slab_splitter(p, mats, seed):
    rng = random.Random(seed)
    spec = SPLITTERS[p["id"][-1]]
    parts = []
    for lo, hi, co, no, tilt, gap in spec["slabs"]:
        def make(sh, lo=lo, hi=hi):
            return stone(mats, lo, hi, seed + lo[0], shears=sh, bev=0.06, tu=3.0, tv=1.5)
        halves = split(mats, make, co, no, ((0, 0, tilt), (-gap, 0.04, 0)), ((0, 0, -tilt), (gap, 0.04, 0)))
        # tilt about the crack, not the origin: shift each half so its crack edge stays near the crack
        for h_ob, sgn in zip(halves, (1, -1)):
            dx = co[0] * (1 - math.cos(math.radians(tilt)))
            dy = -co[0] * math.sin(math.radians(tilt)) * sgn
            h_ob.data.transform(Matrix.Translation(V(dx * sgn * 0, dy, 0)))
            parts.append(ground_clip(h_ob))
    m = Mesh()
    trunk = chain(*spec["trunk"])
    n = len(trunk)
    r0, r1 = spec["r"]
    radii = taper(n, r0, r1, flare=r0 * 0.45)
    tube(m, trunk, radii, BARK, 10, twist=1.6, rough=0.3, seed=seed, caps=(False, True))
    strands(m, trunk, radii, 2, 0.9, 0.4, BARK, seed, end=0.95, sides=4)
    # roots: out of the crack, over the slab halves, over their edges and down into the ground
    slabs = spec["slabs"]
    xs = [s[0][0] for s in slabs] + [s[1][0] for s in slabs]
    zs = [s[0][2] for s in slabs] + [s[1][2] for s in slabs]
    X0, X1, Z0, Z1 = min(xs) - 0.3, max(xs) + 0.3, min(zs), max(zs)
    base = trunk[0]
    for k in range(spec["roots"]):
        a = 2 * math.pi * k / spec["roots"] + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(a), 0, math.sin(a)))
        rr = radii[2] * rng.uniform(0.38, 0.5)
        st = trunk[2] + d * radii[2] * 0.4
        tx = ((X1 if d.x > 0 else X0) - base.x) / d.x if abs(d.x) > 1e-3 else 99
        tz = ((Z1 if d.z > 0 else Z0) - base.z) / d.z if abs(d.z) > 1e-3 else 99
        te = min(tx, tz)
        ctrl = [st]
        for f in (0.35, 0.7, 0.97):
            q = base + d * te * f
            ctrl.append(Vector((q.x, slab_top(slabs, q.x, q.z) + rr * 0.8, q.z)))
        e = base + d * (te + 0.15)
        ctrl += [Vector((e.x, max(0.25, slab_top(slabs, e.x - d.x * 0.3, e.z - d.z * 0.3) * 0.45), e.z)),
                 Vector((base.x, -0.15, base.z)) + d * (te + rng.uniform(0.6, 1.2)) + Vector((d.z, 0, -d.x)) * rng.uniform(-0.4, 0.4)]
        root_path(m, ctrl, rr, rr * 0.3, seed + k)
    for sgn in (1, -1):  # two roots dive straight down the crack
        ctrl = [trunk[1], base + Vector((0.05, 0.25, sgn * (Z1 - base.z) * 0.6)), base + Vector((0.1, -0.15, sgn * (Z1 - base.z + 0.8)))]
        root_path(m, ctrl, radii[1] * 0.4, radii[1] * 0.15, seed + 40 + sgn)
    crown = Mesh()
    c, w, d, th, cn = spec["pad"]
    clumps = crown_pad(crown, rng, c, w, d, th, cn, [LEAF, LEAF2], seed)
    branches(m, trunk[-1], clumps, th, radii[-1] * 0.8, seed)
    foot = Mesh()
    grow_moss(foot, rng, [Vector((X0 + 0.4, 0.0, Z1 - 0.1)), Vector((X1 - 0.3, 0.0, Z0 + 0.2)), base + Vector((0.4, 0.62, 0.5))], 0.45, seed)
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        tuft(foot, base + Vector((math.cos(a) * (X1 - X0) * 0.6, 0, math.sin(a) * (Z1 - Z0) * 0.6)), 0.3, 0.5, GRASS, seed + k, count=6)
    sapling(foot, rng, Vector((X1 + 0.3, 0, 0.3)), 0.7, seed + 9, leaf_len=0.14, limbs=2, per_tip=2, r=0.03)
    parts += [m.object(p["id"], mats, moss=(BARK, MOSS, 0.8), seed=seed), crown.object("crown", mats, moss=None), foot.object("foot", mats, moss=None)]
    return fit(K.join(parts, p["id"]), p["size"])


def root_gripped_block(p, mats, seed):
    rng = random.Random(seed)
    lo, hi = (-0.2, 0, -1.0), (1.8, 2.0, 1.0)
    face = [("line", 1.0, 0, 1.0, 0.5), ("ring", 1.0, 1.0, 0.39), ("line", 1.0, 1.5, 1.0, 2.0), ("line", 0, 1.0, 0.5, 1.0),
            ("line", 1.5, 1.0, 2.0, 1.0)]
    blk = stone(mats, lo, hi, seed, chans=[("front", face), ("right", face), ("top", [("line", 1.0, 0, 1.0, 2.0)])], bev=0.06,
                cw=0.22, cd=0.07, tu=3.0, tv=1.5)
    xform(blk, (0, 12, 4), (0, -0.06, 0))
    ground_clip(blk)
    m = Mesh()
    trunk = chain(((-0.75, 0, 0.35), (0.3, 1.5, 0.1), (-0.5, 2.0, 0.1), (0.25, 1.2, -0.1), 5),
                  ((-0.5, 2.0, 0.1), (0.25, 1.2, -0.1), (0.4, 3.0, -0.05), (0.5, 1.0, 0), 4))
    n = len(trunk)
    radii = taper(n, 0.34, 0.14, flare=0.14)
    tube(m, trunk, radii, BARK, 8, twist=1.4, rough=0.3, seed=seed, caps=(False, True))
    strands(m, trunk, radii, 2, 1.1, 0.4, BARK, seed, sides=4)
    t5 = trunk[5]
    roots = [  # over the top, over the edges and down the faces to the ground
        ([t5, (0.5, 2.18, 0.35), (1.25, 2.2, 0.9), (1.4, 2.0, 1.14), (1.5, 1.0, 1.16), (1.6, 0.1, 1.25), (1.9, -0.12, 1.7)], 0.17, 0.05),
        ([t5, (0.6, 2.2, -0.3), (1.45, 2.24, -0.7), (1.98, 2.0, -0.7), (2.0, 1.0, -0.55), (2.0, 0.1, -0.4), (2.5, -0.12, -0.3)], 0.15, 0.05),
        ([t5, (0.2, 2.16, -0.55), (0.05, 2.05, -1.12), (0.15, 1.0, -1.16), (0.25, -0.12, -1.6)], 0.13, 0.04),
        ([trunk[4], (-0.25, 1.4, 0.95), (-0.15, 0.6, 1.12), (0.1, -0.12, 1.55)], 0.12, 0.04),
        ([trunk[1], (-1.3, 0.1, 0.8), (-1.6, -0.12, 1.2)], 0.14, 0.05),
        ([trunk[1], (-1.2, 0.1, -0.2), (-1.7, -0.12, -0.5)], 0.13, 0.05),
        ([trunk[2], (-0.6, 0.3, -0.8), (-0.6, -0.12, -1.4)], 0.11, 0.04),
    ]
    for k, (ctrl, a, b) in enumerate(roots):
        root_path(m, [Vector(c) for c in ctrl], a, b, seed + k)
    crown = Mesh()
    clumps = crown_pad(crown, rng, (0.45, 3.35, -0.05), 2.9, 2.4, 1.0, 7, [LEAF, LEAF2], seed, droop=0.35, round_=0.8)
    branches(m, trunk[-1], clumps, 1.0, radii[-1] * 0.8, seed, 4)
    foot = Mesh()
    grow_moss(foot, rng, [Vector((0.9, 2.02, 0.2)), Vector((1.7, 0.0, 1.2)), Vector((-1.0, 0.0, 0.6))], 0.35, seed)
    tuft(foot, (2.0, 0, 0.9), 0.3, 0.45, GRASS, seed + 3, count=6)
    tuft(foot, (-1.2, 0, -0.6), 0.3, 0.45, GRASS, seed + 4, count=6)
    parts = [blk, m.object(p["id"], mats, moss=(BARK, MOSS, 0.85), seed=seed), crown.object("crown", mats, moss=None),
             foot.object("foot", mats, moss=None)]
    return fit(K.join(parts, p["id"]), p["size"])


# ---------- saplings, ivy and ground cover ----------

def sapling_piece(p, mats, seed):
    rng = random.Random(seed)
    k = p["id"][-1]
    parts = []
    m = Mesh()
    if k == "a":  # growing from a split small block with a dead channel line
        def make(sh):
            return stone(mats, (-0.32, 0, -0.3), (0.32, 0.55, 0.3), seed, chans=[("front", [("line", 0.2, 0, 0.2, 0.55)])], shears=sh,
                         bev=0.03, cw=0.09, cd=0.03, tu=1.5, tv=0.75)
        parts += [ground_clip(h) for h in split(mats, make, (0.02, 0, 0), (1, 0, 0.15), ((0, 4, 7), (-0.05, 0.02, 0)), ((0, -3, -6), (0.06, 0.02, 0)))]
        sapling(m, rng, (0.02, 0.35, 0), 1.0, seed, leaf_len=0.15, limbs=3, per_tip=2)
        grow_moss(m, rng, [Vector((0.02, 0.5, 0.05)), Vector((0.35, 0, 0.3))], 0.14, seed)
    elif k == "b":  # taller, broad leaves out of cracked paving shards
        for j, (a, tilt) in enumerate(((0.3, 8), (2.4, -10), (4.3, 6))):
            d = Vector((math.cos(a), 0, math.sin(a)))
            ob = stone(mats, (-0.25, 0, -0.2), (0.25, 0.14, 0.2), seed + j, shears=[((0.15, 0, 0), (1, 0, rng.uniform(-0.6, 0.6)))],
                       bev=0.025, tu=1.5, tv=0.75)
            parts.append(ground_clip(xform(ob, (tilt, math.degrees(-a), tilt * 0.5), d * 0.33 + Vector((0, 0.02, 0)))))
        sapling(m, rng, (0, 0, 0), 1.25, seed, leaf_len=0.26, limbs=3, per_tip=2, r=0.05)
        grow_moss(m, rng, [Vector((0, 0, 0)), Vector((0.2, 0, -0.25))], 0.2, seed)
    else:  # low and branching among a few tilted shards
        for j, (x, z, rot) in enumerate(((-0.35, 0.1, 15), (0.35, -0.05, -12), (0.15, 0.3, 8))):
            ob = stone(mats, (-0.18, 0, -0.14), (0.18, 0.22, 0.14), seed + j, shears=[((0.0, 0.2, 0), (0.6, 1, 0.3))], bev=0.025, tu=1.5, tv=0.75)
            parts.append(ground_clip(xform(ob, (0, rot * 3, rot), (x, 0.02, z))))
        sapling(m, rng, (0, 0, 0), 0.8, seed, leaf_len=0.15, limbs=3, per_tip=2, r=0.04)
        grow_moss(m, rng, [Vector((0, 0, 0))], 0.18, seed)
    parts.append(m.object(p["id"], mats, moss=None))
    return fit(K.join(parts, p["id"]), p["size"])


def ivy_a(p, mats, seed):
    """A mound of ivy over a buried stone: dark palmate-leaf cards over a few rounded lobes round a dark leafy core,
    sunlit sprigs on top, and trailing ivy cards spilling from the rim onto the ground."""
    rng = random.Random(seed)
    m = Mesh()
    w, h, d = p["size"]
    R = (w * 0.4, h * 0.55, d * 0.4)
    c = Vector((0, R[1] * 0.75, 0))
    pblob(m, c, (R[0] * 0.75, R[1] * 0.8, R[2] * 0.75), LEAF2, tile=0.6, seed=seed, rough=0.3, rings=4, segs=8, flat_base=0.4)
    lobes = [(c, R)]
    for k in range(4):
        a = 2 * math.pi * k / 4 + rng.uniform(-0.4, 0.4)
        lobes.append((c + Vector((math.cos(a) * R[0] * 0.5, -R[1] * 0.3, math.sin(a) * R[2] * 0.5)), (R[0] * 0.6, R[1] * 0.55, R[2] * 0.6)))
    cc = c - Vector((0, R[1] * 0.6, 0))
    N.card_crown(m, lobes, DARK_C, seed=seed, density=130.0, size=(0.45, 0.7), crown_centre=cc, up_bias=0.35)
    N.card_crown(m, [(c + Vector((0, R[1] * 0.35, 0)), (R[0] * 0.7, R[1] * 0.45, R[2] * 0.7))], LEAF_C, seed=seed + 1, density=60.0,
                 size=(0.32, 0.5), crown_centre=cc, up_bias=0.5)
    for j in range(7):  # trailers spilling from the rim
        a = 2 * math.pi * (j + rng.uniform(-0.3, 0.3)) / 7
        o = Vector((math.cos(a), 0, math.sin(a)))
        cdrape(m, Vector((o.x * R[0] * 0.85, h * 0.5, o.z * R[2] * 0.85)), h * 0.5, IVY_C, rng.choice((2, 0)), math.atan2(-o.x, o.z), seed + j,
               tilt=0.5, widen=0.6)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


def ivy_b(p, mats, seed):
    """Trailing ivy hanging from a twisted stem: two long ivy cards and a shorter one turned across them."""
    m = Mesh()
    w, h, d = p["size"]
    cdrape(m, (0.0, h, -0.02), h * 0.98, IVY_C, 2, 0.0, seed, tilt=0.05, widen=0.42)
    cdrape(m, (0.08, h, 0.02), h * 0.62, IVY_C, 0, 0.0, seed + 1, tilt=0.1, widen=0.6)
    cdrape(m, (-0.12, h, 0.05), h * 0.4, IVY_C, 0, 0.0, seed + 2, tilt=0.1, widen=0.6)
    tube(m, [Vector((-0.28, h + 0.01, -0.04)), Vector((0, h + 0.03, -0.02)), Vector((0.28, h + 0.01, -0.04))], [0.03, 0.035, 0.025], BARK, 4)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


def grass_joint(p, mats, seed):
    """Meadow grass with seed heads sprouting from a paving joint, a dry tuft among it."""
    m = Mesh()
    w, h, d = p["size"]
    for k, (x, z, s_, q) in enumerate(((-0.22, 0.0, 1.0, 3), (0.08, 0.06, 0.7, 2), (0.3, -0.04, 0.8, 0))):
        ctuft(m, (x, 0, z), h * s_, GRASS_C, q, seed + k, planes=3, widen=0.55)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


def moss_patch(p, mats, seed):
    rng = random.Random(seed)
    m = Mesh()
    w, h, d = p["size"]
    pblob(m, (0, 0, 0), (w * 0.4, h * 0.85, d * 0.38), MOSS, tile=0.7, seed=seed, rough=0.45, rings=4, segs=10, flat_base=0.1)
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        pblob(m, (math.cos(a) * w * 0.3, 0, math.sin(a) * d * 0.3), (w * 0.18, h * 0.6, d * 0.17), MOSS, tile=0.7, seed=seed + k + 1,
              rough=0.4, rings=3, segs=7, flat_base=0.1)
    for k in range(8):  # tiny white flowers
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.75)
        c = Vector((math.cos(a) * r * w * 0.38, h * (0.9 - 0.6 * r * r), math.sin(a) * r * d * 0.36))
        ctr = m.vert(c + Vector((0, 0.02, 0)))
        ring = [m.vert(c + Vector((math.cos(b) * 0.035, 0, math.sin(b) * 0.035))) for b in (2 * math.pi * j / 5 + k for j in range(5))]
        for j in range(5):
            m.face((ctr, ring[j], ring[(j + 1) % 5]), ((0.5, 0.5), (0, 0), (1, 0)), FLOWER)
    for k in range(3):  # a few leafy weeds
        a = rng.uniform(0, 2 * math.pi)
        q = Vector((math.cos(a) * w * 0.42, 0.04, math.sin(a) * d * 0.4))
        leaf(m, q, Vector((math.cos(a), 0.5, math.sin(a))), Vector((0, 1, 0)), 0.16)
    return fit(m.object(p["id"], mats, moss=None), p["size"])


# ---------- ruinstone rubble ----------

def rock_a(p, mats, seed):
    rng = random.Random(seed)
    s = 1.6
    face = [("line", 0.8, 0, 0.8, 0.45), ("ring", 0.8, 0.8, 0.28), ("line", 0.8, 1.15, 0.8, 1.6), ("line", 0, 0.8, 0.45, 0.8),
            ("line", 1.15, 0.8, 1.6, 0.8)]
    ob = stone(mats, (-0.8, 0, -0.8), (0.8, s, 0.8), seed, chans=[("front", face), ("right", face), ("top", [("line", 0.8, 0, 0.8, 1.6)])],
               bev=0.05, cw=0.14, cd=0.05, tu=2.6, tv=1.3)
    m = Mesh()
    grow_moss(m, rng, [Vector((-0.75, 0, 0.7)), Vector((0.8, 0, -0.5)), Vector((0.6, 0, 0.82))], 0.3, seed)
    tuft(m, (-0.9, 0, 0.3), 0.2, 0.3, GRASS, seed, count=5)
    return fit(K.join([ob, m.object("m", mats, moss=None)], p["id"]), p["size"])


def rock_b(p, mats, seed):
    rng = random.Random(seed)
    ob = stone(mats, (-0.8, 0, -0.55), (0.8, 0.55, 0.55), seed, chans=[("top", [("line", 0, 0.55, 1.6, 0.55)])],
               shears=[((0.3, 0.3, 0.1), (1, 0.6, 0.35))], bev=0.05, cw=0.14, cd=0.05, tu=2.6, tv=1.3)
    xform(ob, (5, 18, 15), (0, 0.12, 0))
    ground_clip(ob)
    m = Mesh()
    grow_moss(m, rng, [Vector((-0.6, 0, 0.3))], 0.25, seed)
    return fit(K.join([ob, m.object("m", mats, moss=None)], p["id"]), p["size"])


def ring_solid(m, R0, R1, z0, z1, a0, a1, n, cy, b=0.05):
    """Chamfered square-section ring arc in the XY plane (centre (0, cy)), closed with end caps."""
    prof = [(R1, z1 - b), (R1 - b, z1), (R0 + b, z1), (R0, z1 - b), (R0, z0 + b), (R0 + b, z0), (R1 - b, z0), (R1, z0 + b)]
    rows = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        ca, sa = math.cos(a), math.sin(a)
        rows.append([m.vert((ca * r, cy + sa * r, z)) for r, z in prof])
    for i in range(n):
        for k in range(8):
            k1 = (k + 1) % 8
            m.face((rows[i][k], rows[i][k1], rows[i + 1][k1], rows[i + 1][k]), None, STONE)
    m.face(rows[0][::-1], None, STONE)
    m.face(rows[-1], None, STONE)


def rock_c(p, mats, seed):
    rng = random.Random(seed)
    R0, R1, z0, z1, cy = 0.72, 1.2, -0.45, 0.45, 0.82
    a0, a1 = math.radians(-38), math.radians(218)
    halves = []
    ac = math.radians(70)
    for sgn in (1, -1):
        m = Mesh()
        ring_solid(m, R0, R1, z0, z1, a0, a1, 18, cy)
        ob = to_object(m, "ring", mats)
        f = Frame((0, cy, z1), (1, 0, 0), (0, 1, 0), (0, 0, 1), 3, 3)
        cm, im = Mesh(), Mesh()
        channel(cm, im, f, [("ring", 0, 0, (R0 + R1) / 2, a0 - 0.1, a1 + 0.1)], 0.16, 0.05, DEAD)
        cutter = to_object(cm, "cutter", mats)
        boolean(ob, cutter)
        bpy.data.objects.remove(cutter)
        inlay = to_object(im, "inlay", mats, recalc=False)
        no = Vector((-math.sin(ac), math.cos(ac), 0.25)) * sgn
        co = Vector((math.cos(ac) * R0, cy + math.sin(ac) * R0, 0))
        shear(ob, co, no, mat=WEATH)
        shear(inlay, co, no, fill=False)
        uv_stone(ob, (rng.random() * 3, rng.random()), 2.6, 1.3, mats=(STONE, WEATH, SHEAR))
        piece = finish(K.join([ob, inlay], "half"), 50)
        if sgn < 0:  # the broken-off top drops a little and twists
            xform(piece, (0, 4, -3), (0.06, -0.05, 0.04))
        halves.append(ground_clip(piece))
    m = Mesh()
    grow_moss(m, rng, [Vector((math.cos(ac) * 1.0 + 0.05, cy + math.sin(ac) * 1.0, 0.1)), Vector((-0.9, 0, 0.3)), Vector((0.95, 0, -0.3))], 0.22, seed)
    tuft(m, (0.2, 0, 0.6), 0.25, 0.35, GRASS, seed, count=5)
    return fit(K.join(halves + [m.object("m", mats, moss=None)], p["id"]), p["size"])


def rock_d(p, mats, seed):
    rng = random.Random(seed)
    top = [("ring", 1.0, 1.0, 0.5), ("line", 1.0, 0, 1.0, 0.42), ("line", 1.0, 1.58, 1.0, 2.0), ("line", 0, 1.0, 0.42, 1.0),
           ("line", 1.58, 1.0, 2.0, 1.0)]
    planes = [((0.15, 0, 0), Vector((1, 0, 0.3))), ((0, 0, -0.2), Vector((0.25, 0, 1)))]
    parts = []
    for k, (s1, s2) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        ob = stone(mats, (-1, 0, -1), (1, 0.4, 1), seed, chans=[("top", top)], shears=[(planes[0][0], planes[0][1] * s1), (planes[1][0], planes[1][1] * s2)],
                   bev=0.05, cw=0.16, cd=0.05, tu=2.6, tv=1.3)
        rot = (rng.uniform(-2.5, 2.5), rng.uniform(-3, 3), rng.uniform(-2.5, 2.5))
        xform(ob, rot, (-s1 * 0.035, -0.04 * k, -s2 * 0.035))
        parts.append(ground_clip(ob))
    m = Mesh()
    for k, (x, z) in enumerate(((0.12, -0.7), (0.2, 0.6), (-0.6, -0.25), (0.75, -0.08))):  # grass in the cracks
        tuft(m, (x, 0.3, z), 0.12, 0.3, GRASS, seed + k, count=4, width=0.025, lean=0.6)
    grow_moss(m, rng, [Vector((0.15, 0.36, 0.2)), Vector((-0.95, 0.0, 0.8))], 0.16, seed)
    return fit(K.join(parts + [m.object("m", mats, moss=None)], p["id"]), p["size"])


def shard_pile(mats, rng, seed, items, scale=1.0):
    """Precise pale shards and broken blocks: [(size, pos, rot, sheared)]."""
    out = []
    for k, (sz, pos, rot, sh) in enumerate(items):
        w, h, d = (v * scale for v in sz)
        shears = [((rng.uniform(-0.2, 0.2) * w, h * 0.5, 0), rand_dir(rng, 0.6))] if sh else []
        ob = stone(mats, (-w / 2, 0, -d / 2), (w / 2, h, d / 2), seed + k, shears=shears, bev=0.025 if w < 0.4 else 0.04, tu=1.6, tv=0.8,
                   mat=WEATH if k % 4 == 3 else STONE)
        out.append(ground_clip(xform(ob, rot, Vector(pos) * scale)))
    return out


def rock_e(p, mats, seed):
    rng = random.Random(seed)
    items = [((0.6, 0.45, 0.5), (-0.3, 0, -0.2), (0, 20, 0), True), ((0.55, 0.4, 0.45), (0.35, 0, 0.1), (0, -15, 5), False),
             ((0.45, 0.35, 0.4), (0.0, 0.32, 0.0), (12, 35, -18), True), ((0.35, 0.3, 0.3), (-0.55, 0, 0.35), (0, 50, 0), True),
             ((0.3, 0.25, 0.35), (0.6, 0, -0.4), (0, 10, 10), False), ((0.3, 0.22, 0.25), (-0.1, 0.6, 0.15), (-20, 70, 15), True),
             ((0.28, 0.2, 0.22), (0.25, 0.45, -0.2), (15, -30, 25), True), ((0.22, 0.18, 0.2), (0.15, 0, 0.55), (0, 30, 0), False)]
    parts = shard_pile(mats, rng, seed, items)
    m = Mesh()
    grow_moss(m, rng, [Vector((0.05, 0.3, 0.3)), Vector((-0.3, 0.42, -0.1)), Vector((0.5, 0.0, 0.3))], 0.2, seed)
    return fit(K.join(parts + [m.object("m", mats, moss=None)], p["id"]), p["size"])


def rubble_scatter(p, mats, seed):
    rng = random.Random(seed)
    items = [((0.26, 0.2, 0.24), (-0.4, 0, -0.1), (0, 20, 0), False), ((0.2, 0.16, 0.18), (0.1, 0, 0.2), (0, -30, 6), True),
             ((0.18, 0.14, 0.2), (0.4, 0, -0.15), (8, 50, 0), True), ((0.14, 0.12, 0.14), (-0.1, 0, -0.25), (0, 10, 0), False),
             ((0.12, 0.1, 0.12), (0.45, 0, 0.25), (0, 70, 10), False), ((0.16, 0.08, 0.12), (-0.35, 0, 0.25), (0, -40, 0), True)]
    return fit(K.join(shard_pile(mats, rng, seed, items), p["id"]), p["size"])


# ---------- lips and undersides ----------

def ruin_lip(p, mats, seed):
    """Isle edge along X: pale ruinstone paving (a dead channel along it) on top at y = h over grey rock, the isle
    ground meeting it at the back (-Z). Crumbling: broken slab ends, a dropped tile, wilted grass, falling pebbles.
    Paved: an intact edge on a strata course, the channel turning down the face, ivy over the edge."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    crumble = "crumble" in p["id"]
    t = 0.4
    parts = []
    zf = d / 2 - 0.3  # front edge of the paving
    for ix in range(4):
        x0 = -w / 2 + 2 * ix
        for iz in range(2):
            lo, hi = (x0, h - t, zf - 2 * (iz + 1)), (x0 + 2, h, zf - 2 * iz)
            chans = []
            if iz == 0:
                chans.append(("top", [("line", 0, 0.9, 2, 0.9)]))
                if not crumble and ix == 2:
                    chans[0][1].append(("line", 1.0, 0, 1.0, 0.9))
            shears, rot, loc = [], (0, 0, 0), (0, 0, 0)
            if crumble and iz == 0:
                if ix == 1:  # this one has dropped and tilted over the edge
                    rot, loc = (14, 2, -6), (0, -0.55, 0.35)
                    shears = [((x0 + 1, h, zf - 0.6), (0.3, 0.2, 1))]
                elif ix != 2:
                    shears = [((x0 + 1, h, zf - rng.uniform(0.3, 0.9)), (rng.uniform(-0.5, 0.5), 0.25, 1))]
            ob = stone(mats, lo, hi, seed + ix + 4 * iz, chans=chans, shears=shears, bev=0.05, tu=4.0, tv=2.0, mat=WEATH if (ix + iz) % 3 == 2 else STONE)
            if rot != (0, 0, 0):
                xform(ob, rot, loc)
            parts.append(ob)
    if not crumble:  # strata course of ashlar under the front edge, the channel turning down its face
        for ix in range(4):
            x0 = -w / 2 + 2 * ix
            ch = [("front", [("line", 1.0, 0, 1.0, 0.8)])] if ix == 2 else []
            parts.append(stone(mats, (x0 + 0.02, h - t - 0.8, zf - 1.0), (x0 + 1.98, h - t, zf - 0.05), seed + 20 + ix, chans=ch, bev=0.05,
                               tu=4.0, tv=2.0))
    else:  # a broken strata block and loose pieces in the crumble
        parts.append(stone(mats, (-1.0, h - t - 0.7, zf - 1.1), (0.6, h - t, zf - 0.2), seed + 30, shears=[((0.2, h - 0.8, zf - 0.3), (0.6, -0.4, 1))],
                           bev=0.05, tu=4.0, tv=2.0))
    # grey rock body, ragged underneath
    for k in range(5):
        x = -w / 2 + 0.8 + 1.6 * k + rng.uniform(-0.2, 0.2)
        yb = rng.uniform(0.0, 0.9)
        parts.append(hull_rock(mats, (x, yb, 0.1), (2.6, h - t - yb + 0.2, d * 0.9), GREY, seed + 50 + k, n=22, rough=0.25, tile=2.0))
    m = Mesh()
    gz = zf - 4
    grid = [[m.vert((-w / 2 + w * j / 8, h - 0.06 + (0.03 * noise.noise(Vector((j, i, seed))) if 0 < j < 8 else 0), -d / 2 + (gz + d / 2) * i / 2))
             for j in range(9)] for i in range(3)]
    for i in range(2):
        for j in range(8):
            m.face((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]), None, GROUND, 3.0)
    if crumble:
        for k in range(6):  # wilted, browning grass along the top
            x = -w / 2 + 0.6 + (w - 1.2) * k / 5 + rng.uniform(-0.3, 0.3)
            tuft(m, (x, h, zf - rng.uniform(0.2, 2.5)), 0.3, rng.uniform(0.45, 0.7), WILT, seed + k, count=6, width=0.03, lean=0.7)
        pebbles = Mesh()
        for k in range(6):
            q = Vector((rng.uniform(-w / 2 + 1, w / 2 - 1), rng.uniform(0.3, h - 1.2), zf + rng.uniform(0.3, 0.9)))
            s = rng.uniform(0.12, 0.3)
            hull(pebbles, cloud(rng, q, (s, s * 0.8, s), 10, 0.2, seed + k), STONE if k % 2 else GREY, 1.0)
        parts.append(finish(pebbles.object("pebbles", mats, moss=None), 40))
    else:
        for k in range(3):
            tuft(m, (-w / 2 + 1 + 3 * k + rng.uniform(-0.4, 0.4), h, zf - rng.uniform(0.5, 2.5)), 0.3, 0.5, GRASS, seed + k, count=6)
        for k, x in enumerate((-3.2, -2.5, 0.2, 0.8, 2.6, 3.3)):
            ivy_strand(m, rng, (x, h + 0.02, zf - 0.1), rng.uniform(1.0, 2.2), 6, Vector((0, 0, 1)), r=0.025)
        grow_moss(m, rng, [Vector((-3.0, h, zf - 0.3)), Vector((1.6, h, zf - 1.2))], 0.3, seed)
    parts.append(m.object("top", mats, moss=None))
    return fit(K.join(parts, p["id"]), p["size"], scale=False)


def ruin_underside(p, mats, seed):
    """Inverted spire: pale ruinstone strata and a ring of blocks at the top grading into faceted grey rock columns
    whose broken ends trace the taper; a dead channel steps down one face, ivy hangs from the rim, dust and pebbles
    trail from the point."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    big = "-a" in p["id"]
    m = Mesh()
    r = 0.72 if big else 0.6
    cols = []
    for i in range(-8, 9):
        for j in range(-8, 9):
            x = i * r * 1.5 + (j % 2) * r * 0.75
            z = j * r * 1.3
            e = math.hypot(x / (w / 2), z / (d / 2))
            if e > 0.93:
                continue
            ex = e + 0.08 * noise.noise(Vector((x, z, seed)))
            y0 = min(h * min(1.0, max(0.0, ex)) ** 1.15 * rng.uniform(0.9, 1.05), h - 1.4)
            cols.append((x, z, r * rng.uniform(0.86, 0.98), h - 0.75, max(0.0, y0), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4))))
    hex_columns(m, cols, GREY, seed, tile=2.4, bevel_top=0.0, sides=5)
    for f in m.bm.faces:  # the upper band of the columns is pale strata
        c = f.calc_center_median()
        if c.z > h - 2.0 + 0.4 * noise.noise(c * 0.8):
            f.material_index = STONE
    body = finish(m.object("spire", mats, moss=None, seed=seed), 40)
    parts = [body]
    # ring of chamfered ruinstone blocks round the rim, each turned to face out
    nb = 10 if big else 8
    for k in range(nb):
        a = 2 * math.pi * k / nb + rng.uniform(-0.05, 0.05)
        bw = 2 * math.pi * (w + d) / 4 / nb * 0.98
        drop = rng.choice((0.6, 0.85, 1.2))
        ob = stone(mats, (-bw / 2, -drop, -0.9), (bw / 2, 0.0, 0.0), seed + k, bev=0.05, tu=4.0, tv=2.0, mat=WEATH if k % 3 == 1 else STONE)
        R = Vector((math.cos(a) * w / 2 * 0.94, 0, math.sin(a) * d / 2 * 0.94))
        xform(ob, (0, -math.degrees(a) + 90, 0), (R.x, h, R.z))
        parts.append(ob)
    lid = Mesh()
    ring = [lid.vert((math.cos(2 * math.pi * k / 24) * w / 2 * 0.98, h - 0.02, math.sin(2 * math.pi * k / 24) * d / 2 * 0.98)) for k in range(24)]
    lid.face(ring[::-1], None, PATH, 4.0)
    for k in range(10 if big else 8):  # hanging ivy from the rim
        a = 2 * math.pi * k / (10 if big else 8) + 0.3 + rng.uniform(-0.1, 0.1)
        q = (math.cos(a) * w / 2 * 1.02, h - 0.05, math.sin(a) * d / 2 * 1.02)
        ivy_strand(lid, rng, q, rng.uniform(1.6, h * 0.35), 7, Vector((math.cos(a), 0, math.sin(a))), r=0.03)
    pebbles = Mesh()
    for k in range(6):  # dust and pebbles trailing from the point
        q = Vector((rng.uniform(-0.4, 0.4), -rng.uniform(0.3, 2.2), rng.uniform(-0.4, 0.4)))
        s = rng.uniform(0.1, 0.25)
        hull(pebbles, cloud(rng, q, (s, s * 0.8, s), 10, 0.2, seed + k), GREY if k % 2 else STONE, 1.0)
    parts += [lid.object("rim", mats, moss=None), finish(pebbles.object("pebbles", mats, moss=None), 40)]
    ob = K.join(parts, p["id"])
    # the dead channel stepping down the front face
    ch = Mesh()
    steps = [(0.25, 0.9, 1), (0.25, 0.45, 1), (0.5, 0.45, 1), (0.5, 0.0, 1), (0.3, 0.0, 1), (0.3, -0.5, 1)]
    for a, b in zip(steps, steps[1:]):
        pts = surface_path(ob, a, b, 4, wig=0.0, seed=seed, out=0.02)
        if len(pts) > 1:
            tube(ch, pts, [0.14] * len(pts), DEAD, 4, flat=0.35, caps=(False, False))
    return fit(K.join([ob, ch.object("channel", mats, moss=None)], p["id"]), p["size"], scale=False, floor=False)


# ---------- dispatch ----------

def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    pid = p["id"]
    if "slab-splitter" in pid:
        return slab_splitter(p, mats, seed)
    if "sapling" in pid:
        return sapling_piece(p, mats, seed)
    if "lip" in pid:
        return ruin_lip(p, mats, seed)
    if "underside" in pid:
        return ruin_underside(p, mats, seed)
    fn = {"ru-root-gripped-block": root_gripped_block, "ru-ivy-a": ivy_a, "ru-ivy-b": ivy_b, "ru-grass-joint": grass_joint,
          "ru-moss-patch": moss_patch, "ru-rubble-scatter": rubble_scatter, "ru-rock-a": rock_a, "ru-rock-b": rock_b,
          "ru-rock-c": rock_c, "ru-rock-d": rock_d, "ru-rock-e": rock_e}[pid]
    return fn(p, mats, seed)


CATEGORY = {"tree": "tree", "plant": "bush", "ground": "ground", "rock": "rock", "lip": "lip", "underside": "underside", "water": "water"}


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
    K.build_all(build_piece, extras=[(p["id"], CATEGORY[p["family"]]) for p in B.kit["pieces"]], biome="ruin")
