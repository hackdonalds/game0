# Grey blockouts for an architecture kit: one GLB per piece (with socket empties), prefab assemblies from each
# prefab's `layout`, a socket report, and contact-sheet renders. Pieces without a dedicated shape become boxes.
# Usage: Blender --background --python scripts/kit/blockout.py -- <style>
# Coordinates in kit.json are glTF (Y up, front +Z); Blender is Z up, so V() maps (x, y, z) -> (x, -z, y).
import bpy, bmesh, json, math, sys, os
from mathutils import Vector, Matrix

STYLE = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "rootwarden"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
KIT_DIR = os.path.join(ROOT, "art/models/architecture", STYLE)
OUT = os.path.join(KIT_DIR, "blockout")
kit = json.load(open(os.path.join(KIT_DIR, "kit.json")))
PIECES = {p["id"]: p for p in kit["pieces"]}
SOCKET_COLOURS = {0.6: (0.9, 0.25, 0.2, 1), 1.0: (0.95, 0.75, 0.2, 1), 1.6: (0.2, 0.5, 0.95, 1), 2.5: (0.3, 0.75, 0.4, 1)}
GREY = (0.62, 0.62, 0.6, 1)
TOL = 0.2


def V(x, y, z):
    return Vector((x, -z, y))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_obj(name, bm, colour=GREY):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = colour
    for f in me.polygons:
        f.use_smooth = False
    return ob


# ---------- shape builders (all inputs in glTF space) ----------

def frames(points):
    """Parallel-transport frames along a polyline."""
    tangents = []
    for i in range(len(points)):
        a, b = points[max(i - 1, 0)], points[min(i + 1, len(points) - 1)]
        tangents.append((b - a).normalized())
    n = tangents[0].orthogonal().normalized()
    out = []
    for t in tangents:
        n = (n - t * n.dot(t)).normalized()
        out.append((t, n, t.cross(n)))
    return out


def tube(bm, points, radii, sides=10, cap=True):
    rings = []
    for p, r, (t, n, b) in zip(points, radii, frames(points)):
        rings.append([bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * r)
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])


def hermite(p0, t0, p1, t1, n=12):
    pts = []
    for i in range(n + 1):
        s = i / n
        h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
        h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
        pts.append(p0 * h00 + t0 * h10 + p1 * h01 + t1 * h11)
    return pts


def to_blender(points):
    return [V(*p) for p in points]


def gvec(a):
    return Vector(a)


def socket_path(sa, sb, height=None):
    """Curve between two sockets: leaves a against its outward dir, arrives at b along its dir.
    When both point down (an arch), the tangents are scaled so the centreline peaks at `height`."""
    pa, pb = gvec(sa["pos"]), gvec(sb["pos"])
    k = (pb - pa).length
    if height is not None and sa["dir"][1] < -0.9 and sb["dir"][1] < -0.9:
        k = 4 * height  # a cubic Hermite with tangents ±k peaks at k / 4
    return hermite(pa, -gvec(sa["dir"]) * k, pb, gvec(sb["dir"]) * k)


def build_root(p):
    bm = bmesh.new()
    s = [x for x in p["sockets"] if x["name"] != "hang"]  # hang points sit on the surface, not on the path
    r = s[0]["diameter"] / 2
    if "flare" in p["id"]:
        top = gvec(s[0]["pos"])
        w = p["size"][0] / 2
        tube(bm, to_blender([Vector((0, y, 0)) for y in (0, top.y * 0.5, top.y)]), [w * 0.45, r * 1.15, r])
        for k in range(4):  # buttress fins
            a = k * math.pi / 2 + math.pi / 4
            d = Vector((math.cos(a), 0, math.sin(a)))
            pts = hermite(d * w, Vector((0, 1.2, 0)) - d, Vector((0, top.y * 0.7, 0)) + d * r * 0.6, Vector((0, 1, 0)))
            tube(bm, to_blender(pts), [r * 0.35 * (1 - i / 14) + 0.08 for i in range(len(pts))], 6)
    elif "fork" in p["id"]:
        trunk, left, right = (gvec(x["pos"]) for x in s)
        mid = Vector((0, min(left.y, right.y) * 0.55, 0))
        tube(bm, to_blender([trunk, mid]), [r, r])
        for b in (left, right):
            tube(bm, to_blender(hermite(mid, Vector((0, 1, 0)), b, (b - mid).normalized())), [r] * 13)
    elif len(s) == 2:
        pts = socket_path(s[0], s[1], p["size"][1] - r)
        r1 = s[1]["diameter"] / 2  # tapers change diameter along the path
        tube(bm, to_blender(pts), [r + (r1 - r) * i / (len(pts) - 1) for i in range(len(pts))])
    return bm


