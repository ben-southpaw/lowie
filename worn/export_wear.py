"""Export a Lowie TTF's glyph contours to lowie-poke.json for the Lowie Worn demo.

Usage: python export_wear.py <font.ttf> <out.json>

Each contour is one flat list: x0, y0, on0, then per point (dx * 2 + on), dy.
Deltas keep the numbers short; `on` is 1 for an on-curve point, 0 for off-curve.
"""
import json
import sys

from fontTools.ttLib import TTFont

p, out = sys.argv[1], sys.argv[2]
f = TTFont(p)
glyf, hmtx = f["glyf"], f["hmtx"]
cmap = {chr(k): v for k, v in f.getBestCmap().items()}
glyphs, total = {}, 0
for name in f.getGlyphOrder():
    g = glyf[name]
    contours = []
    if g.numberOfContours > 0:
        coords, ends, flags = g.getCoordinates(glyf)
        s = 0
        for e in ends:
            pts = [(int(x), int(y), int(fl & 1)) for (x, y), fl in zip(coords[s:e + 1], flags[s:e + 1])]
            s = e + 1
            x0, y0, on0 = pts[0]
            enc = [x0, y0, on0]
            px, py = x0, y0
            for x, y, on in pts[1:]:
                enc += [(x - px) * 2 + on, y - py]
                px, py = x, y
            contours.append(enc)
    total += len(contours)
    glyphs[name] = {"a": hmtx[name][0], "d": contours}
data = {"upm": f["head"].unitsPerEm, "cmap": cmap, "glyphs": glyphs,
        "version": f["name"].getDebugName(5)}
json.dump(data, open(out, "w"), separators=(",", ":"))
print("glyphs", len(glyphs), "contours", total)
