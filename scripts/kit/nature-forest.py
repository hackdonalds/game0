# Forest nature kit: forest pines, birches, the glowing red-violet Duskcrown broadleaf, the old-growth giant pine,
# the axe-scarred Grudge Tree, brambles, logs, stumps, mushrooms, dark mossy stone, the fern-hung lip and the
# Hollowsky underside pierced by a round hole. Painted swatches cropped from the biome's nature sheet live in
# art/textures/biomes/forest. Generators are shared with nature-roothold.py (loaded below; its build only runs
# when it is the script Blender was started with).
# Usage: Blender --background --python scripts/kit/nature-forest.py -- forest [--only id,id] [--out dir]
import importlib.util, math, os, random, sys
from mathutils import Vector, noise

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
_spec = importlib.util.spec_from_file_location("nature_roothold", os.path.join(_here, "nature-roothold.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
B, K = R.B, R.K
from kitlib import Mesh, hermite  # noqa: E402

tube, mass, card, sprigs, clump, frond, fern, mushroom, flowers = R.tube, R.mass, R.card, R.sprigs, R.clump, R.frond, R.fern, R.mushroom, R.flowers
fern_cards, grass_tufts, moss_drape, fill_crown, conifer_cards, N = R.fern_cards, R.grass_tufts, R.moss_drape, R.fill_crown, R.conifer_cards, R.N
boulder, plate, hull, ribbon, sweep, root, gnarl, basis, UP = R.boulder, R.plate, R.hull, R.ribbon, R.sweep, R.root, R.gnarl, R.basis, R.UP

MATS = [("FO_PineBark", "pine-bark.png", 0), ("FO_BirchBark", "birch-bark.png", 0), ("FO_DuskBark", "dusk-bark.png", 0),
        ("FO_RootBark", "root-bark.png", 0), ("FO_Heartwood", "heartwood.png", 0),
        ("FO_PineNeedle_Foliage", "pine-needles.png", 0), ("FO_PineShade_Foliage", "pine-needles-shade.png", 0),
        ("FO_BirchLeaf_Foliage", "birch-leaf.png", 0), ("FO_BirchShade_Foliage", "birch-leaf-shade.png", 0),
        ("FO_DuskRed_Foliage", "dusk-red.png", 0), ("FO_DuskViolet_Foliage", "dusk-violet.png", 0), ("FO_DuskTip_Glow", "dusk-red.png", 0.8),
        ("FO_GrudgeLeaf_Foliage", "grudge-leaf.png", 0), ("FO_GrudgeShade_Foliage", "grudge-leaf-shade.png", 0),
        ("FO_Fern_Foliage", "fern.png", 0), ("FO_Bramble_Foliage", "bramble.png", 0), ("FO_Moss", "moss.png", 0),
        ("FO_MossStrand_Foliage", "moss.png", 0), ("FO_Stone", "stone.png", 0), ("FO_Slate", "slate.png", 0),
        ("FO_NeedleLitter", "needle-litter.png", 0), ("FO_LeafLitter", "leaf-litter.png", 0), ("FO_Mushroom", "mushroom.png", 0),
        ("FO_Stem", (0.88, 0.82, 0.68), 0), ("FO_ShelfConk", "shelf-fungus.png", 0), ("FO_Ground", "ground.png", 0),
        ("FO_Cliff", "cliff.png", 0), ("FO_Underside", "underside.png", 0), ("FO_Water", "water.png", 0), ("FO_Berry", (0.62, 0.08, 0.1), 0),
        ("FO_Firefly_Glow", (1.0, 0.8, 0.35), 4.0), ("FO_GrudgeBark", "grudge-bark.png", 0), ("FO_ScarWood", "scar-wood.png", 0),
        # alpha-cutout leaf cards (painted sprite atlases shared by every biome)
        ("FO_PineSpray_Foliage_Card", "../../foliage/pine-needles.png", 0), ("FO_BirchLeaf_Foliage_Card", "../../foliage/birch.png", 0),
        ("FO_DuskLeaf_Foliage_Card", "../../foliage/duskcrown.png", 0), ("FO_DuskGlow_Foliage_Card", "../../foliage/duskcrown.png", 0.8),
        ("FO_DarkLeaf_Foliage_Card", "../../foliage/broadleaf-dark.png", 0), ("FO_Fern_Foliage_Card", "../../foliage/fern.png", 0),
        ("FO_Grass_Foliage_Card", "../../foliage/grass.png", 0), ("FO_MossDrape_Foliage_Card", "../../foliage/ivy-moss.png", 0)]
(PINEB, BIRCHB, DUSKB, ROOTB, HEART, PINE, PINES, BIRCH, BIRCHS, DRED, DVIOLET, DGLOW, GRUDGE, GRUDGES, FERN, BRAMBLE, MOSS, STRAND,
 STONE, SLATE, NEEDLES, LITTER, MUSH, STEM, SHELF, GROUND, CLIFF, UNDER, WATER, BERRY, FIREFLY, GRUDGEB, SCAR,
 PINEC, BIRCHC, DUSKC, DGLOWC, DARKC, FERNC, GRASSC, DRAPEC) = range(len(MATS))
SHADE = {PINE: PINES, BIRCH: BIRCHS, GRUDGE: GRUDGES, DRED: DVIOLET}
CAP = HEART
BARKS = (PINEB, BIRCHB, DUSKB, ROOTB, GRUDGEB)


# ---------- extra generators ----------

def shelf(m, c, out, r, mat, seed):
    """Bracket (shelf) fungus: a flattened half-dome jutting from bark along `out`."""
    f, u, s = basis(Vector((out.x, 0, out.z)))
    mass(m, Vector(c) + f * r * 0.15, (r * 0.75, r * 0.2, r), mat, seed, rough=0.12, lobe=0.05, rings=4, segs=8, flat=0.5, axes=(f, u, s), tile=0.6)


def axe_scars(m, centre_pts, radii, scars, depth, wood):
    """Cut V-shaped axe notches into the trunk: vertices on the bark near each scar are pushed into the trunk with
    a wedge profile, and the faces inside the cut take raw wood. scars = [(height, angle, width, half-height)]."""
    pushed = {}
    for v in m.bm.verts:
        p = Vector((v.co.x, v.co.z, -v.co.y))
        for (hy, ang, w, hh) in scars:
            # trunk axis point and radius at this height
            i = min(range(len(centre_pts)), key=lambda k: abs(centre_pts[k].y - p.y))
            ax, r = centre_pts[i], radii[i]
            rel = Vector((p.x - ax.x, 0, p.z - ax.z))
            if rel.length < r * 0.6 or rel.length > r * 1.5:
                continue
            d = Vector((math.cos(ang), 0, math.sin(ang)))
            side = Vector((-d.z, 0, d.x))
            lat = rel.normalized().dot(side) * r
            if rel.normalized().dot(d) < 0.3:
                continue
            dy = p.y - hy
            if abs(dy) < hh and abs(lat) < w:
                k = (1 - abs(dy) / hh) * (1 - (abs(lat) / w) ** 3)
                push = depth * k
                if push > pushed.get(v, 0):
                    pushed[v] = push
                    dn = rel.normalized()
                    v.co.x -= dn.x * push
                    v.co.y -= -dn.z * push
    n = 0
    for f in m.bm.faces:
        if sum(pushed.get(v, 0) > depth * 0.08 for v in f.verts) >= len(f.verts) - 1:
            f.material_index = wood
            n += 1
    if os.environ.get("DEBUG_SCARS"):
        print("[scars] pushed", len(pushed), "faces", n)


def lean_slab(m, c, size, lean, rot, mat, seed, chip=0.15):
    """An upright split slab leaning over by `lean` radians (about its long horizontal axis), turned by `rot`."""
    rng = random.Random(seed)
    w, h, d = size
    pts = []
    for sx in (-1, 1):
        for sy in (0, 1):
            for sz in (-1, 1):
                x, y, z = sx * w / 2 * (1 - chip * rng.random()), sy * h * (1 - chip * rng.random() * sy), sz * d / 2 * (1 - chip * rng.random())
                pts.append(Vector((x, y, z)))
    pts.append(Vector((rng.uniform(-0.2, 0.2) * w, h * rng.uniform(1.0, 1.08), 0)))
    cl, sl = math.cos(lean), math.sin(lean)
    cr, sr = math.cos(rot), math.sin(rot)
    out = []
    for p in pts:
        x, y = p.x * cl - p.y * sl, p.x * sl + p.y * cl
        z = p.z
        out.append(Vector(c) + Vector((x * cr - z * sr, y, x * sr + z * cr)))
    hull(m, out, mat, 1.5, min(w, d) * 0.08)


def firefly(m, c, r, mat):
    c = Vector(c)
    v = [m.vert(c + Vector(d) * r) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    for a, b, cc in ((0, 2, 4), (4, 2, 1), (1, 2, 5), (5, 2, 0), (4, 3, 0), (1, 3, 4), (5, 3, 1), (0, 3, 5)):
        m.face((v[a], v[b], v[cc]), ((0, 0), (1, 0), (0.5, 1)), mat)


# ---------- trees ----------

def fo_pine(p, m, rng, seed, tiers, slim=1.0):
    W, H, _ = p["size"]
    trunk = R.conifer_tree(m, rng, H, W * 0.95, H * 0.018 + 0.1, PINEB, [PINE], tiers=0, roots=5, reach=W * 0.28, root_bark=ROOTB,
                           seed=seed, root_r=0.8, trunk_sides=8)
    grass_tufts(m, rng, (0, 0, 0), W * 0.2, 3, 0.4, GRASSC, seed, pick=2)
    conifer_cards(m, rng, H, W * 0.92 * slim, trunk, PINEC, p["tris"], start=0.12, top_frac=0.05, tiers=tiers, droop=0.5, tilt=(0.35, 0.95),
                  size=0.6, seed=seed, top_n=12, layer=0.05, ragged=0.3)
    return Vector((0, H * 0.5, 0)), W / 2


def fo_birch(p, m, rng, seed, limbs):
    W, H, _ = p["size"]
    cc, cr, trunk, tr_r, lobes = R.broad_tree(
        m, rng, H, W * 0.7, H * 0.55, 0.22 * W / 7 + 0.06, BIRCHB, [BIRCH], lean=(0.03, 0.02), fork=0.42, limbs=limbs, subs=2, roots=4,
        reach=1.1, braid=0, fill=3, trunk_sides=8, trunk_n=10, root_sides=4, limb_sides=5, sub_sides=4, root_bark=ROOTB, seed=seed,
        lobe_r=0.2, top_r=0.26, limb_r=0.5, flare=0.6, limb_n=6, root_n=5, crown_y=H * 0.68, squash=1.15)
    grass_tufts(m, rng, (0, 0, 0), W * 0.15, 3, 0.4, GRASSC, seed, pick=2)
    fill_crown(m, lobes, BIRCHC, p["tris"], (W * 0.13, W * 0.19), cc, seed, up_bias=0.25)
    return cc, cr


def fo_dusk(p, m, rng, seed, young=False):
    W, H, _ = p["size"]
    tr = 0.45 if young else 0.85
    cc, cr, trunk, tr_r, lobes = R.broad_tree(
        m, rng, H, W * 0.95, H * 0.42, tr, DUSKB, [DRED], lean=(0.12, 0.05) if young else (0.02, 0.0), fork=0.36,
        limbs=4 if young else 5, subs=1, roots=4 if young else 6, reach=tr * 3.5, braid=0 if young else 2, fill=2 if young else 4,
        trunk_sides=8 if young else 10, trunk_n=9, root_sides=5, limb_sides=6, sub_sides=4, root_bark=DUSKB, seed=seed,
        lobe_r=0.16, top_r=0.24, limb_r=0.68, flare=1.3, limb_n=7, root_n=7, crown_y=H * 0.72, root_strands=False, squash=0.62)
    grass_tufts(m, rng, (0, 0, 0), W * 0.12, 3, 0.4, GRASSC, seed, pick=2)
    # glowing leaf cards scattered over the sunlit top of the crown
    fill_crown(m, lobes, DUSKC, p["tris"], (W * 0.1, W * 0.155), cc, seed, glow=DGLOWC, glow_n=40 if young else 70, bumps=2)
    return cc, cr


def fo_giant(p, m, rng, seed):
    W, H, _ = p["size"]
    tr = 1.5
    trunk = R.conifer_tree(m, rng, H, W, tr, PINEB, [PINE], tiers=0, trunk_sides=14, roots=7, reach=W * 0.3, root_bark=ROOTB, seed=seed,
                           root_r=0.75, flare=1.6)
    # shelf fungus stepping up one side of the trunk
    for k in range(5):
        y = 2.0 + k * 0.7
        a = 0.6 + 0.15 * math.sin(k * 2)
        out = Vector((math.cos(a), 0, math.sin(a)))
        r_here = tr * (1 + 0.9 * 1.6 * math.exp(-y / H * 10)) * (1.05 - 0.95 * y / H)
        shelf(m, Vector((0, y, 0)) + out * r_here * 0.95, out, 0.55 - 0.05 * k, SHELF, seed + k)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.3
        fern_cards(m, rng, Vector((math.cos(a), 0, math.sin(a))) * W * 0.25, 0.7, 0.7, FERNC, seed + k, 5, 1)
    # old-growth crown: a few broad, flat, clumped tiers high on the trunk, wide gaps between them
    conifer_cards(m, rng, H, W * 0.82, trunk, PINEC, p["tris"], start=0.48, top_frac=0.05, tiers=6, droop=0.14, tilt=(0.8, 1.4),
                  size=0.4, seed=seed, top_n=10, layer=0.1, ragged=0.6, sink=0.25, inner=0.3)
    return Vector((0, H * 0.75, 0)), W / 2


def fo_grudge(p, m, rng, seed):
    W, H, _ = p["size"]
    cc, cr, trunk, tr_r, lobes = R.broad_tree(
        m, rng, H, W * 0.95, H * 0.48, 2.5, GRUDGEB, [GRUDGE], lean=(-0.03, 0.02), fork=0.34, limbs=8, subs=1, roots=8, reach=8.0,
        braid=0, fill=4, trunk_sides=36, trunk_n=30, root_sides=9, limb_sides=9, sub_sides=6, dead=3,
        root_bark=ROOTB, seed=seed, lobe_r=0.15, top_r=0.22, limb_r=0.55, flare=1.2, limb_n=10, root_strands=False,
        root_n=10, root_h=0.14, squash=0.62)
    # deep axe scars facing the approach (+Z) and the flanks
    scars = [(6.0, math.pi / 2, 1.5, 0.75), (7.7, math.pi / 2 + 0.45, 1.3, 0.65), (4.6, math.pi / 2 - 0.55, 1.2, 0.6), (9.0, math.pi / 2 - 0.1, 1.2, 0.6),
             (6.8, 0.25, 1.4, 0.7), (8.0, math.pi + 0.4, 1.3, 0.65)]
    axe_scars(m, trunk, tr_r, scars, 0.9, SCAR)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.9
        d = Vector((math.cos(a), 0, math.sin(a)))
        fern_cards(m, rng, d * rng.uniform(4.5, 6.5), 0.9, 0.8, FERNC, seed + k, 6, 2)
        grass_tufts(m, rng, d * rng.uniform(3.5, 5.0), 0.8, 3, 0.45, GRASSC, seed + k, pick=2)
    R.hang_moss(m, rng, lobes, 10, DRAPEC, seed)
    fill_crown(m, lobes, DARKC, p["tris"], (W * 0.09, W * 0.14), cc, seed, bumps=3)
    return cc, cr


# ---------- understory and ground ----------

def fo_bramble(p, m, rng, seed):
    W, H, D = p["size"]
    lobes = [(-0.25, 0.0, 0.32), (0.22, 0.1, 0.3), (0.0, -0.22, 0.28), (0.05, 0.25, 0.25)]
    for i, (x, z, s) in enumerate(lobes):
        mass(m, (x * W, 0.0, z * D), (s * W * 0.85, H * rng.uniform(0.6, 0.75), s * W * 0.8), BRAMBLE, seed + i, rough=0.28, lobe=0.18, rings=4, segs=7,
             flat=0.2, tile=1.0)
    for k in range(5):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), 0, math.sin(a)))
        st = d * W * 0.15
        end = Vector((d.x * W * 0.55, 0.0, d.z * D * 0.55))
        pts = hermite(st, UP * H * 1.6 + d * 0.3, end, d * 0.6 - UP * 1.0, 4)
        tube(m, pts, [0.03, 0.027, 0.023, 0.019, 0.015], ROOTB, 3, caps=(False, False))
    # leaf cards over the thicket so its outline breaks into ragged leaves
    N.card_crown(m, [(Vector((x * W, H * 0.35, z * D)), (s * W * 1.1, H * 0.6, s * W)) for x, z, s in lobes], DARKC, seed=int(seed * 10),
                 density=28, size=(0.45, 0.65), crown_centre=(0, -0.2, 0), up_bias=0.6)
    for k in range(8):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.42
        y = H * (0.55 + 0.4 * (1 - r / 0.42)) * rng.uniform(0.8, 1.0)
        c = Vector((math.cos(a) * r * W, y, math.sin(a) * r * D))
        for j in range(1):
            mass(m, c + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.04, 0.02), rng.uniform(-0.05, 0.05))), (0.05, 0.05, 0.05), BERRY, seed + k + j,
                 rough=0.1, lobe=0.0, rings=3, segs=4, flat=1.0, tile=0.2)


