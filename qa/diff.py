"""Draws what changed between two builds of the fonts: out/diff.html.

    python qa/diff.py --before out/before/v1.7 --label 1.7 fonts/NohadraSyriac-*.otf

`make diff` does this against the release named by BEFORE (a git tag or
commit). For each style the page shows, before, after and overlaid:

- the highlight texts from qa/texts.py, changed or not;
- every glyph whose outline or width changed, and every glyph added or removed;
- every pair of letters that shapes differently;
- every letter whose marks now sit somewhere else;
- every sample word that shapes differently.

Glyphs are compared by shape (the area where the two outlines differ), not by
their point data, so fonts exported by Glyphs and built by fontmake compare
cleanly. Changes of a unit or two (points snapped to the grid) are counted
apart from the rest and folded away, so the real changes stand out.
"""

import argparse
import collections
import html
import os
import sys

import pathops
from fontTools.pens.svgPathPen import SVGPathPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (FAMILY, LETTERS, ROOT, STYLES, Font, label, shape,  # noqa: E402
                    style_of)
from texts import DIFF_HIGHLIGHTS, PRAYER, VOWELLED_WORDS, WORDS  # noqa: E402

# Glyphs renamed between releases, as built: old name -> new name.
RENAMED = {
    "uni07200710.isol": "uni07200710",
    "uni072C0710.isol": "uni072C0710",
    "uni072A0308.isol": "uni072A.syame",
    "uni072A0308.fina": "uni072A.fina.syame",
}
ZWJ = "\u200d"
TINY = 2   # a difference no thicker than this, in font units, is grid cleanup


def esc(s):
    return html.escape(str(s))


class Side:
    """One font, before or after, and the glyphs the page draws from it."""

    def __init__(self, path, key):
        self.font, self.key, self.used = Font(path), key, set()
        self._paths, self._ops = {}, {}
        # Glyphs stores version 1.7 as revision 1.007: show it as major.minor.
        rev = self.font.tt["head"].fontRevision
        self.version = f"{int(rev)}.{round((rev - int(rev)) * 1000)}"

    def has(self, name):
        return name in self.font.glyphset

    def ops(self, name):
        if name not in self._ops:
            p = pathops.Path()
            self.font.glyphset[name].draw(p.getPen(glyphSet=self.font.glyphset))
            self._ops[name] = p
        return self._ops[name]

    def ref(self, name):
        self.used.add(name)
        return f"{self.key}-{name.replace('.', '_')}"

    def defs(self):
        out = []
        for name in sorted(self.used):
            pen = SVGPathPen(self.font.glyphset)
            self.font.glyphset[name].draw(pen)
            out.append(f'<path id="{self.ref(name)}" transform="scale(1,-1)" '
                       f'd="{pen.getCommands()}"/>')
        return "".join(out)


class Pair:
    """The same style before and after."""

    def __init__(self, before, after, style):
        self.style = style
        self.b = Side(before, f"{style[0].lower()}b")
        self.a = Side(after, f"{style[0].lower()}a")
        self._same = {}

    def glyph_change(self, bname, aname):
        """None if the two glyphs are the same (advance and shape, to within
        a square unit), "tiny" if they differ only by slivers at most TINY
        units thick, else "real"."""
        key = (bname, aname)
        if key not in self._same:
            bf, af = self.b.font, self.a.font
            xor = pathops.op(self.b.ops(bname), self.a.ops(aname), pathops.PathOp.XOR)
            slivers = thin(xor)
            if xor.area < 1 and bf.advance(bname) == af.advance(aname):
                self._same[key] = None
            elif slivers and abs(bf.advance(bname) - af.advance(aname)) <= TINY:
                self._same[key] = "tiny"
            else:
                self._same[key] = "real"
        return self._same[key]

    def run_change(self, brun, arun):
        """None, "tiny" or "real", as for glyphs, for two shaped runs: what
        you see, so a change hidden under the next letter's stroke is no
        change. The runs are lined up on the right, where Syriac starts."""
        shift = width(self.a, arun) - width(self.b, brun)
        xor = pathops.op(ink(self.b, brun, shift), ink(self.a, arun), pathops.PathOp.XOR)
        if xor.area < 1 and not shift:
            return None
        slivers = thin(xor)
        return "tiny" if slivers and abs(shift) <= TINY else "real"

    def shape(self, text):
        return shape(self.b.font.path, text), shape(self.a.font.path, text)


