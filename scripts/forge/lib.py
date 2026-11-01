# Shared helpers for the asset-forge Blender steps. Each step runs headless:
#   blender -b --factory-startup --python scripts/forge/<step>.py -- '<json args>'
# and prints one line `FORGE_RESULT {...}` that scripts/forge.ts parses.
import json
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REPO = Path(__file__).resolve().parents[2]
UP = Vector((0, 0, 1))
# Character space in Blender: -Y is the front, +X is the character's left
DIRS = {"up": Vector((0, 0, 1)), "down": Vector((0, 0, -1)), "front": Vector((0, -1, 0)), "back": Vector((0, 1, 0)),
        "left": Vector((1, 0, 0)), "right": Vector((-1, 0, 0))}

warnings: list[str] = []


def args() -> dict:
    return json.loads(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else {}


def done(**result):
    print("FORGE_RESULT " + json.dumps({"ok": True, "warnings": warnings, **result}))


def fail(message: str, **extra):
    print("FORGE_RESULT " + json.dumps({"ok": False, "error": message, "warnings": warnings, **extra}))
    sys.exit(1)


def warn(message: str):
    warnings.append(message)


def path(p: str) -> str:
    return str((REPO / p).resolve()) if not Path(p).is_absolute() else p


def contract(family: str) -> dict:
    return json.loads((REPO / "art" / "families" / family / "contract.json").read_text())


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(file: str) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path(file))
    new = [o for o in bpy.data.objects if o not in before]
    # The importer adds an Icosphere as the bones' display shape; it is not part of the asset
    shapes = {pb.custom_shape for o in new if o.type == "ARMATURE" for pb in o.pose.bones if pb.custom_shape}
    for o in new:
        if o.type == "ARMATURE":
            for pb in o.pose.bones:
                pb.custom_shape = None
    kept = [o for o in new if o not in shapes]
    for shape in shapes:
        bpy.data.objects.remove(shape)
    return kept


def export(file: str, objects: list, animations: bool = False, key_values: dict | None = None):
    """Write a GLB. Shape key default weights are 0 unless `key_values` names them (a people body ships its
    signature key at 1)."""
    for o in objects:
        if o.type == "MESH" and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks[1:]:
                kb.value = (key_values or {}).get(kb.name, 0.0)
    out = Path(path(file))
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(out), export_format="GLB", use_selection=True, export_extras=True, export_yup=True,
        export_apply=False, export_morph=True, export_morph_normal=True, export_skins=True, export_def_bones=False,
        export_influence_nb=4, export_animations=animations, export_animation_mode="ACTIONS",
        export_texcoords=True, export_normals=True,
        # Only keyed channels: clips carry rotations (plus Hips translation) so each body keeps its own proportions
        export_force_sampling=False, export_optimize_animation_size=True,
    )
    return str(out)


def regions_uv(obj):
    """The body-region UV layer: TEXCOORD_1 in glTF (Blender renames it on import)."""
    layers = obj.data.uv_layers
    return layers.get("Regions") or (layers[1] if len(layers) > 1 else None)


def armature_of(objects: list):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        fail(f"expected one armature, found {len(arms)}")
    return arms[0]


def skinned_meshes(objects: list, arm) -> list:
    return [o for o in objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]


def triangles(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def with_active(obj):
    """Context override so object operators act on `obj` in background mode."""
    bpy.context.view_layer.objects.active = obj
    return bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj])


def dominant_groups(obj) -> list:
    """Index of the heaviest vertex group per vertex (-1 when unweighted)."""
    out = []
    for v in obj.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        out.append(best.group if best and best.weight > 0 else -1)
    return out


def bone_vertices(obj, bones: set) -> list:
    """World positions of vertices whose heaviest group is one of `bones`."""
    names = {g.index: g.name for g in obj.vertex_groups}
    dom = dominant_groups(obj)
    mw = obj.matrix_world
    return [mw @ obj.data.vertices[i].co for i, g in enumerate(dom) if names.get(g) in bones]


