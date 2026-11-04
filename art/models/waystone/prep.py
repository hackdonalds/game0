# Prepare a Meshy GLB for the Waystone demo: real-world scale, centred, base (or top) at y=0, optional glow split.
# blender -b --factory-startup -P art/models/waystone/prep.py -- <src.glb> <out.glb> <axis:height|length|width> <metres>
#         [--anchor base|top] [--glow off|lit|all] [--hue teal|spark] [--yaw <deg>] [--faces <max>] [--tex <px>]
# --glow off: no split. lit: faces whose texture is teal go to material "glow" (emissive map, factor 0, so code lights it).
# all/shine: same split but the glow material ships lit (emissive factor 1), e.g. the glimmer shard.
import bpy, bmesh, sys, math, colorsys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
src, out, axis, size = argv[0], argv[1], argv[2], float(argv[3])
opts = {argv[i][2:]: argv[i + 1] for i in range(4, len(argv) - 1, 2)}
anchor = opts.get("anchor", "base")
glow = opts.get("glow", "off")
yaw = float(opts.get("yaw", 0))
max_faces = int(opts.get("faces", 0))
tex_px = int(opts.get("tex", 0))
hue = opts.get("hue", "teal")  # teal: glimmer inlay; spark: white-blue lightning

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
# drop parents/empties but keep the world transform
mw = obj.matrix_world.copy()
obj.parent = None
obj.matrix_world = mw
for o in list(bpy.context.scene.objects):
    if o is not obj:
        bpy.data.objects.remove(o)
obj.rotation_mode = "XYZ"
obj.rotation_euler.z += math.radians(yaw)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

if max_faces and len(obj.data.polygons) > max_faces:
    m = obj.modifiers.new("dec", "DECIMATE")
    m.ratio = max_faces / len(obj.data.polygons)
    bpy.ops.object.modifier_apply(modifier=m.name)

# scale to real metres (Blender Z is glTF +Y)
co = [v.co for v in obj.data.vertices]
lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
dim = hi - lo
cur = dim.z if axis == "height" else max(dim.x, dim.y)
s = size / cur
centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z if anchor == "top" else lo.z))
obj.data.transform(Matrix.Translation(-centre))
obj.data.transform(Matrix.Scale(s, 4))
obj.data.update()

mat = obj.data.materials[0]
mat.name = "main"
img = None
for n in mat.node_tree.nodes:
    if n.type == "TEX_IMAGE" and n.image:
        img = n.image
        break
if tex_px and img and max(img.size) > tex_px:
    img.scale(tex_px, tex_px)

stats = {}
if glow != "off" and img:
    w, h = img.size
    px = list(img.pixels)  # RGBA floats, bottom-up

    def teal(u, v):
        x = min(w - 1, max(0, int((u % 1) * w)))
        y = min(h - 1, max(0, int((v % 1) * h)))
        i = (y * w + x) * 4
        r, g, b = px[i], px[i + 1], px[i + 2]
        hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
        if hue == "spark":
            return 0.53 <= hh <= 0.72 and ss >= 0.38 and vv >= 0.6
        return 0.40 <= hh <= 0.55 and ss >= 0.30 and vv >= 0.35

    gm = mat.copy()
    gm.name = "glow"
    obj.data.materials.append(gm)
    gi = len(obj.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uvl = bm.loops.layers.uv.active
    n = 0
    for f in bm.faces:
        uvs = [l[uvl].uv for l in f.loops]
        c = sum(uvs, Vector((0, 0))) / len(uvs)
        votes = sum(teal(p.x, p.y) for p in uvs + [c])
        if votes >= 1:
            f.material_index = gi
            n += 1
    bm.to_mesh(obj.data)
    bm.free()
    stats["glowFaces"] = n
    # emissive = base colour texture; factor 0 (code lights it) or 1 (ships lit)
    bsdf = next(nd for nd in gm.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    tex = next(nd for nd in gm.node_tree.nodes if nd.type == "TEX_IMAGE")
    # emissive map = base colour with every non-teal pixel black, so only the inlay lights up
    import numpy as np
    a = np.array(px).reshape(h, w, 4)
    mx, mn = a[..., :3].max(-1), a[..., :3].min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
    if hue == "spark":
        mask = (mx >= 0.6) & (sat >= 0.38) & (b_ >= r_ * 1.4) & (b_ >= g_)
    else:
        mask = (sat >= 0.30) & (mx >= 0.35) & (g_ >= r_ * 1.25) & (b_ >= r_ * 1.1)
    em = a.copy()
    em[..., :3] *= mask[..., None]
    em[..., 3] = 1
    mimg = bpy.data.images.new("glow_mask", w, h)
    mimg.pixels = em.ravel()
    mimg.file_format = "PNG"
    mimg.pack()
    mtex = gm.node_tree.nodes.new("ShaderNodeTexImage")
    mtex.image = mimg
    uvsrc = tex.inputs["Vector"].links[0].from_socket if tex.inputs["Vector"].links else None
    if uvsrc:
        gm.node_tree.links.new(uvsrc, mtex.inputs["Vector"])
    gm.node_tree.links.new(mtex.outputs["Color"], bsdf.inputs["Emission Color"])
    stats["maskPixels"] = round(float(mask.mean()), 3)
    bsdf.inputs["Emission Strength"].default_value = 1.0 if glow == "all" else 0.0

print("PREP", {"faces": len(obj.data.polygons), "scale": s, "dims": tuple(round(d * s, 2) for d in dim), **stats})
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=False, export_yup=True, export_apply=True)
