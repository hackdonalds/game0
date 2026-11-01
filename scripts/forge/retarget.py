# Bake clips from any humanoid rig (Meshy, Mixamo, UE mannequin, Quaternius UAL) onto the family skeleton.
# Each target bone gets the source bone's rotation from rest, corrected so limbs point where the source limbs
# point (so A-pose and T-pose sources both work). Only rotations are keyed, plus Hips translation scaled by
# hip height, so the library plays on every body of the family whatever its proportions.
#   bun run art:forge retarget --source <clips.glb or ["a.glb", "b.glb"]> --target <canonical body.glb> --out <anims.glb>
#     [--clips ["Walk", "Idle"]] [--rename {"clip0": "idle"}] [--family humanoid] [--fps 30]
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, canonical_map, contract, done, export, fail, linear_keys, load, reset, warn  # noqa: E402

import bpy  # noqa: E402
from mathutils import Matrix, Quaternion  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
reset()
scene = bpy.context.scene
scene.render.fps = int(a.get("fps", 30))

tgt_objects = load(a["target"])
tgt = armature_of(tgt_objects)
for o in tgt_objects:
    if o is not tgt:
        bpy.data.objects.remove(o)
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)
tgt.animation_data_clear()

written = []
clamped: dict[str, int] = {}
sources = a["source"] if isinstance(a["source"], list) else [a["source"]]
for source in sources:
    before = set(bpy.data.actions)
    src_objects = load(source)
    src = armature_of(src_objects)
    for o in src_objects:
        if o is not src:
            bpy.data.objects.remove(o)
    imported = [act for act in bpy.data.actions if act not in before]
    clips = [act for act in imported if not a.get("clips") or any(k.lower() in act.name.lower() for k in a["clips"])]
    if not clips:
        fail(f"no clips found in {source}", actions=[x.name for x in imported])

    to_canon = canonical_map(src, c)
    from_canon = {v: k for k, v in to_canon.items()}
    tw = tgt.matrix_world.copy()
    sw = src.matrix_world.copy()


    def rest_world(arm_obj, mw, name):
        return mw @ arm_obj.data.bones[name].matrix_local


    def limb_child(name, names):
        return next((n for n in c["skeleton"]["limbChild"].get(name, "").split("|") if n and n in names), None)


    tbones = tgt.data.bones
    order = sorted((b for b in tbones), key=lambda b: len(b.parent_recursive))
    mapped = [b.name for b in order if b.name in from_canon]
    unmatched = sorted(set(from_canon) - {b.name for b in tbones})
    if unmatched:
        warn(f"source bones with no target: {unmatched}")

    # Per-bone rest correction: rotate the target's rest limb direction onto the source's rest limb direction
    correction = {}
    for name in mapped:
        child = limb_child(name, set(from_canon) & {b.name for b in tbones})
        if not child or name == "Hips":
            correction[name] = Quaternion()
            continue
        d_t = rest_world(tgt, tw, child).translation - rest_world(tgt, tw, name).translation
        d_s = rest_world(src, sw, from_canon[child]).translation - rest_world(src, sw, from_canon[name]).translation
        correction[name] = d_t.rotation_difference(d_s) if d_t.length > 1e-6 and d_s.length > 1e-6 else Quaternion()

    hip_ratio = rest_world(tgt, tw, "Hips").translation.z / max(rest_world(src, sw, from_canon["Hips"]).translation.z, 1e-6)
    rest_rel = {b.name: (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy() for b in tbones}
    tgt.animation_data_create()
    src.animation_data_create()
    for act in clips:
        src.animation_data.action = act
        if hasattr(src.animation_data, "action_slot") and act.slots:
            src.animation_data.action_slot = act.slots[0]
        start, end = (int(round(f)) for f in act.frame_range)
        parts = act.name.split("|")
        short = parts[1] if len(parts) > 2 else parts[-1]
        name = a.get("rename", {}).get(act.name) or a.get("rename", {}).get(short, short)
        out_act = bpy.data.actions.new(name)
        out_act.use_fake_user = True
        tgt.animation_data.action = out_act
        for pb in tgt.pose.bones:
            pb.rotation_mode = "QUATERNION"
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            world = {}
            for b in order:
                parent_w = world[b.parent.name] if b.parent else tw
                rest_w = parent_w @ rest_rel[b.name]
                if b.name in from_canon:
                    s_pb = src.pose.bones[from_canon[b.name]]
                    rs = (sw @ s_pb.matrix).to_3x3().normalized().to_quaternion()
                    rs_rest = rest_world(src, sw, s_pb.name).to_3x3().normalized().to_quaternion()
                    rt_rest = rest_world(tgt, tw, b.name).to_3x3().normalized().to_quaternion()
                    rot = rs @ rs_rest.inverted() @ correction[b.name] @ rt_rest
                    loc = rest_w.translation
                    if b.name == "Hips":
                        loc = (sw @ s_pb.matrix).translation * hip_ratio
                    limit = c["skeleton"].get("limits", {}).get(b.name)
                    child = limb_child(b.name, {x.name for x in tbones})
                    if isinstance(limit, (int, float)) and child and b.parent:
                        # Joint limit: clamp the bend between the parent limb and this limb
                        parent_dir = loc - world[b.parent.name].translation
                        limb_dir = (Matrix.LocRotScale(loc, rot, None) @ rest_rel[child]).translation - loc
                        bend = math.degrees(parent_dir.angle(limb_dir)) if parent_dir.length and limb_dir.length else 0
                        if bend > limit:
                            axis = parent_dir.cross(limb_dir)
                            if axis.length > 1e-9:
                                rot = Quaternion(axis.normalized(), -math.radians(bend - limit)) @ rot
                                clamped[b.name] = clamped.get(b.name, 0) + 1
                    world[b.name] = Matrix.LocRotScale(loc, rot, None)
                else:
                    world[b.name] = rest_w
                if b.name not in from_canon:
                    continue
                local = rest_w.inverted() @ world[b.name]
                pb = tgt.pose.bones[b.name]
                pb.rotation_quaternion = local.to_quaternion()
                pb.keyframe_insert("rotation_quaternion", frame=frame - start)
                if b.name == "Hips":
                    pb.location = local.translation
                    pb.keyframe_insert("location", frame=frame - start)
        linear_keys(out_act)
        written.append({"clip": name, "frames": end - start + 1})

    for act in imported:
        bpy.data.actions.remove(act)
    bpy.data.objects.remove(src)
    tgt.animation_data.action = None


tgt.animation_data.action = None
meta = {"family": c["family"], "kind": "anims", "hipHeight": round((tgt.matrix_world @ tgt.data.bones["Hips"].matrix_local).translation.z, 4), "sources": sources}
tgt["forge"] = json.dumps(meta)
for o in list(bpy.data.objects):
    if o is not tgt:
        bpy.data.objects.remove(o)
# Every clip goes on its own NLA track so the exporter writes one glTF animation per clip
for act in bpy.data.actions:
    if act.name in {w["clip"] for w in written}:
        track = tgt.animation_data.nla_tracks.new()
        track.name = act.name
        track.strips.new(act.name, 0, act)
for act in list(bpy.data.actions):
    if act.name not in {w["clip"] for w in written}:
        bpy.data.actions.remove(act)
out = export(a["out"], [tgt], animations=True)
done(out=out, clips=written, hipHeight=meta["hipHeight"], jointLimitFrames=clamped)
