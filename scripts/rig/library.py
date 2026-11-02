# Build the biped clip library: sample source clips, apply each recipe, retarget onto the canonical body.
# Usage: blender -b --factory-startup -P scripts/rig/library.py -- <out_dir> [--only id,id]
# Reads art/anims/biped/recipes.json and sources.json, and the source cache (bun run anim:fetch biped).
# Writes <out_dir>/<set>.glb (skeleton + clips), <out_dir>/reference.glb (the canonical body) and
# <out_dir>/catalog.json. The Bun wrapper (scripts/anims/build.ts) compresses them into art/anims/biped/.
import csv
import json
import math
import os
import re
import sys
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from autorig import build_armature, find_landmarks, mesh_points, skin  # noqa: E402
from lib import import_glb, reset_scene  # noqa: E402
from retarget import FINGERS, FPS, LOWER, LIBRARY, ROOT, Source, Target, bake, best_loop, import_armature, solve  # noqa: E402

CACHE = Path(os.environ.get("GAME0_ANIM_CACHE", Path.home() / ".cache/game0/anims"))
REFERENCE_BODY = ROOT / "art/models/rootwarden/base.glb"
KAYKIT = "KayKit_Character_Animations_1.1/Animations/gltf/Rig_Medium/Rig_Medium_{}.glb"
KINDS = {"quaternius-ual1": "quaternius", "quaternius-ual2": "quaternius", "kaykit-anims": "kaykit",
         "100style": "100style", "cmu": "cmu"}
MOCAP_SKIP = {"cmu": 0.1}  # seconds: the cgspeed conversion adds a T-pose as the first frame


def source_file(src, recipe):
    if src == "quaternius-ual1":
        return CACHE / src / "UAL1_Standard.glb"
    if src == "quaternius-ual2":
        return CACHE / src / "UAL2_Standard.glb"
    if src == "kaykit-anims":
        rel = KAYKIT.format(recipe["file"])
        path = CACHE / src / rel
        if not path.exists():
            with zipfile.ZipFile(CACHE / src / "KayKit_Character_Animations_1.1.zip") as z:
                z.extract(rel, CACHE / src)
        return path
    return CACHE / src / recipe["file"]


class Sources:
    """Imports each source file once and keeps it until the build ends."""

    def __init__(self, target):
        self.target, self.loaded = target, {}
        cuts = CACHE / "100style/Frame_Cuts.csv"
        self.cuts = {r["STYLE_NAME"]: r for r in csv.DictReader(cuts.open())} if cuts.exists() else {}

    def get(self, recipe):
        src = recipe["source"]
        path = source_file(src, recipe)
        if path not in self.loaded:
            before = set(bpy.data.actions)
            obj, new = import_armature(path)
            for o in new:  # source meshes only slow down every frame change
                if o != obj and o.type == "MESH":
                    bpy.data.objects.remove(o, do_unlink=True)
            obj.hide_set(True)
            actions = [a for a in bpy.data.actions if a not in before]
            self.loaded[path] = (Source(obj, KINDS[src], self.target), actions)
        return self.loaded[path]

    def clip(self, recipe):
        source, actions = self.get(recipe)
        name = recipe.get("clip")
        # Blender renames clashing clip names (KayKit and Quaternius both have "Interact") to "Interact.001"
        action = next((a for a in actions if re.sub(r"\.\d{3}$", "", a.name) == name), None) if name else actions[0]
        if action is None:
            raise KeyError(f"{recipe['id']}: no clip {name} in {recipe['source']}")
        f0, f1 = action.frame_range
        if recipe["source"] in MOCAP_SKIP:
            f0 += MOCAP_SKIP[recipe["source"]] * FPS
        if "cut" in recipe:  # 100STYLE trim points, given at 60 fps
            row = self.cuts[recipe["file"].split("/")[0]]
            f0 = int(row[f"{recipe['cut']}_START"]) / 2
            f1 = int(row[f"{recipe['cut']}_STOP"]) / 2
        if "range" in recipe:
            f0, f1 = f0 + recipe["range"][0], f0 + recipe["range"][1]
        return source, source.sample(action, f0, f1)


def prepare(recipe, sources):
    """Sampled, looped, mirrored... target-space clip for one recipe (or a composite part)."""
    source, clip = sources.clip(recipe)
    loop = recipe.get("loop", False)
    if "autoLoop" in recipe:
        lo, hi = recipe["autoLoop"]
        s, n = best_loop(clip, lo, hi)
        clip = clip.copy_frames(range(s, s + n + 1))
    if "frame" in recipe:
        clip = clip.copy_frames([recipe["frame"]])
    if recipe["source"] in ("100style", "cmu"):
        clip.face_forward(None if loop else [0])  # one-shots may turn: face forward at the start
    if recipe.get("reverse"):
        clip.reverse()
    if recipe.get("mirror"):
        clip.mirror()
    clip.in_place(loop)
    if loop and len(clip) > 2:
        clip.close_loop()
    if "speed" in recipe:  # measured on the source's own body (root-motion exports)
        clip.speed = recipe["speed"] * source.ratio
    return clip


