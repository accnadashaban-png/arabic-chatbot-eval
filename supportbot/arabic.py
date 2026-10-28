"""Text handling for the bot: Arabic folding, a light stemmer, tokens and language.

Kept separate from the evaluator's text helpers on purpose: a bug shared by the bot and the
checks that grade it would hide itself.
"""
from __future__ import annotations

import re
from functools import lru_cache

_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_MARKS = re.compile("[ًٌٍَُِّْٰـ]")       # harakat, shadda, sukun, superscript alef, tatweel
_STRETCH = re.compile(r"(.)\1{2,}")
_WORD = re.compile(r"[a-z0-9']+|[ء-ي]+")
_ARABIC = re.compile("[ء-ي]")
_FRANCO_DIGIT = re.compile(r"[a-z][2357]|[2357][a-z]")
_FRANCO_WORDS = frozenset([
    "ana", "enta", "enti", "ezay", "izay", "3ayez", "3ayza", "msh", "mesh", "mish", "leh", "eh", "momken", "law",
    "keda", "ya3ni", "el", "fe", "fi", "3ala", "fen", "emta", "kam", "bkam", "shokran", "salam", "ahlan", "tany",
    "bta3i", "bta3y", "bta3ak", "elly", "lel", "men", "w", "ya", "dy", "da", "de", "mafeesh", "mafish", "7ad",
    "gedan", "awy", "tamam", "3and", "3andy", "3andak", "3ayzeen", "bas", "kaman",
])
# Arabic glues articles and conjunctions to words: "والسنوي" -> "سنوي", "بالكارت" -> "كارت"
_PREFIXES = ("وبال", "وال", "بال", "فال", "كال", "لل", "ال", "و", "ف", "ب", "ل")
_SUFFIXES = ("هم", "كم", "كن", "ها", "نا", "ات", "ي", "ه", "ك")


def fold(text: str) -> str:
    t = _MARKS.sub("", (text or "").lower()).translate(_FOLD)
    return _STRETCH.sub(r"\1", t)


def tokens(text: str) -> list[str]:
    return _WORD.findall(fold(text))


@lru_cache(maxsize=65536)
def stem(token: str) -> str:
    """Light stemming: strip one common prefix and one common suffix, never below three letters."""
    if not _ARABIC.match(token):
        return token
    for p in _PREFIXES:
        if token.startswith(p) and len(token) - len(p) >= 3:
            token = token[len(p):]
            break
    for s in _SUFFIXES:
        if token.endswith(s) and len(token) - len(s) >= 3:
            token = token[: -len(s)]
            break
    return token


def stems(text: str) -> list[str]:
    return [stem(t) for t in tokens(text)]


def is_franco(text: str) -> bool:
    words = tokens(text)
    latin = [w for w in words if not _ARABIC.match(w)]
    if not latin:
        return False
    hits = sum(1 for w in latin if w in _FRANCO_WORDS or _FRANCO_DIGIT.search(w))
    return hits >= 2 or (hits == 1 and len(latin) <= 3)


def reply_language(message: str) -> str:
    """Arabic for any Arabic script (dialects, code-switching) and for Franco; English otherwise."""
    return "ar" if _ARABIC.search(message or "") or is_franco(message) else "en"
