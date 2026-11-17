"""Programmatic obfuscation encoders.

Core set required by the research question: b64, leet, zwsp, rot13, spaced.
Extended, Arabic-relevant set: tatweel (kashida stretching), tashkeel
(diacritic stuffing), homoglyph (look-alike letters).

Every encoder is deterministic given (text, seed).  Each has a matching
decoder used ONLY by tests (round-trip checks); defenses do not import the
decoders from here.
"""
from __future__ import annotations

import base64
import codecs
import random
import re

CORE_ENCODINGS = ("b64", "leet", "zwsp", "rot13", "spaced")
EXTENDED_ENCODINGS = ("tatweel", "tashkeel", "homoglyph")
ENCODINGS = ("none",) + CORE_ENCODINGS + EXTENDED_ENCODINGS

ZWSP = "​"
TATWEEL = "ـ"
HARAKAT = "َُِْ"  # fatha, damma, kasra, sukun

LEET_MAP = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7"}
LEET_INV = {v: k for k, v in LEET_MAP.items()}

# Look-alike substitutions.  Latin -> Cyrillic, Arabic -> Persian/Urdu forms.
HOMOGLYPH_MAP = {
    "a": "а", "c": "с", "e": "е", "o": "о", "p": "р",
    "x": "х", "y": "у", "i": "і",
    "ك": "ک",  # ك -> ک
    "ي": "ی",  # ي -> ی
    "ه": "ھ",  # ه -> ھ
}
HOMOGLYPH_INV = {v: k for k, v in HOMOGLYPH_MAP.items()}

_ARABIC_LETTER = re.compile(r"[ء-ي]")
# letters that do NOT connect to the following letter (no kashida after them)
_NON_JOINING = set("ءآأؤإادذرزوةى")


def _is_arabic_letter(ch: str) -> bool:
    return bool(_ARABIC_LETTER.match(ch))


def enc_b64(text: str, seed: int = 0) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def dec_b64(text: str) -> str:
    return base64.b64decode(text.encode("ascii")).decode("utf-8")


def enc_leet(text: str, seed: int = 0) -> str:
    return "".join(LEET_MAP.get(ch.lower(), ch) for ch in text)


def dec_leet(text: str) -> str:
    return "".join(LEET_INV.get(ch, ch) for ch in text)


def enc_zwsp(text: str, seed: int = 0) -> str:
    out = []
    for i, ch in enumerate(text):
        out.append(ch)
        nxt = text[i + 1] if i + 1 < len(text) else " "
        if not ch.isspace() and not nxt.isspace():
            out.append(ZWSP)
    return "".join(out)


def dec_zwsp(text: str) -> str:
    return text.replace(ZWSP, "")


def enc_rot13(text: str, seed: int = 0) -> str:
    return codecs.encode(text, "rot_13")


def dec_rot13(text: str) -> str:
    return codecs.decode(text, "rot_13")


def enc_spaced(text: str, seed: int = 0) -> str:
    """Letters separated by one space, words separated by three spaces."""
    return "   ".join(" ".join(word) for word in text.split())


def dec_spaced(text: str) -> str:
    return " ".join(w.replace(" ", "") for w in re.split(r" {3,}", text))


def enc_tatweel(text: str, seed: int = 0) -> str:
    rng = random.Random(seed)
    out = []
    for i, ch in enumerate(text):
        out.append(ch)
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if _is_arabic_letter(ch) and ch not in _NON_JOINING and nxt and _is_arabic_letter(nxt):
            if rng.random() < 0.6:
                out.append(TATWEEL * rng.randint(1, 2))
    return "".join(out)


def dec_tatweel(text: str) -> str:
    return text.replace(TATWEEL, "")


def enc_tashkeel(text: str, seed: int = 0) -> str:
    rng = random.Random(seed)
    out = []
    for ch in text:
        out.append(ch)
        if _is_arabic_letter(ch) and rng.random() < 0.7:
            out.append(rng.choice(HARAKAT))
    return "".join(out)


def dec_tashkeel(text: str) -> str:
    return re.sub(f"[{HARAKAT}]", "", text)


def enc_homoglyph(text: str, seed: int = 0) -> str:
    return "".join(HOMOGLYPH_MAP.get(ch, ch) for ch in text)


def dec_homoglyph(text: str) -> str:
    return "".join(HOMOGLYPH_INV.get(ch, ch) for ch in text)


ENCODERS = {
    "b64": enc_b64, "leet": enc_leet, "zwsp": enc_zwsp, "rot13": enc_rot13,
    "spaced": enc_spaced, "tatweel": enc_tatweel, "tashkeel": enc_tashkeel,
    "homoglyph": enc_homoglyph,
}
DECODERS = {
    "b64": dec_b64, "leet": dec_leet, "zwsp": dec_zwsp, "rot13": dec_rot13,
    "spaced": dec_spaced, "tatweel": dec_tatweel, "tashkeel": dec_tashkeel,
    "homoglyph": dec_homoglyph,
}

# A language-neutral label put in front of opaque encodings, so that the
# carrier does not need a natural-language "decode this" hint (which would add
# a language confound).  Human-readable obfuscations get no label.
LABELS = {"b64": "base64: ", "rot13": "rot13: "}


def encode(name: str, text: str, seed: int = 0) -> str:
    if name == "none":
        return text
    return ENCODERS[name](text, seed)


def present(name: str, encoded: str) -> str:
    """Encoded payload as it is placed inside a carrier."""
    return LABELS.get(name, "") + encoded


MIN_COVERAGE = 0.25
_WHOLE_TEXT = ("b64", "spaced")


def coverage(name: str, text: str, seed: int = 0) -> float:
    """Share of ordinary tokens (not addresses / URLs) that the encoding changes."""
    if name == "none":
        return 1.0
    if name in _WHOLE_TEXT:
        return 1.0 if encode(name, text, seed) != text else 0.0
    tokens = [t for t in text.split() if "@" not in t and "://" not in t]
    if not tokens:
        return 0.0
    changed = sum(1 for t in tokens if ENCODERS[name](t, seed) != t)
    return changed / len(tokens)


def applicable(name: str, text: str, seed: int = 0) -> bool:
    """An encoding is applicable when it changes a real share of the text.

    leet / rot13 do nothing to Arabic-script words and tatweel / tashkeel do
    nothing to Latin words.  Changing only the embedded e-mail address does not
    count.  Cells below MIN_COVERAGE are reported as N/A, never as results.
    """
    return name == "none" or coverage(name, text, seed) >= MIN_COVERAGE
