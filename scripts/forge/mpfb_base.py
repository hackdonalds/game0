# Build the humanoid family base from MakeHuman/MPFB2 CC0 data: a neutral body (gender, age, muscle and weight
# at 0.5), the game-engine skeleton with MakeHuman's weights, a `_neg`/`_pos` shape key pair per contract morph
# slider (art/families/humanoid/mpfb-targets.json), the 52 ARKit face units (faceunits01 pack, CC0), and the
# helper geometry removed except the eyeballs. Run canonicalize on the result.
# Needs the MPFB extension installed in Blender (blender -c extension install mpfb --enable).
#   bun run art:forge mpfb_base --out <raw.glb> [--arkit true]
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import REPO, args, contract, done, export, fail, warn  # noqa: E402

import addon_utils  # noqa: E402
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

a = args()
c = contract("humanoid")
spec = json.loads((REPO / "art/families/humanoid/mpfb-targets.json").read_text())
if not addon_utils.enable("bl_ext.blender_org.mpfb", default_set=True):
    fail("MPFB is not installed: blender -c extension install mpfb --enable")
from bl_ext.blender_org.mpfb.entities.objectproperties import HumanObjectProperties  # noqa: E402
from bl_ext.blender_org.mpfb.services.humanservice import HumanService  # noqa: E402
from bl_ext.blender_org.mpfb.services.targetservice import TargetService  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
h = HumanService.create_human(mask_helpers=False, detailed_helpers=True, extra_vertex_groups=True, scale=0.1)


def set_macros(values: dict):
    for name, value in values.items():
        HumanObjectProperties.set_value(name, value, entity_reference=h)
    TargetService.reapply_macro_details(h)


def mix() -> np.ndarray:
    ev = h.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    co = np.array([v.co[:] for v in mesh.vertices])
    ev.to_mesh_clear()
    return co


def with_targets(names: list) -> np.ndarray:
    loaded = []
    for name in names:
        full = TargetService.target_full_path(name)
        if not full:
            fail(f"MPFB target {name} not found")
        TargetService.load_target(h, full, weight=1.0, name=f"forge_tmp_{len(loaded)}")
        loaded.append(f"forge_tmp_{len(loaded)}")
    co = mix()
    for name in loaded:
        h.shape_key_remove(h.data.shape_keys.key_blocks[name])
    return co


neutral = spec["neutral"]
set_macros(neutral)
basis = mix()
keys: dict[str, np.ndarray] = {}
for slider, m in spec["macros"].items():
    for side in ("neg", "pos"):
        set_macros({**neutral, m["macro"]: m[side]})
        keys[f"{slider}_{side}"] = mix()
set_macros(neutral)
for slider, m in spec["targets"].items():
    for side in ("neg", "pos"):
        keys[f"{slider}_{side}"] = with_targets(m[side])
expressions = c["sliders"]["expressions"] if a.get("arkit", True) else []
for name in expressions:
    if TargetService.target_full_path(name):
        keys[name] = with_targets([name])
    else:
        warn(f"ARKit face unit {name} not installed (faceunits01 pack)")

# Skeleton and weights, fitted to the neutral body
HumanService.add_builtin_rig(h, spec["rig"], import_weights=True)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")

# Our own shape keys on the neutral basis
h.shape_key_clear()
for v, co in zip(h.data.vertices, basis):
    v.co = co
h.shape_key_add(name="Basis", from_mix=False)
for name, co in keys.items():
    kb = h.shape_key_add(name=name, from_mix=False)
    kb.data.foreach_set("co", co.ravel())

# Drop helper geometry (clothes helpers, joints, teeth, tongue), keeping the body and eyeballs
groups = {g.name: g.index for g in h.vertex_groups}
keep = {groups[n] for n in spec["keep"] if n in groups}
missing = [n for n in spec["keep"] if n not in groups]
if missing:
    warn(f"keep groups not found: {missing}")
bm = bmesh.new()
bm.from_mesh(h.data)
deform = bm.verts.layers.deform.active
drop = [v for v in bm.verts if not any(g in keep and w > 0 for g, w in v[deform].items())]
bmesh.ops.delete(bm, geom=drop, context="VERTS")
bm.to_mesh(h.data)
bm.free()
bones = {b.name for b in rig.data.bones}
for g in list(h.vertex_groups):
    if g.name not in bones:
        h.vertex_groups.remove(g)
for mod in list(h.modifiers):
    if mod.type != "ARMATURE":
        h.modifiers.remove(mod)
h.name = "Body"
h["forge"] = json.dumps({"family": "humanoid", "kind": "body", "source": "MakeHuman MPFB2 base (CC0)"})
out = export(a["out"], [rig, h])
done(out=out, vertices=len(h.data.vertices), keys=len(keys), bones=sorted(bones), dropped=len(drop))
