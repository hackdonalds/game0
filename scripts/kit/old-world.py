# Detailed Old-World ruins kit: precise pale ashlar, inset 0.5 m channels with a lit teal inlay, concentric ring
# segments lofted from a channelled cross-section, glyph plates, floating shards and separate moss/root overgrowth.
# Built from kit.json on the 4 m grid; joined prefabs from each prefab's layout, a demo catalogue, contact sheets.
# Textures are the painted swatches in art/textures/old-world.
# Usage: Blender --background --python scripts/kit/old-world.py -- old-world
#
# Layout entries may carry "rotX" / "rotZ" (degrees, applied before rotY) besides "rotY": a quarter ring can only
# become a lower quadrant of a full ring by rolling it about its front axis, and ruins lean.
import bmesh, bpy, math, os, random, sys
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, V, tube  # noqa: E402

# Material slots, in order; every object carries the full list so joined prefabs keep one material set
MATS = [("OW_Stone", "stone-grain.png", 0), ("OW_Weathered", "weathered-stone.png", 0), ("OW_Glyph", "glyph-band.png", 0),
        ("OW_Moss", "moss.png", 0), ("OW_Root", "root-bark.png", 0), ("OW_ChannelLit", "channel-lit.png", 3.0),
        ("OW_ChannelDead", "channel-dead.png", 0), ("OW_Teal", (0.05, 0.78, 0.66), 4.0), ("OW_Flower", (0.95, 0.66, 0.7), 0)]
STONE, WEATH, GLYPH, MOSS, ROOT, GLOW, DEAD, TEAL, FLOWER = range(len(MATS))
K.configure(MATS, os.path.join(B.ROOT, "art/textures/old-world"), cap_mat=ROOT, moss=None)

CH, CD = 0.5, 0.1      # standard channel width and depth
BEV = 0.045            # crisp chamfer on every stone edge
GROOVE = 0.035         # ring joint groove depth

_make_materials = K.make_materials


def make_materials():
    out = _make_materials()
    for m, (_, tex, _) in zip(out, MATS):  # Workbench shows untextured slots by their viewport colour
        if not isinstance(tex, str):
            m.diffuse_color = (*tex, 1)
    return out


K.make_materials = make_materials


def place_layout(layout, build, mats):
    """kitlib.place_layout plus optional rotX / rotZ (glTF axes, degrees) so rings can roll into any quadrant."""
    C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    parts = []
    for e in layout:
        ob = build(B.PIECES[e["id"]], mats)
        g = (Matrix.Translation(Vector(e["pos"])) @ Matrix.Rotation(math.radians(e.get("rotY", 0)), 4, "Y")
             @ Matrix.Rotation(math.radians(e.get("rotZ", 0)), 4, "Z") @ Matrix.Rotation(math.radians(e.get("rotX", 0)), 4, "X"))
        ob.matrix_world = C @ g @ C.inverted()
        parts.append(ob)
    bpy.context.view_layer.update()
    return parts


K.place_layout = place_layout
_render = B.render


def render(path, objs_bounds, color_type="OBJECT"):
    # Standard view transform: AgX greys the pale stone down to beige-brown, which misreports the swatches
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.exposure = 0.45  # Workbench's studio light renders albedo at ~60%; lift it back
    return _render(path, objs_bounds, color_type)


B.render = render


# ---------- mesh plumbing ----------

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


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def boolean(ob, cutter):
    mod = ob.modifiers.new("cut", "BOOLEAN")
    mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
    mod.use_self = True
    apply_mods(ob)


def finish(ob, angle=50):
    """Hard-surface shading: sharp creases above `angle`, face-area weighted normals so big faces stay flat and the
    small chamfers read as rounded highlights."""
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


def glyph_band(ob, y0, y1):
    """Vertical faces between heights y0..y1 (glTF) take the glyph frieze, its painted band fitted to the height."""
    me = ob.data
    uvl = me.uv_layers.active
    for p in me.polygons:
        n = p.normal
        zs = [me.vertices[v].co.z for v in p.vertices]
        if abs(n.z) > 0.3 or min(zs) < y0 - 1e-4 or max(zs) > y1 + 1e-4:
            continue
        p.material_index = GLYPH
        along = 1 if abs(n.x) > abs(n.y) else 0
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[along] / 1.25, 0.29 + (co.z - y0) / (y1 - y0) * 0.46)


def bevel_bm(bm, w=BEV):
    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=w, offset_type="OFFSET", segments=1,
                    profile=0.5, affect="EDGES", clamp_overlap=True)


# ---------- face frames, channels and cutters ----------

