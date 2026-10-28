"""Compare two rounds on the same golden set: what got fixed, what regressed, and whether it is real."""
from __future__ import annotations

from dataclasses import dataclass

from chatbot_eval.dataset import Case
from chatbot_eval.runner import Run
from chatbot_eval.stats import mcnemar_exact


class ComparisonError(ValueError):
    pass


@dataclass
class TagDelta:
    tag: str
    value: str
    total: int
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass
class Comparison:
    before: str
    after: str
    fixed: list[str]
    regressed: list[str]
    still_failing: list[str]
    still_passing: int
    p_value: float
    deltas: list[TagDelta]

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def compare(before: Run, after: Run, cases: list[Case]) -> Comparison:
    if before.dataset != after.dataset:
        raise ComparisonError(f"the runs used different golden sets ({before.dataset} vs {after.dataset}); "
                              "compare rounds only on the same questions")
    a, b = before.by_id(), after.by_id()
    ids = [c.id for c in cases if c.id in a and c.id in b]
    fixed = [i for i in ids if not a[i].passed and b[i].passed]
    regressed = [i for i in ids if a[i].passed and not b[i].passed]
    still_failing = [i for i in ids if not a[i].passed and not b[i].passed]
    deltas = []
    by_id = {c.id: c for c in cases}
    for tag in ("dialect", "intent"):
        groups: dict[str, list[str]] = {}
        for i in ids:
            groups.setdefault(str(getattr(by_id[i], tag)), []).append(i)
        for value, members in groups.items():
            deltas.append(TagDelta(tag, value, len(members), sum(a[i].passed for i in members) / len(members),
                                   sum(b[i].passed for i in members) / len(members)))
    deltas.sort(key=lambda d: d.delta)
    return Comparison(before.label or before.run_id, after.label or after.run_id, fixed, regressed, still_failing,
                      len(ids) - len(fixed) - len(regressed) - len(still_failing), mcnemar_exact(len(fixed), len(regressed)),
                      deltas)
