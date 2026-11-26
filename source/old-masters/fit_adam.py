import sys; sys.path.insert(0, '.'); import tat
import numpy as np
p = tat.load('adam.jpg')
word = sys.argv[1]
def axis_s(pts, x):
    pts = np.asarray(pts, float)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    return np.interp(x, pts[:, 0], seg)
if word.lower() == "thug life":     # across the belly, arched, Tupac style
    # lowercase: a shallow arch. Caps copy Tupac's: a rounder arch, set lower on the belly. Same arc length either way.
    R0, Y0 = (1700, 2600) if word.islower() else (950, 2665)
    T = 0.27 * 1700 / R0
    pts = [(1530 + R0 * np.sin(t), Y0 + R0 * (1 - np.cos(t))) for t in np.linspace(-T, T, 11)]
    H = 200 if word.islower() else int(sys.argv[2]) if len(sys.argv) > 2 else 150
else:                       # across the chest, above the nipples
    pts = [(1150, 2250), (1530, 2210), (1910, 2250)]
    H = 175
wc = axis_s(pts, 1530)
a = tat.coverage(p.shape, pts, [200]*len(pts), word, height=H, along=wc / axis_s(pts, pts[-1][0]),
                 across=0, k=0.3, soft=1.8, wrap=(wc, 540))
out = tat.ink(p, a, strength=0.74, detail_sigma=2.0)
tag = word.replace(" ", "")
tat.save(out, f'r-adam-{tag}.png', crop=(1050, 1950, 2050, 2950), size=(900, 900))
tat.save(out, f'adam-tat-{tag}.jpg')
print(word, H)
