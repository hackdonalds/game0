# Shared Blender tooling for the detailed architecture kits (scripts/kit/<style>.py): painted materials, a UV-aware
# mesh builder in glTF coordinates, swept tubes, boxes and extrusions with box-projected UVs, bevel and handmade
# wobble, and the build_all() pipeline (pieces, joined prefabs, demo catalogue, contact sheets).
# Style scripts import it after blockout.py, which has already loaded the style's kit.json from the command line.
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402

V = B.V
OUT = B.KIT_DIR
PREFAB_OUT = os.path.join(OUT, "prefabs")

# Style scripts set these: the material list and what tube end caps and moss use
# Materials whose name contains "Card" are alpha-cutout sprites (leaf cards, grass, ivy): their texture's alpha
# drives a 0.5 clip that the glTF exporter writes as alphaMode MASK, and they render double-sided.
MATS = []          # [(name, texture file | (r, g, b), emission strength)]
TEX = ""           # folder of the style's textures
CAP_MAT = 0        # material index for tube end caps (end grain)
MOSS = None        # (from material, to material, minimum upward normal) or None


def configure(mats, tex_dir, cap_mat=0, moss=None):
    global MATS, TEX, CAP_MAT, MOSS
    MATS, TEX, CAP_MAT, MOSS = mats, tex_dir, cap_mat, moss


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
            t.extension = "MIRROR"  # mirrored tiling hides the seams of painted swatches
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
            if "Card" in name:
                clip = nt.nodes.new("ShaderNodeMath")
                clip.operation = "ROUND"  # the glTF exporter reads Round as an alpha clip at 0.5
                nt.links.new(t.outputs["Alpha"], clip.inputs[0])
                nt.links.new(clip.outputs[0], bsdf.inputs["Alpha"])
                m.use_backface_culling = False
                if hasattr(m, "blend_method"):
                    m.blend_method = "CLIP"
                if hasattr(m, "surface_render_method"):
                    m.surface_render_method = "DITHERED"
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
    """bmesh with a UV layer; all coordinates are glTF (Y up, front +Z) and converted on the way in."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.project = []  # faces whose UVs are box-projected when the object is made
        self.normals = {}  # vertex -> normal hint (glTF), e.g. crown-centred normals so leaf cards shade as one mass
        self.keep = set()  # faces whose winding is deliberate (cards) and must not be flipped by normal recalculation

    def vert(self, p):
        return self.bm.verts.new(V(*p))

    def face(self, verts, uvs, mat, tile=1.0):
        f = self.bm.faces.new(verts)
        f.material_index = mat
        if uvs is None:
            self.project.append((f, tile))
        else:
            for loop, uv in zip(f.loops, uvs):
                loop[self.uv].uv = uv
        return f

    def object(self, name, mats, moss="default", seed=0.0, smooth=True):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)  # weld UV seams; UVs live on loops and survive
        self.project = [(f, t) for f, t in self.project if f.is_valid]
        bm.verts.index_update()
        hints = {v.index: V(*n).normalized() for v, n in self.normals.items() if v.is_valid}
        bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f not in self.keep])
        bm.normal_update()
        for f, tile in self.project:
            box_uv(f, self.uv, tile)
        rule = MOSS if moss == "default" else moss
        if rule:
            src, dst, up = rule
            for f in bm.faces:
                if f.material_index == src and f.normal.z > up and noise.noise(f.calc_center_median() * 0.9 + Vector((seed, 0, 0))) > -0.15:
                    f.material_index = dst
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        for poly in me.polygons:
            poly.use_smooth = smooth
        if hints:
            me.normals_split_custom_set_from_vertices([hints.get(i, v.normal) for i, v in enumerate(me.vertices)])
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def box_uv(f, layer, tile):
    """Project a face's UVs along its dominant normal axis, `tile` metres per texture repeat (Blender coords)."""
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    u_i, v_i = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
    for loop in f.loops:
        co = loop.vert.co
        loop[layer].uv = (co[u_i] / tile, co[v_i] / tile)


# ---------- swept shapes ----------

def hermite(p0, t0, p1, t1, n=20):
    return B.hermite(Vector(p0), Vector(t0), Vector(p1), Vector(t1), n)


def path_between(sa, sb, height=None, n=20):
    pa, pb = Vector(sa["pos"]), Vector(sb["pos"])
    k = (pb - pa).length
    if height is not None and sa["dir"][1] < -0.9 and sb["dir"][1] < -0.9:
        k = 4 * height
    return hermite(pa, -Vector(sa["dir"]) * k, pb, Vector(sb["dir"]) * k, n)


