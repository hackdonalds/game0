# Debug renders of a rigged .blend: front and side views with joints drawn on top.
# Usage: blender -b --factory-startup -P scripts/rig/render.py -- rig.blend out_dir [action frame ...]
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def setup(out_dir):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.film_transparent = True
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.3
    scene.camera = cam
    return scene, cam


def markers(rig):
    mat = bpy.data.materials.new("Marker")
    mat.diffuse_color = (1, 0.1, 0.1, 1)
    out = []
    for pb in rig.pose.bones:
        for end in ("head", "tail"):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.018, segments=8, ring_count=6)
            s = bpy.context.object
            s.data.materials.append(mat)
            s.color = (1, 0.1, 0.1, 1)
            out.append((s, pb, end))
    return out


def place(ms, rig, offset):
    for s, pb, end in ms:
        s.location = rig.matrix_world @ getattr(pb, end) + offset


def render_views(scene, cam, rig, ms, out, tag):
    views = {"front": ((0, -5, 0.95), (90, 0, 0), Vector((0, -1.5, 0))),
             "side": ((5, 0, 0.95), (90, 0, 90), Vector((1.5, 0, 0)))}
    for name, (loc, rot, off) in views.items():
        cam.location = loc
        cam.rotation_euler = [v * 3.14159 / 180 for v in rot]
        place(ms, rig, off)
        scene.render.filepath = str(out / f"{tag}-{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    scene, cam = setup(out)
    rig = bpy.data.objects["Rig"]
    ms = markers(rig)
    shots = argv[2:]
    if not shots:
        render_views(scene, cam, rig, ms, out, "rest")
    for action, frame in zip(shots[::2], shots[1::2]):
        rig.animation_data_create()
        rig.animation_data.use_nla = False
        rig.animation_data.action = bpy.data.actions[action]
        scene.frame_set(int(frame))
        bpy.context.view_layer.update()
        render_views(scene, cam, rig, ms, out, f"{action}-{frame}")


main()
