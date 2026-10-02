"""Builds out/proof.html: a proof sheet for checking the letters and joins.

Everything drawn in SVG is the built font's outlines placed by HarfBuzz, with
guide lines and the problems from out/qa.json circled. The live-text section
at the end uses the browser's own shaper, which is what applications do.
"""

import collections
import html
import json
import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (FAMILY, FONT, FORM_NAMES, STYLE, LETTERS, MARK_GAP, MARK_TOUCH, OUT,  # noqa: E402
                    Font, bases_for, clearance, components, drawn_marks, joins, label,
                    load_anchors, mark_collisions, place_mark, seams, shape,
                    signs, split_name, spots)
from texts import (ALPHABET, PRAYER, PUNCTUATED, VOWELLED_PRAYER,  # noqa: E402
                   VOWELLED_WORDS, WORDS)

class Drawing:
    """Accumulates glyph uses and guides for one SVG, in font units."""

    def __init__(self, font, qa, lo, hi):
        self.font, self.qa, self.lo, self.hi = font, qa, lo, hi
        self.parts, self.marks, self.x0, self.x1 = [], [], 0, 0

    def run(self, run, x=0, edges=False):
        for name, gx, gy in run:
            w = self.font.glyph(name).width if name in self.font.glyphset else 0
            self.parts.append(f'<use href="#{gid(name)}" x="{x + gx}" y="{-gy}"/>')
            if edges and split_name(name):
                for ex in (x + gx, x + gx + w):
                    self.parts.append(
                        f'<line class="edge" x1="{ex}" x2="{ex}" y1="{-self.hi}" y2="{-self.lo}"/>')
            b = self.font.glyph(name).bounds if name in self.font.glyphset else None
            self.x0 = min(self.x0, x + gx + (b[0] if b else 0))
            self.x1 = max(self.x1, x + gx + max(w, b[2] if b else 0))
        return self

    def mark(self, x, y, cls="bad"):
        self.marks.append(f'<circle class="{cls}" cx="{x}" cy="{-y}" r="34"/>')
        return self

    def svg(self, height, pad=60):
        x0, x1 = self.x0 - pad, self.x1 + pad
        bottom, top = self.qa["bar"]
        guides = []
        for y in sorted(set(self.qa["levels"]) | {bottom, top}):
            cls = "base" if y in (bottom, top) else "level"
            guides.append(f'<line class="{cls}" x1="{x0}" x2="{x1}" y1="{-y}" y2="{-y}"/>')
        vb = f"{x0} {-self.hi} {x1 - x0} {self.hi - self.lo}"
        w = height * (x1 - x0) / (self.hi - self.lo)
        return (f'<svg viewBox="{vb}" width="{w:.0f}" height="{height}">'
                f'{"".join(guides)}<g class="ink">{"".join(self.parts)}</g>'
                f'{"".join(self.marks)}</svg>')


def gid(name):
    return "g-" + name.replace(".", "_")


def defs(font, names):
    out = []
    for name in sorted(names):
        pen = SVGPathPen(font.glyphset)
        font.glyphset[name].draw(pen)
        # Flip y here so every <use> can work in screen coordinates.
        out.append(f'<path id="{gid(name)}" transform="scale(1,-1)" d="{pen.getCommands()}"/>')
    return f'<svg class="defs" aria-hidden="true"><defs>{"".join(out)}</defs></svg>'


def esc(s):
    return html.escape(str(s))


