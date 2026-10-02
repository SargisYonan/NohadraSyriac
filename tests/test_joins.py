"""Pass/fail tests for how the letters connect. Run with `make test`.

These fail only on things that break a join. Style questions (corners, near-miss
heights) are reported by `make qa` instead. To accept a join problem on purpose,
add "<glyph> join-top" (or join-bottom, join-gap) to qa/allow.txt.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "qa"))
from check import bar_metrics  # noqa: E402
from common import (LETTERS, Font, is_allowed, joins, joint_problems,  # noqa: E402
                    label, load_allow, seams, shape)

FONT = Font()
LETTER_GLYPHS = FONT.letters()
BAR = bar_metrics(FONT, LETTER_GLYPHS)
DRAWN = FONT.drawn_codepoints()
ALLOW = load_allow()

SIDES = [(g, side) for g in LETTER_GLYPHS
         for side, on in zip(("right", "left"), joins(g)) if on]



@pytest.mark.parametrize("cp", [cp for cp in LETTERS if cp in DRAWN],
                         ids=lambda cp: LETTERS[cp][0])
def test_letter_has_every_form(cp):
    base = FONT.cmap[cp]
    forms = ["fina"] if LETTERS[cp][1] == "R" else ["init", "medi", "fina"]
    missing = [f for f in forms
               if f"{base}.{f}" not in FONT.glyphset or not FONT.glyph(f"{base}.{f}").polys]
    assert not missing, f"{LETTERS[cp][0]} has no {', '.join(missing)} form"


@pytest.mark.parametrize("glyph,side", SIDES, ids=[f"{g}-{s}" for g, s in SIDES])
def test_joint_matches_connecting_stroke(glyph, side):
    """Each joining edge must stand exactly on the connecting stroke, and the
    stroke must run flat into it. Stems, shoulders and tails that carry on
    past the stroke are fine."""
    problems = [msg for check, (_, size, msg) in
                joint_problems(FONT.glyph(glyph), side, BAR).items()
                if not is_allowed(ALLOW, glyph, check) and size >= (1 if check == "join-sag" else 0.5)]
    assert not problems, f"{label(glyph)}, {side} edge: " + "; ".join(problems)


@pytest.mark.parametrize("first", [cp for cp in DRAWN if LETTERS[cp][1] == "D"],
                         ids=lambda cp: LETTERS[cp][0])
def test_shaping_joins_every_following_letter(first):
    """A dual-joining letter followed by any letter must be shaped into two
    forms that both connect, or into a ligature."""
    bad = []
    for second in DRAWN:
        if (first, second) in FONT.ligatures():
            continue   # one glyph, no seam: see test_ligatures
        run = shape(FONT.path, chr(first) + chr(second))
        found = seams(FONT, run, BAR)
        if len(found) != 1 or found[0]["mismatch"]:
            bad.append(f"{LETTERS[second][0]}: {' '.join(g for g, _, _ in run)}")
    assert not bad, "not joined as expected: " + "; ".join(bad)


@pytest.mark.parametrize("text,alaph", [
    ("ܐ", "uni0710"),                   # alone
    ("ܒܐ", "uni0710.fina"),        # joined, word-final
    ("ܒܐܒ", "uni0710.med2"),  # joined, mid-word
    ("ܘܐ", "uni0710.fin2"),        # after a non-joining letter
    ("ܕܐ", "uni0710.fin3"),        # after Dalath
    ("ܪܐ", "uni0710.fin3"),        # after Rish
], ids=["isolated", "final", "medial2", "final2", "final3-dalath", "final3-rish"])
def test_alaph_forms(text, alaph):
    names = [g for g, _, _ in shape(FONT.path, text)]
    assert alaph in names, f"expected {alaph}, got {names}"


@pytest.mark.parametrize("cp", [cp for cp in DRAWN if LETTERS[cp][1] == "R"],
                         ids=lambda cp: LETTERS[cp][0])
def test_right_joiner_never_joins_forward(cp):
    """Right-joining letters (Alaph, Dalath, Waw, ...) never connect to the
    letter after them, so between two Beths they must not take a form that
    joins on the left."""
    run = shape(FONT.path, "\u0712" + chr(cp) + "\u0712")
    mine = [g for g, _, _ in run if g.startswith(f"uni{cp:04X}")]
    assert mine and not joins(mine[0])[1], f"{LETTERS[cp][0]} shaped as {mine}"


@pytest.mark.parametrize("text,want,gone", [
    ("ܪ̈", "uni072A.syame", "uni0308"),                   # Rish + syame
    ("ܖ̈", "uni072A.syame", "uni0308"),                   # Dotless Dalath Rish + syame
    ("ܒܪ̈", "uni072A.fina.syame", "uni0308"),        # joined Rish + syame
    ("ܪܵ̈", "uni072A.syame", "uni0308"),             # vowel typed in between
    ("ܒܪ̈ܵ", "uni072A.fina.syame", "uni0308"),  # vowel typed after
    ("ܪ", "uni072A", "uni072A.syame"),                         # plain Rish stays plain
    ("ܒܪ", "uni072A.fina", "uni072A.fina.syame"),
], ids=["isolated", "dotless", "final", "vowel-between", "vowel-after", "no-syame",
        "final-no-syame"])
def test_rish_syame(text, want, gone):
    """Rish followed by syame (U+0308) uses the Rish-with-syame glyph, whose
    dots replace both Rish's own dot and the syame. In 1.x a joined Rish got
    the isolated glyph, and a vowel in between left both dots showing."""
    names = [g for g, _, _ in shape(FONT.path, text)]
    assert want in names and gone not in names, f"got {names}"


@pytest.mark.parametrize("text,want", [
    ("\u072C\u0710", "uni072C0710"),                       # Taw Alaph
    ("\u0712\u072C\u0710", "uni072C0710.fina"),           # Taw joined to the letter before
    ("\u072C\u0735\u0710", "uni072C0710"),                # a vowel on the Taw in between
    ("\u0725\u0715\u072C\u0710", "uni072C0710"),         # ending a word: ܥܕܬܐ
    ("\u072C\u0710\u0712", "uni072C0710"),                # mid-word
    ("\u0720\u0710", "uni07200710"),                       # Lamadh Alaph
    ("\u0712\u0720\u0710", "uni07200710.fina"),           # Lamadh joined to the letter before
], ids=["taw-alaph", "taw-alaph-joined", "taw-vowel-between", "taw-word", "taw-mid-word",
        "lamadh-alaph", "lamadh-alaph-joined"])
def test_ligatures(text, want):
    """Taw–Alaph and Lamadh–Alaph are set as ligatures, joined or not.
    (Joined Taw–Alaph was drawn in 1.x but never used.)"""
    names = [g for g, _, _ in shape(FONT.path, text)]
    assert want in names and not any(n.startswith("uni0710") for n in names), f"got {names}"


@pytest.mark.parametrize("text", ["\u072C", "\u0710\u072C", "\u072C\u0712",
                                  "\u072C\u0715\u0710", "\u0720", "\u0710\u0720"],
                         ids=["taw", "alaph-taw", "taw-beth", "taw-dalath-alaph",
                              "lamadh", "alaph-lamadh"])
def test_no_ligature(text):
    """Only Taw or Lamadh directly followed by Alaph form a ligature."""
    names = [g for g, _, _ in shape(FONT.path, text)]
    assert not any(n.startswith(("uni072C0710", "uni07200710")) for n in names), f"got {names}"


def test_unjoined_alaph_keeps_clear_of_the_letter_before():
    """Alaph's arm reaches its own edge. Unjoined, it used to run 52 units
    past it and fuse with Waw, Dalath or Rish before it."""
    for text in ("\u0718\u0710", "\u0715\u0710", "\u072A\u0710", "\u0710\u0710"):
        run = shape(FONT.path, text)
        (alaph, ax, _), (before, bx, _) = run[0], run[1]
        reach = ax + FONT.glyph(alaph).bounds[2]
        start = bx + FONT.glyph(before).bounds[0]
        assert start - reach >= 40, f"{text}: {alaph} reaches {reach}, {before} starts at {start}"
