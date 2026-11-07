"""Lowie prototype: a connected high-contrast serif, built from code.

Each variant in VARIANTS is a set of design settings. Change a number, rerun,
compare proofs.

Join types:
  diagonal - leaves at the baseline, arrives at the next letter's x-height
             (stroke width set by `joinw`: hairline, broken or wedge)
  rail     - foot serifs run on into one continuous baseline stroke
  top      - head serifs run on into one continuous stroke along the x-height
  powder   - a diagonal join made of loose grains, like a line of snow or flour
  powder-rail - a straight baseline line of grains

Dot mode (`dots` setting): after a glyph is drawn, its outline is redrawn as
hand-poke dots. A row of dots traces each edge, then looser dots fill the inside
("outline" skips the fill). Hairlines become a single row of dots.

Outlines: curved parts are smooth quadratic splines through sampled points,
merged into one clean outline per glyph (skia-pathops). A `calt` feature swaps
isolated / initial / medial / final forms so words join and word edges stay clean.
"""
import math
import unicodedata
import random
from pathlib import Path

import pathops
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image, ImageChops, ImageDraw

OUT = Path(__file__).parent.parent / "fonts"
UPM = 1000
ASC = 740
CAP = 700
JY = 240            # low joins cross the glyph edge at this height
JH_DROP = 60        # high joins cross it this far below the x-height

DEFAULTS = dict(
    join="diagonal",
    joinw=("wedge", 22, 95),   # (kind, thin end, thick end)
    rail=26,                   # thickness of rail / top joins
    xh=480,                    # x-height
    st=88, stc=96,             # lowercase and capital stem
    thin=20,                   # hairline in arches and bowls
    sf=18, so=38,              # serif thickness and overhang
    sb=115,                    # sidebearing
    cn=185, cm=150,            # counter width of n/u and of m
    orx=215, Orx=300,          # half-width of o and O
    slant=0,                   # degrees
    grain=9,                   # powder: typical grain radius
    density=0.6,               # powder: share of the join area covered by grains
    scatter=0.12,              # powder: share of grains that stray outside the line
    dots=None,                 # None, "fill" or "outline": redraw the letter as dots
    dot=11,                    # dot radius
    gap=30,                    # distance between dot centres
    jitter=0.25,               # dot randomness: size, spacing, position
    high_exits="borvw",        # letters whose join leaves from the top, as in handwriting
)

VARIANTS = {
    "Wedge Heavy": {},
    "Wedge Heavy Low": dict(high_exits=""),
    "Rail": dict(join="rail", rail=24),
    "Headline": dict(join="top", rail=30),
    "Slab": dict(joinw=("wedge", 40, 90), st=96, stc=104, thin=46, sf=36, so=44),
    "Italic": dict(slant=12),
    "Condensed": dict(cn=110, cm=95, orx=165, Orx=230, sb=85),
    "Powder": dict(join="powder", joinw=("wedge", 40, 100), grain=11, density=1.5),
    "Powder Fine": dict(join="powder", joinw=("wedge", 30, 70), grain=7, density=1.6, scatter=0.08),
    "Powder Rail": dict(join="powder-rail", rail=48, grain=9, density=1.5),
    "Poke Low": dict(dots="poke", dot=15, gap=27, jitter=0.3, joinw=("wedge", 40, 90), high_exits="",
                     st=104, stc=112, thin=50, sf=40, so=44),
    # Release Poke from 0.6: Poke Soft Plus (Ben, 2026-11-07).
    # History: 0.2 and 0.4 Poke Soft, 0.3 Poke Even, 0.5 Poke Ink 85.
    "Poke": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.6, 1.15), fill=(0.25, 0.5, 1.15, 5),
                 rough=0.9, round_rough=0.35, odd_share=0.15, ink_scale=1.0,
                 joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # The 0.1 Poke: rows that follow the contour
    "Poke Classic": dict(dots="poke", dot=15, gap=27, jitter=0.3, joinw=("wedge", 40, 90),
                         st=104, stc=112, thin=50, sf=40, so=44),
    # Fewer, bigger dots, so the dots still read at 50 to 100px (Ben, 2026-11-06)
    "Poke Big": dict(dots="poke", dot=24, gap=44, jitter=0.3, joinw=("wedge", 48, 96),
                     st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Soft": dict(dots="organic", dot=24, gap=44, jitter=0.3, joinw=("wedge", 48, 96),
                      st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Soft Fine": dict(dots="organic", dot=19, gap=35, jitter=0.3, joinw=("wedge", 44, 92),
                           st=108, stc=116, thin=56, sf=44, so=46),
    # Separated dots: diameter below the minimum spacing, so dots do not merge
    # into clumps or leave sharp notches where they overlap (Ben, 2026-11-07)
    # Soft plus small dots in the gaps (Ben: "more variety with smaller dots", 2026-11-07)
    "Poke Mix": dict(dots="organic", dot=24, gap=44, jitter=0.3, fill=(0.3, 0.55, 0.6, 20),
                     joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Wider size range in the main dots too, plus the gap fill
    "Poke Mix Wide": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25),
                          joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Mix Wide with irregular hand-poke dots (Ben: "too circular, too perfect", 2026-11-07)
    "Poke Ink": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25), rough=1.0,
                     joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Ink with dots drawn smaller at the same spacing, so fewer merge (Ben, 2026-11-07)
    "Poke Ink 85": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25), rough=1.0, ink_scale=0.85,
                        joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Ink 75": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25), rough=1.0, ink_scale=0.75,
                        joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Mostly round dots, some irregular (Ben: "too stone like", 2026-11-07)
    "Poke Ink Round": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25),
                           rough=1.0, round_rough=0.15, odd_share=0.35, ink_scale=0.9,
                           joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Ink Rounder": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25),
                             rough=0.8, round_rough=0.1, odd_share=0.2, ink_scale=0.95,
                             joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Soft's spacing and gentle lumps, a little size variety, sparse small dots that do not
    # touch, the odd irregular dot (Ben: "looks like bubbles", 2026-11-07)
    "Poke Soft Plus": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.6, 1.15), fill=(0.25, 0.5, 1.15, 5),
                           rough=0.9, round_rough=0.35, odd_share=0.15, ink_scale=1.0,
                           joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    # Release Shaded and Line from 0.7: same dots and skeleton as Poke 0.6 (Ben, 2026-11-07).
    # The 0.1 to 0.6 versions are kept as Poke Shaded Classic and Poke Line Classic.
    "Poke Shaded": dict(dots="organic", dot=15, gap=28, jitter=0.3, spread=(0.7, 1.15),
                             rough=0.9, round_rough=0.35, odd_share=0.15, wob=0.2, edge_rows=1, edge_keep=0.9,
                             edge_inset=(0.8, 1.2), inner=(1.35, 0.7),
                             joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Line": dict(dots="organic", dot=14, gap=27, jitter=0.3, spread=(0.75, 1.15),
                           rough=0.9, round_rough=0.35, odd_share=0.15, wob=0.15, edge_rows=1, edge_keep=0.93,
                           edge_inset=(0.8, 1.15), inner=(0, 0),
                           joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Ink Rough": dict(dots="organic", dot=24, gap=44, jitter=0.3, spread=(0.5, 1.2), fill=(0.25, 0.6, 0.5, 25), rough=1.8,
                           joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Sparse": dict(dots="organic", dot=16, gap=44, jitter=0.3, spread=(0.85, 1.1), blow=0.0, wob=0.2,
                        joinw=("wedge", 48, 96), st=112, stc=120, thin=60, sf=48, so=48),
    "Poke Even": dict(dots="organic", dot=13, gap=36, jitter=0.3, spread=(0.85, 1.1), blow=0.0, wob=0.2,
                      joinw=("wedge", 44, 92), st=108, stc=116, thin=56, sf=44, so=46),
    "Poke Bigger": dict(dots="poke", dot=32, gap=60, jitter=0.3, joinw=("wedge", 60, 104),
                        st=124, stc=132, thin=70, sf=56, so=52),
    "Poke Shaded Classic": dict(dots="shade", dot=13, gap=27, jitter=0.3, joinw=("wedge", 40, 90),
                        st=104, stc=112, thin=50, sf=40, so=44),
    "Poke Line Classic": dict(dots="line", dot=11, gap=22, jitter=0.3, joinw=("wedge", 40, 90),
                      st=104, stc=112, thin=50, sf=40, so=44),
    "Dot": dict(dots="fill", dot=15, gap=30, jitter=0.3),
    "Dot Fine": dict(dots="fill", dot=9, gap=18, jitter=0.25),
    "Dot Slab": dict(dots="fill", dot=17, gap=33, jitter=0.3, joinw=("wedge", 40, 90),
                     st=104, stc=112, thin=50, sf=40, so=44),
    "Dot Outline": dict(dots="outline", dot=13, gap=25, joinw=("wedge", 26, 70), thin=26, sf=24),
    # earlier styles, kept for reference
    "Wedge": dict(joinw=("wedge", 14, 60)),
    "Hairline": dict(joinw=("hairline", 15, 15)),
    "Broken": dict(joinw=("broken", 26, 26)),
}

P = dict(DEFAULTS)  # active settings, set by build()
RNG = random.Random(1)  # reseeded per build, so builds are repeatable


# ---------- geometry helpers ----------
# Shapes: ("poly", pts) straight sides; ("closed", pts) smooth closed spline;
# ("stroke", left, right) smooth sides with straight end caps.

def rect(x0, y0, x1, y1):
    return ("poly", [(x0, y0), (x0, y1), (x1, y1), (x1, y0)])


def ellipse(cx, cy, rx, ry, n=32):
    return ("closed", [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                       for i in range(n)])


def cubic(p, t):
    mt = 1 - t
    return tuple(mt**3 * p[0][k] + 3 * mt * mt * t * p[1][k] + 3 * mt * t * t * p[2][k] + t**3 * p[3][k]
                 for k in (0, 1))


def cubic_d(p, t):
    mt = 1 - t
    return tuple(3 * mt * mt * (p[1][k] - p[0][k]) + 6 * mt * t * (p[2][k] - p[1][k]) + 3 * t * t * (p[3][k] - p[2][k])
                 for k in (0, 1))


def smooth(a, b, t):
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    u = (t - a) / (b - a)
    return u * u * (3 - 2 * u)


def stroke(p, w, t0=0.0, t1=1.0, n=24):
    """Variable-width stroke along cubic p. w(t) gives full width at t."""
    left, right = [], []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        x, y = cubic(p, t)
        dx, dy = cubic_d(p, t)
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        h = w(t) / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    return ("stroke", left, right)


def grain(cx, cy, r, ang, stretch):
    """One grain: a small ellipse, stretched along the line, slightly lumpy."""
    pts = []
    for i in range(8):
        a = 2 * math.pi * i / 8
        k = 1 + RNG.uniform(-0.18, 0.18)
        x, y = math.cos(a) * r * stretch * k, math.sin(a) * r * k
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    return ("closed", pts)


def powder(p, w, t0=0.0, t1=1.0):
    """Fill the band a stroke would cover with loose grains."""
    samples = [t0 + (t1 - t0) * i / 40 for i in range(41)]
    pts = [cubic(p, t) for t in samples]
    band = sum(math.dist(pts[i], pts[i + 1]) * w(samples[i]) for i in range(40))
    g = P["grain"]
    n = int(band * P["density"] / (math.pi * g * g * 1.4))
    shapes = []
    for _ in range(n):
        t = RNG.uniform(t0, t1)
        x, y = cubic(p, t)
        dx, dy = cubic_d(p, t)
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        half = w(t) / 2
        if RNG.random() < P["scatter"]:
            off = RNG.uniform(-1, 1) * (half + 3 * g)       # strays outside the line
            r = g * RNG.uniform(0.3, 0.6)
        else:
            off = max(-1, min(1, RNG.gauss(0, 0.45))) * max(half - g * 0.5, 1)
            r = g * RNG.uniform(0.55, 1.15) * (0.7 + 0.3 * min(1, half / 30))
        shapes.append(grain(x + nx * off, y + ny * off, r, math.atan2(dy, dx), RNG.uniform(1.0, 1.7)))
    return ("multi", shapes)


