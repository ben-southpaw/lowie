import base64
from pathlib import Path

ROOT = Path(__file__).parent.parent
LABELS = {"PokeLow": "Poke Low", "WedgeHeavyLow": "Wedge Heavy Low", "PokeShaded": "Poke Shaded", "PokeLine": "Poke Line", "DotSlab": "Dot Slab", "DotFine": "Dot Fine", "DotOutline": "Dot Outline", "WedgeHeavy": "Wedge Heavy", "PowderFine": "Powder Fine", "PowderRail": "Powder Rail"}
STYLES = [("Poke", "Hand-poke packing. b, o, r, v, w join from the top, the rest from the bottom."),
          ("PokeLow", "Poke with every join from the bottom."),
          ("PokeShaded", "Dense edge, dots thin out towards the middle, like dotwork shading."),
          ("PokeLine", "Two rows of dots on the edges only: line work."),
          ("DotSlab", "Whole letters in hand-poke dots, on the sturdy Slab shapes."),
          ("Dot", "Whole letters in dots, high-contrast shapes."),
          ("DotFine", "Smaller, tighter dots."),
          ("DotOutline", "Dots trace the edges only. Hollow letters."),
          ("WedgeHeavy", "Solid reference. Mixed high and low joins."),
          ("WedgeHeavyLow", "Solid reference. Every join from the bottom."),
          ("Rail", "Foot serifs run on into one baseline stroke."),
          ("Headline", "Head serifs run on into one stroke along the x-height."),
          ("Slab", "Low contrast: thicker hairlines and serifs, heavier wedges."),
          ("Italic", "Wedge Heavy slanted 12 degrees."),
          ("Condensed", "Narrow counters, tighter joins."),
          ("Powder", "Joins made of loose grains, like a line of snow or flour."),
          ("PowderFine", "Finer grains, tighter line."),
          ("PowderRail", "A straight line of grains along the baseline."),
          ("Wedge", "Earlier: lighter wedges."),
          ("Hairline", "Earlier: thin continuous joins."),
          ("Broken", "Earlier: joins fade before the next letter."),
]

faces, rows = [], []
for name, note in STYLES:
    data = base64.b64encode((ROOT / "fonts" / f"Lowie-Proto-{name}.ttf").read_bytes()).decode()
    faces.append(f"@font-face{{font-family:'M{name}';src:url(data:font/ttf;base64,{data}) format('truetype');}}")
    rows.append(f"""
<section>
  <h2>{LABELS.get(name, name)}</h2><p class="note">{note}</p>
  <div class="big" style="font-family:'M{name}'">minimum</div>
  <div class="mid live" style="font-family:'M{name}'">Quiet zebras jump over brown woven rovers</div>
  <div class="small" style="font-family:'M{name}'">i n m u o h · H O</div>
</section>""")

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lowie Prototype</title>
<style>
{''.join(faces)}
:root{{--bg:#f6f3ee;--ink:#1b1a18;--muted:#77716a;--line:#ddd6cc;--accent:#d0216f}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#151413;--ink:#f1ece4;--muted:#9a938a;--line:#2e2b28}}}}
:root[data-theme="dark"]{{--bg:#151413;--ink:#f1ece4;--muted:#9a938a;--line:#2e2b28}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:32px 16px 64px}}
h1{{font-size:14px;letter-spacing:.12em;text-transform:uppercase;margin:0 0 4px}}
.lede{{color:var(--muted);margin:0 0 20px}}
input{{width:100%;box-sizing:border-box;font:inherit;font-size:18px;padding:10px 12px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--ink)}}
.sw{{display:flex;gap:8px;align-items:center;margin:10px 0 0;font-size:15px}}.sw input{{width:auto}}
body.lo .live,body.lo .big,body.lo .small{{font-feature-settings:"ss01" 1}}
input:focus{{outline:2px solid var(--accent);border-color:transparent}}
section{{border-top:1px solid var(--line);padding:24px 0 8px}}
h2{{font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin:0;color:var(--accent)}}
.note{{color:var(--muted);margin:2px 0 8px}}
.big{{font-size:clamp(72px,16vw,180px);line-height:1.15;overflow-wrap:anywhere}}
.mid{{font-size:clamp(36px,7vw,72px);line-height:1.3;overflow-wrap:anywhere}}
.small{{font-size:36px;color:var(--muted)}}
</style></head><body><main>
<h1>Lowie · prototype 12</h1>
<p class="lede">Sixteen directions to compare, then three earlier styles. Letters a to z and A to Z, figures 0 to 9, punctuation, symbols (@ # % £ $ & € and more) and accents (à á â ä ã å ç é è ê ë ï ñ ö ü and more). Capitals join into lowercase, never to each other. Type to test.</p>
<input id="t" value="Quiet zebras jump over brown woven rovers" aria-label="Test text">
<label class="sw"><input type="checkbox" id="lo"> All low joins (stylistic set 1, ss01)</label>
{''.join(rows)}
</main>
<script>
const t=document.getElementById('t');
document.getElementById('lo').addEventListener('change',e=>document.body.classList.toggle('lo',e.target.checked));
t.addEventListener('input',()=>document.querySelectorAll('.live').forEach(e=>e.textContent=t.value||' '));
</script></body></html>"""
(ROOT / "proofs" / "lowie-specimen.html").write_text(html)
print("ok")