class Frame:
    """A face of a piece: origin, in-plane axes u and v and outward normal n (glTF), and its size (W, H)."""

    def __init__(self, o, u, v, n, W, H):
        self.o, self.u, self.v, self.n = Vector(o), Vector(u), Vector(v), Vector(n)
        self.W, self.H = W, H
        assert self.u.cross(self.v).dot(self.n) > 0.99

    def p(self, a, b, d=0.0):
        return self.o + self.u * a + self.v * b + self.n * d


def frames(w, h, d, centre=False):
    ox, oz = (-w / 2, d / 2) if centre else (0.0, 0.0)
    return {"front": Frame((ox, 0, oz), (1, 0, 0), (0, 1, 0), (0, 0, 1), w, h),
            "back": Frame((ox + w, 0, oz - d), (-1, 0, 0), (0, 1, 0), (0, 0, -1), w, h),
            "top": Frame((ox, h, oz), (1, 0, 0), (0, 0, -1), (0, 1, 0), w, d)}


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


# ---------- stone pieces from ashlar blocks ----------

def box_solid(lo, hi):
    def make(m):
        K.box(m, lo, hi, STONE)
    return make


def outline_solid(outline, z0, z1):
    def make(m):
        K.extrude(m, outline, z0, z1, STONE)
    return make


def stone_piece(p, mats, solids, chans=(), extra_cut=None, glyph=None, seed=0.0, bev=BEV, weathered=()):
    """Each solid is a separately chamfered ashlar block (the chamfers meet as V joints); channels and openings are
    cut through all of them, inlays laid in, UVs box-projected with a per-block offset, normals weighted."""
    rng = random.Random(seed)
    blocks = []
    for i, make in enumerate(solids):
        m = Mesh()
        make(m)
        bevel_bm(m.bm, bev)
        blocks.append(to_object(m, f"{p['id']}.b{i}", mats))
    cm, im = Mesh(), Mesh()
    for f, shapes, *opt in chans:
        channel(cm, im, f, shapes, *opt)
    if extra_cut:
        extra_cut(cm)
    if cm.bm.faces:
        cutter = to_object(cm, "cutter", mats)
        for b in blocks:
            boolean(b, cutter)
        bpy.data.objects.remove(cutter)
    else:
        cm.bm.free()
    for i, b in enumerate(blocks):
        uv_stone(b, (rng.random() * 3, rng.random() * 2), mats=(STONE, WEATH))
        if i in weathered:
            for poly in b.data.polygons:
                poly.material_index = WEATH
            uv_stone(b, (rng.random(), rng.random()), 3.0, 3.0, mats=(WEATH,))
    if glyph:
        glyph_band(blocks[-1], *glyph)
    parts = blocks
    if im.bm.faces:
        parts.append(to_object(im, p["id"] + ".inlay", mats, recalc=False))
    else:
        im.bm.free()
    ob = K.join(parts, p["id"])
    return finish(ob)


def courses(h, step):
    n = max(1, round(h / step))
    return [h * i / n for i in range(n + 1)]


def ashlar(x0, x1, z0, z1, ys, splits):
    """Blocks through the full depth z0..z1, course by course; splits[i] are the head joints of course i."""
    out = []
    for i in range(len(ys) - 1):
        xs = [x0] + list(splits[i % len(splits)]) + [x1]
        for a, b in zip(xs, xs[1:]):
            out.append(box_solid((a, ys[i], z0), (b, ys[i + 1], z1)))
    return out


def build_monolith(p, mats, seed):
    w, h, d = p["size"]
    body = h - 0.6
    ys = courses(body, 2.0)
    solids = ashlar(0, w, -d, 0, ys, [[2.0]]) + [box_solid((0, body, -d), (w, h, 0))]
    node = {6: 3.2, 12: 8.4, 18: 13.6}[h]
    f = frames(w, h, d)["front"]
    shapes = [("line", 2, 0, 2, node - 1.0), ("ring", 2, node, 1.0), ("line", 2, node + 1.0, 2, body - 0.2)]
    return stone_piece(p, mats, solids, [(f, shapes)], glyph=(body, h), seed=seed)


