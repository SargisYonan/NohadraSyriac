"""Pass/fail tests for vowels and other marks. Run with `make test`.

Letters carry `top` and `bottom`; marks above the line carry `_top` (where
they attach) and `top` (where the next mark stacks); marks below carry
`_bottom` and `bottom`; a mark with parts on both sides carries all four.
The mark and mkmk features are generated from these anchors, and the tests
check that the built font follows them and that no mark touches a letter.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "qa"))
from common import (LETTER_ONLY_ANCHORS, MARK_TOUCH, Font, bases_for,  # noqa: E402
                    clearance, components, drawn_marks, is_allowed, label, load_allow,
                    load_anchors, mark_collisions, neighbour_texts, place_mark,
                    shape, split_name, spots)

FONT = Font()
ANCHORS = load_anchors()
LETTERS = FONT.letters()
MARKS = {name: a for name, a in ANCHORS.items() if "_top" in a or "_bottom" in a}
DRAWN = drawn_marks(FONT, ANCHORS)
ALLOW = load_allow()
REACH = 50   # most marks span about this far either side of their anchor


def placed(run, glyph):
    """(x, y) of the one `glyph` in a shaped run."""
    (_, x, y), = [r for r in run if r[0] == glyph]
    return x, y


def expected_anchors(glyph):
    """`top` and `bottom`, or `top_1`, `bottom_1`, ... per letter of a ligature."""
    n = len(components(glyph))
    if n == 1:
        return {"top", "bottom"}
    return {f"{side}_{i}" for side in ("top", "bottom") for i in range(1, n + 1)}


@pytest.mark.parametrize("glyph", LETTERS)
def test_letter_has_top_and_bottom(glyph):
    names = {n for n in ANCHORS[glyph] if not re.fullmatch(r"caret_\d+", n)}
    wanted = expected_anchors(glyph)
    assert wanted <= names and names - wanted <= LETTER_ONLY_ANCHORS, \
        f"{label(glyph)} has anchors {sorted(names)}, expected {sorted(wanted)}"


@pytest.mark.parametrize("glyph", LETTERS)
def test_letter_anchors_clear_the_ink(glyph):
    """Marks must not land on the letter: each top anchor above everything
    under it, each bottom anchor below everything over it."""
    g = FONT.glyph(glyph)
    for side in ("top", "bottom"):
        for spot in spots(ANCHORS, glyph, side):
            x, y = ANCHORS[glyph][spot]
            assert 0 <= x <= g.width, f"{spot} anchor x={x} is outside the letter"
            runs = [r for dx in range(-REACH, REACH + 1, 4) for r in g.ink_at_x(x + dx + 0.5)]
            if side == "top" and runs:
                assert y > max(t for _, t in runs), f"{spot} anchor y={y} is inside the ink"
            if side == "bottom" and runs:
                assert y < min(b for b, _ in runs), f"{spot} anchor y={y} is inside the ink"


@pytest.mark.parametrize("mark", sorted(MARKS))
def test_mark_anchors(mark):
    """Each side a mark attaches on needs its stacking anchor too. Marks with
    parts both above and below (like U+0732) carry both pairs."""
    names = set(MARKS[mark])
    assert names in ({"_top", "top"}, {"_bottom", "bottom"},
                     {"_top", "top", "_bottom", "bottom"}), \
        f"{mark} has anchors {sorted(names)}"


def test_no_stray_anchor_names():
    allowed = {"top", "bottom", "_top", "_bottom"} | LETTER_ONLY_ANCHORS | \
        {"_" + a for a in LETTER_ONLY_ANCHORS}
    # top_1, bottom_2... place marks on each letter of a ligature; caret_1...
    # are where the cursor stops inside it.
    odd = {f"{g}: {n}" for g, a in ANCHORS.items() for n in a
           if n not in allowed and not re.fullmatch(r"(top|bottom|caret)_\d+", n)}
    assert not odd, "unexpected anchors: " + ", ".join(sorted(odd))


@pytest.mark.parametrize("glyph", [g for g in LETTERS
                                   if "." not in g and len(components(g)) == 1])
def test_marks_attach_at_anchors(glyph):
    """Shaping a letter with a mark above and one below must put each mark at
    the letter's anchor. Fails if a hand-written mark feature overrides them."""
    cp = split_name(glyph)[0]
    for mark, base_anchor, mark_anchor in (("ܵ", "top", "_top"), ("ܼ", "bottom", "_bottom")):
        run = shape(FONT.path, chr(cp) + mark)
        mark_glyph = f"uni{ord(mark):04X}"
        (mx, my), (bx, by) = placed(run, mark_glyph), placed(run, glyph)
        want = (bx + ANCHORS[glyph][base_anchor][0] - ANCHORS[mark_glyph][mark_anchor][0],
                by + ANCHORS[glyph][base_anchor][1] - ANCHORS[mark_glyph][mark_anchor][1])
        assert (mx, my) == want, f"{mark_glyph} on {label(glyph)} at {(mx, my)}, anchors say {want}"


