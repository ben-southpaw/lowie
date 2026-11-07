"""Mock-ups of Lowie in use: black ink on light paper. Writes PNGs to ../proofs/demos/.

All names, places and events are made up."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

ROOT = Path(__file__).parent.parent
OUT = ROOT / "proofs" / "demos"
OUT.mkdir(parents=True, exist_ok=True)
SANS = "/System/Library/Fonts/Helvetica.ttc"

INK = (22, 21, 20)
GREY = (120, 116, 108)
WHITE, CREAM, BONE = (248, 246, 241), (241, 235, 222), (233, 230, 224)


def font(style, size):
    return ImageFont.truetype(str(ROOT / "fonts" / f"Lowie-Proto-{style}.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


def sans(size):
    return ImageFont.truetype(SANS, size)


def fit(d, text, style, max_w, start, features=None):
    size = start
    while size > 20:
        f = font(style, size)
        if d.textlength(text, font=f, features=features) <= max_w:
            return f
        size -= 4
    return font(style, size)


def centre(d, y, text, f, W, fill=INK, features=None):
    w = d.textlength(text, font=f, features=features)
    d.text(((W - w) / 2, y), text, font=f, fill=fill, features=features)


def paper(W, H, colour, grain=8, seed=1):
    """Flat colour with a little noise so it reads as printed stock."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), colour)
    noise = Image.effect_noise((W, H), grain).convert("L")
    tint = Image.new("RGB", (W, H), tuple(max(0, c - 14) for c in colour))
    return Image.composite(tint, img, noise.point(lambda v: 36 if v > 140 + rnd.random() else 0))


def flash_day():
    """Poster for a studio flash day."""
    W, H = 1200, 1700
    img = paper(W, H, CREAM, seed=1)
    d = ImageDraw.Draw(img)
    centre(d, 110, "Studio Marrow presents", font("PokeLine", 60), W)
    centre(d, 250, "Flash Day", fit(d, "Flash Day", "Poke", W - 160, 300), W)
    centre(d, 560, "walk-ins only, first come first poked", font("PokeShaded", 58), W)
    d.line([160, 700, W - 160, 700], fill=INK, width=3)
    rows = [("Saturday 14 December", "Poke"), ("12:00 till the ink runs out", "PokeLine"),
            ("small pieces €60 · palm size €90", "Poke")]
    for i, (t, st) in enumerate(rows):
        centre(d, 770 + i * 140, t, fit(d, t, st, W - 200, 84), W)
    d.line([160, 1210, W - 160, 1210], fill=INK, width=3)
    centre(d, 1290, "Bloemgracht 9, Amsterdam", font("PokeLine", 64), W)
    centre(d, 1420, "18+ · bring ID · no booking", sans(30), W, GREY)
    return img


def flash_sheet():
    """A sheet of classic tattoo lettering, the way flash is hung in a studio."""
    W, H = 1400, 1400
    img = paper(W, H, BONE, grain=12, seed=2)
    d = ImageDraw.Draw(img)
    words = [("Mum", "Poke"), ("homesick", "PokeShaded"), ("hold fast", "Poke"),
             ("Forever yours", "PokeLine"), ("no regrets", "PokeShaded"), ("lucky 13", "Poke")]
    for i, (w, st) in enumerate(words):
        cx, cy = 60 + (i % 2) * 660, 60 + (i // 2) * 440
        d.rectangle([cx, cy, cx + 620, cy + 400], outline=GREY, width=2)
        f = fit(d, w, st, 540, 200)
        tw = d.textlength(w, font=f)
        d.text((cx + (620 - tw) / 2, cy + 90), w, font=f, fill=INK)
        d.text((cx + 20, cy + 355), f"{i + 1:02d}", font=sans(24), fill=GREY)
    return img


def zine():
    """A photocopied zine cover."""
    W, H = 1100, 1560
    img = paper(W, H, WHITE, grain=14, seed=3)
    d = ImageDraw.Draw(img)
    d.text((80, 80), "issue 3 · autumn", font=font("PokeLine", 54), fill=INK)
    d.text((80, 230), "small", font=fit(d, "small", "Poke", W - 160, 330), fill=INK)
    d.text((80, 560), "hours", font=fit(d, "hours", "Poke", W - 160, 330), fill=INK)
    d.line([80, 980, W - 80, 980], fill=INK, width=3)
    for i, t in enumerate(["night walks", "kitchen tattoos", "a letter to my sister",
                           "how to keep a sourdough alive"]):
        d.text((80, 1030 + i * 95), t, font=font("PokeShaded", 62), fill=INK)
    d.text((80, H - 110), "€4 · photocopied in Amsterdam", font=sans(28), fill=GREY)
    return img


def label():
    """A bottle label for small-batch kefir."""
    W, H = 1600, 900
    img = paper(W, H, CREAM, grain=8, seed=4)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 40, W - 40, H - 40], radius=40, outline=INK, width=4)
    d.rounded_rectangle([62, 62, W - 62, H - 62], radius=28, outline=INK, width=2)
    centre(d, 110, "wild & slow", font("PokeLine", 70), W)
    centre(d, 220, "Kefir", fit(d, "Kefir", "Poke", W - 500, 330), W)
    centre(d, 560, "geitenmelk · gefermenteerd · 48 uur", font("PokeShaded", 58), W)
    centre(d, 680, "batch 07 · 500 ml · best vóór 21-12", font("Poke", 52), W)
    centre(d, 780, "keep cold, shake gently", sans(28), W, GREY)
    return img


