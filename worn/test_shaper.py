import json, subprocess, random, uharfbuzz as hb, sys
fontp=sys.argv[1]
blob=hb.Blob.from_file_path(fontp); face=hb.Face(blob); font=hb.Font(face)
data=json.load(open('lowie-poke.json'))
order=list(data['glyphs'].keys())
from fontTools.ttLib import TTFont
go=TTFont(fontp).getGlyphOrder()
random.seed(4)
alpha="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZéèëöüçñ .,!?-'0123"
tests=["minimum","Hello world","borvw brown vow","The quick brown fox jumps over the lazy dog","Amsterdam wordt oud","HHH hHo"]+["".join(random.choice(alpha) for _ in range(random.randint(3,30))) for _ in range(400)]
json.dump(tests,open('tests.json','w'))
hbres=[]
for t in tests:
  buf=hb.Buffer(); buf.add_str(t); buf.guess_segment_properties(); hb.shape(font,buf,{})
  hbres.append([go[i.codepoint] for i in buf.glyph_infos])
js=json.loads(subprocess.check_output(['node','-e',"""
const {makeShaper}=require('./shaper.js');const d=require('./lowie-poke.json');const s=makeShaper(d);
const t=require('./tests.json');console.log(JSON.stringify(t.map(x=>s(x).map(o=>o.glyph||'.notdef'))))"""]))
bad=0
for t,a,b in zip(tests,hbres,js):
  if a!=b:
    bad+=1
    if bad<6: print(repr(t)); print(' hb',a); print(' js',b)
print('mismatches',bad,'of',len(tests))
