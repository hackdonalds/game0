# Garden nature kit: apple trees, windbreak poplars, hedgerows, modular crop plots (furrows, wheat, flax,
# cabbages, leeks), herb and flower beds, fence, scarecrow, haystack, well, dry-stone and terrace walls, clay
# bank, the terrace lip and underside, fishpond, irrigation channel and trickle, built from
# art/models/nature/garden/kit.json on the painted swatches in art/textures/biomes/garden.
# Shares the generators in nature-meadow.py (loaded as a module). Material slots 0..24 line up with the meadow
# slots so those generators work unchanged; garden-only materials follow.
# Usage: Blender --background --python scripts/kit/nature-garden.py -- garden [--only id,id] [--close dir]
import importlib.util, math, os, random, sys
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import blockout as B  # noqa: E402
import kitlib as K  # noqa: E402
from kitlib import Mesh, hermite, tube  # noqa: E402

_spec = importlib.util.spec_from_file_location("nature_meadow", os.path.join(os.path.dirname(__file__), "nature-meadow.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
UP = M.UP
lobed, masses, limb, trunk, stone, frame_xf, drystone, head, spike, tuft, ivy, pebble = (
    M.lobed, M.masses, M.limb, M.trunk, M.stone, M.frame_xf, M.drystone, M.head, M.spike, M.tuft, M.ivy, M.pebble)

# Slots 0..24 mirror the meadow slots (TURF in the meadow's GROUND slot, the terrace wall swatch as CLIFF, ...)
MATS = [("GD_Turf", "turf.png", 0), ("GD_FieldPath", "path.png", 0), ("GD_TerraceWall", "cliff.png", 0),
        ("GD_ClayUnderside", "underside.png", 0), ("GD_PoplarBark", "fruitwood-bark.png", 0), ("GD_FruitwoodBark", "fruitwood-bark.png", 0),
        ("GD_HedgeFoliage", "hedge.png", 0), ("GD_AppleFoliage", "apple-leaf.png", 0), ("GD_PoplarFoliageSun", "poplar-sun.png", 0),
        ("GD_FoliageShade", "leaf-shade.png", 0), ("GD_BlossomFoliage", "blossom.png", 0), ("GD_BlossomPinkFoliage", "blossom.png", 0),
        ("GD_FlowerFoliage", "flowers.png", 0), ("GD_WildflowerFoliage", "wildflowers.png", 0), ("GD_GrassFoliage", "long-grass.png", 0),
        ("GD_CloverFoliage", "clover.png", 0), ("GD_Limestone", "limestone.png", 0), ("GD_WarmClay", "clay.png", 0),
        ("GD_Water", "water.png", 0), ("GD_Waterfall", "waterfall.png", 0.15), ("GD_PetalWhiteFoliage", "petal-white.png", 0),
        ("GD_PetalYellowFoliage", "petal-yellow.png", 0), ("GD_PetalPinkFoliage", "petal-pink.png", 0),
        ("GD_LavenderFoliage", "lavender.png", 0), ("GD_TilledSoil", "ground.png", 0),
        # garden only
        ("GD_PoplarFoliage", "poplar-leaf.png", 0), ("GD_WheatFoliage", "wheat.png", 0), ("GD_FlaxFoliage", "flax.png", 0),
        ("GD_CabbageFoliage", "cabbage.png", 0), ("GD_LeekFoliage", "leek.png", 0), ("GD_HerbFoliage", "herbs.png", 0),
        ("GD_Straw", "straw.png", 0), ("GD_WeatheredWood", "weathered-wood.png", 0), ("GD_Linen", "linen.png", 0),
        ("GD_Rope", "rope.png", 0), ("GD_Shingles", "shingles.png", 0), ("GD_PetalBlueFoliage", "petal-blue.png", 0),
        ("GD_PetalRedFoliage", "petal-red.png", 0), ("GD_Sash", "sash.png", 0), ("GD_SpikeVioletFoliage", "spike-violet.png", 0),
        ("GD_SpikePinkFoliage", "spike-pink.png", 0),
        # alpha-cutout sprite cards (art/textures/foliage, 2x2 atlases)
        ("GD_Leaf_Foliage_Card", "../../foliage/broadleaf-green.png", 0), ("GD_LeafShade_Foliage_Card", "../../foliage/broadleaf-dark.png", 0),
        ("GD_Birch_Foliage_Card", "../../foliage/birch.png", 0), ("GD_Blossom_Foliage_Card", "../../foliage/blossom.png", 0),
        ("GD_Grass_Foliage_Card", "../../foliage/grass.png", 0), ("GD_Ivy_Foliage_Card", "../../foliage/ivy-moss.png", 0),
        ("GD_Elder_Foliage_Card", "../../foliage/elder-blossom.png", 0)]
(TURF, PATH, TERRACE, UNDER, POPBARK, BARK, HEDGE, APPLE, POPSUN, SHADE, BLOSSOM, BLOSSOM_P, FLOWERS, WILD, GRASS, CLOVER, LIME,
 CLAY, WATER, FALL, P_WHITE, P_YELLOW, P_PINK, LAVENDER, SOIL, POPLAR, WHEAT, FLAX, CABBAGE, LEEK, HERB, STRAW, WOOD, LINEN, ROPE,
 SHINGLE, P_BLUE, P_RED, SASH, SPIKE_V, SPIKE_P, C_LEAF, C_DARK, C_BIRCH, C_BLOSSOM, C_GRASS, C_IVY, C_ELDER) = range(len(MATS))
M.CARDS = {"leaf": C_LEAF, "dark": C_DARK, "birch": C_BIRCH, "blossom": C_BLOSSOM, "grass": C_GRASS, "ivy": C_IVY, "elder": C_ELDER, "core": SHADE}
grass, leaf_crown = M.grass, M.leaf_crown

# Branch ends show fruitwood; moss (the turf swatch) settles on upward-facing limestone
K.configure(MATS, os.path.join(B.ROOT, "art/textures/biomes/garden"), cap_mat=BARK, moss=(LIME, TURF, 0.62))


# ---------- trees ----------

def poplar(p, mats, seed, blunt=False):
    """Windbreak poplar: short straight trunk under a tall narrow column of stacked leaf-card lobes round a hidden
    dark spindle, tapering to a point (A) or a blunter top (B)."""
    m = Mesh()
    rng = random.Random(seed)
    W, H = p["size"][0], p["size"][1]
    trunk(m, (0, -0.25, 0), (0.05, H * 0.45, 0.0), Vector((0.02, 1, 0)), 0.2, 0.09, POPBARK, sides=7, n=6, seed=seed, flare=1.4,
          rough=0.12, twist=0.4)
    base, top = H * 0.12, H * 0.97
    if blunt:
        prof = lambda t: max(0.14, min(1.0, 1.25 * math.sin(math.pi * min(1.0, t) ** 0.62) ** 0.6))
    else:
        prof = lambda t: max(0.1, math.sin(math.pi * min(1.0, t * 1.02) ** 0.9) ** 0.8)
    # dark core spindle so the column never shows sky through it
    core = [Vector((0, base + (top - base) * t, 0)) for t in (0.0, 0.25, 0.5, 0.75, 0.95)]
    tube(m, core, [W * 0.24 * prof(t) for t in (0.02, 0.25, 0.5, 0.75, 0.95)], SHADE, 7, rough=0.2, seed=seed, caps=(True, True), tile=1.0)
    n = 10
    step = (top - base) / n
    lobes = []
    for i in range(n):
        t = (i + 0.5) / n
        r = W * 0.36 * prof(t)
        a = rng.uniform(0, 2 * math.pi)
        off = Vector((math.cos(a), 0, math.sin(a))) * r * 0.15
        lobes.append((Vector((off.x, base + (top - base) * t, off.z)), (r, step * 0.8, r)))
    lobes.append((Vector((0, top + step * 0.1, 0)), (W * 0.1, step * 0.5, W * 0.1)))
    leaf_crown(m, lobes, [(C_LEAF, 4, None), (C_BIRCH, 3, None)], seed, total=1000 if blunt else 900, size=(0.8, 1.2),
               centre=(0, (base + top) / 2, 0), up_bias=0.5, shade=(C_DARK, None), shade_low=0.15, fill=0.1)
    tuft(m, (0, 0, 0), 0.4, 0.35, GRASS, seed=seed, count=14)
    return m.object(p["id"], mats, seed=seed)


# ---------- crop plots (bottom-left-front: x 0..2, z -2..0) ----------

def furrows(m, w, d, ridges, nx, amp=0.07, base=0.08, mat=SOIL, skirt=True, rot=-0.42, seed=0.0):
    """Ridged soil bed: ridges run along X, `ridges` across the depth. Painted furrows in the soil swatch are
    turned (rot) to lie along the modelled ridges. Returns the ridge-top z positions."""
    nz = ridges * 4
    ca, sa = math.cos(rot), math.sin(rot)
    grid = []
    for i in range(nx + 1):
        x = w * i / nx
        row = []
        for j in range(nz + 1):
            z = -d * j / nz
            edge = 1.0 if 0 < j < nz and 0 < i < nx else 0.0
            y = base + (amp * math.cos(2 * math.pi * (j - 2) / 4) + 0.015 * noise.noise(Vector((x * 3, z * 3, seed)))) * edge
            u, v = x / 1.6, z / 1.6
            row.append((m.vert((x, y, z)), (u * ca - v * sa, u * sa + v * ca)))
        grid.append(row)
    for i in range(nx):
        for j in range(nz):
            a, b, c, e = grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]
            m.face((a[0], e[0], c[0], b[0]), (a[1], e[1], c[1], b[1]), mat)
    if skirt:
        for side in (0, nx):
            col = grid[side]
            for j in range(nz):
                a, b = col[j][0], col[j + 1][0]
                lo_a, lo_b = m.vert((w * side / nx, 0, -d * j / nz)), m.vert((w * side / nx, 0, -d * (j + 1) / nz))
                m.face((lo_a, lo_b, b, a), None, mat, 1.0)
        for j in (0, nz):
            for i in range(nx):
                a, b = grid[i][j][0], grid[i + 1][j][0]
                lo_a, lo_b = m.vert((w * i / nx, 0, -d * j / nz)), m.vert((w * (i + 1) / nx, 0, -d * j / nz))
                m.face((lo_a, a, b, lo_b), None, mat, 1.0)
    return [-d * (4 * r + 2) / nz for r in range(ridges)], [-d * (4 * r) / nz for r in range(ridges)]


def crop_wall(m, rng, x0, x1, z, h, mat, segs=16, lean=0.08, jag=0.08, v_top=1.0, seed=0.0):
    """A row of standing crop: a vertical double-sided strip whose top edge is ragged (ears and flower heads),
    swaying slightly in and out of the row, u along the row, v up the stalks."""
    prev = None
    for i in range(segs + 1):
        x = x0 + (x1 - x0) * i / segs
        dz = 0.05 * math.sin(i * 1.3 + seed)
        top = h * (1 - jag + jag * 2 * ((i * 7 + int(seed * 10)) % 3) / 2) * rng.uniform(0.92, 1.04)
        b = m.vert((x, 0.08, z + dz))
        t = m.vert((x + rng.uniform(-0.03, 0.03), top, z + dz + lean))
        u = x / 0.9
        if prev:
            m.face((prev[0], b, t, prev[1]), ((prev[2], 0), (u, 0), (u, v_top), (prev[2], v_top)), mat)
        prev = (b, t, u)


def crop_plot(p, mats, seed):
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    pid = p["id"]
    if pid.endswith("furrows"):
        ridge, trough = furrows(m, w, d, 5, 6, amp=0.07, base=0.1, seed=seed)
        base_y = 0.17
        for k, z in enumerate(ridge):  # spring seedlings along the ridges
            for i in range(5):
                x = 0.2 + 0.4 * i + rng.uniform(-0.05, 0.05)
                head(m, (x, base_y + 0.1, z), 0.06, HEDGE, seed=seed + k * 5 + i, petals=2, cup=0.9)
    elif pid.endswith("wheat") or pid.endswith("flax"):
        crop = WHEAT if pid.endswith("wheat") else FLAX
        ridge, trough = furrows(m, w, d, 5, 2, amp=0.04, base=0.08, seed=seed, skirt=False)
        for k in range(5):
            z = -0.2 - 0.4 * k
            n = 3 if crop == WHEAT else 2
            for j in range(n):
                crop_wall(m, rng, 0.0, w, z + (j - (n - 1) / 2) * 0.13, h * (0.95 if crop == WHEAT else 0.82) * rng.uniform(0.92, 1.0), crop,
                          segs=14 if crop == WHEAT else 13, lean=0.1 * (1 if j % 2 else -1), jag=0.035, seed=seed + k * 3 + j)
        if crop == FLAX:
            for k in range(16):
                head(m, (rng.uniform(0.1, w - 0.1), h * 0.8 * rng.uniform(0.92, 1.02), -0.2 - 0.4 * rng.randrange(5) + rng.uniform(-0.12, 0.12)),
                     0.06, P_BLUE, seed=seed + k)
    elif pid.endswith("cabbage"):
        furrows(m, w, d, 3, 3, amp=0.05, base=0.08, seed=seed)
        for i in range(3):
            for j in range(3):
                x, z = 0.35 + 0.65 * i + rng.uniform(-0.05, 0.05), -0.33 - 0.67 * j + rng.uniform(-0.05, 0.05)
                r = rng.uniform(0.25, 0.3)
                lobed(m, (x, 0.12 + r * 0.45, z), (r, r * 0.8, r), CABBAGE, seed=seed + i * 3 + j, lobes=6, depth=0.3, rings=4, segs=8, tile=0.55,
                      flat=0.4)
    else:  # leeks
        furrows(m, w, d, 3, 3, amp=0.05, base=0.08, seed=seed)
        for j in range(3):
            for i in range(6):
                x, z = 0.17 + 0.33 * i + rng.uniform(-0.04, 0.04), -0.33 - 0.67 * j
                tuft(m, (x, 0.1, z), 0.12, h * 0.85, LEEK, seed=seed + i + j * 6, count=3, width=0.055, lean=0.35)
    return m.object(pid, mats, seed=seed)


# ---------- beds and props ----------

def stone_box(m, rng, w, d, h, courses=2):
    """Low pale dry-stone box (bottom-center), walls 0.28 thick, with the bed's soil fill."""
    t = 0.28
    runs = [((-w / 2, 0, d / 2), (1, 0, 0), (0, 0, -1), w), ((w / 2, 0, -d / 2), (-1, 0, 0), (0, 0, 1), w),
            ((-w / 2, 0, -d / 2 + t), (0, 0, 1), (1, 0, 0), d - 2 * t), ((w / 2, 0, d / 2 - t), (0, 0, -1), (-1, 0, 0), d - 2 * t)]
    for o, u, wd, L in runs:
        drystone(m, rng, L, h, t, courses, LIME, frame_xf(o, u, wd), core=None, lmin=0.4, lmax=0.7, batter=0.02, pillow=0.0)
    vs = [m.vert((-w / 2 + t, h * 0.82, d / 2 - t)), m.vert((w / 2 - t, h * 0.82, d / 2 - t)), m.vert((w / 2 - t, h * 0.82, -d / 2 + t)),
          m.vert((-w / 2 + t, h * 0.82, -d / 2 + t))]
    m.face(vs, None, SOIL, 1.0)


def bed(p, mats, seed, herbs=True):
    rng = random.Random(seed)
    w, hh, d = p["size"]
    m = Mesh()
    stone_box(m, rng, w, d, 0.36, courses=2)
    box = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    y0 = 0.3
    if herbs:
        for k, (x, z, r) in enumerate([(-0.5, 0.0, 0.32), (-0.2, -0.15, 0.28)]):
            lobed(g, (x, y0 + r * 0.6, z), (r, r * 0.8, r), LAVENDER, seed=seed + k, lobes=6, depth=0.35, rings=4, segs=7, tile=0.4, flat=0.4)
        for k in range(7):
            spike(g, (-0.7 + 0.1 * k, y0 + 0.2, rng.uniform(-0.25, 0.15)), (hh - y0 - 0.1) * rng.uniform(0.75, 1.0), 0.028, SPIKE_V, seed=seed + k,
                  sides=3, bend=0.3)
        # leafy sage and lovage clumps: small dark broadleaf cards; rosemary as grass-like spears
        leaf_crown(g, [((0.15, y0 + 0.2, 0.05), (0.28, 0.2, 0.25)), ((0.4, y0 + 0.15, -0.15), (0.2, 0.15, 0.18))],
                   [(C_DARK, 2, None), (C_LEAF, 1, None)], seed + 5, total=60, size=(0.32, 0.45), centre=(0.25, y0, 0), up_bias=0.6)
        grass(g, (0.62, y0 - 0.02, 0.0), 0.2, hh - y0, seed=seed, quad=1, planes=3)
    else:
        leaf_crown(g, [((-0.45, y0 + 0.2, 0.05), (0.33, 0.22, 0.3)), ((0.25, y0 + 0.2, 0.08), (0.32, 0.22, 0.3))],
                   [(C_BLOSSOM, 2, None), (C_ELDER, 1, None)], seed, total=80, size=(0.42, 0.58), centre=(0, y0, 0), up_bias=0.6,
                   shade=(C_DARK, None), shade_low=0.25)
        for k in range(3):
            spike(g, (0.0 + 0.3 * k - 0.3, y0 + 0.1, -0.22), hh - y0 - 0.05, 0.05, SPIKE_P, seed=seed + k, sides=4)
            for j in range(2):
                head(g, (0.3 * k - 0.3 + 0.06 * (j * 2 - 1), y0 + (hh - y0) * (0.45 + 0.2 * j), -0.16), 0.08, P_PINK, seed=seed + k * 2 + j)
        for k in range(8):
            head(g, (rng.uniform(-0.75, 0.75), y0 + rng.uniform(0.25, 0.45), rng.uniform(-0.25, 0.3)), 0.07, (P_WHITE, P_YELLOW, P_WHITE)[k % 3],
                 seed=seed + k)
    return K.join([box, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def fence(p, mats, seed):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    z = -d / 2
    for x in (0.12, w - 0.12):
        tube(m, [(x, -0.15, z), (x + 0.01, h * 0.5, z), (x, h, z)], [0.08, 0.075, 0.07], WOOD, 5, rough=0.2, seed=seed + x, tile=0.6)
    for k, y in enumerate((h * 0.42, h * 0.8)):
        sag = 0.03
        tube(m, [(0.0, y, z + 0.08), (w * 0.33, y - sag, z + 0.09), (w * 0.66, y - sag + 0.01, z + 0.08), (w, y, z + 0.08)], [0.055] * 4, WOOD, 5,
             rough=0.25, seed=seed + k, tile=0.8, caps=(True, True))
        for x in (0.12, w - 0.12):  # rope lashings
            tube(m, [(x - 0.09, y + 0.05, z + 0.02), (x, y - 0.05, z + 0.15), (x + 0.09, y + 0.05, z + 0.02)], [0.025] * 3, ROPE, 3, tile=0.3,
                 caps=(False, False))
    ob = m.object(p["id"], mats, seed=seed)
    g = Mesh()
    tuft(g, (0.15, 0, z + 0.1), 0.25, 0.3, GRASS, seed=seed, count=4)
    tuft(g, (w - 0.15, 0, z + 0.1), 0.25, 0.3, GRASS, seed=seed + 1, count=3)
    hard = Mesh()
    pebble(hard, (0.35, 0, z + 0.18), (0.22, 0.14, 0.18), LIME, seed=seed, rings=3, segs=5)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed), hard.object(p["id"] + ".st", mats, seed=seed, smooth=False)], p["id"])


