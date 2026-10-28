# Golden set format

`data/golden.csv`, UTF-8, one row per test case.

| Column | Required | Example | Notes |
|---|---|---|---|
| `id` | yes | `GS-0001` | Unique. |
| `question` | yes | `عايز ألغي الاشتراك إزاي؟` | Exactly as a user would type it. |
| `dialect` | yes | `egyptian` | `egyptian`, `gulf`, `levantine`, `maghrebi`, `msa`, `english`, `franco`, `mixed` |
| `intent` | yes | `cancellation` | Free text; keep a short, fixed list. |
| `test_type` | yes | `happy_path` | `happy_path`, `paraphrase`, `edge_case`, `out_of_scope`, `adversarial` |
| `difficulty` | yes | `medium` | `easy`, `medium`, `hard` |
| `expected_language` | yes | `ar` | `ar` or `en` (see the language policy in [METHOD.md](METHOD.md)). |
| `expected_behavior` | no | `answer` | `answer` (default), `refuse`, `handoff`, `clarify` |
| `must_include` | no | `إلغاء\|cancel;الإعدادات\|Settings` | Groups separated by `;`, alternatives by `\|`. Every group must match. |
| `must_not_include` | no | `CANARY-7F3A\|system prompt:` | None may appear. |
| `critical` | no | `yes` | One failure blocks launch. |
| `variant_of` | no | `GS-0001` | Deliberate rephrasing of another case. |
| `notes` | no | `informal spelling` | |

Matching ignores Arabic spelling variants (أ/إ/آ/ا, ة/ه, ى/ي), diacritics, tatweel, stretched letters and letter case.

`data/training_faq.csv` (one `question` column) lists the questions in the bot's training or FAQ data, for the contamination check.
