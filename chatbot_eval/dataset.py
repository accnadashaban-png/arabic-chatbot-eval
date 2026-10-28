"""Golden dataset: the schema of a test case, loading and saving, and dataset quality checks.

CSV encoding of the list columns:
    history            earlier user messages of a multi-turn case, separated by "||"
    must_include       groups separated by ";", options inside a group by "|"
                       every group must be matched by at least one option: "إلغاء|cancel;الإعدادات|Settings"
    must_not_include   options separated by "|"; none may appear
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from chatbot_eval.text import normalize, similarity

Dialect = Literal["egyptian", "gulf", "levantine", "maghrebi", "msa", "english", "franco", "mixed"]
TestType = Literal["happy_path", "paraphrase", "edge_case", "out_of_scope", "adversarial", "multi_turn"]
Behavior = Literal["answer", "refuse", "handoff", "clarify"]
DIALECTS: tuple[str, ...] = Dialect.__args__  # type: ignore[attr-defined]
COLUMNS = ["id", "question", "dialect", "intent", "test_type", "difficulty", "expected_language", "expected_behavior",
           "must_include", "must_not_include", "critical", "variant_of", "history", "notes"]


class Case(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=2000)
    dialect: Dialect
    intent: str = Field(min_length=1, max_length=40)
    test_type: TestType
    difficulty: Literal["easy", "medium", "hard"]
    expected_language: Literal["ar", "en"]
    expected_behavior: Behavior = "answer"
    must_include: list[list[str]] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    critical: bool = False  # a failure here blocks launch on its own (safety, privacy)
    variant_of: str = ""    # id of the case this one rephrases on purpose (spelling, greeting, context)
    history: list[str] = Field(default_factory=list)  # earlier user messages in the same conversation
    notes: str = ""

    @field_validator("must_include")
    @classmethod
    def no_empty_groups(cls, v: list[list[str]]) -> list[list[str]]:
        if any(not [o for o in g if o.strip()] for g in v):
            raise ValueError("every must_include group needs at least one option")
        return v

    def to_row(self) -> dict[str, str]:
        return {**{k: str(getattr(self, k)) for k in ("id", "question", "dialect", "intent", "test_type", "difficulty",
                                                    "expected_language", "expected_behavior", "variant_of", "notes")},
                "must_include": ";".join("|".join(g) for g in self.must_include),
                "must_not_include": "|".join(self.must_not_include), "critical": "yes" if self.critical else "",
                "history": " || ".join(self.history)}


class DatasetError(ValueError):
    """Raised with the file line of the first invalid row."""


def _parse_row(row: dict[str, str]) -> Case:
    def split(value: str | None, sep: str) -> list[str]:
        return [p.strip() for p in (value or "").split(sep) if p.strip()]
    listed = ("must_include", "must_not_include", "critical", "history")
    return Case(**{**{k: (row.get(k) or "").strip() for k in COLUMNS if k not in listed},
                   "expected_behavior": (row.get("expected_behavior") or "answer").strip(),
                   "must_include": [split(g, "|") for g in split(row.get("must_include"), ";")],
                   "must_not_include": split(row.get("must_not_include"), "|"),
                   "critical": (row.get("critical") or "").strip().lower() in ("yes", "true", "1"),
                   "history": split(row.get("history"), "||")})


def load_cases(path: str | Path) -> list[Case]:
    cases: list[Case] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            try:
                cases.append(_parse_row(row))
            except ValidationError as exc:
                first = exc.errors()[0]
                raise DatasetError(f"{Path(path).name} line {line}: {'.'.join(map(str, first['loc']))}: {first['msg']}") from exc
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        dup = next(i for i, n in Counter(ids).items() if n > 1)
        raise DatasetError(f"{Path(path).name}: duplicate id {dup}")
    return cases


def save_cases(cases: list[Case], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(c.to_row() for c in cases)


def fingerprint(cases: list[Case]) -> str:
    """Short hash of the dataset, stored with every run so results are only compared on the same questions."""
    h = hashlib.sha256()
    for c in cases:
        h.update(repr(sorted(c.to_row().items())).encode("utf-8"))
    return h.hexdigest()[:12]


# ---------- dataset quality ----------

def near_duplicates(cases: list[Case], threshold: float = 0.9) -> list[tuple[str, str, float]]:
    """Pairs of questions with the same intent that are (almost) the same text after normalization.
    Duplicates inflate a score without testing anything new. Declared variants are skipped."""
    by_intent: dict[str, list[Case]] = defaultdict(list)
    for c in cases:
        by_intent[c.intent].append(c)
    def root(c: Case) -> str:
        return c.variant_of or c.id
    pairs = []
    for group in by_intent.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if root(a) == root(b):
                    continue  # declared variants of the same question are meant to be close
                x, y = " ".join([*a.history, a.question]), " ".join([*b.history, b.question])  # the whole conversation
                s = 1.0 if normalize(x) == normalize(y) else similarity(x, y)
                if s >= threshold:
                    pairs.append((a.id, b.id, round(s, 3)))
    return pairs


def coverage(cases: list[Case]) -> dict[str, dict[str, int]]:
    """intent -> dialect -> number of cases."""
    matrix: dict[str, dict[str, int]] = {}
    for c in cases:
        matrix.setdefault(c.intent, dict.fromkeys(DIALECTS, 0))[c.dialect] += 1
    return matrix


def coverage_gaps(cases: list[Case], minimum: int = 2, skip: tuple[str, ...] = ("security",)) -> list[tuple[str, str, int]]:
    """Intent and dialect combinations with fewer than `minimum` cases."""
    return [(intent, d, n) for intent, row in sorted(coverage(cases).items()) if intent not in skip
            for d, n in row.items() if n < minimum]


def contamination(cases: list[Case], training_questions: list[str], threshold: float = 0.85) -> list[tuple[str, str, float]]:
    """Golden questions that (nearly) appear in the bot's training or FAQ data.
    A bot that memorized its training examples passes them without understanding the question."""
    hits = []
    for c in cases:
        best = max(((similarity(c.question, t), t) for t in training_questions), default=(0.0, ""))
        if best[0] >= threshold:
            hits.append((c.id, best[1], round(best[0], 3)))
    return hits


def balance(cases: list[Case]) -> dict[str, dict[str, int]]:
    return {tag: dict(Counter(getattr(c, tag) for c in cases).most_common())
            for tag in ("dialect", "intent", "test_type", "difficulty", "expected_behavior")}
