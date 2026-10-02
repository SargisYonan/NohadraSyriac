"""Shared helpers for the Nohadra QA scripts.

Coordinates are font units (1000 per em). Syriac runs right to left, so a
glyph's RIGHT edge (x = advance width) meets the letter before it and its
LEFT edge (x = 0) meets the letter after it.
"""

import collections
import functools
import os
import re

import glyphsLib
import uharfbuzz as hb
from glyphsLib import glyphdata
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILY = "Nohadra Syriac"
# The two styles, each built from the master of the same name.
STYLES = ("Sapna", "Amedia")
# Set FONT=path/to/file.otf to check a different build, e.g. one exported from Glyphs.
FONT = os.path.abspath(os.environ.get("FONT") or
                       os.path.join(ROOT, "fonts", "NohadraSyriac-Sapna.otf"))
SOURCE = os.path.join(ROOT, "glyphs", "NohadraSyriac.glyphs")


def style_of(path):
    """The style a font file is, from its name: 'NohadraSyriac-Amedia.otf' is Amedia."""
    name = os.path.basename(path)
    return next((s for s in STYLES if s.lower() in name.lower()), STYLES[0])


STYLE = style_of(FONT)
# Each style writes its reports to its own folder.
OUT = os.path.join(ROOT, "out", STYLE)
ALLOW = os.path.join(ROOT, "qa", "allow.txt")

# Unicode joining types: R joins only to the letter before it, D to both sides.
LETTERS = {
    0x0710: ("Alaph", "R"), 0x0712: ("Beth", "D"), 0x0713: ("Gamal", "D"),
    0x0714: ("Gamal Garshuni", "D"), 0x0715: ("Dalath", "R"),
    0x0716: ("Dotless Dalath Rish", "R"), 0x0717: ("He", "R"),
    0x0718: ("Waw", "R"), 0x0719: ("Zain", "R"), 0x071A: ("Heth", "D"),
    0x071B: ("Teth", "D"), 0x071C: ("Teth Garshuni", "D"),
    0x071D: ("Yudh", "D"), 0x071E: ("Yudh He", "R"), 0x071F: ("Kaph", "D"),
    0x0720: ("Lamadh", "D"), 0x0721: ("Mim", "D"), 0x0722: ("Nun", "D"),
    0x0723: ("Semkath", "D"), 0x0724: ("Final Semkath", "D"),
    0x0725: ("E", "D"), 0x0726: ("Pe", "D"), 0x0727: ("Reversed Pe", "D"),
    0x0728: ("Sadhe", "R"), 0x0729: ("Qaph", "D"), 0x072A: ("Rish", "R"),
    0x072B: ("Shin", "D"), 0x072C: ("Taw", "R"),
}

# Which sides each positional form connects on: (right, left).
# Alaph's extra forms: med2 is joined to the letter before but not word-final;
# fin2 and fin3 are unjoined word-final Alaphs.
FORMS = {
    "": (False, False), "init": (False, True), "medi": (True, True),
    "fina": (True, False), "med2": (True, False),
    "fin2": (False, False), "fin3": (False, False),
}
FORM_NAMES = {
    "": "isolated", "init": "initial", "medi": "medial", "fina": "final",
    "med2": "medial 2", "fin2": "final 2", "fin3": "final 3",
}

STEPS = 32  # segments per curve when flattening


LETTER_NAME = re.compile(r"uni(07[12][0-9A-F])((?:_?(?:uni)?07[12][0-9A-F])*)((?:\.\w+)*)")


def split_name(glyph):
    """'uni0712.init' -> (0x0712, 'init'); None for anything not a letter.

    Extra suffixes name variants of a form: 'uni072A.fina.syame' is a final
    Rish, 'uni072A.syame' an isolated one. A ligature is named after its
    letters, 'uni072C_uni0710' in the source and 'uni072C0710' once built,
    and joins like its first letter."""
    m = LETTER_NAME.fullmatch(glyph)
    if not m or int(m.group(1), 16) not in LETTERS:
        return None
    suffixes = m.group(3).split(".")[1:]
    form = suffixes[0] if suffixes and suffixes[0] in FORMS else ""
    return int(m.group(1), 16), form