class FlattenPen(BasePen):
    """Collect an outline as closed polygons."""

    def __init__(self):
        super().__init__(None)
        self.contours, self.cur = [], []

    def _moveTo(self, pt):
        self.cur = [pt]

    def _lineTo(self, pt):
        self.cur.append(pt)

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, 7):
            t = i / 6
            self.cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, 9):
            self.cur.append(cubic([p0, p1, p2, p3], i / 8))

    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def dotify(path):
    """Redraw a merged outline as irregular hand-poke dots."""
    fp = FlattenPen()
    path.draw(fp)
    if not fp.contours:
        return path
    ox, oy = 300, 400                      # mask offset, so negative coordinates fit
    W, H = 2200, 1600
    mask = Image.new("1", (W, H), 0)
    for c in fp.contours:                  # even-odd fill: holes cut out
        tmp = Image.new("1", (W, H), 0)
        ImageDraw.Draw(tmp).polygon([(x + ox, H - (y + oy)) for x, y in c], fill=1)
        mask = ImageChops.logical_xor(mask, tmp)
    px = mask.load()

    def inside(x, y):
        X, Y = int(x + ox), int(H - (y + oy))
        return 0 <= X < W and 0 <= Y < H and px[X, Y]

    r0, gap, jit = P["dot"], P["gap"], P["jitter"]
    cell = gap / 1.5
    grid, dots = {}, []

    def free(x, y, dmin):
        gx, gy = int(x // cell), int(y // cell)
        for i in range(gx - 2, gx + 3):
            for j in range(gy - 2, gy + 3):
                for (qx, qy, qr) in grid.get((i, j), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < dmin * dmin:
                        return False
        return True

    def clear(x, y, r, k):
        """True if a dot of radius r at (x, y) overlaps each neighbour by at most
        (1 - k) of its own radius: k=1 means not touching."""
        gx, gy = int(x // cell), int(y // cell)
        for i in range(gx - 3, gx + 4):
            for j in range(gy - 3, gy + 4):
                for (qx, qy, qr) in grid.get((i, j), ()):
                    if math.hypot(qx - x, qy - y) < qr + r * k:
                        return False
        return True
    free.clear = clear

    def add(x, y, r):
        grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y, r))
        dots.append((x, y, r))

    if P["dots"] in ("poke", "shade", "line"):
        poke_rows(fp, inside, free, add)
        return dots_to_path(dots)
    if P["dots"] == "organic":
        organic(fp, inside, free, add)
        return dots_to_path(dots)

    # 1. a row of dots tracing every edge, set just inside the line
    for c in fp.contours:
        pts = c + [c[0]]
        carry = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg == 0:
                continue
            ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
            d = carry
            while d < seg:
                x, y = x0 + ux * d, y0 + uy * d
                inset = r0 * 0.85
                for nx, ny in ((-uy, ux), (uy, -ux)):
                    cx, cy = x + nx * inset, y + ny * inset
                    if inside(cx, cy):
                        cx += RNG.gauss(0, jit * r0 * 0.4)
                        cy += RNG.gauss(0, jit * r0 * 0.4)
                        if free(cx, cy, gap * 0.78):
                            add(cx, cy, r0 * RNG.uniform(1 - jit, 1 + jit * 0.6))
                        break
                d += gap * RNG.uniform(0.85, 1.1)
            carry = d - seg

    # 2. looser dots filling the inside, like shading
    if P["dots"] == "fill":
        xs = [x for c in fp.contours for x, _ in c]
        ys = [y for c in fp.contours for _, y in c]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        tries = int((x1 - x0) * (y1 - y0) / (gap * gap) * 12)
        for _ in range(tries):
            x, y = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
            if inside(x, y) and free(x, y, gap * 0.95):
                add(x, y, r0 * RNG.uniform(1 - jit, 1 + jit * 0.4))

    return dots_to_path(dots)


def ink_dot(cx, cy, r, rough, extras=True):
    """One hand-poke dot: a lumpy blob, often oval or teardrop where the needle
    went in at an angle. rough scales every irregularity (0 = near circle)."""
    ang = P.get("_hand", 0.0) + RNG.gauss(0, 0.6)          # the hand keeps a rough angle
    stretch = 1 + rough * RNG.uniform(0.0, 0.45)
    tail = rough * RNG.uniform(0.0, 0.5) if RNG.random() < 0.35 else 0.0
    flat = rough * RNG.uniform(0.1, 0.3) if RNG.random() < 0.15 else 0.0
    harm = [(k, rough * RNG.uniform(0.02, 0.12) / k * 2, RNG.uniform(0, 2 * math.pi)) for k in (2, 3, 5)]
    fa = RNG.uniform(0, 2 * math.pi)
    pts = []
    n = 18
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + sum(amp * math.cos(h * a + ph) for h, amp, ph in harm)
        k *= 1 + tail * max(0.0, math.cos(a)) ** 3          # drag one side to a point
        if flat and math.cos(a - fa) > 0.75:                  # a flattened side
            k *= 1 - flat * (math.cos(a - fa) - 0.75) * 4
        x, y = math.cos(a) * r * k * stretch, math.sin(a) * r * k
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    out = [("closed", pts)]
    if extras and RNG.random() < 0.12 * rough:                # double poke: a peanut
        d = r * RNG.uniform(0.5, 0.8); b = ang + RNG.gauss(0, 0.8)
        out += ink_dot(cx + d * math.cos(b), cy + d * math.sin(b), r * RNG.uniform(0.6, 0.85), rough, False)
    if extras and RNG.random() < 0.10 * rough:                # a speck of spread ink
        d = r * RNG.uniform(1.4, 2.0); b = RNG.uniform(0, 2 * math.pi)
        out += ink_dot(cx + d * math.cos(b), cy + d * math.sin(b), r * RNG.uniform(0.15, 0.28), rough * 0.5, False)
    return out


def dots_to_path(dots):
    jit = P["jitter"]
    out = pathops.Path(fillType=pathops.FillType.WINDING)
    pen = out.getPen()
    rough = P.get("rough")
    if rough:
        P["_hand"] = RNG.uniform(0, math.pi)
        for x, y, r in dots:
            share = P.get("odd_share", 1.0)                  # share of dots drawn irregular
            if r > P["dot"] * 0.9:                             # big dots stay mostly round
                share *= 0.4
            rr = rough if RNG.random() < share else P.get("round_rough", rough)
            for sh in ink_dot(x, y, r * P.get("ink_scale", 1.0), rr):
                emit(pen, sh, True)
        out.simplify(fix_winding=True, keep_starting_points=False, clockwise=True)
        return out
    for x, y, r in dots:
        emit(pen, grain(x, y, r, RNG.uniform(0, math.pi), RNG.uniform(1.0, 1.0 + jit * 0.6)), True)
    out.simplify(fix_winding=True, keep_starting_points=False, clockwise=True)
    return out


def organic(fp, inside, free, add):
    """Hand-poke without a traced outline: one loose edge row that drifts in and
    out with gaps, then random packing inside (no rows), so the letter ends where
    the dots stop rather than at a drawn line."""
    r0, gap, jit = P["dot"], P["gap"], P["jitter"]

    def size():
        lo, hi = P.get("spread", (0.72, 1.15))
        r = r0 * RNG.uniform(lo, hi)
        return r * 1.4 if RNG.random() < P.get("blow", 0.04) else r   # a few blowouts

    # 1. loose edge: irregular spacing, wandering inset, ~20% missing
    rows, keep = P.get("edge_rows", 1), P.get("edge_keep", 0.8)
    for c, row in [(c, k) for k in range(rows) for c in fp.contours]:
        pts = c + [c[0]]
        carry, wob = 0.0, 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg == 0:
                continue
            ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
            d = carry
            while d < seg:
                wob = wob * 0.7 + RNG.gauss(0, r0 * P.get("wob", 0.35))
                x, y = x0 + ux * d, y0 + uy * d
                for nx, ny in ((-uy, ux), (uy, -ux)):
                    if not inside(x + nx * 2, y + ny * 2):
                        continue
                    lo, hi = P.get("edge_inset", (0.7, 1.6))
                    inset = r0 * RNG.uniform(lo, hi) + wob + row * gap * 0.8
                    cx, cy = x + nx * inset, y + ny * inset
                    if RNG.random() < keep and inside(cx, cy) and free(cx, cy, gap * 0.82):
                        add(cx, cy, size())
                    break
                d += gap * RNG.uniform(0.85, 1.35)
            carry = d - seg

    # 2. random packing inside (dart throwing gives an even but rowless spread)
    xs = [x for c in fp.contours for x, _ in c]
    ys = [y for c in fp.contours for _, y in c]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    space, scale = P.get("inner", (1.0, 1.0))         # interior spacing and dot size (shade: sparser)
    tries = int((x1 - x0) * (y1 - y0) / (gap * gap) * 30) if space else 0
    for _ in range(tries):
        x, y = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
        if inside(x, y) and free(x, y, gap * space * RNG.uniform(0.8, 0.95)):
            add(x, y, size() * scale)

    # 3. small dots in the gaps, as when the needle goes in shallow
    fill = P.get("fill")
    if fill:
        lo, hi, k, n = fill            # radius range (x r0), overlap allowance, tries per gap^2
        for _ in range(int((x1 - x0) * (y1 - y0) / (gap * gap) * n)):
            x, y = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
            r = r0 * RNG.uniform(lo, hi)
            if inside(x, y) and free.clear(x, y, r, k):
                add(x, y, r)


def poke_rows(fp, inside, free, add):
    """Hand-poke packing: rows of dots that follow the outline inwards, the way
    a tattooist works a line and then packs it. Each row drifts as a whole
    (a slow wobble, not independent jitter), a few dots go missing, a few blow out.
      poke  - rows packed all the way in: a solid, beaded letter
      shade - dense edge row, rows thin out towards the middle (dotwork shading)
      line  - only the two outer rows: line work
    """
    r0, gap, jit, mode = P["dot"], P["gap"], P["jitter"], P["dots"]
    rowgap = gap * 0.82
    for k in range(2 if mode == "line" else 14):
        inset = r0 * 0.9 + k * rowgap
        if mode == "shade" and k:
            keep, step = max(0.15, 0.85 - 0.2 * k), gap * (1 + 0.3 * k)
        else:
            keep, step = 0.96, gap
        placed = 0
        for c in fp.contours:
            pts = c + [c[0]]
            carry, wob = 0.0, 0.0
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                seg = math.hypot(x1 - x0, y1 - y0)
                if seg == 0:
                    continue
                ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
                d = carry
                while d < seg:
                    wob = wob * 0.85 + RNG.gauss(0, r0 * 0.2)
                    x, y = x0 + ux * d, y0 + uy * d
                    for nx, ny in ((-uy, ux), (uy, -ux)):
                        if not inside(x + nx * 2, y + ny * 2):
                            continue
                        cx, cy = x + nx * (inset + wob), y + ny * (inset + wob)
                        if inside(cx, cy) and RNG.random() < keep:
                            cx += RNG.gauss(0, jit * r0 * 0.2)
                            cy += RNG.gauss(0, jit * r0 * 0.2)
                            if free(cx, cy, gap * (0.74 if k == 0 else 0.8)):
                                r = r0 * RNG.uniform(1 - jit, 1 + jit * 0.5)
                                if RNG.random() < 0.03:
                                    r *= 1.45          # a blowout
                                add(cx, cy, r)
                                placed += 1
                        break
                    d += step * RNG.uniform(0.85, 1.08)
                carry = d - seg
        if placed == 0:
            break


def area(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly))) / 2


def orient(poly, clockwise=True):
    return poly[::-1] if (area(poly) < 0) != clockwise else poly


# ---------- joins ----------

K = 75
DIR = (1 / math.hypot(1, 1.5), 1.5 / math.hypot(1, 1.5))