def chunks(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def main():
    font = Font()
    qa_path = os.path.join(OUT, "qa.json")
    if not os.path.exists(qa_path):
        raise SystemExit("out/qa.json not found - run `make qa` first")
    qa = json.load(open(qa_path, encoding="utf-8"))
    bar = tuple(qa["bar"])
    letters = font.letters()
    anchors = load_anchors()
    marks = drawn_marks(font, anchors)
    # Tall enough for the highest letter with a mark on it, and the lowest.
    tops = [anchors[g][a][1] for g in letters for a in spots(anchors, g, "top")]
    bottoms = [anchors[g][a][1] for g in letters for a in spots(anchors, g, "bottom")]
    above = [font.glyph(m).bounds[3] - anchors[m]["_top"][1]
             for m, (side, _) in marks.items() if side == "top"]
    below = [font.glyph(m).bounds[1] - anchors[m]["_bottom"][1]
             for m, (side, _) in marks.items() if side == "bottom"]
    lo = min([font.glyph(g).bounds[1] for g in letters] +
             ([min(bottoms) + min(below)] if below else [])) - 60
    hi = max([font.glyph(g).bounds[3] for g in letters] +
             ([max(tops) + max(above)] if above else [])) + 60
    used = set(letters) | set(marks)

    def drawing():
        return Drawing(font, qa, lo, hi)

    # ---- problems, one card per glyph --------------------------------------
    by_glyph = collections.defaultdict(list)
    notes = []
    for item in qa["items"]:
        if item["glyph"] == "*":
            notes.append(item)
        else:
            by_glyph[item["glyph"]].append(item)
    order = {"error": 0, "warning": 1, "info": 2}   # most serious first
    partner_right = "uni0712.init"   # Beth, joins on its left
    partner_left = "uni0712.fina"    # Beth, joins on its right
    cards = []
    for g in sorted(by_glyph, key=lambda g: (min(order[i["severity"]] for i in by_glyph[g]),
                                               split_name(g) or (0, g))):
        items = sorted(by_glyph[g], key=lambda i: order[i["severity"]])
        worst = items[0]["severity"]
        pics = ""
        if g in font.glyphset and font.glyph(g).polys:
            d = drawing().run([(g, 0, 0)], edges=True)
            for i in items:
                if i["x"] is not None:
                    d.mark(i["x"], i["y"], "bad" if i["severity"] == "error" else "warn")
            pics = d.svg(220)
            r, l = joins(g) if split_name(g) else (False, False)
            if r or l:
                run, x = [], 0
                if l:
                    run.append((partner_left, x, 0))
                    x += font.glyph(partner_left).width
                run.append((g, x, 0))
                x += font.glyph(g).width
                if r:
                    run.append((partner_right, x, 0))
                ctx = drawing().run(run)
                for s in seams(font, run, bar):
                    for y, _ in s["problems"]:
                        ctx.mark(s["x"], y)
                pics += ctx.svg(220)
        rows = "".join(
            f'<li class="{i["severity"]}"><b>{esc(i["check"])}</b> {esc(i["message"])}</li>'
            for i in items)
        cards.append(f'<article class="card {worst}"><h3>{esc(label(g))} '
                     f'<code>{esc(g)}</code></h3><div class="pics">{pics}</div>'
                     f'<ul>{rows}</ul></article>')

    counts = collections.Counter(i["severity"] for i in qa["items"])

    # ---- every letter in every form ---------------------------------------
    form_rows = []
    for cp, (name, jt) in LETTERS.items():
        base = font.cmap.get(cp)
        if not base or not font.glyph(base).polys:
            continue
        forms = ["", "init", "medi", "fina"] if jt == "D" else ["", "fina"]
        if cp == 0x0710:
            forms += ["med2", "fin2", "fin3"]
        cells = []
        for form in ["", "init", "medi", "fina", "med2", "fin2", "fin3"]:
            g = base + (f".{form}" if form else "")
            if form in forms and g in font.glyphset:
                cells.append(f'<td>{drawing().run([(g, 0, 0)], edges=True).svg(120)}'
                             f'<small>{esc(g)}</small></td>')
            else:
                cells.append("<td></td>")
        form_rows.append(f"<tr><th>{esc(name)}<br><span class=syr>{chr(cp)}</span></th>"
                         f"{''.join(cells)}</tr>")
    for g in [g for g in letters if len(components(g)) > 1 and not split_name(g)[1]]:
        cells = []
        for form in ["", "init", "medi", "fina", "med2", "fin2", "fin3"]:
            name = g + (f".{form}" if form else "")
            cells.append(f'<td>{drawing().run([(name, 0, 0)], edges=True).svg(120)}'
                         f'<small>{esc(name)}</small></td>' if name in font.glyphset else "<td></td>")
        text = "".join(chr(c) for c in components(g))
        form_rows.append(f"<tr><th>{esc(label(g).rsplit(' ', 1)[0])}<br>"
                         f"<span class=syr>{text}</span></th>{''.join(cells)}</tr>")

    # ---- every joining pair ------------------------------------------------
    drawn = font.drawn_codepoints()
    firsts = [cp for cp in drawn if LETTERS[cp][1] == "D"]
    bad_pairs = []
    head = "".join(f"<th class=syr>{chr(cp)}</th>" for cp in drawn)
    matrix = []
    for a in firsts:
        cells = []
        for b in drawn:
            run = shape(font.path, chr(a) + chr(b))
            used.update(g for g, _, _ in run)
            d = drawing().run(run)
            problems = []
            for s in seams(font, run, bar):
                for y, message in s["problems"]:
                    d.mark(s["x"], y)
                    problems.append((y, message))
            if problems:
                bad_pairs.append((a, b, problems))
            title = f"{LETTERS[a][0]} + {LETTERS[b][0]}" + \
                "".join(f"\n{m}" for _, m in problems)
            cells.append(f'<td class="{"bad" if problems else ""}" title="{esc(title)}">'
                         f'{d.svg(64, pad=40)}</td>')
        matrix.append(f"<tr><th class=syr>{chr(a)}</th>{''.join(cells)}</tr>")

    # ---- every mark on every letter ----------------------------------------
    order_marks = sorted(marks, key=lambda m: (marks[m][0] != "top", m))
    mark_head = "".join(f"<th>{esc(m)}</th>" for m in order_marks)
    mark_rows, mark_bad = [], 0
    for g in letters:
        cells = []
        for m in order_marks:
            if g not in bases_for(m, letters):
                cells.append("<td></td>")
                continue
            places = spots(anchors, g, marks[m][0])
            if not places:
                cells.append('<td class="bad" title="no anchor">–</td>')
                mark_bad += 1
                continue
            # One copy of the mark on each letter (two on a ligature).
            run, gaps = [(g, 0, 0)], []
            for spot in places:
                x, y = place_mark(anchors, g, m, marks[m], spot)
                run.append((m, x, y))
                gaps.append(clearance(font.glyph(m), x, y, font.glyph(g), 0, 0))
            known = [d for d in gaps if d is not None]
            d = min(known) if known else None
            cls = "bad" if d is not None and d < MARK_TOUCH else \
                "warn" if d is not None and d < MARK_GAP else ""
            mark_bad += cls == "bad"
            title = f"{label(g)} + {m}: " + ("clear" if d is None else f"{d:.0f} units apart")
            cells.append(f'<td class="{cls}" title="{esc(title)}">'
                         f'{drawing().run(run).svg(70, pad=30)}</td>')
        mark_rows.append(f"<tr><th>{esc(label(g))}<br><small>{esc(g)}</small></th>"
                         f"{''.join(cells)}</tr>")

    # ---- words, with any bad joints or colliding marks circled --------------
    def words_svg(text, height):
        run = shape(font.path, text)
        used.update(g for g, _, _ in run)
        d = drawing().run(run)
        for s in seams(font, run, bar):
            for y, _ in s["problems"]:
                d.mark(s["x"], y)
        for m, mx, my, _, dist in mark_collisions(font, run):
            if dist < MARK_GAP:
                b = font.glyph(m).bounds
                d.mark(mx + (b[0] + b[2]) / 2, my + (b[1] + b[3]) / 2,
                       "bad" if dist < MARK_TOUCH else "warn")
        return d.svg(height, pad=80)

    word_svgs = "".join(f"<figure>{words_svg(w, 90)}</figure>" for w in WORDS)
    stress = "".join(f"<figure>{words_svg(chr(0x0712) + chr(cp) + chr(0x0712), 90)}</figure>"
                     for cp in firsts) + \
        "".join(f"<figure>{words_svg(chr(cp) * 3, 90)}</figure>" for cp in firsts)

    vowelled = "".join(f"<figure>{words_svg(w, 110)}</figure>" for w in VOWELLED_WORDS)
    plain_signs, mark_signs = signs(font)
    sign_svgs = "".join(f"<figure>{words_svg(t, 110)}<small>U+{ord(t[-1]):04X}</small></figure>"
                        for t in plain_signs + mark_signs)
    punctuated = "".join(f"<div>{words_svg(' '.join(line), 130)}</div>"
                         for line in chunks(PUNCTUATED.split(), 5))
    vowelled_big = "".join(f"<div>{words_svg(' '.join(line), 150)}</div>"
                           for line in chunks(VOWELLED_PRAYER.split(), 5))
    # Marks beside every letter: the neighbour collisions the QA found.
    neighbour = "".join(f"<figure>{words_svg(i['example'], 110)}</figure>"
                        for i in qa["items"] if i["check"] == "mark-neighbour")

    waterfall = "".join(f'<p class="syr live" style="font-size:{s}px">'
                        f'<span class="size">{s}px</span>{esc(PRAYER[:90])}</p>'
                        for s in (12, 14, 18, 24, 36, 48, 72))

    font_url = os.path.relpath(FONT, OUT)
    page = TEMPLATE.format(
        family=FAMILY, style=STYLE,
        font_url=font_url, defs=defs(font, used & set(font.glyphset.keys())),
        bar=f"{bar[0]}–{bar[1]}", levels=", ".join(str(v) for v in qa["levels"]),
        errors=counts["error"], warnings=counts["warning"], infos=counts["info"],
        pairs=len(bad_pairs), total_pairs=len(firsts) * len(drawn),
        cards="".join(cards) or "<p>No problems found.</p>",
        notes="".join(f'<li class="{i["severity"]}"><b>{esc(i["check"])}</b> '
                      f'{esc(i["message"])}</li>' for i in notes),
        form_head="".join(f"<th>{FORM_NAMES[f]}</th>"
                          for f in ["", "init", "medi", "fina", "med2", "fin2", "fin3"]),
        forms="".join(form_rows), head=head, matrix="".join(matrix),
        words=word_svgs, stress=stress, prayer=esc(PRAYER), alphabet=esc(ALPHABET),
        spaced=esc(" ".join(ALPHABET)), waterfall=waterfall,
        big=words_svg(PRAYER[:60], 160), alpha_svg=words_svg(ALPHABET, 120),
        MARK_TOUCH=MARK_TOUCH, MARK_GAP=MARK_GAP, mark_head=mark_head,
        mark_rows="".join(mark_rows), mark_bad=mark_bad,
        mark_total=len(letters) * len(marks), vowelled=vowelled, vowelled_big=vowelled_big,
        neighbour=neighbour or "<p>None.</p>", vprayer=esc(VOWELLED_PRAYER),
        signs=sign_svgs, punctuated=punctuated, punctuated_live=esc(PUNCTUATED))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "proof.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {os.path.relpath(path)}: {len(bad_pairs)} of "
          f"{len(firsts) * len(drawn)} letter pairs have a bad joint")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{family} {style} proof</title>
