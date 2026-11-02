# Prepare alpha sprites for cutout rendering: grow each opaque pixel's colour outward into the transparent area
# (so mipmaps and filtering at cut edges blend towards the leaf colour, not black) and resize to a web-friendly size.
# Usage: Blender --background --python scripts/kit/bleed.py -- <size> <sprite.png ...>
import bpy, sys
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
size, files = int(args[0]), args[1:]
for path in files:
    img = bpy.data.images.load(path)
    if img.size[0] != size:
        img.scale(size, size)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb, a = px[..., :3].copy(), px[..., 3]
    known = a > 0.5
    rgb[~known] = 0
    for _ in range(48):  # each pass grows the coloured region by one pixel
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(known.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            k = np.roll(np.roll(known, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * k[..., None]
            cnt += k
        grow = (~known) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][..., None]
        known = known | grow
    px[..., :3] = rgb
    img.pixels[:] = px.ravel()
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    print("bled", path, w)
