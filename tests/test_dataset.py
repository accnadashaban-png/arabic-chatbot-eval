from pathlib import Path

import pytest

from chatbot_eval.builder import build_cases, informal, training_questions
from chatbot_eval.dataset import (
    DIALECTS,
    Case,
    DatasetError,
    contamination,
    coverage,
    coverage_gaps,
    fingerprint,
    load_cases,
    near_duplicates,
    save_cases,
)

GOLDEN = Path(__file__).resolve().parent.parent / "data" / "golden.csv"


def case(i: str, q: str, intent: str = "pricing", dialect: str = "egyptian", **kw) -> Case:
    return Case(id=i, question=q, dialect=dialect, intent=intent, test_type="happy_path", difficulty="easy",  # type: ignore[arg-type]
                expected_language="ar", **kw)


def test_round_trip_keeps_every_field(tmp_path: Path) -> None:
    c = case("A1", "الاشتراك بكام؟", must_include=[["10"], ["دولار", "$"]], must_not_include=["CANARY"], critical=True,
             expected_behavior="refuse", variant_of="A0", notes="note")
    save_cases([c], tmp_path / "g.csv")
    assert load_cases(tmp_path / "g.csv") == [c]


def test_errors_name_the_line(tmp_path: Path) -> None:
    good = case("A1", "سؤال").to_row()
    path = tmp_path / "g.csv"
    save_cases([case("A1", "سؤال"), case("A2", "سؤال تاني")], path)
    text = path.read_text(encoding="utf-8").replace("A2,سؤال تاني,egyptian", "A2,سؤال تاني,klingon")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DatasetError, match="line 3: dialect"):
        load_cases(path)
    save_cases([case("A1", "x"), case("A1", "y")], path)
    with pytest.raises(DatasetError, match="duplicate id A1"):
        load_cases(path)
    assert good["must_include"] == ""


def test_near_duplicates_ignore_declared_variants() -> None:
    cases = [case("A1", "الاشتراك بكام في الشهر؟"), case("A2", "الإشتراك بكام فى الشهر"),
             case("A3", "الاشتراك بكام في الشهر", variant_of="A1"), case("A4", "الاشتراك بكام في الشهر؟", intent="refund")]
    pairs = {(a, b) for a, b, _ in near_duplicates(cases)}
    assert pairs == {("A1", "A2"), ("A2", "A3")}  # A3 is a declared variant of A1; A4 is another intent


def test_coverage_and_contamination() -> None:
    cases = [case("A1", "بكام؟"), case("A2", "How much?", dialect="english")]
    assert coverage(cases)["pricing"]["egyptian"] == 1
    assert ("pricing", "gulf", 0) in coverage_gaps(cases, minimum=1)
    assert contamination(cases, ["how much?", "unrelated question"]) == [("A2", "how much?", 1.0)]


def test_built_dataset_is_balanced_clean_and_committed() -> None:
    cases = build_cases()
    assert len(cases) == 624 and len({c.id for c in cases}) == len(cases)
    assert not near_duplicates(cases) and not coverage_gaps(cases)
    assert all(n >= 5 for row in coverage(cases).values() for n in row.values())
    assert {c.dialect for c in cases} == set(DIALECTS)
    assert all(c.expected_language == ("en" if c.dialect == "english" else "ar") for c in cases)
    assert all(c.critical == (c.intent == "security") for c in cases)
    assert len(contamination(cases, training_questions())) == 3  # planted on purpose for the demo
    assert fingerprint(load_cases(GOLDEN)) == fingerprint(cases), "data/golden.csv is stale: run python -m chatbot_eval build"


def test_informal_spelling_variant() -> None:
    assert informal("عايز ألغي الاشتراك إزاي؟") == "عايززز الغي الاشتراك ازاي"
    assert informal("الـ monthly plan بكام؟") == "الـ monthly plan بكاممم"
