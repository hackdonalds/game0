# Retarget clips from Quaternius' Universal Animation Library (CC0) onto a rig made by autorig.py.
# Usage: blender -b --factory-startup -P scripts/rig/retarget.py -- rig.blend out.glb [out.blend]
# Each target bone copies its source bone's world-space rotation change. The source's T-pose
# rest is first turned onto the target's A-pose rest, so the arms don't come out 45 degrees off.
# Forearms, hands and fingers are matched on palm facing as well as direction, so fists curl inward.
# Hip motion is scaled by the hip-height ratio so short-legged bodies don't float or sink.
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

LIBS = Path(__file__).resolve().parents[2] / "art/references/anims/quaternius"
FPS = 30

BONE_MAP = {"hips": "pelvis", "spine": "spine_01", "chest": "spine_03", "neck": "neck_01", "head": "Head"}
for s, q in (("L", "l"), ("R", "r")):
    BONE_MAP.update({
        f"clavicle.{s}": f"clavicle_{q}", f"upper_arm.{s}": f"upperarm_{q}", f"forearm.{s}": f"lowerarm_{q}",
        f"hand.{s}": f"hand_{q}", f"thigh.{s}": f"thigh_{q}", f"shin.{s}": f"calf_{q}",
        f"foot.{s}": f"foot_{q}", f"toe.{s}": f"ball_{q}",
    })
    for f in ("thumb", "index", "middle", "ring", "pinky"):
        BONE_MAP.update({f"{f}_0{i}.{s}": f"{f}_0{i}_{q}" for i in (1, 2, 3)})

# name: (library file, source clip, source ground speed in m/s measured from the root-motion export)
CLIPS = {
    "Idle": ("UAL1_Standard.glb", "Idle_Loop", 0),
    "Walk": ("UAL1_Standard.glb", "Walk_Loop", 0.975),
    "Run": ("UAL1_Standard.glb", "Jog_Fwd_Loop", 5.357),
    "Sprint": ("UAL1_Standard.glb", "Sprint_Loop", 8.25),
    "JumpStart": ("UAL1_Standard.glb", "Jump_Start", 0),
    "JumpLoop": ("UAL1_Standard.glb", "Jump_Loop", 0),
    "JumpLand": ("UAL1_Standard.glb", "Jump_Land", 0),
    "HitChest": ("UAL1_Standard.glb", "Hit_Chest", 0),
    "HitHead": ("UAL1_Standard.glb", "Hit_Head", 0),
    "Punch": ("UAL1_Standard.glb", "Punch_Cross", 0),
    "Hook": ("UAL2_Standard.glb", "Melee_Hook", 0),
    "HitKnockback": ("UAL2_Standard.glb", "Hit_Knockback", 0),
    "CarryWalk": ("UAL2_Standard.glb", "Walk_Carry_Loop", 0.65),
}
# Standing with a load: Idle legs and spine, arms held as in the first frame of CarryWalk
CARRY_ARMS = [n for n in BONE_MAP if n.split(".")[0] in ("clavicle", "upper_arm", "forearm", "hand")
              or n.split("_")[0] in ("thumb", "index", "middle", "ring", "pinky")]


def frame(direction, across):
    """Orthonormal basis with y along the bone and x across the palm."""
    y = direction.normalized()
    x = (across - y * across.dot(y)).normalized()
    return Matrix((x, y, x.cross(y))).transposed()


class Target:
    def __init__(self, obj):
        self.obj = obj
        bones = obj.data.bones
        self.order = [b.name for b in bones if b.parent is None]
        i = 0
        while i < len(self.order):  # parents before children
            self.order += [c.name for c in bones[self.order[i]].children]
            i += 1
        self.rest = {n: bones[n].matrix_local.copy() for n in self.order}
        self.parent = {n: bones[n].parent.name if bones[n].parent else None for n in self.order}
        self.hip_height = bones["thigh.L"].head_local.z


