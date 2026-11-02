# Shared nature generators for the biome kits (scripts/kit/nature-<biome>.py), built on kitlib's Mesh (glTF
# coordinates, Y up). Trees with branching trunks and clumped painterly canopies, conifers with drooping tiers,
# faceted and layered rocks, grass and plant clumps, and isle lip and underside pieces.
# Material naming for the demo shader: names containing "Foliage" sway in the wind and render double-sided,
# names containing "Glow" are emissive (see demos/roam/src/world/materials.ts).
import math, random
from mathutils import Vector, noise
from kitlib import tube, hermite


def blob(m, centre, radii, mat, seed=0.0, rough=0.25, rings=6, segs=10, tile=1.5, flat_base=1.0):
    """Noise-displaced ellipsoid with lat-long UVs and pole fans: foliage clumps, bushes, moss cushions, pebbles.
    `flat_base` < 1 squashes the lower half so the shape sits on the ground or on a branch."""
    c = Vector(centre)
    rx, ry, rz = radii
    off = Vector((seed, seed * 0.37, seed * 0.71))
    ur = max(1, round(2 * math.pi * max(rx, rz) / tile))
    vr = max(1, round(math.pi * ry / tile))

    def point(phi, th):
        d = Vector((math.cos(phi) * math.cos(th), math.sin(phi), math.cos(phi) * math.sin(th)))
        k = 1 + rough * noise.noise(d * 1.7 + off)
        y = d.y * ry * k * (flat_base if d.y < 0 else 1)
        return c + Vector((d.x * rx * k, y, d.z * rz * k))

    rows = []
    for i in range(1, rings):
        phi = -math.pi / 2 + math.pi * i / rings
        rows.append([(m.vert(point(phi, 2 * math.pi * j / segs)), (j / segs * ur, i / rings * vr)) for j in range(segs + 1)])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(segs):
            m.face((r0[j][0], r0[j + 1][0], r1[j + 1][0], r1[j][0]), (r0[j][1], r0[j + 1][1], r1[j + 1][1], r1[j][1]), mat)
    bottom = m.vert(point(-math.pi / 2, 0))
    top = m.vert(point(math.pi / 2, 0))
    for j in range(segs):
        a, b = rows[0][j], rows[0][j + 1]
        m.face((bottom, b[0], a[0]), ((a[1][0], 0), b[1], a[1]), mat)
        a, b = rows[-1][j], rows[-1][j + 1]
        m.face((a[0], b[0], top), (a[1], b[1], (a[1][0], vr)), mat)


def broadleaf(m, height, trunk_r, bark, leaf, seed=0, canopy=(0.75, 0.45), branches=5, clumps=9, lean=(0.0, 0.0),
              crown_y=0.62, flare=True, clump_mats=None):
    """Broadleaf tree: flared, curving trunk; primary branches reaching into the crown; a crown of overlapping
    clumps (a dome of `canopy` = (width, height) as fractions of tree height). `clump_mats` may mix leaf colours."""
    rng = random.Random(seed)
    H = height
    cw, ch = canopy[0] * H, canopy[1] * H
    top = Vector((lean[0] * H, H * crown_y, lean[1] * H))
    trunk = hermite((0, -0.3, 0), (0, H * 0.5, 0), top, Vector((lean[0], 1, lean[1])).normalized() * H * 0.4, 10)
    tube(m, trunk, [trunk_r * (1.35 - 0.75 * i / 10) for i in range(11)], bark, 10, twist=0.8, rough=0.18, seed=seed, caps=(False, True))
    if flare:
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), 0, math.sin(a)))
            tube(m, hermite(Vector((0, trunk_r * 1.6, 0)) + d * trunk_r * 0.4, d + Vector((0, -1.2, 0)), d * trunk_r * 3.2 + Vector((0, -0.2, 0)), d, 6),
                 [trunk_r * (0.5 - 0.06 * i) for i in range(7)], bark, 6, rough=0.2, seed=seed + k)
    centre = top + Vector((0, ch * 0.35, 0))
    ends = []
    for k in range(branches):
        a = 2 * math.pi * k / branches + rng.uniform(-0.4, 0.4)
        out = Vector((math.cos(a), 0, math.sin(a)))
        start = trunk[rng.randint(6, 9)]
        end = centre + out * cw * rng.uniform(0.3, 0.42) + Vector((0, rng.uniform(-0.15, 0.25) * ch, 0))
        tube(m, hermite(start, out * H * 0.15 + Vector((0, H * 0.12, 0)), end, (end - start).normalized() * H * 0.1, 8),
             [trunk_r * (0.55 - 0.045 * i) for i in range(9)], bark, 7, rough=0.15, seed=seed + 10 + k)
        ends.append(end)
    mats = clump_mats or [leaf]
    for i, e in enumerate(ends):
        s = cw * rng.uniform(0.2, 0.27)
        blob(m, e, (s, s * 0.72, s), mats[i % len(mats)], seed=seed + 20 + i, rough=0.3, flat_base=0.55)
    for i in range(clumps):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, 0.35) * cw
        y = rng.uniform(0.1, 0.55) * ch
        p = centre + Vector((math.cos(a) * r, y, math.sin(a) * r))
        s = cw * rng.uniform(0.18, 0.26) * (1.1 - y / ch * 0.5)
        blob(m, p, (s, s * 0.75, s), mats[(i + 1) % len(mats)], seed=seed + 40 + i, rough=0.3, flat_base=0.6)


