"""Arabic-aware text helpers: normalization, language detection (including Franco), matching."""
from __future__ import annotations

import re

DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")  # harakat, superscript alef, tatweel
ALEF = re.compile(r"[\u0622\u0623\u0625\u0671]")          # آ أ إ ٱ -> ا
REPEATS = re.compile(r"(.)\1{2,}")                           # ازاااي -> ازاي
ARABIC_LETTER = re.compile(r"[\u0621-\u064A]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
SPACES = re.compile(r"\s+")
PUNCTUATION = re.compile(r"[^\w\s]")
# Arabizi digits stand for Arabic sounds (2 = ء, 3 = ع, 5 = خ, 7 = ح) when written inside words
FRANCO_DIGIT = re.compile(r"[a-z][2357]|[2357][a-z]", re.I)
FRANCO_WORDS = {"ana", "enta", "enti", "ezay", "izay", "ezzay", "3ayez", "3ayza", "ayez", "msh", "mesh", "mish", "leh", "eh",
                "kam", "bkam", "momken", "lw", "law", "keda", "kda", "ya3ni", "yaani", "el", "fe", "fi", "ma3a", "3ala",
                "eshterak", "el2eshterak", "elkors", "elcourse", "shokran", "salam", "3aleko", "ahlan", "ba2a", "aslan", "wala"}


def normalize(text: str) -> str:
    """Fold spelling variants so matching and de-duplication are fair to how people type Arabic."""
    t = DIACRITICS.sub("", text or "")
    t = ALEF.sub("ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")      # ى -> ي, ة -> ه
    t = t.replace("ؤ", "و").replace("ئ", "ي")      # ؤ -> و, ئ -> ي
    t = REPEATS.sub(r"\1", t.lower())
    return SPACES.sub(" ", t).strip()


def is_franco(text: str) -> bool:
    """Arabic written in Latin letters (Arabizi), e.g. "3ayez a2lel el eshterak"."""
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in FRANCO_WORDS or FRANCO_DIGIT.search(w))
    return hits >= 2 or (hits >= 1 and len(words) <= 3)


def detect_language(text: str) -> str:
    """'ar', 'en', 'franco' or 'unknown', from the script that dominates the letters."""
    ar = len(ARABIC_LETTER.findall(text or ""))
    en = len(LATIN_LETTER.findall(text or ""))
    if ar == 0 and en == 0:
        return "unknown"
    if ar >= en:
        return "ar"
    return "franco" if is_franco(text) else "en"


def contains_any(text: str, options: list[str]) -> bool:
    """True if any option appears in the text, after normalizing both sides."""
    haystack = normalize(text)
    return any(normalize(o) in haystack for o in options if o.strip())


def char_ngrams(text: str, n: int = 3) -> set[str]:
    t = f" {SPACES.sub(' ', PUNCTUATION.sub(' ', normalize(text))).strip()} "  # punctuation is noise here
    return {t[i:i + n] for i in range(max(len(t) - n + 1, 1))}


def similarity(a: str, b: str) -> float:
    """Jaccard similarity of character trigrams: robust to word order changes and small typos."""
    x, y = char_ngrams(a), char_ngrams(b)
    return len(x & y) / len(x | y) if x | y else 1.0
