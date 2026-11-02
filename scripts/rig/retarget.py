# Retarget engine for the biped family, plus the character step of `bun run art:rig`.
# Usage: blender -b --factory-startup -P scripts/rig/retarget.py -- rig.blend out.glb [out.blend] [--sets a,b] [--clips id,id]
#   Plays the library's canonical clip sets (art/anims/biped/clips/*.glb) on a rig made by autorig.py.
#
# Every target bone copies its source bone's world-space rotation change. Limb rests are first turned
# onto the target's (bone direction), so a T-pose library drives an A-pose body; the spine, head and
# feet stand the same way in every rest pose, so they copy the change as is. Hip motion is scaled by
# leg length so short-legged bodies don't float or sink. Library sources are described by ADAPTERS;
# scripts/rig/library.py uses this module to build the canonical sets from them.
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

FPS = 30
ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "art/anims/biped"
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
LOWER = ("hips", "thigh", "shin", "foot", "toe")  # bone prefixes driven by the legs in composite clips


def sides(table):
    """Expand {"bone.{S}": "src_{s}"} templates for both sides."""
    out = {}
    for k, v in table.items():
        if "{S}" in k:
            for S, s, side, Side in (("L", "l", "left", "Left"), ("R", "r", "right", "Right")):
                out[k.format(S=S)] = v.format(s=s, side=side, Side=Side, S=S)
        else:
            out[k] = v
    return out


ADAPTERS = {
    # Quaternius Universal Animation Library: UE-mannequin names, fingers
    "quaternius": {
        "map": sides({
            "hips": "pelvis", "spine": "spine_01", "chest": "spine_03", "neck": "neck_01", "head": "Head",
            "clavicle.{S}": "clavicle_{s}", "upper_arm.{S}": "upperarm_{s}", "forearm.{S}": "lowerarm_{s}",
            "hand.{S}": "hand_{s}", "thigh.{S}": "thigh_{s}", "shin.{S}": "calf_{s}", "foot.{S}": "foot_{s}",
            "toe.{S}": "ball_{s}",
            **{f"{f}_0{i}.{{S}}": f"{f}_0{i}_{{s}}" for f in FINGERS for i in (1, 2, 3)},
        })
    },
    # KayKit Character Animations (Rig_Medium): no neck, clavicles or fingers
    "kaykit": {
        "map": sides({
            "hips": "hips", "spine": "spine", "chest": "chest", "head": "head",
            "upper_arm.{S}": "upperarm.{s}", "forearm.{S}": "lowerarm.{s}", "hand.{S}": "hand.{s}",
            "thigh.{S}": "upperleg.{s}", "shin.{S}": "lowerleg.{s}", "foot.{S}": "foot.{s}", "toe.{S}": "toes.{s}",
        }),
    },
    # 100STYLE (XSens BVH, centimetres): four chest bones, no fingers
    "100style": {
        "map": sides({
            "hips": "Hips", "spine": "Chest", "chest": "Chest3", "neck": "Neck", "head": "Head",
            "clavicle.{S}": "{Side}Collar", "upper_arm.{S}": "{Side}Shoulder", "forearm.{S}": "{Side}Elbow",
            "hand.{S}": "{Side}Wrist", "thigh.{S}": "{Side}Hip", "shin.{S}": "{Side}Knee", "foot.{S}": "{Side}Ankle",
            "toe.{S}": "{Side}Toe",
        }),
    },
    # CMU mocap, RancidMilk's FBX conversion: finger bones exist but carry no motion, so they're left out
    "cmu": {
        "map": sides({
            "hips": "hip", "spine": "abdomen", "chest": "chest", "neck": "neck", "head": "head",
            "clavicle.{S}": "{s}Collar", "upper_arm.{S}": "{s}Shldr", "forearm.{S}": "{s}ForeArm", "hand.{S}": "{s}Hand",
            "thigh.{S}": "{s}Thigh", "shin.{S}": "{s}Shin", "foot.{S}": "{s}Foot",
        }),
    },
    # The library's own canonical sets: same bone names as the target
    "canonical": {"map": None},
}
FEET = ("foot.L", "foot.R", "toe.L", "toe.R")
NEUTRAL = ("hips", "spine", "chest", "neck", "head", "foot", "toe")  # same rest pose in every skeleton


