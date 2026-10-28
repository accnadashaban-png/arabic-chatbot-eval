# Support bot: use it for your business

The bot answers your audience from your own content, in their dialect, and knows when to pass a conversation to your team.

## 1. Your knowledge base

A folder with two files (see [`supportbot/demo_kb`](../supportbot/demo_kb)):

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

**`lexicon.csv` (optional)**: your product words, same format as [`supportbot/lexicon.csv`](../supportbot/lexicon.csv). It is merged with the shared lexicon of dialect, English and Franco words.

```bash
SB_KB_DIR=path/to/your_kb python -m supportbot serve
python -m supportbot ask "سؤال" --kb path/to/your_kb
```

## 2. How a message is handled

1. **Guard:** prompt injection (Arabic, English, Franco; spaced out, digit swaps, hidden characters, one typo), administrator credentials, other people's data and SQL are refused with a fixed message.
2. **Lookup:** the lexicon turns dialect words into concepts; BM25 ranks entries; entries that share a topic concept with the message lead, words only break ties. A message with no known concept is answered only on a strong word match.
3. **Follow-ups:** a short message that names no topic ("والسنوي؟", "and if I miss it?") is read together with the previous user message.
4. **Policy:** hand off, refuse, answer, or ask a clarifying question when the best match is weak or two topics tie.
5. **Answer:** the entry text in the user's language: Arabic for Arabic script, Franco and code-switching, English otherwise.

Every reply carries its behavior, topic, sources, confidence and mode, returned by the API as `supportbot`.

## 3. Optional LLM

```bash
SB_LLM_PROVIDERS="groq|https://api.groq.com/openai/v1/chat/completions|llama-3.3-70b-versatile;gemini|https://generativelanguage.googleapis.com/v1beta/openai/chat/completions|gemini-2.5-flash"
SB_LLM_KEY_GROQ=...
SB_LLM_KEY_GEMINI=...
```

Providers are tried in order; the next one answers when one is rate limited or down. The model only rewrites answers (never hand-offs or refusals), sees only the matching entries, and its reply is **rejected** if it:

- contains a number or link that is not in those entries,
- is in the wrong language,
- contains markup or script,
- contains the per-process canary or any distinctive phrase of the system prompt.

A rejected reply is replaced by the knowledge-base text, and the reason is recorded in `notes`.

## 4. Server

`POST /v1/chat/completions` (OpenAI format; the last message must be from the user; client `system` messages are ignored), `GET /` chat page, `GET /health`.

- Optional bearer key: `SB_API_KEY` (constant-time comparison).
- Requests over 64 KB are refused; at most 40 messages of history are read, each cut to 2,000 characters.
- Logs never contain raw messages: emails, card numbers (Luhn-checked) and phone numbers are masked.
- Security headers on every response; the chat page escapes all text and cannot be framed.

## 5. Evaluate before you launch

```bash
python -m chatbot_eval validate --training path/to/your_kb/faq.csv   # your FAQ must not contain test questions
python -m chatbot_eval run --bot http --label "UAT round 1"          # BOT_URL=http://127.0.0.1:8070/v1/chat/completions
python -m chatbot_eval report runs/<run>.jsonl --md report.md --strict
```

Write your own golden set from real conversations, keep a held-out set you never tune on, and run `pytest tests/test_redteam.py` after every change.
