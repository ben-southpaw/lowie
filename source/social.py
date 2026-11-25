"""Instagram carousel for Lowie: 1080x1350, black on light. Writes to ../launch/."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
OUT = ROOT / "launch"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1350
INK, GREY, PAPER = (22, 21, 20), (120, 116, 108), (248, 246, 241)
SANS = "/System/Library/Fonts/Helvetica.ttc"


def f(style, size):
    return ImageFont.truetype(str(ROOT / "fonts" / f"Lowie-Proto-{style}.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


def s(size):
    return ImageFont.truetype(SANS, size)


def canvas():
    img = Image.new("RGB", (W, H), PAPER)
    return img, ImageDraw.Draw(img)


def centre(d, y, t, font, fill=INK, features=None):
    w = d.textlength(t, font=font, features=features)
    d.text(((W - w) / 2, y), t, font=font, fill=fill, features=features)


def foot(d, n):
    d.text((60, H - 80), "Lowie · free and open source", font=s(26), fill=GREY)
    t = f"{n}/5"
    d.text((W - 60 - d.textlength(t, font=s(26)), H - 80), t, font=s(26), fill=GREY)


def slide1():
    img, d = canvas()
    centre(d, 360, "Lowie", f("Poke", 330))
    centre(d, 760, "a connected serif", f("PokeLine", 72))
    centre(d, 860, "in hand-poke tattoo dots", f("PokeLine", 72))
    foot(d, 1)
    return img


def slide2():
    img, d = canvas()
    d.text((70, 90), "Three styles", font=s(32), fill=GREY)
    for i, (t, st, lab) in enumerate([("hold fast", "Poke", "Poke"), ("slow rivers", "PokeShaded", "Poke Shaded"),
                                       ("borrowed light", "PokeLine", "Poke Line")]):
        y = 200 + i * 330
        size = 170
        while d.textlength(t, font=f(st, size)) > W - 140:
            size -= 6
        d.text((70, y), t, font=f(st, size), fill=INK)
        d.text((70, y + size + 30), lab, font=s(28), fill=GREY)
    foot(d, 2)
    return img


def slide3():
    img, d = canvas()
    d.text((70, 90), "Every letter joins the next", font=s(32), fill=GREY)
    centre(d, 300, "brown woven", f("Poke", 150))
    centre(d, 500, "default: b o r v w join high", s(28), GREY)
    centre(d, 700, "brown woven", f("Poke", 150), features=["ss01"])
    centre(d, 900, "stylistic set 1: every join low", s(28), GREY)
    foot(d, 3)
    return img


def from_demo(name, n, label):
    img, d = canvas()
    demo = Image.open(ROOT / "proofs" / "demos" / f"{name}.png")
    box_w, box_h = W - 140, H - 300
    k = min(box_w / demo.width, box_h / demo.height)
    demo = demo.resize((int(demo.width * k), int(demo.height * k)), Image.LANCZOS)
    x, y = (W - demo.width) // 2, 150 + (box_h - demo.height) // 2
    img.paste(demo, (x, y))
    d.rectangle([x - 1, y - 1, x + demo.width, y + demo.height], outline=(222, 218, 210))
    d.text((70, 70), label, font=s(32), fill=GREY)
    foot(d, n)
    return img


if __name__ == "__main__":
    slides = [slide1(), slide2(), slide3(), from_demo("flash-sheet", 4, "Made for flash"),
              from_demo("flash-day", 5, "and posters")]
    for i, im in enumerate(slides, 1):
        im.save(OUT / f"instagram-{i}.png")
    # square cover for Are.na, Reddit and link previews
    sq = Image.new("RGB", (1200, 1200), PAPER)
    sq.paste(slides[0].crop((0, 75, 1080, 1275)).resize((1200, 1200 * 1200 // 1200)), (0, 0))
    sq.save(OUT / "square.png")
    print("ok")