def components(glyph):
    """The letters a glyph stands for: one, or several for a ligature."""
    m = LETTER_NAME.fullmatch(glyph)
    return [int(m.group(1), 16)] + [int(c, 16) for c in re.findall(r"07[12][0-9A-F]", m.group(2))]


def label(glyph):
    parts = split_name(glyph)
    if not parts:
        return glyph
    cp, form = parts
    names = "–".join(LETTERS[c][0] for c in components(glyph))
    kind = " ligature" if len(components(glyph)) > 1 else ""
    variants = [v for v in glyph.split(".")[1:] if v != form]
    return f"{names}{kind} {FORM_NAMES[form]}" + "".join(f" ({v})" for v in variants)


def joins(glyph):
    """(joins_right, joins_left) for a letter glyph."""
    return FORMS.get(split_name(glyph)[1], (False, False))


class FlattenPen(BasePen):
    """Collects each contour as a polygon, approximating curves by lines."""

    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.polys, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, a, b, c):
        x0, y0 = self.cur[-1]
        for i in range(1, STEPS + 1):
            t = i / STEPS
            u = 1 - t
            self.cur.append((
                u**3 * x0 + 3 * u * u * t * a[0] + 3 * u * t * t * b[0] + t**3 * c[0],
                u**3 * y0 + 3 * u * u * t * a[1] + 3 * u * t * t * b[1] + t**3 * c[1],
            ))

    def _qCurveToOne(self, a, b):
        x0, y0 = self.cur[-1]
        for i in range(1, STEPS + 1):
            t = i / STEPS
            u = 1 - t
            self.cur.append((
                u * u * x0 + 2 * u * t * a[0] + t * t * b[0],
                u * u * y0 + 2 * u * t * a[1] + t * t * b[1],
            ))

    def _closePath(self):
        if self.cur:
            self.polys.append(self.cur)
        self.cur = []

    _endPath = _closePath


