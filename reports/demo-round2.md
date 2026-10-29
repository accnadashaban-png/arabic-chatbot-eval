# Chatbot evaluation: UAT round 2

**Decision: NO-GO** · bot `demo-bot-v2` · golden set `d1cb795c78d4` · 1769 cases

Pass rate **45.4%** (95% interval 43.1% to 47.7%) · language match 97.4% · critical failures **0**

## Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Overall pass rate | 45.4% | >= 90.0% | **FAIL** |
| Answer language matches the question | 97.4% | >= 98.0% | **FAIL** |
| Critical failures (leaks, failed safety cases) | 0 | <= 0 | pass |
| p95 response time | 0 ms | <= 8000 ms | pass |
| Dialect: maghrebi | 35.7% | >= 80.0% | **FAIL** |
| Dialect: mixed | 41.5% | >= 80.0% | **FAIL** |
| Dialect: egyptian | 46.3% | >= 80.0% | **FAIL** |
| Dialect: gulf | 46.3% | >= 80.0% | **FAIL** |
| Dialect: levantine | 46.5% | >= 80.0% | **FAIL** |
| Dialect: msa | 47.4% | >= 80.0% | **FAIL** |
| Dialect: franco | 50.0% | >= 80.0% | **FAIL** |
| Dialect: english | 53.8% | >= 80.0% | **FAIL** |
| Intent: live_sessions | 0.0% | >= 80.0% | **FAIL** |
| Intent: mobile_app | 0.0% | >= 80.0% | **FAIL** |
| Intent: upgrade_plan | 0.0% | >= 80.0% | **FAIL** |
| Intent: invoice | 0.0% | >= 80.0% | **FAIL** |
| Intent: account_email | 0.0% | >= 80.0% | **FAIL** |
| Intent: data_deletion | 0.0% | >= 80.0% | **FAIL** |
| Intent: complaint | 0.0% | >= 80.0% | **FAIL** |
| Intent: community | 0.0% | >= 80.0% | **FAIL** |
| Intent: payment_methods | 0.0% | >= 80.0% | **FAIL** |
| Intent: thanks | 0.0% | >= 80.0% | **FAIL** |
| Intent: pricing | 9.5% | >= 80.0% | **FAIL** |
| Intent: payment | 81.2% | >= 80.0% | pass |
| Intent: human_agent | 83.1% | >= 80.0% | pass |
| Intent: password | 85.0% | >= 80.0% | pass |
| Intent: video | 87.5% | >= 80.0% | pass |
| Intent: certificate | 88.1% | >= 80.0% | pass |
| Intent: vague | 89.2% | >= 80.0% | pass |
| Intent: course_access | 90.0% | >= 80.0% | pass |
| Intent: security | 91.7% | >= 80.0% | pass |
| Intent: cancellation | 93.8% | >= 80.0% | pass |
| Intent: refund | 100.0% | >= 80.0% | pass |
| Intent: out_of_scope | 100.0% | >= 80.0% | pass |

## Why answers failed

| Reason | Cases |
|---|---|
| language | 46 |
| behavior | 837 |
| content | 693 |

## By dialect

| dialect | Cases | Pass rate | 95% interval |
|---|---|---|---|
| maghrebi | 241 | 35.7% | 29.9% to 41.9% |
| mixed | 234 | 41.5% | 35.3% to 47.9% |
| egyptian | 246 | 46.3% | 40.2% to 52.6% |
| gulf | 246 | 46.3% | 40.2% to 52.6% |
| levantine | 241 | 46.5% | 40.3% to 52.8% |
| msa | 247 | 47.4% | 41.2% to 53.6% |
| franco | 154 | 50.0% | 42.2% to 57.8% |
| english | 160 | 53.8% | 46.0% to 61.3% |

## By intent

| intent | Cases | Pass rate | 95% interval |
|---|---|---|---|
| live_sessions | 84 | 0.0% | 0.0% to 4.4% |
| mobile_app | 83 | 0.0% | 0.0% to 4.4% |
| upgrade_plan | 80 | 0.0% | 0.0% to 4.6% |
| invoice | 80 | 0.0% | 0.0% to 4.6% |
| account_email | 80 | 0.0% | 0.0% to 4.6% |
| data_deletion | 80 | 0.0% | 0.0% to 4.6% |
| complaint | 80 | 0.0% | 0.0% to 4.6% |
| community | 79 | 0.0% | 0.0% to 4.6% |
| payment_methods | 78 | 0.0% | 0.0% to 4.7% |
| thanks | 78 | 0.0% | 0.0% to 4.7% |
| pricing | 84 | 9.5% | 4.9% to 17.7% |
| payment | 80 | 81.2% | 71.3% to 88.3% |
| human_agent | 77 | 83.1% | 73.2% to 89.9% |
| password | 80 | 85.0% | 75.6% to 91.2% |
| video | 80 | 87.5% | 78.5% to 93.1% |
| certificate | 84 | 88.1% | 79.5% to 93.4% |
| vague | 74 | 89.2% | 80.1% to 94.4% |
| course_access | 80 | 90.0% | 81.5% to 94.8% |
| security | 84 | 91.7% | 83.8% to 95.9% |
| cancellation | 80 | 93.8% | 86.2% to 97.3% |
| refund | 84 | 100.0% | 95.6% to 100.0% |
| out_of_scope | 80 | 100.0% | 95.4% to 100.0% |

## Compared with UAT round 1

Fixed **224**, regressed **51**, still failing 915. McNemar exact p = 4.9e-27 (a real change).

| Slice | Before | After | Change |
|---|---|---|---|
| intent = pricing | 70.2% | 9.5% | -60.7% |
| dialect = mixed | 35.5% | 41.5% | +6.0% |
| dialect = maghrebi | 27.4% | 35.7% | +8.3% |
| intent = certificate | 79.8% | 88.1% | +8.3% |
| intent = cancellation | 85.0% | 93.8% | +8.8% |
| intent = password | 76.2% | 85.0% | +8.8% |
| intent = payment | 72.5% | 81.2% | +8.8% |
| intent = course_access | 81.2% | 90.0% | +8.8% |
| intent = video | 78.8% | 87.5% | +8.8% |
| intent = out_of_scope | 91.2% | 100.0% | +8.8% |
| intent = human_agent | 74.0% | 83.1% | +9.1% |
| dialect = english | 41.2% | 53.8% | +12.5% |
| intent = security | 70.2% | 91.7% | +21.4% |
| dialect = franco | 0.0% | 50.0% | +50.0% |
| intent = vague | 0.0% | 89.2% | +89.2% |
| intent = refund | 0.0% | 100.0% | +100.0% |

## Examples of failures

| Case | Question | Answer | Why |
|---|---|---|---|
| GS-0040 (maghrebi) | كيفاش نحبس الاشتراك؟ | عذرًا، لم أفهم سؤالك. | behavior, content |
| GS-0041 (maghrebi) | السلام عليكم، كيفاش نحبس الاشتراك؟ | عذرًا، لم أفهم سؤالك. | behavior, content |
| GS-0042 (maghrebi) | كيفاش نحبس الاشتراك عافاك؟ | عذرًا، لم أفهم سؤالك. | behavior, content |
| GS-0043 (maghrebi) | كيفاششش نحبس الاشتراك | عذرًا، لم أفهم سؤالك. | behavior, content |
| GS-0044 (maghrebi) | كيفاش نحبس الاتشراك؟ | عذرًا، لم أفهم سؤالك. | behavior, content |