def fo_log(p, m, rng, seed):
    W, H, D = p["size"]
    r = H * 0.46
    R.hollow_log(m, W * 0.86, r, PINEB, HEART, HEART, seed, splinter=0.7, sides=8, n=6)
    for i in range(3):
        mass(m, (-W * 0.28 + i * W * 0.22, r * 1.8, rng.uniform(-0.08, 0.08)), (W * 0.13, 0.12, r * 0.6), MOSS, seed + i, rough=0.3, rings=4, segs=7, tile=1.2)
    for k in range(3):
        mushroom(m, Vector((rng.uniform(-1.2, 0.8), 0, D * 0.4)), rng.uniform(0.12, 0.2), rng.uniform(0.09, 0.13), MUSH, STEM, STEM, seed + k, sides=6)
    fern_cards(m, rng, (W * 0.25, 0, -D * 0.42), 0.5, 0.55, FERNC, seed + 5, 7, 2)
    for i in range(3):
        moss_drape(m, rng, (-W * 0.28 + i * W * 0.22, r * 1.65, D * 0.3), r * 1.2, 0.6, DRAPEC, seed + i, face=(0, 0, 1))


def fo_broken_stump(p, m, rng, seed):
    W, H, D = p["size"]
    r = W * 0.24
    sides = 10
    pts = [Vector((0, -0.25, 0)), Vector((0, H * 0.25, 0)), Vector((0.02, H * 0.5, 0)), Vector((0.03, H * 0.62, 0))]
    rings = tube(m, pts, [r * 1.4, r * 1.08, r * 1.0, r * 0.96], PINEB, sides, twist=0.5, rough=0.12, seed=seed, caps=(False, False))
    top = rings[-1]
    tc = pts[-1]
    # jagged splintered top: tall shards on the rim, raw wood inside and a sunken broken core
    core = m.vert(tc + Vector((0, H * 0.04, 0)))
    for k in range(sides):
        v0, v1 = top[k][0], top[k + 1][0]
        p0 = Vector((v0.co.x, v0.co.z, -v0.co.y))
        p1 = Vector((v1.co.x, v1.co.z, -v1.co.y))
        mid = (p0 + p1) / 2
        hgt = H * (0.38 * abs(math.sin(k * 1.9 + seed)) ** 1.5) * rng.uniform(0.6, 1.0)
        tip = m.vert(mid + (tc - mid) * 0.25 + Vector((0, hgt, 0)))
        m.face((v0, v1, tip), ((0, 0), (1, 0), (0.5, 1)), PINEB if k % 2 else HEART)
        inner = m.vert(mid + (tc - mid) * 0.5 + Vector((0, hgt * 0.5, 0)))
        m.face((v1, v0, inner), ((0, 0), (1, 0), (0.5, 1)), HEART)
        m.face((v1, inner, core), ((0, 0), (0.5, 1), (1, 0)), HEART)
        m.face((inner, v0, core), ((0, 0), (0.5, 1), (1, 0)), HEART)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        d = Vector((math.cos(a), 0, math.sin(a)))
        root(m, Vector((0, H * 0.18, 0)) + d * r * 0.5, d, W * 0.42, r * 0.55, ROOTB, seed + k, 4, 5, r1=r * 0.15)
    for k in range(3):
        a = 0.8 + k * 0.5
        out = Vector((math.cos(a), 0, math.sin(a)))
        shelf(m, Vector((0, 0.3 + k * 0.22, 0)) + out * r * 1.25, out, 0.2 - 0.03 * k, SHELF, seed + k)
    mass(m, (r * 0.6, 0.0, -r * 0.8), (0.45, 0.15, 0.35), MOSS, seed, rough=0.3, rings=4, segs=7, flat=0.2, tile=1.0)
    fern_cards(m, rng, (-W * 0.35, 0, W * 0.2), 0.4, 0.5, FERNC, seed + 3, 5, 1)
    grass_tufts(m, rng, (W * 0.3, 0, W * 0.3), 0.3, 2, 0.3, GRASSC, seed, pick=2)


