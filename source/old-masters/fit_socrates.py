import sys; sys.path.insert(0, '.'); import tat
p = tat.load('socrates.jpg')
a = tat.coverage(p.shape, [(2380, 1172), (2440, 1150), (2500, 1142), (2560, 1148), (2618, 1166)], [70]*5, "no regrets",
                 height=56, along=0.50, across=0, k=0.3, soft=0.9, wrap=(122, 140))
out = tat.ink(p, a, strength=0.8, detail_sigma=1.5)
tat.save(out, 'r-socrates.png', crop=(2300, 1040, 2700, 1340), size=(960, 720))
tat.save(out, 'socrates-tat.jpg')
