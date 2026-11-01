# Report what a GLB contains: objects, bones, shape keys, triangles, materials, size and forge metadata.
#   bun run art:forge inspect --in <file.glb>
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, done, load, reset, triangles  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

a = args()
reset()
objects = load(a["in"])
report = {"objects": {}, "actions": [act.name for act in bpy.data.actions]}
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in objects:
    d = {"type": o.type, "parent": o.parent.name if o.parent else None,
         "scale": [round(s, 4) for s in o.scale], "rotation": [round(r, 4) for r in o.rotation_euler]}
    if "forge" in o:
        d["forge"] = json.loads(o["forge"])
    if o.type == "ARMATURE":
        d["bones"] = {b.name: {"parent": b.parent.name if b.parent else None, "deform": b.use_deform} for b in o.data.bones}
    if o.type == "MESH":
        d.update(triangles=triangles(o), vertices=len(o.data.vertices),
                 shapeKeys=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],
                 uvLayers=[u.name for u in o.data.uv_layers], materials=[m.name for m in o.data.materials if m],
                 vertexGroups=len(o.vertex_groups), colorAttributes=[c.name for c in o.data.color_attributes])
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    if o.type == "EMPTY":
        d["location"] = [round(x, 4) for x in o.matrix_world.translation]
    report["objects"][o.name] = d
report["size"] = [round(x, 3) for x in (hi - lo)] if hi.x > lo.x else None
done(**report)
