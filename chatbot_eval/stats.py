"""Small, exact statistics for honest evaluation reports (standard library only)."""
from __future__ import annotations

import math
from collections import Counter


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a pass rate. Honest for small slices, unlike +/- 1.96 * standard error."""
    if total == 0:
        return (0.0, 1.0)
    p = passed / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(fixed: int, regressed: int) -> float:
    """Two-sided exact McNemar p-value: is round B really different from round A on the same questions?
    Only the questions that changed outcome count; under "no change" each is a coin flip."""
    n = fixed + regressed
    if n == 0:
        return 1.0
    k = min(fixed, regressed)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Agreement between two raters beyond chance (1 = perfect, 0 = chance level)."""
    if len(a) != len(b) or not a:
        raise ValueError("need two label lists of the same, non-zero length")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]
