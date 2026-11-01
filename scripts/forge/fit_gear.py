# Fit a garment or armour piece to a family body (the Outfit Studio / BodySlide loop, scripted):
#   0. subdivide coarse pieces (long edges let a dense body bulge through between gear vertices),
#   1. push the garment out of the body by its layer offset: gear vertices out of the body, then gear faces out
#      wherever body vertices still poke through them,
#   2. copy skin weights from the nearest body surface (top 4, normalised; loose parts such as skirts and capes
#      get their weights smoothed),
#   3. bake one shape key per body shape key through Surface Deform, pushed out again per key, so the garment
#      follows every slider and every people's signature shape,
#   4. work out what it covers: body regions, and an exact body mask in the shared body UV space
#      (<out>.mask.png), so the body is hidden under the piece in every pose and nothing pokes through.
# The garment must already be aligned to the body in its rest pose.
#   bun run art:forge fit_gear --body <body.glb> --gear <garment.glb> --out <fitted.glb> --slot top
#     [--family humanoid] [--covers ["chest", "belly"]] [--hides ["cloak"]] [--cover-threshold 0.85] [--smooth 12]
#     [--rest-keys {"people_galeborne": 1}]
#     [--own-shape true] [--mask true] [--max-edge 0.02] [--loose 0.08] [--hug 0.012] [--erode 2]
# --rest-keys: the body shape the piece was made on (e.g. {"people_galeborne": 1} for a piece cut from the
# Galeborne). By default the piece is then re-expressed on the neutral base so it fits every people.
# --own-shape: a people's own part (mantle, crest): it keeps that shape, and only the other keys are baked.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, contract, done, export, fail, load, path, rasterise, regions_uv, reset, save_png, skinned_meshes, triangles, warn, with_active  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
slot = a["slot"]
layer = c["slots"].get(slot)
if layer is None:
    fail(f"unknown slot {slot}", slots=list(c["slots"]))
offset = a.get("offset", c["gearLayers"].get(layer, {}).get("offset", 0.004))

reset()
body_objects = load(a["body"])
arm = armature_of(body_objects)
body = max(skinned_meshes(body_objects, arm), key=lambda m: len(m.data.vertices))
arm.data.pose_position = "REST"
keys = body.data.shape_keys.key_blocks[1:] if body.data.shape_keys else []
rest_keys = a.get("rest-keys", {})
for k in keys:
    k.value = rest_keys.get(k.name, 0)

gear_objects = load(a["gear"])
parts = [o for o in gear_objects if o.type == "MESH"]
if not parts:
    fail("the gear file has no mesh")
for o in parts:
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
    o.modifiers.clear()
    o.vertex_groups.clear()
    if o.data.shape_keys:
        o.shape_key_clear()
for o in gear_objects:
    if o not in parts:
        bpy.data.objects.remove(o)
gear = parts[0]
if len(parts) > 1:
    with bpy.context.temp_override(active_object=gear, object=gear, selected_objects=parts, selected_editable_objects=parts):
        bpy.ops.object.join()
with with_active(gear):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
deps = bpy.context.evaluated_depsgraph_get

# 0. Subdivide while edges are long and the budget allows
budget = c["budgets"].get("gear", {}).get("triangles", 6000)
subdivided = 0
while True:
    me = gear.data
    mean_edge = sum((me.vertices[e.vertices[0]].co - me.vertices[e.vertices[1]].co).length for e in me.edges) / max(len(me.edges), 1)
    if mean_edge <= a.get("max-edge", 0.02) or triangles(gear) * 4 > budget:
        break
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    subdivided += 1
gear.data.calc_loop_triangles()
gtris = [tuple(t.vertices) for t in gear.data.loop_triangles]
# Generated meshes are split at UV seams: vertices at one position move together
weld = {}
for v in gear.data.vertices:
    weld.setdefault(tuple(round(x, 5) for x in v.co), []).append(v.index)