<style>
@font-face {{ font-family: "Proof Font"; src: url("{font_url}"); }}
:root {{
  --bg: #ffffff; --fg: #1d1b18; --muted: #6b665e; --line: #e4e0d8; --card: #fff;
  --ink: #1d1b18; --base: #3b82c4; --level: #b9c7d6; --edge: #d9c8a8;
  --error: #c8322b; --warning: #c98a12; --info: #2f7f8f;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #171614; --fg: #ece8e1; --muted: #a39d93; --line: #34312c; --card: #211f1c;
    --ink: #ece8e1; --base: #5aa2e0; --level: #3f4d5c; --edge: #6b5b3e;
    --error: #ef6a5f; --warning: #e0a73a; --info: #5bb5c4;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.5 system-ui, -apple-system, sans-serif; }}
main {{ max-width: 1400px; margin: 0 auto; padding: 24px 16px 80px; }}
nav {{ position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--line);
  padding: 10px 16px; display: flex; gap: 18px; flex-wrap: wrap; z-index: 2; }}
nav a {{ color: var(--fg); text-decoration: none; font-weight: 600; }}
h1 {{ margin: 0 0 4px; }} h2 {{ margin-top: 48px; border-bottom: 1px solid var(--line); }}
.muted, small {{ color: var(--muted); }}
.defs {{ position: absolute; width: 0; height: 0; }}
svg {{ max-width: 100%; height: auto; display: block; }}
.ink {{ fill: var(--ink); }}
line.base {{ stroke: var(--base); stroke-width: 3; }}
line.level {{ stroke: var(--level); stroke-width: 3; stroke-dasharray: 12 10; }}
line.edge {{ stroke: var(--edge); stroke-width: 3; }}
circle {{ fill: none; stroke-width: 9; }}
circle.bad {{ stroke: var(--error); }} circle.warn {{ stroke: var(--warning); }}
.stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }}
.stat {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 10px 16px; min-width: 130px; }}
.stat b {{ display: block; font-size: 26px; }}
.stat.error b {{ color: var(--error); }} .stat.warning b {{ color: var(--warning); }}
.stat.info b {{ color: var(--info); }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; margin-right: 16px; }}
.legend i {{ display: inline-block; width: 22px; height: 0; border-top: 3px solid; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 14px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-left: 5px solid;
  border-radius: 8px; padding: 12px 14px; min-width: 0; }}
