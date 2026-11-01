# Make a held prop from a generated model: one mesh, real length, its long axis standing up, and an empty named
# Grip at the hand-hold (the origin; glTF +Y runs along the handle), so it attaches to any Socket_Grip_* bone.
#   bun run art:forge prop --in <model.glb> --out <prop.glb> --length 2.1 [--grip 0.42] [--flip true] [--name spear]
# --grip: where the hand holds it, as a fraction of the length from the bottom end. --flip turns it end over end
# when the generator delivered it upside down.
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, contract, done, export, fail, load, reset, triangles, with_active  # noqa: E402

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

a = args()
reset()
objects = load(a["in"])
meshes = [o for o in objects if o.type == "MESH"]
if not meshes:
    fail("no mesh")
for o in objects:
    if o not in meshes:
        bpy.data.objects.remove(o)
for m in meshes:
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
prop = meshes[0]
if len(meshes) > 1:
    with bpy.context.temp_override(active_object=prop, object=prop, selected_objects=meshes, selected_editable_objects=meshes):
        bpy.ops.object.join()
with with_active(prop):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# Contract budgets: decimate to the triangle budget, downscale textures to the texture budget
budget = contract("rigid")["kinds"]["prop"]
before = triangles(prop)
if before > budget["triangles"]:
    dec = prop.modifiers.new("budget", "DECIMATE")
    dec.ratio = budget["triangles"] / before * 0.97
    with with_active(prop):
        bpy.ops.object.modifier_apply(modifier=dec.name)
for img in bpy.data.images:
    if img.size[0] and max(img.size) > budget["texture"]:
        f = budget["texture"] / max(img.size)
        img.scale(int(img.size[0] * f), int(img.size[1] * f))

pts = [v.co for v in prop.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
size = hi - lo
axis = max(range(3), key=lambda i: size[i])
# Stand the long axis up (+Z in Blender is glTF +Y)
turn = {0: Matrix.Rotation(math.radians(90), 4, "Y"), 1: Matrix.Rotation(math.radians(-90), 4, "X"), 2: Matrix.Identity(4)}[axis]
if a.get("flip"):
    turn = Matrix.Rotation(math.pi, 4, "X") @ turn
prop.data.transform(turn @ Matrix.Translation(-(lo + hi) / 2))
pts = [v.co for v in prop.data.vertices]
zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
scale = a["length"] / (zmax - zmin)
grip_z = (zmin + a.get("grip", 0.4) * (zmax - zmin)) * scale
prop.data.transform(Matrix.Translation((0, 0, -grip_z)) @ Matrix.Scale(scale, 4))
prop.name = a.get("name", Path(a["out"]).stem.split(".")[0])
grip = bpy.data.objects.new("Grip", None)
bpy.context.scene.collection.objects.link(grip)
grip.empty_display_type = "ARROWS"
meta = {"family": "rigid", "kind": "prop", "rigidKind": "prop", "length": a["length"], "grip": a.get("grip", 0.4),
        "sockets": a.get("sockets", ["Socket_Grip_R", "Socket_Grip_L", "Socket_Back"]), "source": a["in"]}
prop["forge"] = json.dumps(meta)
grip["forge"] = json.dumps({"role": "grip"})
out = export(a["out"], [prop, grip])
done(out=out, triangles=triangles(prop), length=a["length"], longAxis="xyz"[axis])