def join_width(part):
    kind, lo, hi = P["joinw"]
    if kind == "hairline":
        return (lambda t: lo), (0.0, 1.0)
    if kind == "broken":
        if part == "exit":
            return (lambda t: hi * (1 - t / 0.68) ** 0.8 if t < 0.68 else 0), (0.0, 0.68)
        return (lambda t: hi * ((t - 0.32) / 0.68) ** 0.8 if t > 0.32 else 0), (0.32, 1.0)
    if part == "exit":
        return (lambda t: lo + (hi - lo) * (1 - smooth(0.0, 0.55, t))), (0.0, 1.0)
    return (lambda t: lo + (hi - lo) * smooth(0.45, 1.0, t)), (0.0, 1.0)


def exit_join(a, adv, kind="low"):
    xh, r = P["xh"], P["rail"]
    if P["join"] == "rail":
        return rect(a["exit_b"][0] - 10, 0, adv + 3, r)
    if P["join"] == "top":
        return rect(a["exit_t"] - 10, xh - r + 12, adv + 3, xh + 12)
    if P["join"] == "powder-rail":
        x0 = a["exit_b"][0] - 10
        return powder([(x0, r / 2), (x0 + 1, r / 2), (adv - 1, r / 2), (adv + 4, r / 2)], lambda t: r)
    w, (t0, t1) = join_width("exit")
    if t1 == 1.0:
        t1 = 1.03                    # overlap the glyph edge so joins have no seam
    if kind == "high":
        jh = xh - JH_DROP
        sx, sy = a["exit_h"]
        sx -= w(0) * 0.3
        p = [(sx, sy), (sx + K * 0.8, sy - 12), (adv - K * 0.9, jh - K * 0.22), (adv, jh)]
        return powder(p, w, t0, t1) if P["join"] == "powder" else stroke(p, w, t0, t1)
    sx, sy = a["exit_b"]
    y0 = max(sy, w(0) / 2)
    sx -= w(0) * 0.3                 # tuck the thick end inside the stem
    p = [(sx, y0), (sx + K * 0.8, y0 + K * 0.45), (adv - K * DIR[0], JY - K * DIR[1]), (adv, JY)]
    return powder(p, w, t0, t1) if P["join"] == "powder" else stroke(p, w, t0, t1)


def entry_join(a, kind="low"):
    xh, r = P["xh"], P["rail"]
    if P["join"] == "rail":
        return rect(-3, 0, a["entry_b"] + 10, r)
    if P["join"] == "top":
        return rect(-3, xh - r + 12, a["entry_t"][0] + 10, xh + 12)
    if P["join"] == "powder-rail":
        x1 = a["entry_b"] + 10
        return powder([(-4, r / 2), (1, r / 2), (x1 - 1, r / 2), (x1, r / 2)], lambda t: r)
    w, (t0, t1) = join_width("entry")
    ex, ey = a["entry_t"]
    ey = min(ey, xh - w(1) / 2)
    ex += w(1) * 0.3
    if t0 == 0.0:
        t0 = -0.03
    if kind == "high":
        jh = xh - JH_DROP
        p = [(0, jh), (K * 0.9, jh + K * 0.22), (ex - K * 0.8, ey), (ex, ey)]
        return powder(p, w, t0, t1) if P["join"] == "powder" else stroke(p, w, t0, t1)
    p = [(0, JY), (K * DIR[0], JY + K * DIR[1]), (ex - K * 0.8, ey - K * 0.25), (ex, ey)]
    return powder(p, w, t0, t1) if P["join"] == "powder" else stroke(p, w, t0, t1)


# ---------- glyphs ----------
# Builders take (no_head, no_foot): drop the head serif on the left stem, drop
# the foot serif on the right stem. They return (shapes, holes, advance, anchors).

def arch(x_from, x_to):
    xh, st, thin = P["xh"], P["st"], P["thin"]
    p = [(x_from - 15, xh - 120), (x_from + 10, xh + 35), (x_to + st / 2, xh + 35), (x_to + st / 2, xh - 170)]
    return stroke(p, lambda t: thin + (st - thin) * smooth(0.45, 0.95, t))


def stem_anchors(s, r):
    st, sf, xh = P["st"], P["sf"], P["xh"]
    return dict(exit_b=(r + st - 4, sf / 2), exit_t=r + st / 2,
                entry_t=(s + 4, xh - sf / 2), entry_b=s + st / 2)


def g_i(no_head, no_foot):
    s, st, sf, so, xh = P["sb"], P["st"], P["sf"], P["so"], P["xh"]
    shapes = [rect(s, 0, s + st, xh), ellipse(s + st / 2, xh + 170, 52, 52), rect(s - so, 0, s, sf)]
    if not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    if not no_foot:
        shapes.append(rect(s + st, 0, s + st + so, sf))
    return shapes, [], s + st + P["sb"], stem_anchors(s, s)


def g_n(no_head, no_foot, tall=False):
    s, st, sf, so, xh = P["sb"], P["st"], P["sf"], P["so"], P["xh"]
    r = s + st + P["cn"]
    shapes = [rect(s, 0, s + st, ASC if tall else xh), arch(s + st, r), rect(r, 0, r + st, xh - 160),
              rect(s - so, 0, s + st + so, sf), rect(r - so, 0, r, sf)]
    if tall:
        shapes.append(rect(s - so, ASC - sf, s, ASC))
    elif not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    if not no_foot:
        shapes.append(rect(r + st, 0, r + st + so, sf))
    return shapes, [], r + st + P["sb"], stem_anchors(s, r)


def g_h(no_head, no_foot):
    return g_n(no_head, no_foot, tall=True)


def g_m(no_head, no_foot):
    s, st, sf, so, xh = P["sb"], P["st"], P["sf"], P["so"], P["xh"]
    m = s + st + P["cm"]
    r = m + st + P["cm"]
    shapes = [rect(s, 0, s + st, xh), arch(s + st, m), rect(m, 0, m + st, xh - 160),
              arch(m + st, r), rect(r, 0, r + st, xh - 160),
              rect(s - so, 0, s + st + so, sf), rect(m - so, 0, m + st + so, sf), rect(r - so, 0, r, sf)]
    if not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    if not no_foot:
        shapes.append(rect(r + st, 0, r + st + so, sf))
    return shapes, [], r + st + P["sb"], stem_anchors(s, r)


def g_u(no_head, no_foot):
    s, st, sf, so, xh, thin = P["sb"], P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    r = s + st + P["cn"]
    bowl = stroke([(s + st / 2, 170), (s + st / 2, -30), (r - 10, -35), (r + 10, 120)],
                  lambda t: st - (st - thin) * smooth(0.05, 0.55, t))
    shapes = [rect(s, 160, s + st, xh), bowl, rect(r, 0, r + st, xh), rect(r - so, xh - sf, r, xh)]
    if not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    if not no_foot:
        shapes.append(rect(r + st, 0, r + st + so, sf))
    return shapes, [], r + st + P["sb"], stem_anchors(s, r)


def g_o(no_head, no_foot):
    rx, xh = P["orx"], P["xh"]
    ry, cy = xh / 2 + 10, xh / 2
    cx = 60 + rx
    shapes = [ellipse(cx, cy, rx, ry)]
    holes = [ellipse(cx, cy, rx - (P["st"] - 3), ry - P["sf"])]
    a = dict(exit_b=(cx + 0.5 * rx, 40), exit_t=cx, entry_t=(cx - 0.5 * rx, xh - 50), entry_b=cx,
             exit_h=(cx + 0.45 * rx, xh - 40))
    return shapes, holes, cx + rx + 60, a


def arc_stroke(cx, cy, rx, ry, a0, a1, w, n=40):
    """Stroke along an elliptical arc, angles in degrees (a1 < a0 runs clockwise).
    w(t, ang) gives full width at t in [0, 1], ang in degrees."""
    left, right = [], []
    k = math.radians(a1 - a0)
    for i in range(n + 1):
        t = i / n
        ang = a0 + (a1 - a0) * t
        a = math.radians(ang)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        dx, dy = -rx * math.sin(a) * k, ry * math.cos(a) * k
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        h = w(t, ang) / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    return ("stroke", left, right)


def line_stroke(x0, y0, x1, y1, w0, w1=None):
    w1 = w0 if w1 is None else w1
    p = [(x0, y0), (x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3),
         (x0 + 2 * (x1 - x0) / 3, y0 + 2 * (y1 - y0) / 3), (x1, y1)]
    return stroke(p, lambda t: w0 + (w1 - w0) * t, n=4)


def dotline(p, w, n=24):
    """A small stroke that dot styles draw as one hand-poked line along its centre.
    Solid styles draw it as an ordinary stroke."""
    centre = [(cubic(p, i / n), w(i / n)) for i in range(n + 1)]
    return ("dotline", stroke(p, w, n=n), centre)


def dotline_line(x0, y0, x1, y1, w0, w1=None):
    w1 = w0 if w1 is None else w1
    p = [(x0, y0), (x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3),
         (x0 + 2 * (x1 - x0) / 3, y0 + 2 * (y1 - y0) / 3), (x1, y1)]
    return dotline(p, lambda t: w0 + (w1 - w0) * t, n=8)