class Source:
    def __init__(self, path, target):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        self.objects = set(bpy.data.objects) - before
        self.obj = next(o for o in self.objects if o.type == "ARMATURE")
        self.obj.animation_data_create()
        mw = self.obj.matrix_world
        bones = self.obj.data.bones
        self.rest = {s: (mw @ bones[s].matrix_local) for s in BONE_MAP.values()}
        self.ratio = target.hip_height / (mw @ bones["thigh_l"].head_local).z
        # Rotation that turns each source rest bone onto the target rest bone
        self.align = {}
        for t, s in BONE_MAP.items():
            src_dir = self.rest[s].to_3x3() @ Vector((0, 1, 0))
            tgt_dir = target.rest[t].to_3x3() @ Vector((0, 1, 0))
            side = t[-1]
            if t.startswith(("forearm", "hand")) or t.split("_")[0] in ("thumb", "index", "middle", "ring", "pinky"):
                # Across the palm, index knuckle to pinky knuckle
                q = side.lower()
                src_across = (mw @ bones[f"index_01_{q}"].head_local) - (mw @ bones[f"pinky_01_{q}"].head_local)
                tgt_across = target.rest[f"index_01.{side}"].translation - target.rest[f"pinky_01.{side}"].translation
                self.align[t] = (frame(tgt_dir, tgt_across) @ frame(src_dir, src_across).transposed()).to_quaternion()
            else:
                self.align[t] = src_dir.rotation_difference(tgt_dir)

    def remove(self):
        for o in self.objects:
            bpy.data.objects.remove(o, do_unlink=True)

    def frames(self, clip):
        action = bpy.data.actions[clip]
        self.obj.animation_data.action = action
        f0, f1 = (int(round(f)) for f in action.frame_range)
        for f in range(f0, f1 + 1):
            bpy.context.scene.frame_set(f)
            mw = self.obj.matrix_world
            yield {s: mw @ self.obj.pose.bones[s].matrix for s in BONE_MAP.values()}


def solve(target, source, pose):
    """Local pose (basis) matrices for every target bone from one source frame."""
    world, basis = {}, {}
    for name in target.order:
        rest, parent = target.rest[name], target.parent[name]
        offset = target.rest[parent].inverted() @ rest if parent else rest
        chain = world[parent] @ offset if parent else offset
        if name in BONE_MAP:
            s = BONE_MAP[name]
            delta = pose[s].to_quaternion() @ source.rest[s].to_quaternion().inverted() @ source.align[name].inverted()
            rot = (delta @ rest.to_quaternion()).to_matrix().to_4x4()
            loc = chain.translation
            if name == "hips":
                loc = rest.translation + (pose[s].translation - source.rest[s].translation) * source.ratio
            world[name] = Matrix.Translation(loc) @ rot
        else:
            world[name] = chain
        basis[name] = offset.inverted() @ (world[parent].inverted() if parent else Matrix()) @ world[name]
    return basis


def key(target, frame, basis, last):
    for name, m in basis.items():
        pb = target.obj.pose.bones[name]
        q = m.to_quaternion()
        if name in last and last[name].dot(q) < 0:
            q.negate()  # keep quaternions continuous so interpolation doesn't spin the long way
        last[name] = q
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if name == "hips":
            pb.location = m.translation
            pb.keyframe_insert("location", frame=frame)


def bake(target, name, frames):
    ad = target.obj.animation_data_create()
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    ad.action = action
    last = {}
    for f, basis in enumerate(frames):
        key(target, f, basis, last)
    track = ad.nla_tracks.new()
    track.name = name
    track.strips.new(name, 0, action)
    ad.action = None
    return len(frames) - 1


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    bpy.context.scene.render.fps = FPS  # glTF import converts clip times using the scene rate
    target = Target(bpy.data.objects["Rig"])
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

    meta, sampled = {}, {}
    for lib in dict.fromkeys(v[0] for v in CLIPS.values()):
        source = Source(LIBS / lib, target)
        for name, (l, clip, speed) in CLIPS.items():
            if l != lib:
                continue
            sampled[name] = [solve(target, source, p) for p in source.frames(clip)]
            meta[name] = {"speed": round(speed * source.ratio, 3), "source": clip}
        ratio = source.ratio
        source.remove()
    for a in list(bpy.data.actions):  # the libraries' own clips
        bpy.data.actions.remove(a)

    arms = sampled["CarryWalk"][0]
    sampled["CarryIdle"] = [{**b, **{n: arms[n] for n in CARRY_ARMS}} for b in sampled["Idle"]]
    meta["CarryIdle"] = {"speed": 0, "source": "Idle_Loop + Walk_Carry_Loop arms"}
    for name, frames in sampled.items():
        meta[name]["frames"] = bake(target, name, frames)

    out = Path(argv[1]).resolve()
    if len(argv) > 2:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(argv[2]).resolve()))
    bpy.ops.export_scene.gltf(
        filepath=str(out), export_format="GLB", export_animation_mode="ACTIONS",
        export_force_sampling=True, export_optimize_animation_size=True, export_def_bones=False,
    )
    out.with_suffix(".clips.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("RETARGETED", f"hip ratio {ratio:.2f}", json.dumps(meta))


main()
