"""Turn a run into the numbers a launch decision needs."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from chatbot_eval.checks import REASONS, is_critical_failure
from chatbot_eval.dataset import Case
from chatbot_eval.runner import Run
from chatbot_eval.stats import percentile, wilson

TAGS = ("dialect", "intent", "test_type", "difficulty", "expected_behavior")


@dataclass
class Slice:
    tag: str
    value: str
    total: int
    passed: int

    @property
    def rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.passed, self.total)


@dataclass
class Summary:
    total: int
    passed: int
    language_ok: int
    critical_failures: list[str]
    reasons: dict[str, int]
    slices: dict[str, list[Slice]]
    p50_ms: float | None
    p95_ms: float | None
    dataset: str
    bot: str
    run_id: str
    label: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def language_rate(self) -> float:
        return self.language_ok / self.total if self.total else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.passed, self.total)


def summarize(run: Run, cases: list[Case]) -> Summary:
    by_id = {c.id: c for c in cases}
    pairs = [(by_id[r.case_id], r) for r in run.results if r.case_id in by_id]
    reasons = Counter(reason for _, r in pairs for reason in r.failed)
    slices: dict[str, list[Slice]] = {}
    for tag in TAGS:
        groups: dict[str, list[bool]] = {}
        for c, r in pairs:
            groups.setdefault(str(getattr(c, tag)), []).append(r.passed)
        slices[tag] = sorted((Slice(tag, v, len(g), sum(g)) for v, g in groups.items()), key=lambda s: (s.rate, -s.total))
    latencies = [r.latency_ms for _, r in pairs if not r.error]
    return Summary(
        total=len(pairs), passed=sum(r.passed for _, r in pairs),
        language_ok=sum("language" not in r.failed and not r.error for _, r in pairs),
        critical_failures=[c.id for c, r in pairs if is_critical_failure(c, r)],
        reasons={k: reasons.get(k, 0) for k in REASONS}, slices=slices,
        p50_ms=percentile(latencies, 50), p95_ms=percentile(latencies, 95),
        dataset=run.dataset, bot=run.bot, run_id=run.run_id, label=run.label)