def thin(xor):
    """Whether every piece of a difference is a sliver no more than TINY
    units thick on average (its area over its length), straight or curved."""
    for c in xor.contours:
        p = pathops.Path()
        c.draw(p.getPen())
        x0, y0, x1, y1 = c.bounds
        if abs(p.area) / max(x1 - x0, y1 - y0, 1) > TINY:
            return False
    return True


def ink(side, run, dx=0):
    """The ink of a shaped run as one outline."""
    out = pathops.Path()
    for name, x, y in run:
        moved = side.ops(name).transform(1, 0, 0, 1, x + dx, y)
        out = pathops.op(out, moved, pathops.PathOp.UNION)
    return out


# --- drawing -------------------------------------------------------------------

def extent(side, run):
    """(left, bottom, right, top) of a run's ink and advances, in font units."""
    xs, ys = [0], [0]
    for name, x, y in run:
        g = side.font.glyph(name)
        xs += [x, x + side.font.advance(name)]
        if g.bounds:
            xs += [x + g.bounds[0], x + g.bounds[2]]
            ys += [y + g.bounds[1], y + g.bounds[3]]
    return min(xs), min(ys), max(xs), max(ys)


def width(side, run):
    return max([x + side.font.advance(g) for g, x, _ in run] + [0])


def svg(layers, height, edges=()):
    """One drawing: `layers` are (side, run, css class, x offset), drawn in
    order; `edges` are (x, css class) advance lines."""
    boxes = [extent(side, run) for side, run, _, _ in layers]
    offs = [dx for _, _, _, dx in layers]
    x0 = min(b[0] + dx for b, dx in zip(boxes, offs)) - 60
    x1 = max(b[2] + dx for b, dx in zip(boxes, offs)) + 60
    y0 = min(min(b[1] for b in boxes), -250) - 30
    y1 = max(max(b[3] for b in boxes), 560) + 40
    parts = [f'<line class="base" x1="{x0}" x2="{x1}" y1="0" y2="0"/>']
    for x, cls in edges:
        parts.append(f'<line class="{cls}" x1="{x}" x2="{x}" y1="{-y1}" y2="{-y0}"/>')
    for side, run, cls, dx in layers:
        uses = "".join(f'<use href="#{side.ref(g)}" x="{x + dx}" y="{-y}"/>'
                       for g, x, y in run if side.font.glyph(g).polys)
        parts.append(f'<g class="{cls}">{uses}</g>')
    w = height * (x1 - x0) / (y1 - y0)
    return (f'<svg viewBox="{x0} {-y1} {x1 - x0} {y1 - y0}" width="{w:.0f}" '
            f'height="{height}" role="img">{"".join(parts)}</svg>')


def trio(p, brun, arun, height):
    """Before, after, and the two overlaid, lined up on the right edge where
    Syriac text starts."""
    shift = width(p.a, arun) - width(p.b, brun)
    return (f'<figure class="v b"><figcaption>{esc(p.b.version)}</figcaption>'
            f'{svg([(p.b, brun, "before", 0)], height)}</figure>'
            f'<figure class="v a"><figcaption>{esc(p.a.version)}</figcaption>'
            f'{svg([(p.a, arun, "after", 0)], height)}</figure>'
            f'<figure class="v o"><figcaption>overlaid</figcaption>'
            f'{svg([(p.b, brun, "before ghost", shift), (p.a, arun, "after ghost", 0)], height)}'
            f'</figure>')


def chip(change):
    return {"real": '<span class="chip changed">changed</span>',
            "tiny": '<span class="chip tiny">1–2 units</span>',
            None: '<span class="chip same">unchanged</span>'}[change]


# --- sections ------------------------------------------------------------------

def highlights(p):
    rows = []
    for text, note in DIFF_HIGHLIGHTS:
        brun, arun = p.shape(text)
        changed = p.run_change(brun, arun)
        rows.append(f'<article class="case"><header><p class="syr" lang="syr" dir="rtl">'
                    f'{esc(text)}</p>{chip(changed)}</header><p class="note">{esc(note)}</p>'
                    f'<div class="trio">{trio(p, brun, arun, 120)}</div></article>')
    return "".join(rows)


