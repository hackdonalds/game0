# Orthographic QA renders of a GLB (Workbench, fast, no GPU needed), optionally posed or coloured by region/dye.
#   bun run art:forge render --in <file.glb> --out <prefix> [--views ["front","left","back","right"]] [--size 512]
#     [--pose {"LeftUpperArm": [0, 0, 60]}]  # degrees, pose-bone XYZ Euler
#     [--action Walk --frame 12]              # pose from an imported clip
#     [--color texture|regions|dye|single]    # regions: one colour per body region; dye: the <in>.dye.png mask
#     [--keys {"body_muscle_pos": 1}]         # shape key values, applied to every mesh that has the key
#     [--with other.glb ...]                  # extra GLBs loaded into the same scene (gear on a body); their meshes
#                                             # are rebound to the first file's armature so they follow the pose
# Writes <prefix>-<view>.png and prints the paths.
import colorsys
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import apply_pose_offsets, args, contract, done, fail, load, path, pose_offsets, regions_uv, reset  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

a = args()
reset()
objects = load(a["in"])
for extra in ([a["with"]] if isinstance(a.get("with"), str) else a.get("with", [])):
    objects += load(extra)
arms = [o for o in objects if o.type == "ARMATURE"]
meshes = [o for o in objects if o.type == "MESH"]
if len(arms) > 1:
    main = next(x for x in arms if any(m.parent == x or any(md.type == "ARMATURE" and md.object == x for md in m.modifiers) for m in meshes))
    for m in meshes:
        for mod in m.modifiers:
            if mod.type == "ARMATURE" and mod.object in arms[1:]:
                mod.object = main
        if m.parent in arms[1:]:
            mw = m.matrix_world.copy()
            m.parent = main
            m.matrix_world = mw
    for extra_arm in [x for x in arms if x is not main]:
        bpy.data.objects.remove(extra_arm)
    arms = [main]

if arms and a.get("action"):
    # Clips from a family library play on any body of the family: bone names and rest rotations match
    act = bpy.data.actions.get(a["action"]) or next((x for x in bpy.data.actions if a["action"].lower() in x.name.lower()), None)
    if not act:
        fail(f"no clip {a['action']}", clips=[x.name for x in bpy.data.actions])
    arms[0].animation_data_create()
    arms[0].animation_data.action = act
    if act.slots:
        arms[0].animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(int(a.get("frame", act.frame_range[0])))
    body_meta = next((json.loads(m["forge"]) for m in meshes if "forge" in m and json.loads(m["forge"]).get("kind") == "body"), {})
    if body_meta.get("people"):
        apply_pose_offsets(arms[0], pose_offsets(contract(body_meta.get("family", "humanoid")), body_meta["people"], a.get("keys", {})))
if arms and a.get("pose"):
    for bone, rot in a["pose"].items():
        pb = arms[0].pose.bones.get(bone)
        if pb:
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = Euler([math.radians(r) for r in rot])
# Worn pieces hide the body under them with their body masks, as the runtime does
masks = []
for o in meshes:
    meta = json.loads(o["forge"]) if "forge" in o else {}
    if meta.get("kind") == "gear" and meta.get("mask"):
        for extra in ([a["with"]] if isinstance(a.get("with"), str) else a.get("with", [])):
            f = Path(path(extra)).with_suffix(".mask.png")
            if f.name == meta["mask"] and f.exists():
                img = bpy.data.images.load(str(f))
                masks.append(np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], -1)[..., 0])
if masks:
    hide = np.maximum.reduce(masks)
    h, w = hide.shape
    for o in meshes:
        meta = json.loads(o["forge"]) if "forge" in o else {}
        if meta.get("kind") != "body":
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        uv = bm.loops.layers.uv[0]
        gone = [f for f in bm.faces if all(hide[min(h - 1, int(l[uv].uv[1] * h)), min(w - 1, int(l[uv].uv[0] * w))] > 0.5 for l in f.loops)]
        bmesh.ops.delete(bm, geom=gone, context="FACES_ONLY")
        bm.to_mesh(o.data)
        bm.free()

# A people's body turns its signature key on in every mesh worn with it (generalised gear carries the key at 0)
people_keys = {}
for o in meshes:
    if "forge" in o:
        meta = json.loads(o["forge"])
        if meta.get("kind") == "body" and meta.get("signature"):
            people_keys[meta["signature"]] = 1.0
for m in meshes:
    for name, value in {**people_keys, **a.get("keys", {})}.items():
        if m.data.shape_keys and name in m.data.shape_keys.key_blocks:
            m.data.shape_keys.key_blocks[name].value = value
bpy.context.view_layer.update()

color = a.get("color", "texture")
if color in ("regions", "dye"):
    for m in meshes:
        attr = m.data.color_attributes.new("ForgeQA", "FLOAT_COLOR", "CORNER")
        if color == "regions" and regions_uv(m):
            uv = regions_uv(m).data
            for i in range(len(m.data.loops)):
                r = int(uv[i].uv[0] * 32)
                attr.data[i].color = (*colorsys.hsv_to_rgb((r * 0.618) % 1, 0.65, 0.95), 1)
        elif color == "dye":
            mask = bpy.data.images.load(path(a["in"]).replace(".glb", ".dye.png"))
            w, h = mask.size
            px = mask.pixels[:]
            uv = m.data.uv_layers[0].data
            for i in range(len(m.data.loops)):
                u, v = uv[i].uv
                x, y = min(w - 1, max(0, int(u * w))), min(h - 1, max(0, int(v * h)))
                k = (y * w + x) * 4
                attr.data[i].color = (px[k] * 0.9 + 0.1, px[k + 1] * 0.9 + 0.1, px[k + 2] * 0.9 + 0.1, 1)
        m.data.color_attributes.active_color = attr
        m.data.color_attributes.render_color_index = m.data.color_attributes.find(attr.name)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = {"texture": "TEXTURE", "single": "SINGLE"}.get(color, "VERTEX")
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = int(a.get("size", 512))
scene.render.film_transparent = True

deps = bpy.context.evaluated_depsgraph_get()
pts = [m.matrix_world @ v.co for m in meshes for v in m.evaluated_get(deps).to_mesh().vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centre, extent = (lo + hi) / 2, max(hi - lo)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
cam.data.type, cam.data.ortho_scale = "ORTHO", extent * 1.1
scene.camera = cam
views = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (1, 0, 0), "right": (-1, 0, 0), "top": (0, 0, 1),
         "three-quarter": (0.7, -0.7, 0.25)}
written = []
for view in a.get("views", ["front", "left", "back", "right"]):
    d = Vector(views[view]).normalized()
    cam.location = centre + d * extent * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{path(a['out'])}-{view}.png"
    bpy.ops.render.render(write_still=True)
    written.append(scene.render.filepath)
done(files=written)
