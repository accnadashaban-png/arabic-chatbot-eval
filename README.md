# arabic-chatbot-eval

A small, practical toolkit to **test an Arabic + English chatbot before launch**. It runs a tagged golden test set against your bot, checks every answer, and writes an Excel report broken down by dialect, intent, test type and difficulty.

Built from the process I use for pre-launch chatbot evaluation. All data in this repo is **synthetic** (a fictional online-course platform).

## What it checks

| Check | Why it matters |
|---|---|
| **Language match** | The most common bilingual failure: an Arabic question answered in English, or the reverse |
| **Expected content** | The answer contains at least one expected keyword |
| **Errors & speed** | Failed calls and response time per question |

## Golden dataset format

`data/golden_sample.csv`. One row per test case:

| Column | Example |
|---|---|
| `question` | `عايز ألغي الاشتراك إزاي؟` |
| `dialect` | Egyptian · Gulf · MSA · English · Franco · Mixed |
| `intent` | cancellation · pricing · account · out_of_scope · security |
| `test_type` | happy_path · edge_case · out_of_scope · adversarial |
| `difficulty` | easy · medium · hard |
| `expected_language` | `ar` or `en` |
| `expected_keywords` | `إلغاء\|الإعدادات\|Settings` (any one must appear) |

## Quick start

```bash
pip install -r requirements.txt
python evaluate.py --mock
```

`--mock` uses a built-in fake bot that makes realistic mistakes, so you can see the report right away.

### Test your own bot

Point it at any OpenAI-compatible `/chat/completions` endpoint:

```bash
cp .env.example .env   # then fill in BOT_URL, BOT_API_KEY, BOT_MODEL
python evaluate.py --data data/golden_sample.csv --out report.xlsx
```

## The report

`evaluation_report.xlsx` has these sheets:

- **Summary:** pass rate, language mismatches, keyword misses, errors
- **By dialect / By intent / By test_type / By difficulty:** where the bot fails
- **Failures:** every failed case with the bot's answer, ready for review
- **All results**

One overall score hides real problems. A bot can do well in English and still fail dialect questions, which is why every result is broken down by tag.

## Tests

```bash
pytest -q
```

## Read more

[How to Evaluate an Arabic Chatbot Before Launch](https://nadashaaban.com/arabic-chatbot-evaluation.html)

---

Made by [Nada Shaban](https://nadashaaban.com) · MIT License
