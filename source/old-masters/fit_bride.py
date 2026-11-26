import sys; sys.path.insert(0, '.'); import tat
p = tat.load('bride.jpg')
pts = [(1860, 1512), (1950, 1500), (2050, 1486)]
a = tat.coverage(p.shape, pts, [80]*3, "LOVE", height=96, along=0.42, across=0, k=0.4, soft=1.8,
                 wrap=(110, 420))
out = tat.ink(p, a, strength=0.75, detail_sigma=2.5)
tat.save(out, 'r-bride.png', crop=(1750, 1250, 2450, 1700), size=(1050, 675))
tat.save(out, 'bride-tat.jpg')