weld_groups = [g for g in weld.values() if len(g) > 1]


def body_surface():
    """BVH of the body as it currently evaluates (current shape key values), in world space."""
    ev = body.evaluated_get(deps())
    mesh = ev.to_mesh()
    mesh.calc_loop_triangles()
    mw = body.matrix_world
    verts = [mw @ v.co for v in mesh.vertices]
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, tris), verts, tris


def push_out(coords, bvh, limit=0.12):
    moved = 0
    for i, v in enumerate(coords):
        loc, n, _, d = bvh.find_nearest(v)
        if loc is not None and d < limit and (v - loc).dot(n) < offset:
            coords[i] = loc + n * offset
            moved += 1
    return moved


def resolve(coords, bverts, bnormals, iterations=5):
    """Push gear faces out wherever body vertices poke through them (or come closer than the layer offset)."""
    worst = 0.0
    for _ in range(iterations):
        gbvh = BVHTree.FromPolygons(coords, gtris)
        delta = [Vector() for _ in coords]
        weight = [0.0] * len(coords)
        worst = 0.0
        for p, bn in zip(bverts, bnormals):
            loc, n, ti, d = gbvh.find_nearest(p)
            if loc is None or d > 0.06:
                continue
            if n.dot(bn) < 0:
                n = -n  # gear faces wound inwards
            need = (p - loc).dot(n) + offset
            if need <= 0:
                continue
            worst = max(worst, need - offset)
            i0, i1, i2 = gtris[ti]
            p0, p1, p2 = coords[i0], coords[i1], coords[i2]
            area = ((p1 - p0).cross(p2 - p0)).length or 1e-12
            for idx, (x, y) in zip((i0, i1, i2), ((p1, p2), (p2, p0), (p0, p1))):
                b = ((x - loc).cross(y - loc)).length / area
                delta[idx] += n * need * b
                weight[idx] += b
        moved = [i for i, w in enumerate(weight) if w > 0]
        if not moved:
            break
        for i in moved:
            coords[i] = coords[i] + delta[i] / max(weight[i], 1.0)
        for group in weld_groups:
            mean = sum((coords[i] for i in group), Vector()) / len(group)
            for i in group:
                coords[i] = mean
    return worst


def fit_surface(coords):
    """Gear vertices out of the body, then gear faces out from under poking body vertices."""
    bvh, bverts, btris = body_surface()
    moved = push_out(coords, bvh)
    ev = body.evaluated_get(deps())
    mesh = ev.to_mesh()
    bnormals = [body.matrix_world.to_3x3() @ v.normal for v in mesh.vertices]
    ev.to_mesh_clear()
    resolve(coords, bverts, bnormals)
    return moved


# 1. Push the basis out of the body
bvh, bverts, btris = body_surface()
coords = [gear.matrix_world @ v.co for v in gear.data.vertices]
moved_basis = fit_surface(coords)
bvh, bverts, btris = body_surface()
for v, co in zip(gear.data.vertices, coords):
    v.co = co

# 2. Skin weights from the nearest body triangle, interpolated barycentrically
bnames = {g.index: g.name for g in body.vertex_groups}
deform = {b.name for b in arm.data.bones if b.use_deform}
bweights = [{bnames[g.group]: g.weight for g in v.groups if g.weight > 0 and bnames[g.group] in deform} for v in body.data.vertices]
gweights, distance = [], []
for co in coords:
    loc, _, tri, d = bvh.find_nearest(co)
    i0, i1, i2 = btris[tri]
    p0, p1, p2 = bverts[i0], bverts[i1], bverts[i2]
    area = ((p1 - p0).cross(p2 - p0)).length or 1e-12
    bary = [((p1 - loc).cross(p2 - loc)).length / area, ((p2 - loc).cross(p0 - loc)).length / area, ((p0 - loc).cross(p1 - loc)).length / area]
    w: dict[str, float] = {}
    for idx, b in zip((i0, i1, i2), bary):
        for name, weight in bweights[idx].items():
            w[name] = w.get(name, 0) + weight * b
    gweights.append(w)
    distance.append(d)