.card.error {{ border-left-color: var(--error); }} .card.warning {{ border-left-color: var(--warning); }}
.card.info {{ border-left-color: var(--info); }}
.card h3 {{ margin: 0 0 8px; font-size: 16px; }} .card code {{ color: var(--muted); font-weight: 400; }}
.pics {{ display: flex; gap: 12px; overflow-x: auto; }}
.card ul {{ margin: 8px 0 0; padding-left: 18px; }}
.card li.error b {{ color: var(--error); }} .card li.warning b {{ color: var(--warning); }}
.card li.info b, .notes li b {{ color: var(--info); }}
.notes {{ padding-left: 18px; }}
.scroll {{ overflow-x: auto; }}
.scroll.tall {{ max-height: 80vh; overflow-y: auto; }}
.marks th {{ font-size: 12px; position: sticky; top: 0; background: var(--bg); }}
.marks tr th:first-child {{ position: sticky; left: 0; text-align: left; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid var(--line); padding: 4px; vertical-align: bottom; text-align: center; }}
th {{ font-weight: 600; }}
td small {{ display: block; font-size: 11px; }}
.marks td.warn {{ background: color-mix(in srgb, var(--warning) 16%, transparent); }}
.marks td.bad, .matrix td.bad {{ background: color-mix(in srgb, var(--error) 14%, transparent); }}
.matrix th.syr {{ font-size: 28px; }}
.syr {{ font-family: "Proof Font"; direction: rtl; }}
figure {{ display: inline-block; margin: 0 10px 10px 0; background: var(--card);
  border: 1px solid var(--line); border-radius: 6px; padding: 4px; }}