def limit_and_normalize(obj, limit: int = 4, deform: set | None = None):
    """Keep the `limit` heaviest deform weights per vertex and normalise them to 1."""
    names = {g.index: g.name for g in obj.vertex_groups}
    changed = 0
    for v in obj.data.vertices:
        gs = [g for g in v.groups if g.weight > 0 and (deform is None or names[g.group] in deform)]
        gs.sort(key=lambda g: g.weight, reverse=True)
        drop, keep = gs[limit:], gs[:limit]
        for g in drop:
            obj.vertex_groups[g.group].remove([v.index])
        total = sum(g.weight for g in keep)
        if total > 0 and abs(total - 1) > 1e-4:
            for g in keep:
                g.weight /= total
        changed += bool(drop)
    return changed


def norm(name: str) -> str:
    name = re.sub(r"^mixamorig\d*", "", name.split(":")[-1], flags=re.I)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def aliases(c: dict) -> dict:
    table = {norm(n): n for n in c["skeleton"]["core"] + c["skeleton"]["optional"]}
    fingers = {"thumb": ("Thumb", ["Metacarpal", "Proximal", "Distal"]), "index": ("Index", ["Proximal", "Intermediate", "Distal"]),
               "middle": ("Middle", ["Proximal", "Intermediate", "Distal"]), "ring": ("Ring", ["Proximal", "Intermediate", "Distal"]),
               "pinky": ("Little", ["Proximal", "Intermediate", "Distal"])}
    for side, s in (("Left", "l"), ("Right", "r")):
        lo = side.lower()
        for keys, bone in [((f"{lo}shoulder", f"clavicle{s}"), "Shoulder"), ((f"{lo}arm", f"upperarm{s}"), "UpperArm"),
                           ((f"{lo}forearm", f"lowerarm{s}"), "LowerArm"), ((f"{lo}hand", f"hand{s}"), "Hand"),
                           ((f"{lo}upleg", f"thigh{s}"), "UpperLeg"), ((f"{lo}leg", f"calf{s}"), "LowerLeg"),
                           ((f"{lo}foot", f"foot{s}"), "Foot"), ((f"{lo}toebase", f"ball{s}"), "Toes"), ((f"{lo}eye", f"eye{s}"), "Eye")]:
            for k in keys:
                table[k] = f"{side}{bone}"
        for key, (finger, parts) in fingers.items():
            for i, part in enumerate(parts, 1):
                table[f"{lo}hand{key}{i}"] = f"{side}{finger}{part}"  # Mixamo
                table[f"{key}0{i}{s}"] = f"{side}{finger}{part}"  # UE
    table.update({"pelvis": "Hips", "neck01": "Neck", "jaw": "Jaw"})
    return table

def canonical_map(arm, c: dict) -> dict:
    """Source bone name -> contract name: aliases for limbs and fingers, hierarchy for the spine chain."""
    table = aliases(c)
    bones = arm.data.bones
    mapping: dict[str, str] = {}
    for b in bones:
        target = table.get(norm(b.name))
        if target and not norm(b.name).startswith("spine"):
            mapping[b.name] = target
    hips = next((b for b in bones if mapping.get(b.name) == "Hips"), None)
    head = next((b for b in bones if mapping.get(b.name) == "Head"), None)
    if not hips or not head:
        fail("could not find Hips and Head", bones=[b.name for b in bones])
    neck = next((b for b in bones if mapping.get(b.name) == "Neck"), None) or head.parent
    mapping[neck.name] = "Neck"
    chain = []
    b = neck.parent
    while b and b != hips:
        chain.insert(0, b)
        b = b.parent
    names = {1: ["Spine"], 2: ["Spine", "Chest"], 3: ["Spine", "Chest", "UpperChest"]}.get(len(chain))
    if names is None:
        names = ["Spine"] + [f"Spine{i}" for i in range(2, len(chain) - 1)] + ["Chest", "UpperChest"]
        warn(f"spine has {len(chain)} bones; extra ones keep Spine<n> names")
    for bone, name in zip(chain, names):
        mapping[bone.name] = name
    if len(set(mapping.values())) != len(mapping):
        fail("two bones map to the same canonical name", mapping=mapping)
    return mapping