def specimen():
    """A type specimen card: every letter, figures and accents."""
    W, H = 1400, 1400
    img = paper(W, H, WHITE, grain=5, seed=5)
    d = ImageDraw.Draw(img)
    d.text((80, 70), "Lowie Poke", font=sans(34), fill=GREY)
    d.text((80, 140), "Aa Gg Rr", font=fit(d, "Aa Gg Rr", "Poke", W - 160, 260), fill=INK)
    lines = [("Sphinx of black quartz,", "Poke", 92), ("judge my vow.", "Poke", 92),
             ("Café, crème brûlée, naïve", "PokeShaded", 76), ("Zoë and the piñata", "PokeShaded", 76),
             ("0123456789 & € £ $ %", "PokeLine", 76)]
    y = 520
    for t, st, sz in lines:
        d.text((80, y), t, font=fit(d, t, st, W - 160, sz), fill=INK)
        y += sz + 64
    return img


def joins():
    """The font's own wordmark, with the two join settings side by side."""
    W, H = 1600, 900
    img = paper(W, H, WHITE, grain=5, seed=6)
    d = ImageDraw.Draw(img)
    centre(d, 70, "Lowie", fit(d, "Lowie", "Poke", W - 420, 400), W)
    centre(d, 500, "a connected hand-poke serif", font("PokeLine", 70), W)
    d.text((120, 660), "mixed joins (default)", font=sans(26), fill=GREY)
    d.text((120, 700), "brown woven", font=font("Poke", 80), fill=INK)
    d.text((860, 660), "all low joins (ss01)", font=sans(26), fill=GREY)
    d.text((860, 700), "brown woven", font=font("Poke", 80), fill=INK, features=["ss01"])
    return img


DEMOS = {"flash-day": flash_day, "specimen": specimen, "zine": zine,
         "flash-sheet": flash_sheet, "label": label, "joins": joins}
ROWS = (("flash-day", "label", "zine"), ("flash-sheet", "specimen", "joins"))

if __name__ == "__main__":
    imgs = {}
    for name, fn in DEMOS.items():
        imgs[name] = fn()
        imgs[name].save(OUT / f"{name}.png")
    # contact sheet, every demo scaled to the same height
    h = 600
    scaled = [[imgs[n].resize((int(imgs[n].width * h / imgs[n].height), h), Image.LANCZOS) for n in r]
              for r in ROWS]
    W = max(sum(im.width for im in r) + 40 * (len(r) + 1) for r in scaled)
    sheet = Image.new("RGB", (W, 2 * h + 120), (255, 255, 255))
    edge = (222, 218, 210)
    for j, r in enumerate(scaled):
        x = 40
        for im in r:
            y = 40 + j * (h + 40)
            sheet.paste(im, (x, y))
            ImageDraw.Draw(sheet).rectangle([x - 1, y - 1, x + im.width, y + h], outline=edge)
            x += im.width + 40
    sheet.save(OUT / "demos-sheet.png")
    print("ok", list(DEMOS))
