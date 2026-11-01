# Check a fitted piece on a body through every clip: how much skin pokes through the cloth where the body is not
# hidden by the piece's mask. Poking = a ray from a body vertex inward hits the piece (the cloth is under the skin).
#   bun run art:forge check_fit --body <people.body.glb> --gear <fitted.glb> --anims <anims.glb>
#     [--keys {"body_gender_pos": 0.7}] [--samples 8] [--limit-mm 5] [--extremes true]
# --extremes: check the people's defaults, its widest allowed body and its narrowest allowed body (every body slider
# at the end of the people's clamp range) instead of one --keys set.
# Fails when any sampled frame shows more than --limit-mm of visible poke-through. A failure at a few frames of one
# clip, on hands or shins, is usually the clip on a wider body: give the people a pose offset in the contract
# (e.g. "pose": {"armSpread": 6}); the check, renders and runtime all apply it.
# Skin-layer parts (hair, crests, feathers) grow out of the skin, so their roots are under it by design: they are
# reported but never fail.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import apply_pose_offsets, args, armature_of, contract, done, load, path, pose_offsets, regions_uv, reset, skinned_meshes  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
reset()
body_objects = load(a["body"])
arm = armature_of(body_objects)
body = max(skinned_meshes(body_objects, arm), key=lambda m: len(m.data.vertices))
gear_objects = load(a["gear"])
garm = next(o for o in gear_objects if o.type == "ARMATURE")
gear = next(o for o in gear_objects if o.type == "MESH")
for md in gear.modifiers:
    if md.type == "ARMATURE":
        md.object = arm
bpy.data.objects.remove(garm)
before = set(bpy.data.actions)
anim_objects = load(a["anims"])
clips = [x for x in bpy.data.actions if x not in before]
for o in anim_objects:
    bpy.data.objects.remove(o)

meta = json.loads(body.get("forge", "{}"))
keys = {**({meta["signature"]: 1} if meta.get("signature") else {}), **a.get("keys", {})}
offsets = pose_offsets(c, meta.get("people"), keys)
for m in (body, gear):
    for kb in (m.data.shape_keys.key_blocks[1:] if m.data.shape_keys else []):
        kb.value = keys.get(kb.name, 0)

# Body vertices hidden by the piece's mask (all their UV corners masked), as the runtime discards them
hidden = set()
gmeta = json.loads(gear.get("forge", "{}"))
mask_file = Path(path(a["gear"])).with_suffix(".mask.png")
if gmeta.get("mask") and mask_file.exists():
    img = bpy.data.images.load(str(mask_file))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, -1)[..., 0]
    uv = body.data.uv_layers[0].data
    visible = {}
    for loop in body.data.loops:
        u, v = uv[loop.index].uv
        visible[loop.vertex_index] = visible.get(loop.vertex_index, False) or px[min(h - 1, int(v * h)), min(w - 1, int(u * w))] < 0.5
    hidden = {i for i, vis in visible.items() if not vis}
ruv = regions_uv(body).data
region = {}
for loop in body.data.loops:
    region[loop.vertex_index] = c["regions"][int(ruv[loop.index].uv[0] * 32)]


def evaluated(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = o.matrix_world
    out = ([mw @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles], [(mw.to_3x3() @ v.normal).normalized() for v in me.vertices])
    ev.to_mesh_clear()
    return out


def measure():
    gv, gt, _ = evaluated(gear)
    bv, bt, bn = evaluated(body)
    g = BVHTree.FromPolygons(gv, gt)
    b = BVHTree.FromPolygons(bv, bt)
    depths, where = [], {}
    for i, (p, n) in enumerate(zip(bv, bn)):
        if i in hidden:
            continue
        hit, _, _, depth = g.ray_cast(p, -n, 0.05)
        if hit is None:
            continue
        # Only if the cloth is met before the ray leaves the body (a thin hand next to cloth is not poking)
        exit_hit, _, _, exit_d = b.ray_cast(p - n * 1e-4, -n, 0.05)
        if exit_hit is not None and exit_d < depth:
            continue
        depths.append(depth)
        where[region[i]] = where.get(region[i], 0) + 1
    return round(max(depths, default=0) * 1000, 1), len(depths), where


limit = a.get("limit-mm", 5)


def set_keys(values: dict):
    global offsets
    for m in (body, gear):
        for kb in (m.data.shape_keys.key_blocks[1:] if m.data.shape_keys else []):
            kb.value = values.get(kb.name, 0)
    offsets = pose_offsets(c, meta.get("people"), values)


def run_checks() -> dict:
    report = {}
    arm.animation_data_create()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    apply_pose_offsets(arm, offsets)
    report["rest"] = dict(zip(("maxMm", "vertices", "regions"), measure()))
    for clip in clips:
        arm.animation_data.action = clip
        if clip.slots:
            arm.animation_data.action_slot = clip.slots[0]
        start, end = clip.frame_range
        worst = {"maxMm": 0, "frame": None, "vertices": 0, "regions": {}}
        for f in np.linspace(start, end, int(a.get("samples", 8))):
            bpy.context.scene.frame_set(int(round(f)))
            apply_pose_offsets(arm, offsets)
            mm, n, where = measure()
            if mm > worst["maxMm"]:
                worst = {"maxMm": mm, "frame": int(round(f)), "vertices": n, "regions": where}
        report[clip.name] = worst
    return report


def slider_keys(values: dict) -> dict:
    out = {}
    for name, v in values.items():
        if v:
            out[f"{name}_{'pos' if v > 0 else 'neg'}"] = abs(v)
    return out


people = c.get("peoples", {}).get(meta.get("people") or "", {})
signature = {meta["signature"]: 1} if meta.get("signature") else {}
if a.get("extremes"):
    body_sliders = [n for n in c["sliders"]["morph"]["body"] if n != "body_age"]
    clamp = lambda n: people.get("clamp", {}).get(n, [-1, 1])  # noqa: E731
    defaults = {n: v for n, v in people.get("defaults", {}).items() if n in c["sliders"]["morph"]["body"] + c["sliders"]["morph"]["face"]}
    cases = {
        "defaults": {**signature, **slider_keys(defaults)},
        "widest": {**signature, **slider_keys({n: clamp(n)[1] for n in body_sliders})},
        "narrowest": {**signature, **slider_keys({n: clamp(n)[0] for n in body_sliders})},
    }
else:
    cases = {"keys": keys}
report = {}
for case, values in cases.items():
    set_keys(values)
    for name, r in run_checks().items():
        report[f"{case}/{name}" if len(cases) > 1 else name] = r
rooted = gmeta.get("layer") == "skin"
failing = {} if rooted else {k: v for k, v in report.items() if v["maxMm"] > limit}
done(passed=not failing, limitMm=limit, rootedPart=rooted, poseOffsets={k: round(v[1], 4) for k, v in offsets.items()},
     hiddenVertices=len(hidden), report=report, failing=sorted(failing))