def bone_order(bones):
    order = [b.name for b in bones if b.parent is None]
    i = 0
    while i < len(order):  # parents before children
        order += [c.name for c in bones[order[i]].children]
        i += 1
    return order


def bone_dir(bone, mw):
    """Rest direction: towards the child that starts nearest the tail (the hips have spine and thighs)."""
    head = mw @ bone.head_local
    end = bone.tail_local
    if bone.children:
        end = min((c.head_local for c in bone.children), key=lambda h: (h - bone.tail_local).length)
    d = (mw @ end) - head
    return d if d.length > 1e-6 else (mw @ bone.tail_local) - head


class Target:
    def __init__(self, obj):
        self.obj = obj
        bones = obj.data.bones
        self.order = bone_order(bones)
        self.rest = {n: bones[n].matrix_local.copy() for n in self.order}
        self.parent = {n: bones[n].parent.name if bones[n].parent else None for n in self.order}
        self.dir = {n: bone_dir(bones[n], Matrix()) for n in self.order}
        self.leg = (bones["thigh.L"].head_local - bones["foot.L"].head_local).length
        self.hips = bones["hips"].head_local.copy()
        self.standing = self.hips.z - min(bones[n].head_local.z for n in FEET if n in bones)


class Source:
    """An imported source armature, mapped onto the target's bone names."""

    def __init__(self, obj, kind, target):
        self.obj, self.kind = obj, kind
        adapter = ADAPTERS[kind]
        bones = obj.data.bones
        mapping = adapter["map"] or {n: n for n in target.order}
        # Finger motion is left out for now: when a body's thumb side is misread the palm flips and the
        # wrist twists like a rope, which looks far worse than open hands that keep the model's shape
        self.map = {t: s for t, s in mapping.items() if s in bones and t in target.rest and t.split("_")[0] not in FINGERS}
        mw = obj.matrix_world
        self.rest = {s: (mw @ bones[s].matrix_local).to_quaternion() for s in self.map.values()}
        rest_pos = {t: mw @ bones[s].head_local for t, s in self.map.items()}
        self.leg = (rest_pos["thigh.L"] - rest_pos["foot.L"]).length
        self.ratio = target.leg / self.leg
        feet = [rest_pos[n].z for n in FEET if n in rest_pos]
        self.standing = rest_pos["hips"].z - min(feet)
        self.align = {}
        for t, s in self.map.items():
            src_dir, tgt_dir = bone_dir(bones[s], mw), target.dir[t]
            if t.split(".")[0] in NEUTRAL:
                # Both skeletons stand upright with flat feet at rest, but bone directions here are
                # conventions (CMU's head bone points 45 degrees forward): copy the change, not the direction
                self.align[t] = Quaternion()
            else:
                self.align[t] = src_dir.rotation_difference(tgt_dir)

    def sample(self, action, f0=None, f1=None, step=1.0):
        """Clip of target-space world rotation deltas and hip positions, one entry per output frame."""
        ad = self.obj.animation_data_create()
        ad.action = action
        if action.slots:
            ad.action_slot = action.slots[0]
        a0, a1 = action.frame_range
        f0 = a0 if f0 is None else f0
        f1 = a1 if f1 is None else f1
        rots, hips, feet = [], [], []
        scene = bpy.context.scene
        t = f0
        while t <= f1 + 1e-6:
            scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
            mw = self.obj.matrix_world
            pose = {s: mw @ self.obj.pose.bones[s].matrix for s in self.map.values()}
            rots.append({tb: pose[s].to_quaternion() @ self.rest[s].inverted() @ self.align[tb].inverted()
                         for tb, s in self.map.items()})
            hips.append(pose[self.map["hips"]].translation.copy())
            feet.append(min(pose[self.map[n]].translation.z for n in FEET if n in self.map))
            t += step
        return Clip(rots, hips, feet, self)