def glyphs(p):
    """Cards for every glyph that changed, was added or was removed."""
    bnames, anames = set(p.b.font.tt.getGlyphOrder()), p.a.font.tt.getGlyphOrder()
    back = {v: k for k, v in RENAMED.items()}
    groups = collections.defaultdict(list)
    matched = set()
    for a in anames:
        b = back.get(a, a)
        kind = "mark" if p.a.font.is_mark(a) else \
            "letter" if a.startswith("uni07") and not p.a.font.is_mark(a) else "other"
        if b not in bnames:
            groups[kind].append((None, a, "added"))
            continue
        matched.add(b)
        change = p.glyph_change(b, a)
        if not change:
            continue
        if change == "tiny":
            kind = "tiny"
        notes = []
        if b != a:
            notes.append(f"renamed from {b}")
        bw, aw = p.b.font.glyph(b).width, p.a.font.glyph(a).width
        if bw != aw:
            notes.append(f"width {bw} → {aw}")
        area = pathops.op(p.b.ops(b), p.a.ops(a), pathops.PathOp.XOR).area
        if area >= 1:
            notes.append(f"outline changed ({area:,.0f} units²)" if p.a.font.glyph(a).polys
                         else "now draws nothing")
        groups[kind].append((b, a, "; ".join(notes)))
    for b in sorted(bnames - matched):
        groups["other"].append((b, None, "removed"))

    out, total, tiny = [], 0, 0
    for kind, title in (("letter", "Letters"), ("mark", "Marks"), ("other", "Other glyphs"),
                        ("tiny", "Points snapped to the grid (1–2 units)")):
        cards = []
        for b, a, note in groups[kind]:
            name = a or b
            edges = []
            if b:
                edges.append((p.b.font.advance(b), "edge before"))
            if a:
                edges.append((p.a.font.advance(a), "edge after"))
            layers = ([(p.b, [(b, 0, 0)], "before ghost", 0)] if b else []) + \
                ([(p.a, [(a, 0, 0)], "after ghost", 0)] if a else [])
            cards.append(f'<article class="glyph"><div class="pic">{svg(layers, 150, edges)}'
                         f'</div><h4>{esc(label(name))}</h4><code>{esc(name)}</code>'
                         f'<p>{esc(note)}</p></article>')
        if kind == "tiny":
            tiny = len(cards)
            if cards:
                out.append(f'<details><summary><h3>{title} <span class="count">{len(cards)}'
                           f'</span></h3></summary><div class="glyphs">{"".join(cards)}</div>'
                           f'</details>')
            continue
        total += len(cards)
        if cards:
            out.append(f'<h3>{title} <span class="count">{len(cards)}</span></h3>'
                       f'<div class="glyphs">{"".join(cards)}</div>')
    return "".join(out) or "<p class='none'>No glyph changed.</p>", total, tiny


def pairs(p):
    """Every two letters, the first joining forward, and every letter before
    Alaph: drawn overlaid where they shape differently."""
    drawn = p.a.font.drawn_codepoints()
    texts = [chr(a) + chr(b) for a in drawn if LETTERS[a][1] == "D" for b in drawn]
    texts += [chr(a) + "\u0710" for a in drawn if LETTERS[a][1] == "R"]
    cells = {"real": [], "tiny": []}
    for text in texts:
        brun, arun = p.shape(text)
        change = p.run_change(brun, arun)
        if change:
            shift = width(p.a, arun) - width(p.b, brun)
            cells[change].append(f'<figure class="cell"><figcaption class="syr" lang="syr" dir="rtl">'
                         f'{esc(text)}</figcaption>'
                         f'{svg([(p.b, brun, "before ghost", shift), (p.a, arun, "after ghost", 0)], 90)}'
                         f'</figure>')
    return cells, len(texts)


def marks(p):
    """Every letter, in every form, whose marks now sit somewhere else: drawn
    with the mark that moved the most, on each side."""
    drawn = p.a.font.drawn_codepoints()
    mark_chars = [chr(cp) for cp, g in sorted(p.a.font.cmap.items())
                  if p.a.font.is_mark(g) and p.a.font.glyph(g).polys]
    moved = {}
    for cp in drawn:
        c = chr(cp)
        forms = [c, ZWJ + c] + ([c + ZWJ, ZWJ + c + ZWJ] if LETTERS[cp][1] == "D" else [])
        for form in forms:
            for m in mark_chars:
                text = form.replace(c, c + m)
                brun, arun = p.shape(text)
                bpos, apos = mark_offset(p.b.font, brun), mark_offset(p.a.font, arun)
                if not bpos or not apos or bpos[1:] == apos[1:]:
                    continue
                base, side = apos[0], "above" if apos[3] > 0 else "below"
                dist = abs(bpos[1] - apos[1]) + abs(bpos[2] - apos[2])
                if dist and dist > moved.get((base, side), (0,))[0]:
                    moved[base, side] = (dist, text, brun, arun)
    cards = []
    for (base, side), (dist, text, brun, arun) in sorted(moved.items()):
        cards.append(f'<article class="case small"><header><p class="syr" lang="syr" dir="rtl">'
                     f'{esc(text.replace(ZWJ, ""))}</p><span class="chip changed">{esc(side)}'
                     f'</span></header><p class="note">{esc(label(base))}: marks {esc(side)} '
                     f'moved, this one by {dist:.0f} units</p>'
                     f'<div class="trio">{trio(p, brun, arun, 110)}</div></article>')
    return cards


