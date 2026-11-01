# Fit a garment or armour piece to a family body (the Outfit Studio / BodySlide loop, scripted):
#   1. push the garment out of the body by its layer offset,
#   2. copy skin weights from the nearest body surface (top 4, normalised; loose parts such as skirts and capes
#      get their weights smoothed),
#   3. bake one shape key per body shape key through Surface Deform, pushed out again per key, so the garment
#      follows every slider and every people's signature shape,
#   4. work out which body regions it covers (the body hides those faces when it is worn).
# The garment must already be aligned to the body in its rest pose.
#   bun run art:forge fit_gear --body <body.glb> --gear <garment.glb> --out <fitted.glb> --slot top
#     [--family humanoid] [--covers ["chest", "belly"]] [--hides ["cloak"]] [--cover-threshold 0.85] [--smooth 12]
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, contract, done, export, fail, load, regions_uv, reset, skinned_meshes, triangles, warn, with_active  # noqa: E402

import bpy  # noqa: E402
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
for k in keys:
    k.value = 0

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


# 1. Push the basis out of the body
bvh, bverts, btris = body_surface()
coords = [gear.matrix_world @ v.co for v in gear.data.vertices]
moved_basis = push_out(coords, bvh)
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
far = [d > offset + 0.03 for d in distance]
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
for i, w in enumerate(gweights):
    top = sorted(w.items(), key=lambda kv: kv[1], reverse=True)[: c["skeleton"]["maxInfluences"]]
    total = sum(v for _, v in top)
    if total <= 0:
        unweighted += 1
        continue
    for name, weight in top:
        g = groups.get(name) or gear.vertex_groups.new(name=name)
        groups[name] = g
        g.add([i], weight / total, "REPLACE")
if unweighted:
    warn(f"{unweighted} gear vertices got no weights")

# 3. One gear shape key per body shape key, through Surface Deform
baked = []
if keys:
    gear.shape_key_add(name="Basis", from_mix=False)
    sd = gear.modifiers.new("forge_fit", "SURFACE_DEFORM")
    sd.target = body
    with with_active(gear):
        bpy.ops.object.surfacedeform_bind(modifier=sd.name)
    if not sd.is_bound:
        fail("Surface Deform could not bind (the garment may have loose vertices far from the body)")
    for k in keys:
        k.value = 1
        ev = gear.evaluated_get(deps())
        mesh = ev.to_mesh()
        key_coords = [gear.matrix_world @ v.co for v in mesh.vertices]
        ev.to_mesh_clear()
        kbvh, _, _ = body_surface()
        push_out(key_coords, kbvh)
        kb = gear.shape_key_add(name=k.name, from_mix=False)
        inv = gear.matrix_world.inverted()
        for i, co in enumerate(key_coords):
            kb.data[i].co = inv @ co
        k.value = 0
        baked.append(k.name)
    gear.modifiers.remove(sd)

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

gear.name = Path(a["out"]).stem.split(".")[0]
gear.parent = arm
gear.matrix_parent_inverse = Matrix.Identity(4)
mod = gear.modifiers.new("Armature", "ARMATURE")
mod.object = arm
arm.data.pose_position = "POSE"
meta = {"family": c["family"], "kind": "gear", "slot": slot, "layer": layer, "order": c["gearLayers"].get(layer, {}).get("order", 0),
        "offset": offset, "covers": covers, "hides": a.get("hides", []), "shapeKeys": baked, "body": a["body"]}
gear["forge"] = json.dumps(meta)
arm["forge"] = json.dumps({"family": c["family"], "kind": "gear-skeleton"})
for o in list(bpy.data.objects):
    if o not in (gear, arm):
        bpy.data.objects.remove(o)
out = export(a["out"], [arm, gear])
Path(out).with_suffix(".part.json").write_text(json.dumps(meta, indent=2))
done(out=out, slot=slot, layer=layer, covers=covers, coverage=coverage, shapeKeys=baked, pushedOut=moved_basis,
     looseVertices=sum(far), triangles=triangles(gear))
