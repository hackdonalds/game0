# Wrap the family base mesh onto a people's (or species') sculpt, so every people shares one topology.
#   1. skeleton pre-fit: each base vertex follows its bones from the base joints to the target joints
#      (linear blend skinning with per-bone affine maps that align and stretch each limb),
#   2. shrinkwrap onto the target surface, with Corrective Smooth keeping the base's edge flow,
#   3. store the result as shape key `people_<id>` on the base, and the target's joint positions as the
#      people's rest skeleton (<out>.rest.json). Both go into the people's body build.
# Both inputs must be canonical (run canonicalize first). Faces need landmarks for close fits; this step gets
# proportions and silhouette, and the fit report says how far the result is from the target.
#   bun run art:forge wrap --base <base.body.glb> --target <people.body.glb> --out <base+key.glb> --key people_galeborne
#     [--smooth 12] [--family humanoid]
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, contract, done, export, load, reset, skinned_meshes, with_active  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
reset()
base_objects = load(a["base"])
barm = armature_of(base_objects)
base = max(skinned_meshes(base_objects, barm), key=lambda m: len(m.data.vertices))
target_objects = load(a["target"])
tarm = armature_of(target_objects)
targets = skinned_meshes(target_objects, tarm)
for arm in (barm, tarm):
    arm.data.pose_position = "REST"


def heads(arm):
    return {b.name: (arm.matrix_world @ b.head_local) for b in arm.data.bones}


bh, th = heads(barm), heads(tarm)
shared = set(bh) & set(th)


def limb_child(name):
    return next((n for n in c["skeleton"]["limbChild"].get(name, "").split("|") if n in shared), None)


def affine(name) -> Matrix:
    """Map base bone space to target: move the joint, turn the limb, stretch it along its length."""
    if name not in shared:
        return Matrix.Identity(4)
    child = limb_child(name)
    if not child:
        return Matrix.Translation(th[name] - bh[name])
    db, dt = bh[child] - bh[name], th[child] - th[name]
    r = dt.length / max(db.length, 1e-6)
    d = db.normalized()
    stretch = Matrix.Identity(3) + (r - 1) * Matrix([[d.x * d.x, d.x * d.y, d.x * d.z], [d.y * d.x, d.y * d.y, d.y * d.z], [d.z * d.x, d.z * d.y, d.z * d.z]])
    turn = db.rotation_difference(dt).to_matrix()
    m = (turn @ stretch).to_4x4()
    return Matrix.Translation(th[name]) @ m @ Matrix.Translation(-bh[name])


# 1. Skeleton pre-fit with linear blend skinning
maps = {g.index: np.array(affine(g.name)) for g in base.vertex_groups}
mw = base.matrix_world
coords = np.array([list(mw @ v.co) + [1.0] for v in base.data.vertices])
fitted = np.zeros((len(coords), 3))
for i, v in enumerate(base.data.vertices):
    ws = [(g.group, g.weight) for g in v.groups if g.weight > 0 and g.group in maps]
    total = sum(w for _, w in ws)
    if not total:
        fitted[i] = coords[i, :3]
        continue
    fitted[i] = sum(w * (maps[gi] @ coords[i]) for gi, w in ws)[:3] / total

# 2. Shrinkwrap onto the target, smoothed against the base's own shape
target = targets[0]
if len(targets) > 1:
    with bpy.context.temp_override(active_object=target, object=target, selected_objects=targets, selected_editable_objects=targets):
        bpy.ops.object.join()
for m in target.modifiers:
    m.show_viewport = False
work = bpy.data.objects.new("wrap", base.data.copy())
bpy.context.scene.collection.objects.link(work)
work.shape_key_clear() if work.data.shape_keys else None
inv = work.matrix_world.inverted()
for v, co in zip(work.data.vertices, fitted):
    v.co = inv @ Vector(co)
sw = work.modifiers.new("shrink", "SHRINKWRAP")
sw.target, sw.wrap_method, sw.wrap_mode = target, "NEAREST_SURFACEPOINT", "ON_SURFACE"
cs = work.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
cs.iterations, cs.factor, cs.rest_source, cs.smooth_type = int(a.get("smooth", 12)), 0.5, "ORCO", "LENGTH_WEIGHTED"
deps = bpy.context.evaluated_depsgraph_get()
ev = work.evaluated_get(deps)
mesh = ev.to_mesh()
result = [work.matrix_world @ v.co for v in mesh.vertices]
ev.to_mesh_clear()

# Fit report: distance from the target's surface to the wrapped surface, both ways
mesh_t = target.evaluated_get(deps).to_mesh()
mesh_t.calc_loop_triangles()
tverts = [target.matrix_world @ v.co for v in mesh_t.vertices]
tbvh = BVHTree.FromPolygons(tverts, [tuple(t.vertices) for t in mesh_t.loop_triangles])
base.data.calc_loop_triangles()
wbvh = BVHTree.FromPolygons(result, [tuple(t.vertices) for t in base.data.loop_triangles])
to_target = np.array([tbvh.find_nearest(p)[3] for p in result])
to_wrap = np.array([wbvh.find_nearest(p)[3] for p in tverts[:: max(1, len(tverts) // 20000)]])

# 3. Shape key on the base, rest skeleton sidecar
if not base.data.shape_keys:
    base.shape_key_add(name="Basis", from_mix=False)
kb = base.data.shape_keys.key_blocks.get(a["key"]) or base.shape_key_add(name=a["key"], from_mix=False)
binv = base.matrix_world.inverted()
for i, co in enumerate(result):
    kb.data[i].co = binv @ co
for o in list(bpy.data.objects):
    if o not in (base, barm):
        bpy.data.objects.remove(o)
meta = json.loads(base.get("forge", "{}"))
meta.setdefault("signatures", [])
if a["key"] not in meta["signatures"]:
    meta["signatures"].append(a["key"])
base["forge"] = json.dumps(meta)
out = export(a["out"], [barm, base])
rest = {name: [round(x, 5) for x in th[name]] for name in sorted(shared)}
Path(out).with_suffix(".rest.json").write_text(json.dumps({"key": a["key"], "target": a["target"], "heads": rest}, indent=2))
done(out=out, key=a["key"], rest=str(Path(out).with_suffix(".rest.json")),
     fit={"meanToTarget": round(float(to_target.mean()), 4), "p95ToTarget": round(float(np.percentile(to_target, 95)), 4),
          "meanTargetToWrap": round(float(to_wrap.mean()), 4), "p95TargetToWrap": round(float(np.percentile(to_wrap, 95)), 4)})
