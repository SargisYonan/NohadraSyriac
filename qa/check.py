"""Checks Nohadra's letters, joins and marks, one style at a time.

    python qa/check.py            report everything
    python qa/check.py --strict   exit 1 if there are errors (used by make ci)
    python qa/check.py --quiet    only write out/qa.json

    FONT=fonts/NohadraSyriac-Amedia.otf python qa/check.py   check Amedia

Joins and marks are measured on the built font (fonts/NohadraSyriac-Sapna.otf
unless FONT says otherwise), which is what applications see. Corners and
alignment are measured on the style's master in the Glyphs source, which is
what you edit. Every problem is written to out/<style>/qa.json as well, for
qa/proof.py to draw on the proof sheet.

Silence something you meant to do by adding "<glyph> <check>" to
qa/allow.txt, or "<glyph> mark-neighbour <mark>" to excuse a single mark.
"""

import argparse
import collections
import json
import math
import os
import sys

import glyphsLib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (LETTERS, MARK_GAP, MARK_TOUCH, OUT, PROBE, SAG, SOURCE,  # noqa: E402
                    STYLE, Font, master_layer, bases_for, clearance, components, drawn_marks, edge_reach,
                    is_allowed, joint_problems, joins, label, load_allow,
                    load_anchors, mark_collisions, mode, neighbour_texts,
                    place_mark, production_name, run_at, shape, split_name, spots)

OVERHANG = 10      # ink this far past the advance width is flagged
NEAR_LEVEL = 15    # a flat edge this close to a common height is flagged
SLANT = 4          # a line this close to flat/upright is flagged
CORNER_SLACK = 3   # rounding this far from the usual radius is flagged

SEVERITY = {"error": 0, "warning": 1, "info": 2}


class Report:
    def __init__(self, allowed):
        self.items, self.allowed, self.silenced = [], allowed, 0

    def add(self, severity, check, glyph, message, x=None, y=None, mark=None, example=None):
        """Record a problem; `x`, `y` place it on the glyph for the proof sheet,
        `mark` names the mark involved, and `example` is text that shows it."""
        if is_allowed(self.allowed, glyph, check, mark):
            self.silenced += 1
            return
        item = dict(severity=severity, check=check, glyph=glyph, label=label(glyph),
                    message=message, x=None if x is None else round(x),
                    y=None if y is None else round(y))
        if example:
            item["example"] = example
        self.items.append(item)


def r1(v):
    return round(v, 1) if abs(v - round(v)) > 0.05 else int(round(v))


def distance(d):
    """How close a mark comes, in words."""
    return f"overlaps it by {-round(d)}" if d < 0 else f"comes within {round(d)}"


# --- joins ------------------------------------------------------------------

def bar_metrics(font, letters):
    """The height of the connecting stroke, taken from what most joints do."""
    bottoms, tops = [], []
    for g in letters:
        glyph = font.glyph(g)
        for side, on in zip(("right", "left"), joins(g)):
            if on:
                x = glyph.width - PROBE if side == "right" else PROBE
                runs = glyph.ink_at_x(x)
                if runs:
                    bottoms.append(round(runs[0][0]))
                    short = [t for b, t in runs if t < 400]
                    if short:
                        tops.append(round(short[0]))
    return mode(bottoms), mode(tops)


def check_joins(font, letters, report):
    bottom, top = bar_metrics(font, letters)
    mid = (bottom + top) / 2
    overlap = {"left": [], "right": []}

    for g in letters:
        glyph = font.glyph(g)
        for side, on in zip(("right", "left"), joins(g)):
            edge = glyph.width if side == "right" else 0
            where = "right edge (joins the letter before)" if side == "right" \
                else "left edge (joins the letter after)"

            if not on:
                # A flat, full-height cut on a side that never joins reads as
                # a broken join.
                x = edge - PROBE if side == "right" else PROBE
                run = run_at(glyph.ink_at_x(x), mid)
                if run and abs(run[0] - bottom) < 1 and abs(run[1] - top) < 1:
                    report.add("warning", "stub", g,
                               f"{side} edge never joins, but ends in a flat cut the "
                               f"full height of the connecting stroke, so it looks "
                               f"like a join with nothing attached", edge, mid)
                continue

            problems = joint_problems(glyph, side, (bottom, top))
            for check, (y, size, msg) in problems.items():
                limit = 0 if check == "join-gap" else SAG if check == "join-sag" else 2
                report.add("error" if size > limit else "warning", check, g,
                           f"{where}: {msg}", edge, y)
            if "join-gap" not in problems:
                overlap[side].append((g, edge_reach(glyph, side, mid) - edge))

    for side, rows in overlap.items():
        usual = mode([round(o) for _, o in rows])
        for g, o in rows:
            if round(o) != usual:
                report.add("info", "join-overlap", g,
                           f"{side} joint reaches {r1(o)} past the edge; most {side} "
                           f"joints reach {usual}", (0 if side == "left" else
                                                     font.glyph(g).width) + o, mid)
    return bottom, top


