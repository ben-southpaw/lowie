import sys; sys.path.insert(0, '.'); import tat, math, random
import numpy as np
from scipy.ndimage import gaussian_filter
p = tat.load('pearl.jpg')
# "sorry" under her right eye, parallel to the eye line, turning away with the cheek
pts = [(1590, 1915), (1730, 1940), (1870, 1965)]
a = tat.coverage(p.shape, pts, [90]*3, "sorry", height=105, along=0.47, across=0, k=0.3, soft=2.2,
                 wrap=(0, 520), edge=0.99)

# teardrop under the outer corner of the eye: a hand-poked dotted outline
def teardrop(top, H, W, tilt, step=5.2, seed=7):
    rnd = random.Random(seed)
    yy, xx = np.mgrid[0:p.shape[0], 0:p.shape[1]]
    m = np.zeros(p.shape[:2], np.float32)
    pts_o = []
    for t in np.linspace(0, 2 * math.pi, 2000):
        pts_o.append((W / 2 * math.sin(t) * math.sin(t / 2) ** 1.3, (1 - math.cos(t)) / 2 * H))
    # walk the outline, dropping a dot every `step` px
    acc, last = 0, pts_o[0]; dots = [last]
    for q in pts_o[1:]:
        acc += math.dist(q, last); last = q
        if acc >= step * rnd.uniform(0.85, 1.15):
            dots.append(q); acc = 0
    ca, sa = math.cos(tilt), math.sin(tilt)
    x0, y0 = top
    box = (slice(int(y0 - 10), int(y0 + H + 10)), slice(int(x0 - W), int(x0 + W)))
    sy, sx = yy[box].astype(np.float32), xx[box].astype(np.float32)
    sub = np.zeros(sy.shape, np.float32)
    for dx, dy in dots:
        cx = x0 + dx * ca - dy * sa + rnd.gauss(0, 0.6)
        cy = y0 + dx * sa + dy * ca + rnd.gauss(0, 0.6)
        r = rnd.uniform(1.6, 2.5)
        sub = np.maximum(sub, np.clip(r + 0.5 - np.hypot(sx - cx, sy - cy), 0, 1))
    m[box] = gaussian_filter(sub, 1.6)
    return m

tear = teardrop(top=(1856, 1868), H=58, W=32, tilt=math.radians(-6), step=5.6)
tear2 = teardrop(top=(1866, 1942), H=56, W=31, tilt=math.radians(-6), step=5.6, seed=11)
a = np.maximum(a, np.maximum(tear, tear2) * 1.4)
out = tat.ink(p, np.clip(a, 0, 1), strength=0.7, colour=(0.24, 0.26, 0.30), detail_sigma=2.5)
tat.save(out, 'r-pearl-face.png', crop=(1500, 1700, 2050, 2050), size=(1100, 700))
tat.save(out, 'pearl-face-tat.jpg')
