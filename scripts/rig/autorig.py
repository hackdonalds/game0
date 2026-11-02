# Rig a static A-pose humanoid GLB (Meshy output) headless in Blender.
# Usage: blender -b --factory-startup -P scripts/rig/autorig.py -- in.glb out.blend [--check]
# Always writes out.check.json (rig-readiness report). With --check it saves the skeleton without skinning.
# Finds joints from the mesh shape, builds a game skeleton, and skins it by
# bone-heat weighting a watertight voxel proxy, then copying weights to the real mesh.
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from lib import import_glb, reset_scene  # noqa: E402


def mesh_points(obj, n=400_000):
    """Evenly sample the surface: Meshy meshes have big faces, so vertices alone leave holes."""
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    a, b, c = (co[tri.reshape(-1, 3)[:, i]] for i in range(3))
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(0)
    pick = rng.choice(len(a), n, p=area / area.sum())
    u, v = rng.random((2, n, 1))
    flip = (u + v) > 1
    u, v = np.where(flip, 1 - u, u), np.where(flip, 1 - v, v)
    return a[pick] + u * (b[pick] - a[pick]) + v * (c[pick] - a[pick])


def clusters(values, gap):
    """Split sorted 1D values into runs separated by more than `gap`."""
    v = np.sort(values)
    if len(v) == 0:
        return []
    cuts = np.where(np.diff(v) > gap)[0]
    return [(r[0], r[-1]) for r in np.split(v, cuts + 1)]


def slab(P, z, h):
    return P[np.abs(P[:, 2] - z) < h]


