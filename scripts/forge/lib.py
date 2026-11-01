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
    bpy.context.scene.render.fps = 30  # the forge frame rate: glTF times convert to frames at this rate on import


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


def dominant_groups(obj, only: set | None = None) -> list:
    """Index of the heaviest vertex group per vertex (-1 when unweighted), optionally among `only` names."""
    names = {g.index: g.name for g in obj.vertex_groups}
    out = []
    for v in obj.data.vertices:
        best = max((g for g in v.groups if only is None or names[g.group] in only), key=lambda g: g.weight, default=None)
        out.append(best.group if best and best.weight > 0 else -1)
    return out


def bone_vertices(obj, bones: set) -> list:
    """World positions of vertices whose heaviest group is one of `bones`."""
    names = {g.index: g.name for g in obj.vertex_groups}
    arm = obj.find_armature()
    dom = dominant_groups(obj, {b.name for b in arm.data.bones if b.use_deform} if arm else None)
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



def albedo_image(material):
    """The image feeding a material's Base Color, if any."""
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            link = next(iter(node.inputs["Base Color"].links), None)
            n = link.from_node if link else None
            while n and n.type != "TEX_IMAGE" and n.inputs and n.inputs[0].links:
                n = n.inputs[0].links[0].from_node
            return n.image if n and n.type == "TEX_IMAGE" else None
    return None


def face_colours(obj, samples: bool = False):
    """Mean painted albedo per polygon (corners and centre sampled from the base colour texture); with
    samples=True, every sample per polygon (corners first, centre last)."""
    import numpy as np
    uv = obj.data.uv_layers[0].data
    cache = {}
    out = np.zeros((len(obj.data.polygons), 3), dtype=np.float32)
    every = []
    for p in obj.data.polygons:
        mat = obj.data.materials[p.material_index] if obj.data.materials else None
        if mat not in cache:
            img = albedo_image(mat)
            cache[mat] = (np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], -1)[..., :3], img.size) if img else None
        data = cache[mat]
        if data is None:
            out[p.index] = mat.diffuse_color[:3] if mat else (0.8, 0.8, 0.8)
            every.append(out[p.index][None])
            continue
        px, (w, h) = data
        pts = np.array([uv[li].uv[:] for li in p.loop_indices], dtype=np.float32)
        pts = np.vstack([pts, pts.mean(0)]) % 1.0
        cols = px[(pts[:, 1] * (h - 1)).astype(int), (pts[:, 0] * (w - 1)).astype(int)]
        out[p.index] = cols.mean(0)
        every.append(cols)
    return every if samples else out


def socket_points(arm, meshes, c: dict) -> dict:
    """Where each contract socket goes on these meshes as they evaluate now (shape keys included): the centroid
    of the vertices dominated by the socket's `from` bones, then optionally a ray to the surface plus an offset."""
    deps = bpy.context.evaluated_depsgraph_get()
    deform = {b.name for b in arm.data.bones if b.use_deform}
    points = {}
    for sk in c["sockets"]:
        source = {n for n in sk["from"] if n in arm.data.bones}
        pts = []
        for m in meshes:
            names = {g.index: g.name for g in m.vertex_groups}
            ev = m.evaluated_get(deps).to_mesh()
            for v, src_v in zip(ev.vertices, m.data.vertices):
                best = max((g for g in src_v.groups if names[g.group] in deform), key=lambda g: g.weight, default=None)
                if best and names[best.group] in source:
                    pts.append(m.matrix_world @ v.co)
            m.evaluated_get(deps).to_mesh_clear()
        if not pts:
            warn(f"{sk['name']}: no vertices for {sorted(source)}; placed at the bone head")
            bone = next(n for n in sk["bone"].split("|") if n in arm.data.bones)
            points[sk["name"]] = arm.matrix_world @ arm.data.bones[bone].head_local
            continue
        p = sum(pts, Vector()) / len(pts)
        if "ray" in sk:
            d = DIRS[sk["ray"]]
            hits = []
            for m in meshes:
                inv = m.matrix_world.inverted()
                ok, loc, *_ = m.ray_cast(inv @ p, (inv.to_3x3() @ d).normalized(), depsgraph=deps)
                if ok:
                    hits.append(m.matrix_world @ loc)
            if hits:
                p = min(hits, key=lambda h: (h - p).length) + d * sk.get("offset", 0)
            else:
                warn(f"{sk['name']}: ray {sk['ray']} missed the body; left at the centroid")
        points[sk["name"]] = p
    return points


