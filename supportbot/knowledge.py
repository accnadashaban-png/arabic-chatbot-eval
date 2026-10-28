"""Knowledge base, dialect lexicon and BM25 retrieval.

Bring your own content: a folder with
    faq.csv        id, topic, concepts, questions (| separated), answer_ar, answer_en
    policies.json  which topics hand off to people or are refused, confidence thresholds, fixed messages
The lexicon maps dialect, English and Franco words to shared concepts, so "بكام", "قديش", "شحال" and
"how much" all find the pricing entry.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from supportbot.arabic import fold, stem, stems, tokens

HERE = Path(__file__).resolve().parent
DEMO_KB = HERE / "demo_kb"
LEXICON = HERE / "lexicon.csv"
CONCEPT_WEIGHT = 3  # a concept counts like three ordinary words
# Descriptors that narrow a request but do not name it ("when", "course", "account"): a topic concept such as
# CERTIFICATE outranks them, so "is there a certificate after the course?" is about the certificate.
SECONDARY = frozenset({"SCHEDULE", "COURSE", "ACCOUNT", "CHANGE", "MONTHLY", "YEARLY", "SUBSCRIPTION", "PAY", "DATA",
                       "NOTWORKING", "MISSING", "RECORDING", "PHONE"})
STOPWORDS = frozenset(stem(fold(w)) for w in [
    "في", "من", "على", "علي", "عن", "الى", "إلى", "هل", "ما", "ماذا", "كيف", "ازاي", "إزاي", "شو", "وش", "ايه",
    "إيه", "انا", "أنا", "انت", "هو", "هي", "هذا", "هذه", "ده", "دي", "اللي", "التي", "الذي", "او", "أو", "لو",
    "مع", "كل", "بعد", "قبل", "عند", "عندي", "عندكم", "ممكن", "يمكن", "يمكنني", "أريد", "اريد", "عايز", "عاوز",
    "أبغى", "ابغى", "أبي", "ابي", "بدي", "بغيت", "ودي", "فيه", "يا", "السلام", "عليكم", "مرحبا", "لكم", "لي", "ليا",
    "the", "a", "an", "i", "my", "me", "you", "your", "is", "are", "am", "do", "does", "did", "to", "of", "for",
    "in", "on", "and", "or", "can", "could", "how", "what", "it", "this", "that", "with", "be", "have", "has",
    "please", "hi", "hello", "there", "here", "there's", "i'm", "i've", "i'd", "we", "us", "our", "want", "need",
    "would", "like", "get", "got", "some", "any", "all", "few", "been", "being", "was", "were", "will", "just",
    "so", "very",
])


@dataclass(frozen=True)
class Entry:
    id: str
    topic: str
    concepts: frozenset[str]
    questions: tuple[str, ...]
    answer: dict[str, str]


@dataclass
class Lexicon:
    words: list[tuple[str, str]] = field(default_factory=list)    # (concept, folded single word)
    phrases: list[tuple[str, str]] = field(default_factory=list)  # (concept, folded phrase)

    @classmethod
    def load(cls, *paths: Path) -> Lexicon:
        """The shared lexicon, plus any extra files that exist (a company's own product words)."""
        lex = cls()
        for path in paths or (LEXICON,):
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                for w in row["words"].split("|"):
                    w = fold(w.strip())
                    if w:
                        (lex.phrases if " " in w else lex.words).append((row["concept"], w))
        return lex

    def concepts(self, text: str) -> set[str]:
        """Short and Latin words must match a whole word ("month" is not "months"); longer Arabic words may sit
        inside one, since Arabic attaches prefixes and suffixes. Long Arabic words also tolerate one typo."""
        toks = tokens(text)
        folded = f" {' '.join(toks)} "  # punctuation-free, so "كلمة السر،" still matches "كلمة السر"
        found: set[str] = set()
        for c, p in self.phrases:  # a phrase claims its words: "live agent" is not also LIVE
            if f" {p} " in folded:
                found.add(c)
                folded = folded.replace(f" {p} ", " ")
        toks = folded.split()
        unmatched = set(toks)
        for c, w in self.words:
            if len(w) <= 3 or not _arabic(w):
                hit = [t for t in toks if t == w or stem(t) == w]
            else:
                hit = [t for t in toks if w in t or stem(t) == stem(w)]
            if hit:
                found.add(c)
                unmatched -= set(hit)
        for t in unmatched:  # "الشاهدة" is still "الشهادة"
            if len(t) >= 4 and _arabic(t):
                found |= {c for c, w in self.words if len(w) >= 5 and (one_typo(t, w) or one_typo(stem(t), stem(w)))}
        return found


def _arabic(word: str) -> bool:
    return "ء" <= word[0] <= "ي"


def one_typo(a: str, b: str) -> bool:
    """Same length and one swapped pair of neighbours, or (in long words only) one different letter.
    Short Arabic words are too close to each other for more: أشتري / أشكر / أشتكي differ by one letter."""
    if len(a) != len(b) or a == b or len(a) < 4:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(diff) == 1:
        return len(a) >= 6
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def load_entries(folder: Path) -> list[Entry]:
    with (folder / "faq.csv").open(encoding="utf-8-sig", newline="") as f:
        return [Entry(r["id"], r["topic"], frozenset(r["concepts"].split()), tuple(q for q in r["questions"].split("|") if q),
                      {"ar": r["answer_ar"], "en": r["answer_en"]}) for r in csv.DictReader(f)]


def load_policies(folder: Path) -> dict[str, Any]:
    return dict(json.loads((folder / "policies.json").read_text(encoding="utf-8")))


@dataclass
class Hit:
    entry: Entry
    score: float
    margin: float  # how far ahead of the best entry from another topic (0..1)
    concepts: set[str]
    anchored: bool = True  # False when no concept matched and words alone decided


class Index:
    """Okapi BM25 over each entry's questions, answers and concepts."""

    def __init__(self, entries: list[Entry], lexicon: Lexicon, k1: float = 1.5, b: float = 0.75):
        self.entries, self.lexicon, self.k1, self.b = entries, lexicon, k1, b
        self.docs = [self._terms(" ".join(e.questions) + " " + e.answer["ar"] + " " + e.answer["en"], set(e.concepts))
                     for e in entries]
        self.avg = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log((n - k + 0.5) / (k + 0.5) + 1) for t, k in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    @staticmethod
    def _terms(text: str, concepts: set[str]) -> list[str]:
        return [s for s in stems(text) if s not in STOPWORDS] + [f"#{c}" for c in sorted(concepts) for _ in range(CONCEPT_WEIGHT)]

    def search(self, text: str) -> Hit | None:
        concepts = self.lexicon.concepts(text)
        query = set(self._terms(text, concepts))
        if not query:
            return None
        scores = []
        for e, tf, doc in zip(self.entries, self.tf, self.docs, strict=True):
            s = sum(self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(doc) / self.avg))
                    for t in query if t in tf)
            scores.append((s, e))
        # Concepts lead, words break ties: when the message names a known concept, only entries about that concept
        # compete. A word that merely appears in some answer ("المشكلة") must not pull a vague message to a topic.
        anchored = [(s, e) for s, e in scores if e.concepts & concepts]
        pool = anchored or scores
        def rank(e: Entry) -> tuple[int, int]:
            shared = e.concepts & concepts
            return len(shared - SECONDARY), len(shared & SECONDARY)
        pool.sort(key=lambda x: (rank(x[1]), x[0]), reverse=True)
        top_score, top = pool[0]
        if top_score <= 0:
            return None
        rival = next((s for s, e in pool[1:] if e.topic != top.topic and rank(e) == rank(top)), 0.0)
        return Hit(top, top_score, (top_score - rival) / top_score, concepts, anchored=bool(anchored))
