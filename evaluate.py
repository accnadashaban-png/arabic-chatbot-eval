"""Run a golden test set against a chatbot and write an Excel evaluation report.

Usage:
    python evaluate.py --mock                      # demo with a built-in fake bot
    python evaluate.py --data data/golden_sample.csv --out report.xlsx

Real bot: set BOT_URL (an OpenAI-compatible /chat/completions endpoint),
BOT_API_KEY and optionally BOT_MODEL in your environment or a .env file.
"""
import argparse
import os
import re
import time

import pandas as pd
import requests

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Return 'ar' or 'en' from the share of Arabic vs Latin letters."""
    ar = len(ARABIC.findall(text or ""))
    en = len(LATIN.findall(text or ""))
    if ar == 0 and en == 0:
        return "unknown"
    return "ar" if ar >= en else "en"


def keywords_found(answer: str, expected: str) -> bool:
    """True if any expected keyword (separated by |) appears in the answer."""
    if not isinstance(expected, str) or not expected.strip():
        return True
    answer = (answer or "").lower()
    return any(k.strip().lower() in answer for k in expected.split("|"))


def mock_bot(question: str) -> str:
    """A fake bot for demos. It sometimes answers Arabic questions in English,
    so the report shows how language mismatches are caught."""
    q = question.lower()
    if "الغي" in q or "ألغي" in q or "cancel" in q:
        return "You can cancel any time from Settings > Subscription."
    if "سعر" in q or "بكام" in q or "price" in q or "kam" in q:
        return "الاشتراك الشهري بسعر 10 دولار، والسنوي بسعر 100 دولار."
    if "شهادة" in q or "certificate" in q:
        return "نعم، تحصل على شهادة بعد إتمام الكورس." if detect_language(question) == "ar" else "Yes, you get a certificate after finishing the course."
    if "باسورد" in q or "كلمة المرور" in q or "password" in q:
        return "اضغط على (نسيت كلمة المرور) وهيوصلك لينك على الإيميل." if detect_language(question) == "ar" else "Click 'Forgot password' and we'll email you a reset link."
    return "عذرًا، لا أملك معلومات عن هذا الموضوع. هل تريد التحدث مع فريق الدعم؟" if detect_language(question) == "ar" else "Sorry, I can't help with that. Would you like to talk to support?"


def real_bot(question: str) -> str:
    url = os.environ["BOT_URL"]
    headers = {"Authorization": f"Bearer {os.environ.get('BOT_API_KEY', '')}"}
    body = {
        "model": os.environ.get("BOT_MODEL", "default"),
        "messages": [{"role": "user", "content": question}],
    }
    r = requests.post(url, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def run(data_path: str, out_path: str, use_mock: bool) -> pd.DataFrame:
    cases = pd.read_csv(data_path)
    ask = mock_bot if use_mock else real_bot
    rows = []
    for case in cases.itertuples(index=False):
        start = time.perf_counter()
        try:
            answer, error = ask(case.question), ""
        except Exception as exc:  # keep going if one call fails
            answer, error = "", str(exc)
        seconds = round(time.perf_counter() - start, 2)

        answer_lang = detect_language(answer)
        lang_ok = answer_lang == case.expected_language
        kw_ok = keywords_found(answer, case.expected_keywords)
        rows.append({
            **case._asdict(),
            "answer": answer,
            "answer_language": answer_lang,
            "language_match": lang_ok,
            "keywords_found": kw_ok,
            "passed": lang_ok and kw_ok and not error,
            "seconds": seconds,
            "error": error,
        })

    results = pd.DataFrame(rows)
    write_report(results, out_path)
    return results


def write_report(results: pd.DataFrame, out_path: str) -> None:
    summary = pd.DataFrame({
        "metric": ["test cases", "pass rate", "language mismatches", "keyword misses", "errors"],
        "value": [
            len(results),
            f"{results['passed'].mean():.0%}",
            int((~results["language_match"]).sum()),
            int((~results["keywords_found"]).sum()),
            int((results["error"] != "").sum()),
        ],
    })
    with pd.ExcelWriter(out_path, engine="openpyxl") as xl:
        summary.to_excel(xl, sheet_name="Summary", index=False)
        for tag in ["dialect", "intent", "test_type", "difficulty"]:
            by_tag = (results.groupby(tag)["passed"].agg(["count", "mean"])
                      .rename(columns={"count": "cases", "mean": "pass_rate"}).reset_index())
            by_tag.to_excel(xl, sheet_name=f"By {tag}", index=False)
        results[~results["passed"]].to_excel(xl, sheet_name="Failures", index=False)
        results.to_excel(xl, sheet_name="All results", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data/golden_sample.csv")
    parser.add_argument("--out", default="evaluation_report.xlsx")
    parser.add_argument("--mock", action="store_true", help="use the built-in fake bot")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    results = run(args.data, args.out, args.mock)
    print(f"{len(results)} cases · pass rate {results['passed'].mean():.0%} · "
          f"language mismatches {int((~results['language_match']).sum())} · report: {args.out}")


if __name__ == "__main__":
    main()