def build_wall(p, mats, seed):
    w, h, d = p["size"]
    fr = frames(w, h, d)
    f = fr["front"]
    pid = p["id"]
    chans, cut = [], None
    if pid.endswith("plain"):
        solids = ashlar(0, w, -d, 0, [0, 2, 4, 6], [[2.6], [1.4]])
    elif pid.endswith("channelled"):
        solids = ashlar(0, w, -d, 0, [0, 1.5, 3, 4.5, 6], [[2.0]])
        chans = [(f, [("line", 2, 0, 2, 2.0), ("ring", 2, 3.0, 1.0), ("line", 2, 4.0, 2, 6)])]
    elif pid.endswith("window"):
        solids = ashlar(0, w, -d, 0, [0, 1, 3, 5, 6], [[2.0], [2.0], [2.0], [1.3, 2.7]])
        (ow, oh), (ox, oy) = p["opening"]["size"], p["opening"]["offset"]

        def cut(cm):
            slot = [(x + ox + ow / 2, y + oy) for x, y in K.arch(ow, oh, 10)]
            prism(cm, f, slot, -d - 0.3, 0.3)
            for face in (fr["front"], fr["back"]):  # crisp reveal around the slot on both faces
                cx = ox + ow / 2 if face is fr["front"] else w - (ox + ow / 2)
                rev = [(x + cx, y + oy - 0.15) for x, y in K.arch(ow + 0.3, oh + 0.3, 10)]
                prism(cm, face, rev, -0.07, 0.3)
    else:  # doorway
        solids = ashlar(0, w, -d, 0, [0, 2, 4, 6], [[2.0], [2.0], [1.3, 2.7]])
        (ow, oh), (ox, oy) = p["opening"]["size"], p["opening"]["offset"]
        spring = oh - ow / 2
        cx = ox + ow / 2
        rr = ow / 2 + 0.25 + CH / 2
        chans = [(f, [("line", cx - rr, 0, cx - rr, spring), ("ring", cx, spring, rr, 0, math.pi),
                      ("line", cx + rr, 0, cx + rr, spring)])]

        def cut(cm):
            door = [(x + cx, max(y, -0.3) if y > 0 else -0.3) for x, y in K.arch(ow, oh, 14)]
            prism(cm, f, door, -d - 0.3, 0.3)
    return stone_piece(p, mats, solids, chans, cut, seed=seed)


def build_corner(p, mats, seed):
    w, h, d = p["size"]
    solids = []
    for i, (y0, y1) in enumerate(zip([0, 2, 4], [2, 4, 6])):
        if i % 2 == 0:
            solids += [box_solid((0, y0, -1), (2, y1, 0)), box_solid((2, y0, -1), (w, y1, 0)),
                       box_solid((0, y0, -2.5), (1, y1, -1)), box_solid((0, y0, -d), (1, y1, -2.5))]
        else:
            solids += [box_solid((1, y0, -1), (2.5, y1, 0)), box_solid((2.5, y0, -1), (w, y1, 0)),
                       box_solid((0, y0, -2), (1, y1, 0)), box_solid((0, y0, -d), (1, y1, -2))]
    return stone_piece(p, mats, solids, seed=seed)


def build_column(p, mats, seed):
    w, h, d = p["size"]
    solids = [box_solid((-w / 2, y0, -d / 2), (w / 2, y1, d / 2)) for y0, y1 in ((0, 2.1), (2.1, 4.0), (4.0, h))]
    f = frames(w, h, d, centre=True)["front"]
    return stone_piece(p, mats, solids, [(f, [("line", 0.5, 0, 0.5, h)])], seed=seed)


def build_floor(p, mats, seed):
    w, h, d = p["size"]
    pid = p["id"]
    solids = [box_solid((x, 0, z - 2), (x + 2, h, z)) for x in (0, 2) for z in (0, -2)]
    f = frames(w, h, d)["top"]
    if pid.endswith("straight"):
        shapes = [("line", 2, 0, 2, 4)]
    elif pid.endswith("t"):
        shapes = [("line", 0, 2, 4, 2), ("line", 2, 0, 2, 2)]
    elif pid.endswith("corner"):
        shapes = [("line", 2, 4, 2, 1.75), ("line", 2, 2, 4, 2)]
    elif pid.endswith("cross") and "inlay" in pid:
        shapes = [("line", 0, 2, 4, 2), ("line", 2, 0, 2, 4)]
    elif pid.endswith("cross"):
        shapes = [("ring", 2, 2, 0.75), ("line", 2, 0, 2, 1.25), ("line", 2, 2.75, 2, 4), ("line", 0, 2, 1.25, 2), ("line", 2.75, 2, 4, 2)]
    elif pid.endswith("node"):
        shapes = [("ring", 2, 2, 1.0), ("line", 2, 0, 2, 1.0), ("line", 2, 3.0, 2, 4), ("line", 0, 2, 1.0, 2), ("line", 3.0, 2, 4, 2)]
    else:  # ring inlay
        shapes = [("ring", 2, 2, 1.5), ("ring", 2, 2, 0.6), ("line", 2, 0, 2, 0.5), ("line", 2, 3.5, 2, 4),
                  ("line", 0, 2, 0.5, 2), ("line", 3.5, 2, 4, 2)]
    return stone_piece(p, mats, solids, [(f, shapes)], seed=seed)


def build_steps(p, mats, seed):
    w, h, d = p["size"]
    n = 4
    solids = []
    for k in range(n):
        y1, z0, z1 = h * (k + 1) / n, -d * (k + 1) / n, -d * k / n
        sx = 2.3 if k % 2 == 0 else 1.7
        solids += [box_solid((0, 0, z0), (sx, y1, z1)), box_solid((sx, 0, z0), (w, y1, z1))]
    return stone_piece(p, mats, solids, seed=seed)