def fo_mushrooms(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, 0.0, 0), (W * 0.48, 0.1, D * 0.46), MOSS, seed, rough=0.3, rings=4, segs=8, flat=0.3, tile=1.0)
    spots = [(-0.05, 0.0, 0.95, 0.24), (0.28, 0.1, 0.62, 0.17), (-0.32, 0.15, 0.55, 0.15), (0.35, -0.22, 0.38, 0.12), (-0.2, -0.28, 0.32, 0.1),
             (0.1, 0.32, 0.3, 0.1)]
    for i, (x, z, h, cr) in enumerate(spots):
        mushroom(m, Vector((x * W, 0.03, z * D)), h * H * 0.8, cr, MUSH, STEM, STEM, seed + i, lean=(x * 0.2, z * 0.2), sides=7)


def fo_fireflies(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, 0.02, 0), (W * 0.1, W * 0.06, W * 0.1), MOSS, seed, rings=4, segs=6, rough=0.3)
    fern_cards(m, rng, (0, 0, 0), W * 0.42, H * 0.6, FERNC, seed, 13, 5)
    fern_cards(m, rng, (0, 0, 0), W * 0.3, H * 0.45, FERNC, seed + 3, 8, 0, flat=0.15)
    for i in range(7):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.1, 0.5)
        firefly(m, (math.cos(a) * r * W, H * rng.uniform(0.65, 1.0), math.sin(a) * r * D), 0.035, FIREFLY)


