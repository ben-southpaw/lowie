"""Mock-ups of Lowie Poke in use. Writes PNGs to ../proofs/demos/."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

ROOT = Path(__file__).parent.parent
OUT = ROOT / "proofs" / "demos"
OUT.mkdir(parents=True, exist_ok=True)
SANS = "/System/Library/Fonts/Helvetica.ttc"


def font(style, size):
    return ImageFont.truetype(str(ROOT / "fonts" / f"Lowie-Proto-{style}.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


def fit(d, text, style, max_w, start):
    size = start
    while size > 20:
        f = font(style, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(style, size)


def centre(d, y, text, f, fill, W, features=None):
    w = d.textlength(text, font=f, features=features)
    d.text(((W - w) / 2, y), text, font=f, fill=fill, features=features)


def paper(W, H, colour, grain=10, seed=1):
    """Flat colour with a little noise so it reads as printed stock."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), colour)
    noise = Image.effect_noise((W, H), grain).convert("L")
    tint = Image.new("RGB", (W, H), tuple(max(0, c - 18) for c in colour))
    img = Image.composite(tint, img, noise.point(lambda v: 40 if v > 140 + rnd.random() else 0))
    return img


def poster():
    W, H = 1200, 1700
    img = paper(W, H, (236, 228, 214))
    d = ImageDraw.Draw(img)
    ink, red = (28, 26, 24), (196, 40, 52)
    d.rectangle([60, 60, W - 60, H - 60], outline=ink, width=3)
    centre(d, 140, "late night cinema", font("PokeLine", 64), red, W)
    f = fit(d, "Amsterdam", "Poke", W - 200, 300)
    centre(d, 330, "Amsterdam", f, ink, W)
    centre(d, 620, "slow films, strong coffee", font("PokeShaded", 72), ink, W)
    d.line([200, 800, W - 200, 800], fill=ink, width=2)
    for i, (day, film) in enumerate([("vrijdag", "The quiet hours"), ("zaterdag", "Rivers & ruins"),
                                     ("zondag", "Één nacht")]):
        y = 880 + i * 190
        d.text((200, y), day, font=font("PokeLine", 60), fill=red)
        d.text((200, y + 70), film, font=font("Poke", 92), fill=ink)
    centre(d, H - 200, "Doors 21:00 · €9", font("Poke", 64), ink, W)
    return img


def sleeve():
    W = H = 1400
    img = paper(W, W, (24, 26, 30), grain=14, seed=2)
    d = ImageDraw.Draw(img)
    cream = (234, 223, 200)
    d.ellipse([300, 230, 1100, 1030], outline=(196, 40, 52), width=6)
    f = fit(d, "slow rivers", "Poke", W - 260, 260)
    centre(d, 520, "slow rivers", f, cream, W)
    centre(d, 1120, "side a: hollow · borrowed light · nine", font("PokeLine", 46), cream, W)
    centre(d, 1190, "side b: woven · the long drive home", font("PokeLine", 46), cream, W)
    return img


