# Check a GLB against its family contract. Errors block export to the game; warnings are for review.
#   bun run art:forge validate --in <file.glb> [--family humanoid] [--kind body|gear|anims|prop|rigid] [--body <body.glb>]
# kind defaults to the asset's forge metadata. --body lets gear be checked against the body's shape keys.
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import args, contract, done, glb_json, load, regions_uv, reset, triangles  # noqa: E402

import bpy  # noqa: E402

a = args()
reset()
objects = load(a["in"])
meta = next((json.loads(o["forge"]) for o in objects if "forge" in o), {})
family = a.get("family") or meta.get("family", "humanoid")
kind = a.get("kind") or meta.get("kind", "body")
c = contract(family)
errors: list[str] = []
warns: list[str] = []
arms = [o for o in objects if o.type == "ARMATURE"]
meshes = [o for o in objects if o.type == "MESH"]
stats = {"family": family, "kind": kind, "triangles": sum(triangles(m) for m in meshes)}

if not meta:
    warns.append("no forge metadata: the asset did not come through the forge steps")
for o in objects:
    if any(abs(s - 1) > 1e-4 for s in o.scale) or any(abs(r) > 1e-4 for r in o.rotation_euler):
        errors.append(f"{o.name}: unapplied transform (scale {tuple(round(s, 3) for s in o.scale)})")

if family != "rigid" and kind in ("body", "gear", "anims"):
    if len(arms) != 1:
        errors.append(f"expected one armature, found {len(arms)}")
    else:
        arm = arms[0]
        names = {b.name for b in arm.data.bones}
        sk = c["skeleton"]
        missing = [n for n in sk["core"] if n not in names]
        if missing:
            errors.append(f"missing core bones: {missing}")
        chain_re = re.compile("^(" + "|".join(re.escape(v.split("..")[0].rsplit("_", 1)[0]) for v in sk["chains"].values()) + r")_\d+$")
        known = set(sk["core"]) | set(sk["optional"]) | {s["name"] for s in c["sockets"]}
        unknown = sorted(n for n in names if n not in known and not chain_re.match(n))
        if unknown:
            errors.append(f"bones outside the contract: {unknown}")
        if kind == "body":
            absent = [s["name"] for s in c["sockets"] if s["name"] not in names]
            if absent:
                errors.append(f"missing sockets: {absent}")
        tilted = [b.name for b in arm.data.bones if (b.tail_local - b.head_local).normalized().z < 0.999]
        if tilted:
            errors.append(f"bones not pointing up at rest (clips will not transfer): {tilted[:8]}")
        if kind == "anims":
            stats["clips"] = [act.name for act in bpy.data.actions]
            if not bpy.data.actions:
                errors.append("animation library has no clips")
            # What the file holds, not what Blender re-imported: engines play every frame between keys
            gltf = glb_json(a["in"])
            nodes = [n.get("name") for n in gltf.get("nodes", [])]
            for anim in gltf.get("animations", []):
                kinds = {s["interpolation"] for s in anim["samplers"] if "interpolation" in s} or {"LINEAR"}
                if kinds - {"LINEAR", "STEP"}:
                    errors.append(f"clip {anim.get('name')}: {sorted(kinds)} interpolation (must be LINEAR; cubic tangents overshoot between keys)")
                moved = sorted({nodes[ch["target"]["node"]] for ch in anim["channels"] if ch["target"]["path"] != "rotation"} - {"Hips"})
                if moved:
                    errors.append(f"clip {anim.get('name')}: translation/scale keys on {moved[:6]} (would override body proportions)")
        deform = {b.name for b in arm.data.bones if b.use_deform}
        for m in meshes:
            gnames = {g.index: g.name for g in m.vertex_groups}
            over, unnorm, unweighted = 0, 0, 0
            for v in m.data.vertices:
                ws = [g.weight for g in v.groups if g.weight > 1e-6 and gnames[g.group] in deform]
                over += len(ws) > sk["maxInfluences"]
                unweighted += not ws
                unnorm += bool(ws) and abs(sum(ws) - 1) > 0.01
            if over:
                errors.append(f"{m.name}: {over} vertices with more than {sk['maxInfluences']} influences")
            if unweighted:
                errors.append(f"{m.name}: {unweighted} vertices with no weights")
            if unnorm:
                warns.append(f"{m.name}: {unnorm} vertices with weights not summing to 1")

    for m in meshes:
        keys = [k.name for k in m.data.shape_keys.key_blocks[1:]] if m.data.shape_keys else []
        allowed = set(c["sliders"]["morph"].get("body", []) + c["sliders"]["morph"].get("face", []))
        allowed = {f"{n}_{s}" for n in allowed for s in ("neg", "pos")} | set(c["sliders"].get("expressions", []))
        odd = [k for k in keys if k not in allowed and not re.match(r"^(people|species)_[a-z0-9_]+$", k)]
        if odd:
            warns.append(f"{m.name}: shape keys outside the contract: {odd[:10]}")
        if kind == "body" and not regions_uv(m):
            errors.append(f"{m.name}: no Regions UV layer (body hiding will not work)")
        stats.setdefault("shapeKeys", {})[m.name] = len(keys)

if kind == "gear":
    if meta.get("slot") not in c.get("slots", {}):
        errors.append(f"unknown gear slot {meta.get('slot')!r}")
    if a.get("body"):
        objects_body = load(a["body"])
        body_keys = {k.name for o in objects_body if o.type == "MESH" and o.data.shape_keys for k in o.data.shape_keys.key_blocks[1:]}
        for m in meshes:
            have = {k.name for k in m.data.shape_keys.key_blocks[1:]} if m.data.shape_keys else set()
            lacking = sorted(body_keys - have)
            if lacking:
                meta_keys = set(meta.get("fittedKeys", []))
                unfitted = [k for k in lacking if meta_keys and k not in meta_keys]
                if unfitted or not meta_keys:
                    errors.append(f"{m.name}: was never fitted to body keys {(unfitted or lacking)[:10]}; refit it")
                else:
                    checks_note = f"{m.name}: {len(lacking)} body keys don't move this piece and were left out"
                    warns.append(checks_note)

if family == "rigid" or kind in ("prop", "rigid"):
    sub = c["kinds"].get(meta.get("rigidKind", kind), {}) if family == "rigid" else {}
    for req in sub.get("requires", []):
        if not any(o.name == req or o.name.startswith(req + ".") for o in objects):
            errors.append(f"missing required empty {req}")
    if arms and family == "rigid":
        warns.append("rigid asset has an armature")

budget = c.get("budgets", {}).get(kind) or (c.get("kinds", {}).get(meta.get("rigidKind", kind), {}) if family == "rigid" else {})
if budget and stats["triangles"] > budget.get("triangles", math.inf):
    errors.append(f"{stats['triangles']} triangles exceeds the {kind} budget of {budget['triangles']}")
for img in bpy.data.images:
    if img.size[0] and budget and max(img.size) > budget.get("texture", math.inf):
        warns.append(f"texture {img.name} is {img.size[0]}x{img.size[1]}, budget {budget['texture']}")

dye = Path(a["in"]).with_suffix(".dye.png")
stats["dyeMask"] = dye.exists()
done(valid=not errors, errors=errors, checks=warns, stats=stats)
