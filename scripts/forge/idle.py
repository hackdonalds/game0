# Add a procedural looping idle (breathing, weight shift, slight head and arm drift) to a family clip library.
# A stand-in until a real idle comes from a CC0 library or Meshy; it follows the same rules as retargeted clips
# (rotations only, plus Hips translation).
#   bun run art:forge idle --in <anims.glb> --out <anims.glb> [--name idle] [--seconds 4] [--drop ["idle"]]
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, done, export, linear_keys, load, reset  # noqa: E402

import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

a = args()
reset()
arm = armature_of(load(a["in"]))
name = a.get("name", "idle")
for act in list(bpy.data.actions):
    if act.name in a.get("drop", [name]):
        bpy.data.actions.remove(act)
fps = 30
frames = int(a.get("seconds", 4) * fps)
# bone: (axis amplitudes in degrees, cycles per loop, phase)
motion = {
    "Spine": ((1.2, 0, 0.6), 1, 0.0), "Chest": ((1.6, 0, 0), 2, 0.1), "UpperChest": ((1.0, 0, 0), 2, 0.15),
    "Neck": ((-0.8, 1.5, 0), 1, 0.4), "Head": ((-1.0, 2.5, 0.8), 1, 0.45),
    "LeftShoulder": ((0, 0, 1.2), 2, 0.2), "RightShoulder": ((0, 0, -1.2), 2, 0.2),
    "LeftUpperArm": ((2.0, 0, 1.5), 1, 0.3), "RightUpperArm": ((2.0, 0, -1.5), 1, 0.8),
    "LeftLowerArm": ((3.0, 0, 0), 1, 0.35), "RightLowerArm": ((3.0, 0, 0), 1, 0.85),
    "Hips": ((0, 0, 1.0), 1, 0.0), "LeftUpperLeg": ((0, 0, -1.0), 1, 0.0), "RightUpperLeg": ((0, 0, -1.0), 1, 0.0),
}
act = bpy.data.actions.new(name)
act.use_fake_user = True
arm.animation_data_create()
arm.animation_data.action = act
for f in range(frames + 1):
    t = f / frames
    for bone, (amp, cycles, phase) in motion.items():
        pb = arm.pose.bones.get(bone)
        if not pb:
            continue
        s = math.sin(2 * math.pi * (cycles * t + phase))
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Euler([math.radians(x * s) for x in amp]).to_quaternion()
        pb.keyframe_insert("rotation_quaternion", frame=f)
    hips = arm.pose.bones["Hips"]
    hips.location = Vector((0.012 * math.sin(2 * math.pi * t), 0, 0.004 * math.sin(4 * math.pi * t)))
    hips.keyframe_insert("location", frame=f)
for clip in bpy.data.actions:
    linear_keys(clip)
arm.animation_data.action = None
for track in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(track)
for clip in bpy.data.actions:
    track = arm.animation_data.nla_tracks.new()
    track.name = clip.name
    track.strips.new(clip.name, 0, clip)
out = export(a.get("out", a["in"]), [arm], animations=True)
done(out=out, clips=[x.name for x in bpy.data.actions], frames=frames)