def foot_speed(frames_world):
    """Ground speed of an in-place loop: how fast the planted foot slides back."""
    speeds = []
    for a, b in zip(frames_world, frames_world[1:]):
        foot = min(("toe.L", "toe.R"), key=lambda n: a[n].translation.z)
        speeds.append(abs(b[foot].translation.y - a[foot].translation.y) * FPS)
    speeds.sort()
    return speeds[len(speeds) // 2] if speeds else 0.0


def build(recipes, sources, target, defaults):
    built = {}
    for r in recipes:
        clip = prepare(r, sources)
        frames = [solve(target, rot, pos, defaults) for rot, pos in zip(clip.rots, clip.pos)]
        if "upper" in r:
            upper = prepare({**r["upper"], "id": r["id"]}, sources)
            ufr = [solve(target, rot, pos, defaults) for rot, pos in zip(upper.rots, upper.pos)]
            hold = r["upper"].get("hold")
            for i, f in enumerate(frames):
                u = ufr[hold if hold is not None else i % len(ufr)]
                for k in f:
                    if not k.split(".")[0].startswith(LOWER):
                        f[k] = u[k]
        speed = clip.speed
        if r.get("loop") and speed == 0 and r.get("set") == "locomotion":
            speed = foot_speed(world_frames(target, frames))
        bake(target, r["id"], frames)
        built[r["id"]] = {
            "id": r["id"], "name": r["name"], "set": r["set"], "tags": r.get("tags", []),
            **({"variantOf": r["variantOf"]} if r.get("variantOf") else {}),
            "loop": r.get("loop", False), "speed": round(speed, 3), "frames": len(frames) - 1, "fps": FPS,
            "source": r["source"], "sourceClip": r.get("clip") or r.get("file"),
            **({"upperSource": f"{r['upper']['source']}:{r['upper'].get('clip') or r['upper'].get('file')}"} if "upper" in r else {}),
            **({"note": r["note"]} if r.get("note") else {}),
        }
        print("BUILT", r["id"], len(frames), round(speed, 2))
        if r["id"] == "idle":  # relaxed hands for sources without finger motion
            defaults.update({k: v for k, v in frames[0].items() if k.split("_")[0] in FINGERS})
    return built


def world_frames(target, frames):
    out = []
    for basis in frames:
        world = {}
        for n in target.order:
            p = target.parent[n]
            offset = target.rest[p].inverted() @ target.rest[n] if p else target.rest[n]
            world[n] = (world[p] @ offset if p else offset) @ basis[n]
        out.append(world)
    return out


def skin_anchor(rig):
    """A one-triangle mesh skinned to the hips: glTF only carries a skeleton through a skin."""
    me = bpy.data.meshes.new("SkinAnchor")
    me.from_pydata([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new("SkinAnchor", me)
    bpy.context.collection.objects.link(obj)
    obj.vertex_groups.new(name="hips").add([0, 1, 2], 1.0, "REPLACE")
    obj.parent = rig
    obj.modifiers.new("Armature", "ARMATURE").object = rig
    return obj


def export(target, out, sets):
    rig = target.obj
    ad = rig.animation_data
    anchor = skin_anchor(rig)
    for o in bpy.context.scene.objects:
        o.select_set(o in (rig, anchor))
    bpy.context.view_layer.objects.active = rig
    for name, ids in sets.items():
        for track in list(ad.nla_tracks):
            ad.nla_tracks.remove(track)
        for clip_id in ids:
            track = ad.nla_tracks.new()
            track.name = clip_id
            track.strips.new(clip_id, 0, bpy.data.actions[clip_id])
        bpy.ops.export_scene.gltf(
            filepath=str(out / f"{name}.glb"), export_format="GLB", use_selection=True,
            export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_optimize_animation_size=True,
            export_def_bones=False,
        )


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = Path(argv[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None

    reset_scene()
    bpy.context.scene.render.fps = FPS
    mesh = import_glb(REFERENCE_BODY)
    J, H, _ = find_landmarks(mesh_points(mesh))
    rig = build_armature(J, H)
    skin(mesh, rig, H)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out / "reference.glb"), export_format="GLB", use_selection=True,
                              export_animations=False, export_def_bones=False)
    bpy.data.objects.remove(mesh, do_unlink=True)  # keeps frame changes cheap while sampling
    target = Target(rig)

    recipes = json.loads((LIBRARY / "recipes.json").read_text())
    idle = [r for r in recipes if r["id"] == "idle"]
    recipes = idle + [r for r in recipes if r["id"] != "idle" and (not only or r["id"] in only)]
    licenses = {s["id"]: s["license"] for s in json.loads((LIBRARY / "sources.json").read_text())}
    built = build(recipes, Sources(target), target, {})
    for entry in built.values():
        entry["license"] = licenses[entry["source"]]

    for o in [o for o in bpy.data.objects if o != target.obj]:  # the source armatures
        bpy.data.objects.remove(o, do_unlink=True)
    for a in [a for a in bpy.data.actions if a.name not in built]:
        bpy.data.actions.remove(a)
    sets = {}
    for entry in built.values():
        sets.setdefault(entry["set"], []).append(entry["id"])
    export(target, out, sets)
    (out / "catalog.json").write_text(json.dumps(list(built.values()), indent=2) + "\n")
    print("LIBRARY", len(built), "clips in", len(sets), "sets")


main()