def fo_needle_litter(p, m, rng, seed):
    W, H, D = p["size"]
    mass(m, (0, -0.02, 0), (W * 0.46, H * 0.35, D * 0.46), NEEDLES, seed, rough=0.25, lobe=0.12, rings=4, segs=10, flat=0.1, tile=1.0)
    for k in range(4):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0.1, 0.35)
        c = Vector((math.cos(a) * r * W, H * 0.3, math.sin(a) * r * D))
        b = rng.uniform(0, math.pi)
        f = Vector((math.cos(b), 0.1, math.sin(b)))
        fw, fu, fs = basis(f)
        mass(m, c, (0.07, 0.045, 0.045), PINEB, seed + k, rough=0.2, lobe=0.0, rings=4, segs=6, flat=1.0, axes=(fw, fu, fs), tile=0.3)
    for i in range(10):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.45
        c = Vector((math.cos(a) * r * W, H * 0.22, math.sin(a) * r * D))
        b = rng.uniform(0, 2 * math.pi)
        card(m, c, Vector((math.cos(b), 0.05, math.sin(b))), 0.22, 0.12, NEEDLES, fold=-0.05, droop=-0.05)


def fo_moss_clump(p, m, rng, seed):
    W, H, D = p["size"]
    for i, (x, z, s, h) in enumerate([(-0.2, -0.05, 0.33, 1.0), (0.2, 0.1, 0.3, 0.8), (0.0, -0.3, 0.24, 0.6)]):
        mass(m, (x * W, 0.0, z * D), (s * W, H * h, s * W * 0.9), MOSS, seed + i, rough=0.28, lobe=0.15, rings=5, segs=8, flat=0.2, tile=1.0)
    boulder(m, (0.32 * W, 0, 0.3 * D), (0.28, 0.2, 0.24), STONE, seed, n=10, bevel=0.0)
    for i, (x, z, s) in enumerate([(-0.2, -0.05, 0.33), (0.2, 0.1, 0.3)]):
        grass_tufts(m, rng, (x * W, H * 0.5, z * D), s * W * 0.4, 2, 0.22, GRASSC, seed + i, pick=2)


