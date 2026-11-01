# Shared helpers for the headless Blender rig scripts.
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    """Import a single-mesh GLB, apply transforms, stand it on the ground centred at the origin."""
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    mesh = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = np.empty(len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(axis=0), co.max(axis=0)
    shift = Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    mesh.data.transform(Matrix.Translation(shift))
    mesh.name = "Body"
    return mesh


def world_rot(rig, bone, axis, degrees):
    """Pose quaternion for `bone` that rotates it about an armature-space axis."""
    rest = rig.data.bones[bone].matrix_local.to_quaternion()
    q = Quaternion(Vector(axis), np.radians(degrees))
    return rest.inverted() @ q @ rest