def dome_surface(bm, r, arc, rings=8, segs_per_90=6):
    segs = max(2, round(arc / 90 * segs_per_90))
    closed = arc >= 360
    grid = []
    for i in range(rings + 1):
        phi = (math.pi / 2) * i / rings
        row = []
        for j in range(segs if closed else segs + 1):
            th = math.radians(arc) * j / segs
            row.append(bm.verts.new(V(r * math.cos(phi) * math.cos(th), r * math.sin(phi), -r * math.cos(phi) * math.sin(th))))
        grid.append(row)
    n = len(grid[0])
    for i in range(rings):
        for j in range(n if closed else n - 1):
            a, b = grid[i][j], grid[i][(j + 1) % n]
            c, d = grid[i + 1][(j + 1) % n], grid[i + 1][j]
            if len({a, b, c, d}) == 4:
                bm.faces.new((a, b, c, d))
            else:
                bm.faces.new([v for v in (a, b, c, d) if v not in (c, d)][:2] + [c])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)


def solidify(ob, t):
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = t
    m.offset = -1
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="solid")


def build_shell(p):
    bm = bmesh.new()
    if p["id"].endswith("pod"):
        h, w = p["size"][1], p["size"][0] / 2
        pts = [Vector((0, h * (1 - i / 16), 0)) for i in range(17)]
        radii = [max(0.05, w * math.sin(math.pi * (i / 16) ** 0.8)) for i in range(17)]
        tube(bm, to_blender(pts), radii, 14)
        return bm, None
    dome_surface(bm, p["radius"], p["arc"])
    return bm, max(0.25, p["radius"] * 0.06)


def build_insert(p):
    w, h, _ = p["size"]
    bm = bmesh.new()
    if "window" in p["id"]:
        pts = [Vector((0, h / 2, -0.15)), Vector((0, h / 2, 0.15))]
        tube(bm, to_blender(pts), [min(w, h) / 2] * 2, 16)
    else:  # door: arch-topped slab
        prof = [(-w / 2, 0)] + [(math.cos(a) * w / 2, h - w / 2 + math.sin(a) * w / 2) for a in
                                (math.pi - math.pi * k / 10 for k in range(11))] + [(w / 2, 0)]
        front = [bm.verts.new(V(x, y, 0.15)) for x, y in prof]
        back = [bm.verts.new(V(x, y, -0.15)) for x, y in prof]
        bm.faces.new(front)
        bm.faces.new(list(reversed(back)))
        n = len(prof)
        for i in range(n):
            bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]))
    return bm


def build_box(p):
    w, h, d = p["size"]
    x0, z0 = (-w / 2, -d / 2) if p["pivot"] == "bottom-center" else (0, -d)
    bm = bmesh.new()
    vs = [bm.verts.new(V(x0 + w * (i & 1), h * (i >> 1 & 1), z0 + d * (i >> 2 & 1))) for i in range(8)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])
    return bm


def build_cap(p):
    w, h, _ = p["size"]
    bm = bmesh.new()
    pts = [Vector((0, h * i / 8, 0)) for i in range(9)]
    tube(bm, to_blender(pts), [max(0.05, w / 2 * math.cos(math.pi / 2 * i / 8) ** 0.6) for i in range(9)], 16)
    return bm