# ---------- rocks ----------

def fo_cluster(p, m, rng, seed):
    W, H, D = p["size"]
    for i, (x, z, s, h) in enumerate([(-0.18, -0.05, 0.55, 1.0), (0.25, 0.12, 0.45, 0.75), (0.05, -0.3, 0.38, 0.55), (-0.3, 0.3, 0.3, 0.45)]):
        boulder(m, (x * W, 0, z * D), (W * s, H * h, D * s), STONE, seed + i, n=22, round_=0.55, rot=rng.uniform(0, 3))


def fo_split(p, m, rng, seed):
    W, H, D = p["size"]
    for i, (x, lean, hf) in enumerate([(-0.3, 0.22, 0.85), (0.0, 0.02, 1.0), (0.3, -0.2, 0.8)]):
        lean_slab(m, (x * W, -0.05, rng.uniform(-0.05, 0.05)), (W * 0.3, H * hf, D * 0.85), lean, rng.uniform(-0.15, 0.15), STONE, seed + i)
    boulder(m, (0.45 * W, 0, 0.35 * D), (0.4, 0.3, 0.35), STONE, seed + 9, n=12)


def fo_hollow(p, m, rng, seed):
    """Ring of stacked dark blocks around a round hole (sky shows through), on a bed of base blocks."""
    W, H, D = p["size"]
    cy = H * 0.55
    rr = H * 0.42
    n = 9
    for k in range(n):
        a = 2 * math.pi * k / n + 0.2
        c = Vector((math.cos(a) * W * 0.3, cy + math.sin(a) * rr, 0))
        if c.y < 0.35:
            continue
        sz = rr * rng.uniform(0.65, 0.8)
        boulder(m, c - Vector((0, sz * 0.4, 0)), (sz * 1.1, sz * 0.85, D * rng.uniform(0.7, 0.9)), STONE, seed + k, n=11, round_=0.35, rot=a + math.pi / 2,
                sink=0.0, base=-0.9, bevel=0.03)
    for i, x in enumerate((-0.32, 0.0, 0.32)):
        boulder(m, (x * W * 0.9, -0.05, rng.uniform(-0.05, 0.05)), (W * 0.36, H * 0.22, D * 0.95), STONE, seed + 20 + i, n=12, round_=0.35, sink=0.0,
                base=-0.9, bevel=0.03)