def test_every_drawn_mark_attaches():
    """A mark with outlines but no attaching anchor is drawn wherever the pen
    happens to be, beside the letter instead of on it."""
    gdef = FONT.tt["GDEF"].table.GlyphClassDef.classDefs
    loose = [g for g, cls in gdef.items() if cls == 3 and FONT.glyph(g).polys
             and not any(a.startswith("_") for a in ANCHORS.get(g, {}))
             and not is_allowed(ALLOW, g, "unattached")]
    assert not loose, "marks with no attaching anchor: " + ", ".join(sorted(loose))


@pytest.mark.parametrize("mark", sorted(DRAWN))
def test_mark_sits_on_its_anchors(mark):
    """An above mark rises from its `_top` and its `top` clears it; a below
    mark hangs from its `_bottom` and its `bottom` is under it."""
    if is_allowed(ALLOW, "*", "mark-clearance", mark):
        pytest.skip(f"{mark} is drawn to touch the letter (qa/allow.txt)")
    _, y0, _, y1 = FONT.glyph(mark).bounds
    a = ANCHORS[mark]
    if "_top" in a:
        assert y0 >= a["_top"][1] - 5, f"ink dips to y={y0:.0f}, below _top at {a['_top'][1]}"
        assert a["top"][1] > y1, f"top anchor y={a['top'][1]} is inside the ink (to {y1:.0f})"
    else:
        assert y1 <= a["_bottom"][1] + 5, \
            f"ink rises to y={y1:.0f}, above _bottom at {a['_bottom'][1]}"
        assert a["bottom"][1] < y0, \
            f"bottom anchor y={a['bottom'][1]} is inside the ink (to {y0:.0f})"


@pytest.mark.parametrize("mark", sorted(DRAWN))
def test_mark_clears_every_letter(mark):
    """Placed by the anchors, the mark must not touch any form of any letter."""
    bad = []
    for glyph in bases_for(mark, LETTERS):
        for spot in spots(ANCHORS, glyph, DRAWN[mark][0]):
            x, y = place_mark(ANCHORS, glyph, mark, DRAWN[mark], spot)
            d = clearance(FONT.glyph(mark), x, y, FONT.glyph(glyph), 0, 0)
            if d is not None and d < MARK_TOUCH and \
                    not is_allowed(ALLOW, glyph, "mark-clearance", mark):
                bad.append(f"{label(glyph)} at {spot} ({d:.0f})")
    assert not bad, f"{mark} touches: " + ", ".join(bad)


@pytest.mark.parametrize("mark", sorted(m for m in DRAWN if "." not in m))
def test_mark_clears_neighbours(mark):
    """In shaped text, a mark must not run into the letters beside its own,
    on any form of any letter next to any other letter."""
    bad = set()
    for text in neighbour_texts(FONT, chr(int(mark[3:7], 16))):
        for _, _, _, other, d in mark_collisions(FONT, shape(FONT.path, text)):
            if d < MARK_TOUCH and not is_allowed(ALLOW, other, "mark-neighbour", mark):
                bad.add(f"{text} hits {label(other)} ({d:.0f})")
    assert not bad, f"{mark}: " + "; ".join(sorted(bad))


@pytest.mark.parametrize("kind", ["top", "bottom"])
def test_marks_stack(kind):
    """Two marks on the same side stack without touching."""
    side = [m for m, (base, _) in DRAWN.items() if base == kind]
    bad = []
    for first in side:
        for second in side:
            if is_allowed(ALLOW, first, "mark-stack", second):
                continue
            x, y = place_mark(ANCHORS, first, second, DRAWN[second])
            d = clearance(FONT.glyph(second), x, y, FONT.glyph(first), 0, 0)
            if d is not None and d < MARK_TOUCH:
                bad.append(f"{second} on {first} ({d:.0f})")
    assert not bad, "; ".join(bad)


@pytest.mark.parametrize("text,mark,spot", [
    ("\u072C\u0735\u0710", "uni0735", "top_1"),      # zqapa on the Taw
    ("\u072C\u0710\u0735", "uni0735", "top_2"),      # zqapa on the Alaph
    ("\u072C\u073C\u0710", "uni073C", "bottom_1"),   # dot below the Taw
    ("\u072C\u0710\u073C", "uni073C", "bottom_2"),   # dot below the Alaph
])
def test_marks_on_taw_alaph(text, mark, spot):
    """A vowel on either letter of the Taw–Alaph ligature sits over that
    letter, at its own anchor."""
    run = shape(FONT.path, text)
    (mx, my), (bx, by) = placed(run, mark), placed(run, "uni072C0710")
    side = spot.split("_")[0]
    want = (bx + ANCHORS["uni072C0710"][spot][0] - ANCHORS[mark]["_" + side][0],
            by + ANCHORS["uni072C0710"][spot][1] - ANCHORS[mark]["_" + side][1])
    assert (mx, my) == want, f"{mark} at {(mx, my)}, {spot} says {want}"