def cut_openings(ob, p):
    """Cut each opening through the shell: a box at the opening's azimuth and sill height, deep enough to pass the wall."""
    reach = p.get("radius", p["size"][0] / 2)
    for o in p.get("openings", []):
        w, h = o["size"]
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        cutter = new_obj("cutter", bm)
        cutter.scale = (w, reach * 1.2, h)
        a = math.radians(o["azimuth"])
        cutter.location = V(math.sin(a) * reach, o["height"] + h / 2, math.cos(a) * reach)
        cutter.rotation_euler = (0, 0, a)
        mod = ob.modifiers.new("cut", "BOOLEAN")
        mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="cut")
        bpy.data.objects.remove(cutter)


def build_piece(p):
    """Returns the piece object (not yet exported), built at the origin."""
    fam, pid = p["family"], p["id"]
    thickness = None
    if fam == "root":
        bm = build_root(p)
    elif fam == "shell":
        bm, thickness = build_shell(p)
    elif fam == "insert":
        bm = build_insert(p)
    elif pid.endswith(("cap-moss", "cap-flowering-moss")):
        bm = build_cap(p)
    else:
        bm = build_box(p)
    ob = new_obj(pid, bm)
    if thickness:
        solidify(ob, thickness)
    if fam == "shell":
        cut_openings(ob, p)
    for s in p.get("sockets", []):
        e = bpy.data.objects.new(f"socket.{s['name']}", None)
        e.empty_display_type = "CIRCLE"
        e.empty_display_size = s["diameter"] / 2
        e.location = V(*s["pos"])
        e.rotation_mode = "QUATERNION"
        e.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(V(*s["dir"]))
        e["diameter"] = s["diameter"]
        e.parent = ob
        bpy.context.scene.collection.objects.link(e)
    return ob


def socket_markers(ob, p):
    """Coloured discs at sockets so renders show where and how big they are."""
    out = []
    for s in p.get("sockets", []):
        bm = bmesh.new()
        d = V(*s["dir"]).normalized()
        c = V(*s["pos"])
        tube(bm, [c - d * 0.04, c + d * 0.04], [s["diameter"] / 2 + 0.03] * 2, 16)
        m = new_obj(f"{p['id']}.marker.{s['name']}", bm, SOCKET_COLOURS.get(s["diameter"], (1, 0, 1, 1)))
        m.parent = ob
        out.append(m)
    return out


# ---------- export ----------

def export_pieces():
    os.makedirs(OUT, exist_ok=True)
    for p in kit["pieces"]:
        reset()
        ob = build_piece(p)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{p['id']}.glb"), export_format="GLB",
                                  use_selection=True, export_extras=True, export_yup=True, export_apply=True)


# ---------- prefabs: place by layout and check sockets ----------

def world_sockets(entry):
    p = PIECES[entry["id"]]
    rot = Matrix.Rotation(math.radians(entry.get("rotY", 0)), 4, "Y")
    pos = Vector(entry["pos"])
    return [{"piece": entry["id"], "name": s["name"], "diameter": s["diameter"],
             "pos": rot @ Vector(s["pos"]) + pos, "dir": (rot.to_3x3() @ Vector(s["dir"])).normalized()}
            for s in p.get("sockets", [])]


def check_prefab(f):
    issues, joints = [], []
    counts = {}
    for e in f["layout"]:
        counts[e["id"]] = counts.get(e["id"], 0) + 1
    listed = {x["id"]: x["count"] for x in f["pieces"]}
    if counts != listed:
        issues.append(f"layout counts {counts} differ from pieces {listed}")
    socks = [s for e in f["layout"] for s in world_sockets(e)]
    used = set()
    for i, a in enumerate(socks):
        for j in range(i + 1, len(socks)):
            b = socks[j]
            if a["piece"] == b["piece"] and (a["pos"] - b["pos"]).length < 1e-6:
                continue
            if (a["pos"] - b["pos"]).length < TOL:
                facing = a["dir"].dot(b["dir"]) < -0.8
                ok = facing and a["diameter"] == b["diameter"]
                joints.append(f"{a['piece']}.{a['name']} ↔ {b['piece']}.{b['name']}: {'ok' if ok else 'MISMATCH'}"
                              + ("" if ok else f" (diameters {a['diameter']}/{b['diameter']}, facing {facing})"))
                used |= {i, j}
                if not ok:
                    issues.append(joints[-1])
    free = [f"{s['piece']}.{s['name']}" for k, s in enumerate(socks) if k not in used and s["pos"].y > 0.05]
    return {"id": f["id"], "joints": joints, "open_sockets_above_ground": free, "issues": issues}


