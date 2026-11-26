"""Paint a Lowie word onto skin in an old painting.

The body part is modelled as a strip along a centreline (any direction), with a
screen half-width at each point. The strip is a cylinder whose radius is
half-width / k: k=1 a full limb, smaller k a flatter surface such as a chest or back.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates, gaussian_filter
from scipy.spatial import cKDTree

FONTS = "/Users/benjamindryden/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ben/lowie-font/fonts/"


def word_texture(word, style="Poke", features=None):
    f = ImageFont.truetype(FONTS + f"Lowie-Proto-{style}.ttf", 400, layout_engine=ImageFont.Layout.RAQM)
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    l, t, r, b = d.textbbox((0, 0), word, font=f, features=features)
    asc, desc = f.getmetrics()
    # vertical box is the font's ascent+descent, so words of different letters share a baseline
    tex = Image.new("L", (r - l + 40, asc + desc + 40), 0)
    ImageDraw.Draw(tex).text((20 - l, 20), word, font=f, fill=255, features=features)
    return np.asarray(tex).astype(np.float32) / 255


def coverage(shape, pts, hw, word, height, along=0.5, across=0.0, k=1.0, style="Poke",
             soft=1.2, edge=0.96, tex=None, wrap=None):
    """Alpha map (0..1) of the word on the strip.

    pts, hw: centreline points (x, y) and screen half-widths; text reads in point order,
    its top on the left-hand side of the direction of travel (image 'up' for a line running right).
    height: word height in px measured along the surface (ascent+descent box).
    along: word centre as a fraction of the centreline length. across: centre offset in surface px,
    positive = toward the bottom of the letters.
    """
    pts = np.asarray(pts, float); hw = np.asarray(hw, float)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    L = seg[-1]
    s_d = np.linspace(0, L, int(L) + 1)
    cx = np.interp(s_d, seg, pts[:, 0]); cy = np.interp(s_d, seg, pts[:, 1])
    hd = np.interp(s_d, seg, hw)
    tx = np.gradient(cx); ty = np.gradient(cy); n = np.hypot(tx, ty); tx /= n; ty /= n
    if tex is None:
        tex = word_texture(word, style)
    TH, TW = tex.shape
    width = height * TW / TH
    pad = int(hw.max() + 10)
    x0 = max(int(pts[:, 0].min()) - pad, 0); x1 = min(int(pts[:, 0].max()) + pad, shape[1])
    y0 = max(int(pts[:, 1].min()) - pad, 0); y1 = min(int(pts[:, 1].max()) + pad, shape[0])
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    _, idx = cKDTree(np.c_[cx, cy]).query(np.c_[xs.ravel(), ys.ravel()])
    idx = idx.reshape(xs.shape)
    dx = xs - cx[idx]; dy = ys - cy[idx]
    s = s_d[idx] + dx * tx[idx] + dy * ty[idx]          # along, with sub-sample correction
    down = -dx * ty[idx] + dy * tx[idx]                  # across, + toward letter bottoms
    h = hd[idx]
    vraw = down / h
    kv = np.clip(k * vraw, -0.999, 0.999)
    arc = (h / k) * np.arcsin(kv)                       # distance over the surface
    row = (arc - (across - height / 2)) / height
    sc = along * L
    if wrap:                                            # text runs round a body (chest, back)
        wc, wR = wrap                                   # axis position along the line, screen radius
        u = np.clip((s - wc) / wR, -0.999, 0.999)
        s = wc + wR * np.arcsin(u)
        sc = wc + wR * np.arcsin(np.clip((sc - wc) / wR, -0.999, 0.999))
        a_turn = np.sqrt(1 - u ** 2)
    col = (s - (sc - width / 2)) / width
    a = map_coordinates(tex, [row * TH, col * TW], order=1, mode="constant", cval=0)
    a[(row < 0) | (row > 1) | (col < 0) | (col > 1) | (np.abs(vraw) > edge)] = 0
    a *= np.clip(np.sqrt(1 - kv ** 2) * 1.3, 0, 1)       # thins where the surface turns away
    if wrap:
        a *= np.clip(a_turn * 1.3, 0, 1)
    a = gaussian_filter(a, soft)
    out = np.zeros(shape[:2], np.float32)
    out[y0:y1, x0:x1] = a
    return out


def ink(paint, alpha, strength=0.8, colour=(0.20, 0.25, 0.30), detail_sigma=2.0, detail=0.9):
    """Multiply ink into the paint and lay the paint's own cracks back over it."""
    a = (alpha * strength)[..., None]
    blur = gaussian_filter(paint, (detail_sigma, detail_sigma, 0))
    inked = np.clip(paint * np.array(colour) / 0.55, 0, 1)
    out = paint * (1 - a) + inked * a + (paint - blur) * a * detail
    return np.clip(out, 0, 1)


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255


def save(arr, path, crop=None, size=None):
    im = Image.fromarray((arr * 255).astype(np.uint8))
    if crop:
        im = im.crop(crop)
    if size:
        im = im.resize(size, Image.LANCZOS)
    im.save(path, quality=92)
    return im


def grid(path, out, crop, step=50, scale=1.0):
    """Crop with a labelled coordinate grid, for measuring by eye."""
    im = Image.open(path).convert("RGB").crop(crop)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)))
    d = ImageDraw.Draw(im)
    for gx in range(0, crop[2] - crop[0], step):
        X = gx * scale; d.line([X, 0, X, im.height], fill=(255, 0, 0)); d.text((X + 2, 2), str(crop[0] + gx), fill=(255, 0, 0))
    for gy in range(0, crop[3] - crop[1], step):
        Y = gy * scale; d.line([0, Y, im.width, Y], fill=(255, 0, 0)); d.text((2, Y + 2), str(crop[1] + gy), fill=(255, 0, 0))
    im.save(out)
