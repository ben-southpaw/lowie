import json, sys
from fontTools.ttLib import TTFont
p=sys.argv[1]; out=sys.argv[2]
f=TTFont(p); glyf=f['glyf']; hmtx=f['hmtx']
cmap={chr(k):v for k,v in f.getBestCmap().items()}
glyphs={}
total=0
for name in f.getGlyphOrder():
    g=glyf[name]; adv=hmtx[name][0]
    dots=[]
    if g.numberOfContours>0:
        coords,ends,flags=g.getCoordinates(glyf)
        s=0
        for e in ends:
            pts=coords[s:e+1]; fl=flags[s:e+1]; s=e+1
            # flat list: x,y,on per point
            dots.append([v for (x,y) in pts for v in (int(x),int(y))] if not any(o&1 for o in fl) else [-1]+[v for (x,y),o in zip(pts,fl) for v in (int(x),int(y),int(o&1))])
    total+=len(dots)
    glyphs[name]={'a':adv,'d':dots}
data={'upm':f['head'].unitsPerEm,'asc':f['hhea'].ascent,'desc':f['hhea'].descent,'cmap':cmap,'glyphs':glyphs}
json.dump(data,open(out,'w'),separators=(',',':'))
print('glyphs',len(glyphs),'contours',total)
