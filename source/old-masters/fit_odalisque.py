import sys; sys.path.insert(0, '.'); import tat
# odalisque.jpg = the Commons "avec cadre" photo cropped to (1296, 1376, 9840, 6160), frame removed
import numpy as np
p = tat.load('odalisque.jpg')
# "Lowie" as a real tramp stamp. Her lower spine runs down and to the right towards the cleft (about 45 deg here),
# and her waist line rises to the right at about 28 deg. The word sits on the sacrum, centred on the spine,
# runs along the waist line and sweeps up at both ends. She is twisted, so the torso's axis is right of the spine:
# the left half of the word turns away towards her left flank and foreshortens.
import math
C = np.array([1940.0, 3270.0])                            # spine at the sacrum
ang = math.radians(-62)
u = np.array([math.cos(ang), math.sin(ang)])              # along the waist, left to right
v = np.array([-0.707, -0.707])                            # body 'up', along the spine towards the head
ts = np.arange(-700, 1001, 100)
pts = [tuple(C + u * t + v * 70 * min((t / 500) ** 2, 1.6)) for t in ts]
seg = np.r_[0, np.cumsum(np.hypot(*np.diff(np.asarray(pts), axis=0).T))]
s_spine = float(np.interp(0, ts, seg)); L = seg[-1]
s_axis = float(np.interp(80, ts, seg))                    # torso axis, a little right of the spine (she is twisted)
a = tat.coverage(p.shape, pts, [360] * len(pts), "Lowie", height=300, along=s_spine / L, across=0, k=0.3, soft=2.2,
                 wrap=(s_axis, 900), edge=0.99)
out = tat.ink(p, a, strength=0.72, colour=(0.22, 0.25, 0.30), detail_sigma=2.5)
tat.save(out, 'r-odal.png', crop=(1300, 2700, 3300, 3700), size=(1400, 700))
tat.save(out, 'odalisque-tat.jpg')
tat.save(out, 'open-odal.jpg', crop=(250, 1180, 4122, 3600), size=(2400, 1500))