def check_overhang(font, letters, report, bar):
    """Ink past the advance width. On a side that joins, the connecting
    stroke itself may run on into the next letter (Nohadra's do, by 50
    units); anything else past the edge is flagged."""
    bottom, top = bar
    for g in letters:
        glyph = font.glyph(g)
        right_join, left_join = joins(g)

        def stray(x, y, joined):
            return not (joined and bottom - 0.5 <= y <= top + 0.5)

        pts = [(x, y) for p in glyph.polys for x, y in p]
        right = [(x, y) for x, y in pts if x > glyph.width + OVERHANG and stray(x, y, right_join)]
        left = [(x, y) for x, y in pts if x < -OVERHANG and stray(x, y, left_join)]
        if right:
            x1, y = max(right)
            report.add("warning", "overhang", g,
                       f"ink reaches x={r1(x1)}, {r1(x1 - glyph.width)} units past the "
                       f"right edge, under or into the letter before", x1, y)
        if left:
            x0, y = min(left)
            report.add("warning", "overhang", g,
                       f"ink reaches x={r1(x0)}, {r1(-x0)} units past the left "
                       f"edge, under or into the letter after", x0, y)


# --- outlines (from the source) ----------------------------------------------

def segments(path):
    """[(start_node, [following nodes up to and including the next on-curve])]"""
    nodes = list(path.nodes)
    on = [i for i, n in enumerate(nodes) if n.type != "offcurve"]
    out = []
    for k, i in enumerate(on):
        j = on[(k + 1) % len(on)]
        pts, m = [], i
        while True:
            m = (m + 1) % len(nodes)
            pts.append(nodes[m])
            if m == j:
                break
        out.append((nodes[i], pts))
    return out


def source_letters(font_source, built):
    """(built name, layer) for every letter in the source that is in the font."""
    for g in font_source.glyphs:
        name = production_name(g.name)
        if g.export and name in built:
            yield name, master_layer(g)


def check_outlines(source, font, report):
    letters = list(source_letters(source, set(font.letters())))

    # Heights that many flat edges share (baseline, top of the stroke, ...).
    flat = collections.Counter()
    users = collections.defaultdict(set)
    for g, layer in letters:
        for path in layer.paths:
            for a, pts in segments(path):
                b = pts[-1]
                if len(pts) == 1 and a.position.y == b.position.y and \
                        abs(a.position.x - b.position.x) >= 20:
                    flat[a.position.y] += 1
                    users[a.position.y].add(g)
    levels = sorted(y for y, n in flat.items() if n >= 6 and len(users[y]) >= 3)

    mixed = []
    for g, layer in letters:
        kinds = {n.type for p in layer.paths for n in p.nodes}
        if "qcurve" in kinds and "curve" in kinds:
            mixed.append(g)
        for path in layer.paths:
            if not path.closed:
                x, y = path.nodes[0].position.x, path.nodes[0].position.y
                if len(path.nodes) == 1:
                    report.add("warning", "stray-point", g,
                               f"a lone point at ({r1(x)},{r1(y)}) that belongs to no "
                               f"outline; select it and delete it", x, y)
                else:
                    report.add("error", "open-path", g,
                               f"outline starting at ({r1(x)},{r1(y)}) is not closed, "
                               f"so it will not be filled", x, y)
            for a, pts in segments(path):
                if len(pts) != 1:
                    continue
                (x0, y0), (x1, y1) = (a.position.x, a.position.y), \
                    (pts[0].position.x, pts[0].position.y)
                dx, dy = abs(x1 - x0), abs(y1 - y0)
                if 0 < dy <= SLANT and dx >= 20:
                    report.add("warning", "slanted-line", g,
                               f"line from ({r1(x0)},{r1(y0)}) to ({r1(x1)},{r1(y1)}) "
                               f"is {r1(dy)} units off flat", (x0 + x1) / 2, (y0 + y1) / 2)
                elif 0 < dx <= SLANT and dy >= 20:
                    report.add("warning", "slanted-line", g,
                               f"line from ({r1(x0)},{r1(y0)}) to ({r1(x1)},{r1(y1)}) "
                               f"is {r1(dx)} units off upright", (x0 + x1) / 2, (y0 + y1) / 2)
                elif dy == 0 and dx >= 20 and y0 not in levels:
                    near = [lv for lv in levels if 0 < abs(lv - y0) <= NEAR_LEVEL]
                    if near:
                        lv = min(near, key=lambda v: abs(v - y0))
                        report.add("warning", "off-level", g,
                                   f"flat edge at y={r1(y0)} is {r1(abs(y0 - lv))} units "
                                   f"{'above' if y0 > lv else 'below'} the common height "
                                   f"y={r1(lv)} ({flat[lv]} edges use it)",
                                   (x0 + x1) / 2, y0)

    if mixed:
        report.add("info", "mixed-curves", "*",
                   f"{len(mixed)} letters mix quadratic (TrueType) and cubic curves in "
                   f"one outline. Glyphs exports this fine, but other tools choke on it. "
                   f"To tidy: select all, Paths > Other > Convert to Cubic. "
                   f"Letters: {', '.join(mixed)}")

    check_corners(letters, levels, report, font)
    return levels