# ---------- lip, water, underside ----------

def fo_lip(p, m, rng, seed):
    W, H, D = p["size"]
    R.lip_edge(m, W, D, H, GROUND, MOSS, CLIFF, seed, notch=-1.8, segs=14)
    R.cliff_face(m, rng, W, D, H, STONE, seed, top=1.25, rows=3)
    R.lip_roots(m, rng, W, D, H, (-3.0, 0.4, 2.9), ROOTB, seed, r=0.26)
    for i in range(14):
        x = -W / 2 + 0.3 + i * (W - 0.6) / 13 + rng.uniform(-0.2, 0.2)
        if abs(x + 1.8) < 0.5:
            continue
        moss_drape(m, rng, (x, H - 0.45, D / 2 + 0.62), rng.uniform(1.6, 3.0), 1.5, DRAPEC, seed + i, face=(0, 0, 1), ivy=i % 3 == 0)
    for i in range(3):
        x = rng.uniform(-W / 2 + 0.8, W / 2 - 0.8)
        c = Vector((x, H + 0.3, rng.uniform(-0.6, 0.8)))
        N.card_crown(m, [(c, (0.5, 0.35, 0.5))], DUSKC, seed=int(seed * 10) + i, density=30, size=(0.5, 0.7), crown_centre=c - UP * 0.3, up_bias=0.5)
    for i in range(3):
        fern_cards(m, rng, (rng.uniform(-3, 3), H - 0.05, rng.uniform(-0.6, 0.9)), 0.6, 0.7, FERNC, seed + i, 7, 2)
    for i in range(6):
        x = rng.uniform(-W / 2 + 0.5, W / 2 - 0.5)
        if abs(x + 1.8) > 0.5:
            grass_tufts(m, rng, (x, H, rng.uniform(-1.0, 1.1)), 0.3, 2, 0.4, GRASSC, seed + i, pick=2)