def dotline_dots(part):
    """Dots along a dotline: one row where it is thin, two or three where it swells."""
    r0, gap, jit = P["dot"], P["gap"], P["jitter"]
    centre = part[2]
    dots, carry, wob = [], 0.0, 0.0
    for ((x0, y0), w0), ((x1, y1), w1) in zip(centre, centre[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg == 0:
            continue
        ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
        d = carry
        while d < seg:
            f = d / seg
            x, y, w = x0 + ux * d, y0 + uy * d, w0 + (w1 - w0) * f
            wob = wob * 0.8 + RNG.gauss(0, r0 * 0.12)
            n = max(1, round(w / (gap * 1.3)))
            for i in range(n):
                off = (i - (n - 1) / 2) * gap * 0.9 + wob
                r = r0 * RNG.uniform(1 - jit * 0.7, 1 + jit * 0.3)
                dots.append((x - uy * off + RNG.gauss(0, jit * r0 * 0.15),
                             y + ux * off + RNG.gauss(0, jit * r0 * 0.15), r))
            d += gap * 1.05 * RNG.uniform(0.9, 1.12)
        carry = d - seg
    return dots


def stress(st, thin):
    """Vertical stress: thick at the sides of a bowl, thin at top and bottom."""
    return lambda t, ang: thin + (st - thin) * abs(math.cos(math.radians(ang))) ** 1.6


def g_r(no_head, no_foot):
    s, st, sf, so, xh, thin = P["sb"], P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    arm = stroke([(s + st - 10, xh - 110), (s + st + 15, xh + 10), (s + st + 80, xh + 12), (s + st + 125, xh - 25)],
                 lambda t: thin + 4)
    shapes = [rect(s, 0, s + st, xh), arm, ellipse(s + st + 118, xh - 52, 36, 40),
              rect(s - so, 0, s + st, sf)]
    if not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    if not no_foot:
        shapes.append(rect(s + st, 0, s + st + so + 10, sf))
    a = stem_anchors(s, s)
    a["exit_h"] = (s + st + 112, xh - 48)
    return shapes, [], s + st + P["sb"] + 20, a


def g_e(no_head, no_foot):
    st, xh, thin, sf = P["st"], P["xh"], P["thin"], P["sf"]
    rx = P["orx"] - 45
    ry, cy = xh / 2 - 2, xh / 2 + 4
    cx = 60 + rx + st / 2
    base = stress(st, max(thin - 2, sf))
    w = lambda t, ang: base(t, ang) * (1 - 0.45 * smooth(0.8, 1.0, t))   # taper the tail
    bowl = arc_stroke(cx, cy, rx, ry, 4, 322, w)
    bar = rect(cx - rx, xh * 0.5, cx + rx + st / 2 - 6, xh * 0.5 + sf + 6)
    a = dict(exit_b=(cx + rx * 0.6, 45), exit_t=cx, entry_t=(cx - rx * 0.55, xh - 55), entry_b=cx)
    return [bowl, bar], [], cx + rx + st / 2 + 60, a


def g_a(no_head, no_foot):
    s, st, sf, so, xh, thin = 70, P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    R = s + 150 + P["cn"] // 2
    bcx, brx, bry, bcy = R - 78, 104, 118, 128
    hook = stroke([(R + st / 2, xh - 160), (R + st / 2, xh + 25), (s + 70, xh + 25), (s + 45, xh - 70)],
                  lambda t: st - (st - thin) * smooth(0.0, 0.5, t))
    bowl = arc_stroke(bcx, bcy, brx, bry, 75, 300, stress(st * 0.95, thin))
    top_join = line_stroke(bcx + brx * 0.2, bcy + bry * 0.97, R + 20, bcy + bry + 20, thin)
    low_join = line_stroke(bcx + brx * 0.45, bcy - bry * 0.86, R + 10, 45, thin)
    shapes = [rect(R, 0, R + st, xh - 150), hook, ellipse(s + 55, xh - 85, 40, 44), bowl, top_join, low_join]
    if not no_foot:
        shapes.append(rect(R + st, 0, R + st + so, sf))
    a = dict(exit_b=(R + st - 4, sf / 2), exit_t=R + st / 2, entry_t=(s + 40, xh - 70), entry_b=bcx)
    return shapes, [], R + st + P["sb"], a


def s_shape(H, rx, st, thin, sf, x0=60):
    cx = x0 + rx + st / 2
    ry = H * 0.25
    up_cy, lo_cy = H - ry - 8, ry + 8
    spine, mid = st * 0.95, st * 0.45
    upper = arc_stroke(cx, up_cy, rx, ry, 25, 205, lambda t, ang: thin + (mid - thin) * smooth(0.4, 1.0, t))
    p0 = (cx + rx * math.cos(math.radians(205)), up_cy + ry * math.sin(math.radians(205)))
    p3 = (cx + rx * math.cos(math.radians(25)), lo_cy + ry * math.sin(math.radians(25)))
    sp = stroke([p0, (p0[0] + rx * 0.25, p0[1] - ry * 0.75), (p3[0] - rx * 0.25, p3[1] + ry * 0.75), p3],
                lambda t: mid + (spine - mid) * math.sin(math.pi * t))
    lower = arc_stroke(cx, lo_cy, rx, ry, 25, -155, lambda t, ang: mid - (mid - thin) * smooth(0.0, 0.6, t))
    bh = H * 0.14
    beak_t = rect(cx + rx * 0.84, H - 40 - bh, cx + rx * 0.84 + sf + 4, H - 40)
    beak_b = rect(cx - rx * 0.92 - sf - 4, 40, cx - rx * 0.92, 40 + bh)
    a = dict(exit_b=(cx + rx * 0.45, 30), exit_t=cx, entry_t=(cx - rx * 0.6, H - 50), entry_b=cx)
    return [upper, sp, lower, beak_t, beak_b], [], cx + rx + st / 2 + 60, a


def g_s(no_head, no_foot):
    return s_shape(P["xh"], P["orx"] - 85, P["st"], P["thin"], P["sf"])


def v_shape(s, halves, no_head, no_foot, H=None, st=None, span=None, sf=None):
    """A run of diagonals: thick down, thin up, repeated `halves` times (v=1, w=2)."""
    H = H or P["xh"]
    st = st or P["st"]
    sf = sf or P["sf"]
    so, thin = P["so"], P["thin"]
    span = span or 125 + P["cn"] * 0.15
    shapes, x = [], s + st / 2
    apexes = []
    for i in range(halves):
        ax = x + span
        shapes.append(line_stroke(x, H, ax, 8, st * 1.05, st * 0.8))
        top = ax + span * 0.95
        shapes.append(line_stroke(ax, 8, top, H, thin + 6))
        apexes.append(ax)
        x = top
    shapes.append(rect(s - so, H - sf, s + st / 2, H) if no_head else rect(s - so, H - sf, s + st + so, H))
    shapes.append(rect(s + st / 2, H - sf, s + st + so, H))
    shapes.append(rect(x - so - 10, H - sf, x + so, H))
    for ax in apexes:
        shapes.append(rect(ax - 26, 0, ax + 26, 22))
    a = dict(exit_b=(apexes[-1] + 10, 12), exit_t=x, entry_t=(s + 4, H - sf / 2), entry_b=apexes[0],
             exit_h=(x - 10, H - 30))
    return shapes, [], x + so + 50, a


def g_v(no_head, no_foot):
    return v_shape(P["sb"], 1, no_head, no_foot)


def g_w(no_head, no_foot):
    return v_shape(P["sb"], 2, no_head, no_foot)


DESC = -220


def g_l(no_head, no_foot):
    s, st, sf, so = P["sb"], P["st"], P["sf"], P["so"]
    shapes = [rect(s, 0, s + st, ASC), rect(s - so, ASC - sf, s, ASC), rect(s - so, 0, s, sf)]
    if not no_foot:
        shapes.append(rect(s + st, 0, s + st + so, sf))
    return shapes, [], s + st + P["sb"], stem_anchors(s, s)


def g_t(no_head, no_foot):
    st, sf, xh, thin = P["st"], P["sf"], P["xh"], P["thin"]
    s = P["sb"] + 30
    hook = stroke([(s + st / 2, 140), (s + st / 2, -12), (s + st + 50, -12), (s + st + 95, 55)],
                  lambda t: st - (st - thin) * smooth(0.1, 0.8, t))
    shapes = [rect(s, 120, s + st, xh + 120), hook, rect(s - 70, xh - sf - 6, s + st + 85, xh)]
    a = dict(exit_b=(s + st + 70, 30), exit_t=s + st + 60, entry_t=(s - 60, xh - 12), entry_b=s + st / 2)
    return shapes, [], s + st + 95 + P["sb"] - 50, a


def g_f(no_head, no_foot):
    s, st, sf, so, xh, thin = P["sb"], P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    hook = stroke([(s + st / 2, ASC - 130), (s + st / 2, ASC + 10), (s + st + 90, ASC + 10), (s + st + 135, ASC - 40)],
                  lambda t: st - (st - thin) * smooth(0.0, 0.6, t))
    shapes = [rect(s, 0, s + st, ASC - 120), hook, ellipse(s + st + 125, ASC - 62, 36, 40),
              rect(s - 70, xh - sf - 6, s + st + 80, xh), rect(s - so, 0, s, sf)]
    if not no_foot:
        shapes.append(rect(s + st, 0, s + st + so, sf))
    a = dict(exit_b=(s + st - 4, sf / 2), exit_t=s + st + 60, entry_t=(s - 60, xh - 12), entry_b=s + st / 2)
    return shapes, [], s + st + P["sb"] + 10, a


def bowl_rx():
    return P["orx"] - 55


def bowl_parts(side, stem_x):
    """A bowl beside a stem: side "left" (d, q, g) or "right" (b, p).
    stem_x is the stem edge the bowl attaches to."""
    st, xh, thin = P["st"], P["xh"], P["thin"]
    rx, ry, cy = bowl_rx(), P["xh"] / 2 - 6, P["xh"] / 2
    sgn = -1 if side == "left" else 1
    bcx = stem_x + sgn * (rx * 0.34 + 30)
    if side == "left":
        arc = arc_stroke(bcx, cy, rx, ry, 70, 290, stress(st, thin))
    else:
        arc = arc_stroke(bcx, cy, rx, ry, 110, -110, stress(st, thin))
    ex = bcx - sgn * rx * 0.34
    tj = line_stroke(ex, cy + ry * 0.94, stem_x - sgn * 15, xh - 50, thin)
    bj = line_stroke(ex, cy - ry * 0.94, stem_x - sgn * 15, 50, thin)
    return [arc, tj, bj], bcx, rx


def left_bowl_stem_x():
    return 60 + bowl_rx() * 1.34 + 30 + P["st"] / 2


def g_d(no_head, no_foot, desc=False):
    st, sf, so, xh = P["st"], P["sf"], P["so"], P["xh"]
    R = left_bowl_stem_x()
    parts, bcx, rx = bowl_parts("left", R)
    if desc:
        shapes = parts + [rect(R, DESC, R + st, xh), rect(R - so, DESC, R + st + so, DESC + sf)]
    else:
        shapes = parts + [rect(R, 0, R + st, ASC), rect(R - so, ASC - sf, R, ASC)]
        if not no_foot:
            shapes.append(rect(R + st, 0, R + st + so, sf))
    a = dict(exit_b=(R + st - 4, sf / 2), exit_t=R + st / 2, entry_t=(bcx - rx * 0.55, xh - 55), entry_b=bcx)
    return shapes, [], R + st + P["sb"], a


def g_q(no_head, no_foot):
    return g_d(no_head, no_foot, desc=True)


def g_b(no_head, no_foot, desc=False):
    s, st, sf, so, xh = P["sb"], P["st"], P["sf"], P["so"], P["xh"]
    parts, bcx, rx = bowl_parts("right", s + st)
    if desc:
        shapes = parts + [rect(s, DESC, s + st, xh), rect(s - so, DESC, s + st + so, DESC + sf)]
        if not no_head:
            shapes.append(rect(s - so, xh - sf, s, xh))
    else:
        shapes = parts + [rect(s, 0, s + st, ASC), rect(s - so, ASC - sf, s, ASC), rect(s - so, 0, s, sf)]
    a = dict(exit_b=(bcx + rx * 0.6, 45), exit_t=bcx, entry_t=(s + 4, xh - sf / 2), entry_b=s + st / 2,
             exit_h=(bcx + rx * 0.55, xh - 45))
    return shapes, [], bcx + rx + st / 2 + 60, a


def g_p(no_head, no_foot):
    return g_b(no_head, no_foot, desc=True)


def g_c(no_head, no_foot):
    st, xh, thin, sf = P["st"], P["xh"], P["thin"], P["sf"]
    rx = P["orx"] - 45
    ry, cy = xh / 2 - 2, xh / 2 + 4
    cx = 60 + rx + st / 2
    base = stress(st, max(thin - 2, sf))
    bowl = arc_stroke(cx, cy, rx, ry, 42, 322, lambda t, ang: base(t, ang) * (1 - 0.45 * smooth(0.8, 1.0, t)))
    ang = math.radians(42)
    ball = ellipse(cx + rx * math.cos(ang) - 8, cy + ry * math.sin(ang) - 22, 38, 42)
    a = dict(exit_b=(cx + rx * 0.6, 45), exit_t=cx, entry_t=(cx - rx * 0.55, xh - 55), entry_b=cx)
    return [bowl, ball], [], cx + rx + st / 2 + 50, a


def g_g(no_head, no_foot):
    st, sf, xh, thin = P["st"], P["sf"], P["xh"], P["thin"]
    R = left_bowl_stem_x()
    parts, bcx, rx = bowl_parts("left", R)
    hook = stroke([(R + st / 2, -40), (R + st / 2, DESC - 15), (bcx - 30, DESC - 15), (bcx - 80, DESC + 50)],
                  lambda t: st - (st - thin) * smooth(0.1, 0.7, t))
    shapes = parts + [rect(R, -60, R + st, xh), rect(R + st, xh - sf, R + st + 45, xh), hook,
                      ellipse(bcx - 75, DESC + 62, 38, 40)]
    a = dict(exit_b=(R + st - 4, 12), exit_t=R + st / 2, entry_t=(bcx - rx * 0.55, xh - 55), entry_b=bcx)
    return shapes, [], R + st + P["sb"], a


def g_j(no_head, no_foot):
    st, sf, so, xh, thin = P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    s = P["sb"] + 40
    hook = stroke([(s + st / 2, -20), (s + st / 2, DESC - 15), (s - 70, DESC - 15), (s - 110, DESC + 45)],
                  lambda t: st - (st - thin) * smooth(0.1, 0.7, t))
    shapes = [rect(s, -40, s + st, xh), ellipse(s + st / 2, xh + 170, 52, 52), hook,
              ellipse(s - 105, DESC + 57, 36, 40)]
    if not no_head:
        shapes.append(rect(s - so, xh - sf, s, xh))
    a = stem_anchors(s, s)
    a["exit_b"] = (s + st - 4, 12)
    return shapes, [], s + st + P["sb"], a


def g_k(no_head, no_foot):
    s, st, sf, so, xh, thin = P["sb"], P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    shapes = [rect(s, 0, s + st, ASC), rect(s - so, ASC - sf, s, ASC), rect(s - so, 0, s + st + so, sf),
              line_stroke(s + st - 10, 150, s + st + 175, xh - sf / 2, thin + 4),
              rect(s + st + 140, xh - sf, s + st + 215, xh),
              line_stroke(s + st + 45, 245, s + st + 185, 8, st * 0.85, st * 0.75),
              rect(s + st + 140, 0, s + st + 205, sf)]
    if not no_foot:
        shapes.append(rect(s + st + 205, 0, s + st + 240, sf))
    a = stem_anchors(s, s)
    a.update(exit_b=(s + st + 215, sf / 2), exit_t=s + st + 180)
    return shapes, [], s + st + 240 + P["sb"] - 40, a


def x_shape(s, H, span, st, thin, sf, so, no_head, no_foot):
    xl, xr = s + st / 2, s + st / 2 + span
    shapes = [line_stroke(xl, H - 8, xr, 8, st * 0.95), line_stroke(xr, H - 8, xl, 8, thin + 6),
              rect(xl - 55 if not no_head else xl, H - sf, xl + 45, H), rect(xr - 50, H - sf, xr + 45, H),
              rect(xl - 55, 0, xl + 45, sf), rect(xr - 45, 0, xr + (45 if not no_foot else 0), sf)]
    a = dict(exit_b=(xr + 20, sf / 2), exit_t=xr, entry_t=(s + 4, H - sf / 2), entry_b=xl)
    return shapes, [], xr + 45 + P["sb"] - 40, a


def g_x(no_head, no_foot):
    return x_shape(P["sb"], P["xh"], 260, P["st"], P["thin"], P["sf"], P["so"], no_head, no_foot)


def g_y(no_head, no_foot):
    s, st, sf, so, xh, thin = P["sb"], P["st"], P["sf"], P["so"], P["xh"], P["thin"]
    span = 125 + P["cn"] * 0.15
    xl = s + st / 2
    ax = xl + span
    xr = ax + span * 0.95
    end = (ax - 60, DESC + 40)
    x_meet = xr + (end[0] - xr) * ((xh - 8) / (xh - end[1]))
    shapes = [line_stroke(xr, xh, end[0], end[1], thin + 6), line_stroke(xl, xh, x_meet + 5, 8, st * 1.05, st * 0.8),
              ellipse(end[0] - 22, end[1] - 5, 36, 40),
              rect(s - so, xh - sf, s + st / 2, xh) if no_head else rect(s - so, xh - sf, s + st + so, xh),
              rect(s + st / 2, xh - sf, s + st + so, xh), rect(xr - so - 10, xh - sf, xr + so, xh)]
    a = dict(exit_b=(x_meet + 15, 12), exit_t=xr, entry_t=(s + 4, xh - sf / 2), entry_b=x_meet)
    return shapes, [], xr + so + 50, a


def z_shape(s, H, w, st, sf, no_head, no_foot):
    shapes = [rect(s, H - sf - 8, s + w, H), rect(s + 10, 0, s + w + 10, sf + 10),
              line_stroke(s + w - 25, H - sf - 4, s + 35, sf + 6, st * 0.9),
              rect(s + w + 10 - sf - 4, 0, s + w + 10, H * 0.23)]
    if not no_head:
        shapes.append(rect(s, H - H * 0.23, s + sf + 4, H))
    a = dict(exit_b=(s + w + 6, 10), exit_t=s + w, entry_t=(s + 4, H - 12), entry_b=s + 40)
    return shapes, [], s + w + 10 + P["sb"] - 20, a


def g_z(no_head, no_foot):
    return z_shape(P["sb"] - 20, P["xh"], 250, P["st"], P["sf"], no_head, no_foot)


# ---------- capitals ----------
# Capitals never take an entry join; they join only to the letter on their right.

def cap_t():
    return max(20, P["sf"])


def cap_thin():
    return P["thin"] + 4


def cap_stem(L, no_foot, top=True, foot_left=True):
    """A capital stem with serifs; the right foot serif drops when a join leaves there."""
    stc, so, t = P["stc"], P["so"], cap_t()
    shapes = [rect(L, 0, L + stc, CAP)]
    if top:
        shapes.append(rect(L - so, CAP - t, L + stc + so, CAP))
    if foot_left:
        shapes.append(rect(L - so, 0, L + stc, t))
    if not no_foot:
        shapes.append(rect(L + stc, 0, L + stc + so, t))
    return shapes


def ca(exit_x, exit_t, y=None):
    return dict(exit_b=(exit_x, y if y is not None else cap_t() / 2), exit_t=exit_t)


def g_A(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L, ax = 60, 320
    shapes = [line_stroke(L + 20, 0, ax - 10, CAP + 5, cap_thin()),
              line_stroke(ax - 20, CAP + 5, ax + 240, 0, stc * 1.05, stc),
              rect(L + 95, 210, ax + 165, 210 + t + 2),
              rect(L - 40, 0, L + 85, t), rect(ax + 180, 0, ax + 260, t)]
    if not no_foot:
        shapes.append(rect(ax + 260, 0, ax + 300, t))
    return shapes, [], ax + 300 + P["sb"] - 40, ca(ax + 280, ax)


def g_B(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    ucx, ucy, urx = L + stc + 95, 530, 120
    ury = CAP - t / 2 - ucy
    lcx, lcy, lrx = L + stc + 110, 185, 145
    lry = lcy - t / 2
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L, CAP), rect(L - so, 0, L, t),
              arc_stroke(ucx, ucy, urx, ury, 90, -90, stress(stc * 0.95, t)),
              arc_stroke(lcx, lcy, lrx, lry, 90, -90, stress(stc, t)),
              rect(L + stc - 5, CAP - t, ucx, CAP), rect(L + stc - 5, 0, lcx, t),
              rect(L + stc - 5, ucy - ury - t / 2, max(ucx, lcx), lcy + lry + t / 2)]
    return shapes, [], lcx + lrx + stc / 2 + 60, ca(lcx + lrx * 0.55, ucx, 45)


def c_bowl(a1=312):
    stc, t = P["stc"], cap_t()
    crx, cry, cy = P["Orx"] - 55, 345, 350
    cx = 60 + crx + stc / 2
    arc = arc_stroke(cx, cy, crx, cry, 48, a1, stress(stc * 1.05, t))
    xe = cx + crx * math.cos(math.radians(48))
    beak = rect(xe - 4, 520, xe + t, 690)
    return [arc, beak], cx, crx


def g_C(no_head, no_foot):
    shapes, cx, crx = c_bowl()
    t = cap_t()
    xe = cx + crx * math.cos(math.radians(312))
    shapes.append(rect(xe - 4, 12, xe + t, 180))
    return shapes, [], cx + crx + P["stc"] / 2 + 50, ca(cx + crx * 0.6, cx, 45)


def g_G(no_head, no_foot):
    shapes, cx, crx = c_bowl(335)
    stc, t = P["stc"], cap_t()
    x1 = cx + crx + stc * 0.45
    shapes += [rect(x1 - stc, 30, x1, 300), rect(cx + crx - 150, 300 - t, x1 + 20, 300)]
    return shapes, [], x1 + 60, ca(x1 - 10, cx, 40)


def g_D(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    dcx, drx, cy = L + stc + 40, 260, 350
    dry = CAP - t / 2 - cy
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L, CAP), rect(L - so, 0, L, t),
              arc_stroke(dcx, cy, drx, dry, 90, -90, stress(stc * 1.05, t)),
              rect(L + stc - 5, CAP - t, dcx, CAP), rect(L + stc - 5, 0, dcx, t)]
    return shapes, [], dcx + drx + stc / 2 + 60, ca(dcx + drx * 0.55, dcx, 45)


def g_E(no_head, no_foot, F=False):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L, CAP),
              rect(L, CAP - t - 2, L + 330, CAP), rect(L + 330 - t - 4, CAP - 130, L + 330, CAP),
              rect(L, 335, L + 270, 335 + t + 4), rect(L + 270 - t - 2, 290, L + 270, 400)]
    if F:
        shapes.append(rect(L - so, 0, L + stc, t))
        if not no_foot:
            shapes.append(rect(L + stc, 0, L + stc + so, t))
        return shapes, [], L + 330 + P["sb"] - 40, ca(L + stc - 4, L + 330)
    shapes += [rect(L - so, 0, L, t), rect(L, 0, L + 350, t + 4), rect(L + 350 - t - 4, 0, L + 350, 140)]
    return shapes, [], L + 350 + P["sb"] - 30, ca(L + 346, L + 330)


