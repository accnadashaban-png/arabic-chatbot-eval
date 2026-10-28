"""Run a golden set against a bot and store the run, so later rounds can be compared with it."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chatbot_eval.bots import Bot
from chatbot_eval.checks import CaseResult, check
from chatbot_eval.dataset import Case, fingerprint


@dataclass
class Run:
    run_id: str
    bot: str
    dataset: str          # fingerprint of the golden set used
    started_at: str
    results: list[CaseResult] = field(default_factory=list)
    label: str = ""       # e.g. "UAT round 1"

    def by_id(self) -> dict[str, CaseResult]:
        return {r.case_id: r for r in self.results}

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"run_id": self.run_id, "bot": self.bot, "dataset": self.dataset, "started_at": self.started_at,
                "label": self.label, "cases": len(self.results)}
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"meta": meta}, ensure_ascii=False) + "\n")
            for r in self.results:
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        return path

    @classmethod
    def load(cls, path: str | Path) -> Run:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        meta: dict[str, Any] = json.loads(lines[0])["meta"]
        results = [CaseResult(**json.loads(line)) for line in lines[1:] if line.strip()]
        return cls(meta["run_id"], meta["bot"], meta["dataset"], meta["started_at"], results, meta.get("label", ""))


def run(cases: list[Case], bot: Bot, workers: int = 4, label: str = "") -> Run:
    """Ask every question (in parallel, order kept) and check every answer. One failing call never stops the run."""
    def one(case: Case) -> CaseResult:
        history: list[dict[str, str]] = []
        start = time.perf_counter()
        try:
            for turn in case.history:  # replay earlier turns with the bot's own replies; only the last answer is checked
                history += [{"role": "user", "content": turn}, {"role": "assistant", "content": bot.ask(turn, list(history))}]
            start = time.perf_counter()
            answer, error = bot.ask(case.question, history), ""
        except Exception as exc:  # noqa: BLE001 - record and continue
            answer, error = "", f"{type(exc).__name__}: {exc}"[:300]
        return check(case, answer, (time.perf_counter() - start) * 1000, error)

    started = datetime.now(UTC)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(one, cases))
    run_id = f"{started:%Y%m%d-%H%M%S}-{bot.name}"
    return Run(run_id, bot.name, fingerprint(cases), started.isoformat(timespec="seconds"), results, label)