def conifer(m, height, trunk_r, bark, needle, seed=0, tiers=6, spread=0.32, bend=(0.0, 0.0), droop=0.35):
    """Conifer: straight or wind-bent trunk with stacked drooping needle tiers that shrink towards the top.
    `bend` leans the upper trunk (x, z as fractions of height) for wind-blown crag pines."""
    rng = random.Random(seed)
    H = height
    tip = Vector((bend[0] * H, H, bend[1] * H))
    trunk = hermite((0, -0.3, 0), (0, H * 0.6, 0), tip, Vector((bend[0] * 2, 1, bend[1] * 2)).normalized() * H * 0.5, 12)
    tube(m, trunk, [trunk_r * (1.2 - 1.05 * i / 12) for i in range(13)], bark, 8, twist=0.6, rough=0.15, seed=seed)
    for k in range(tiers):
        t = 0.22 + 0.72 * k / tiers
        idx = min(12, int(t * 12))
        c = trunk[idx]
        R = H * spread * (1 - 0.8 * k / tiers) * rng.uniform(0.9, 1.1)
        h = H * 0.2 * (1 - 0.4 * k / tiers)
        segs = 12
        rim, under = [], []
        apex = m.vert(c + Vector((0, h, 0)))
        for j in range(segs):
            a = 2 * math.pi * j / segs + k * 0.4
            r = R * (1 + 0.22 * noise.noise(Vector((math.cos(a) * 2, k, math.sin(a) * 2 + seed))))
            d = Vector((math.cos(a), 0, math.sin(a)))
            rim.append(m.vert(c + d * r + Vector((0, -h * droop, 0))))
            under.append(m.vert(c + d * r * 0.55 + Vector((0, h * 0.05, 0))))
        for j in range(segs):
            j1 = (j + 1) % segs
            u0, u1 = j / segs * 3, (j + 1) / segs * 3
            m.face((rim[j], rim[j1], apex), ((u0, 0), (u1, 0), ((u0 + u1) / 2, 1)), needle)
            m.face((rim[j1], rim[j], under[j], under[j1]), ((u1, 0), (u0, 0), (u0, 0.4), (u1, 0.4)), needle)


def rock(m, size, mat, seed=0, rough=0.35, rings=5, segs=8, sink=0.15):
    """Chunky faceted boulder: a coarse noise-displaced ellipsoid (build the object with smooth=False for facets)."""
    w, h, d = size
    blob(m, (0, h * 0.5 - sink, 0), (w / 2, h / 2 + sink / 2, d / 2), mat, seed=seed, rough=rough, rings=rings, segs=segs, tile=2.0, flat_base=0.7)


def slabs(m, size, mat, seed=0, layers=4, tilt=0.18):
    """Layered slate or ledge rock: stacked, offset, tilted slabs with chunky edges."""
    rng = random.Random(seed)
    w, h, d = size
    y = -0.1
    for i in range(layers):
        lh = h / layers * rng.uniform(0.8, 1.2)
        s = 1 - 0.18 * i
        ox, oz = rng.uniform(-0.12, 0.12) * w, rng.uniform(-0.12, 0.12) * d
        blob(m, (ox, y + lh / 2, oz), (w / 2 * s, lh / 2, d / 2 * s), mat, seed=seed + i, rough=0.18, rings=3, segs=7, tile=2.0, flat_base=1.0)
        y += lh * (1 - tilt)


