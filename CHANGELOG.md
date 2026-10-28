# Changelog

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
