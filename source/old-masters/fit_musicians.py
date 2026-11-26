import sys; sys.path.insert(0, '.'); import tat
p = tat.load('musicians.jpg')
pts = [(2800, 1300), (3030, 1250), (3260, 1215), (3500, 1195)]
L = sum(((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2) ** .5 for i in range(3))
a = tat.coverage(p.shape, pts, [320]*4, "anarchy", height=230, along=(3200-2800)/L, across=0, k=0.35, soft=1.8,
                 wrap=(3240-2800, 560))
out = tat.ink(p, a, strength=0.72, detail_sigma=2.0)
tat.save(out, 'r-musicians.png', crop=(2500, 800, 3800, 1900), size=(1040, 880))
tat.save(out, 'musicians-tat.jpg')