# Loose cloth (far from the body) gets Laplacian-smoothed weights so it doesn't tear between bones
# Only genuinely loose cloth (capes, skirts) gets smoothed weights; closer cloth (shorts, sleeves) follows the
# body's own weights so limbs can't swing through it
far = [d > offset + a.get("loose", 0.08) for d in distance]
if any(far):
    neighbours = [[] for _ in gear.data.vertices]
    for e in gear.data.edges:
        x, y = e.vertices
        neighbours[x].append(y)
        neighbours[y].append(x)
    for _ in range(int(a.get("smooth", 12))):
        nxt = []
        for i, w in enumerate(gweights):
            if not far[i] or not neighbours[i]:
                nxt.append(w)
                continue
            acc = dict(w)
            for j in neighbours[i]:
                for name, weight in gweights[j].items():
                    acc[name] = acc.get(name, 0) + weight
            nxt.append({k: v / (len(neighbours[i]) + 1) for k, v in acc.items()})
        gweights = nxt
groups = {}
unweighted = 0
# Vertices whose nearest body triangle carries no weights (eyeballs, seams) borrow the nearest weighted vertex's
from mathutils.kdtree import KDTree  # noqa: E402
weighted_idx = [i for i, w in enumerate(bweights) if w]
kd = KDTree(len(weighted_idx))
for j, i in enumerate(weighted_idx):
    kd.insert(bverts[i], j)
kd.balance()
for i, w in enumerate(gweights):
    if not any(v > 0 for v in w.values()):
        _, j, _ = kd.find(coords[i])
        gweights[i] = dict(bweights[weighted_idx[j]])
        unweighted += 1
if unweighted:
    warn(f"{unweighted} gear vertices borrowed weights from the nearest weighted body vertex")
for i, w in enumerate(gweights):
    top = sorted(w.items(), key=lambda kv: kv[1], reverse=True)[: c["skeleton"]["maxInfluences"]]
    total = sum(v for _, v in top)
    if total <= 0:
        continue
    for name, weight in top:
        g = groups.get(name) or gear.vertex_groups.new(name=name)
        groups[name] = g
        g.add([i], weight / total, "REPLACE")

