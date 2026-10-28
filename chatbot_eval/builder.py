"""Expand the seed questions into a golden dataset with deliberate variants.

Language policy (what language a good answer must be in):
- Arabic script in any dialect -> Arabic
- Franco (Arabic in Latin letters) -> Arabic: the user speaks Arabic, only the keyboard is Latin
- English -> English
- Code-switching (Arabic with English words) -> Arabic: these are Arabic speakers using English terms
"""
from __future__ import annotations

import re
from typing import Any

from chatbot_eval.dataset import Case
from chatbot_eval.templates import (
    CONTEXT,
    CONTEXT_AR,
    CONVERSATIONS,
    GREETING,
    GREETING_AR,
    HOLDOUT,
    INTENTS,
    POLITE,
    TRAINING_FAQ,
)
from chatbot_eval.text import ARABIC_LETTER

LEVEL = {"english": "easy", "msa": "easy", "egyptian": "medium", "gulf": "medium", "levantine": "medium",
         "maghrebi": "hard", "franco": "hard", "mixed": "hard"}
HARDER = {"easy": "medium", "medium": "hard", "hard": "hard"}
LATIN_SCRIPT = ("english", "franco")


def expected_language(dialect: str) -> str:
    return "en" if dialect == "english" else "ar"


def informal(question: str) -> str:
    """How many people really type: no hamza, ه for ة, no question mark, a stretched word."""
    t = re.sub("[\u0623\u0625\u0622]", "\u0627", question).replace("ة", "ه").rstrip("؟?").strip()
    words = t.split(" ")
    for i, w in enumerate(words):  # stretch the first plain Arabic word: "عايز" -> "عايززز"
        if len(w) >= 3 and re.fullmatch("[\u0621-\u063A\u0641-\u064A]+", w):
            words[i] = w + w[-1] * 2
            break
    return " ".join(words)


def polite(question: str, dialect: str) -> str:
    """The same request with a courtesy word at the end: "..., لو سمحت؟"."""
    mark = "؟" if question.rstrip().endswith("؟") else "?" if question.rstrip().endswith("?") else ""
    return f"{question.rstrip().rstrip('؟?').rstrip()} {POLITE[dialect]}{mark}"


def typo(question: str) -> str:
    """Swap two neighbouring letters in the longest Arabic word, the most common slip on a phone keyboard."""
    words = question.split(" ")
    candidates = [i for i, w in enumerate(words) if len(w) >= 5 and ARABIC_LETTER.search(w)]
    if not candidates:
        return question
    i = max(candidates, key=lambda k: len(words[k]))
    w, mid = words[i], len(words[i]) // 2
    words[i] = w[:mid - 1] + w[mid] + w[mid - 1] + w[mid + 1:]
    return " ".join(words)


def make_case(case_id: str, question: str, intent: str, dialect: str, test_type: str, difficulty: str,
              variant_of: str = "", notes: str = "", history: list[str] | None = None,
              must_include: list[list[str]] | None = None) -> Case:
    spec = INTENTS[intent]
    return Case(id=case_id, question=question, dialect=dialect, intent=intent,  # type: ignore[arg-type]
                test_type=test_type, difficulty=difficulty,  # type: ignore[arg-type]
                expected_language=expected_language(dialect),  # type: ignore[arg-type]
                expected_behavior=spec["behavior"],
                must_include=spec["must_include"] if must_include is None else must_include,
                must_not_include=spec.get("must_not_include", []), critical=spec.get("critical", False),
                variant_of=variant_of, notes=notes, history=history or [])


def build_cases() -> list[Case]:
    cases: list[Case] = []

    def add(question: str, intent: str, dialect: str, test_type: str, difficulty: str, variant_of: str = "", notes: str = "",
            **extra: Any) -> str:
        case_id = f"GS-{len(cases) + 1:04d}"
        cases.append(make_case(case_id, question, intent, dialect, test_type, difficulty, variant_of, notes, **extra))
        return case_id

    for intent, spec in INTENTS.items():
        special = spec.get("test_type")
        for dialect, seeds in spec["seeds"].items():
            level = "hard" if special == "adversarial" else LEVEL[dialect]
            for n, seed in enumerate(seeds):
                base = add(seed, intent, dialect, special or "happy_path", level)
                latin = dialect in LATIN_SCRIPT
                add(GREETING.get(dialect, GREETING_AR) + seed, intent, dialect, special or "paraphrase", level, base, "greeting first")
                add(polite(seed, dialect), intent, dialect, special or "paraphrase", level, base, "courtesy word")
                if n == 0:
                    context = CONTEXT.get(dialect, CONTEXT_AR)
                    add(context + seed, intent, dialect, special or "paraphrase", HARDER[level], base, "extra context first")
                if not latin:
                    add(informal(seed), intent, dialect, special or "edge_case", HARDER[level], base, "informal spelling")
                    if typo(seed) != seed:
                        add(typo(seed), intent, dialect, special or "edge_case", HARDER[level], base, "typo")
    for conv in CONVERSATIONS:
        for dialect, turns in conv["turns"].items():
            add(turns[-1], conv["intent"], dialect, "multi_turn", "hard", notes="needs the conversation",
                history=turns[:-1], must_include=conv.get("must_include"))
    return cases


def build_holdout() -> list[Case]:
    level = {**LEVEL, "maghrebi": "hard"}
    return [make_case(f"HO-{n:03d}", q, intent, dialect, INTENTS[intent].get("test_type", "happy_path"), level[dialect],
                      notes="held out") for n, (intent, dialect, q) in enumerate(HOLDOUT, start=1)]


def training_questions() -> list[str]:
    return list(TRAINING_FAQ)
