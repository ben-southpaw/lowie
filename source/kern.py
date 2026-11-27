"""Automatic kerning for Lowie, measured from the built dot outlines.

Only pairs that never join are kerned, so the joins always meet exactly:
capitals before capitals, figures and punctuation, and any letter next to a figure
or punctuation mark. Lowercase before lowercase, and a capital before lowercase,
always join (calt), so they are left alone.

Method: each glyph gets a profile, the leftmost and rightmost ink in 20-unit bands.
The gap of a pair is its smallest horizontal distance between the two inks, taken
between bands no more than 40 units apart (so a period under the bar of a T counts).
Only pairs with a shape that leaves room on the facing side are considered (OPEN_RIGHT
before, OPEN_LEFT after: T V W Y A L P, r v w y f, quotes, period, comma, 1, 7...).
Those are tightened so their gap comes down towards the gap between two H's, and any
pair that would touch is opened up. Round and straight pairs stay on their side bearings.
"""
import numpy as np

BAND = 20
LO, HI = -300, 1000                     # y range covered by the profiles
NB = (HI - LO) // BAND
REACH = 2                               # bands either side that still count as "facing"


def profiles(glyph):
    """Leftmost and rightmost x of the ink in each band (NaN where there is none)."""
    left, right = np.full(NB, np.nan), np.full(NB, np.nan)
    if getattr(glyph, "numberOfContours", 0) <= 0:
        return left, right
    xy = np.array(list(glyph.coordinates), float)
    b = np.clip(((xy[:, 1] - LO) // BAND).astype(int), 0, NB - 1)
    for i in np.unique(b):
        xs = xy[b == i, 0]
        left[i], right[i] = xs.min(), xs.max()
    return left, right


def gap(rgap_l, left_r):
    """Smallest distance between L's right edge and R's left edge, over facing bands."""
    best = np.inf
    for d in range(-REACH, REACH + 1):
        a = rgap_l[max(0, -d):NB - max(0, d)]
        b = left_r[max(0, d):NB - max(0, -d)]
        s = a + b
        if np.any(~np.isnan(s)):
            best = min(best, np.nanmin(s))
    return best


ACCENTS = ("acute", "grave", "circumflex", "dieresis", "tilde", "ring", "cedilla")
QUOTES = {"quoteright", "quoteleft", "quotedblright", "quotedblleft", "quotesingle", "quotedbl"}
# Glyphs whose right side leaves room (their neighbour can tuck in), and whose left side does.
OPEN_RIGHT = set("TVWYAPFLKXR" "rvwyfkx") | QUOTES | {"seven", "one", "slash"}
OPEN_LEFT = set("AJTVWYX") | QUOTES | {"period", "comma", "ellipsis", "colon", "semicolon", "slash",
                                         "four", "one"}


def letter(name):
    """Base letter of a glyph name: Aacute.init -> A, period -> period."""
    n = name.split(".")[0]
    return n[0] if len(n) > 1 and n[0].isalpha() and n[1:] in ACCENTS else n


def kerning(glyphs, advances, lefts, rights, skip=lambda l, r: False, ref="H", strength=0.7,
            lo=-180, hi=60, threshold=20, touch=0.35):
    """Return {(left, right): value}. lefts/rights are the glyph names that may take part."""
    prof = {n: profiles(glyphs[n]) for n in set(lefts) | set(rights) | {ref}}
    rgap = {n: advances[n] - prof[n][1] for n in prof}     # space to the right of the ink
    lgap = {n: prof[n][0] for n in prof}                   # space to the left of the ink
    target = gap(rgap[ref], lgap[ref])                     # the gap between two H's
    out = {}
    for l in lefts:
        for r in rights:
            if skip(l, r) or not (letter(l) in OPEN_RIGHT or letter(r) in OPEN_LEFT):
                continue
            actual = gap(rgap[l], lgap[r])
            if not np.isfinite(actual):
                continue                                   # the two never face each other
            if actual > target:
                k = strength * (target - actual)           # tighten an open pair
            elif actual < touch * target:
                k = target * 0.6 - actual                  # open up a pair that nearly touches
            else:
                continue
            k = int(round(max(lo, min(hi, k)) / 5) * 5)
            if abs(k) >= threshold:
                out[(l, r)] = k
    return out


def feature(pairs):
    """A kern feature in feaLib syntax, one glyph pair per line."""
    if not pairs:
        return ""
    lines = [f"        pos {l} {r} {v};" for (l, r), v in sorted(pairs.items())]
    return "    feature kern {\n" + "\n".join(lines) + "\n    } kern;\n"
