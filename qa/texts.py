"""Sample text for the proofs: the alphabet, words, the Lord's Prayer, and
the same with East Syriac vowels."""

ALPHABET = "ܐܒܓܕܗܘܙܚܛܝܟܠܡܢܣܥܦܨܩܪܫܬ"

WORDS = """ܫܠܡܐ ܐܬܘܪܝܐ ܣܘܪܝܝܐ ܟܬܒܐ ܥܠܡܐ ܡܠܟܐ ܐܠܗܐ ܕܝܒܐ ܢܘܗܪܐ ܒܪܢܫܐ
ܡܕܢܚܐ ܥܕܬܐ ܠܫܢܐ ܣܦܪܐ ܦܬܓܡܐ ܨܠܘܬܐ ܛܘܒܐ ܙܒܢܐ ܓܢܬܐ ܩܠܐ ܚܘܒܐ
ܡܝܐ ܝܘܡܐ ܠܠܝܐ ܐܪܥܐ ܫܡܝܐ ܩܕܝܫܐ ܚܝܐ ܒܝܬ ܢܗܪܝܢ""".split()

PRAYER = ("ܐܒܘܢ ܕܒܫܡܝܐ ܢܬܩܕܫ ܫܡܟ ܬܐܬܐ ܡܠܟܘܬܟ ܢܗܘܐ ܨܒܝܢܟ ܐܝܟܢܐ ܕܒܫܡܝܐ "
          "ܐܦ ܒܐܪܥܐ ܗܒ ܠܢ ܠܚܡܐ ܕܣܘܢܩܢܢ ܝܘܡܢܐ ܘܫܒܘܩ ܠܢ ܚܘܒܝܢ ܘܚܛܗܝܢ "
          "ܐܝܟܢܐ ܕܐܦ ܚܢܢ ܫܒܩܢ ܠܚܝܒܝܢ ܘܠܐ ܬܥܠܢ ܠܢܣܝܘܢܐ ܐܠܐ ܦܨܢ ܡܢ ܒܝܫܐ")

# Punctuation in use: a sentence ending, a pause, a paragraph end.
PUNCTUATED = ("ܐܒܘܢ ܕܒܫܡܝܐ. ܢܬܩܕܫ ܫܡܟ: ܬܐܬܐ ܡܠܟܘܬܟ܁ ܢܗܘܐ ܨܒܝܢܟ܂ "
              "ܐܝܟܢܐ ܕܒܫܡܝܐ܅ ܐܦ ܒܐܪܥܐ܀")


# Vowelled text is written with ASCII stand-ins for the marks, which are hard
# to type and to read in source: a ptaha, A zqapa, e zlama psiqa, E zlama
# qashya, i/u hbasa-esasa (under Yudh/Waw), o rwaha, q qushshaya, r rukkakha,
# s syame.
MARK_KEYS = {"a": "\u0732", "A": "\u0735", "e": "\u0738", "E": "\u0739", "i": "\u073C",
             "u": "\u073C", "o": "\u073F", "q": "\u0741", "r": "\u0742", "s": "\u0308"}


def vowel(text):
    return "".join(MARK_KEYS.get(ch, ch) for ch in text)


VOWELLED_WORDS = [vowel(w) for w in """ܫܠAܡAܐ ܐAܬrܘoܪAܝAܐ ܣܘuܪAܝAܐ ܟܬrAܒrAܐ ܟܬrAܒrEsܐ
ܡaܠܟAܐ ܡaܠܟEsܐ ܥAܠܡAܐ ܐaܠAܗAܐ ܕEܐܒrAܐ ܢܘuܗܪAܐ ܝAܘܡAܐ ܠeܠܝAܐ ܡaܕܢܚAܐ
ܥEܕܬrAܐ ܠeܫAܢAܐ ܣeܦܪEsܐ ܨܠܘoܬrAܐ ܛܘoܒrAܐ ܚܘuܒAܐ ܡaܝAܐ ܩaܕܝiܫAܐ ܚaܝEsܐ
ܟqaܠܒqAܐ ܒܝiܬ ܢaܗܪܝiܢ""".split()]

VOWELLED_PRAYER = vowel(
    "ܐaܒܘuܢ ܕܒaܫܡaܝAܐ ܢeܬܩaܕaܫ ܫܡAܟr ܬEܐܬEܐ ܡaܠܟܘuܬrAܟr ܢeܗܘEܐ ܨeܒܝAܢAܟr "
    "ܐaܝܟaܢAܐ ܕܒaܫܡaܝAܐ ܐAܦ ܒܐaܪܥAܐ ܗaܒ ܠaܢ ܠaܚܡAܐ ܕܣܘuܢܩAܢaܢ ܝAܘܡAܢAܐ "
    "ܘaܫܒܘoܩ ܠaܢ ܚAܘܒaܝܢ ܘܚAܛAܗaܝܢ ܐaܝܟaܢAܐ ܕܐAܦ ܚܢaܢ ܫܒaܩܢ ܠܚaܝAܒaܝܢ "
    "ܘܠAܐ ܬaܥܠaܢ ܠܢeܣܝܘoܢAܐ ܐeܠAܐ ܦaܨAܢ ܡeܢ ܒܝiܫAܐ")


# Texts that show the places a release is most likely to change, each with
# what to look for. qa/diff.py draws them first, before and after.
DIFF_HIGHLIGHTS = [
    ("ܒܪ̈ ܪ̈", "Rish with syame, joined and alone: the syame's dots replace Rish's dot, and a joined Rish keeps its join."),
    ("ܪܵ̈ ܒܪ̈ܵ", "A vowel typed before or after the syame: still one Rish with two dots, and the vowel clears them."),
    ("ܒܬܐ ܥܕܬܐ ܬܐ", "Taw–Alaph: one ligature, after a joining letter too."),
    ("ܒܠܐ ܠܐ", "Lamadh–Alaph, joined and alone."),
    ("ܒܞܒ ܞ", "Yudh He after a joining letter: it needs a final form to join."),
    ("ܘܐ ܕܐ ܪܐ ܐܐ", "Alaph after letters that never join forward: it should not touch them."),
    ("ܢܘܗܕܪܐ ܐܡܕܝܐ", "Words ending in Alaph."),
    ("ܤܼ ܒܤܼ ܤ̤", "Marks under Final Semkath: below its tail, not inside it."),
    ("ܥܵ ܥ̃ ܥܑ ܟ̈ ܟܵ", "Marks over E and Kaph: clear of the tall stroke."),
    ("ܓ̤ ܟ̤ ܒܟ̤ ܡ̤ ܞ̤", "The diaeresis below beside a descender."),
    ("ܒ̈ܵ ܒܼ݂ ܒ̇ܵ", "Two marks on one side of a letter stack instead of overlapping."),
    ("◌ܵ ◌ܼ ◌̈ ◌̤", "Marks on the dotted circle, above and below."),
    ("ܚܝܐ ܒܚܒ ܝܘܡܐ", "Heth and Yudh."),
    ("ܒܒܒ ܓܓܓ ܟܟܟ ܦܦܦ ܫܫܫ ܠܠܠ", "Joins: the stroke meets the next letter at full height."),
    ("ܗ ܒܗ ܔ ܒܔ", "He and Gamal Garshuni, alone and joined."),
]