# ---------- renders ----------

def figure(at):
    bm = bmesh.new()
    h = kit.get("scaleFigure", 1.8)
    tube(bm, [at, at + Vector((0, 0, h - 0.25))], [0.22, 0.22], 12)
    tube(bm, [at + Vector((0, 0, h - 0.4)), at + Vector((0, 0, h))], [0.17, 0.17], 12)
    return new_obj("figure", bm, (0.85, 0.45, 0.3, 1))


def label(text, at, size=0.5):
    cu = bpy.data.curves.new(text, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new(text, cu)
    ob.location = at
    ob.rotation_euler = (math.radians(55), 0, math.radians(35))
    ob.color = (0.1, 0.1, 0.1, 1)
    bpy.context.scene.collection.objects.link(ob)


def render(path, objs_bounds):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "OBJECT"
    sc.display.shading.show_cavity = True
    sc.display.shading.show_shadows = True
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.9, 0.9, 0.88)
    lo, hi = objs_bounds
    centre = (lo + hi) / 2
    span = max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = span * 1.15
    sc.collection.objects.link(cam)
    d = Vector((1, -1.3, 1.1)).normalized()
    cam.location = centre + d * span * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = span * 6
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1500
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    return Vector(tuple(min(p[i] for p in pts) for i in range(3))), Vector(tuple(max(p[i] for p in pts) for i in range(3)))


def render_pieces():
    reset()
    x = y = row_h = 0.0
    width = 60.0
    objs = []
    for p in kit["pieces"]:
        w, h, d = p["size"]
        if x + w > width:
            x, y = 0.0, y - row_h - 3
            row_h = 0.0
        ob = build_piece(p)
        ob.location = Vector((x + w / 2, y, 0))
        objs += [ob] + socket_markers(ob, p)
        label(p["id"].removeprefix(f"{kit['prefix']}-"), Vector((x + w / 2, y - d / 2 - 1.2, 0)), 0.45)
        x += w + 2.5
        row_h = max(row_h, d)
    objs.append(figure(Vector((-3, 0, 0))))
    bpy.context.view_layer.update()
    render(os.path.join(OUT, "sheet-pieces.png"), bounds(objs))


def render_prefabs(report):
    reset()
    x = 0.0
    objs = []
    for f in kit.get("prefabs", []):
        if "layout" not in f:
            continue
        lo = hi = None
        group = []
        for e in f["layout"]:
            p = PIECES[e["id"]]
            ob = build_piece(p)
            ob.rotation_euler = (0, 0, math.radians(e.get("rotY", 0)))
            ob.location = V(*e["pos"])
            group += [ob] + socket_markers(ob, p)
        bpy.context.view_layer.update()
        lo, hi = bounds(group)
        shift = Vector((x - lo.x, 0, 0))
        for o in group:
            if o.parent is None:
                o.location += shift
        bpy.context.view_layer.update()
        lo, hi = bounds(group)
        objs += group
        objs.append(figure(Vector((hi.x + 1, lo.y, 0))))
        label(f["name"], Vector(((lo.x + hi.x) / 2, lo.y - 3, 0)), 1.0)
        x = hi.x + 6
    bpy.context.view_layer.update()
    if objs:
        render(os.path.join(OUT, "sheet-prefabs.png"), bounds(objs))


export_pieces()
report = [check_prefab(f) for f in kit.get("prefabs", []) if "layout" in f]
json.dump(report, open(os.path.join(OUT, "socket-report.json"), "w"), indent=2, ensure_ascii=False)
render_pieces()
render_prefabs(report)
for r in report:
    print(f"[prefab] {r['id']}: {len(r['joints'])} joints, {len(r['issues'])} issues")
    for i in r["issues"]:
        print("   ", i)