def g_F(no_head, no_foot):
    return g_E(no_head, no_foot, F=True)


def g_I(no_head, no_foot):
    L = 80
    return cap_stem(L, no_foot), [], L + P["stc"] + P["sb"], ca(L + P["stc"] - 4, L + P["stc"] / 2)


def g_J(no_head, no_foot):
    stc, so, thin = P["stc"], P["so"], P["thin"]
    x = 150
    hook = stroke([(x + stc / 2, 200), (x + stc / 2, -15), (x - 110, -15), (x - 150, 90)],
                  lambda t: stc - (stc - thin) * smooth(0.2, 0.8, t))
    shapes = [rect(x, 160, x + stc, CAP), rect(x - so, CAP - cap_t(), x + stc + so, CAP), hook,
              ellipse(x - 140, 100, 40, 44)]
    return shapes, [], x + stc + P["sb"], ca(x + stc / 2 + 30, x + stc / 2, 20)


def g_K(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L + stc + so, CAP), rect(L - so, 0, L + stc + so, t),
              line_stroke(L + stc - 5, 250, L + stc + 260, CAP - t / 2, cap_thin()),
              rect(L + stc + 215, CAP - t, L + stc + 320, CAP),
              line_stroke(L + stc + 60, 380, L + stc + 290, 5, stc * 0.95, stc * 0.85),
              rect(L + stc + 230, 0, L + stc + 310, t)]
    if not no_foot:
        shapes.append(rect(L + stc + 310, 0, L + stc + 350, t))
    return shapes, [], L + stc + 350 + P["sb"] - 40, ca(L + stc + 330, L + stc + 270)


def g_L(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L + stc + so, CAP), rect(L - so, 0, L, t),
              rect(L, 0, L + 330, t + 4), rect(L + 330 - t - 4, 0, L + 330, 150)]
    return shapes, [], L + 330 + P["sb"] - 30, ca(L + 326, L + stc / 2)


