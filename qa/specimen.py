"""Renders the README images from the built font: plain black on white.

    python qa/specimen.py        writes documentation/<style>/*.svg

Text is shaped by HarfBuzz and written as the font's own outlines in SVG, so
the images are sharp at any size and on any screen, and look the same on every
machine without needing the font installed.
"""

import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LETTERS, ROOT, STYLE, Font, shape, signs  # noqa: E402
from texts import ALPHABET  # noqa: E402

DOCS = os.path.join(ROOT, "documentation", STYLE)
WIDTH = 1600          # width of the proof images, in pixels
MARGIN = 64
PAD = 48              # white space around a word image
PAPER = "#ffffff"
INK = "#000000"

# One image each, at different sizes.
WORDS = [
    ("ܢܘܗܕܪܐ", 260),
    ("ܨܦܢܐ", 260),
    ("ܐܡܕܝܐ", 260),
    ("ܥܠ ܐܪܥܐ ܫܠܡܐ ܘܣܒܪܐ ܛܒܐ ܠܒܪܢܫ̈ܐ", 110),
    ("ܥܲܠ ܐܲܪܥܵܐ ܫܠܵܡܵܐ ܘܣܲܒܪܵܐ ܛܵܒܵܐ ܠܒܲܪܢܵܫ̈ܐ", 110),
]


def width(font, run):
    """Width of a shaped line in font units: the last glyph's pen position
    plus its advance."""
    name, x, _ = run[-1]
    return x + font.glyph(name).width


def shaped(font, text):
    run = shape(font.path, text)
    if any(g == ".notdef" for g, _, _ in run):
        raise SystemExit(f"text needs a character the font does not have: {text}")
    return run


def glyph_path(font, name):
    """SVG path data for a glyph in font units (y up)."""
    if name not in _PATHS:
        pen = SVGPathPen(font.glyphset)
        font.glyphset[name].draw(pen)
        _PATHS[name] = pen.getCommands()
    return _PATHS[name]


_PATHS = {}


def run_svg(font, run, scale, x0, baseline):
    """<path> elements for a shaped run, placed in pixel coordinates."""
    out = []
    for name, gx, gy in run:
        if not font.glyph(name).polys:
            continue
        out.append(f'<path transform="translate({x0 + gx * scale:.2f} {baseline - gy * scale:.2f}) '
                   f'scale({scale:.4f} {-scale:.4f})" d="{glyph_path(font, name)}"/>')
    return out


def save(paths, w, h, path):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}">'
           f'<rect width="100%" height="100%" fill="{PAPER}"/>'
           f'<g fill="{INK}">{"".join(paths)}</g></svg>\n')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {os.path.relpath(path, ROOT)} ({w}x{h})")


def ink_box(font, run):
    """(left, bottom, right, top) of the ink of a shaped run, in font units."""
    boxes = [(x + b[0], y + b[1], x + b[2], y + b[3])
             for name, x, y in run for b in [font.glyph(name).bounds] if b]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def word_image(font, text, size, path):
    """`text` at `size` pixels per em, cropped to its ink plus PAD."""
    run = shaped(font, text)
    scale = size / 1000
    x0, y0, x1, y1 = ink_box(font, run)
    w = round((x1 - x0) * scale) + 2 * PAD
    h = round((y1 - y0) * scale) + 2 * PAD
    save(run_svg(font, run, scale, PAD - x0 * scale, PAD + y1 * scale), w, h, path)


class Page:
    """Right-to-left lines of text, wrapped to the page, top to bottom."""

    def __init__(self, font):
        self.font, self.lines, self.y = font, [], MARGIN

    def words(self, text, size, leading=1.9, gap=0, sep=" "):
        """Set `text` (a string, or a list of groups to keep whole) at `size`
        pixels per em, wrapping between words or groups, which are joined
        by `sep`."""
        scale = size / 1000
        room = (WIDTH - 2 * MARGIN) / scale
        items = text.split() if isinstance(text, str) else text
        lines, line = [], []
        for item in items:
            trial = sep.join(line + [item])
            if line and width(self.font, shaped(self.font, trial)) > room:
                lines.append(sep.join(line))
                line = [item]
            else:
                line.append(item)
        if line:
            lines.append(sep.join(line))
        for text_line in lines:
            run = shaped(self.font, text_line)
            self.y += size * 1.05
            x = WIDTH - MARGIN - width(self.font, run) * scale
            self.lines.append((run, scale, x, self.y))
            self.y += size * (leading - 1.05)
        self.y += gap

    def render(self, path):
        paths = []
        for run, scale, x, baseline in self.lines:
            paths += run_svg(self.font, run, scale, x, baseline)
        save(paths, WIDTH, int(self.y + MARGIN), path)


def main():
    font = Font()
    os.makedirs(DOCS, exist_ok=True)
    drawn = font.drawn_codepoints()
    dual = [chr(cp) for cp in drawn if LETTERS[cp][1] == "D"]
    right = [chr(cp) for cp in drawn if LETTERS[cp][1] == "R"]
    plain_signs, marks = signs(font)
    beth = "ܒ"
    ligatures = font.ligatures()

    for i, (text, size) in enumerate(WORDS, 1):
        word_image(font, text, size, os.path.join(DOCS, f"word-{i}.svg"))

    # The alphabet as one word, so every letter takes its connected form.
    word_image(font, ALPHABET, 120, os.path.join(DOCS, "alphabet.svg"))

    # Every character the font draws: letters, punctuation, marks.
    page = Page(font)
    page.words(" ".join(chr(cp) for cp in drawn), 110, gap=30)
    page.words(" ".join(plain_signs), 110, gap=30)
    page.words(" ".join(marks), 110, leading=2.2)
    page.render(os.path.join(DOCS, "proof-charset.svg"))

    # Every letter in each of its joined forms: isolated, initial, medial,
    # final (right-joining letters have only isolated and final). A
    # zero-width joiner on a side makes the letter join on that side.
    zwj = "\u200d"
    forms = []
    for cp in drawn:
        ch = chr(cp)
        joined = [ch + zwj, zwj + ch + zwj] if LETTERS[cp][1] == "D" else []
        forms.append(" ".join([ch] + joined + [zwj + ch]))
    # Ligatures: each drawn one, isolated then final.
    for first, second in ligatures:
        pair = chr(first) + chr(second)
        forms.append(pair + " " + zwj + pair)
    page = Page(font)
    page.words(forms, 100, leading=2.0, sep="     ")
    page.render(os.path.join(DOCS, "proof-forms.svg"))

    # Joining: each dual-joining letter between two Beths, then three in a
    # row; each right-joining letter after Beth.
    page = Page(font)
    page.words(" ".join(beth + c + beth for c in dual), 84, gap=30)
    page.words(" ".join(c * 3 for c in dual), 84, gap=30)
    page.words(" ".join([beth + c for c in right] +
                        [beth + chr(a) + chr(b) for a, b in ligatures]), 84)
    page.render(os.path.join(DOCS, "proof-joins.svg"))

    # Vowels and other marks, each on a dotted circle.
    page = Page(font)
    page.words(" ".join(marks), 140, leading=2.3)
    page.render(os.path.join(DOCS, "proof-vowels.svg"))


if __name__ == "__main__":
    main()