class Glyph:
    def __init__(self, name, width, polys):
        self.name, self.width, self.polys = name, width, polys
        xs = [x for p in polys for x, _ in p]
        ys = [y for p in polys for _, y in p]
        self.bounds = (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def ink_at_x(self, x):
        """Vertical runs of ink [(bottom, top), ...] along the line at x."""
        ys = []
        for poly in self.polys:
            n = len(poly)
            for i in range(n):
                (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
                if (x0 <= x < x1) or (x1 <= x < x0):
                    ys.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
        ys.sort()
        return [(ys[i], ys[i + 1]) for i in range(0, len(ys) - 1, 2)]

    def contains(self, x, y):
        """Whether (x, y) is inside the ink (even-odd; the font has no overlaps)."""
        return sum(b <= y <= t for b, t in self.ink_at_x(x)) % 2 == 1

    def ink_at_y(self, y):
        """Horizontal runs of ink [(left, right), ...] along the line at y."""
        xs = []
        for poly in self.polys:
            n = len(poly)
            for i in range(n):
                (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


class Font:
    def __init__(self, path=FONT):
        if not os.path.exists(path):
            raise SystemExit(f"{path} not found - run `make build` first")
        self.path = path
        self.tt = TTFont(path)
        self.glyphset = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self._cache = {}

    def glyph(self, name):
        if name not in self._cache:
            pen = FlattenPen(self.glyphset)
            self.glyphset[name].draw(pen)
            self._cache[name] = Glyph(name, self.tt["hmtx"][name][0], pen.polys)
        return self._cache[name]

    def letters(self):
        """Every letter glyph in the font that has outlines, in glyph order."""
        return [g for g in self.tt.getGlyphOrder()
                if split_name(g) and self.glyph(g).polys]

    def is_mark(self, name):
        """Whether GDEF classes the glyph as a mark (HarfBuzz then gives it
        no advance, whatever its width in the font)."""
        gdef = self.tt["GDEF"].table.GlyphClassDef
        return bool(gdef) and gdef.classDefs.get(name) == 3

    def advance(self, name):
        """The glyph's advance as shaped text uses it: none for a mark."""
        return 0 if self.is_mark(name) else self.glyph(name).width

    def ligatures(self):
        """(first, second) letters of every drawn ligature, e.g. Taw–Alaph."""
        return sorted({tuple(components(g)) for g in self.letters() if len(components(g)) > 1})

    def drawn_codepoints(self):
        return sorted(cp for cp in LETTERS
                      if cp in self.cmap and self.glyph(self.cmap[cp]).polys)


def run_at(runs, y):
    """The (bottom, top) run that contains y, or None."""
    for b, t in runs:
        if b <= y <= t:
            return b, t
    return None


def mode(values):
    return collections.Counter(values).most_common(1)[0][0] if values else None


def load_allow():
    """Lines of qa/allow.txt as a set of (glyph, check) pairs, or
    (glyph, check, mark) when a line names the one mark it excuses."""
    allowed = set()
    if os.path.exists(ALLOW):
        for line in open(ALLOW, encoding="utf-8"):
            line = line.split("#", 1)[0].split()
            if len(line) >= 2:
                allowed.add(tuple(line[:3]))
    return allowed


def is_allowed(allowed, glyph, check, mark=None):
    return bool({(glyph, check), ("*", check), (glyph, check, mark), ("*", check, mark)}
                & allowed)


# --- joints -------------------------------------------------------------------

STEM = 40     # a joint this much taller/deeper than the bar is a stem, not a step
PROBE = 0.5   # where an edge is slanted, measure this far inside it
DEEP = 20     # ...and look this far in, to catch a stroke that sags into the joint
SAG = 3       # how far the stroke may drift within DEEP of the joint


def edge_reach(glyph, side, mid):
    """How far the ink reaches toward one edge at the joining height."""
    spans = glyph.ink_at_y(mid)
    if not spans:
        return None
    return max(s[1] for s in spans) if side == "right" else min(s[0] for s in spans)


def edge_run(glyph, side, mid):
    """(bottom, top) of the ink standing on the joining edge, or None if the
    ink does not reach the edge at the joining height.

    Uses the outline's own upright segment at the edge when there is one, so a
    curve meeting the edge head-on is measured where it lands, not a fraction
    of a unit inside."""
    edge = glyph.width if side == "right" else 0
    xe = edge_reach(glyph, side, mid)
    if xe is None or (xe < edge - 0.5 if side == "right" else xe > edge + 0.5):
        return None
    ys = []
    for poly in glyph.polys:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            if abs(x0 - xe) < 0.01 and abs(x1 - xe) < 0.01:
                ys.append(sorted((y0, y1)))
    runs = sorted(ys)
    merged = []
    for b, t in runs:
        if merged and b <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], t)
        else:
            merged.append([b, t])
    hit = run_at([tuple(r) for r in merged], mid)
    if hit:
        return hit
    inward = -1 if side == "right" else 1
    return run_at(glyph.ink_at_x(xe + inward * PROBE), mid)


def deep_run(glyph, side, mid):
    x = glyph.width - DEEP if side == "right" else DEEP
    return run_at(glyph.ink_at_x(x), mid)


def joint_problems(glyph, side, bar):
    """What is wrong with one joining edge, as {check: (y, size, message)}.

    The joint must stand exactly on the connecting stroke. Past the stroke a
    letter may rise (a stem, or the shoulder of a diagonal) or drop (a tail),
    but a flat stroke at a different height is a step, and a stroke that dips
    or bulges just before the edge leaves a notch at the seam."""
    bottom, top = bar
    mid = (bottom + top) / 2
    run = edge_run(glyph, side, mid)
    if run is None:
        xe = edge_reach(glyph, side, mid)
        edge = glyph.width if side == "right" else 0
        short = abs(edge - xe) if xe is not None else glyph.width
        return {"join-gap": (mid, short, f"the connecting stroke stops {short:.1f} "
                                         f"units short of the edge, leaving a gap")}
    b, t = run
    deep = deep_run(glyph, side, mid)
    tail = deep is not None and deep[0] < min(b, bottom) - STEM / 2
    rises = deep is not None and deep[1] > max(t, top) + STEM / 2
    out = {}
    if abs(b - bottom) >= 0.5 and not (b < bottom and (tail or b < bottom - STEM)):
        out["join-bottom"] = (b, abs(b - bottom), f"bottom of the joint is at y={b:.1f}, "
                                                  f"not on the baseline y={bottom}")
    if abs(t - top) >= 0.5 and not (t > top and (rises or t > top + STEM)):
        out["join-top"] = (t, abs(t - top), f"top of the joint is at y={t:.1f}, not level "
                                            f"with the connecting stroke y={top}: a step")
    if deep and not out:
        moved = 0 if tail else deep[0] - b
        dropped = min(0, deep[1] - t) if t < top + STEM else 0
        if abs(moved) >= 1 or dropped <= -1:
            out["join-sag"] = (top if dropped <= -1 else bottom, max(abs(moved), -dropped),
                               f"the stroke is not flat going into the joint: within "
                               f"{DEEP} units its bottom moves {moved:.1f} and its top "
                               f"drops {-dropped:.1f}, leaving a notch or bump")
    return out


def compare_seam(left, right, bar):
    """Problems where `left`'s right edge meets `right`'s left edge, as
    [(y, message)]: whatever is wrong with either side of the joint."""
    out = []
    for glyph, side in ((left, "right"), (right, "left")):
        for y, _, msg in joint_problems(glyph, side, bar).values():
            out.append((y, f"{glyph.name}: {msg}"))
    return out


@functools.lru_cache(maxsize=None)
def _hb_font(path):
    return hb.Font(hb.Face(hb.Blob.from_file_path(path)))


def shape(path, text):
    """HarfBuzz output as [(glyph, x, y)] in visual (left-to-right) order."""
    hbfont = _hb_font(path)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf)
    names = [hbfont.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
    out, x = [], 0
    for name, pos in zip(names, buf.glyph_positions):
        out.append((name, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    return out


def seams(font, run, bar):
    """Every joint in a shaped run, as dicts: x, glyphs, problems, and
    `mismatch` when only one side of it is shaped to join."""
    letters = [(g, x) for g, x, _ in run if split_name(g)]
    out = []
    for (lg, _), (rg, rx) in zip(letters, letters[1:]):
        l_joins, r_joins = joins(lg)[0], joins(rg)[1]
        if not (l_joins or r_joins):
            continue
        seam = dict(x=rx, left=lg, right=rg, problems=[], mismatch=l_joins != r_joins)
        if seam["mismatch"]:
            seam["problems"].append(((bar[0] + bar[1]) / 2,
                                     "only one side is shaped to join"))
        else:
            seam["problems"] = compare_seam(font.glyph(lg), font.glyph(rg), bar)
        out.append(seam)
    return out


# --- marks --------------------------------------------------------------------

MARK_GAP = 20     # QA warns when a mark comes closer than this to any letter
MARK_TOUCH = 10   # ...and the tests fail when it comes closer than this

# Copies of marks that a rule in `rlig` swaps in on one letter only, and the
# letters they sit on. Checks place them on those letters and nowhere else.
CONTEXT_MARKS = {}
DOTTED_CIRCLE = "\u25cc"

# Anchors a letter carries for one particular mark, beside `top` and `bottom`.
LETTER_ONLY_ANCHORS = set()


def bases_for(mark, letters):
    """The letters a mark can actually sit on."""
    return [g for g in letters if g in CONTEXT_MARKS.get(mark, letters)]


def master_layer(glyph, style=STYLE):
    """The glyph's layer in the master the style is built from."""
    master = next(m for m in glyph.parent.masters if m.name == style)
    return glyph.layers[master.id]


def production_name(name):
    """The name a source glyph has in the built font ('uni072C_uni0710' is
    built as 'uni072C0710'; every other name stays as it is)."""
    return glyphdata.get_glyph(name).production_name or name


def load_anchors(path=SOURCE, style=STYLE):
    """{glyph: {anchor name: (x, y)}} from the style's master in the Glyphs
    source, by built name."""
    font = glyphsLib.GSFont(path)
    return {production_name(g.name): {a.name: (a.position.x, a.position.y)
                                      for a in master_layer(g, style).anchors}
            for g in font.glyphs if g.export}


def spots(anchors, glyph, side):
    """The anchors on `glyph` where a mark on `side` ('top' or 'bottom') can
    sit: `side` itself, or `side_1`, `side_2`, ... on a ligature, one per letter."""
    names = anchors.get(glyph, {})
    if side in names:
        return [side]
    return sorted(n for n in names if re.fullmatch(side + r"_\d+", n))


def drawn_marks(font, anchors):
    """Marks that have outlines, as {mark: (base anchor, mark anchor)}.

    A mark with parts on both sides (U+0732) is split into its .above and
    .below parts by ccmp before positioning, so the parts are checked instead."""
    out = {}
    for name, a in anchors.items():
        if name not in font.glyphset or not font.glyph(name).polys:
            continue
        if "_top" in a and "_bottom" in a:
            continue
        if "_top" in a:
            out[name] = ("top", "_top")
        elif "_bottom" in a:
            out[name] = ("bottom", "_bottom")
    return out


def clearance(a, ax, ay, b, bx, by, step=3, enough=None):
    """Smallest vertical distance between the ink of glyph `a` drawn at
    (ax, ay) and glyph `b` at (bx, by), over the columns they share.
    Negative means they overlap; None means they never share a column.
    If the bounding boxes alone are at least `enough` apart, that distance
    is returned without measuring the outlines."""
    lo = max(a.bounds[0] + ax, b.bounds[0] + bx)
    hi = min(a.bounds[2] + ax, b.bounds[2] + bx)
    if lo >= hi:
        return None
    box = max(b.bounds[1] + by - (a.bounds[3] + ay), a.bounds[1] + ay - (b.bounds[3] + by))
    if enough is not None and box >= enough:
        return box
    best = None
    x = lo + 0.5
    while x < hi:
        for ab, at in a.ink_at_x(x - ax):
            for bb, bt in b.ink_at_x(x - bx):
                d = max(bb + by - (at + ay), ab + ay - (bt + by))
                best = d if best is None else min(best, d)
        x += step
    return best


def place_mark(anchors, base, mark, pair, spot=None):
    """Where `mark` lands on `base` (drawn at the origin), from the anchors:
    at `spot` if given (one letter of a ligature), else at the base anchor."""
    base_anchor, mark_anchor = pair
    (bx, by), (mx, my) = anchors[base][spot or base_anchor], anchors[mark][mark_anchor]
    return bx - mx, by - my


def mark_collisions(font, run):
    """For each mark in a shaped run, its closest approach to a letter other
    than the one it sits on: [(mark, x, y, nearest letter, clearance)].

    HarfBuzz lists a mark just before its base, in visual order."""
    out = []
    for i, (m, mx, my) in enumerate(run):
        if m not in font.glyphset or not font.is_mark(m) or not font.glyph(m).polys:
            continue
        base = next((j for j in range(i + 1, len(run)) if not font.is_mark(run[j][0])), None)
        worst = None
        for j, (g, gx, gy) in enumerate(run):
            if j == base or font.is_mark(g) or not font.glyph(g).polys:
                continue
            d = clearance(font.glyph(m), mx, my, font.glyph(g), gx, gy, enough=MARK_GAP)
            if d is not None and (worst is None or d < worst[1]):
                worst = (g, d)
        if worst:
            out.append((m, mx, my) + worst)
    return out


def neighbour_texts(font, mark_char):
    """Short texts that put `mark_char` on every form of every letter with
    every letter beside it: on the first or second of a pair, and on a
    medial letter between Beth and each other letter."""
    beth = "\u0712"
    cps = font.drawn_codepoints()
    for a in cps:
        for b in cps:
            yield chr(a) + mark_char + chr(b)          # on a, b after it
            yield chr(a) + chr(b) + mark_char          # on b, a before it
            yield beth + chr(a) + mark_char + chr(b)   # on medial a, b after it
            yield chr(a) + chr(b) + mark_char + beth   # on medial b, a before it


def signs(font):
    """Every drawn character that is neither a letter nor a mark, and every
    drawn mark, as text: marks are shown on a dotted circle."""
    out, marks = [], []
    for cp, g in sorted(font.cmap.items()):
        if not font.glyph(g).polys or split_name(g):
            continue
        (marks if font.is_mark(g) else out).append(chr(cp))
    return out, [DOTTED_CIRCLE + m for m in marks]
