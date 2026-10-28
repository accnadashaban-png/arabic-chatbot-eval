"""Command line.

    python -m chatbot_eval demo                               # both demo rounds, reports in reports/
    python -m chatbot_eval build                              # regenerate data/golden.csv from the seeds
    python -m chatbot_eval validate                           # schema, duplicates, coverage, contamination
    python -m chatbot_eval run --bot http --label "UAT round 1"   # a real bot (BOT_URL, BOT_API_KEY, BOT_MODEL)
    python -m chatbot_eval report runs/B.jsonl --compare runs/A.jsonl --xlsx report.xlsx --strict
    python -m chatbot_eval review-export runs/B.jsonl review.xlsx
    python -m chatbot_eval review-import runs/B.jsonl review.xlsx
    python -m chatbot_eval judge runs/B.jsonl                 # optional LLM judge (JUDGE_URL, JUDGE_API_KEY, JUDGE_MODEL)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from chatbot_eval.bots import Bot, BotError, HttpBot, MockBot
from chatbot_eval.builder import build_cases, build_holdout, training_questions
from chatbot_eval.compare import compare
from chatbot_eval.dataset import DatasetError, balance, contamination, coverage_gaps, load_cases, near_duplicates, save_cases
from chatbot_eval.gates import Gates, decide
from chatbot_eval.judge import JudgeError, OpenAICompatibleModel, grade
from chatbot_eval.metrics import summarize
from chatbot_eval.report import write_excel, write_markdown
from chatbot_eval.review import agreement, export_review, import_review
from chatbot_eval.runner import Run, run

ROOT = Path(__file__).resolve().parent.parent
GOLDEN, TRAINING, GATES = ROOT / "data" / "golden.csv", ROOT / "data" / "training_faq.csv", ROOT / "data" / "gates.json"
HOLDOUT = ROOT / "data" / "holdout.csv"


def load_training(path: Path) -> list[str]:
    """Questions the bot was built or trained on: a CSV with a `question` column, or a knowledge-base FAQ whose
    `questions` column lists several, separated by "|"."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        out: list[str] = []
        for row in csv.DictReader(f):
            out += [row["question"]] if row.get("question") else [q for q in (row.get("questions") or "").split("|") if q]
        return out


