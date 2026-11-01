# Bake a generated body's painted skin onto a people's body built on the family base (shared UVs), so stone,
# bark or feathered skin carries over. Where the generated body has something standing off the skin (clothes,
# feathers, growths: those become gear), the texels are filled from the surrounding skin instead.
#   bun run art:forge bake_skin --source <people.canon.glb> --body <people.body.glb> --out <people.body.glb>
#     [--parts ["x-crest.glb", "x-mantle.glb", ...]] [--size 2048] [--ray 0.12]
# --parts: the pieces `extract` cut from the same generated body; their faces are not skin. Without it, faces
# further than --off-skin from the people's body count as not skin (only reliable where the wrap shrinkwrapped).
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, done, export, face_colours, load, path, reset, skinned_meshes  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

a = args()
size = int(a.get("size", 2048))
reset()
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1

body_objects = load(a["body"])
arm = armature_of(body_objects)
body = max(skinned_meshes(body_objects, arm), key=lambda m: len(m.data.vertices))
arm.data.pose_position = "REST"
src_objects = load(a["source"])
sarm = next((o for o in src_objects if o.type == "ARMATURE"), None)
if sarm:
    sarm.data.pose_position = "REST"
source = max((o for o in src_objects if o.type == "MESH"), key=lambda m: len(m.data.vertices))

