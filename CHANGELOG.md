# Changelog

## 2.1.0

- **Live database** (`supportbot/store.py`): knowledge base, settings and a masked conversation log in SQLite or
  PostgreSQL; the bot picks up changes within seconds without a restart. Identical answers on both databases, tested.
- **Admin API**: manage entries, conversation insights with content gaps, and LLM provider status, behind `SB_ADMIN_KEY`.
- **LLM provider group**: per-failure cooldowns (quota, rate limit with `Retry-After`, invalid key, outage with growing
  pauses), the next provider answers at once, the soonest to recover is tried when all rest, status without keys.
- **LLM choice when retrieval is unsure**: the model picks among the three closest entries or asks to clarify; its
  choice and wording pass the same grounding checks, and hand-offs are never rewritten.
- **Embeddable widget** (`/widget.js`): launcher in the corner, dark theme, right-to-left aware, Shadow DOM, full screen
  on phones; demo product page. CORS allow-list (`SB_ALLOWED_ORIGINS`) and per-visitor rate limit for public use.
- Fixed: card numbers followed by text were masked together with the following space.
- Greetings ("hi", "السلام عليكم") get a greeting back instead of a clarifying question.
- 140 tests; CI runs the PostgreSQL tests against a PostgreSQL 16 service.

## 2.0.0

**Evaluation toolkit (`chatbot_eval`)**
- Golden set of 1,769 cases: 22 support intents, 8 dialects (Egyptian, Gulf, Levantine, Maghrebi, MSA, English, Franco,
  code-switching), expected behavior (answer, refuse, hand off, clarify), critical safety cases with a canary, greeting,
  courtesy, context, informal-spelling and typo variants, and 24 multi-turn conversations. A separate 88-case held-out set.
- Dataset QA: line-numbered schema errors, near-duplicates after Arabic normalization, coverage gaps, contamination
  against a bot's FAQ or training data.
- Checks: language policy, required and forbidden content, behavior, errors and latency; criticality for leaks and
  unrefused attacks. Multi-turn cases replay the conversation with the bot's own replies.
- Statistics: Wilson intervals, worst-first slices, exact McNemar test between UAT rounds. Launch gates with a GO / NO-GO
  decision; Excel and Markdown reports; `--strict` for CI. Human review sheet with Cohen's kappa; optional LLM judge.

**Support bot (`supportbot`)**
- Bring-your-own knowledge base (`faq.csv`, `policies.json`, optional `lexicon.csv`); dialect lexicon with light
  stemming and typo tolerance; BM25 with topic concepts leading; follow-up handling; hand-off, refusal and clarification
  policies; Arabic replies for Arabic script, Franco and code-switching.
- Optional LLM through any OpenAI-compatible providers with failover; replies are used only if they pass grounding checks
  (numbers and links from the sources, language, no markup, no canary or prompt phrases).
- OpenAI-compatible HTTP server and chat page (standard library), bearer key, size limits, personal data masked in logs.
- Results: development set 98.8% (GO), held-out set 63.6% with 4 critical failures at the first run, 68.2% and none after
  the red-team fix (NO-GO).

**Red team**
- 47 attack tests: instruction override and extraction in three languages and disguised forms, credentials, other users'
  data, SQL, split and forged conversations, a compromised LLM, and server attacks. The first run found 18 gaps; all fixed.

121 tests, 92% coverage; no pandas dependency; CI on Python 3.11 and 3.12.

## 1.0.0

- First version: a single script, 16 test cases, language and keyword checks, Excel report.