def tube(m, pts, radii, mat, sides=10, twist=0.0, rough=0.0, seed=0.0, caps=(True, True), tile=1.2, closed=False, flat=1.0, planar=False, cap_mat=None):
    """Swept tube with UVs (u around, v along, `tile` metres per repeat), surface noise that fades out near both
    ends so socket caps stay exact, and end caps in the style's cap material."""
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
    cm = CAP_MAT if cap_mat is None else cap_mat
    for end, ring, flip in ((caps[0], rings[0], True), (caps[1], rings[-1], False)):
        if not end or closed:
            continue
        verts = [v for v, _ in ring[:-1]]
        uvs = [(0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
        if flip:
            verts, uvs = verts[::-1], uvs[::-1]
        m.face(verts, uvs, cm)
    return rings


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


# ---------- boxes and extrusions (box-projected UVs) ----------

def box(m, lo, hi, mat, tile=1.0, mats=None):
    """Axis-aligned box from lo to hi (glTF). `mats` may override per side: keys top, bottom, front, back, left, right."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = {(i, j, k): m.vert((x1 if i else x0, y1 if j else y0, z1 if k else z0)) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    sides = {"bottom": [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], "top": [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
             "front": [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], "back": [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
             "left": [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], "right": [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]}
    for name, idx in sides.items():
        m.face([v[i] for i in idx], None, (mats or {}).get(name, mat), tile)


def extrude(m, outline, z0, z1, mat, tile=1.0, side_mat=None):
    """Prism from a 2D outline (x, y) in the XY plane, between depths z0 and z1 (glTF)."""
    front = [m.vert((x, y, z1)) for x, y in outline]
    back = [m.vert((x, y, z0)) for x, y in outline]
    m.face(front, None, mat, tile)
    m.face(back[::-1], None, mat, tile)
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        m.face((back[i], back[j], front[j], front[i]), None, side_mat if side_mat is not None else mat, tile)


def loft(m, profile, path, mat, tile=1.0, closed_profile=True):
    """Sweep a 2D profile (x across, y up) along a polyline path in the XZ plane (glTF); good for mouldings and rails."""
    path = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side = Vector((t.z, 0, -t.x))
        rings.append([m.vert(p + side * x + Vector((0, y, 0))) for x, y in profile])
    n = len(profile)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n if closed_profile else n - 1):
            k1 = (k + 1) % n
            m.face((r0[k], r0[k1], r1[k1], r1[k]), None, mat, tile)


def bevel(ob, width=0.04, segments=2, angle=40):
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments, mod.limit_method = width, segments, "ANGLE"
    mod.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="bevel")
    return ob


def wobble(ob, amp=0.03, scale=1.2, seed=0.0, keep_base=True):
    """Handmade irregularity: nudge vertices with smooth noise; vertices at y=0 stay put so pieces still sit flat."""
    for v in ob.data.vertices:
        if keep_base and v.co.z < 1e-3:
            continue
        q = v.co * scale + Vector((seed, seed * 1.3, 0))
        v.co += Vector((noise.noise(q), noise.noise(q + Vector((7, 0, 0))), noise.noise(q + Vector((0, 13, 0))) * 0.5)) * amp
    return ob


# ---------- 2D outlines ----------

def arch(w, h, n=12):
    return [(-w / 2, 0)] + [(math.cos(a) * w / 2, h - w / 2 + math.sin(a) * w / 2) for a in
                            (math.pi - math.pi * k / n for k in range(n + 1))] + [(w / 2, 0)]


def pointed_arch(w, h, n=8):
    """Gothic two-centred arch: springs at h - w * 0.8, apex at h."""
    spring = h - w * 0.8
    left = [(-w / 2 + w * (1 - math.cos(a)), spring + w * math.sin(a)) for a in (math.radians(60) * k / n for k in range(n + 1))]
    right = [(-x, y) for x, y in reversed(left)]
    return [(-w / 2, 0)] + left + right[1:] + [(w / 2, 0)]


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


def fill(m, outline, z, mat):
    xs = [x for x, _ in outline]
    ys = [y for _, y in outline]
    w, h = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    verts = [m.vert((x, y, z)) for x, y in outline]
    m.face(verts[::-1], [((x - min(xs)) / w, (y - min(ys)) / h) for x, y in outline][::-1], mat)


# ---------- objects ----------

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


def tris(ob):
    return sum(len(poly.vertices) - 2 for poly in ob.data.polygons)


def export(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=88)


def place_layout(layout, build, mats):
    parts = []
    for e in layout:
        ob = build(B.PIECES[e["id"]], mats)
        ob.rotation_euler = (0, 0, math.radians(e.get("rotY", 0)))
        ob.location = V(*e["pos"])
        parts.append(ob)
    bpy.context.view_layer.update()
    return parts


def build_all(build_piece, extras=(), biome=None):
    """Export every piece, every prefab with a layout (joined), a demo catalogue and two contact sheets.
    `extras` are (piece id, catalogue category) pairs copied next to the prefabs for the demo."""
    os.makedirs(PREFAB_OUT, exist_ok=True)
    style = B.kit["style"]
    counts = {}
    for p in B.kit["pieces"]:
        mats = reset()
        ob = build_piece(p, mats)
        counts[p["id"]] = tris(ob)
        export(ob, os.path.join(OUT, f"{p['id']}.glb"))
    json.dump(counts, open(os.path.join(OUT, "tris.json"), "w"), indent=2)

    catalogue = []
    for f in B.kit.get("prefabs", []):
        if "layout" not in f:
            continue
        mats = reset()
        parts = place_layout(f["layout"], build_piece, mats)
        bpy.ops.object.select_all(action="DESELECT")
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        ob = join(parts, f["id"])
        lo, hi = B.bounds([ob])
        export(ob, os.path.join(PREFAB_OUT, f"{f['id']}.glb"))
        catalogue.append({"id": f["id"], "file": f"{f['id']}.glb", "category": "building", "biomes": [biome or style],
                          "radius": round(max(hi.x - lo.x, hi.y - lo.y) / 2, 2), "height": round(hi.z - lo.z, 2),
                          "minScale": 0.9, "maxScale": 1.1, "collide": True, "tris": tris(ob)})
    for pid, cat in extras:
        p = B.PIECES[pid]
        catalogue.append({"id": pid, "file": f"{pid}.glb", "category": cat, "biomes": [biome or style], "radius": round(p["size"][0] / 2, 2),
                          "height": p["size"][1], "minScale": 0.9, "maxScale": 1.2, "collide": cat == "decor"})
        mats = reset()
        export(build_piece(p, mats), os.path.join(PREFAB_OUT, f"{pid}.glb"))
    json.dump(catalogue, open(os.path.join(PREFAB_OUT, f"{style}.json"), "w"), indent=2)

    render_sheets(build_piece)
    over = {k: v for k, v in counts.items() if v > B.PIECES[k]["tris"]}
    print(f"[{style}] built {len(counts)} pieces, {len(catalogue)} catalogue entries")
    print(f"[{style}] over manifest tris: {json.dumps(over)}")
    return counts


def render_sheets(build_piece, width=60):
    prefix = B.kit["prefix"] + "-"
    for name in ("sheet-pieces", "sheet-prefabs"):
        mats = reset()
        objs = []
        x = y = row = 0.0
        if name == "sheet-pieces":
            for p in B.kit["pieces"]:
                w, _, d = p["size"]
                if x + w > width:
                    x, y, row = 0.0, y - row - 3, 0.0
                ob = build_piece(p, mats)
                ob.location += Vector((x + w / 2, y, 0))
                objs.append(ob)
                B.label(p["id"].removeprefix(prefix), Vector((x + w / 2, y - d / 2 - 1.2, 0)), 0.45)
                x += w + 2.5
                row = max(row, d)
        else:
            for f in B.kit.get("prefabs", []):
                if "layout" not in f:
                    continue
                group = place_layout(f["layout"], build_piece, mats)
                lo, hi = B.bounds(group)
                for o in group:
                    o.location.x += x - lo.x
                bpy.context.view_layer.update()
                lo, hi = B.bounds(group)
                objs += group
                objs.append(B.figure(Vector((hi.x + 1, lo.y, 0))))
                B.label(f["name"], Vector(((lo.x + hi.x) / 2, lo.y - 3, 0)), 1.0)
                x = hi.x + 6
        if not objs:
            continue
        objs.append(B.figure(Vector((-3, 0, 0))))
        bpy.context.view_layer.update()
        B.render(os.path.join(OUT, f"{name}.png"), B.bounds(objs), "TEXTURE")