def scarecrow(p, mats, seed):
    m = Mesh()
    w, h, d = p["size"]
    tube(m, [(0, -0.2, 0), (0.01, 1.0, 0), (0, 1.75, 0)], [0.05, 0.05, 0.045], WOOD, 5, rough=0.2, seed=seed, tile=0.6)
    arm = 0.62
    tube(m, [(-arm - 0.05, 1.42, 0), (0, 1.44, 0), (arm + 0.05, 1.41, 0)], [0.04] * 3, WOOD, 4, rough=0.2, seed=seed, tile=0.6)
    # shirt body, sleeves, sash
    tube(m, [(0, 0.88, 0), (0, 1.1, 0.01), (0, 1.38, 0), (0, 1.5, 0)], [0.2, 0.22, 0.25, 0.12], LINEN, 8, rough=0.2, seed=seed, tile=0.8)
    for s in (-1, 1):
        tube(m, [(s * 0.1, 1.42, 0), (s * 0.35, 1.43, 0.01), (s * 0.55, 1.41, 0)], [0.12, 0.1, 0.09], LINEN, 6, rough=0.25, seed=seed + s, tile=0.6,
             caps=(False, True))
        tuft(m, (s * 0.57, 1.41, 0), 0.12, 0.16, STRAW, seed=seed + s, count=4, width=0.03, lean=1.4)
    tube(m, [(0, 0.98, 0), (0, 1.06, 0)], [0.23, 0.23], SASH, 8, caps=(False, False), tile=0.4)
    tube(m, [(0.16, 1.0, 0.12), (0.22, 0.82, 0.16)], [0.04, 0.03], SASH, 4, tile=0.3)
    tuft(m, (0, 0.86, 0), 0.15, 0.18, STRAW, seed=seed + 3, count=4, width=0.03, lean=1.2)
    # burlap head and straw hat
    lobed(m, (0, 1.68, 0), (0.15, 0.17, 0.14), LINEN, seed=seed, lobes=4, depth=0.15, rings=5, segs=7, tile=0.3)
    tube(m, [(0, 1.76, 0), (0, 1.79, 0), (0, 1.83, 0), (0, 1.97, 0), (0, 2.02, 0)], [0.36, 0.33, 0.16, 0.13, 0.03], STRAW, 10, rough=0.08,
         seed=seed, tile=0.5, caps=(True, False))
    tuft(m, (0, 0, 0), 0.25, 0.3, GRASS, seed=seed, count=4)
    return m.object(p["id"], mats, seed=seed)