def build_plinth(p, mats, seed):
    w, h, d = p["size"]
    lo_h, band_top = 0.25, 0.75
    solids = [box_solid((x, 0, z - 2), (x + 2, lo_h, z)) for x in (0, 2) for z in (0, -2)]
    solids.append(box_solid((0.3, lo_h, -d + 0.3), (w - 0.3, band_top, -0.3)))
    e = 0.15
    solids += [box_solid((e, band_top, -d + e), (2, h, -2)), box_solid((2, band_top, -d + e), (w - e, h, -2)),
               box_solid((e, band_top, -2), (2, h, -e)), box_solid((2, band_top, -2), (w - e, h, -e))]
    ob = stone_piece(p, mats, solids, seed=seed)
    # Lit channel band: a glowing ring set into the recessed course
    m = Mesh()
    g = 0.24
    K.box(m, (g, 0.33, -d + g), (w - g, 0.67, -g), GLOW)
    band = to_object(m, "band", mats)
    uvl = band.data.uv_layers.active
    for poly in band.data.polygons:
        for li in poly.loop_indices:
            co = band.data.vertices[band.data.loops[li].vertex_index].co
            uvl.data[li].uv = ((co.x - co.y) / 3, (co.z - 0.33) / 0.34)
    return K.join([ob, finish(band)], p["id"])


def build_keystone(p, mats, seed):
    w, h, d = p["size"]
    out = [(-1, 0), (1, 0), (1, 1.2), (1.6, 1.2), (2, 1.6), (2, 4.4), (1.6, 4.8), (1, 4.8), (1, 5.5), (0.5, 6),
           (-0.5, 6), (-1, 5.5), (-1, 4.8), (-1.6, 4.8), (-2, 4.4), (-2, 1.6), (-1.6, 1.2), (-1, 1.2)]
    fr = frames(w, h, d, centre=True)
    shapes = [("line", 2, 0, 2, 2.0), ("ring", 2, 3, 1.0), ("line", 2, 4.0, 2, 6), ("line", 0, 3, 1.0, 3), ("line", 3.0, 3, 4, 3)]
    return stone_piece(p, mats, [outline_solid(out, -d / 2, d / 2)], [(fr["front"], shapes), (fr["back"], shapes)], seed=seed, bev=0.06)


def build_glyph_plate(p, mats, seed):
    w, h, d = p["size"]
    f = frames(w, h, d)["front"]
    k = p["id"][-1]
    if k == "a":
        shapes = [("ring", 2, 2, 1.4), ("ring", 2, 2, 0.6), ("line", 2, 0, 2, 0.6), ("line", 2, 3.4, 2, 4)]
    elif k == "b":
        shapes = [("ring", 2, 2.95, 0.45), ("line", 2, 3.4, 2, 4), ("line", 2, 0, 2, 2.5),
                  ("ring", 2, 0, 1.75, 0, math.pi), ("ring", 2, 0, 1.0, 0, math.pi)]
    else:
        shapes = [("ring", 2, 2, 0.5), ("line", 2, 0, 2, 1.5), ("line", 2, 2.5, 2, 4), ("line", 0.55, 2, 1.5, 2), ("line", 2.5, 2, 3.45, 2)]
    border = [("line", 0.25, 0.25, 3.75, 0.25), ("line", 0.25, 3.75, 3.75, 3.75), ("line", 0.25, 0.25, 0.25, 3.75), ("line", 3.75, 0.25, 3.75, 3.75)]

    def cut(cm):  # hairline border groove, precise and unlit
        for s in border:
            _, u0, v0, u1, v1 = s
            if v0 == v1:
                prism(cm, f, [(u0 - 0.02, v0 - 0.02), (u1 + 0.02, v0 - 0.02), (u1 + 0.02, v0 + 0.02), (u0 - 0.02, v0 + 0.02)], -0.03, 0.2)
            else:
                prism(cm, f, [(u0 - 0.02, v0 + 0.02), (u0 + 0.02, v0 + 0.02), (u0 + 0.02, v1 - 0.02), (u0 - 0.02, v1 - 0.02)], -0.03, 0.2)
    return stone_piece(p, mats, [box_solid((0, 0, -d), (w, h, 0))], [(f, shapes, 0.3, 0.07)], cut, seed=seed, bev=0.03)


# ---------- ring and arch segments: lofted channelled cross-section ----------

