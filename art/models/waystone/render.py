# Review render of a GLB: four three-quarter views (every 90 degrees) on one 1024 px sheet, textured, flat studio light.
# blender -b --factory-startup -P art/models/waystone/render.py -- <model.glb> <out.png>
import bpy, sys, math, os, tempfile
import numpy as np
from mathutils import Vector

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
for m in bpy.data.materials:  # Workbench shows the active image node: make it the base colour, not the glow mask
    if m.use_nodes:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b and b.inputs["Base Color"].links:
            m.node_tree.nodes.active = b.inputs["Base Color"].links[0].from_node
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x = sc.render.resolution_y = 512
sc.world = bpy.data.worlds.new("w")
sc.display.shading.background_type = "VIEWPORT"
sc.display.shading.background_color = (0.75, 0.75, 0.75)
pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c, r = (lo + hi) / 2, (hi - lo).length / 2
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
d = r / math.sin(math.radians(18)) * 0.8
tiles = []
tmp = tempfile.mkdtemp()
for i, a in enumerate([-30, 60, 150, 240]):
    t = math.radians(a)
    cam.location = c + Vector((math.sin(t) * d * 0.94, -math.cos(t) * d * 0.94, d * 0.34))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(tmp, f"{i}.png")
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(sc.render.filepath)
    tiles.append(np.array(im.pixels[:]).reshape(512, 512, 4))
sheet = np.zeros((1024, 1024, 4))
sheet[512:, :512], sheet[512:, 512:], sheet[:512, :512], sheet[:512, 512:] = tiles
img = bpy.data.images.new("sheet", 1024, 1024, alpha=True)
img.pixels = sheet.ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("dims", tuple(round(x, 2) for x in hi - lo), "min", tuple(round(x, 2) for x in lo))