def fo_lip_trunk(p, m, rng, seed):
    """Dead branching trunk lying along X, its thick end on the turf (-X) and its broken crown jutting over the lip."""
    W, H, D = p["size"]
    r = H * 0.38
    pts = [Vector((-W / 2 + 0.3, r * 0.8, 0.0)), Vector((-W / 4, r * 0.95, 0.05)), Vector((0.2, r * 1.0, -0.05)), Vector((W / 4, r * 1.05, 0.05)),
           Vector((W / 2 - 1.2, r * 1.1, 0.0))]
    rings = tube(m, pts, [r * 1.15, r * 1.0, r * 0.9, r * 0.75, r * 0.6], PINEB, 8, twist=0.4, rough=0.15, seed=seed, caps=(True, False))
    tip = pts[-1]
    for j, (dz, dy, L) in enumerate([(0.5, 0.25, 1.4), (-0.45, 0.15, 1.2), (0.05, -0.1, 1.5)]):
        end = tip + Vector((L, dy, dz))
        tube(m, hermite(tip - Vector((0.2, 0, 0)), Vector((1, 0, dz)), end, Vector((1, dy, dz * 0.5)), 4),
             [r * 0.5, r * 0.4, r * 0.3, r * 0.22, r * 0.15], PINEB, 5, rough=0.2, seed=seed + j, caps=(False, True))
    for i in range(3):
        mass(m, (-W * 0.3 + i * W * 0.22, r * 1.85, 0), (W * 0.12, 0.1, r * 0.6), MOSS, seed + i, rough=0.3, rings=4, segs=7, tile=1.2)
    for i in range(4):
        moss_drape(m, rng, (-W * 0.1 + i * 0.6, r * 1.2, rng.uniform(-0.2, 0.2)), rng.uniform(0.6, 1.1), 0.7, DRAPEC, seed + i)


def fo_fall(p, m, rng, seed):
    W, H, D = p["size"]
    n = 8
    pts = [Vector((0, H - 0.05, -0.25)), Vector((0, H - 0.25, 0.15))] + [Vector((0.06 * math.sin(i * 1.3), H - 0.25 - (H - 0.25) * i / n, 0.25 + 0.08 * i / n)) for i in range(1, n + 1)]
    widths = [0.8, 0.85] + [0.85 + 0.45 * i / n for i in range(1, n + 1)]
    sweep(m, pts, widths, 0.12, (1, 0, 0), WATER, 6, uv_len=3.0)
    mass(m, (0, H - 0.1, -0.1), (0.55, 0.12, 0.3), STEM, seed, rough=0.3, rings=3, segs=6, tile=0.5)
    mass(m, (0, 0.05, 0.4), (0.75, 0.15, 0.5), STEM, seed + 1, rough=0.35, rings=3, segs=7, tile=0.5)


def fo_underside(p, m, rng, seed):
    W, H, D = p["size"]
    hole = (H * 0.55, 1.5)
    R.underside_core(m, W * 0.86, H, UNDER, seed, segs=14, tiers=7, hole=hole)
    R.underside_chunks(m, rng, W, H, STONE, seed, hole=hole)
    # tunnel lining through the hole along Z
    reach = W / 2 * 0.86 * (1 - 0.45) ** 0.75 + 0.6
    tp = [Vector((0, hole[0], z)) for z in (-reach, -reach * 0.3, reach * 0.3, reach)]
    tube(m, tp, [hole[1] * 1.05] * 4, STONE, 12, rough=0.15, seed=seed, caps=(False, False))
    # a root coiling around the hole's rim on the front face, and two spiralling roots trailing below the tip
    ring = []
    for i in range(15):
        a = 2 * math.pi * i / 14
        ring.append(Vector((math.cos(a) * hole[1] * 1.35, hole[0] + math.sin(a) * hole[1] * 1.35, reach - 0.2 + 0.15 * math.sin(a * 2))))
    tube(m, ring, [0.24] * 15, ROOTB, 6, rough=0.2, seed=seed, caps=(False, False))
    R.underside_roots(m, rng, W, H, ROOTB, seed, count=2, r=0.38)
    for i in range(12):
        a = rng.uniform(0.2, math.pi - 0.2) * (1 if i % 2 else -1)  # keep the curtains off the hole's faces
        a = a if abs(math.sin(a)) < 0.8 else a + 0.6
        t = rng.uniform(0.05, 0.45)
        Rr = W / 2 * 0.86 * (1 - t) ** 0.8 + 0.2
        moss_drape(m, rng, (math.cos(a) * Rr, H * (1 - t), math.sin(a) * Rr), rng.uniform(1.4, 3.0), 1.2, DRAPEC, seed + i, face=(math.cos(a), 0, math.sin(a)))
    return hole, reach


# ---------- assembly ----------