def mark_offset(font, run):
    """(letter, x, y, height) of the first mark in a run relative to its
    letter, or None."""
    letters = [(g, x, y) for g, x, y in run if not font.is_mark(g) and font.glyph(g).polys]
    ms = [(g, x, y) for g, x, y in run if font.is_mark(g) and font.glyph(g).polys]
    if len(letters) != 1 or not ms:
        return None
    (lg, lx, ly), (mg, mx, my) = letters[0], ms[0]
    b = font.glyph(mg).bounds
    return lg, mx - lx, my - ly, my + (b[1] + b[3]) / 2


def words(p):
    texts = WORDS + VOWELLED_WORDS + [" ".join(PRAYER.split()[i:i + 4])
                                      for i in range(0, len(PRAYER.split()), 4)]
    rows = {"real": [], "tiny": []}
    for text in texts:
        brun, arun = p.shape(text)
        change = p.run_change(brun, arun)
        if change:
            rows[change].append(f'<article class="case"><header><p class="syr" lang="syr" dir="rtl">'
                        f'{esc(text)}</p></header><div class="trio">{trio(p, brun, arun, 100)}'
                        f'</div></article>')
    return rows, len(texts)


# --- page ----------------------------------------------------------------------

def build(p):
    hl = highlights(p)
    glyph_html, nglyphs, ntiny = glyphs(p)
    pair_cells, npairs = pairs(p)
    mark_cards = marks(p)
    word_rows, nwords = words(p)
    stats = [(nglyphs, f"glyphs changed, added or removed, and {ntiny} snapped by a unit or two"),
             (len(pair_cells["real"]), f"of {npairs} letter pairs shape differently, and "
                                       f"{len(pair_cells['tiny'])} by a unit or two"),
             (len(mark_cards), "letter forms place marks differently"),
             (len(word_rows["real"]), f"of {nwords} sample texts change, and "
                                      f"{len(word_rows['tiny'])} by a unit or two")]

    def folded(items, what):
        return (f'<details><summary>{len(items)} {what} differ by only a unit or two</summary>'
                f'<div class="{"cells" if what == "pairs" else "cases"}">{"".join(items)}</div>'
                f'</details>') if items else ""
    body = (
        f'<section class="style" id="{p.style.lower()}" data-style="{p.style}">'
        f'<div class="stats">{"".join(f"<div><b>{n}</b><span>{esc(t)}</span></div>" for n, t in stats)}</div>'
        f'<h2 id="{p.style.lower()}-highlights">Things to look at</h2>'
        f'<p class="lede">The places a release most often changes, drawn whether or not they did.</p>'
        f'<div class="cases">{hl}</div>'
        f'<h2 id="{p.style.lower()}-glyphs">Glyphs</h2>'
        f'<p class="lede">Each glyph overlaid on the {esc(p.b.version)} version. Dashed lines are '
        f'the advance widths.</p>{glyph_html}'
        f'<h2 id="{p.style.lower()}-pairs">Letter pairs</h2>'
        f'<p class="lede">Every pair of letters that shapes differently, overlaid. Pairs are '
        f'aligned on the right, where the text starts.</p>'
        f'<div class="cells">{"".join(pair_cells["real"]) or "<p class=none>None.</p>"}</div>'
        f'{folded(pair_cells["tiny"], "pairs")}'
        f'<h2 id="{p.style.lower()}-marks">Marks</h2>'
        f'<p class="lede">Each letter form whose vowels or marks moved, shown with the mark that '
        f'moved the most.</p>'
        f'<div class="cases">{"".join(mark_cards) or "<p class=none>None.</p>"}</div>'
        f'<h2 id="{p.style.lower()}-words">Sample text</h2>'
        f'<div class="cases">{"".join(word_rows["real"]) or "<p class=none>None.</p>"}</div>'
        f'{folded(word_rows["tiny"], "texts")}'
        f'</section>')
    return body, p.b.defs() + p.a.defs()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--before", required=True, help="folder with the earlier fonts")
    ap.add_argument("--label", default="before", help="name of the earlier release")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "diff.html"))
    ap.add_argument("fonts", nargs="+")
    args = ap.parse_args()

    sections, defs, tabs, versions = [], [], [], set()
    for path in sorted(args.fonts, key=lambda f: STYLES.index(style_of(f))):
        style = style_of(path)
        before = os.path.join(args.before, os.path.basename(path))
        p = Pair(before, path, style)
        versions.add((p.b.version, p.a.version))
        body, d = build(p)
        sections.append(body)
        defs.append(d)
        tabs.append(style)
        print(f"{style}: compared {before} with {path}")
    (bv, av), = versions
    title = f"{FAMILY} {bv} to {av}"
    page = TEMPLATE.format(
        title=esc(title), before=esc(bv), after=esc(av), label=esc(args.label),
        tabs="".join(f'<button type="button" id="tab-{s.lower()}" data-show="{s}" '
                     f'aria-pressed="{str(i == 0).lower()}">{s}</button>'
                     for i, s in enumerate(tabs)),
        sections="".join(sections), defs="".join(defs))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {os.path.relpath(args.out)} ({os.path.getsize(args.out) / 1e6:.1f} MB)")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Public+Sans:wght@400;600&family=JetBrains+Mono:wght@400&family=Noto+Sans+Syriac+Eastern&display=swap">
