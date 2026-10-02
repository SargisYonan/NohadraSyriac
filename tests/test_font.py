"""Pass/fail tests for the font as a whole. Run with `make test`."""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "qa"))
from common import Font  # noqa: E402

FONT = Font()
# Characters that are meant to draw nothing.
INVISIBLE = {0x0000, 0x000D, 0x0020, 0x00A0, 0x200C, 0x200D, 0x200E, 0x200F}


def test_no_character_draws_nothing():
    """Every character the font claims must have an outline. An empty glyph
    makes the character vanish; leaving it out (Export unticked in Glyphs)
    lets apps borrow it from another font instead."""
    empty = [f"U+{cp:04X} {unicodedata.name(chr(cp), '?').title()} ({g})"
             for cp, g in sorted(FONT.cmap.items())
             if cp not in INVISIBLE and not FONT.glyph(g).polys]
    assert not empty, "these characters draw nothing: " + "; ".join(empty)


def test_invisible_characters_draw_nothing():
    """Spaces, joiners and direction marks must not draw anything (LRM and
    RLM used to draw an arrow)."""
    drawn = [f"U+{cp:04X} ({g})" for cp, g in sorted(FONT.cmap.items())
             if cp in INVISIBLE and FONT.glyph(g).polys]
    assert not drawn, "these characters should be invisible: " + "; ".join(drawn)


def test_win_metrics_cover_every_glyph():
    """Windows clips whatever lies outside winAscent/winDescent."""
    os2 = FONT.tt["OS/2"]
    ys = [FONT.glyph(g).bounds for g in FONT.tt.getGlyphOrder() if FONT.glyph(g).bounds]
    assert os2.usWinAscent >= max(b[3] for b in ys)
    assert os2.usWinDescent >= -min(b[1] for b in ys)
    assert os2.fsSelection & (1 << 7), "Use Typo Metrics should be on"


def test_marks_have_no_advance():
    """Marks are drawn over the letter, not beside it."""
    wide = [g for g in FONT.tt.getGlyphOrder() if FONT.is_mark(g) and FONT.glyph(g).width]
    assert not wide, "marks with an advance width: " + ", ".join(wide)


def test_notdef_is_visible():
    assert FONT.glyph(".notdef").polys, ".notdef must be drawn, so missing characters show"