def is_counter(path, layer):
    """Whether the contour is a counter (a hole in the letter): one that lies
    inside another contour of the glyph."""
    x, y = path.nodes[0].position.x, path.nodes[0].position.y
    for other in layer.paths:
        if other is path:
            continue
        pts = [(n.position.x, n.position.y) for n in other.nodes]
        inside = False
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        if inside:
            return True
    return False


def corners(g, layer, ink):
    """Every roughly square corner in the glyph: rounded (a curve between two
    lines) or sharp (two lines). `ink` is the built glyph, used to tell outer
    corners from inside ones, and a counter's corners from the inside corners
    where two strokes meet."""
    width = layer.width
    right_join, left_join = joins(g)
    for path in layer.paths:
        counter = is_counter(path, layer)
        segs = segments(path)
        n = len(segs)
        for k, (a, pts) in enumerate(segs):
            prev, nxt = segs[k - 1], segs[(k + 1) % n]
            if len(pts) == 1 and len(nxt[1]) == 1:
                p0, p2 = a.position, nxt[1][0].position
                c = (pts[0].position.x, pts[0].position.y)
                rad, radii, chord = 0, (0, 0), None
            elif len(pts) > 1 and len(prev[1]) == 1:
                # A rounded corner: the curve (or a short run of curves, as a
                # converted TrueType corner becomes) between two straight lines.
                j = k
                while len(segs[(j + 1) % n][1]) > 1 and j - k < 3:
                    j += 1
                after = segs[(j + 1) % n]
                if len(after[1]) != 1:
                    continue
                p0, s, e, p2 = prev[0].position, a.position, segs[j % n][1][-1].position, \
                    after[1][0].position
                d1 = (s.x - p0.x, s.y - p0.y)
                d2 = (p2.x - e.x, p2.y - e.y)
                den = d1[0] * d2[1] - d1[1] * d2[0]
                if den == 0:
                    continue
                t = ((e.x - s.x) * d2[1] - (e.y - s.y) * d2[0]) / den
                c = (s.x + t * d1[0], s.y + t * d1[1])
                radii = (math.hypot(c[0] - s.x, c[1] - s.y),
                         math.hypot(c[0] - e.x, c[1] - e.y))
                rad = sum(radii) / 2
                chord = ((s.x + e.x) / 2, (s.y + e.y) / 2)
            else:
                continue
            d1 = (c[0] - p0.x, c[1] - p0.y)
            d2 = (p2.x - c[0], p2.y - c[1])
            l1, l2 = math.hypot(*d1), math.hypot(*d2)
            if not l1 or not l2:
                continue
            u1, u2 = (d1[0] / l1, d1[1] / l1), (d2[0] / l2, d2[1] / l2)
            angle = math.degrees(math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1]))))
            if not 70 < angle < 110:
                continue

            if chord and rad >= 2:
                # A rounded outer corner cuts its tip away, leaving the virtual
                # corner outside the ink; an inside fillet fills it in.
                convex = not ink.contains(*c)
                v = (c[0] - chord[0], c[1] - chord[1])
                out = v if convex else (-v[0], -v[1])
            else:
                # Sharp: an outer corner has ink in one of the four diagonal
                # directions around it, an inside corner in three.
                diag = [(dx, dy) for dx in (-1, 1) for dy in (-1, 1)]
                inside = [d for d in diag if ink.contains(c[0] + 3 * d[0], c[1] + 3 * d[1])]
                if len(inside) == 1:
                    convex, out = True, (-inside[0][0], -inside[0][1])
                elif len(inside) == 3:
                    convex = False
                    out = next(d for d in diag if d not in inside)
                else:
                    continue
            # Cut ends of joining strokes are square by design.
            if rad == 0 and ((right_join and abs(c[0] - width) <= 2) or
                             (left_join and c[0] <= 2)):
                continue
            yield dict(x=c[0], y=c[1], radius=rad, radii=radii, convex=convex, counter=counter,
                       vert="top" if out[1] > 0 else "bottom",
                       horiz="right" if out[0] > 0 else "left")