def cmd_build(_: argparse.Namespace) -> int:
    cases = build_cases()
    save_cases(cases, GOLDEN)
    save_cases(build_holdout(), HOLDOUT)
    with TRAINING.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["question"])
        writer.writerows([q] for q in training_questions())
    print(f"wrote {len(cases)} cases to {GOLDEN.relative_to(ROOT)} and the held-out set to {HOLDOUT.relative_to(ROOT)}")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    cases = load_cases(a.data)
    dups, gaps = near_duplicates(cases), coverage_gaps(cases, a.min_per_cell)
    leaks = contamination(cases, load_training(Path(a.training)))
    print(f"{len(cases)} cases · valid schema")
    for tag, counts in balance(cases).items():
        print(f"  {tag}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"near duplicates: {len(dups)}" + "".join(f"\n  {x} ~ {y} ({s})" for x, y, s in dups[:20]))
    print(f"coverage gaps (intent x dialect < {a.min_per_cell}): {len(gaps)}" + "".join(f"\n  {i} / {d}: {n}" for i, d, n in gaps[:20]))
    print(f"in the training data (contamination): {len(leaks)}" + "".join(f"\n  {i} ~ \"{t}\" ({s})" for i, t, s in leaks[:20]))
    return 1 if a.strict and (dups or gaps or leaks) else 0


def make_bot(spec: str) -> Bot:
    if spec.startswith("mock"):
        return MockBot(int(spec.split(":v")[1]) if ":v" in spec else 1)
    if spec == "http":
        return HttpBot.from_env()
    if spec == "support":
        from supportbot.bot import SupportBot  # the bot shipped with this repo; the evaluator does not depend on it
        return SupportBot()
    raise SystemExit(f"unknown bot {spec!r}: use mock, mock:v2, support or http")


def cmd_run(a: argparse.Namespace) -> int:
    cases = load_cases(a.data)
    result = run(cases, make_bot(a.bot), a.workers, a.label)
    path = result.save(a.out or ROOT / "runs" / f"{result.run_id}.jsonl")
    s = summarize(result, cases)
    print(f"{s.total} cases · pass {s.pass_rate:.1%} · language {s.language_rate:.1%} · critical {len(s.critical_failures)} · {path}")
    return 0


def report(run_path: str, data: str, gates_path: str | None, compare_path: str | None, xlsx: str | None, md: str | None) -> bool:
    cases, current = load_cases(data), Run.load(run_path)
    s = summarize(current, cases)
    d = decide(s, Gates.load(gates_path))
    comparison = compare(Run.load(compare_path), current, cases) if compare_path else None
    if xlsx:
        write_excel(xlsx, current, cases, s, d, comparison)
    if md:
        write_markdown(md, s, d, comparison, cases, current)
    print(f"{s.label or s.run_id}: {d.label} · pass {s.pass_rate:.1%} · critical {len(s.critical_failures)}")
    for g in d.blockers:
        print(f"  blocked by {g.name}: {g.value} (needs {g.threshold})")
    if comparison:
        c = comparison
        print(f"  vs {c.before}: fixed {len(c.fixed)}, regressed {len(c.regressed)}, p = {c.p_value:.2g}")
    return d.go


def cmd_report(a: argparse.Namespace) -> int:
    go = report(a.run, a.data, a.gates, a.compare, a.xlsx, a.md)
    return 1 if a.strict and not go else 0


def cmd_demo(_: argparse.Namespace) -> int:
    cases = load_cases(GOLDEN)
    runs = ROOT / "runs"
    first = run(cases, MockBot(1), label="UAT round 1").save(runs / "demo-round1.jsonl")
    second = run(cases, MockBot(2), label="UAT round 2").save(runs / "demo-round2.jsonl")
    out = ROOT / "reports"
    report(str(first), str(GOLDEN), str(GATES), None, str(out / "demo-round1.xlsx"), str(out / "demo-round1.md"))
    report(str(second), str(GOLDEN), str(GATES), str(first), str(out / "demo-round2.xlsx"), str(out / "demo-round2.md"))
    bot = make_bot("support")
    dev = run(cases, bot, label="Support bot, development set").save(runs / "support-dev.jsonl")
    held = run(load_cases(HOLDOUT), bot, label="Support bot, held-out set").save(runs / "support-holdout.jsonl")
    report(str(dev), str(GOLDEN), str(GATES), None, str(out / "support-dev.xlsx"), str(out / "support-dev.md"))
    report(str(held), str(HOLDOUT), str(GATES), None, str(out / "support-holdout.xlsx"), str(out / "support-holdout.md"))
    return 0


def cmd_review_export(a: argparse.Namespace) -> int:
    path = export_review(Run.load(a.run), load_cases(a.data), a.out)
    print(f"review sheet: {path} (fill in human_verdict: pass or fail)")
    return 0


def cmd_review_import(a: argparse.Namespace) -> int:
    current, human = Run.load(a.run), import_review(a.sheet)
    auto = {r.case_id: "pass" if r.passed else "fail" for r in current.results}
    ag = agreement(auto, human)
    print(f"{ag.reviewed} reviewed · agreement {ag.accuracy:.1%} · Cohen's kappa {ag.kappa:.2f}")
    print(f"  automatic checks too lenient (passed, people failed): {ag.auto_too_lenient or 'none'}")
    print(f"  automatic checks too strict (failed, people passed): {ag.auto_too_strict or 'none'}")
    return 0


def cmd_judge(a: argparse.Namespace) -> int:
    model, current = OpenAICompatibleModel.from_env(), Run.load(a.run)
    by_case = {c.id: c for c in load_cases(a.data)}
    out = Path(a.out or Path(a.run).with_suffix(".judge.jsonl"))
    graded = 0
    with out.open("w", encoding="utf-8") as f:
        for r in current.results[: a.limit]:
            if r.error:
                continue
            try:
                g = grade(model, by_case[r.case_id], r.answer)
            except JudgeError as exc:
                print(f"  skipped: {exc}")
                continue
            f.write(json.dumps(g.__dict__, ensure_ascii=False) + "\n")
            graded += 1
    print(f"graded {graded} answers: {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chatbot_eval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    v = sub.add_parser("validate")
    v.add_argument("--data", default=str(GOLDEN))
    v.add_argument("--training", default=str(TRAINING))
    v.add_argument("--min-per-cell", type=int, default=2)
    v.add_argument("--strict", action="store_true", help="exit 1 on duplicates, gaps or contamination")
    v.set_defaults(fn=cmd_validate)
    r = sub.add_parser("run")
    r.add_argument("--data", default=str(GOLDEN))
    r.add_argument("--bot", default="mock", help="mock, mock:v2, support or http")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--label", default="")
    r.add_argument("--out")
    r.set_defaults(fn=cmd_run)
    rp = sub.add_parser("report")
    rp.add_argument("run")
    rp.add_argument("--data", default=str(GOLDEN))
    rp.add_argument("--gates", default=str(GATES))
    rp.add_argument("--compare", help="an earlier run on the same golden set")
    rp.add_argument("--xlsx")
    rp.add_argument("--md")
    rp.add_argument("--strict", action="store_true", help="exit 1 on NO-GO (for CI)")
    rp.set_defaults(fn=cmd_report)
    re_ = sub.add_parser("review-export")
    re_.add_argument("run")
    re_.add_argument("out")
    re_.add_argument("--data", default=str(GOLDEN))
    re_.set_defaults(fn=cmd_review_export)
    ri = sub.add_parser("review-import")
    ri.add_argument("run")
    ri.add_argument("sheet")
    ri.set_defaults(fn=cmd_review_import)
    j = sub.add_parser("judge")
    j.add_argument("run")
    j.add_argument("--data", default=str(GOLDEN))
    j.add_argument("--limit", type=int, default=100)
    j.add_argument("--out")
    j.set_defaults(fn=cmd_judge)
    args = p.parse_args(argv)
    try:
        return int(args.fn(args))
    except (DatasetError, BotError, JudgeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
