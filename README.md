# arabic-chatbot-eval

[![CI](https://github.com/accnadashaban-png/arabic-chatbot-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/accnadashaban-png/arabic-chatbot-eval/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Golden set](https://img.shields.io/badge/golden%20set-3%2C613%20cases%20%C2%B7%208%20dialects-success) ![Red team](https://img.shields.io/badge/red%20team-47%20attacks-success) ![License](https://img.shields.io/badge/license-MIT-green)

Two things in one repository:

1. **An evaluation toolkit** for Arabic + English chatbots: a tagged golden set across eight dialects, dialect-aware checks, honest statistics, UAT round comparison and a **GO / NO-GO** decision.
2. **A customer-support bot** for any business: bring your own FAQ, it answers your audience in their dialect, remembers each person's conversations, hands refunds and complaints to your team, refuses attacks, and can use any LLM with grounding checks. It comes with an admin console and is evaluated with the toolkit, including a held-out set and a red-team suite.

> Built from the process I use for pre-launch chatbot evaluation at work. Everything here is **synthetic**: **Lernova**, a fictional online-learning platform. No company data.

## Results

| | Development set | Held-out set |
|---|---|---|
| Cases | 3,613 (45 intents) | 180 (new wording, never used for tuning) |
| Pass rate (95% interval) | **98.9%** (98.5–99.2%) | **52.2%** (45.0–59.4%) |
| Critical failures | 0 | 0 |
| Decision | **GO** | **NO-GO** |

The gap is the point. A bot tuned on its development set looks ready; new wording shows it is not.

- **Version 2.0** (22 intents): 98.8% on development, 63.6% held-out with 4 critical failures (requests for **other users' data** that were not refused). The red-team work closed that gap: 68.2% and none.
- **Version 2.2** (the business grew to 45 intents): the 88 original held-out questions score 67.0%, and the 92 new ones, written before tuning and run once on the frozen bot, score **38.0%**. A keyword-and-lexicon bot does not generalize to wording nobody listed; this is the measured case for the grounded LLM mode, not a reason to tune on the held-out set.
- Of the 86 held-out failures, **52 are safe**: the bot asks the user to clarify instead of answering wrong. 31 picked the wrong entry.

Full reports: [development](reports/support-dev.md) · [held-out](reports/support-holdout.md) · demo UAT [round 1](reports/demo-round1.md) and [round 2](reports/demo-round2.md) (a demo bot built for the first release, judged on that scope: 1,769 cases).

## The demo business: Lernova

A fictional online-learning membership (courses, live classes, certificates, mentors, team plans), big enough to behave like a real support desk. 43 knowledge-base entries in Arabic and English, 45 intents in the golden set:

| Area | What people ask |
|---|---|
| Plans and billing | prices, free trial, change plan, pause, cancel, refunds (handed to the team), double charges (handed to billing), payment failed, payment methods, invoices, tax, discounts, student aid, gift memberships, invite-a-friend reward, team plans for companies |
| Learning | course access, how long access lasts, where to start (learning paths), course language and subtitles, progress not saving, final quiz and retakes, projects and feedback, certificates and verification on LinkedIn, mentoring, live sessions, offline downloads, requesting a course, teaching on the platform |
| Account | password, email and phone, devices, two-step verification and hacked accounts, data deletion (handed to the team) |
| Conversation | greetings, thanks, complaints and "talk to a person" (handed to the team), support hours, vague messages (a question back), off-topic requests (declined), attacks (refused) |

Replace [`supportbot/demo_kb`](supportbot/demo_kb) with your own business and the same pipeline, guardrails and evaluation apply.

## The evaluation toolkit

| Step | What you get |
|---|---|
| **Golden set** | 3,613 cases: 45 support intents × Egyptian, Gulf, Levantine, Maghrebi, MSA, English, Franco and code-switching; greeting, courtesy, extra-context, informal-spelling and typo variants; 36 multi-turn conversations. Each case states the expected behavior: answer, refuse, hand off or clarify. |
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

- **People and conversations, like a modern AI assistant:** every visitor gets an anonymous id in their browser (or send your own user id), each conversation is saved with its messages, a returning visitor sees their chat again, and the "new conversation" button starts a fresh one. Nobody can read or append to another person's chat. Erase a person and everything they said with one call.
- **Live database:** knowledge base, settings, people, chats and messages in SQLite (no setup) or PostgreSQL. Add or change an answer through the admin API, a script or another system and the bot uses it within seconds, without a restart. Tested on both databases with identical answers.
- **Admin console** (`/admin`) and API: read every conversation, find a person, edit or switch off answers live, see **insights** (messages per day, answered rate, hand-offs, top topics, and the questions the bot could not answer: your next content to write) and the state of each LLM provider. Behind its own key.
- **Arabic that people really write:** a lexicon maps dialect, English and Franco words to shared concepts (`بكام`, `قديش`, `شحال`, `how much` → price), with light stemming and tolerance for one typo.
- **Knows when not to answer:** refunds, complaints, data deletion and "talk to a person" go to your team; off-topic requests are declined; unclear messages get a question back.
- **Conversation memory:** "and the yearly one?" is read with the previous question.
- **A group of LLM providers that never leaves users waiting:** list several (free tiers welcome). A provider out of credit rests for hours, a rate-limited one for a minute, one that is down for seconds with growing pauses; the next one answers at once and the first comes back when ready. If all are down, the knowledge base still answers.
- **Smarter, never trusted blindly:** when retrieval is unsure, the model picks among the closest entries or asks the user to clarify; it may reword answers but every number and link must come from the sources, in the right language, with no markup and nothing from its instructions. Hand-offs and refusals are never rewritten.
- **Guardrails:** prompt injection in Arabic, English and Franco (also spaced out, with digit swaps or hidden characters), credential requests, requests for other users' data, SQL; personal data is masked in logs and in the database.
- **Embeddable widget:** one script tag, a launcher in the corner, dark and RTL-aware, isolated in a Shadow DOM, full screen on phones. Only the websites you list may call the bot from a browser, and each visitor is rate limited.

| Overview | Conversations |
|---|---|
| ![Admin console overview: messages per day, top topics and content gaps](docs/admin-overview.jpg) | ![Admin console: a saved conversation with each answer's topic and confidence](docs/admin-chats.jpg) |

### The database

```mermaid
erDiagram
    users ||--o{ chats : starts
    chats ||--o{ turns : contains
    users {
        text id PK "anonymous visitor id or your own user id"
        text name "optional"
        text email "optional"
        text language
        text first_seen
        text last_seen
        int chats
        int messages
    }
    chats {
        text id PK
        text user_id FK
        text started_at
        text updated_at
        text title "first question"
        text status "open or handed_off"
        int turns
        text last_topic
    }
    turns {
        int id PK
        text chat_id FK
        text user_id
        text at
        text question "emails, cards and phones masked"
        text answer
        text language
        text topic
        text behavior "answer, clarify, handoff or refuse"
        real confidence
        text mode "kb, llm or guard"
    }
    kb_entries {
        text id PK
        text topic
        text concepts "! marks a required concept"
        text questions
        text answer_ar
        text answer_en
        int active
        text updated_at
    }
    kb_settings {
        text key PK
        text value "policies as JSON"
    }
```

Sample rows (synthetic):

| `chats.id` | `user_id` | `title` | `status` | `turns` | `last_topic` |
|---|---|---|---|---|---|
| `9f2c…e1` | `v-41ad…` | الاشتراك بكام؟ | open | 2 | pricing |
| `b7a0…3c` | `v-41ad…` | I was charged twice this month | handed_off | 1 | double_charge |

| `turns.chat_id` | `question` | `answer` (shortened) | `topic` | `behavior` | `confidence` (retrieval score) | `mode` |
|---|---|---|---|---|---|---|
| `9f2c…e1` | الاشتراك بكام؟ | الاشتراك الشهري 10 دولار، والسنوي 100 دولار… | pricing | answer | 6.46 | kb |
| `9f2c…e1` | والسنوي؟ | الاشتراك الشهري 10 دولار، والسنوي 100 دولار… | pricing | answer | 15.54 | kb |
| `b7a0…3c` | I was charged twice this month | I'm sorry about that. A double charge needs a check… | double_charge | handoff | 12.04 | kb |

| `kb_entries.id` | `topic` | `concepts` | `questions` | `answer_en` (shortened) |
|---|---|---|---|---|
| `KB-02` | pricing | `PRICE MONTHLY YEARLY` | ما أسعار الباقات؟\|What are your prices? | The monthly plan is $10 and the yearly plan is $100… |
| `KB-25` | team_plan | `!TEAM PRICE PLAN HUMAN` | هل يوجد اشتراك جماعي؟\|Lernova for Teams | Lernova for Teams is $8 per person per month… |

### Run it

```bash
python -m supportbot serve                 # http://127.0.0.1:8070, creates supportbot.db from the demo knowledge base
SB_ADMIN_KEY=<a long random key> python -m supportbot serve   # also opens the admin console at /admin
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
pytest                             # 145 tests
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
supportbot/     the bot: arabic, lexicon, knowledge (BM25), guard, llm (provider group), store (live database: people, chats, knowledge), bot, server, web (widget, admin console), demo_kb/
data/           golden set, held-out set, training FAQ, gates
docs/           method, dataset format, support bot guide
reports/        demo and support-bot reports
tests/          145 tests: statistics by hand, every check, the bot, red team, live database, server, end to end
```

The bot and the evaluator share no code on purpose: a text-handling bug in both would hide itself.

## Read more

[How to Evaluate an Arabic Chatbot Before Launch](https://nadashaaban.com/arabic-chatbot-evaluation.html)

---

Made by [Nada Shaban](https://nadashaaban.com) · MIT License
