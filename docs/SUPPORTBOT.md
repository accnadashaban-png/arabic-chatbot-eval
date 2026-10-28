# Support bot: run it for your business

A standalone assistant that answers your audience from your own content, in their dialect, reads a live database, and knows when to pass a conversation to your team.

## 1. Start it

```bash
pip install -e .                                   # add [postgres] for PostgreSQL
python -m supportbot serve                         # http://127.0.0.1:8070, demo page with the widget
```

On first start it creates `supportbot.db` (SQLite) and loads the demo knowledge base. Use your own:

```bash
python -m supportbot serve --kb path/to/your_kb                                   # loads your folder into a new database
SB_DATABASE_URL=postgresql://bot:pass@db:5432/support python -m supportbot serve   # PostgreSQL
```

## 2. Your knowledge base

Start from a folder (see [`supportbot/demo_kb`](../supportbot/demo_kb)); after the first start it lives in the database and is managed through the admin API.

**`faq.csv`**

| Column | Example | Notes |
|---|---|---|
| `id` | `KB-02` | Shown as the source of each answer. |
| `topic` | `pricing` | Used by the policies below. |
| `concepts` | `PRICE MONTHLY YEARLY` | From the lexicon: what this entry is about. Name the topic concept first; descriptors (`COURSE`, `ACCOUNT`, `SCHEDULE`...) only narrow it. |
| `questions` | `ما أسعار الباقات؟\|What are your prices?` | A few natural phrasings, separated by `\|`. |
| `answer_ar`, `answer_en` | | The exact text users see. Keep facts (prices, days, links) here: the LLM may only repeat them. |

**`policies.json`**

```json
{
  "business": "a short description used in the LLM prompt",
  "handoff_topics": ["refund", "data_deletion", "complaint", "human_agent"],
  "refuse_topics": ["out_of_scope"],
  "min_score": 2.0,
  "min_score_words_only": 8.0,
  "min_margin": 0.15,
  "messages": {"clarify": {"ar": "...", "en": "..."}, "refuse_attack": {"ar": "...", "en": "..."}}
}
```

- **Hand-off topics** answer with the entry text (which should say a person will follow up) and are never rewritten by an LLM.
- **Thresholds** belong to each knowledge base: a small FAQ scores lower than a large one. Tune them on your own evaluation set, never on the held-out set.

**`lexicon.csv` (optional)**: your product words, same format as [`supportbot/lexicon.csv`](../supportbot/lexicon.csv), merged with the shared lexicon of dialect, English and Franco words.

## 3. Live database

| Table | Holds |
|---|---|
| `kb_entries` | The knowledge base. Entries are switched off (`active = 0`), never deleted, so past conversations stay readable. |
| `kb_settings` | The policies. |
| `conversations` | Time, language, topic, behavior, confidence and mode of every message, with the question's emails, card numbers and phone numbers masked. No IP addresses. |

Before answering, the bot checks (at most every two seconds) whether entries or settings changed and rebuilds its index if so. Any writer works: the admin API, a script, or another system writing to the same tables.

## 4. Admin API

Set `SB_ADMIN_KEY`; every call sends it as `X-Admin-Key`. Without a key the admin API is off.

| Call | Does |
|---|---|
| `GET /admin/entries` | List active entries. |
| `PUT /admin/entries/<id>` | Add or change an entry (JSON with `topic`, `concepts`, `questions`, `answer_ar`, `answer_en`); live at once. |
| `DELETE /admin/entries/<id>` | Switch an entry off. |
| `GET /admin/insights?days=7` | Conversations, answered rate, hand-offs, by topic, behavior and mode, and **content gaps**: the questions the bot most often could not answer. |
| `GET /admin/llm` | Each LLM provider: available or resting, for how long, last error, answers served. |

```bash
curl -X PUT http://127.0.0.1:8070/admin/entries/KB-30 -H "X-Admin-Key: $SB_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"topic":"delivery","concepts":"SCHEDULE","questions":["When will my order arrive?"],"answer_ar":"يصل الطلب خلال 3 أيام عمل.","answer_en":"Orders arrive within 3 working days."}'
```

