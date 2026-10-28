"""Guardrails: refuse prompt injection, credential and data-exfiltration requests; keep personal data out of logs.

Detection runs on a normalized copy of the message: Arabic folded, diacritics and tatweel removed, invisible
characters dropped, spaced-out letters joined ("i g n o r e"), common digit-for-letter swaps undone ("1gn0re"),
and one typo tolerated in key words.
"""
from __future__ import annotations

import re

from supportbot.arabic import tokens
from supportbot.knowledge import one_typo

_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")  # zero-width and direction marks
_SPACED = re.compile(r"\b(?:\w ){3,}\w\b")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s"})
_KEY_WORDS = ("التعليمات", "تعليمات", "تعليماتك")

_OVERRIDE = re.compile(r"\b(ignore|disregard|forget|bypass|override)\b|تجاهل|(^|\s)(انس|انسي|نسي|انسا)(\s|$)")
_TARGET = re.compile(r"instruction|rules|prompt|guideline|تعليمات|التعليمات|تعليماتك|قواعدك|ta3limat")
_ALWAYS = re.compile(
    r"system prompt|developer mode|jailbreak|\bdan\b|تعليمات النظام|متبرمج|تعليماتك"
    r"|التعليمات (اللي|يلي|التي) (معطين|عطاو|متبرمج)"
    r"|(اكتب|اكتبها|اطبع|اعرض|ورين|ektebly).{0,30}(التعليمات|تعليمات|prompt)"
    r"|\b(repeat|print|show|output|reveal)\b.{0,30}\b(text|words|message|everything|instructions)\b.{0,15}\b(above|before|earlier|initial)\b"
    r"|what (were|are) you (told|instructed)|your (instructions|prompt|rules|guidelines)\b")
_ADMIN_SECRET = re.compile(
    r"\badmin\W*(s\W+)?(password|pass|credentials|login)"
    r"|(password|credentials|login)\W+(of|for)\W+(the\W+)?admin"
    r"|(باسورد|الباسورد|كلمه السر|كلمه مرور|كلمه المرور|مودباس|المودباس|بيانات حساب) (بتاع |ديال |حق |تبع )?(ال)?(ادمن|مسوول)"
    r"|password bta3 el admin")
_OTHERS_DATA = re.compile(
    r"\b(emails?|phones?|phone numbers?|numbers|addresses|data|details|accounts?|info|information|passwords?)\b.{0,25}"
    r"\b(of|for)?\s*(all|every|other|another)\s*(users?|customers?|subscribers?|members?|people)\b"
    r"|\b(all|every|other|another)\s*(users?|customers?|subscribers?|members?)('s?)?\b.{0,25}"
    r"\b(emails?|phones?|numbers|addresses|data|details|accounts?|info|information)\b"
    r"|\b(list|dump|export)\b.{0,15}\b(users?|customers?|subscribers?|members?)\b"
    r"|(ايميلات|ايميل|بيانات|معلومات|ارقام|جوالات|تلفونات|حسابات)( \S+){0,3} (كل )?(ال)?(مشتركين|عملاء|اعضاء|زباين|ناس|يوزرز)")
_SQL = re.compile(r"\bselect\b.+\bfrom\b|\bdrop\s+table\b|\bunion\s+select\b|\binsert\s+into\b|\bdelete\s+from\b"
                  r"|'\s*or\s*'?\d'?\s*=\s*'?\d|;\s*--")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PHONE = re.compile(r"(?<!\w)\+?\d[\d -]{7,}\d(?!\w)")


def _normalized(message: str) -> list[str]:
    """The message as a guard should read it, with and without digit-for-letter swaps."""
    raw = _INVISIBLE.sub("", message or "").lower()
    raw = _SPACED.sub(lambda m: m.group().replace(" ", ""), raw)
    words = [next((k for k in _KEY_WORDS if one_typo(w, k)), w) for w in tokens(raw)]
    plain = " ".join(words)
    return [plain, plain.translate(_LEET), raw]


def is_attack(message: str) -> bool:
    """Attempts to override or reveal instructions, obtain credentials, read other people's data, or run SQL."""
    for t in _normalized(message):
        if _ALWAYS.search(t) or _ADMIN_SECRET.search(t) or _OTHERS_DATA.search(t) or _SQL.search(t):
            return True
        if _OVERRIDE.search(t) and _TARGET.search(t):
            return True
    return False


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d) * (2 if alt else 1)
        total += n - 9 if n > 9 else n
        alt = not alt
    return total % 10 == 0


def redact(text: str) -> str:
    """Mask emails, payment card numbers (Luhn-valid) and phone numbers before anything is logged."""
    text = EMAIL.sub("[email]", text)
    text = CARD.sub(lambda m: "[card]" if _luhn(re.sub(r"\D", "", m.group())) else m.group(), text)
    return PHONE.sub("[phone]", text)