def haystack(p, mats, seed):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    ys = [-0.1, 0.25, 0.8, 1.4, 1.9, 2.25, 2.35]
    rs = [1.42, 1.45, 1.32, 1.02, 0.62, 0.22, 0.04]
    tube(m, [Vector((0.03 * math.sin(i), y, 0.03 * math.cos(i))) for i, y in enumerate(ys)], rs, STRAW, 14, rough=0.12, seed=seed, tile=1.2,
         caps=(False, False))
    tuft(m, (0, 2.3, 0), 0.2, 0.3, STRAW, seed=seed, count=5, width=0.05, lean=1.0)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        tuft(m, (math.cos(a) * 1.4, 0, math.sin(a) * 1.4), 0.35, 0.35, STRAW, seed=seed + k, count=3, width=0.05, lean=1.2)
    for k, a in enumerate((0.5, 2.6)):  # props leaning on the stack
        foot = Vector((math.cos(a) * 1.85, 0, math.sin(a) * 1.85))
        topp = Vector((math.cos(a) * 1.0, 1.75, math.sin(a) * 1.0))
        tube(m, [foot, topp], [0.05, 0.04], WOOD, 4, tile=0.6)
    return m.object(p["id"], mats, seed=seed)


def well(p, mats, seed):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    R, t, hw = 0.85, 0.32, 0.85
    n = 8
    for c in range(3):
        v0 = c * hw / 3
        off = (c % 2) * 0.5
        for k in range(n):
            a0 = 2 * math.pi * (k + off) / n
            a1 = 2 * math.pi * (k + off + 1) / n - 0.06
            mid = (a0 + a1) / 2
            ch = 2 * (R + t / 2) * math.sin((a1 - a0) / 2)
            o = Vector((math.cos(mid) * (R + t), 0, math.sin(mid) * (R + t)))
            u = Vector((-math.sin(mid), 0, math.cos(mid)))
            stone(m, (-ch / 2, v0 + 0.015, 0), (ch / 2, v0 + hw / 3 - 0.015, t), LIME, rng, frame_xf(o - u * 0, u, -o.normalized()),
                  pillow=0.03, taper=0.025)
    walls = m.object(p["id"], mats, seed=seed, smooth=False)
    s = Mesh()
    # water far down, posts, beam, gable roof, pulley, rope and bucket
    wl = [s.vert((math.cos(a) * R * 1.02, 0.35, math.sin(a) * R * 1.02)) for a in (2 * math.pi * k / 8 for k in range(8))]
    s.face(wl[::-1], [(0.5 + 0.5 * math.cos(2 * math.pi * k / 8), 0.5 + 0.5 * math.sin(2 * math.pi * k / 8)) for k in range(8)][::-1], WATER)
    for x in (-R - t / 2, R + t / 2):
        tube(s, [(x, 0.3, 0), (x, 1.5, 0), (x * 0.98, 2.45, 0)], [0.09, 0.085, 0.08], WOOD, 5, rough=0.15, seed=seed + x, tile=0.7)
    tube(s, [(-R - 0.35, 2.38, 0), (R + 0.35, 2.4, 0)], [0.07, 0.07], WOOD, 5, tile=0.8)
    ridge, eave, half = 3.0, 2.25, 0.95
    L = R + t + 0.35
    for sgn in (-1, 1):
        # shingled roof: three overlapping rows of split boards, each tilted and nudged a little
        rows_ = 3
        for r in range(rows_):
            t0, t1 = r / rows_, (r + 1) / rows_ + 0.12
            n_b = 6
            for k in range(n_b):
                x0 = -L + 2 * L * k / n_b + 0.01
                x1 = -L + 2 * L * (k + 1) / n_b - 0.01
                lift = 0.035 * (rows_ - r) + rng.uniform(0.0, 0.02)
                p0 = lambda x, t: Vector((x, ridge + (eave - ridge) * t + lift, sgn * half * t))
                tw = rng.uniform(-0.03, 0.03)
                vs = [s.vert(p0(x0, t1) + Vector((0, tw, 0))), s.vert(p0(x1, t1) - Vector((0, tw, 0))), s.vert(p0(x1, t0)), s.vert(p0(x0, t0))]
                ou, ov = rng.random(), rng.random()
                uv = [(ou, ov), (ou + 0.35, ov), (ou + 0.35, ov + 0.5), (ou, ov + 0.5)]
                s.face(vs if sgn > 0 else vs[::-1], uv if sgn > 0 else uv[::-1], WOOD)
        a2, b2 = s.vert((-L, ridge - 0.02, 0)), s.vert((L, ridge - 0.02, 0))
        c2, e2 = s.vert((L, eave - 0.02, sgn * half)), s.vert((-L, eave - 0.02, sgn * half))
        s.face((a2, e2, c2, b2) if sgn > 0 else (b2, c2, e2, a2), None, WOOD, 0.8)
    tube(s, [(-L - 0.05, ridge + 0.12, 0), (L + 0.05, ridge + 0.12, 0)], [0.07, 0.07], WOOD, 5, tile=0.8)
    for x in (-L * 0.98, L * 0.98):
        s.face((s.vert((x, ridge, 0)), s.vert((x, eave, half)), s.vert((x, eave, -half))), None, WOOD, 0.8)
    tube(s, [(0, 2.4, -0.06), (0, 2.4, 0.06)], [0.18, 0.18], WOOD, 8, tile=0.5)
    tube(s, [(0.18, 2.4, 0), (0.18, 1.55, 0)], [0.015, 0.015], ROPE, 3, tile=0.2, caps=(False, False))
    tube(s, [(0.18, 1.2, 0), (0.18, 1.5, 0)], [0.14, 0.17], WOOD, 8, tile=0.5, caps=(True, False))
    tube(s, [(R + 0.65, 0.0, 0.55), (R + 0.65, 0.32, 0.55)], [0.17, 0.2], WOOD, 8, tile=0.5, caps=(True, False))
    tuft(s, (-R - 0.4, 0, 0.5), 0.3, 0.35, GRASS, seed=seed, count=4)
    tuft(s, (R + 0.3, 0, -0.6), 0.3, 0.3, GRASS, seed=seed + 1, count=3)
    return K.join([walls, s.object(p["id"] + ".roof", mats, seed=seed)], p["id"])