<style>
/* Layout: a proofing sheet. One column of before / after / overlaid strips,
   switched between the two styles; glyphs and pairs as dense grids. */
:root {{
  --paper: #fbfaf7; --ink: #1b1d22; --muted: #646872; --rule: #e3e1db; --card: #ffffff;
  --before: #c8462c; --after: #2456b8; --same: #4f7a55;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --body: "Public Sans", system-ui, -apple-system, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
  --syriac: "Noto Sans Syriac Eastern", "Noto Sans Syriac", serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #15171b; --ink: #e8e6e1; --muted: #9a9ea8; --rule: #2c2f36; --card: #1c1f24;
  --before: #ff7d61; --after: #74a6ff; --same: #8cc795; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --paper: #15171b; --ink: #e8e6e1; --muted: #9a9ea8; --rule: #2c2f36; --card: #1c1f24;
  --before: #ff7d61; --after: #74a6ff; --same: #8cc795; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink);
  font: 15px/1.55 var(--body); }}
main {{ max-width: 1240px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 80px; }}
h1, h2, h3 {{ font-family: var(--display); font-stretch: 80%; text-wrap: balance; }}
h1 {{ font-size: clamp(30px, 5vw, 46px); line-height: 1.05; margin: 0 0 10px; font-weight: 800; }}
h2 {{ font-size: 24px; margin: 44px 0 6px; padding-top: 14px; border-top: 2px solid var(--ink); }}
h3 {{ font-size: 17px; margin: 22px 0 10px; }}
.count {{ font: 13px var(--mono); color: var(--muted); font-stretch: normal; }}
.lede, .intro {{ max-width: 68ch; color: var(--muted); margin: 0 0 14px; }}
.intro {{ color: var(--ink); }}
.key {{ display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 14px 0 0; color: var(--muted);
  font-size: 13px; }}
.key span {{ display: inline-flex; align-items: center; gap: 7px; }}
.key i {{ width: 18px; height: 12px; border-radius: 2px; display: inline-block; }}
.bar {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 2; background: var(--paper);
  display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center;
  padding-block: 10px; border-bottom: 1px solid var(--rule); margin-top: 22px; }}
.tabs {{ display: inline-flex; border: 1px solid var(--ink); border-radius: 6px; overflow: hidden; }}
.tabs button {{ font: 600 14px var(--body); padding: 6px 16px; border: 0; background: transparent;
  color: var(--ink); cursor: pointer; }}
.tabs button[aria-pressed="true"] {{ background: var(--ink); color: var(--paper); }}
.tabs button:focus-visible {{ outline: 3px solid var(--after); outline-offset: -3px; }}
.jump {{ display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13px; }}
.jump a {{ color: var(--muted); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: 1px; background: var(--rule); border: 1px solid var(--rule); margin-top: 24px; }}
.stats div {{ background: var(--paper); padding: 12px 14px; }}
.stats b {{ display: block; font: 800 30px/1 var(--display); font-variant-numeric: tabular-nums; }}
.stats span {{ font-size: 13px; color: var(--muted); }}
.cases {{ display: grid; gap: 12px; }}
.case {{ background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
  padding: 12px 14px; min-width: 0; }}