# 3. One gear shape key per body shape key, through Surface Deform (bound in the rest-keys state)
own_shape = bool(a.get("own-shape", False))
baked, skipped = [], []
if keys:
    sd = gear.modifiers.new("forge_fit", "SURFACE_DEFORM")
    sd.target = body
    sd.falloff = 8
    with with_active(gear):
        bpy.ops.object.surfacedeform_bind(modifier=sd.name)
    binding = None
    if not sd.is_bound:
        # Fallback binder: every vertex rides on its nearest body triangle (barycentric point plus an offset in
        # the triangle's frame). Surface Deform refuses some pieces; this always binds.
        warn("Surface Deform could not bind; using the nearest-triangle binder")
        gear.modifiers.remove(sd)
        sd = None
        _, rest_verts, rest_tris = body_surface()
        rbvh = BVHTree.FromPolygons(rest_verts, rest_tris)

        def frame(p0, p1, p2):
            e1 = (p1 - p0).normalized()
            n = (p1 - p0).cross(p2 - p0).normalized()
            return e1, n.cross(e1), n

        binding = []
        for v in gear.data.vertices:
            p = gear.matrix_world @ v.co
            loc, _, ti, _ = rbvh.find_nearest(p)
            i0, i1, i2 = rest_tris[ti]
            p0, p1, p2 = rest_verts[i0], rest_verts[i1], rest_verts[i2]
            area = ((p1 - p0).cross(p2 - p0)).length
            if area < 1e-10:
                # Degenerate triangle: ride on its nearest corner instead
                k = min(range(3), key=lambda j: ((p0, p1, p2)[j] - loc).length)
                bary = tuple(1.0 if j == k else 0.0 for j in range(3))
            else:
                raw = (((p1 - loc).cross(p2 - loc)).length / area, ((p2 - loc).cross(p0 - loc)).length / area, ((p0 - loc).cross(p1 - loc)).length / area)
                total = sum(raw) or 1.0
                bary = tuple(min(max(b / total, 0.0), 1.0) for b in raw)
            e1, e2, n = frame(p0, p1, p2)
            d = p - loc
            binding.append(((i0, i1, i2), bary, (d.dot(e1), d.dot(e2), d.dot(n))))

    def shaped(values: dict) -> list:
        """Gear vertex positions with the body's keys set to `values` (others 0), pushed out of the body."""
        for k in keys:
            k.value = values.get(k.name, 0)
        if binding is None:
            ev = gear.evaluated_get(deps())
            mesh = ev.to_mesh()
            co = [gear.matrix_world @ v.co for v in mesh.vertices]
            ev.to_mesh_clear()
        else:
            _, bv, _ = body_surface()
            co = []
            for (i0, i1, i2), (b0, b1, b2), (x, y, z) in binding:
                p0, p1, p2 = bv[i0], bv[i1], bv[i2]
                n = (p1 - p0).cross(p2 - p0)
                base = p0 * b0 + p1 * b1 + p2 * b2
                if n.length < 1e-10 or (p1 - p0).length < 1e-9:
                    co.append(base + Vector((x, y, z)).length * Vector((0, 0, 0)))  # degenerate now: keep the point
                    continue
                e1 = (p1 - p0).normalized()
                n = n.normalized()
                co.append(base + e1 * x + n.cross(e1) * y + n * z)
        fit_surface(co)
        return co

    if own_shape:
        # A people's own part: keeps the shape it was made in; the people's keys change nothing
        basis = shaped(rest_keys)
        targets = {k.name: (basis if k.name in rest_keys else shaped({**rest_keys, k.name: 1})) for k in keys}
    else:
        # Re-expressed on the neutral base, so it fits every people and slider
        basis = shaped({})
        targets = {k.name: shaped({k.name: 1}) for k in keys}
    if sd:
        gear.modifiers.remove(sd)
    inv = gear.matrix_world.inverted()
    for v, co in zip(gear.data.vertices, basis):
        v.co = inv @ co
    gear.shape_key_add(name="Basis", from_mix=False)
    skipped = []
    for name, co in targets.items():
        # Keys that don't move this piece (face shapes on shorts) are left out; the runtime skips missing keys
        if max((p - b).length for p, b in zip(co, basis)) < a.get("key-threshold", 0.0005):
            skipped.append(name)
            continue
        kb = gear.shape_key_add(name=name, from_mix=False)
        for i, p in enumerate(co):
            kb.data[i].co = inv @ p
        baked.append(name)
    for k in keys:
        k.value = rest_keys.get(k.name, 0)

# 4. Covered body regions: body vertices just behind the garment surface
covers = a.get("covers")
if covers is None:
    ev = gear.evaluated_get(deps())
    gm = ev.to_mesh()
    gm.calc_loop_triangles()
    gbvh = BVHTree.FromPolygons([gear.matrix_world @ v.co for v in gm.vertices], [tuple(t.vertices) for t in gm.loop_triangles])
    ev.to_mesh_clear()
    uv = regions_uv(body)
    region_of_vertex = {}
    if uv:
        for loop in body.data.loops:
            region_of_vertex[loop.vertex_index] = int(uv.data[loop.index].uv[0] * 32)
    total, hidden = {}, {}
    for i, co in enumerate(bverts):
        r = region_of_vertex.get(i)
        if r is None:
            continue
        total[r] = total.get(r, 0) + 1
        loc, n, _, d = gbvh.find_nearest(co)
        if loc is not None and d < offset + 0.05 and (co - loc).dot(n) < 0:
            hidden[r] = hidden.get(r, 0) + 1
    threshold = a.get("cover-threshold", 0.85)
    covers = sorted(c["regions"][r] for r, n in total.items() if hidden.get(r, 0) / n >= threshold)
    coverage = {c["regions"][r]: round(hidden.get(r, 0) / n, 2) for r, n in total.items() if hidden.get(r, 0)}
