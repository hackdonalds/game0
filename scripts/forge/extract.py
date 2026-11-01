# Cut the parts a generated body has but the family base doesn't (feathers, crests, horns, fused clothes) out of
# the generated mesh, keeping their original UVs and texture. A face is kept when it lies further than
# --min-distance from the people's body surface (the base with the people's key on) and, if --regions is given,
# when its nearest body point is in one of those regions. The result is a static mesh in body space, ready for
# fit_gear (use --rest-keys {"people_<id>": 1}).
#   bun run art:forge extract --source <people.canon.glb> --body <people.body.glb> --out <part.glb>
#     [--regions ["upperarm_l", ...]] [--min-distance 0.015] [--grow 1] [--name mantle]
#     [--skin-regions ["shin_l", "shin_r"]] [--skin-tolerance 0.08] [--min-island 24] [--budget gear] [--close 2]
#     [--corner-distance 0.5]   # every face corner must be at least this fraction of --min-distance off the body
#     [--keep-near ["#242d3f"]] [--drop-near ["#242d3f"]] [--colour-tolerance 0.12] [--not-face true]
# --keep-near keeps only faces painted close to one of the colours (a garment); --drop-near drops them (a crest
# or mantle next to the garment). --not-face drops faces over the face: the base vertices any ARKit expression
# moves (a crest or beard never takes the face it grew from).
# The part is decimated to the contract's triangle budget and its textures downscaled to the texture budget.
# --skin-regions: where the generated body is bare skin; their median painted colour is the skin colour, and
# faces with skin colour at any corner are dropped (a crest without the face under it, shorts without the legs).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, armature_of, contract, done, export, face_colours, fail, load, regions_uv, reset, skinned_meshes, triangles, with_active  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

a = args()
c = contract(a.get("family", "humanoid"))
reset()
body_objects = load(a["body"])
barm = armature_of(body_objects)
body = max(skinned_meshes(body_objects, barm), key=lambda m: len(m.data.vertices))
barm.data.pose_position = "REST"
ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())  # people key at its default (1)
mesh = ev.to_mesh()
mesh.calc_loop_triangles()
bverts = [body.matrix_world @ v.co for v in mesh.vertices]
btris = [tuple(t.vertices) for t in mesh.loop_triangles]
bvh = BVHTree.FromPolygons(bverts, btris)
uv = regions_uv(body)
vregion = {}
for loop in body.data.loops:
    vregion[loop.vertex_index] = int(uv.data[loop.index].uv[0] * 32)
ev.to_mesh_clear()
wanted = {c["regions"].index(r) for r in a["regions"]} if a.get("regions") else None
face_vertices = set()
if a.get("not-face") and body.data.shape_keys:
    kb = body.data.shape_keys.key_blocks
    basis = [v.co.copy() for v in kb[0].data]
    for name in c["sliders"].get("expressions", []):
        if name in kb:
            for i, v in enumerate(kb[name].data):
                if (v.co - basis[i]).length > 0.001:
                    face_vertices.add(i)
min_d = a.get("min-distance", 0.015)

source_objects = load(a["source"])
sarm = armature_of(source_objects)
sarm.data.pose_position = "REST"
parts = skinned_meshes(source_objects, sarm) or [o for o in source_objects if o.type == "MESH"]
src = parts[0]
for o in source_objects:
    if o is not src:
        bpy.data.objects.remove(o)
src.modifiers.clear()
src.vertex_groups.clear()
mw = src.matrix_world.copy()
src.parent = None
src.matrix_world = mw

colours = face_colours(src)
corner_colours = face_colours(src, samples=True)
bm = bmesh.new()
bm.from_mesh(src.data)
bm.transform(src.matrix_world)
bm.faces.ensure_lookup_table()
nearest = {f.index: bvh.find_nearest(f.calc_center_median()) for f in bm.faces}
skin = None
if a.get("skin-regions"):
    bare = {c["regions"].index(r) for r in a["skin-regions"]}
    samples = [colours[i] for i, (loc, _, tri, d) in nearest.items() if loc is not None and d < 0.02 and vregion.get(btris[tri][0]) in bare]
    if not samples:
        fail("no faces found in --skin-regions to sample the skin colour")
    skin = np.median(np.array(samples), axis=0)
