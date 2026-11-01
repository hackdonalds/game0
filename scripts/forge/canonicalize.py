# Turn any rigged body (Meshy, Mixamo, UE mannequin, Rigify export) into the family contract:
# applied transforms in metres, feet on the ground, canonical bone names, a Root bone, every bone pointing up
# (shared rest rotations), socket bones, a 'Regions' UV layer for body hiding, and at most 4 normalised weights.
#   bun run art:forge canonicalize --in <rigged.glb> --out <body.glb> [--family humanoid] [--people galeborne] [--height 2.05]
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, canonical_map, socket_points, armature_of, contract, done, export, fail, limit_and_normalize, load, regions_uv, reset, skinned_meshes, triangles, warn, with_active  # noqa: E402

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


a = args()
c = contract(a.get("family", "humanoid"))
reset()
objects = load(a["in"])
arm = armature_of(objects)
meshes = skinned_meshes(objects, arm)
if not meshes:
    fail("no mesh is skinned to the armature")

# Strays (Meshy ships a hidden Icosphere) and imported animation go: clips come from the family library
removed = [o.name for o in objects if o is not arm and o not in meshes]
for o in objects:
    if o is not arm and o not in meshes:
        bpy.data.objects.remove(o)
arm.animation_data_clear()
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)

# Apply every transform: unparent, apply, reparent with an identity parent inverse
for m in meshes:
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
for o in [arm, *meshes]:
    with with_active(o):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def bounds():
    pts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


# Optional real height, then feet on the ground and centred on the origin
lo, hi = bounds()
s = a["height"] / (hi.z - lo.z) if "height" in a else 1.0
fit = Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
for o in [arm, *meshes]:
    o.matrix_world = fit @ o.matrix_world
    with with_active(o):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for m in meshes:
    m.parent = arm
    m.matrix_parent_inverse = Matrix.Identity(4)

# Canonical names: aliases for limbs, hierarchy for the spine chain
mapping = canonical_map(arm, c)
bones = arm.data.bones
chain_prefixes = tuple(re.sub(r"_\d+.*", "_", v.split("..")[0]) for v in c["skeleton"]["chains"].values())
weighted = {g.name for m in meshes for g in m.vertex_groups
            if any(vg.group == g.index and vg.weight > 0 for v in m.data.vertices for vg in v.groups)}


def mapped_ancestor(bone):
    p = bone.parent
    while p and p.name not in mapping and not p.name.startswith(chain_prefixes):
        p = p.parent
    return p


# Unmapped bones: merge their weights into the nearest kept ancestor, then delete them
drop = [b.name for b in bones if b.name not in mapping and not b.name.startswith(chain_prefixes)]
for name in drop:
    parent = mapped_ancestor(bones[name])
    if name in weighted:
        if not parent:
            fail(f"weighted bone {name} has no kept ancestor")
        for m in meshes:
            src, dst = m.vertex_groups.get(name), m.vertex_groups.get(parent.name) or m.vertex_groups.new(name=parent.name)
            for v in m.data.vertices:
                for g in v.groups:
                    if src and g.group == src.index and g.weight > 0:
                        dst.add([v.index], g.weight, "ADD")
        warn(f"merged weights of {name} into {parent.name}")
for m in meshes:
    for name in drop:
        if name in m.vertex_groups:
            m.vertex_groups.remove(m.vertex_groups[name])

with with_active(arm):
    bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for name in drop:
    for child in eb[name].children:
        child.use_connect = False
        child.parent = eb[name].parent
    eb.remove(eb[name])
# Two-phase rename avoids collisions such as Spine02 -> Spine while Spine still exists
for i, (old, _) in enumerate(mapping.items()):
    eb[old].name = f"__forge_{i}"
bpy.ops.object.mode_set(mode="OBJECT")
for m in meshes:
    for i, (old, _) in enumerate(mapping.items()):
        if old in m.vertex_groups:
            m.vertex_groups[old].name = f"__forge_{i}"
with with_active(arm):
    bpy.ops.object.mode_set(mode="EDIT")
for i, (_, new) in enumerate(mapping.items()):
    eb[f"__forge_{i}"].name = new
bpy.ops.object.mode_set(mode="OBJECT")
for m in meshes:
    for i, (_, new) in enumerate(mapping.items()):
        if f"__forge_{i}" in m.vertex_groups:
            m.vertex_groups[f"__forge_{i}"].name = new

missing = [n for n in c["skeleton"]["core"] if n not in arm.data.bones]
if missing:
    fail("core bones missing after mapping", missing=missing, mapping=mapping)

# Root bone, bones pointing up with roll 0, and sockets
sockets = {}
points = socket_points(arm, meshes, c)

with with_active(arm):
    bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for b in eb:
    b.use_connect = False
for b in eb:
    length = max(b.length, 0.03)
    b.tail = b.head + Vector((0, 0, length))
    b.roll = 0
root = eb.get("Root") or eb.new("Root")
root.head, root.tail, root.use_deform, root.parent = Vector((0, 0, 0)), Vector((0, 0, 0.1)), False, None
eb["Hips"].parent = root
for sk in c["sockets"]:
    bone = next(n for n in sk["bone"].split("|") if n in eb)
    s_b = eb.new(sk["name"])
    s_b.head = points[sk["name"]]
    s_b.tail = s_b.head + Vector((0, 0, 0.05))
    s_b.parent, s_b.use_deform = eb[bone], False
    sockets[sk["name"]] = {"bone": bone, "at": [round(x, 4) for x in s_b.head]}
bpy.ops.object.mode_set(mode="OBJECT")

# Regions UV: the region of each vertex's heaviest bone
regions = c["regions"]
region_of = {}
for b in arm.data.bones:
    r, p = None, b
    while p and r is None:
        r = c["boneRegion"].get(p.name) or next((c["chainRegion"][k] for k, v in c["skeleton"]["chains"].items()
                                                  if p.name.startswith(v.split("..")[0].rsplit("_", 1)[0] + "_")), None)
        p = p.parent
    region_of[b.name] = r or "hips"
deform = {b.name for b in arm.data.bones if b.use_deform}
counts = {}
for m in meshes:
    limited = limit_and_normalize(m, c["skeleton"]["maxInfluences"], deform)
    if limited:
        warn(f"{m.name}: trimmed {limited} vertices to {c['skeleton']['maxInfluences']} influences")
    names = {g.index: g.name for g in m.vertex_groups}
    vert_region = []
    for v in m.data.vertices:
        best = max((g for g in v.groups if names[g.group] in deform), key=lambda g: g.weight, default=None)
        vert_region.append(regions.index(region_of.get(names.get(best.group) if best else None, "hips")))
    uv = regions_uv(m) or m.data.uv_layers.new(name="Regions")
    m.data.uv_layers[0].active_render = True
    for loop in m.data.loops:
        uv.data[loop.index].uv = ((vert_region[loop.vertex_index] + 0.5) / 32, 0.5)
    for r in vert_region:
        counts[regions[r]] = counts.get(regions[r], 0) + 1

meta = {"family": c["family"], "kind": "body", "people": a.get("people"), "source": a["in"]}
arm["forge"] = json.dumps(meta)
for m in meshes:
    m["forge"] = json.dumps(meta)
lo, hi = bounds()
out = export(a["out"], [arm, *meshes])
done(out=out, height=round(hi.z - lo.z, 3), renamed=mapping, droppedBones=drop, removedObjects=removed, sockets=sockets,
     triangles=sum(triangles(m) for m in meshes), regionVertices=counts)
