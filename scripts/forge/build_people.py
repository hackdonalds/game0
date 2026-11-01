# Build a people's shippable body from the family base: the people's signature shape key on by default, and
# the skeleton moved to the people's joints (from wrap's .rest.json), and sockets re-placed on its surface.
# Bone rest rotations stay identical (all bones point up), so the family clip library plays unchanged.
#   bun run art:forge build_people --base <base+keys.glb> --rest <people.rest.json> --people galeborne --out <galeborne.body.glb>
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, contract, done, export, fail, load, path, reset, skinned_meshes, socket_points, with_active  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
people = a["people"]
if people not in c.get("peoples", c.get("species", {})):
    fail(f"{people} is not in the {c['family']} contract")
rest = json.loads(Path(path(a["rest"])).read_text())
key = rest["key"]
reset()
objects = load(a["base"])
arm = armature_of(objects)
meshes = skinned_meshes(objects, arm)
if not any(m.data.shape_keys and key in m.data.shape_keys.key_blocks for m in meshes):
    fail(f"the base has no shape key {key}; run wrap first")

# Sockets are re-placed on the people's own surface (the wrapped hands, back and head), not just moved
arm.data.pose_position = "REST"
for m in meshes:
    for kb in (m.data.shape_keys.key_blocks[1:] if m.data.shape_keys else []):
        kb.value = 1.0 if kb.name == key else 0.0
sockets = socket_points(arm, meshes, c)
arm.data.pose_position = "POSE"
with with_active(arm):
    bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
moved = {}
# Parents first, so a socket's offset is taken from its parent's new position
for b in sorted(eb, key=lambda x: len(x.parent_recursive)):
    old = b.head.copy()
    if b.name in sockets:
        new = sockets[b.name]
    elif b.name in rest["heads"]:
        new = Vector(rest["heads"][b.name])
    elif b.parent and b.parent.name in moved:
        new = old + moved[b.parent.name]
    else:
        continue
    moved[b.name] = new - old
    length = b.length
    b.head, b.tail = new, new + Vector((0, 0, length))
bpy.ops.object.mode_set(mode="OBJECT")

meta = {"family": c["family"], "kind": "body", "people": people, "signature": key, "base": a["base"]}
arm["forge"] = json.dumps(meta)
for m in meshes:
    m["forge"] = json.dumps(meta)
out = export(a["out"], [arm, *meshes], key_values={key: 1.0})
done(out=out, people=people, movedBones=len(moved), maxMove=round(max((v.length for v in moved.values()), default=0), 4))