## 5. How a message is handled

1. **Guard:** prompt injection (Arabic, English, Franco; spaced out, digit swaps, hidden characters, one typo), administrator credentials, other people's data and SQL are refused with a fixed message.
2. **Lookup:** the lexicon turns dialect words into concepts; BM25 ranks entries; entries that share a topic concept with the message lead, words only break ties. A message with no known concept is answered only on a strong word match.
3. **Follow-ups:** a short message that names no topic ("والسنوي؟", "and if I miss it?") is read together with the previous user message.
4. **Policy:** hand off, refuse, answer, or, when the best match is weak or two topics tie, ask the LLM to choose (below) or ask the user to clarify.
5. **Answer:** the entry text in the user's language (Arabic for Arabic script, Franco and code-switching), or an LLM wording that passed the checks.

Every reply carries its behavior, topic, sources, confidence, mode and notes, returned by the API as `supportbot`.

## 6. The LLM provider group

```bash
SB_LLM_PROVIDERS="groq|https://api.groq.com/openai/v1/chat/completions|llama-3.3-70b-versatile;gemini|https://generativelanguage.googleapis.com/v1beta/openai/chat/completions|gemini-2.5-flash;openrouter|https://openrouter.ai/api/v1/chat/completions|meta-llama/llama-3.3-70b-instruct:free"
SB_LLM_KEY_GROQ=...
SB_LLM_KEY_GEMINI=...
SB_LLM_KEY_OPENROUTER=...
```

Providers are used in order. When one fails, the next answers in the same request, and the failed one rests:

| Failure | Rest |
|---|---|
| Out of credit or quota (402, or 429 mentioning quota) | 6 hours |
| Rate limited (429) | 1 minute, or the provider's `Retry-After` |
| Invalid key (401, 403) | 24 hours |
| Down, timeout, broken reply | 20 to 30 seconds, doubling on repeated failures (up to 8×) |
| Our request rejected (400) | none: the next provider is tried, this one stays available |

When every provider is resting, the one that recovers first is tried; if it fails too, the knowledge base answers. `GET /admin/llm` shows the state of each.

**What the model may do.** Reword an answer from the matching entry, or, when retrieval is unsure, pick among the three closest entries (or say the user should clarify). **What it may not do.** Its reply is rejected, and the knowledge-base text is sent, if it:

- cites an entry that was not offered, or none,
- contains a number or link that is not in the entry,
- is in the wrong language, contains markup or script,
- contains the per-process canary or any distinctive phrase of the system prompt.

Hand-offs and refusals always use the fixed entry text. The reason for every rejection is recorded in `notes`.

## 7. Put it on your site

```html
<script src="https://your-bot-host/widget.js" data-api="https://your-bot-host" data-name="Lernova Assistant" defer></script>
```

Optional: `data-lang="ar|en"` (default: the page's `lang`, followed live), `data-position="left"`.

| Setting | Purpose |
|---|---|
| `SB_ALLOWED_ORIGINS=https://www.example.com,https://app.example.com` | Only these sites may call the bot from a browser (CORS). |
| `SB_RATE_PER_MINUTE=30` | Messages per visitor per minute (`0` turns it off). |
| `SB_API_KEY` | A bearer key for server-to-server calls. Never put it in browser code: a key there is public. |

Requests over 64 KB are refused; at most 40 messages of history are read, each cut to 2,000 characters; client `system` messages are ignored; security headers on every response; the widget escapes all text and renders in a Shadow DOM.

## 8. Evaluate before you launch

```bash
python -m chatbot_eval validate --training path/to/your_kb/faq.csv   # your FAQ must not contain test questions
python -m chatbot_eval run --bot http --label "UAT round 1"          # BOT_URL=http://127.0.0.1:8070/v1/chat/completions
python -m chatbot_eval report runs/<run>.jsonl --md report.md --strict
```

Write your own golden set from real conversations, keep a held-out set you never tune on, run `pytest tests/test_redteam.py` after every change, and read `/admin/insights` every week: content gaps are your next entries.