def g_M(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L, w = 70, 560
    th = cap_thin() + 6
    shapes = [rect(L, 0, L + th, CAP), line_stroke(L + 25, CAP - 5, L + w / 2, 5, stc),
              line_stroke(L + w / 2, 5, L + w - stc + 10, CAP - 5, cap_thin()), rect(L + w - stc, 0, L + w, CAP),
              rect(L - so, CAP - t, L + 60, CAP), rect(L - so, 0, L + th + so, t),
              rect(L + w - stc - 20, CAP - t, L + w + so, CAP), rect(L + w - stc - so, 0, L + w, t)]
    if not no_foot:
        shapes.append(rect(L + w, 0, L + w + so, t))
    return shapes, [], L + w + P["sb"], ca(L + w - 4, L + w - stc / 2)


def g_N(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L, w = 70, 440
    th = cap_thin() + 6
    shapes = [rect(L, 0, L + th, CAP), line_stroke(L + 25, CAP - 5, L + w - 35, 5, stc),
              rect(L + w - th, 0, L + w, CAP),
              rect(L - so, CAP - t, L + 70, CAP), rect(L - so, 0, L + th + so, t),
              rect(L + w - th - so, CAP - t, L + w + so, CAP)]
    return shapes, [], L + w + P["sb"], ca(L + w - 4, L + w - th / 2, 10)


def g_P(no_head, no_foot, leg=False):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 70
    ucx, ucy, urx = L + stc + 110, 495, 140
    ury = CAP - t / 2 - ucy
    shapes = [rect(L, 0, L + stc, CAP), rect(L - so, CAP - t, L, CAP),
              arc_stroke(ucx, ucy, urx, ury, 90, -90, stress(stc * 1.05, t)),
              rect(L + stc - 5, CAP - t, ucx, CAP), rect(L + stc - 5, ucy - ury - t / 2, ucx, ucy - ury + t / 2)]
    adv = ucx + urx + stc / 2 + 50
    if not leg:
        shapes.append(rect(L - so, 0, L + stc, t))
        if not no_foot:
            shapes.append(rect(L + stc, 0, L + stc + so, t))
        return shapes, [], adv, ca(L + stc - 4, ucx)
    shapes += [rect(L - so, 0, L + stc + so, t),
               line_stroke(L + stc + 120, ucy - ury, L + stc + 275, 5, stc * 0.95, stc * 0.85),
               rect(L + stc + 215, 0, L + stc + 295, t)]
    if not no_foot:
        shapes.append(rect(L + stc + 295, 0, L + stc + 335, t))
    return shapes, [], max(adv, L + stc + 335 + P["sb"] - 40), ca(L + stc + 315, ucx)


def g_R(no_head, no_foot):
    return g_P(no_head, no_foot, leg=True)


def g_Q(no_head, no_foot):
    shapes, holes, adv, a = g_O(no_head, no_foot)
    stc, thin = P["stc"], P["thin"]
    cx = 60 + P["Orx"]
    shapes = list(shapes) + [stroke([(cx - 30, 30), (cx + 40, -70), (cx + 200, -90), (cx + 300, -30)],
                                    lambda t: stc - (stc - thin) * smooth(0.1, 0.9, t))]
    return shapes, holes, adv, a


def g_S(no_head, no_foot):
    shapes, holes, adv, a = s_shape(CAP, 185, P["stc"], P["thin"], cap_t())
    return shapes, holes, adv, a


def g_T(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L, w = 50, 500
    sx = L + w / 2 - stc / 2
    shapes = [rect(L, CAP - t - 4, L + w, CAP), rect(L, CAP - 130, L + t + 4, CAP),
              rect(L + w - t - 4, CAP - 130, L + w, CAP), rect(sx, 0, sx + stc, CAP), rect(sx - so, 0, sx + stc, t)]
    if not no_foot:
        shapes.append(rect(sx + stc, 0, sx + stc + so, t))
    return shapes, [], L + w + P["sb"] - 40, ca(sx + stc - 4, L + w)


def g_U(no_head, no_foot):
    stc, t, so, thin = P["stc"], cap_t(), P["so"], P["thin"]
    L, w = 70, 480
    th = cap_thin() + 6
    bowl = stroke([(L + stc / 2, 230), (L + stc / 2, -20), (L + w - th - 60, -20), (L + w - th / 2, 160)],
                  lambda tt: stc - (stc - thin) * smooth(0.1, 0.6, tt))
    shapes = [rect(L, 200, L + stc, CAP), rect(L + w - th, 0, L + w, CAP), bowl,
              rect(L - so, CAP - t, L + stc + so, CAP), rect(L + w - th - so, CAP - t, L + w + so, CAP)]
    return shapes, [], L + w + P["sb"], ca(L + w - 4, L + w - th / 2, 12)


def g_V(no_head, no_foot):
    return v_shape(60, 1, False, no_foot, H=CAP, st=P["stc"], span=250, sf=cap_t())


def g_W(no_head, no_foot):
    return v_shape(50, 2, False, no_foot, H=CAP, st=P["stc"], span=195, sf=cap_t())


def g_X(no_head, no_foot):
    return x_shape(60, CAP, 400, P["stc"], P["thin"] + 4, cap_t(), P["so"], False, no_foot)


def g_Y(no_head, no_foot):
    stc, t, so = P["stc"], cap_t(), P["so"]
    L = 60
    cx = L + 260
    shapes = [line_stroke(L + 40, CAP - 5, cx, 330, stc, stc * 0.9),
              line_stroke(L + 480, CAP - 5, cx + 20, 330, cap_thin()),
              rect(cx - stc / 2, 0, cx + stc / 2, 360),
              rect(L - 20, CAP - t, L + 130, CAP), rect(L + 420, CAP - t, L + 540, CAP),
              rect(cx - stc / 2 - so, 0, cx + stc / 2, t)]
    if not no_foot:
        shapes.append(rect(cx + stc / 2, 0, cx + stc / 2 + so, t))
    return shapes, [], L + 540 + P["sb"] - 40, ca(cx + stc / 2 - 4, L + 480)


def g_Z(no_head, no_foot):
    return z_shape(60, CAP, 420, P["stc"], cap_t(), False, no_foot)


# ---------- figures and punctuation ----------
# These never join. A letter beside them keeps its unjoined end.

FH = 690   # figure height


def fst():
    return P["stc"] * 0.95


def ring(cx, cy, rx, ry):
    """Outer ellipse and its counter, thick at the sides."""
    return [ellipse(cx, cy, rx, ry)], [ellipse(cx, cy, rx - fst(), ry - P["thin"] * 1.1)]


def ball_at(x, y, r=42):
    return ellipse(x, y, r, r * 1.08)


def g_zero(nh, nf):
    sh, ho = ring(260, FH / 2, 200, FH / 2 + 8)
    return sh, ho, 520, {}


def g_one(nh, nf):
    st, t, thin = fst(), cap_t(), P["thin"]
    x = 210
    return [rect(x, 0, x + st, FH), line_stroke(x + 10, FH - 10, x - 115, FH - 150, thin + 4),
            rect(x - 110, 0, x + st + 110, t)], [], 520, {}


def top_hook(cx, cy, r, a1, ball=True):
    st, thin = fst(), P["thin"]
    arc = arc_stroke(cx, cy, r, r, 160, a1, stress(st, thin))
    shapes = [arc]
    if ball:
        a = math.radians(160)
        shapes.append(ball_at(cx + r * math.cos(a) + 12, cy + r * math.sin(a) - 16))
    return shapes


def pt(cx, cy, rx, ry, ang):
    a = math.radians(ang)
    return cx + rx * math.cos(a), cy + ry * math.sin(a)


def g_two(nh, nf):
    st, t, thin = fst(), cap_t(), P["thin"]
    L, cx, cy, r = 60, 260, FH - 185, 165
    ex, ey = pt(cx, cy, r, r, -40)
    shapes = top_hook(cx, cy, r, -40) + [line_stroke(ex, ey, L + 30, st * 0.4, thin + 10),
                                         rect(L + 10, 0, L + 400, st * 0.8), rect(L + 400 - t - 4, 0, L + 400, 140)]
    return shapes, [], 520, {}


def g_three(nh, nf):
    st, thin = fst(), P["thin"]
    cx = 255
    up = arc_stroke(cx, FH - 160, 145, 150, 150, -90, stress(st, thin))
    lo = arc_stroke(cx + 10, 195, 175, 190, 90, -150, stress(st, thin))
    bx, by = pt(cx, FH - 160, 145, 150, 150)
    lx, ly = pt(cx + 10, 195, 175, 190, -150)
    shapes = [up, lo, ball_at(bx + 10, by - 14), ball_at(lx + 12, ly + 16), rect(cx - 70, 377, cx + 15, 377 + thin + 4)]
    return shapes, [], 520, {}


def g_four(nh, nf):
    st, t, thin = fst(), cap_t(), P["thin"]
    L = 40
    x = L + 280
    return [rect(x, 0, x + st, FH), line_stroke(x + 10, FH, L + 15, 230, thin + 4),
            rect(L, 215, x + st + 60, 215 + thin + 10), rect(x - 70, 0, x + st + 70, t)], [], 540, {}


def g_five(nh, nf):
    st, thin = fst(), P["thin"]
    L = 60
    cx, cy, rx, ry = L + 200, 215, 180, 215
    lx, ly = pt(cx, cy, rx, ry, -150)
    shapes = [rect(L + 50, FH - st * 0.55, L + 380, FH), rect(L + 50, 370, L + 56 + thin, FH),
              arc_stroke(cx, cy, rx, ry, 135, -150, stress(st, thin)), ball_at(lx + 12, ly + 16)]
    return shapes, [], 520, {}


def g_six(nh, nf):
    st, thin = fst(), P["thin"]
    L, cx = 60, 260
    sh, ho = ring(cx, 220, 195, 225)
    up = stroke([(L + st / 2 + 6, 230), (L + st / 2 + 6, FH - 40), (cx, FH + 5), (cx + 150, FH - 60)],
                lambda t: st - (st - thin) * smooth(0.2, 0.75, t))
    return sh + [up, ball_at(cx + 150, FH - 78)], ho, 520, {}


def g_seven(nh, nf):
    st, t, thin = fst(), cap_t(), P["thin"]
    L = 60
    return [rect(L, FH - st * 0.5, L + 400, FH), rect(L, FH - 140, L + t + 4, FH),
            line_stroke(L + 385, FH - 20, L + 150, 0, thin + 10, st)], [], 520, {}


def g_eight(nh, nf):
    cx = 260
    s1, h1 = ring(cx, 525, 160, 165)
    s2, h2 = ring(cx, 190, 190, 195)
    return s1 + s2, h1 + h2, 520, {}


def g_nine(nh, nf):
    st, thin = fst(), P["thin"]
    cx = 260
    sh, ho = ring(cx, FH - 220, 195, 225)
    R = cx + 195 - st / 2 - 6
    dn = stroke([(R, FH - 230), (R, 40), (cx, -5), (cx - 150, 60)],
                lambda t: st - (st - thin) * smooth(0.2, 0.75, t))
    return sh + [dn, ball_at(cx - 150, 78)], ho, 520, {}


DOT = 54


def comma_at(x, y):
    return [ellipse(x, y, DOT, DOT),
            dotline([(x + 40, y), (x + 48, y - 70), (x + 20, y - 140), (x - 20, y - 200)], lambda t: 50 - 38 * t)]


def g_period(nh, nf):
    return [ellipse(110, DOT, DOT, DOT)], [], 230, {}


def g_comma(nh, nf):
    return comma_at(110, DOT), [], 230, {}


def g_colon(nh, nf):
    return [ellipse(110, DOT, DOT, DOT), ellipse(110, P["xh"] - DOT, DOT, DOT)], [], 230, {}


def g_semicolon(nh, nf):
    return comma_at(110, DOT) + [ellipse(110, P["xh"] - DOT, DOT, DOT)], [], 230, {}


def g_exclam(nh, nf):
    st, thin = fst(), P["thin"]
    x = 130
    return [line_stroke(x, FH, x, 210, st, thin + 4), ellipse(x, DOT, DOT, DOT)], [], 260, {}


def g_question(nh, nf):
    st, thin = fst(), P["thin"]
    cx, cy, r = 210, FH - 165, 150
    ex, ey = pt(cx, cy, r, r, -80)
    return top_hook(cx, cy, r, -80) + [line_stroke(ex, ey, ex - 5, 210, thin + 6, st * 0.6),
                                        ellipse(ex - 5, DOT, DOT, DOT)], [], 440, {}


def g_hyphen(nh, nf):
    return [rect(60, 215, 280, 215 + fst() * 0.55)], [], 340, {}


def g_quotesingle(nh, nf):
    return [line_stroke(90, FH, 90, FH - 230, 64, 16)], [], 180, {}


def g_quotedbl(nh, nf):
    return [line_stroke(90, FH, 90, FH - 230, 64, 16), line_stroke(210, FH, 210, FH - 230, 64, 16)], [], 300, {}


def g_quoteright(nh, nf):
    return comma_at(110, FH - DOT), [], 230, {}


def paren(side):
    st, thin = fst(), P["thin"]
    w = lambda t, ang: thin + (st * 0.85 - thin) * abs(math.cos(math.radians(ang))) ** 3
    if side == "left":
        return [arc_stroke(500, 260, 360, 540, 125, 235, w)], [], 300, {}
    return [arc_stroke(-200, 260, 360, 540, 55, -55, w)], [], 300, {}


def g_parenleft(nh, nf):
    return paren("left")


def g_parenright(nh, nf):
    return paren("right")


def g_periodcentered(nh, nf):
    return [ellipse(110, P["xh"] / 2, DOT * 0.85, DOT * 0.85)], [], 230, {}


def g_ampersand(nh, nf):
    st, thin = fst(), P["thin"]
    ux, uy, urx, ury = 215, 545, 105, 128            # upper loop
    lx, ly, lrx, lry = 250, 205, 185, 210            # lower bowl
    upper = arc_stroke(ux, uy, urx, ury, 235, -55, stress(st * 0.75, thin))
    a0 = pt(ux, uy, urx, ury, 235)
    a1 = pt(ux, uy, urx, ury, -55)
    b0 = pt(lx, ly, lrx, lry, 125)
    b1 = pt(lx, ly, lrx, lry, 335)
    shapes = [upper,
              line_stroke(a0[0] + 8, a0[1] + 10, 560, 0, st * 0.55, st * 0.85),          # thick diagonal
              line_stroke(a1[0], a1[1] + 6, b0[0] + 4, b0[1] - 4, thin + 4),       # thin link into the bowl
              arc_stroke(lx, ly, lrx, lry, 125, 335, stress(st, thin)),
              line_stroke(b1[0] - 6, b1[1] - 6, 545, 330, thin + 8, thin + 2),     # arm
              rect(490, 320, 600, 320 + thin + 6)]
    return shapes, [], 660, {}


def g_euro(nh, nf):
    st, thin = fst(), P["thin"]
    cx, cy, rx, ry = 320, FH / 2, 250, FH / 2 + 6
    c = arc_stroke(cx, cy, rx, ry, 48, 312, stress(st, thin))
    shapes = [c, rect(30, cy + 45, 400, cy + 45 + thin + 14), rect(30, cy - 75, 380, cy - 75 + thin + 14)]
    for ang in (48, 312):                            # small serifs at the arc ends
        x, y = pt(cx, cy, rx, ry, ang)
        shapes.append(rect(x - thin, y - 70 if ang > 180 else y - 10, x + 4, y + 10 if ang > 180 else y + 70))
    return shapes, [], 600, {}


def xform(sh, f):
    """Apply point function f to any shape."""
    k = sh[0]
    if k == "multi":
        return ("multi", [xform(x, f) for x in sh[1]])
    if k == "stroke":
        return ("stroke", [f(p) for p in sh[1]], [f(p) for p in sh[2]])
    if k == "dotline":
        return ("dotline", xform(sh[1], f), [(f(p), w) for p, w in sh[2]])
    return (k, [f(p) for p in sh[1]])


def turned(glyph, cy):
    """Rotate a glyph half a turn about its own centre line (for ¡ ¿ and opening quotes)."""
    shapes, holes, adv, a = glyph(False, False)
    f = lambda p: (adv - p[0], 2 * cy - p[1])
    return [xform(x, f) for x in shapes], [xform(x, f) for x in holes], adv, a


def small_ring(cx, cy, rx, ry, w):
    return ellipse(cx, cy, rx, ry), ellipse(cx, cy, rx - w, ry - w * 0.8)


MID = 300      # height of maths signs, centred on the figures


def sym_w(extra):
    """Stroke weight for signs and dashes. Dot styles need more to read."""
    return fst() * 0.8 if P["dots"] else P["thin"] + extra


def g_plus(nh, nf):
    t = sym_w(18)
    return [rect(70, MID - t / 2, 430, MID + t / 2), rect(250 - t / 2, MID - 180, 250 + t / 2, MID + 180)], [], 500, {}


def g_minus(nh, nf):
    t = sym_w(18)
    return [rect(70, MID - t / 2, 430, MID + t / 2)], [], 500, {}


def g_equal(nh, nf):
    t = sym_w(16)
    return [rect(70, MID + 50, 430, MID + 50 + t), rect(70, MID - 50 - t, 430, MID - 50)], [], 500, {}


def g_multiply(nh, nf):
    w = sym_w(14)
    return [line_stroke(110, MID - 140, 390, MID + 140, w), line_stroke(110, MID + 140, 390, MID - 140, w)], [], 500, {}


def g_less(nh, nf):
    w = sym_w(14)
    return [line_stroke(420, MID + 190, 80, MID, w), line_stroke(420, MID - 190, 80, MID, w)], [], 500, {}


def g_greater(nh, nf):
    w = sym_w(14)
    return [line_stroke(80, MID + 190, 420, MID, w), line_stroke(80, MID - 190, 420, MID, w)], [], 500, {}


def g_asterisk(nh, nf):
    cx, cy, r = 220, FH - 150, 135
    arms = []
    for k in range(5):
        a = math.radians(90 + 72 * k)
        arms.append(line_stroke(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), 18 if not P["dots"] else 40, fst() * (1.0 if P["dots"] else 0.7)))
    return arms, [], 440, {}


def g_underscore(nh, nf):
    return [rect(0, -130, 500, -130 + sym_w(16))], [], 500, {}


def g_endash(nh, nf):
    return [rect(40, 215, 460, 215 + sym_w(30))], [], 500, {}


def g_emdash(nh, nf):
    return [rect(40, 215, 960, 215 + sym_w(30))], [], 1000, {}


def g_bar(nh, nf):
    return [rect(110, -160, 110 + sym_w(22), FH + 60)], [], 260, {}


def g_backslash(nh, nf):
    return [line_stroke(330, -120, 50, FH + 40, sym_w(10))], [], 380, {}


def g_bracketleft(nh, nf):
    st, t = fst() * 0.85, sym_w(10)
    return [rect(90, -140, 90 + st, FH + 50), rect(90, -140, 250, -140 + t), rect(90, FH + 50 - t, 250, FH + 50)], [], 300, {}


def g_bracketright(nh, nf):
    st, t = fst() * 0.85, sym_w(10)
    return [rect(210 - st, -140, 210, FH + 50), rect(50, -140, 210, -140 + t), rect(50, FH + 50 - t, 210, FH + 50)], [], 300, {}


def g_ellipsis(nh, nf):
    return [ellipse(110 + 230 * i, DOT, DOT, DOT) for i in range(3)], [], 690, {}


def g_quoteleft(nh, nf):
    return turned(g_quoteright, FH - DOT - 70)


def g_quotedblright(nh, nf):
    return comma_at(110, FH - DOT) + comma_at(250, FH - DOT), [], 370, {}


def g_quotedblleft(nh, nf):
    return turned(g_quotedblright, FH - DOT - 70)


def g_exclamdown(nh, nf):
    return turned(g_exclam, 235)


def g_questiondown(nh, nf):
    return turned(g_question, 235)


def g_degree(nh, nf):
    o, h = small_ring(170, FH - 110, 105, 105, 30)
    return [o], [h], 340, {}


def g_percent(nh, nf):
    o1, h1 = small_ring(170, FH - 160, 115, 150, P["thin"] + 22)
    o2, h2 = small_ring(530, 160, 115, 150, P["thin"] + 22)
    return [o1, o2, line_stroke(150, 0, 560, FH, P["thin"] + 10)], [h1, h2], 700, {}


def g_numbersign(nh, nf):
    w, t = P["thin"] + 18, P["thin"] + 14
    return [line_stroke(200, 40, 260, FH - 40, w), line_stroke(380, 40, 440, FH - 40, w),
            rect(70, 440, 560, 440 + t), rect(50, 230, 540, 230 + t)], [], 620, {}


def g_dollar(nh, nf):
    shapes, holes, adv, _ = g_S(False, False)
    xs = [p[0] for sh in shapes for p in shape_points(sh)]
    cx = (min(xs) + max(xs)) / 2
    w = P["thin"] + 10
    return list(shapes) + [rect(cx - w / 2, -90, cx + w / 2, CAP + 90)], list(holes), adv, {}


def g_sterling(nh, nf):
    st, thin = fst(), P["thin"]
    stem = stroke([(190, 60), (170, 380), (200, FH - 10), (400, FH - 40)],
                  lambda t: st - (st - thin) * smooth(0.3, 0.85, t))
    return [stem, ball_at(410, FH - 70), rect(80, 320, 360, 320 + thin + 12),
            rect(60, 0, 470, st * 0.6), rect(470 - thin - 4, 0, 470, 120),
            line_stroke(70, 70, 200, 50, thin + 10, st * 0.8)], [], 520, {}


def g_at(nh, nf):
    st, thin = fst(), P["thin"]
    cx, cy = 400, 260
    outer = arc_stroke(cx, cy, 340, 360, -25, 315, lambda t, ang: thin + 6 + (st * 0.55) * abs(math.cos(math.radians(ang))) ** 2)
    o, h = small_ring(cx - 20, cy + 20, 130, 150, st * 0.75)
    x0, y0 = pt(cx, cy, 340, 360, -25)
    stem = stroke([(cx + 120, cy + 170), (cx + 100, cy - 60), (cx + 160, cy - 140), (x0, y0)],
                  lambda t: st * 0.7 - (st * 0.7 - thin) * t)
    return [outer, o, stem], [h], 820, {}


def g_asciicircum(nh, nf):
    return mark("circumflex", 220, 420)[0], [], 440, {}


def g_asciitilde(nh, nf):
    return mark("tilde", 250, 250)[0], [], 500, {}


def g_slash(nh, nf):
    return [line_stroke(50, -120, 330, FH + 40, P["thin"] + 10)], [], 380, {}


OTHER = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
         "seven": "7", "eight": "8", "nine": "9", "period": ".", "comma": ",", "colon": ":",
         "semicolon": ";", "exclam": "!", "question": "?", "hyphen": "-", "quotesingle": "'",
         "quotedbl": '"', "quoteright": "\u2019", "parenleft": "(", "parenright": ")", "slash": "/",
         "periodcentered": "\u00b7", "ampersand": "&", "euro": "\u20ac",
         "plus": "+", "minus": "\u2212", "equal": "=", "multiply": "\u00d7", "less": "<", "greater": ">",
         "asterisk": "*", "underscore": "_", "endash": "\u2013", "emdash": "\u2014", "bar": "|",
         "backslash": "\\", "bracketleft": "[", "bracketright": "]", "ellipsis": "\u2026",
         "quoteleft": "\u2018", "quotedblleft": "\u201c", "quotedblright": "\u201d",
         "exclamdown": "\u00a1", "questiondown": "\u00bf", "degree": "\u00b0", "percent": "%",
         "numbersign": "#", "dollar": "$", "sterling": "\u00a3", "at": "@", "asciicircum": "^",
         "asciitilde": "~"}


def g_H(no_head, no_foot):
    s, stc, so = 70, P["stc"], P["so"]
    r = s + stc + 300
    t = max(20, P["sf"])
    shapes = [rect(s, 0, s + stc, CAP), rect(r, 0, r + stc, CAP), rect(s + stc, 340, r, 340 + t + 2),
              rect(s - so, 0, s + stc + so, t), rect(s - so, CAP - t, s + stc + so, CAP),
              rect(r - so, CAP - t, r + stc + so, CAP), rect(r - so, 0, r, t)]
    if not no_foot:
        shapes.append(rect(r + stc, 0, r + stc + so, t))
    return shapes, [], r + stc + P["sb"], dict(exit_b=(r + stc - 4, t / 2), exit_t=r + stc / 2)


def g_O(no_head, no_foot):
    rx, ry, cy = P["Orx"], 360, 345
    cx = 60 + rx
    holes = [ellipse(cx, cy, rx - (P["stc"] + 9), ry - max(22, P["sf"] * 1.2))]
    return [ellipse(cx, cy, rx, ry)], holes, cx + rx + 60, dict(exit_b=(cx + 0.5 * rx, 60), exit_t=cx + 0.4 * rx)


LOWER = {"i": g_i, "n": g_n, "h": g_h, "m": g_m, "u": g_u, "o": g_o,
         "r": g_r, "e": g_e, "a": g_a, "s": g_s, "v": g_v, "w": g_w,
         "b": g_b, "c": g_c, "d": g_d, "f": g_f, "g": g_g, "j": g_j, "k": g_k, "l": g_l,
         "p": g_p, "q": g_q, "t": g_t, "x": g_x, "y": g_y, "z": g_z}
CAPS = {c: globals()["g_" + c] for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}


# ---------- accents ----------
# An accented letter is its base letter plus a mark. It joins exactly like the base.

def shape_points(sh):
    if sh[0] == "multi":
        return [p for part in sh[1] for p in shape_points(part)]
    if sh[0] == "stroke":
        return sh[1] + sh[2]
    if sh[0] == "dotline":
        return shape_points(sh[1])
    return sh[1]


def mark(kind, cx, y0, cap=False):
    """Mark shapes and holes, sitting on y0 and centred on cx."""
    st, thin = P["st"], P["thin"]
    k = 0.75 if cap else 1.0          # capitals get flatter marks
    if kind == "acute":
        return [dotline_line(cx - 45, y0, cx + 55, y0 + 165 * k, thin + 6, st * 0.75)], []
    if kind == "grave":
        return [dotline_line(cx + 45, y0, cx - 55, y0 + 165 * k, thin + 6, st * 0.75)], []
    if kind == "circumflex":
        top = y0 + 140 * k
        return [dotline_line(cx - 115, y0, cx + 8, top, thin + 4, thin + 26),
                dotline_line(cx + 115, y0, cx - 8, top, thin + 4, thin + 26)], []
    if kind == "dieresis":
        r = 46
        return [ellipse(cx - 95, y0 + r + 10, r, r), ellipse(cx + 95, y0 + r + 10, r, r)], []
    if kind == "tilde":
        h = (110 if P["dots"] else 80) * k
        p = [(cx - 125, y0 + h * 0.3), (cx - 60, y0 + h * 1.4), (cx + 40, y0 - h * 0.2), (cx + 125, y0 + h)]
        return [dotline(p, lambda t: thin + 4 + (st * 0.5) * math.sin(math.pi * t))], []
    if kind == "ring":
        cy = y0 + 70 * k
        return [ellipse(cx, cy, 72, 70 * k)], [ellipse(cx, cy, 38, 36 * k)]
    if kind == "cedilla":
        p = [(cx + 5, 10), (cx + 15, -70), (cx + 110, -100), (cx - 70, -200)]
        return [dotline(p, lambda t: 30 + 22 * math.sin(math.pi * t))], []
    raise ValueError(kind)


def accented(base, kind, cap=False):
    def fn(no_head, no_foot):
        shapes, holes, adv, a = base(no_head, no_foot)
        shapes, holes = list(shapes), list(holes)
        top = CAP if cap else P["xh"]
        if base in (g_i, g_j):             # drop the dot, centre on it
            dot = shapes.pop(1)
            cx = sum(p[0] for p in dot[1]) / len(dot[1])
        else:
            xs = [p[0] for sh in shapes for p in shape_points(sh) if 0 <= p[1] <= top]
            cx = (min(xs) + max(xs)) / 2
        y0 = top + (45 if cap else 95)
        m, mh = mark(kind, cx, y0, cap)
        return shapes + m, holes + mh, adv, a
    return fn


MARKS = {"acute": "\u0301", "grave": "\u0300", "circumflex": "\u0302", "dieresis": "\u0308",
         "tilde": "\u0303", "ring": "\u030a", "cedilla": "\u0327"}
ACCENT_SET = {"a": "acute grave circumflex dieresis tilde ring", "e": "acute grave circumflex dieresis",
              "i": "acute grave circumflex dieresis", "o": "acute grave circumflex dieresis tilde",
              "u": "acute grave circumflex dieresis", "y": "acute dieresis", "n": "tilde", "c": "cedilla"}
BASE = {}       # accented glyph name -> base letter
CHARS = {}      # glyph name -> character
for _b, _ks in ACCENT_SET.items():
    for _k in _ks.split():
        for _base, _table, _cap in ((_b, LOWER, False), (_b.upper(), CAPS, True)):
            _ch = unicodedata.normalize("NFC", _base + MARKS[_k])
            if len(_ch) != 1:
                continue
            _name = _base + _k
            _table[_name] = accented(_table[_base], _k, _cap)
            BASE[_name] = _base
            CHARS[_name] = _ch
# suffix: (entry kind, has exit). Entry kind matches the exit of the letter before.
FORMS = {"": (None, False), ".init": (None, True), ".medi": ("low", True), ".fina": ("low", False),
         ".medih": ("high", True), ".finah": ("high", False)}


def exit_kind(name):
    if name.endswith(".lo"):
        return "low"
    if P["join"] in ("diagonal", "powder") and BASE.get(name, name) in P["high_exits"]:
        return "high"
    return "low"


def emit(pen, shape, clockwise):
    kind = shape[0]
    if kind == "stroke":
        _, L, R = shape
        if (area(L + R[::-1]) < 0) != clockwise:
            L, R = R, L
        pen.moveTo(L[0])
        pen.qCurveTo(*L[1:])
        pen.lineTo(R[-1])
        pen.qCurveTo(*R[-2::-1])
    elif kind == "closed":
        pen.qCurveTo(*orient(shape[1], clockwise), None)
    else:
        pts = orient(shape[1], clockwise)
        pen.moveTo(pts[0])
        for pt in pts[1:]:
            pen.lineTo(pt)
    pen.closePath()


def draw(fn, entry, exit_, kind="low"):
    # Which serifs a join replaces depends on where the join attaches.
    no_head = bool(entry) and P["join"] in ("diagonal", "top", "powder")
    no_foot = exit_ and kind == "low" and P["join"] in ("diagonal", "rail", "powder", "powder-rail")
    shapes, holes, adv, a = fn(no_head, no_foot)
    shapes = list(shapes)
    if exit_:
        shapes.append(exit_join(a, adv, kind))
    if entry:
        shapes.append(entry_join(a, entry))
    flat, lines = [], []
    for sh in shapes:
        for part in (sh[1] if sh[0] == "multi" else [sh]):
            if part[0] == "dotline":
                (lines.append(part) if P["dots"] else flat.append(part[1]))
            else:
                flat.append(part)
    path = pathops.Path(fillType=pathops.FillType.WINDING)
    ppen = path.getPen()
    for part in flat:
        emit(ppen, part, True)
    for sh in holes:
        emit(ppen, sh, False)
    path.simplify(fix_winding=True, keep_starting_points=False, clockwise=True)
    if P["dots"]:
        path = dotify(path)
        if lines:
            extra = dots_to_path([d for part in lines for d in dotline_dots(part)])
            path = pathops.op(path, extra, pathops.PathOp.UNION)
    pen = TTGlyphPen(None)
    path.draw(TransformPen(pen, (1, 0, math.tan(math.radians(P["slant"])), 1, 0, 0)))
    return pen.glyph(dropImpliedOnCurves=True), adv


VERSION = "0.7"
RELEASE = ["Poke", "Poke Shaded", "Poke Line"]
COPYRIGHT = "Copyright 2026 Ben Dryden"
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")


def build(name, release=False):
    P.clear()
    P.update(DEFAULTS, **VARIANTS[name])
    RNG.seed(1)
    glyphs, metrics = {".notdef": TTGlyphPen(None).glyph(), "space": TTGlyphPen(None).glyph()}, {}
    metrics[".notdef"], metrics["space"] = (500, 0), (260, 0)
    order = [".notdef", "space"]
    # Stylistic set 1 swaps each high-exit letter for a copy that exits low.
    letters = dict(LOWER)
    alts = [c for c in LOWER if exit_kind(c) == "high"]
    letters.update({c + ".lo": LOWER[c] for c in alts})
    for gname, fn in letters.items():
        for suf, (entry, exit_) in FORMS.items():
            glyphs[gname + suf], adv = draw(fn, entry, exit_, exit_kind(gname))
            metrics[gname + suf] = (adv, 0)
            order.append(gname + suf)
    for gname, fn in CAPS.items():
        for suf, exit_ in (("", False), (".init", True)):
            glyphs[gname + suf], adv = draw(fn, None, exit_)
            metrics[gname + suf] = (adv, 0)
            order.append(gname + suf)
    for gname in OTHER:
        glyphs[gname], adv = draw(globals()["g_" + gname], None, False)
        metrics[gname] = (adv, 0)
        order.append(gname)
    for gname, g in glyphs.items():
        g.recalcBounds(glyphs)
        metrics[gname] = (metrics[gname][0], getattr(g, "xMin", 0))

    fam = "Lowie" if release else "Lowie Proto"
    family = fam + " " + name
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(CHARS.get(c, c)): c for c in list(LOWER) + list(CAPS)}
    cmap[32] = "space"
    cmap.update({ord(ch): gname for gname, ch in OTHER.items()})
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=900, descent=-250)
    ps = fam.replace(" ", "") + "-" + name.replace(" ", "")
    fb.setupNameTable({"familyName": family, "styleName": "Regular",
                       "typographicFamily": fam, "typographicSubfamily": name,
                       "fullName": family, "psName": ps, "uniqueFontIdentifier": ps + "-" + VERSION,
                       "version": "Version " + VERSION + "00", "copyright": COPYRIGHT,
                       "designer": "Ben Dryden", "licenseDescription": LICENSE,
                       "licenseInfoURL": "https://openfontlicense.org"})
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-250, usWinAscent=900, usWinDescent=250,
                sxHeight=P["xh"], sCapHeight=CAP, fsType=0)
    fb.setupPost()

    def cls(suffix, names=letters):
        return " ".join(c + suffix for c in names)

    low = [c for c in letters if exit_kind(c) == "low"]
    high = [c for c in letters if exit_kind(c) == "high"]
    out = lambda names: " ".join(cls(x, names) for x in (".init", ".medi", ".medih"))
    entry_rules = f"""
            sub @lowout @init' by @medi;
            sub @lowout @isol' by @fina;"""
    if high:
        entry_rules += f"""
            sub @highout @init' by @medih;
            sub @highout @isol' by @finah;"""
    ss01 = ""
    if alts:
        ss01 = ("feature ss01 { featureNames { name \"All low joins\"; }; lookup AllLow { sub ["
                + " ".join(alts) + "] by [" + " ".join(c + ".lo" for c in alts) + "]; } AllLow; } ss01;")
    fea = f"""
    @isol = [{cls("")}];
    @init = [{cls(".init")}];
    @medi = [{cls(".medi")}];
    @fina = [{cls(".fina")}];
    @medih = [{cls(".medih")}];
    @finah = [{cls(".finah")}];
    @caps = [{cls("", CAPS)}];
    @capsinit = [{cls(".init", CAPS)}];
    @lowout = [{out(low)} @capsinit];
    {"@highout = [" + out(high) + "];" if high else ""}
    {ss01}
    feature calt {{
        lookup ExitForms {{
            sub @isol' @isol by @init;
            sub @caps' @isol by @capsinit;
        }} ExitForms;
        lookup EntryForms {{{entry_rules}
        }} EntryForms;
    }} calt;
    """
    addOpenTypeFeaturesFromString(fb.font, fea)
    out = (OUT.parent / "release" / "fonts") if release else OUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / ((ps if release else "Lowie-Proto-" + name.replace(" ", "")) + ".ttf")
    fb.save(path)
    if release:                                   # web version, much smaller
        fb.font.flavor = "woff2"
        fb.font.save(out / (ps + ".woff2"))
        fb.font.flavor = None
    return family, path


if __name__ == "__main__":
    import sys
    if "--release" in sys.argv:                   # python build.py --release
        for name in RELEASE:
            fam, p = build(name, release=True)
            print(fam, p.stat().st_size, "bytes")
        sys.exit()
    names = [a.replace("_", " ") for a in sys.argv[1:]] or list(VARIANTS)   # e.g. build.py Poke Poke_Big
    for name in names:
        fam, p = build(name)
        print(fam, p.stat().st_size, "bytes")