class Clip:
    """A clip in target space: per frame, world rotation deltas per target bone and the hip position."""

    def __init__(self, rots, hips, feet, source):
        self.rots = rots
        floor = float(np.percentile(feet, 3))
        self.pos = [Vector(((h.x - hips[0].x) * source.ratio, (h.y - hips[0].y) * source.ratio,
                            (h.z - floor - source.standing) * source.ratio)) for h in hips]
        self.speed = 0.0

    def copy_frames(self, idx):
        c = Clip.__new__(Clip)
        c.rots = [dict(self.rots[i]) for i in idx]
        c.pos = [self.pos[i].copy() for i in idx]
        c.speed = self.speed
        return c

    def __len__(self):
        return len(self.rots)

    def facing(self, i=0):
        """Yaw of the hips (radians) at frame i; 0 means facing -Y."""
        lat = self.rots[i]["hips"] @ Vector((1, 0, 0))
        return math.atan2(lat.y, lat.x)

    def turn(self, angle):
        r = Quaternion((0, 0, 1), angle)
        for f, p in zip(self.rots, self.pos):
            for k in f:
                f[k] = r @ f[k]
            p.rotate(r)

    def face_forward(self, frames=None):
        yaws = [self.facing(i) for i in (frames or range(len(self)))]
        self.turn(-math.atan2(np.mean(np.sin(yaws)), np.mean(np.cos(yaws))))

    def mirror(self):
        sx = Matrix.Diagonal((-1, 1, 1))
        swap = lambda n: n[:-1] + {"L": "R", "R": "L"}[n[-1]] if n[-2:] in (".L", ".R") else n
        for i, f in enumerate(self.rots):
            self.rots[i] = {swap(k): (sx @ q.to_matrix() @ sx).to_quaternion() for k, q in f.items()}
        for p in self.pos:
            p.x = -p.x

    def reverse(self):
        self.rots.reverse()
        self.pos.reverse()
        base = self.pos[0].copy()
        for p in self.pos:
            p.x -= base.x
            p.y -= base.y

    def in_place(self, loop):
        """Remove travel: for loops the straight-line drift (kept as speed), otherwise just the start offset."""
        n = len(self) - 1
        p0, p1 = self.pos[0].copy(), self.pos[-1].copy()
        drift = Vector((p1.x - p0.x, p1.y - p0.y, 0))
        if loop and n > 0:
            self.speed = drift.length / (n / FPS)
            for i, p in enumerate(self.pos):
                p -= Vector((p0.x, p0.y, 0)) + drift * (i / n)
        else:
            for p in self.pos:
                p.x -= p0.x
                p.y -= p0.y

    def close_loop(self):
        """Spread the seam error over the loop, then make the last frame equal the first."""
        n = len(self) - 1
        first, last = self.rots[0], self.rots[-1]
        for k in first:
            err = first[k] @ last[k].inverted()
            if err.w < 0:
                err.negate()
            for i in range(1, n + 1):
                self.rots[i][k] = Quaternion().slerp(err, i / n) @ self.rots[i][k]
        for i in range(1, n + 1):
            self.pos[i].z += (self.pos[0].z - self.pos[-1].z) * i / n
        self.rots[-1] = dict(first)


def best_loop(clip, lo, hi, start=0, stop=None):
    """(start, length) of the most seamless loop between frames start and stop, length in [lo, hi]."""
    stop = len(clip) if stop is None else stop
    keys = [k for k in clip.rots[0] if not k.split("_")[0] in FINGERS]
    q = np.array([[list(f[k]) for k in keys] for f in clip.rots[start:stop]])  # (N, B, 4)
    yaw = np.array([clip.facing(i) for i in range(start, stop)])
    z = np.array([p.z for p in clip.pos[start:stop]])
    best = (1e9, start, lo)
    n = len(q)
    for L in range(lo, min(hi, n - 2) + 1):
        a, b = q[: n - L - 1], q[L : n - 1]
        a2, b2 = q[1 : n - L], q[L + 1 : n]
        pose = 2 * np.arccos(np.clip(np.abs((a * b).sum(-1)), 0, 1)).sum(-1)
        vel = 2 * np.arccos(np.clip(np.abs((a2 * b2).sum(-1)), 0, 1)).sum(-1)
        turn = np.abs(np.angle(np.exp(1j * (yaw[L : n - 1] - yaw[: n - L - 1]))))
        cost = pose + 0.5 * vel + 4 * turn + 5 * np.abs(z[L : n - 1] - z[: n - L - 1]) + 0.002 * L
        i = int(np.argmin(cost))
        if cost[i] < best[0]:
            best = (float(cost[i]), start + i, L)
    return best[1], best[2]


