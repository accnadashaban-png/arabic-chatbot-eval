"""Expand the seed questions into a golden dataset with deliberate variants.

Language policy (what language a good answer must be in):
- Arabic script in any dialect -> Arabic
- Franco (Arabic in Latin letters) -> Arabic: the user speaks Arabic, only the keyboard is Latin
- English -> English
- Code-switching (Arabic with English words) -> Arabic: these are Arabic speakers using English terms
"""
from __future__ import annotations

import re

from chatbot_eval.dataset import Case
from chatbot_eval.templates import CONTEXT, CONTEXT_AR, GREETING, GREETING_AR, INTENTS, TRAINING_FAQ

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


def build_cases() -> list[Case]:
    cases: list[Case] = []

    def add(question: str, intent: str, dialect: str, test_type: str, difficulty: str, variant_of: str = "", notes: str = "") -> str:
        spec = INTENTS[intent]
        case_id = f"GS-{len(cases) + 1:04d}"
        cases.append(Case(
            id=case_id, question=question, dialect=dialect, intent=intent,  # type: ignore[arg-type]
            test_type=test_type, difficulty=difficulty,  # type: ignore[arg-type]
            expected_language=expected_language(dialect),  # type: ignore[arg-type]
            expected_behavior=spec["behavior"], must_include=spec["must_include"],
            must_not_include=spec.get("must_not_include", []), critical=spec.get("critical", False),
            variant_of=variant_of, notes=notes))
        return case_id

    for intent, spec in INTENTS.items():
        special = spec.get("test_type")
        for dialect, seeds in spec["seeds"].items():
            level = "hard" if special == "adversarial" else LEVEL[dialect]
            for n, seed in enumerate(seeds):
                base = add(seed, intent, dialect, special or "happy_path", level)
                latin = dialect in LATIN_SCRIPT
                greeting = GREETING.get(dialect, GREETING_AR)
                add(greeting + seed, intent, dialect, special or "paraphrase", level, base, "greeting first")
                if n == 0:
                    context = CONTEXT.get(dialect, CONTEXT_AR)
                    add(context + seed, intent, dialect, special or "paraphrase", HARDER[level], base, "extra context first")
                if not latin:
                    add(informal(seed), intent, dialect, special or "edge_case", HARDER[level], base, "informal spelling")
    return cases


def training_questions() -> list[str]:
    return list(TRAINING_FAQ)
