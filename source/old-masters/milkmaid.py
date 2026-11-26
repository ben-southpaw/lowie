"""Prototype: a Lowie tattoo painted onto Vermeer's Milkmaid forearm."""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import map_coordinates, gaussian_filter

FONTS = "/Users/benjamindryden/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ben/lowie-font/fonts/"
WORD = sys.argv[1] if len(sys.argv) > 1 else "melk"
STYLE = sys.argv[2] if len(sys.argv) > 2 else "Poke"

src = Image.open("milkmaid.jpg").convert("RGB")
paint = np.asarray(src).astype(np.float32) / 255

# arm cylinder, measured by eye on the full-res image: x -> (centre y, half width)
AX = np.array([1600, 1680, 1840, 2000, 2120, 2240])
CY = np.array([2432, 2428, 2418, 2405, 2390, 2368])
HW = np.array([58, 62, 74, 85, 92, 100])
XC, MAXW = 1985, 660          # word centre along the arm, longest it may run
TH0, SPAN_MAX = -0.12, 1.95    # centre angle and largest angular height (radians round the arm)

# render the word flat, generous padding
f = ImageFont.truetype(FONTS + f"Lowie-Proto-{STYLE}.ttf", 400, layout_engine=ImageFont.Layout.RAQM)
tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
l, t, r, b = tmp.textbbox((0, 0), WORD, font=f)
tex = Image.new("L", (r - l + 40, b - t + 40), 0)
ImageDraw.Draw(tex).text((20 - l, 20 - t), WORD, font=f, fill=255)
tex = np.asarray(tex).astype(np.float32) / 255
TH, TW = tex.shape

# fit width: word spans X0..X1, height from SPAN; keep aspect by trimming X1
aspect = TW / TH

bx0, bx1, by0, by1 = XC - MAXW // 2 - 30, XC + MAXW // 2 + 30, 2220, 2540
ys, xs = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
cy = np.interp(xs, AX, CY)
hw = np.interp(xs, AX, HW)
vraw = (ys - cy) / hw
v = np.clip(vraw, -0.999, 0.999)
theta = np.arcsin(v)
# horizontal: arc height at mid arm sets the scale so letters keep their shape
hw_mid = np.interp(XC, AX, HW)
mid_h = min(hw_mid * SPAN_MAX, MAXW / aspect)        # as big as the arm allows
word_w = mid_h * aspect
cx0 = XC - word_w / 2
col = (xs - cx0) / word_w
SPAN = mid_h / hw_mid
row = (theta - (TH0 - SPAN / 2)) / SPAN
a = map_coordinates(tex, [row * TH, col * TW], order=1, mode="constant", cval=0)
a[(row < 0) | (row > 1) | (col < 0) | (col > 1) | (np.abs(vraw) > 0.96)] = 0
# foreshortened near the silhouette: thin out, and ink sits slightly lighter
a *= np.clip(np.cos(theta) * 1.3, 0, 1)
a = gaussian_filter(a, 1.4)                         # match the softness of the paint here

alpha = np.zeros(paint.shape[:2], np.float32)
alpha[by0:by1, bx0:bx1] = a * 0.8                  # healed, not fresh

INK = np.array([0.20, 0.25, 0.30])                  # faded blue-black
under = paint
blur = gaussian_filter(paint, (2.0, 2.0, 0))
detail = paint - blur                               # craquelure, brush texture
inked = under * INK / 0.55                          # multiply: takes the painting's light
inked = np.clip(inked, 0, 1)
out = under * (1 - alpha[..., None]) + inked * alpha[..., None]
out += detail * alpha[..., None] * 0.9              # cracks run through the ink
out = np.clip(out, 0, 1)

img = Image.fromarray((out * 255).astype(np.uint8))
img.save(f"milkmaid-{WORD}-{STYLE}.jpg", quality=92)
img.crop((1500, 2150, 2600, 2650)).save(f"crop-{WORD}-{STYLE}.png")
src.crop((1500, 2150, 2600, 2650)).save("crop-orig.png")
print("word px", round(word_w), "x", round(mid_h))