# Which source faces stand off the people's skin (clothes, feathers, growths)
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
me = ev.to_mesh()
me.calc_loop_triangles()
bvh = BVHTree.FromPolygons([body.matrix_world @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
ev.to_mesh_clear()
sev = source.evaluated_get(deps).to_mesh()
centres = [source.matrix_world @ p.center for p in sev.polygons]
source.evaluated_get(deps).to_mesh_clear()
if a.get("parts"):
    # Faces that became parts: their centres lie on an extracted piece (same generated geometry)
    part_bvhs = []
    for file in a["parts"]:
        for o in load(file):
            if o.type == "MESH":
                o.data.calc_loop_triangles()
                part_bvhs.append(BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [tuple(t.vertices) for t in o.data.loop_triangles]))
                bpy.data.objects.remove(o)
            elif o.name in bpy.data.objects:
                bpy.data.objects.remove(o)
    off = np.array([any((b.find_nearest(c)[3] or 1) < 0.001 for b in part_bvhs) for c in centres])
    # Grow from the parts across connected faces that aren't skin-coloured: a garment's faces that lie close to
    # the body (left out of the extracted piece) are still garment, and the growth stops at bare skin
    cols = face_colours(source)
    skin_ref = np.median(cols[~off], axis=0) if (~off).any() else cols.mean(0)
    skin_ref = np.median(cols[~off & (np.linalg.norm(cols - skin_ref, axis=1) < 0.15)], axis=0)
    by_pos = {}
    for p in source.data.polygons:
        for vi in p.vertices:
            by_pos.setdefault(tuple(round(x, 5) for x in source.data.vertices[vi].co), []).append(p.index)
    neighbours = [set() for _ in source.data.polygons]
    for faces in by_pos.values():
        for f in faces:
            neighbours[f].update(faces)
    frontier = list(np.nonzero(off)[0])
    tol = a.get("skin-tolerance", 0.12)
    while frontier:
        nxt = []
        for f in frontier:
            for g in neighbours[f]:
                if not off[g] and np.linalg.norm(cols[g] - skin_ref) > tol:
                    off[g] = True
                    nxt.append(g)
        frontier = nxt
else:
    off = np.array([bvh.find_nearest(c)[3] > a.get("off-skin", 0.006) for c in centres])


def bake(kind: str, image):
    for o in bpy.data.objects:
        o.select_set(False)
    source.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    nodes = body.active_material.node_tree.nodes
    tex = nodes.get("forge_bake") or nodes.new("ShaderNodeTexImage")
    tex.name, tex.image = "forge_bake", image
    nodes.active = tex
    bpy.ops.object.bake(type=kind, pass_filter={"COLOR"} if kind == "DIFFUSE" else set(), use_selected_to_active=True,
                        cage_extrusion=a.get("ray", 0.12) / 2, max_ray_distance=a.get("ray", 0.12), margin=8)
    return np.array(image.pixels[:], dtype=np.float32).reshape(size, size, 4)


mat = bpy.data.materials.new("Skin")
mat.use_nodes = True
body.data.materials.clear()
body.data.materials.append(mat)

# 1. Painted colour
colour = bpy.data.images.new("skin_colour", size, size, alpha=False)
paint = bake("DIFFUSE", colour)

# 2. Where the colour came from something off the skin: bake an emission flag from the same source faces
flag_mat = bpy.data.materials.new("forge_flag")
flag_mat.use_nodes = True
nt = flag_mat.node_tree
nt.nodes.clear()
emit = nt.nodes.new("ShaderNodeEmission")
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "forge_off"
outn = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(attr.outputs["Fac"], emit.inputs["Strength"])
nt.links.new(emit.outputs[0], outn.inputs[0])
fa = source.data.attributes.new("forge_off", "FLOAT", "FACE")
fa.data.foreach_set("value", off.astype(np.float32))
source.data.materials.clear()
source.data.materials.append(flag_mat)
for p in source.data.polygons:
    p.material_index = 0
flag_img = bpy.data.images.new("skin_flag", size, size, alpha=False)
flag = bake("EMIT", flag_img)[..., 0] > 0.5

if a.get("debug"):
    for name, arr in (("paint", paint[..., :3]), ("flag", np.repeat(flag[..., None].astype(np.float32), 3, 2))):
        im = bpy.data.images.new(name, size, size, alpha=False)
        im.pixels = np.concatenate([arr, np.ones((size, size, 1), dtype=np.float32)], 2).ravel().tolist()
        im.filepath_raw = f"{a['debug']}-{name}.png"
        im.file_format = "PNG"
        im.save()

# 3. Fill the flagged texels from the nearest true skin (push-pull), then a soft blend at the edges
rgb = paint[..., :3].copy()
known = ~flag & (paint[..., :3].sum(-1) > 0)  # baked skin; black = no hit (between UV islands)
skin_median = np.median(rgb[known], axis=0) if known.any() else np.array([0.8, 0.7, 0.6])
# Texels far darker than the skin are missed rays or shadowed undersides, not skin: fill them too
lum = rgb @ np.array([0.299, 0.587, 0.114])
dark = lum < 0.45 * float(skin_median @ np.array([0.299, 0.587, 0.114]))
known &= ~dark
flag = flag | dark
filled, have = rgb.copy(), known.copy()
for _ in range(64):
    if have.all():
        break
    acc = np.zeros_like(filled)
    cnt = np.zeros(have.shape, dtype=np.float32)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (2, 0), (-2, 0), (0, 2), (0, -2)):
        acc += np.roll(np.roll(filled * have[..., None], dy, 0), dx, 1)
        cnt += np.roll(np.roll(have.astype(np.float32), dy, 0), dx, 1)
    grow = ~have & (cnt > 0)
    filled[grow] = acc[grow] / cnt[grow][:, None]
    have = have | grow
filled[~have] = skin_median
out_img = bpy.data.images.new(f"{Path(a['out']).stem}_skin", size, size, alpha=False)
out_img.pixels = np.concatenate([filled, np.ones((size, size, 1), dtype=np.float32)], 2).ravel().tolist()
out_img.pack()

# The body material: the baked skin as base colour, nothing else (painterly albedo, toon ramp in the engine)
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
tex = nodes.get("forge_bake")
tex.image = out_img
mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 1.0
for o in list(bpy.data.objects):
    if o not in (body, arm):
        bpy.data.objects.remove(o)
meta = json.loads(body.get("forge", "{}"))
meta["skin"] = {"source": a["source"], "size": size, "filledFraction": round(float(flag.mean()), 3)}
body["forge"] = json.dumps(meta)
out = export(a["out"], [arm, body], key_values={meta["signature"]: 1.0} if meta.get("signature") else None)
done(out=out, size=size, skinMedian="#%02x%02x%02x" % tuple(int(x * 255) for x in np.clip(skin_median, 0, 1)),
     offSkinFaces=int(off.sum()), filledTexels=round(float(flag.mean()), 3))