def build_piece(p, mats):
    seed = (sum(map(ord, p["id"])) % 97) * 0.37
    rng = random.Random(p["id"])
    pid = p["id"]
    m = Mesh()
    fn, flat, up, facing, inward = None, (), (LITTER, NEEDLES), None, None
    crown = None
    stone_moss = R.granite_paint(STONE, MOSS, 0.55, seed, -0.05)
    bark_moss = lambda mi, c, n: MOSS if mi in BARKS and n.y > 0.5 and noise.noise(c * 0.9) > -0.1 else None  # noqa: E731
    if pid == "fo-grudge-tree":
        crown = fo_grudge(p, m, rng, seed)
    elif pid == "fo-pine-a":
        crown = fo_pine(p, m, rng, seed, 13)
    elif pid == "fo-pine-b":
        crown = fo_pine(p, m, rng, seed, 11, slim=0.85)
    elif pid == "fo-birch-a":
        crown = fo_birch(p, m, rng, seed, 5)
    elif pid == "fo-birch-b":
        crown = fo_birch(p, m, rng, seed, 4)
    elif pid == "fo-duskcrown-a":
        crown = fo_dusk(p, m, rng, seed)
    elif pid == "fo-duskcrown-b":
        crown = fo_dusk(p, m, rng, seed, young=True)
    elif pid == "fo-giant-pine":
        crown = fo_giant(p, m, rng, seed)
    elif pid == "fo-fern-clump":
        W, H, _ = p["size"]
        mass(m, (0, 0.02, 0), (W * 0.1, W * 0.06, W * 0.1), MOSS, seed, rings=4, segs=6, rough=0.3)
        fern_cards(m, rng, (0, 0, 0), W / 2 * 0.85, H * 0.9, FERNC, seed, 16, 6)
        fern_cards(m, rng, (0, 0, 0), W / 2 * 0.65, H * 0.75, FERNC, seed + 3, 11, 0, flat=0.15)
        fern_cards(m, rng, (0, 0, 0), W / 2 * 0.5, H * 0.6, FERNC, seed + 5, 7, 0, flat=-0.1)
    elif pid == "fo-bramble":
        fo_bramble(p, m, rng, seed)
    elif pid == "fo-fallen-log":
        fo_log(p, m, rng, seed)
        fn = bark_moss
    elif pid == "fo-broken-stump":
        fo_broken_stump(p, m, rng, seed)
        fn = bark_moss
    elif pid == "fo-mushroom-cluster":
        fo_mushrooms(p, m, rng, seed)
    elif pid == "fo-fireflies-fern":
        fo_fireflies(p, m, rng, seed)
    elif pid == "fo-needle-litter":
        fo_needle_litter(p, m, rng, seed)
    elif pid == "fo-leaf-litter":
        R.rh_litter(p, m, rng, seed, mat=LITTER)
    elif pid == "fo-moss-clump":
        fo_moss_clump(p, m, rng, seed)
        flat = (STONE,)
    elif pid == "fo-surface-roots":
        R.rh_surface_roots(p, m, rng, seed, mat=ROOTB, moss=None)
        W, H, D = p["size"]
        for i in range(1):
            mass(m, (rng.uniform(-0.3, 0.3) * W, -0.03, rng.uniform(-0.3, 0.3) * D), (0.3, 0.06, 0.25), NEEDLES, seed + i, rough=0.3, rings=3, segs=6,
                 flat=0.2, tile=1.0)
    elif pid == "fo-boulder-a":
        W, H, D = p["size"]
        boulder(m, (0, 0, 0), (W * 0.95, H, D * 0.95), STONE, seed, n=40, round_=0.8, rot=0.4)
        boulder(m, (W * 0.4, 0, D * 0.32), (W * 0.28, H * 0.25, D * 0.28), STONE, seed + 1, n=12, round_=0.5)
        fn, flat = stone_moss, (STONE, MOSS)
    elif pid == "fo-boulder-b":
        fo_cluster(p, m, rng, seed)
        fn, flat = stone_moss, (STONE, MOSS)
    elif pid == "fo-split-rock":
        fo_split(p, m, rng, seed)
        fn, flat = stone_moss, (STONE, MOSS)
    elif pid == "fo-slate-slab":
        R.rh_slate_slab(p, m, rng, seed, mat=SLATE, moss=MOSS)
        flat = (SLATE,)
    elif pid == "fo-hollow-outcrop":
        fo_hollow(p, m, rng, seed)
        fn, flat = stone_moss, (STONE, MOSS)
    elif pid == "fo-lip-edge":
        fo_lip(p, m, rng, seed)
        fn, flat = R.granite_paint(STONE, MOSS, 0.6, seed, 0.0), (STONE,)
        facing = {GROUND: UP, MOSS: Vector((0, 0.2, 1)), CLIFF: Vector((0, -1, 0.4))}
    elif pid == "fo-lip-fallen-trunk":
        fo_lip_trunk(p, m, rng, seed)
        fn = bark_moss
    elif pid == "fo-brook-fall":
        fo_fall(p, m, rng, seed)
    elif pid == "fo-underside-hollow":
        hole, reach = fo_underside(p, m, rng, seed)
        flat = (STONE, UNDER)
        fn = R.granite_paint(STONE, MOSS, 0.55, seed, 0.1)
        inward = (Vector((0, hole[0], 0)), Vector((0, 0, 1)), hole[1] * 1.1)
    else:
        raise ValueError(pid)
    ob = m.object(pid, mats, moss=None, seed=seed)
    if crown is not None:
        cc, cr = crown
        fn = R.tree_paint(SHADE, cc, cr, bark=BARKS, moss=MOSS, seed=seed)
    return R.post(ob, fn, flat, up, inward=inward, facing=facing)


if __name__ == "__main__":
    K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/forest"), cap_mat=HEART, moss=None)
    only, out = R.cli()
    if only:
        R.preview(build_piece, only, out or "/tmp/fo-preview")
    else:
        K.build_all(build_piece, extras=[(p["id"], R.category(p)) for p in B.kit["pieces"]], biome="forest")