def check_corners(letters, levels, report, font):
    groups = collections.defaultdict(list)
    for g, layer in letters:
        for c in corners(g, layer, font.glyph(g)):
            near = [lv for lv in levels if abs(lv - c["y"]) <= NEAR_LEVEL]
            level = min(near, key=lambda v: abs(v - c["y"])) if near else None
            key = (c["convex"], c["counter"], c["vert"], c["horiz"], level)
            groups[key].append((g, c))

    for (convex, counter, vert, horiz, level), rows in groups.items():
        if len(rows) < 4:
            continue
        usual = mode([round(c["radius"]) for _, c in rows])
        agree = sum(abs(c["radius"] - usual) <= CORNER_SLACK for _, c in rows)
        if agree < len(rows) * 2 / 3:
            continue  # no clear convention here
        kind = (f"outer {vert}-{horiz} corner" if convex else
                f"{'counter' if counter else 'inside'} corner (opening {vert}-{horiz})") + \
            (f" at y≈{level}" if level is not None else "")
        for g, c in rows:
            rad = c["radius"]
            if abs(rad - usual) > CORNER_SLACK:
                what = "is sharp" if rad == 0 else f"has radius {r1(rad)}"
                report.add("warning", "corner", g,
                           f"{kind} {what}; {agree} of {len(rows)} like it use "
                           f"radius {usual}", c["x"], c["y"])
            elif rad and abs(c["radii"][0] - c["radii"][1]) > 5:
                report.add("info", "corner-uneven", g,
                           f"{kind} is lopsided: {r1(c['radii'][0])} on one side, "
                           f"{r1(c['radii'][1])} on the other", c["x"], c["y"])


# --- coverage -----------------------------------------------------------------

def check_coverage(font, report):
    for cp, (name, jt) in LETTERS.items():
        base = font.cmap.get(cp)
        if not base or not font.glyph(base).polys:
            report.add("info", "missing", f"uni{cp:04X}",
                       f"{name} (U+{cp:04X}) is not drawn")
            continue
        wanted = ["fina"] if jt == "R" else ["init", "medi", "fina"]
        for form in wanted:
            g = f"{base}.{form}"
            if g not in font.glyphset or not font.glyph(g).polys:
                report.add("error", "missing", g, f"{name} has no {form} form")


# --- marks --------------------------------------------------------------------