# ---------- walls and banks ----------

def terrace_wall(p, mats, seed):
    """Retaining wall, 4 m, 2 m high for x 0..2 then 1 m for x 2..4, turf caps running back to z = -1."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    dep = 0.55
    for x0, x1, hh, nc in ((0.0, 2.0, 2.0, 6), (2.0, 4.0, 1.0, 3)):
        drystone(m, rng, x1 - x0, hh - 0.1, dep, nc, LIME, frame_xf((x0, 0, 0), (1, 0, 0), (0, 0, -1)), core=None, lmin=0.48, lmax=0.8,
                 batter=0.04, pillow=0.04, back=False)
    # the exposed end of the high section above the step
    drystone(m, rng, dep, 1.0 - 0.1, 0.25, 3, LIME, frame_xf((2.0, 1.0, 0), (0, 0, -1), (-1, 0, 0)), core=None, lmin=0.6, lmax=0.6, batter=0.0,
             back=False)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    for x0, x1, hh in ((0.0, 2.0, 2.0), (2.0, 4.0, 1.0)):
        lobed(g, ((x0 + x1) / 2, hh - 0.08, -d / 2 + 0.02), ((x1 - x0) / 2 + 0.06, 0.16, d / 2 + 0.02), TURF, seed=seed + x0, lobes=8, depth=0.3,
              rings=4, segs=12, tile=1.2, flat=0.3, up=0.0)
        for k in range(2):
            ivy(g, Vector((x0 + 0.4 + 1.0 * k + rng.uniform(-0.1, 0.1), hh - 0.05, 0.05)), rng.uniform(0.35, hh * 0.45), HEDGE, seed=seed + k + x0,
                width=0.18, outward=Vector((0, 0, 0.5)), sides=4, n=5)
    tuft(g, (3.3, 0, 0.12), 0.3, 0.3, GRASS, seed=seed, count=4)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def broken_wall(p, mats, seed):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    drystone(m, rng, w, 0.55, 0.5, 2, LIME, frame_xf((0, 0, 0), (1, 0, 0), (0, 0, -1)), core=CLAY, ragged=0.55, lmin=0.35, lmax=0.6)
    for k in range(7):  # tumbled rubble
        a = rng.uniform(-1.2, 1.2)
        x, y = rng.uniform(0.2, w - 0.5), (0.55 if k < 2 else 0.0)
        z = rng.uniform(-0.45, 0.25) if k >= 2 else -0.3
        stone(m, (0, 0, 0), (rng.uniform(0.25, 0.4), rng.uniform(0.16, 0.22), rng.uniform(0.2, 0.3)), LIME, rng,
              frame_xf((x, y, z), (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a))), taper=0.05)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    for k in range(3):
        tuft(g, (rng.uniform(0.2, w - 0.2), 0, rng.uniform(-0.3, 0.1)), 0.3, 0.32, GRASS, seed=seed + k, count=4)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def clay_bank(p, mats, seed):
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    lobed(m, (0, -0.15, 0), (w * 0.46, h * 0.75, d * 0.45), CLAY, seed=seed, lobes=7, depth=0.3, rough=0.2, rings=6, segs=12, tile=1.2, flat=0.3,
          up=-0.2)
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi)
        s = rng.uniform(0.15, 0.28)
        pebble(m, (math.cos(a) * w * 0.52, 0, math.sin(a) * d * 0.5), (s * 1.3, s * 0.8, s), CLAY, seed=seed + k, rings=3, segs=5)
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    lobed(g, (0, h * 0.62, 0), (w * 0.4, 0.28, d * 0.38), TURF, seed=seed, lobes=6, depth=0.3, rings=4, segs=10, tile=1.2, flat=0.35)
    for k in range(9):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.85
        head(g, (math.cos(a) * r * w * 0.34, h * 0.62 + 0.28 * (1 - r * r) + 0.06, math.sin(a) * r * d * 0.34), 0.07, (P_WHITE, P_WHITE, P_YELLOW)[k % 3], seed=seed + k)
    tuft(g, (w * 0.3, h * 0.7, d * 0.2), 0.3, 0.3, GRASS, seed=seed, count=4)
    tuft(g, (-w * 0.25, h * 0.75, -d * 0.1), 0.3, 0.3, GRASS, seed=seed + 1, count=4)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def underside_terrace(p, mats, seed):
    w, h, d = p["size"]

    def courses(m, rng):
        # two terrace wall courses stepping down into the rock below the turf rim
        outline = M.oval(w, d, 16, seed=seed, rough=0.12)
        M.ring_band(m, outline, [h, h - 0.9, h - 0.9, h - 1.8, h - 1.8, h - 2.4], [1.0, 1.0, 0.94, 0.94, 0.88, 0.86], TERRACE, tile=2.2,
                    v_span=0.9)
        cap = [m.vert((x, h, z)) for x, z in outline]
        m.face(cap[::-1], None, TURF, 2.0)

    return M.underside_piece(p, mats, seed, rock=UNDER, turf=TURF, ivy_mat=HEDGE, root=BARK, extra=courses, rock_top=h - 2.2, inset=0.87)


def channel(p, mats, seed):
    """Irrigation channel, bottom-left-front pivot (x 0..2, z -0.5..0): a narrow stone-lined trough with flat cap
    stones along both edges and a water strip."""
    rng = random.Random(seed)
    w, h, d = p["size"]
    m = Mesh()
    zc = -d / 2
    prof = [(-0.25, 0.22), (-0.11, 0.2), (-0.09, 0.06), (0.09, 0.06), (0.11, 0.2), (0.25, 0.22)]
    rows = []
    for x in (0.0, w / 2, w):
        rows.append([(m.vert((x, y, zc + z)), (x / 1.0, z / 0.5 + y)) for z, y in prof])
    for i in range(2):
        for j in range(len(prof) - 1):
            a, b, c, e = rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]
            m.face((a[0], e[0], c[0], b[0]), (a[1], e[1], c[1], b[1]), TURF if j in (0, 4) else LIME)
    vs = [m.vert((0, 0.13, zc - 0.09)), m.vert((0, 0.13, zc + 0.09)), m.vert((w, 0.13, zc + 0.09)), m.vert((w, 0.13, zc - 0.09))]
    m.face(vs, [(0, 0), (0, 0.3), (2, 0.3), (2, 0)], WATER)
    for side in (-1, 1):
        x = 0.0
        while x < w - 1e-3:
            x1 = min(w, x + rng.uniform(0.38, 0.5))
            if w - x1 < 0.2:
                x1 = w
            stone(m, (x + (0.015 if x > 0 else 0), 0.16, 0), (x1 - (0.015 if x1 < w else 0), 0.28, 0.16), LIME, rng,
                  frame_xf((0, 0, zc + side * 0.09 + (0.16 if side < 0 else 0) * 0), (1, 0, 0), (0, 0, side)), pillow=0.02, taper=0.02)
            x = x1
    ob = m.object(p["id"], mats, seed=seed, smooth=False)
    g = Mesh()
    tuft(g, (rng.uniform(0.3, 1.7), 0.2, -0.02), 0.2, 0.25, GRASS, seed=seed, count=3)
    return K.join([ob, g.object(p["id"] + ".g", mats, seed=seed)], p["id"])


def fishpond(p, mats, seed):
    w, h, d = p["size"]
    n = 28
    outline = []
    for k in range(n):  # rounded rectangle (superellipse)
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        outline.append((w / 2 * math.copysign(abs(c) ** 0.45, c), d / 2 * math.copysign(abs(s) ** 0.45, s)))

    def kerb(hard, rng):
        drystone(hard, rng, w * 0.82, 0.28, 0.36, 1, LIME, frame_xf((-w * 0.41, 0, d / 2 - 0.08), (1, 0, 0), (0, 0, -1)), core=None,
                 lmin=0.4, lmax=0.6, batter=0.0, pillow=0.03)

    return M.pond(p, mats, seed, rim_mat=TURF, water=WATER, stone_mat=LIME, reeds=GRASS, pads=CLOVER, outline=outline, n_stones=0, extra=kerb)


# ---------- dispatch ----------

def build_piece(p, mats):
    import bpy
    bpy.context.scene.display.shading.show_specular_highlight = False
    M.grade_cards(mats)
    pid = p["id"]
    seed = M.seed_of(pid)
    if pid == "gd-orchard-a":
        return M.orchard(p, mats, seed, leaves=[(C_BLOSSOM, 3, M.WHITE_BLOSSOM), (C_LEAF, 2, None)], crown_semi=(0.36, 0.22), cy_frac=0.66)
    if pid == "gd-orchard-b":
        return M.orchard(p, mats, seed, leaning=True, leaves=[(C_BLOSSOM, 3, M.PINK_BLOSSOM), (C_LEAF, 2, None)], crown_semi=(0.38, 0.17),
                         cy_frac=0.68, split=1.0)
    if pid.startswith("gd-poplar"):
        return poplar(p, mats, seed, blunt=pid.endswith("-b"))
    if pid == "gd-hedgerow-4m":
        return M.hedgerow(p, mats, seed, leaves=[(C_LEAF, 5, None), (C_ELDER, 1, None), (C_DARK, 1, None)],
                          flowers=(P_WHITE, P_PINK, P_WHITE, P_WHITE), spikes=())
    if pid == "gd-hedgerow-corner":
        return M.hedgerow(p, mats, seed, corner=True, leaves=[(C_LEAF, 5, None), (C_BLOSSOM, 2, M.PINK_BLOSSOM), (C_DARK, 1, None)],
                          flowers=(P_WHITE, P_PINK, P_PINK, P_WHITE), spikes=())
    if pid.startswith("gd-plot") or pid.startswith("gd-crop"):
        return crop_plot(p, mats, seed)
    if pid == "gd-herb-bed":
        return bed(p, mats, seed, herbs=True)
    if pid == "gd-flower-bed":
        return bed(p, mats, seed, herbs=False)
    if pid == "gd-fence-2m":
        return fence(p, mats, seed)
    if pid == "gd-scarecrow":
        return scarecrow(p, mats, seed)
    if pid == "gd-haystack":
        return haystack(p, mats, seed)
    if pid == "gd-well":
        return well(p, mats, seed)
    if pid in ("gd-wall-straight-2m", "gd-wall-corner"):
        return M.dry_wall(p, mats, seed, corner=pid.endswith("corner"), core=CLAY)
    if pid == "gd-wall-broken":
        return broken_wall(p, mats, seed)
    if pid == "gd-terrace-wall-stepped":
        return terrace_wall(p, mats, seed)
    if pid == "gd-clay-bank":
        return clay_bank(p, mats, seed)
    if pid == "gd-lip-terrace":
        return M.lip_piece(p, mats, seed, turf=TURF, cliff=TERRACE, ivy_mat=HEDGE, flowers=(P_WHITE, P_YELLOW, P_WHITE), overhang=0.2)
    if pid == "gd-underside-terrace":
        return underside_terrace(p, mats, seed)
    if pid == "gd-fishpond":
        return fishpond(p, mats, seed)
    if pid == "gd-channel-2m":
        return channel(p, mats, seed)
    if pid == "gd-trickle":
        return M.waterfall(p, mats, seed, fall=FALL, stone_mat=LIME)
    m = Mesh()
    rng = random.Random(seed)
    w, h, d = p["size"]
    if pid == "gd-grass-tuft":
        M.grass_tuft(m, w, h, seed, long=True)
    elif pid == "gd-clover":
        M.clover_patch(p, m, seed, leaf=CLOVER, bloom=P_WHITE)
    elif pid == "gd-wildflower-clump":
        M.flower_clump(p, m, seed, mound=WILD, heads=(P_WHITE, P_YELLOW, P_PINK, P_WHITE), spikes=SPIKE_V)
    else:
        raise ValueError(f"no builder for {pid}")
    return m.object(pid, mats, seed=seed)


def catalogue_category(p):
    pid = p["id"]
    if "wall" in pid or "fence" in pid:
        return "wall"
    if pid.startswith(("gd-plot", "gd-crop", "gd-herb-bed", "gd-flower-bed")):
        return "crop"
    if pid in ("gd-scarecrow", "gd-haystack", "gd-well"):
        return "prop"
    if pid == "gd-clay-bank":
        return "rock"
    return {"tree": "tree", "plant": "bush", "ground": "ground", "rock": "rock", "lip": "lip", "underside": "underside",
            "water": "water"}.get(p["family"], "prop")


M.main(build_piece, "garden", catalogue_category)
