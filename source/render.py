"""Render a PNG proof. Usage: render.py OUT.png STYLE[,STYLE] "line" ["line" ...]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
args = sys.argv[1:]
feats = []
if args[0].startswith("--features="):        # e.g. --features=ss01
    feats = args.pop(0).split("=", 1)[1].split(",")
out, styles, lines = args[0], args[1].split(","), args[2:]
W, rowh = 1700, 230
img = Image.new("RGB", (W, rowh * len(lines) * len(styles) + 40), "#f6f3ee")
d = ImageDraw.Draw(img)
lab = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
y = 20
for s in styles:
    f = ImageFont.truetype(str(ROOT / "fonts" / f"Lowie-Proto-{s}.ttf"), 150,
                           layout_engine=ImageFont.Layout.RAQM)
    for ln in lines:
        d.text((20, y), s + (" + " + ",".join(feats) if feats else ""), font=lab, fill="#d0216f")
        d.text((40, y + 10), ln, font=f, fill="#1b1a18", features=feats or None)
        y += rowh
img.save(ROOT / "proofs" / out)