.case header {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
.case .syr {{ font: 26px/1.4 var(--syriac); margin: 0; }}
.case.small .syr {{ font-size: 22px; }}
.note {{ margin: 2px 0 8px; color: var(--muted); max-width: 70ch; }}
.chip {{ font: 600 11px var(--body); letter-spacing: .06em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 99px; border: 1px solid currentColor; white-space: nowrap; }}
.chip.changed {{ color: var(--before); }} .chip.same {{ color: var(--same); }}
.chip.tiny {{ color: var(--muted); }}
details {{ margin-top: 12px; }}
summary {{ cursor: pointer; color: var(--muted); }}
summary h3 {{ display: inline; }}
details > .glyphs, details > .cells, details > .cases {{ margin-top: 10px; }}
.trio {{ display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: flex-end; overflow-x: auto; }}
figure {{ margin: 0; min-width: 0; }}
figcaption {{ font: 12px var(--mono); color: var(--muted); }}
.v.b figcaption {{ color: var(--before); }} .v.a figcaption {{ color: var(--after); }}
svg {{ display: block; max-width: 100%; height: auto; }}
.glyphs {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 190px), 1fr));
  gap: 10px; }}
.glyph {{ background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
  padding: 10px; min-width: 0; }}
.glyph .pic svg {{ margin: 0 auto; }}
.glyph h4 {{ margin: 8px 0 0; font: 600 13px var(--body); }}
.glyph code {{ font: 11px var(--mono); color: var(--muted); overflow-wrap: anywhere; }}
.glyph p {{ margin: 4px 0 0; font-size: 12px; color: var(--muted); }}
.cells {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 150px), 1fr));
  gap: 8px; }}
.cell {{ background: var(--card); border: 1px solid var(--rule); border-radius: 6px; padding: 6px; }}
.cell figcaption {{ font: 18px var(--syriac); color: var(--ink); text-align: right; }}
.none {{ color: var(--muted); }}
.defs {{ position: absolute; width: 0; height: 0; overflow: hidden; }}
line.base {{ stroke: var(--rule); stroke-width: 4; }}
line.edge {{ stroke-width: 3; stroke-dasharray: 14 10; }}
line.edge.before {{ stroke: var(--before); }} line.edge.after {{ stroke: var(--after); }}
g.before {{ fill: var(--before); }} g.after {{ fill: var(--after); }}
g.ghost {{ fill-opacity: .5; }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style></head>
<body><main>
<h1>{title}</h1>
<p class="intro">What changed in the fonts between {label} and this build, {after}. Everything here is drawn from the fonts themselves, shaped by HarfBuzz the way
applications shape them.</p>
<div class="key"><span><i style="background:var(--before)"></i>{before}</span>
<span><i style="background:var(--after)"></i>{after}</span>
<span><i style="background:linear-gradient(90deg,var(--before),var(--after))"></i>overlaid: where they agree the colors mix</span></div>
<div class="bar"><div class="tabs" role="group" aria-label="Style">{tabs}</div>
<nav class="jump" id="jump"></nav></div>
{sections}
</main>
<svg class="defs" aria-hidden="true"><defs>{defs}</defs></svg>
<script>
(function () {{
  var sections = document.querySelectorAll("section.style");
  var buttons = document.querySelectorAll(".tabs button");
  var jump = document.getElementById("jump");
  function show(style) {{
    sections.forEach(function (s) {{ s.hidden = s.dataset.style !== style; }});
    buttons.forEach(function (b) {{ b.setAttribute("aria-pressed", String(b.dataset.show === style)); }});
    var id = style.toLowerCase();
    jump.innerHTML = [["highlights", "Things to look at"], ["glyphs", "Glyphs"], ["pairs", "Pairs"],
      ["marks", "Marks"], ["words", "Text"]].map(function (s) {{
        return '<a href="#' + id + '-' + s[0] + '">' + s[1] + '</a>'; }}).join("");
  }}
  buttons.forEach(function (b) {{ b.addEventListener("click", function () {{ show(b.dataset.show); }}); }});
  var start = (location.hash || "").replace("#", "").split("-")[0];
  var match = Array.prototype.find.call(buttons, function (b) {{ return b.dataset.show.toLowerCase() === start; }});
  show(match ? match.dataset.show : buttons[0].dataset.show);
}})();
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