def ring_piece(p, mats, R, a0, a1, c, zf, step, jstep, seed):
    ri, b = R - 1, 0.05
    c0, c1, zb = R - 0.75, R - 0.25, zf - 1
    P = [(R, zf - b), (R - b, zf), (c1, zf), (c1, zf - CD), (c0, zf - CD), (c0, zf), (ri + b, zf), (ri, zf - b),
         (ri, zb + b), (ri + b, zb), (c0, zb), (c0, zb + CD), (c1, zb + CD), (c1, zb), (R - b, zb), (R, zb + b)]
    kinds = "wfwgwfwwwfwgwfww"
    deep = {3, 4, 11, 12}
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    en = []
    for i in range(n):
        dx, dz = P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1]
        L = math.hypot(dx, dz)
        en.append((sgn * dz / L, -sgn * dx / L))
    inset = []
    for i in range(n):
        a, bq = en[i - 1], en[i]
        nx, nz = a[0] + bq[0], a[1] + bq[1]
        L = math.hypot(nx, nz) or 1
        inset.append((0, 0) if i in deep else (-nx / L * GROOVE, -nz / L * GROOVE))
    plen = [0.0]
    for i in range(n):
        plen.append(plen[-1] + math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1]))

    closed = a1 - a0 >= 2 * math.pi - 1e-6
    dlt = 0.05 / R
    nb = max(1, math.ceil((a1 - a0) / step - 1e-6))
    nj = max(1, round((a1 - a0) / jstep))
    joints = [a0 + (a1 - a0) * j / nj for j in (range(nj) if closed else range(1, nj))]
    ang = []
    if not closed:
        ang += [(a0, True), (a0 + dlt, False), (a1 - dlt, False), (a1, True)]
    for j in joints:
        ang += [(j - dlt, False), (j, True), (j + dlt, False)]
    for i in range(nb if closed else nb + 1):
        a = a0 + (a1 - a0) * i / nb
        if all(abs(a - x) > 2.5 * dlt for x, _ in ang) and (not closed or all(abs(a - 2 * math.pi - x) > 2.5 * dlt for x, _ in ang)):
            ang.append((a, False))
    ang = sorted((a % (2 * math.pi) if closed else a, ins) for a, ins in ang)

    rng = random.Random(seed)
    ox, oy = rng.random() * 3, rng.random() * 2
    m = Mesh()
    rings = []
    for a, ins in ang:
        ca, sa = math.cos(a), math.sin(a)
        row = []
        for i, (r, z) in enumerate(P):
            if ins:
                r, z = r + inset[i][0], z + inset[i][1]
            row.append(m.vert((c[0] + r * ca, c[1] + r * sa, z)))
        rings.append((a, row))
    if closed:
        rings.append((rings[0][0] + 2 * math.pi, rings[0][1]))
    rm = R - 0.5
    for (aA, A), (aB, Bq) in zip(rings, rings[1:]):
        for k in range(n):
            k1 = (k + 1) % n
            quad = (A[k], A[k1], Bq[k1], Bq[k])
            kind = kinds[k]
            if kind == "f":
                uvs = [((v.co.x / 4 + ox), (v.co.z / 2 + oy)) for v in quad]
                m.face(quad, uvs, STONE)
            elif kind == "g":
                m.face(quad, [(rm * aA / 3, 0), (rm * aA / 3, 1), (rm * aB / 3, 1), (rm * aB / 3, 0)], GLOW)
            else:
                v0, v1 = plen[k] / 2 + oy, plen[k + 1] / 2 + oy
                m.face(quad, [(rm * aA / 4 + ox, v0), (rm * aA / 4 + ox, v1), (rm * aB / 4 + ox, v1), (rm * aB / 4 + ox, v0)], STONE)
    if not closed:
        for (a, row), flip in ((rings[0], True), (rings[-1], False)):
            uvs = [(P[i][0] / 4 + ox, P[i][1] / 2 + oy) for i in range(n)]
            vs = row
            if flip:
                vs, uvs = vs[::-1], uvs[::-1]
            m.face(vs, uvs, STONE)
    ob = to_object(m, p["id"], mats)
    return finish(ob)


def build_ring(p, mats, seed):
    R, arc = p["radius"], p["arc"]
    step = {4: math.radians(10), 8: math.radians(7.5), 16: math.radians(5)}[R]
    jstep = math.radians({4: 22.5, 8: 22.5, 16: 15}[R])
    if arc == 360:
        return ring_piece(p, mats, R, 0, 2 * math.pi, (0, R), 0.5, math.radians(12), math.radians(36), seed)
    if arc == 180:
        return ring_piece(p, mats, R, 0, math.pi, (0, 0), 0.5, step, math.radians(30), seed)
    if arc == 90:
        return ring_piece(p, mats, R, math.pi / 2, math.pi, (R, 0), 0.0, step, jstep, seed)
    s = math.sqrt(0.5)
    return ring_piece(p, mats, R, math.pi / 2, 3 * math.pi / 4, (s * R, -(R - 1) * s), 0.0, step, jstep, seed)


