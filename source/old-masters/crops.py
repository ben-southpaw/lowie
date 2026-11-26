"""Same-scale crops: height 9x word height, centred on the inked pixels. 4:5 at 960x1200, or wide 3:2 at 1800x1200."""
import sys
import numpy as np
from PIL import Image
def crop(orig, tat, h, out, aspect=0.8):
    a = np.asarray(Image.open(orig).convert("L"), np.int16)
    b = np.asarray(Image.open(tat).convert("L"), np.int16)
    ys, xs = np.nonzero(np.abs(a - b) > 12)
    cx, cy = np.median(xs), np.median(ys)
    H = 9 * h; W = H * aspect
    top = cy - 0.55 * H; left = cx - W / 2
    top = min(max(top, 0), a.shape[0] - H); left = min(max(left, 0), a.shape[1] - W)
    Image.open(tat).convert("RGB").crop((int(left), int(top), int(left + W), int(top + H))) \
        .resize((round(1200 * aspect), 1200), Image.LANCZOS).save(out, quality=92)
if __name__ == "__main__":
    crop(sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 0.8)