.live {{ margin: 0 0 14px; line-height: 1.6; }}
.size {{ font: 12px system-ui; color: var(--muted); margin-left: 12px; direction: ltr;
  display: inline-block; width: 44px; }}
.try textarea {{ width: 100%; font-size: 48px; min-height: 140px; padding: 12px;
  background: var(--card); color: var(--fg); border: 1px solid var(--line); border-radius: 8px; }}
.try label {{ display: flex; gap: 10px; align-items: center; margin: 8px 0; }}
</style></head>
<body>
<nav><a href="#problems">Problems</a><a href="#forms">Forms</a><a href="#pairs">Pairs</a>
<a href="#words">Words</a><a href="#marks">Marks</a><a href="#signs">Punctuation</a><a href="#text">Live text</a></nav>
<main>
<h1>{family} {style} proof</h1>
<p class="muted">Letters and joins only. Connecting stroke y={bar}; common heights {levels}.
Rebuild with <code>make proof</code>.</p>
<div class="stats">
<div class="stat error"><b>{errors}</b>errors</div>
<div class="stat warning"><b>{warnings}</b>warnings</div>
<div class="stat info"><b>{infos}</b>notes</div>
<div class="stat error"><b>{pairs}</b>of {total_pairs} letter pairs join badly</div>
</div>
<p class="legend"><span><i style="border-color:var(--base)"></i>baseline and top of the connecting stroke</span>
<span><i style="border-color:var(--level);border-top-style:dashed"></i>other common heights</span>
<span><i style="border-color:var(--edge)"></i>glyph edges (advance width)</span>
<span><i style="border-color:var(--error)"></i>error</span>
<span><i style="border-color:var(--warning)"></i>warning</span></p>

