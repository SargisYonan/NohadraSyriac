# Changelog

## 2.0 (2026-10-01)

Both styles were checked with the QA tools, tests and proofs from Diba, which
found the problems below. `make diff` draws every change against 1.7.

### Shaping

- Rish with syame (ܪ̈) after a joining letter used the unjoined Rish, so the
  join broke. Rish-syame now follows the joining forms, and a vowel typed
  between Rish and the syame no longer leaves Rish's own dot showing under the
  syame. Dotless Dalath-Rish with syame works the same way.
- Taw–Alaph after a joining letter (ܒܬܐ) now uses the joined Taw–Alaph
  ligature, which was drawn but never used.
- Yudh He (ܞ) had no final form, so a letter joining to it was left with a
  dangling join. It now has one.
- Vowels and marks attach to the letters again in fonts built outside Glyphs
  (fontmake): the source no longer has empty `mark` and `kern` features that
  blocked the generated ones.
- Two marks on the same side of a letter now stack instead of overlapping:
  every mark has a stacking anchor.
- Removed six positioning lookups no feature used.
- The stylistic sets have names: ss01 "Semkath drawn as Final Semkath", ss02
  "Ring-shaped Qushshaya and Rukkakha".

### Letters

- Alaph after a letter that never joins forward (ܘܐ, ܕܐ, ܪܐ, ܐܐ) touched it:
  the unjoined Alaphs were 52 units narrower than their arm. They are now as
  wide as the joined Alaph, so the arm ends at the letter's edge.
- Gamal Garshuni final was 32 units narrower than its own join.
- He final's inner notch was off the grid every other letter uses.
- Amedia: the joining stroke of eleven initial and medial letters (Beth,
  Gamal, Teth Garshuni, Kaph, Lamadh, Pe, Shin) ended in rounded corners,
  pinching the joint; it is now the full height of the connecting stroke.
- Amedia: Heth and Yudh had sharp corners where every other stroke end is
  rounded.
- Amedia: Lamadh–Alaph's arm was 21 units longer than Sapna's.
- Points a unit or two off the grid snapped back: Lamadh–Alaph, Heth, Taw,
  Taw–Alaph, Waw, Semkath, Final Semkath, Pe, Reversed Pe, Sadhe, He, Yudh,
  Yudh He, and every joint that ran one unit past its edge.
- LRM and RLM (U+200E, U+200F) drew an arrow; they are invisible now.

### Marks

- Marks below Final Semkath sat inside its tail (a hbasa vanished entirely).
- Marks above E and Kaph ran into their tall strokes.
- The diaeresis below ran into the descenders of Gamal, Gamal Garshuni,
  Kaph, Mim and Yudh He.
- A vowel above Rish-syame landed on the syame's dots.
- The dotted circle (◌) had no anchor for marks below, and three stray ones.
- Marks have no advance width.

### Font files

- Built from the source with fontmake (`make build`) instead of exporting from
  Glyphs.app, so every build is the same.
- winAscent/winDescent were 672/304, which clipped vowels over Lamadh and Taw
  on Windows; they now cover the marks.
- Amedia was marked as weight 300 (Light); both styles are 400, as their
  strokes are the same weight.
- Some glyphs were renamed: `uni072A0308.isol`/`.fina` to `uni072A.syame` and
  `uni072A.fina.syame`, and the ligatures to `uni0720_uni0710` and
  `uni072C_uni0710` (built as `uni07200710` and `uni072C0710`).

### Tools

- `make qa`, `make test`, `make proof`, `make images`, `make diff` and
  `make fontbakery`, with CI running all of them on every push.
- The README images are rendered from the fonts (`documentation/`). The old
  sample PNGs were drawn with an Arabic reshaper that dropped the vowels.

## 1.7

The last release built in Glyphs.app.