def blades(m, centre, radius, height, mat, seed=0, count=14, width=0.06, lean=0.5, tip_mat=None):
    """Grass or reed clump: tapered, curving blades fanning out from a centre (each blade is a thin double-sided strip)."""
    rng = random.Random(seed)
    c = Vector(centre)
    for k in range(count):
        a = rng.uniform(0, 2 * math.pi)
        base = c + Vector((math.cos(a), 0, math.sin(a))) * rng.uniform(0, radius * 0.4)
        out = Vector((math.cos(a), 0, math.sin(a)))
        hh = height * rng.uniform(0.6, 1.1)
        tipp = base + out * radius * rng.uniform(0.5, 1.0) * lean + Vector((0, hh, 0))
        pts = hermite(base, Vector((0, hh, 0)), tipp, out * hh * lean + Vector((0, hh * 0.3, 0)), 4)
        side = Vector((-math.sin(a), 0, math.cos(a)))
        prev = None
        for i, p in enumerate(pts):
            wv = width * (1 - i / len(pts))
            pair = (m.vert(p - side * wv), m.vert(p + side * wv))
            if prev:
                v = i / (len(pts) - 1)
                mm = tip_mat if (tip_mat is not None and i == len(pts) - 1) else mat
                m.face((prev[0], prev[1], pair[1], pair[0]), ((0, v - 0.25), (1, v - 0.25), (1, v), (0, v)), mm)
            prev = pair


def lip(m, width, depth, height, top, cliff, seed=0, overhang=0.5):
    """Isle edge segment along X (0..width centred on the pivot): a grassy top at y = height whose outer edge (+Z)
    bulges and overhangs, then a rough cliff face dropping to y = 0. The top meets the isle ground at the back (-Z)."""
    segs, drops = 16, 5
    rows = []
    for i in range(drops + 1):
        t = i / drops
        row = []
        for j in range(segs + 1):
            x = -width / 2 + width * j / segs
            n = noise.noise(Vector((x * 0.6, t * 3, seed)))
            z = depth / 2 + overhang * (1 - t) ** 0.5 + n * 0.45 - t * overhang * 0.8
            y = height * (1 - t) + n * 0.25 * t
            row.append(m.vert((x, y, z)))
        rows.append(row)
    for i in range(drops):
        for j in range(segs):
            m.face((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]), None, cliff, 2.0)
    back = [m.vert((-width / 2 + width * j / segs, height, -depth / 2)) for j in range(segs + 1)]
    for j in range(segs):
        m.face((back[j], rows[0][j], rows[0][j + 1], back[j + 1]), None, top, 2.0)