def solve(target, rots, pos, defaults=None):
    """Local pose (basis) matrices for every target bone from one clip frame."""
    world, basis = {}, {}
    for name in target.order:
        rest, parent = target.rest[name], target.parent[name]
        offset = target.rest[parent].inverted() @ rest if parent else rest
        chain = world[parent] @ offset if parent else offset
        if name in rots:
            rot = (rots[name] @ rest.to_quaternion()).to_matrix().to_4x4()
            loc = target.hips + pos if name == "hips" else chain.translation
            world[name] = Matrix.Translation(loc) @ rot
        elif defaults and name in defaults:
            world[name] = chain @ defaults[name]
        else:
            world[name] = chain
        basis[name] = offset.inverted() @ (world[parent].inverted() if parent else Matrix()) @ world[name]
    return basis


def bake(target, name, frames):
    """Key a list of basis dicts as a new action pushed to the NLA, so glTF exports it as a clip."""
    ad = target.obj.animation_data_create()
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    ad.action = action
    last = {}
    for f, basis in enumerate(frames):
        for bone, m in basis.items():
            pb = target.obj.pose.bones[bone]
            q = m.to_quaternion()
            if bone in last and last[bone].dot(q) < 0:
                q.negate()  # keep quaternions continuous so interpolation doesn't spin the long way
            last[bone] = q
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if bone == "hips":
                pb.location = m.translation
                pb.keyframe_insert("location", frame=f)
    track = ad.nla_tracks.new()
    track.name = name
    track.strips.new(name, 0, action)
    ad.action = None
    return action


def import_armature(path):
    """Import a GLB/FBX/BVH and return (armature object, every new object)."""
    before = set(bpy.data.objects)
    path = str(path)
    if path.endswith(".bvh"):
        bpy.ops.import_anim.bvh(filepath=path, use_fps_scale=True, update_scene_fps=False, update_scene_duration=False)
    elif path.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    new = set(bpy.data.objects) - before
    return next(o for o in new if o.type == "ARMATURE"), new


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    picks = {}
    for flag in ("--sets", "--clips"):
        if flag in argv:
            picks[flag] = argv[argv.index(flag) + 1].split(",")
            argv = argv[: argv.index(flag)] + argv[argv.index(flag) + 2:]
    sets, wanted = picks.get("--sets"), picks.get("--clips")
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    bpy.context.scene.render.fps = FPS
    target = Target(bpy.data.objects["Rig"])
    catalog = {c["id"]: c for c in json.loads((LIBRARY / "catalog.json").read_text())}
    meta = {}
    for glb in sorted((LIBRARY / "clips").glob("*.glb")):
        if (sets and glb.stem not in sets) or (wanted and not any(catalog[c]["set"] == glb.stem for c in wanted)):
            continue
        obj, new = import_armature(glb)
        source = Source(obj, "canonical", target)
        clips = [a for a in bpy.data.actions if a.name in catalog and catalog[a.name]["set"] == glb.stem
                 and (not wanted or a.name in wanted)]
        for action in clips:
            clip = source.sample(action)
            frames = [solve(target, r, p) for r, p in zip(clip.rots, clip.pos)]
            entry = catalog[action.name]
            bpy.data.actions.remove(action)
            bake(target, entry["id"], frames)
            meta[entry["id"]] = {**entry, "speed": round(entry.get("speed", 0) * source.ratio, 3)}
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in [a for a in bpy.data.actions if a.name not in meta]:
        bpy.data.actions.remove(a)

    out = Path(argv[1]).resolve()
    if len(argv) > 2:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(argv[2]).resolve()))
    bpy.ops.export_scene.gltf(
        filepath=str(out), export_format="GLB", export_animation_mode="ACTIONS",
        export_force_sampling=True, export_optimize_animation_size=True, export_def_bones=False,
    )
    out.with_suffix(".clips.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("RETARGETED", len(meta), "clips")


if __name__ == "__main__":
    main()
