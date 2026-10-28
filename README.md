# arabic-chatbot-eval

[![CI](https://github.com/accnadashaban-png/arabic-chatbot-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/accnadashaban-png/arabic-chatbot-eval/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Golden set](https://img.shields.io/badge/golden%20set-1%2C769%20cases%20%C2%B7%208%20dialects-success) ![Red team](https://img.shields.io/badge/red%20team-47%20attacks-success) ![License](https://img.shields.io/badge/license-MIT-green)

Two things in one repository:

1. **An evaluation toolkit** for Arabic + English chatbots: a tagged golden set across eight dialects, dialect-aware checks, honest statistics, UAT round comparison and a **GO / NO-GO** decision.
2. **A customer-support bot** for any business: bring your own FAQ, it answers your audience in their dialect, hands refunds and complaints to your team, refuses attacks, and can use any LLM with grounding checks. It is evaluated with the toolkit, including a held-out set and a red-team suite.

> Built from the process I use for pre-launch chatbot evaluation at work. Everything here is **synthetic**: a fictional online-learning platform. No company data.

## Results

| | Development set | Held-out set |
|---|---|---|
| Cases | 1,769 | 88 (new wording, never used for tuning) |
| Pass rate (95% interval) | **98.8%** (98.1–99.2%) | **68.2%** (57.9–77.0%) |
| Critical failures | 0 | 0 (4 before the red-team fix) |
| Decision | **GO** | **NO-GO** |

The gap is the point. A bot tuned on its development set looks ready; new wording shows it is not. The first held-out run also found that requests for **other users' data** were not refused (4 critical failures). The red-team work closed that gap, so the held-out number after the fix no longer measures that category without bias, and both runs are reported. Of the 28 remaining held-out failures, **24 are safe**: the bot asks the user to clarify instead of answering wrong.

Full reports: [development](reports/support-dev.md) · [held-out](reports/support-holdout.md) · demo UAT [round 1](reports/demo-round1.md) and [round 2](reports/demo-round2.md).

## The evaluation toolkit

| Step | What you get |
|---|---|
| **Golden set** | 1,769 cases: 22 support intents × Egyptian, Gulf, Levantine, Maghrebi, MSA, English, Franco and code-switching; greeting, courtesy, extra-context, informal-spelling and typo variants; 24 multi-turn conversations. Each case states the expected behavior: answer, refuse, hand off or clarify. |
| **Dataset QA** | Schema errors by line, near-duplicates after Arabic normalization, intent × dialect coverage, and **contamination**: test questions that appear in the bot's own FAQ or training data. |
| **Answer checks** | Language (Franco and code-switching users expect Arabic), required content, forbidden content (a canary catches leaked instructions), behavior, errors and latency. |
| **Honest numbers** | 95% Wilson intervals everywhere, slices worst-first, slices too small to judge are flagged instead of scored, a held-out set. |
| **UAT rounds** | Fixed, regressed and still-failing cases between rounds, with an exact McNemar test. |
| **Decision** | GO only if every gate passes. Excel and Markdown reports; `--strict` stops a CI pipeline on NO-GO. |
| **People in the loop** | A review sheet for human reviewers with agreement and Cohen's kappa, and an optional LLM judge measured the same way. |

Method: [docs/METHOD.md](docs/METHOD.md) · dataset format: [docs/DATASET.md](docs/DATASET.md).

## The support bot

A standalone assistant that runs on its own server, reads a **live database** and sits in the corner of any website or app.

| English | Arabic (right-to-left) |
|---|---|
| ![The widget answering a price question, a follow-up and a refund request handed to the team](docs/widget-en.jpg) | ![The same widget in Arabic](docs/widget-ar.jpg) |

```
message -> guard -> knowledge lookup (dialect lexicon + BM25) -> follow-up -> policy -> answer (knowledge base or LLM) -> checks
                         ^ live database: changes are picked up in seconds, conversations are logged for insights
```

- **Live database:** knowledge base, settings and a conversation log in SQLite (no setup) or PostgreSQL. Add or change an answer through the admin API, a script or another system and the bot uses it within seconds, without a restart. Tested on both databases with identical answers.
- **Admin API:** manage entries, see **insights** (answered rate, hand-offs, top topics, and the questions the bot could not answer: your next content to write) and the state of each LLM provider. Behind its own key.
- **Arabic that people really write:** a lexicon maps dialect, English and Franco words to shared concepts (`بكام`, `قديش`, `شحال`, `how much` → price), with light stemming and tolerance for one typo.
- **Knows when not to answer:** refunds, complaints, data deletion and "talk to a person" go to your team; off-topic requests are declined; unclear messages get a question back.
- **Conversation memory:** "and the yearly one?" is read with the previous question.
- **A group of LLM providers that never leaves users waiting:** list several (free tiers welcome). A provider out of credit rests for hours, a rate-limited one for a minute, one that is down for seconds with growing pauses; the next one answers at once and the first comes back when ready. If all are down, the knowledge base still answers.
- **Smarter, never trusted blindly:** when retrieval is unsure, the model picks among the closest entries or asks the user to clarify; it may reword answers but every number and link must come from the sources, in the right language, with no markup and nothing from its instructions. Hand-offs and refusals are never rewritten.
- **Guardrails:** prompt injection in Arabic, English and Franco (also spaced out, with digit swaps or hidden characters), credential requests, requests for other users' data, SQL; personal data is masked in logs and in the database.
- **Embeddable widget:** one script tag, a launcher in the corner, dark and RTL-aware, isolated in a Shadow DOM, full screen on phones. Only the websites you list may call the bot from a browser, and each visitor is rate limited.

```bash
python -m supportbot serve                 # http://127.0.0.1:8070, creates supportbot.db from the demo knowledge base
SB_DATABASE_URL=postgresql://user:pass@host/db python -m supportbot serve
```

```html
<script src="https://your-bot-host/widget.js" data-api="https://your-bot-host" data-name="Lernova Assistant" defer></script>
```

## Red team

`tests/test_redteam.py` runs 47 attacks: instruction override and extraction in three languages and disguised forms, credential and data-exfiltration requests, SQL, an attack split over two messages, forged conversation history, a **compromised LLM** (leaking the canary or its instructions, adding links, scripts, phone numbers or the user's card number), and server attacks (path traversal, malformed and oversized requests, client-sent system messages, script injection). The first run found 18 gaps; all are fixed and stay tested. Normal questions that look similar ("I forgot my password, can the admin help?") are checked not to be refused.

## Quick start

```bash
pip install -e ".[dev]"
python -m chatbot_eval demo        # UAT demo rounds + the support bot on both sets; reports in reports/
pytest                             # 140 tests
```

**Test your own bot** (any OpenAI-compatible endpoint):

```bash
cp .env.example .env               # BOT_URL, BOT_API_KEY, BOT_MODEL
python -m chatbot_eval validate --training path/to/your_faq.csv
python -m chatbot_eval run --bot http --label "UAT round 1"
python -m chatbot_eval report runs/<run>.jsonl --xlsx round1.xlsx --md round1.md --strict
```

## Project layout

```
chatbot_eval/   the evaluator: dataset, builder, checks, runner, metrics, gates, compare, review, judge, reports
supportbot/     the bot: arabic, lexicon, knowledge (BM25), guard, llm (provider group), store (live database), bot, server, web widget, demo_kb/
data/           golden set, held-out set, training FAQ, gates
docs/           method, dataset format, support bot guide
reports/        demo and support-bot reports
tests/          140 tests: statistics by hand, every check, the bot, red team, live database, server, end to end
```

The bot and the evaluator share no code on purpose: a text-handling bug in both would hide itself.

## Read more

[How to Evaluate an Arabic Chatbot Before Launch](https://nadashaaban.com/arabic-chatbot-evaluation.html)

---

Made by [Nada Shaban](https://nadashaaban.com) · MIT License