def underside(m, top_w, height, mat, seed=0, top_d=None, tiers=6, segs=14, lumps=0.3):
    """Isle underside taper: rock that narrows from an irregular top outline at y = height to a point at y = 0,
    in rough strata. Pair with tube() roots or drips from the caller."""
    top_d = top_d or top_w
    rings = []
    for i in range(tiers + 1):
        t = i / tiers  # 0 at the top
        y = height * (1 - t)
        shrink = (1 - t) ** 0.6 if i < tiers else 0
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            n = 1 + lumps * noise.noise(Vector((math.cos(a) * 1.5, t * 4, math.sin(a) * 1.5 + seed)))
            ring.append(m.vert((math.cos(a) * top_w / 2 * shrink * n + (0.4 * t * math.sin(seed)),
                                y, math.sin(a) * top_d / 2 * shrink * n)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(segs):
            j1 = (j + 1) % segs
            m.face((r0[j], r0[j1], r1[j1], r1[j]), None, mat, 2.0)
    m.face(rings[0][::-1], None, mat, 2.0)


# ---------- alpha-cutout cards (materials named "*Card*", sprites in art/textures/foliage/, 2×2 atlases) ----------

def _quadrant(rng, atlas=2, pick=None):
    q = pick if pick is not None else rng.randrange(atlas * atlas)
    qx, qy = q % atlas, q // atlas
    return qx / atlas, qy / atlas, 1 / atlas


def _card(m, centre, right, up, w, h, mat, uv0, normal=None):
    c = Vector(centre)
    corners = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
    u, v, s = uv0
    uvs = [(u, v), (u + s, v), (u + s, v + s), (u, v + s)]
    if normal is not None and right.cross(up).dot(Vector(normal)) < 0:
        corners, uvs = corners[::-1], uvs[::-1]  # wind the card so its front faces along its normal hint
    verts = [m.vert(p) for p in corners]
    m.keep.add(m.face(verts, uvs, mat))
    if normal is not None:
        for vv in verts:
            m.normals[vv] = normal
    return verts


def card_crown(m, lobes, mat, seed=0, density=14.0, size=(0.9, 1.4), crown_centre=None, up_bias=0.35, atlas=2):
    """Leafy crown from alpha-cutout cards: each lobe is (centre, (rx, ry, rz)); cards scatter mostly near each lobe's
    surface, face outwards with random roll, and carry normals pointing away from `crown_centre` so the whole crown
    shades as one soft mass with ragged painted edges. `density` is cards per square metre of lobe surface / 10."""
    rng = random.Random(seed)
    cc = Vector(crown_centre) if crown_centre is not None else sum((Vector(c) for c, _ in lobes), Vector()) / len(lobes)
    span = max(max(r) for _, r in lobes)
    for c, (rx, ry, rz) in lobes:
        c = Vector(c)
        area = 4 * math.pi * (rx * ry + rx * rz + ry * rz) / 3  # close to an ellipsoid's surface area
        n_cards = max(6, int(area * density / 10))
        for _ in range(n_cards):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1) * 0.8 + 0.15, rng.gauss(0, 1))).normalized()
            depth = rng.uniform(0.55, 1.0) ** 0.5
            p = c + Vector((d.x * rx, d.y * ry, d.z * rz)) * depth
            out = (p - cc)
            out = (out / span + Vector((0, up_bias, 0))).normalized() if out.length > 1e-4 else Vector((0, 1, 0))
            face = (d * 0.6 + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.2, 0.4), rng.uniform(-0.4, 0.4)))).normalized()
            right = face.cross(Vector((0, 1, 0)))
            right = right.normalized() if right.length > 1e-3 else Vector((1, 0, 0))
            up = right.cross(face).normalized()
            roll = rng.uniform(-0.6, 0.6)
            right, up = right * math.cos(roll) + up * math.sin(roll), up * math.cos(roll) - right * math.sin(roll)
            s = rng.uniform(*size)
            _card(m, p, right, up, s, s, mat, _quadrant(rng, atlas), normal=out)


def card_tuft(m, base, height, width, mat, seed=0, planes=3, pick=None, lean=0.0, atlas=2, normal_up=0.7):
    """Grass, fern, reed or flower tuft: `planes` crossed vertical cards sharing one sprite quadrant (roots at the
    bottom edge of the sprite), with normals tilted up so tufts light like the ground they stand on."""
    rng = random.Random(seed)
    b = Vector(base)
    uv0 = _quadrant(rng, atlas, pick)
    for k in range(planes):
        a = math.pi * k / planes + rng.uniform(-0.2, 0.2)
        right = Vector((math.cos(a), 0, math.sin(a)))
        face = Vector((-math.sin(a), 0, math.cos(a)))
        up = (Vector((0, 1, 0)) + face * lean).normalized()
        n = (face * (1 - normal_up) + Vector((0, 1, 0)) * normal_up).normalized()
        _card(m, b + up * height / 2, right, up, width, height, mat, uv0, normal=n)


def card_drape(m, top, length, width, mat, seed=0, count=3, spread=0.6, pick=None, atlas=2, facing=None):
    """Hanging ivy, moss or weed: cards hanging down from `top` (sprite drawn hanging from its top edge)."""
    rng = random.Random(seed)
    t = Vector(top)
    for k in range(count):
        a = rng.uniform(0, math.pi) if facing is None else facing + rng.uniform(-0.4, 0.4)
        right = Vector((math.cos(a), 0, math.sin(a)))
        face = Vector((-math.sin(a), 0, math.cos(a)))
        L = length * rng.uniform(0.7, 1.1)
        c = t + right * rng.uniform(-spread, spread) * width - Vector((0, L / 2, 0))
        _card(m, c, right, Vector((0, 1, 0)), width, L, mat, _quadrant(rng, atlas, pick), normal=(face + Vector((0, 0.4, 0))).normalized())
