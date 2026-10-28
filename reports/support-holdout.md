# Chatbot evaluation: Support bot, held-out set

**Decision: NO-GO** · bot `support-bot` · golden set `c9e09e0f6c51` · 88 cases

Pass rate **68.2%** (95% interval 57.9% to 77.0%) · language match 100.0% · critical failures **0**

## Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Overall pass rate | 68.2% | >= 90.0% | **FAIL** |
| Answer language matches the question | 100.0% | >= 98.0% | pass |
| Critical failures (leaks, failed safety cases) | 0 | <= 0 | pass |
| p95 response time | 21 ms | <= 8000 ms | pass |
| Dialect: egyptian | 68.2% | >= 80.0% | **FAIL** |
| Dialect: english | 77.3% | >= 80.0% | **FAIL** |

Not judged, too few cases: dialect = maghrebi (2 cases); dialect = gulf (13 cases); dialect = levantine (9 cases); dialect = msa (19 cases); dialect = franco (1 cases); intent = human_agent (4 cases); intent = out_of_scope (4 cases); intent = thanks (4 cases); intent = payment (4 cases); intent = complaint (4 cases); intent = cancellation (4 cases); intent = payment_methods (4 cases); intent = invoice (4 cases); intent = pricing (4 cases); intent = password (4 cases); intent = video (4 cases); intent = mobile_app (4 cases); intent = refund (4 cases); intent = certificate (4 cases); intent = course_access (4 cases); intent = vague (4 cases); intent = security (4 cases); intent = upgrade_plan (4 cases); intent = account_email (4 cases); intent = live_sessions (4 cases); intent = community (4 cases); intent = data_deletion (4 cases)

## Why answers failed

| Reason | Cases |
|---|---|
| behavior | 25 |
| content | 13 |

## By dialect

| dialect | Cases | Pass rate | 95% interval |
|---|---|---|---|
| maghrebi | 2 | 0.0% | 0.0% to 65.8% |
| gulf | 13 | 61.5% | 35.5% to 82.3% |
| levantine | 9 | 66.7% | 35.4% to 87.9% |
| egyptian | 22 | 68.2% | 47.3% to 83.6% |
| msa | 19 | 68.4% | 46.0% to 84.6% |
| english | 22 | 77.3% | 56.6% to 89.9% |
| franco | 1 | 100.0% | 20.7% to 100.0% |

## By intent

| intent | Cases | Pass rate | 95% interval |
|---|---|---|---|
| human_agent | 4 | 0.0% | 0.0% to 49.0% |
| out_of_scope | 4 | 0.0% | 0.0% to 49.0% |
| thanks | 4 | 0.0% | 0.0% to 49.0% |
| payment | 4 | 25.0% | 4.6% to 69.9% |
| complaint | 4 | 25.0% | 4.6% to 69.9% |
| cancellation | 4 | 50.0% | 15.0% to 85.0% |
| payment_methods | 4 | 50.0% | 15.0% to 85.0% |
| invoice | 4 | 50.0% | 15.0% to 85.0% |
| pricing | 4 | 75.0% | 30.1% to 95.4% |
| password | 4 | 75.0% | 30.1% to 95.4% |
| video | 4 | 75.0% | 30.1% to 95.4% |
| mobile_app | 4 | 75.0% | 30.1% to 95.4% |
| refund | 4 | 100.0% | 51.0% to 100.0% |
| certificate | 4 | 100.0% | 51.0% to 100.0% |
| course_access | 4 | 100.0% | 51.0% to 100.0% |
| vague | 4 | 100.0% | 51.0% to 100.0% |
| security | 4 | 100.0% | 51.0% to 100.0% |
| upgrade_plan | 4 | 100.0% | 51.0% to 100.0% |
| account_email | 4 | 100.0% | 51.0% to 100.0% |
| live_sessions | 4 | 100.0% | 51.0% to 100.0% |
| community | 4 | 100.0% | 51.0% to 100.0% |
| data_deletion | 4 | 100.0% | 51.0% to 100.0% |

## Examples of failures

| Case | Question | Answer | Why |
|---|---|---|---|
| HO-003 (msa) | كيف أنهي اشتراكي الشهري؟ | الاشتراك الشهري 10 دولار، والسنوي 100 دولار (أي شهران مجانًا). | content |
| HO-004 (english) | Please end my plan | Could you tell me more? I can help with your subscription, payments, courses and account. | behavior, content |
| HO-007 (maghrebi) | قداش الاشتراك؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| HO-018 (gulf) | ما أذكر الباسوورد | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| HO-021 (egyptian) | مش عارفة أدفع بالكارت | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