else:
    coverage = None

# 5. Exact body mask: body faces whose every vertex has the piece just outside it along its normal
mask_file = None
if a.get("mask", layer not in ("skin",)):
    for k in keys:
        k.value = rest_keys.get(k.name, 0)
    ev = gear.evaluated_get(deps())
    gm = ev.to_mesh()
    gm.calc_loop_triangles()
    gbvh = BVHTree.FromPolygons([gear.matrix_world @ v.co for v in gm.vertices], [tuple(t.vertices) for t in gm.loop_triangles])
    ev.to_mesh_clear()
    ev = body.evaluated_get(deps())
    bm_eval = ev.to_mesh()
    covered_v = []
    for v in bm_eval.vertices:
        # Covered: the piece hugs the skin here (within the layer offset plus 12 mm). Where cloth flares away
        # (hems, loose legs) the skin under it is still seen at an angle, so it stays visible
        p, n = body.matrix_world @ v.co, (body.matrix_world.to_3x3() @ v.normal).normalized()
        hit = gbvh.ray_cast(p - n * 0.03, n, 0.03 + offset + a.get("hug", 0.012))[0]
        covered_v.append(hit is not None)
    ev.to_mesh_clear()
    # Erode the hidden area away from the piece's edges (no see-through gaps at hems or holes)
    neighbours = [[] for _ in body.data.vertices]
    for e in body.data.edges:
        x, y = e.vertices
        neighbours[x].append(y)
        neighbours[y].append(x)
    for _ in range(int(a.get("erode", 2))):
        covered_v = [cv and all(covered_v[j] for j in neighbours[i]) for i, cv in enumerate(covered_v)]
    body.data.calc_loop_triangles()
    uv0 = body.data.uv_layers[0].data
    tri_uv = [[uv0[li].uv[:] for li in t.loops] for t in body.data.loop_triangles if all(covered_v[i] for i in t.vertices)]
    if tri_uv:
        img = rasterise(np.array(tri_uv), np.ones((len(tri_uv), 3), dtype=np.float32), int(a.get("mask-size", 512)), grow=1)
        mask_file = save_png(img, Path(path(a["out"])).with_suffix(".mask.png"))
    else:
        warn("the piece covers no whole body face; no mask written")

gear.name = Path(a["out"]).stem.split(".")[0]
gear.parent = arm
gear.matrix_parent_inverse = Matrix.Identity(4)
mod = gear.modifiers.new("Armature", "ARMATURE")
mod.object = arm
arm.data.pose_position = "POSE"
meta = {"family": c["family"], "kind": "gear", "slot": slot, "ownShape": own_shape, "restKeys": rest_keys, "layer": layer, "order": c["gearLayers"].get(layer, {}).get("order", 0),
        "offset": offset, "covers": covers, "hides": a.get("hides", []), "shapeKeys": baked, "fittedKeys": baked + skipped, "body": a["body"],
        "mask": Path(mask_file).name if mask_file else None}
gear["forge"] = json.dumps(meta)
arm["forge"] = json.dumps({"family": c["family"], "kind": "gear-skeleton"})
for o in list(bpy.data.objects):
    if o not in (gear, arm):
        bpy.data.objects.remove(o)
out = export(a["out"], [arm, gear])
Path(out).with_suffix(".part.json").write_text(json.dumps(meta, indent=2))
done(out=out, slot=slot, layer=layer, covers=covers, coverage=coverage, shapeKeys=len(baked), unchangedKeys=len(skipped), pushedOut=moved_basis,
     looseVertices=sum(far), triangles=triangles(gear), subdivided=subdivided, mask=mask_file)