# ---------- floating shards ----------

def build_fragment(p, mats, seed):
    s = p["size"][0]
    rng = random.Random(seed)
    m = Mesh()
    k = 6
    ym = 0.5 * s
    slant = Vector((rng.uniform(-1, 1), 0, rng.uniform(-1, 1))).normalized()
    ring = []
    for i in range(k):
        a = 2 * math.pi * i / k + rng.uniform(-0.25, 0.25)
        rr = s * 0.4 * rng.uniform(0.8, 1.0)
        ring.append(Vector((math.cos(a) * rr, 0, math.sin(a) * rr)))
    stone = [m.vert(q + Vector((0, ym, 0))) for q in ring]
    stone += [m.vert(q * 0.97 + Vector((0, s * (0.84 + 0.16 * (q.normalized().dot(slant) + 1) / 2), 0))) for q in ring]
    res = bmesh.ops.convex_hull(m.bm, input=stone)
    sf = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.bevel(m.bm, geom=list({e for f in sf for e in f.edges}), offset=0.025 * s, offset_type="OFFSET",
                    segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
    for f in m.bm.faces:
        f.material_index = WEATH if f.calc_center_median().z > ym + 0.05 * s and f.normal.z > 0.6 else STONE
    tip = Vector((rng.uniform(-0.08, 0.08) * s, 0, rng.uniform(-0.08, 0.08) * s))
    cry = [m.vert(q * 0.9 + Vector((0, ym + 0.03 * s, 0))) for q in ring]
    cry += [m.vert(q * 0.55 + tip * 0.4 + Vector((0, ym * 0.5, 0))) for q in ring[1::2]]
    cry.append(m.vert(tip))
    res = bmesh.ops.convex_hull(m.bm, input=cry)
    for g in res["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = TEAL
    if s >= 2:
        top = Vector((0, s * 0.92, 0))
        blob(m, top, s * 0.28, 0.22, seed=seed)
        blob(m, top + slant * s * 0.15 + Vector((0.2, -0.05, 0.1)), s * 0.16, 0.16, seed=seed + 1)
    ob = to_object(m, p["id"], mats)
    uv_stone(ob, (rng.random(), rng.random()), 1.5, 1.0)
    return finish(ob, 40)


# ---------- overgrowth ----------

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


def blob(m, c, R, h, mat=MOSS, sides=9, seed=0.0, rough=0.28):
    c = Vector(c)
    n = 4
    pts = [c + Vector((0, h * i / n - 0.04, 0)) for i in range(n + 1)]
    radii = [max(0.02, R * math.cos(math.pi / 2 * i / n) ** 0.6) for i in range(n + 1)]
    tube(m, pts, radii, mat, sides, rough=rough, seed=seed, tile=1.0, planar=True, cap_mat=mat)


def cushion(m, x0, x1, z0, z1, y, amp, nx, nz, seed, keep_front=False, droop=0.0):
    """Moss mat: a noisy heightfield that thins to nothing at its ragged edges."""
    grid = []
    for i in range(nx + 1):
        row = []
        for j in range(nz + 1):
            u, v = i / nx, j / nz
            x, z = x0 + (x1 - x0) * u, z0 + (z1 - z0) * v
            edge = min(u, 1 - u, v, 1 if keep_front else 1 - v) * min(nx, nz) / 1.5
            e = min(1.0, edge) ** 0.7
            q = Vector((x * 1.7, z * 1.7, seed))
            rim = min(u, 1 - u, v, 1 - v) < 1e-6
            if rim:  # ragged outline, drooping over the block edge
                x += noise.noise(q) * 0.12 + droop * 0.5 * ((u < 1e-6) * -1 + (u > 1 - 1e-6))
                z += noise.noise(q + Vector((5, 0, 0))) * 0.12 + droop * 0.5 * ((v < 1e-6) * -1 + (v > 1 - 1e-6))
            hgt = y + 0.015 + amp * e * (0.5 + 0.35 * noise.noise(q * 1.6 + Vector((0, 0, 3))) + 0.25 * noise.noise(q * 4.1))
            if rim:
                hgt -= droop * (0.6 + 0.4 * noise.noise(q * 2.3))
            row.append(m.vert((x, hgt, z)))
        grid.append(row)
    for i in range(nx):
        for j in range(nz):
            a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]
            m.face((a, b, c, d), [(a.co.x / 1.2, a.co.y / 1.2), (b.co.x / 1.2, b.co.y / 1.2), (c.co.x / 1.2, c.co.y / 1.2), (d.co.x / 1.2, d.co.y / 1.2)], MOSS)


def build_moss_drape(p, m, seed):
    w, h, d = p["size"]
    yt = h - 0.15  # the wall top it hangs over
    rng = random.Random(seed)
    cushion(m, 0.0, w, -d, 0.02, yt, 0.14, 12, 4, seed, keep_front=True, droop=0.1)
    lip = [Vector((x, yt + 0.03, 0.05)) for x in [0.15 + (w - 0.3) * i / 10 for i in range(11)]]
    tube(m, lip, [0.1] * len(lip), MOSS, 7, rough=0.45, seed=seed, cap_mat=MOSS)
    x = 0.22
    i = 0
    while x < w - 0.15:
        L = min(yt - 0.05, 0.5 + 2.4 * (0.5 + 0.5 * math.sin(i * 2.37 + seed)) ** 1.6 * rng.uniform(0.6, 1.0))
        r = rng.uniform(0.08, 0.13)
        sway = rng.uniform(-0.15, 0.15)
        pts = spline([(x, yt + 0.02, 0.06), (x + sway * 0.3, yt - L * 0.4, r * 0.85), (x + sway, yt - L, r * 0.7)], 3)
        n = len(pts) - 1
        radii = [r * (1.3 - 0.55 * t / n) * (0.75 + 0.25 * math.sin(t * 1.9 + i)) for t in range(n)] + [r * 0.3]
        tube(m, pts, radii, MOSS, 6, rough=0.5, seed=seed + i, cap_mat=MOSS)
        x += rng.uniform(0.22, 0.34)
        i += 1


def build_moss_cap(p, m, seed):
    w, h, d = p["size"]
    rng = random.Random(seed)
    cushion(m, 0.0, w, -d, 0.0, 0.0, h - 0.04, 14, 14, seed, droop=0.14)
    for k in range(9):
        x, z = rng.uniform(0.6, w - 0.6), -rng.uniform(0.6, d - 0.6)
        y = 0.03 + (h - 0.06) * 0.7
        K.disc(m, (x, y, z), rng.uniform(0.07, 0.11), 0.05, FLOWER, FLOWER, 6)
    for k in range(6):
        blob(m, (rng.uniform(0.6, w - 0.6), 0.14, -rng.uniform(0.6, d - 0.6)), rng.uniform(0.3, 0.55), 0.13, seed=seed + k, rough=0.45)


def build_root_cluster(p, m, seed):
    w, h, d = p["size"]
    yt = h - 0.2  # top of the gripped block; its front face is z = 0
    rng = random.Random(seed)
    roots = [  # (control points, start radius, end radius): two thick roots over the edge, tendrils, grip roots on top
        ([(0.15, yt + 0.16, -0.9), (0.8, yt + 0.2, -0.55), (1.45, yt + 0.19, -0.15), (1.75, yt - 0.08, 0.17), (1.6, yt - 0.7, 0.18),
          (1.9, yt - 1.25, 0.15), (1.65, 0.0, 0.12)], 0.24, 0.06),
        ([(3.85, yt + 0.14, -0.8), (3.2, yt + 0.17, -0.45), (2.65, yt + 0.15, -0.1), (2.45, yt - 0.12, 0.15), (2.7, yt - 0.85, 0.15),
          (2.45, yt - 1.5, 0.12)], 0.2, 0.05),
        ([(1.68, yt - 0.4, 0.17), (1.25, yt - 0.85, 0.12), (1.0, yt - 1.4, 0.1), (1.15, 0.2, 0.08)], 0.1, 0.025),
        ([(2.6, yt - 0.5, 0.15), (3.05, yt - 0.95, 0.1), (3.4, yt - 1.35, 0.08), (3.3, 0.35, 0.06)], 0.09, 0.02),
        ([(1.8, yt - 1.0, 0.16), (2.1, yt - 1.4, 0.1), (2.2, 0.15, 0.07)], 0.07, 0.018),
        ([(0.9, yt + 0.1, -0.55), (0.35, yt + 0.08, -0.25), (0.05, yt + 0.02, 0.03), (-0.02, yt - 0.45, 0.06)], 0.09, 0.02),
        ([(3.2, yt + 0.1, -0.45), (3.6, yt + 0.08, -0.12), (3.95, yt - 0.05, 0.05), (3.9, yt - 0.6, 0.06)], 0.08, 0.02),
        ([(1.2, yt + 0.12, -0.35), (2.0, yt + 0.08, -0.75), (2.9, yt + 0.1, -0.6)], 0.07, 0.04),
    ]
    for i, (ctrl, r0, r1) in enumerate(roots):
        pts = spline(ctrl, 3)
        tube(m, pts, [r0 + (r1 - r0) * (t / (len(pts) - 1)) ** 0.7 for t in range(len(pts))], ROOT, 8 if r0 > 0.15 else 6,
             twist=0.6, rough=0.2, seed=seed + i)
    cushion(m, 0.3, 3.7, -0.92, -0.02, yt, 0.1, 8, 3, seed)
    for k, (x, z) in enumerate([(1.15, -0.4), (2.85, -0.35), (0.5, -0.7)]):
        blob(m, (x, yt + 0.05, z), rng.uniform(0.25, 0.35), 0.2, seed=seed + k)
    blob(m, (1.75, yt - 0.1, 0.2), 0.2, 0.14, seed=seed + 9)
    blob(m, (2.5, yt - 0.15, 0.18), 0.16, 0.12, seed=seed + 7)


def build_sapling(p, m, seed):
    rng = random.Random(seed)
    trunk = spline([(0, -0.05, 0), (0.03, 0.5, 0.02), (-0.05, 1.0, 0.0), (0.04, 1.5, -0.03)], 3)
    tube(m, trunk, [0.055 * (1 - 0.7 * t / (len(trunk) - 1)) for t in range(len(trunk))], ROOT, 6, rough=0.15, seed=seed)
    tips = [Vector(trunk[-1])]
    for k, (y, ang) in enumerate([(0.7, 0.3), (1.0, 2.5), (1.25, 4.3)]):
        base = Vector(trunk[min(len(trunk) - 1, int(y / 1.55 * (len(trunk) - 1)))])
        d = Vector((math.cos(ang), 0, math.sin(ang)))
        end = base + d * 0.38 + Vector((0, 0.3, 0))
        pts = spline([base, base + d * 0.2 + Vector((0, 0.12, 0)), end], 3)
        tube(m, pts, [0.025 * (1 - 0.6 * t / (len(pts) - 1)) for t in range(len(pts))], ROOT, 4, rough=0.1, seed=seed + k)
        tips.append(end)
    for k, t in enumerate(tips):
        for j in range(3):
            a = rng.uniform(0, 2 * math.pi)
            dv = Vector((math.cos(a), rng.uniform(0.2, 0.8), math.sin(a))).normalized()
            pts = [t, t + dv * 0.08, t + dv * 0.17, t + dv * 0.24]
            tube(m, pts, [0.01, 0.07, 0.055, 0.01], MOSS, 4, flat=0.22, seed=seed + k * 4 + j, cap_mat=MOSS)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        d = Vector((math.cos(a), 0, math.sin(a)))
        pts = spline([(0, 0.05, 0), d * 0.2 + Vector((0, 0.02, 0)), d * 0.42 + Vector((0, -0.02, 0))], 3)
        tube(m, pts, [0.04, 0.03, 0.02, 0.015, 0.01, 0.008, 0.005][:len(pts)] + [0.005] * max(0, len(pts) - 7), ROOT, 4, rough=0.2, seed=seed + k)
    blob(m, (0.05, 0.0, 0.05), 0.22, 0.1, seed=seed)
    K.disc(m, (0.15, 0.06, -0.12), 0.05, 0.03, FLOWER, FLOWER, 6)


def organic(p, mats, seed, fn):
    m = Mesh()
    fn(p, m, seed)
    return m.object(p["id"], mats, moss=None, seed=seed)


# ---------- dispatch ----------

def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    pid = p["id"]
    if "monolith" in pid:
        return build_monolith(p, mats, seed)
    if "wall-slab" in pid:
        return build_wall(p, mats, seed)
    if "corner-block" in pid:
        return build_corner(p, mats, seed)
    if pid.endswith("column"):
        return build_column(p, mats, seed)
    if "floor-slab" in pid or "inlay" in pid:
        return build_floor(p, mats, seed)
    if pid.endswith("steps"):
        return build_steps(p, mats, seed)
    if pid.endswith("plinth"):
        return build_plinth(p, mats, seed)
    if pid.endswith("keystone"):
        return build_keystone(p, mats, seed)
    if "glyph-plate" in pid:
        return build_glyph_plate(p, mats, seed)
    if p["family"] == "ring":
        return build_ring(p, mats, seed)
    if "fragment" in pid:
        return build_fragment(p, mats, seed)
    fn = {"old-root-cluster": build_root_cluster, "old-moss-drape": build_moss_drape, "old-moss-cap": build_moss_cap,
          "old-sapling": build_sapling}[pid]
    return organic(p, mats, seed, fn)


_only = os.environ.get("OW_ONLY")
if _only:  # development: build a subset of pieces (and no prefabs) for a quick look
    keys = _only.split(",")
    B.kit["pieces"] = [p for p in B.kit["pieces"] if any(k in p["id"] for k in keys)]
    if not os.environ.get("OW_PREFABS"):
        B.kit["prefabs"] = []
    K.build_all(build_piece, extras=[], biome="ruin")
else:
    K.build_all(build_piece, extras=[("old-fragment-large", "decor"), ("old-fragment-medium", "prop"), ("old-fragment-small", "prop"),
                                     ("old-sapling", "prop"), ("old-monolith-2", "decor")], biome="ruin")