def check_marks(font, letters, report):
    """Vowels and other marks: anchors present, and every drawn mark clear of
    every letter it can sit on, of the letters beside it, and of a mark
    stacked on it."""
    anchors = load_anchors()
    drawn = drawn_marks(font, anchors)

    def grade(d):
        return "error" if d < MARK_TOUCH else "warning"

    for g in letters:
        wanted = len(components(g))
        for side in ("top", "bottom"):
            if len(spots(anchors, g, side)) != wanted:
                need = side if wanted == 1 else f"{side}_1 to {side}_{wanted}"
                report.add("error", "anchor", g, f"needs {need} anchors so marks can "
                           f"attach to every letter")

    gdef = font.tt["GDEF"].table.GlyphClassDef.classDefs
    for g, cls in gdef.items():
        attaches = any(a.startswith("_") for a in anchors.get(g, {}))
        if cls == 3 and font.glyph(g).polys and not attaches and \
                not is_allowed(report.allowed, g, "unattached"):
            report.add("error", "anchor", g, "mark has no attaching anchor, so it is "
                       "drawn beside the letter instead of on it")

    for mark, pair in drawn.items():
        _, y0, _, y1 = font.glyph(mark).bounds
        a = anchors[mark]
        own = "top" if "_top" in a else "bottom"
        if own not in a:
            report.add("warning", "anchor", mark, f"no {own} anchor, so a second mark "
                       f"cannot stack on it")
        elif (own == "top" and a["top"][1] <= y1) or (own == "bottom" and a["bottom"][1] >= y0):
            report.add("warning", "anchor", mark, f"{own} anchor is inside the mark's ink, "
                       f"so a stacked mark would overlap it", *a[own])

        for g in bases_for(mark, letters):
            for spot in spots(anchors, g, pair[0]):
                x, y = place_mark(anchors, g, mark, pair, spot)
                d = clearance(font.glyph(mark), x, y, font.glyph(g), 0, 0)
                if d is not None and d < MARK_GAP:
                    report.add(grade(d), "mark-clearance", g,
                               f"{mark} {distance(d)} units; move the {spot} anchor",
                               *anchors[g][spot], mark=mark)

    # Marks running into the letters beside their own, in shaped text.
    worst = {}
    for mark in [m for m in drawn if "." not in m]:
        for text in neighbour_texts(font, chr(int(mark[3:7], 16))):
            for m, _, _, other, d in mark_collisions(font, shape(font.path, text)):
                if d < MARK_GAP and ((mark, other) not in worst or d < worst[mark, other][0]):
                    worst[mark, other] = (d, text)
    for (mark, other), (d, text) in sorted(worst.items()):
        report.add(grade(d), "mark-neighbour", other,
                   f"{mark} on the letter beside it {distance(d)} units, e.g. in \u200e{text}",
                   mark=mark, example=text)

    for side in ("top", "bottom"):
        group = [m for m, (base, _) in drawn.items() if base == side]
        for first in group:
            if side not in anchors[first]:
                continue   # reported above: nothing can stack on it
            for second in group:
                x, y = place_mark(anchors, first, second, drawn[second])
                d = clearance(font.glyph(second), x, y, font.glyph(first), 0, 0)
                if d is not None and d < MARK_GAP:
                    report.add(grade(d), "mark-stack", first,
                               f"{second} stacked on it {distance(d)} units",
                               *anchors[first][side], mark=second)


# --- output -------------------------------------------------------------------

COLOURS = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}


def print_report(report, levels, bar):
    tty = sys.stdout.isatty()

    def c(sev, text):
        return f"{COLOURS[sev]}{text}\033[0m" if tty else text

    print(f"{STYLE}: connecting stroke y={bar[0]} to y={bar[1]}")
    print(f"Common heights of flat edges: {', '.join(str(r1(v)) for v in levels)}\n")

    by_glyph = collections.defaultdict(list)
    for item in report.items:
        by_glyph[item["glyph"]].append(item)

    def order(g):
        parts = split_name(g)
        return parts if parts else (0, g)

    for g in sorted(by_glyph, key=order):
        items = sorted(by_glyph[g], key=lambda i: SEVERITY[i["severity"]])
        print("Whole font" if g == "*" else f"{label(g)}  [{g}]")
        for i in items:
            print(f"  {c(i['severity'], i['severity'].upper()):<8} {i['check']:<13} {i['message']}")
        print()

    counts = collections.Counter(i["severity"] for i in report.items)
    print(", ".join(c(s, f"{counts[s]} {s}{'s' if counts[s] != 1 else ''}")
                    for s in SEVERITY) +
          (f", {report.silenced} silenced by qa/allow.txt" if report.silenced else ""))
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict", action="store_true", help="exit 1 if there are errors")
    ap.add_argument("--quiet", action="store_true", help="only write out/qa.json")
    args = ap.parse_args()

    font = Font()
    source = glyphsLib.GSFont(SOURCE)
    letters = font.letters()
    report = Report(load_allow())

    check_coverage(font, report)
    bar = check_joins(font, letters, report)
    check_overhang(font, letters, report, bar)
    levels = check_outlines(source, font, report)
    check_marks(font, letters, report)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "qa.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(bar=bar, levels=levels, items=report.items), fh,
                  ensure_ascii=False, indent=1)

    if args.quiet:
        counts = collections.Counter(i["severity"] for i in report.items)
    else:
        counts = print_report(report, levels, bar)
    if args.strict and counts["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