def action_fcurves(action):
    """F-curves of an action, for both legacy and layered (Blender 4.4+/5) actions."""
    if hasattr(action, "layers") and action.layers:
        return [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    return list(getattr(action, "fcurves", []))


def linear_keys(action):
    """Linear interpolation on every key. Bezier keys export as glTF CUBICSPLINE, whose tangents overshoot
    between keys: Blender renders on whole frames look right while a 60 fps engine shakes."""
    for fc in action_fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def glb_json(file: str) -> dict:
    """The JSON chunk of a GLB, to check what an exporter actually wrote."""
    import struct
    data = Path(path(file)).read_bytes()
    length, kind = struct.unpack_from("<II", data, 12)
    return json.loads(data[20:20 + length])


def rasterise(tri_uv, colours, size: int, grow: int = 4):
    """Paint each triangle's colour into a size x size UV-space image (row 0 = v 0, Blender's image order), then
    grow the painted islands by `grow` pixels so seams don't leave gaps."""
    import numpy as np
    img = np.zeros((size, size, 3), dtype=np.float32)
    filled = np.zeros((size, size), dtype=bool)
    for tri, col in zip(np.asarray(tri_uv) * (size - 1), colours):
        lo = np.floor(tri.min(0)).astype(int).clip(0, size - 1)
        hi = np.ceil(tri.max(0)).astype(int).clip(0, size - 1)
        xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        p = np.stack([xs.ravel() + 0.5, ys.ravel() + 0.5], 1)
        a0, b0, c0 = tri
        v0, v1, v2 = c0 - a0, b0 - a0, p - a0
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-9:
            continue
        u = (v2[:, 0] * v1[1] - v1[0] * v2[:, 1]) / den
        v = (v0[0] * v2[:, 1] - v2[:, 0] * v0[1]) / den
        inside = (u >= -0.01) & (v >= -0.01) & (u + v <= 1.02)
        img[ys.ravel()[inside], xs.ravel()[inside]] = col
        filled[ys.ravel()[inside], xs.ravel()[inside]] = True
    for _ in range(grow):
        out = img.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            shifted = np.roll(np.roll(img, dy, 0), dx, 1)
            sf = np.roll(np.roll(filled, dy, 0), dx, 1)
            take = ~filled & sf
            out[take] = shifted[take]
            filled = filled | take
        img = out
    return img


def save_png(img, file) -> str:
    """Write an RGB float image (rows bottom-up) as a non-colour PNG."""
    import numpy as np
    h, w = img.shape[:2]
    im = bpy.data.images.new(Path(file).stem, w, h, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels = np.concatenate([img, np.ones((h, w, 1), dtype=np.float32)], 2).ravel().tolist()
    im.filepath_raw = str(file)
    im.file_format = "PNG"
    im.save()
    return str(file)


def pose_offsets(c: dict, people: str | None, keys: dict | None = None) -> dict:
    """Additive pose offsets from the contract (the people's fixed `pose` plus `sliderPose` from the current
    shape key values), as {bone: (axis, radians)} in bone-local space. Bones point up at rest with roll 0, so
    local Z is the character's front (back) axis in Blender."""
    import math
    out = {}
    amounts = dict(c.get("peoples", {}).get(people or "", {}).get("pose", {}) or {})
    for name, rule in (c.get("sliderPose") or {}).items():
        amounts[name] = amounts.get(name, 0) + rule.get("base", 0) + sum(w * (keys or {}).get(k, 0) for k, w in rule["per"].items())
    for name, deg in amounts.items():
        spec = c.get("poseOffsets", {}).get(name)
        if not spec:
            continue
        for bone, sign in spec["bones"].items():
            out[bone] = ("Z", math.radians(deg) * sign)
    return out


def apply_pose_offsets(arm, offsets: dict):
    """Rotate pose bones by their offsets after the clip has been evaluated (call after frame_set). The offset is
    applied in the parent's frame, after the clip's rotation, so a clip's twist can't turn it inwards."""
    from mathutils import Quaternion
    for bone, (axis, angle) in offsets.items():
        pb = arm.pose.bones.get(bone)
        if pb:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis], angle) @ pb.rotation_quaternion
    bpy.context.view_layer.update()