tol = a.get("skin-tolerance", 0.08)
hexes = lambda hs: np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)] for h in hs], dtype=np.float32) if hs else None  # noqa: E731
keep_near, drop_near = hexes(a.get("keep-near")), hexes(a.get("drop-near"))
ctol = a.get("colour-tolerance", 0.12)
keep = set()
corner_d = a.get("corner-distance", 0.5)
vdist = {}
for f in bm.faces:
    loc, _, tri, d = nearest[f.index]
    if loc is None or d < min_d:
        continue
    # Every corner must stand off the body too: big generated triangles that span from a hem onto the skin
    # read as cloth by their centre and colour, and hang down as spikes
    if corner_d and any(vdist.setdefault(v.index, bvh.find_nearest(v.co)[3]) < min_d * corner_d for v in f.verts):
        continue
    if wanted is not None and vregion.get(btris[tri][0]) not in wanted:
        continue
    if face_vertices and any(i in face_vertices for i in btris[tri]):
        continue
    if keep_near is not None and np.linalg.norm(keep_near - colours[f.index], axis=1).min() > ctol:
        continue
    if drop_near is not None and np.linalg.norm(drop_near - colours[f.index], axis=1).min() < ctol:
        continue
    # Skin anywhere on the face (a corner or the centre) drops it: big triangles straddle hems and skin
    if skin is not None and np.linalg.norm(corner_colours[f.index] - skin, axis=1).min() < tol:
        continue
    keep.add(f)
# Grow the selection a ring or two so parts don't end in a ragged edge
for _ in range(int(a.get("grow", 1))):
    ring = {g for f in keep for e in f.edges for g in e.link_faces}
    if wanted is not None:
        ring = {f for f in ring if vregion.get(btris[nearest[f.index][2]][0]) in wanted}
    if skin is not None:
        ring = {f for f in ring if np.linalg.norm(corner_colours[f.index] - skin, axis=1).min() >= tol}
    if keep_near is not None:
        ring = {f for f in ring if np.linalg.norm(keep_near - colours[f.index], axis=1).min() <= ctol}
    if drop_near is not None:
        ring = {f for f in ring if np.linalg.norm(drop_near - colours[f.index], axis=1).min() >= ctol}
    keep |= ring
if not keep:
    fail("nothing left after the distance and region filters; lower --min-distance or widen --regions")
# Close small holes (a fly or seam painted near skin colour): grow the selection, then shrink it back.
# Neighbours are found through shared vertex positions, since generated meshes are split at UV seams.
by_pos = {}
for f in bm.faces:
    for v in f.verts:
        by_pos.setdefault(tuple(round(x, 5) for x in v.co), set()).add(f)
neighbours = {f: set().union(*(by_pos[tuple(round(x, 5) for x in v.co)] for v in f.verts)) - {f} for f in bm.faces}
for _ in range(int(a.get("close", 2))):
    grown = keep | {g for f in keep for g in neighbours[f]}
    keep = {f for f in grown if f in keep or neighbours[f] <= grown}
# Drop small disconnected islands (stray fragments of skin or seams). Generated meshes are split at UV seams,
# so faces connect through shared vertex positions, not shared vertices.
parent = {f: f for f in keep}


def root(f):
    while parent[f] is not f:
        parent[f] = parent[parent[f]]
        f = parent[f]
    return f


by_position = {}
for f in keep:
    for v in f.verts:
        key = tuple(round(x, 5) for x in v.co)
        other = by_position.setdefault(key, f)
        ra, rb = root(f), root(other)
        if ra is not rb:
            parent[ra] = rb
groups = {}
for f in keep:
    groups.setdefault(root(f), []).append(f)
islands = list(groups.values())
small = [i for i in islands if len(i) < int(a.get("min-island", 24))]
for island in small:
    keep -= set(island)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES_ONLY")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(src.data)
bm.free()
src.matrix_world.identity()
budget = c["budgets"][a.get("budget", "gear")]
before = triangles(src)
if before > budget["triangles"]:
    dec = src.modifiers.new("budget", "DECIMATE")
    dec.ratio = budget["triangles"] / before * 0.97
    with with_active(src):
        bpy.ops.object.modifier_apply(modifier=dec.name)
for img in bpy.data.images:
    if img.size[0] and max(img.size) > budget["texture"]:
        f = budget["texture"] / max(img.size)
        img.scale(int(img.size[0] * f), int(img.size[1] * f))
src.name = a.get("name", Path(a["out"]).stem.split(".")[0])
out = export(a["out"], [src])
done(out=out, faceVertices=len(face_vertices), triangles=triangles(src), trianglesBefore=before, faces=len(src.data.polygons), islands=len(islands) - len(small), droppedIslands=len(small),
     skinColour=None if skin is None else "#%02x%02x%02x" % tuple(int(x * 255) for x in np.clip(skin, 0, 1)))