def flash():
    """A tattoo flash sheet: words in boxes on aged paper."""
    W, H = 1400, 1400
    img = paper(W, H, (232, 220, 196), grain=16, seed=3)
    d = ImageDraw.Draw(img)
    ink, red = (24, 22, 20), (178, 34, 44)
    centre(d, 60, "flash", font("PokeLine", 90), red, W)
    words = [("mum", "Poke", ink), ("forever", "PokeShaded", ink), ("hold fast", "Poke", red),
             ("lucky", "PokeLine", ink), ("zonder", "Poke", ink), ("rover", "PokeShaded", red)]
    for i, (w, style, col) in enumerate(words):
        cx, cy = 60 + (i % 2) * 660, 220 + (i // 2) * 380
        d.rectangle([cx, cy, cx + 620, cy + 330], outline=(120, 100, 80), width=2)
        f = fit(d, w, style, 540, 190)
        tw = d.textlength(w, font=f)
        d.text((cx + (620 - tw) / 2, cy + 50), w, font=f, fill=col)
        d.text((cx + 20, cy + 290), f"{i + 1:02d}", font=ImageFont.truetype(SANS, 24), fill=(120, 100, 80))
    return img


def cafe():
    """A chalkboard café sign."""
    W, H = 1400, 1000
    img = paper(W, H, (40, 46, 42), grain=18, seed=4)
    d = ImageDraw.Draw(img)
    chalk, warm = (232, 230, 220), (236, 196, 120)
    d.rectangle([30, 30, W - 30, H - 30], outline=(120, 90, 60), width=24)
    centre(d, 90, "koffie & kefir", fit(d, "koffie & kefir", "Poke", W - 240, 170), chalk, W)
    rows = [("één koffie", "€2,80"), ("flat white", "€3,90"), ("kefir, huisgemaakt", "€3,50"),
            ("appeltaart", "€4,20")]
    for i, (item, price) in enumerate(rows):
        y = 390 + i * 120
        d.text((150, y), item, font=font("PokeLine", 80), fill=chalk)
        pw = d.textlength(price, font=font("Poke", 80))
        d.text((W - 150 - pw, y), price, font=font("Poke", 80), fill=warm)
    return img


def cover():
    W, H = 1100, 1650
    img = paper(W, H, (176, 196, 186), grain=10, seed=5)
    d = ImageDraw.Draw(img)
    ink = (22, 34, 32)
    centre(d, 180, "a novel", font("PokeLine", 60), ink, W)
    f = fit(d, "The quiet", "PokeShaded", W - 160, 240)
    centre(d, 420, "The quiet", f, ink, W)
    centre(d, 680, "hours", fit(d, "hours", "PokeShaded", W - 160, 300), ink, W)
    d.ellipse([W / 2 - 14, 1060, W / 2 + 14, 1088], fill=ink)
    centre(d, H - 260, "Ben Dryden", font("Poke", 90), ink, W)
    return img


def wordmark():
    """The font's own wordmark, with the two join settings side by side."""
    W, H = 1600, 900
    img = paper(W, H, (246, 243, 238), grain=6, seed=6)
    d = ImageDraw.Draw(img)
    ink, red = (27, 26, 24), (208, 33, 111)
    centre(d, 80, "Lowie", fit(d, "Lowie", "Poke", W - 400, 400), ink, W)
    centre(d, 520, "a connected hand-poke serif", font("PokeLine", 70), ink, W)
    lab = ImageFont.truetype(SANS, 26)
    d.text((120, 680), "mixed joins (default)", font=lab, fill=red)
    d.text((120, 720), "brown woven", font=font("Poke", 76), fill=ink)
    d.text((860, 680), "all low joins (ss01)", font=lab, fill=red)
    d.text((860, 720), "brown woven", font=font("Poke", 76), fill=ink, features=["ss01"])
    return img


DEMOS = {"poster": poster, "sleeve": sleeve, "flash": flash, "cafe": cafe, "cover": cover,
         "wordmark": wordmark}

if __name__ == "__main__":
    imgs = {}
    for name, fn in DEMOS.items():
        imgs[name] = fn()
        imgs[name].save(OUT / f"{name}.png")
    # contact sheet, every demo scaled to the same height
    h = 600
    row1 = [imgs[n] for n in ("poster", "sleeve", "cover")]
    row2 = [imgs[n] for n in ("flash", "cafe", "wordmark")]
    scaled = [[im.resize((int(im.width * h / im.height), h), Image.LANCZOS) for im in r] for r in (row1, row2)]
    W = max(sum(im.width for im in r) + 40 * (len(r) + 1) for r in scaled)
    sheet = Image.new("RGB", (W, 2 * h + 120), (250, 249, 246))
    for j, r in enumerate(scaled):
        x = 40
        for im in r:
            sheet.paste(im, (x, 40 + j * (h + 40)))
            x += im.width + 40
    sheet.save(OUT / "demos-sheet.png")
    print("ok", list(DEMOS))