def find_landmarks(P):
    H = P[:, 2].max()
    thin = 0.006 * H
    gap = 0.012 * H

    def split(z):
        """x-clusters of a thin horizontal slab."""
        return clusters(slab(P, z, thin)[:, 0], gap)

    # Crotch: scan up the legs until the gap between them closes
    crotch = 0.3 * H
    for z in np.arange(0.3 * H, 0.65 * H, 0.004 * H):
        cs = [c for c in split(z) if c[1] > -0.2 * H and c[0] < 0.2 * H]
        if not (any(hi < 0 for _, hi in cs) and any(lo > 0 for lo, _ in cs)):
            break
        crotch = z

    # Armpit: scan up from the waist until the arms stay merged with the torso
    armpit_z, torso_half, merged = 0.68 * H, 0.12 * H, 0
    arm_pts = {1: [], -1: []}
    for z in np.arange(crotch + 0.1 * H, 0.9 * H, 0.004 * H):
        cs = split(z)
        mid = [c for c in cs if c[0] < 0 < c[1]]
        outer = {sgn: [c for c in cs if c[0] * sgn > 0 and c[1] * sgn > 0 and c not in mid] for sgn in (1, -1)}
        if mid and outer[1] and outer[-1]:
            armpit_z, torso_half, merged = z, min(-mid[0][0], mid[0][1]), 0
            for sgn in (1, -1):
                c = min(outer[sgn], key=lambda c: abs(c[0] + c[1]))  # innermost: the arm
                arm_pts[sgn].append(((c[0] + c[1]) / 2, z))
        elif (merged := merged + 1) > 6:
            break

    def shoulder_x(sgn, z):
        """Extend the arm's centre line (fitted below the armpit) up to height z."""
        pts = np.array(arm_pts[sgn][-25:])
        if len(pts) < 4:
            return sgn * torso_half
        k, b = np.polyfit(pts[:, 1], pts[:, 0], 1)
        return k * z + b

    sh_z = armpit_z + 0.065 * H
    neck_z = sh_z + 0.06 * H

    def centre_y(z, x0, x1):
        s = slab(P, z, 2 * thin)
        s = s[(s[:, 0] > x0) & (s[:, 0] < x1)]
        return float(np.percentile(s[:, 1], [2, 98]).mean()) if len(s) else 0.0

    def axis_centroid(a, b, t, radius):
        """Centroid of the mesh cross-section at fraction t along a->b."""
        d = b - a
        L = np.linalg.norm(d)
        d = d / L
        rel = P - a
        along = rel @ d
        perp = np.linalg.norm(rel - np.outer(along, d), axis=1)
        sel = P[(np.abs(along - t * L) < 0.015 * H) & (perp < radius)]
        return sel.mean(axis=0) if len(sel) else a + d * t * L

    notes = {"armpit_samples": min(len(arm_pts[1]), len(arm_pts[-1])), "crotch": crotch / H, "armpit": armpit_z / H}
    def wrist(sh, tip):
        """Walking back from the fingertips, the first narrowing of the arm: the hand is wide, the
        wrist narrow, the forearm wider again (hands vary a lot in length, so no fixed fraction)."""
        d = tip - sh
        L = np.linalg.norm(d)
        d = d / L
        rel = P - sh
        along = rel @ d
        perp = np.linalg.norm(rel - np.outer(along, d), axis=1)
        ts = np.arange(0.92, 0.5, -0.01)
        widths = []
        for t in ts:
            sel = (np.abs(along - t * L) < 0.006 * H) & (perp < 0.08 * H)
            widths.append(np.percentile(perp[sel], 90) if sel.sum() > 20 else np.inf)
        w = np.convolve(np.nan_to_num(widths, posinf=1.0), np.ones(5) / 5, mode="same")
        start = int(np.argmax(w[: len(w) // 2]))  # widest part of the hand
        for i in range(start + 1, len(w) - 3):
            if w[i] <= w[i - 1] and w[i] < w[i + 1] and w[i] < w[i + 3]:
                return axis_centroid(sh, tip, ts[i], 0.05 * H)
        return axis_centroid(sh, tip, 0.77, 0.05 * H)

    J = {}
    J["hips"] = np.array([0, centre_y(crotch + 0.05 * H, -0.1 * H, 0.1 * H), crotch + 0.05 * H])
    spine_z = J["hips"][2] + (neck_z - J["hips"][2]) * 0.3
    chest_z = J["hips"][2] + (neck_z - J["hips"][2]) * 0.62
    J["spine"] = np.array([0, centre_y(spine_z, -0.1 * H, 0.1 * H), spine_z])
    J["chest"] = np.array([0, centre_y(chest_z, -0.1 * H, 0.1 * H), chest_z])
    J["neck"] = np.array([0, centre_y(neck_z - 0.03 * H, -0.06 * H, 0.06 * H), neck_z - 0.03 * H])
    J["head"] = np.array([0, centre_y(neck_z + 0.02 * H, -0.06 * H, 0.06 * H), neck_z + 0.02 * H])
    J["head_end"] = np.array([0, J["head"][1], H])

    for side, sgn in (("L", 1), ("R", -1)):
        sh = np.array([shoulder_x(sgn, sh_z), centre_y(sh_z, -0.1 * H, 0.1 * H), sh_z])
        J[f"clavicle.{side}"] = np.array([sgn * 0.04 * H, sh[1], sh_z + 0.01 * H])
        arm = P[(P[:, 0] * sgn > torso_half) & (P[:, 2] > 0.3 * H)]  # above the knees, or slim bodies' feet win
        tip = arm[np.argmax(arm[:, 0] * sgn - 0.5 * arm[:, 2])]  # outermost, lowest fingertip
        J[f"upper_arm.{side}"] = sh
        J[f"forearm.{side}"] = axis_centroid(sh, tip, 0.44, 0.07 * H)
        J[f"hand.{side}"] = wrist(sh, tip)
        J[f"hand_end.{side}"] = tip
        fingers, notes[f"hands.{side}"] = find_fingers(P, J, side)
        J.update(fingers)

        legs = P[(P[:, 0] * sgn > 0.01 * H) & (P[:, 0] * sgn < 0.3 * H)]
        ankle_z = 0.055 * H
        knee_z = ankle_z + 0.5 * (crotch + 0.02 * H - ankle_z)
        k = slab(legs, knee_z, 2 * thin)
        a = slab(legs, ankle_z + 0.03 * H, 2 * thin)
        J[f"thigh.{side}"] = np.array([np.median(k[:, 0]) * 0.9, J["hips"][1], crotch + 0.02 * H])
        J[f"shin.{side}"] = np.array([np.median(k[:, 0]), np.median(k[:, 1]), knee_z])
        ankle = np.array([np.median(a[:, 0]), np.median(a[:, 1]), ankle_z])
        J[f"foot.{side}"] = ankle
        sole = legs[legs[:, 2] < 0.03 * H]
        fwd = sole[np.argmin(sole[:, 1])]  # character faces -Y
        J[f"toe.{side}"] = ankle + (np.array([fwd[0], fwd[1], 0.02 * H]) - ankle) * 0.65
        J[f"toe_end.{side}"] = np.array([fwd[0], fwd[1], 0.02 * H])
    return J, H, notes


def check(J, H, notes):
    """Rig-readiness report: [(level, message)] with level "fail" or "warn"."""
    issues = []
    if notes["armpit_samples"] < 4:
        issues.append(("fail", "arms touch the torso: no clear gap under the arms"))
    if not 0.33 <= notes["crotch"] <= 0.55:
        issues.append(("fail", f"no clear gap between the legs (crotch at {notes['crotch']:.2f} of height)"))
    for side, sgn in (("L", 1), ("R", -1)):
        arm = J[f"hand.{side}"] - J[f"upper_arm.{side}"]
        angle = np.degrees(np.arctan2(abs(arm[0]), -arm[2]))
        if not 25 <= angle <= 65:
            issues.append(("fail", f"arm {side} hangs {angle:.0f} degrees from vertical; A-pose wants 30-60"))
        mode = notes[f"hands.{side}"]
        if mode == "mitten":
            issues.append(("warn", f"hand {side}: fingers closed together, so they bend as one mitten"))
        elif mode == "no-thumb":
            issues.append(("warn", f"hand {side}: thumb not separate from the palm, so it is placed by proportion"))
        toe, ankle = J[f"toe_end.{side}"], J[f"foot.{side}"]
        if toe[1] > ankle[1]:
            issues.append(("fail", f"foot {side} doesn't point forward (-Y)"))
    asym = abs(J["hand_end.L"][0] + J["hand_end.R"][0]) / H
    if asym > 0.05:
        issues.append(("warn", f"arms are not mirror images ({asym:.2f} of height apart)"))
    return issues


FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def find_fingers(P, J, side):
    """Finger joints from slices across the hand: four tracks past the knuckles, plus a thumb off to one side."""
    w0, tip = J[f"hand.{side}"], J[f"hand_end.{side}"]
    a = tip - w0
    L = np.linalg.norm(a)
    a = a / L
    rel = P - w0
    for _ in range(2):  # aim down the middle of the hand, not at whichever fingertip sticks out most
        t = rel @ a
        hand = (t > 0.05 * L) & (np.linalg.norm(rel, axis=1) < 1.3 * L)
        a = rel[hand].mean(axis=0)
        a = a / np.linalg.norm(a)
        L = float(np.percentile(rel[hand] @ a, 99))
    t = rel @ a
    perp = rel - np.outer(t, a)
    near = (t > -0.1 * L) & (t < 1.2 * L) & (np.linalg.norm(perp, axis=1) < 0.8 * L)
    T, Q = t[near], perp[near]
    w = np.linalg.eigh(np.cov(Q.T))[1][:, 2]  # across the palm
    n = np.cross(a, w)  # through the palm
    W, N = Q @ w, Q @ n
    half, gap = 0.035 * L, 0.03 * L

    def slice_at(f):
        """[(w centre, n centre, width)] of each cluster in the slab at distance f along the hand."""
        m = np.abs(T - f) < half
        out = []
        for lo, hi in clusters(W[m], gap):
            sel = m & (W >= lo) & (W <= hi)
            out.append(((lo + hi) / 2, float(np.mean(N[sel])), hi - lo))
        return out

    def point(f, wc, nc):
        return w0 + f * a + wc * w + nc * n

    # The middle of the stretch where slices cross four separate fingers
    fours = [f for f in np.arange(0.3, 1.0, 0.03) * L if len(slice_at(f)) == 4]
    ref = float(np.median(fours)) if fours else None
    joints = {}
    if ref is None:
        return mitten(slice_at, point, w0, w, L, side), "mitten"
    step = 0.04 * L
    tracks = []
    for wc, nc, width in sorted(slice_at(ref)):
        track = {ref: (wc, nc)}
        f, cur = ref, wc
        while (f := f + step) < 1.2 * L:  # out to the fingertip
            cs = [c for c in slice_at(f) if abs(c[0] - cur) < width]
            if not cs:
                break
            c = min(cs, key=lambda c: abs(c[0] - cur))
            track[f], cur = (c[0], c[1]), c[0]
        end = max(track)
        f, cur, knuckle = ref, wc, ref
        while (f := f - step) > 0:  # back to where the finger merges into the palm
            c = min(slice_at(f), key=lambda c: abs(c[0] - cur))
            if c[2] > 2.5 * width or abs(c[0] - cur) > width:
                break
            track[f], cur, knuckle = (c[0], c[1]), c[0], f
        fs = sorted(track)
        ws, ns = [track[k][0] for k in fs], [track[k][1] for k in fs]
        tracks.append((knuckle, end, fs, ws, ns))

    # The thumb: in cross-sections between the wrist and the knuckles the hand splits into two blobs,
    # palm and thumb. Blobs are found in 2D (across and through the palm) because a thumb may stick
    # out of the palm's face rather than its edge.
    kn = min(tr[0] for tr in tracks)
    cell = 0.035 * L
    pts = w0 + T[:, None] * a + Q

    def blobs(f):
        m = np.where(np.abs(T - f) < half)[0]
        cells = {}
        for i, key in zip(m, map(tuple, np.floor(np.c_[W[m], N[m]] / cell).astype(int))):
            cells.setdefault(key, []).append(i)
        seen, out = set(), []
        for start in cells:
            if start in seen:
                continue
            stack, members = [start], []
            seen.add(start)
            while stack:
                c = stack.pop()
                members += cells[c]
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nb = (c[0] + dx, c[1] + dy)
                        if nb in cells and nb not in seen:
                            seen.add(nb)
                            stack.append(nb)
            out.append(np.array(members))
        return sorted(out, key=len, reverse=True)

    thumb_pts = []
    for f in np.arange(-0.1, 1.0, 0.04) * L:
        if f > kn - 0.02 * L:
            break
        bs = [b for b in blobs(f) if len(b) > 15]
        if len(bs) == 2:
            thumb_pts.append(bs[1])
    if not thumb_pts:
        mitt = mitten(slice_at, point, w0, w, L, side)
        joints.update({k: v for k, v in mitt.items() if k.startswith("thumb")})
        mode = "no-thumb"
        tip = mitt[f"thumb_tip.{side}"]
        base = mitt[f"thumb_01.{side}"]
    else:
        mode = "fingers"
        cloud = pts[np.concatenate(thumb_pts)]
        base = w0 + max(0.0, min(0.12 * L, float((cloud.mean(axis=0) - w0) @ a) - 0.25 * L)) * a
        d = cloud.mean(axis=0) - base
        d = d / np.linalg.norm(d)
        rel_b = pts - base
        along = rel_b @ d
        cone = (along > 0) & (np.linalg.norm(rel_b - np.outer(along, d), axis=1) < 0.12 * L)
        tip = pts[cone][np.argmax(along[cone])]
        inward = (cloud.mean(axis=0) - tip) * 0.15  # the tip point is on the surface; pull the chain inside
    thumb_low = (tip - w0) @ w < np.mean([tr[3][0] for tr in tracks])
    if not thumb_low:
        tracks.reverse()  # index first: the finger next to the thumb
    for name, (knuckle, end, fs, ws, ns) in zip(FINGERS[1:], tracks):
        for i, frac in enumerate((0, 0.45, 0.75, 1), start=1):
            f = knuckle + frac * (end - knuckle)
            key = f"{name}_0{i}.{side}" if i < 4 else f"{name}_tip.{side}"
            joints[key] = point(f, np.interp(f, fs, ws), np.interp(f, fs, ns))
    if mode == "fingers":
        for i, frac in enumerate((0.15, 0.45, 0.72, 1.0), start=1):
            key = f"thumb_0{i}.{side}" if i < 4 else f"thumb_tip.{side}"
            joints[key] = base + frac * (tip - base) + inward * frac
    return joints, mode


def mitten(slice_at, point, w0, w, L, side):
    """Fingers closed together: spread four finger bones evenly across the palm and put the thumb
    on the palm edge nearest the front (hands hang with thumbs forward in an A-pose)."""
    palm = max(slice_at(0.55 * L), key=lambda c: c[2], default=(0, 0, 0.5 * L))
    lo, hi, nc = palm[0] - palm[2] / 2, palm[0] + palm[2] / 2, palm[1]
    front_low = (w0 + lo * w)[1] < (w0 + hi * w)[1]  # character faces -Y
    edge, inner = (lo, hi) if front_low else (hi, lo)
    joints = {}
    for k, name in enumerate(FINGERS[1:]):
        wc = edge + (inner - edge) * (k + 0.5) / 4
        for i, f in enumerate((0.45, 0.65, 0.82, 0.97), start=1):
            joints[f"{name}_0{i}.{side}" if i < 4 else f"{name}_tip.{side}"] = point(f * L, wc, nc)
    out = edge + (edge - inner) * 0.1
    for i, (f, wc) in enumerate(((0.05, edge * 0.6), (0.2, edge), (0.33, out), (0.45, out)), start=1):
        joints[f"thumb_0{i}.{side}" if i < 4 else f"thumb_tip.{side}"] = point(f * L, wc, nc)
    return joints


# name: (head joint, tail joint, parent, deform)
BONES = {
    "root": None,
    "hips": ("hips", "spine", "root"),
    "spine": ("spine", "chest", "hips"),
    "chest": ("chest", "neck", "spine"),
    "neck": ("neck", "head", "chest"),
    "head": ("head", "head_end", "neck"),
}
for s in "LR":
    BONES.update({
        f"clavicle.{s}": (f"clavicle.{s}", f"upper_arm.{s}", "chest"),
        f"upper_arm.{s}": (f"upper_arm.{s}", f"forearm.{s}", f"clavicle.{s}"),
        f"forearm.{s}": (f"forearm.{s}", f"hand.{s}", f"upper_arm.{s}"),
        f"hand.{s}": (f"hand.{s}", f"middle_01.{s}", f"forearm.{s}"),
        f"thigh.{s}": (f"thigh.{s}", f"shin.{s}", "hips"),
        f"shin.{s}": (f"shin.{s}", f"foot.{s}", f"thigh.{s}"),
        f"foot.{s}": (f"foot.{s}", f"toe.{s}", f"shin.{s}"),
        f"toe.{s}": (f"toe.{s}", f"toe_end.{s}", f"foot.{s}"),
    })
    for f in FINGERS:
        for i in (1, 2, 3):
            tail = f"{f}_0{i + 1}.{s}" if i < 3 else f"{f}_tip.{s}"
            BONES[f"{f}_0{i}.{s}"] = (f"{f}_0{i}.{s}", tail, f"hand.{s}" if i == 1 else f"{f}_0{i - 1}.{s}")
FINGER_BONES = [n for n in BONES if n.split("_")[0] in FINGERS]


def build_armature(J, H):
    arm_data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    root = eb.new("root")
    root.head, root.tail = (0, 0, 0), (0, 0.15 * H, 0)
    for name, spec in BONES.items():
        if spec is None:
            continue
        b = eb.new(name)
        b.head, b.tail = Vector(J[spec[0]]), Vector(J[spec[1]])
    for name, spec in BONES.items():
        if spec:
            eb[name].parent = eb[spec[2]]
            eb[name].use_connect = False
    # Socket for carried props: in front of the chest at hand height
    sock = eb.new("carry")
    mid = (Vector(J["hand.L"]) + Vector(J["hand.R"])) / 2
    sock.head = Vector((0, J["chest"][1] - 0.2 * H, (J["chest"][2] + mid.z) / 2))
    sock.tail = sock.head + Vector((0, 0, 0.08 * H))
    sock.parent = eb["chest"]
    for b in eb:
        b.roll = 0
    bpy.ops.object.mode_set(mode="OBJECT")
    for name in ("root", "carry"):
        arm_data.bones[name].use_deform = False
    return rig


def fill_unweighted(mesh):
    """Thin bits (twigs, leaf tips) vanish from the voxel proxy; copy weights from the nearest weighted vertex."""
    from mathutils.kdtree import KDTree
    verts = mesh.data.vertices
    weighted = [v for v in verts if sum(g.weight for g in v.groups) > 1e-3]
    empty = [v for v in verts if sum(g.weight for g in v.groups) <= 1e-3]
    if not empty:
        return
    tree = KDTree(len(weighted))
    for i, v in enumerate(weighted):
        tree.insert(v.co, i)
    tree.balance()
    groups = mesh.vertex_groups
    for v in empty:
        _, i, _ = tree.find(v.co)
        for g in weighted[i].groups:
            groups[g.group].add([v.index], g.weight, "REPLACE")
    print("FILLED", len(empty), "unweighted vertices")


def surface_distances(co, edges, members, seeds):
    """Shortest distance along the mesh surface from seed vertices (with start costs) to every member.

    Vertices sharing a position are joined first: glTF import splits the surface at every UV seam."""
    import heapq
    keys = {}
    node = np.array([keys.setdefault(tuple(np.round(c, 5)), len(keys)) for c in co[members]])
    local = {int(v): i for i, v in enumerate(members)}
    adj = [[] for _ in range(len(keys))]
    for a, b in edges:
        if a in local and b in local:
            na, nb = node[local[a]], node[local[b]]
            if na != nb:
                w = float(np.linalg.norm(co[a] - co[b]))
                adj[na].append((nb, w))
                adj[nb].append((na, w))
    dist = np.full(len(keys), np.inf)
    heap = []
    for v, cost in seeds:
        n = node[local[v]]
        if cost < dist[n]:
            dist[n] = cost
            heap.append((cost, n))
    heapq.heapify(heap)
    while heap:
        d, n = heapq.heappop(heap)
        if d > dist[n]:
            continue
        for m, w in adj[n]:
            if d + w < dist[m]:
                dist[m] = d + w
                heapq.heappush(heap, (d + w, m))
    return dist[node]


def split_hand_weights(mesh, rig):
    """Share each vertex's hand weight among the hand and finger bones by distance along the surface.

    Finger gaps are thinner than the voxel proxy, so bone heat would glue neighbouring fingers together,
    and straight-line distance lets a curled finger grab its neighbour; along the surface a finger is
    only reachable through the palm."""
    bones = rig.data.bones
    co = np.array([v.co for v in mesh.data.vertices])
    ev = np.empty(len(mesh.data.edges) * 2, dtype=np.int64)
    mesh.data.edges.foreach_get("vertices", ev)
    edges = ev.reshape(-1, 2).tolist()
    for side in "LR":
        names = [f"hand.{side}"] + [n for n in FINGER_BONES if n.endswith(side)]
        heads = np.array([bones[n].head_local for n in names])
        tails = np.array([bones[n].tail_local for n in names])
        hand = mesh.vertex_groups[f"hand.{side}"]
        idx, wh = [], []
        for v in mesh.data.vertices:
            for g in v.groups:
                if g.group == hand.index and g.weight > 0:
                    idx.append(v.index)
                    wh.append(g.weight)
        idx, wh = np.array(idx), np.array(wh)
        p = co[idx][:, None, :]
        d = tails - heads
        u = np.clip(((p - heads) * d).sum(-1) / (d * d).sum(-1), 0, 1)
        straight = np.linalg.norm(p - (heads + u[..., None] * d), axis=-1)  # (verts, bones)
        nearest = straight.argmin(axis=1)
        dist = np.empty_like(straight)
        for k in range(len(names)):
            own = np.where(nearest == k)[0]
            if not len(own):
                dist[:, k] = straight[:, k]
                continue
            close = own[straight[own, k] <= np.percentile(straight[own, k], 25)]
            geo = surface_distances(co, edges, idx, [(int(idx[i]), straight[i, k]) for i in close])
            dist[:, k] = np.where(np.isfinite(geo), geo, straight[:, k] * 3)
        share = 1 / (dist + 1e-4) ** 4
        share[share < np.sort(share, axis=1)[:, [-2]]] = 0  # two nearest bones blend
        share /= share.sum(axis=1, keepdims=True)
        for k, name in enumerate(names):
            group = mesh.vertex_groups[name]
            for i, w in zip(idx, wh * share[:, k]):
                group.add([int(i)], float(w), "REPLACE")


def skin(mesh, rig, H):
    """Bone-heat weights on a voxel-remeshed proxy, transferred to the real mesh."""
    proxy = mesh.copy()
    proxy.data = mesh.data.copy()
    proxy.name = "WeightProxy"
    bpy.context.collection.objects.link(proxy)
    mod = proxy.modifiers.new("remesh", "REMESH")
    mod.mode, mod.voxel_size = "VOXEL", 0.012 * H
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.modifier_apply(modifier=mod.name)

    for name in FINGER_BONES:  # weighted separately in split_hand_weights
        rig.data.bones[name].use_deform = False
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for name in FINGER_BONES:
        rig.data.bones[name].use_deform = True

    for b in rig.data.bones:
        if b.use_deform:
            mesh.vertex_groups.new(name=b.name)
    dt = mesh.modifiers.new("weights", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(proxy)
    fill_unweighted(mesh)
    split_hand_weights(mesh, rig)

    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    bpy.ops.object.vertex_group_limit_total(limit=4)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    mesh.parent = rig
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = rig


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, out = argv[0], argv[1]
    reset_scene()
    mesh = import_glb(src)
    J, H, notes = find_landmarks(mesh_points(mesh))
    issues = check(J, H, notes)
    report = {"height": round(float(H), 3), "ok": not any(lvl == "fail" for lvl, _ in issues),
              "issues": [{"level": lvl, "message": m} for lvl, m in issues]}
    Path(out).with_suffix(".check.json").write_text(json.dumps(report, indent=2) + "\n")
    print("CHECK", json.dumps(report))
    if "--check" in argv:
        rig = build_armature(J, H)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(out).resolve()))
        return
    rig = build_armature(J, H)
    skin(mesh, rig, H)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(out).resolve()))
    print("RIGGED", {k: [round(float(c), 3) for c in v] for k, v in J.items()})


if __name__ == "__main__":
    main()