<h2 id="problems">Problems</h2>
<p class="muted">Each glyph is drawn alone, then between two Beths when it joins, so you can see
the joint the way it will print. Coordinates are in font units, as shown in Glyphs.</p>
<ul class="notes">{notes}</ul>
<div class="cards">{cards}</div>

<h2 id="forms">Every letter, every form</h2>
<div class="scroll"><table><tr><th></th>{form_head}</tr>{forms}</table></div>

<h2 id="pairs">Every joining pair</h2>
<p class="muted">Row letter first, column letter second, shaped by HarfBuzz. Red cells have a joint
that does not line up; hover for details.</p>
<div class="scroll"><table class="matrix"><tr><th></th>{head}</tr>{matrix}</table></div>

<h2 id="words">Words</h2>
<div>{alpha_svg}</div>
<div>{words}</div>
<h3>Each dual-joining letter between Beths, then tripled</h3>
<div>{stress}</div>
<div>{big}</div>

<h2 id="marks">Marks</h2>
<p class="muted">Every drawn vowel and mark on every form of every letter, placed by the anchors.
Red cells touch the letter (under {MARK_TOUCH} units), amber ones come close (under {MARK_GAP}).
{mark_bad} of {mark_total} combinations touch.</p>
<div class="scroll tall"><table class="marks"><tr><th></th>{mark_head}</tr>{mark_rows}</table></div>
<h3>Marks running into the letter beside them</h3>
<div>{neighbour}</div>
<h3>Vowelled words</h3>
<div>{vowelled}</div>
<h3>Vowelled text</h3>
<div>{vowelled_big}</div>

<h2 id="signs">Punctuation and signs</h2>
<p class="muted">Every drawn character that is not a letter, and every drawn mark on a dotted circle.</p>
<div>{signs}</div>
<h3>In use</h3>
<div>{punctuated}</div>

<h2 id="text">Live text</h2>
<p class="muted">Set by your browser's own shaper, as an app would set it.</p>
<p class="syr live" style="font-size:40px">{alphabet}</p>
<p class="syr live" style="font-size:40px">{spaced}</p>
<p class="syr live" style="font-size:32px">{prayer}</p>
<p class="syr live" style="font-size:32px">{punctuated_live}</p>
<p class="syr live" style="font-size:40px; line-height:2.2">{vprayer}</p>
{waterfall}
<div class="try">
<label>Size <input type="range" min="12" max="200" value="64" id="size"> <span id="sizeval">64px</span></label>
<textarea class="syr" id="try" spellcheck="false">{prayer}</textarea>
</div>
</main>
<script>
const s = document.getElementById("size"), t = document.getElementById("try"),
      v = document.getElementById("sizeval");
s.oninput = () => {{ t.style.fontSize = s.value + "px"; v.textContent = s.value + "px"; }};
</script>
{defs}
</body></html>
"""


if __name__ == "__main__":
    main()
