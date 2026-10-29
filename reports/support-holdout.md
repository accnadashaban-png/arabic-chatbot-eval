# Chatbot evaluation: Support bot, held-out set

**Decision: NO-GO** · bot `support-bot` · golden set `1975b09683b8` · 180 cases

Pass rate **52.2%** (95% interval 45.0% to 59.4%) · language match 100.0% · critical failures **0**

## Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Overall pass rate | 52.2% | >= 90.0% | **FAIL** |
| Answer language matches the question | 100.0% | >= 98.0% | pass |
| Critical failures (leaks, failed safety cases) | 0 | <= 0 | pass |
| p95 response time | 55 ms | <= 8000 ms | pass |
| Dialect: egyptian | 42.2% | >= 80.0% | **FAIL** |
| Dialect: gulf | 52.0% | >= 80.0% | **FAIL** |
| Dialect: english | 57.8% | >= 80.0% | **FAIL** |
| Dialect: msa | 59.5% | >= 80.0% | **FAIL** |

Not judged, too few cases: dialect = maghrebi (3 cases); dialect = levantine (19 cases); dialect = franco (1 cases); intent = human_agent (4 cases); intent = out_of_scope (4 cases); intent = thanks (4 cases); intent = certificate_verify (4 cases); intent = course_request (4 cases); intent = account_security (4 cases); intent = scholarship (4 cases); intent = payment (4 cases); intent = complaint (4 cases); intent = team_plan (4 cases); intent = pause_subscription (4 cases); intent = progress (4 cases); intent = become_instructor (4 cases); intent = mentoring (4 cases); intent = learning_path (4 cases); intent = support_hours (4 cases); intent = course_expiry (4 cases); intent = cancellation (4 cases); intent = video (4 cases); intent = payment_methods (4 cases); intent = invoice (4 cases); intent = offline_download (4 cases); intent = gift (4 cases); intent = devices (4 cases); intent = double_charge (4 cases); intent = referral (4 cases); intent = discounts (4 cases); intent = pricing (4 cases); intent = password (4 cases); intent = mobile_app (4 cases); intent = exam_retake (4 cases); intent = assignments (4 cases); intent = tax (4 cases); intent = trial (4 cases); intent = course_language (4 cases); intent = refund (4 cases); intent = certificate (4 cases); intent = course_access (4 cases); intent = vague (4 cases); intent = security (4 cases); intent = upgrade_plan (4 cases); intent = account_email (4 cases); intent = live_sessions (4 cases); intent = community (4 cases); intent = data_deletion (4 cases)

## Why answers failed

| Reason | Cases |
|---|---|
| behavior | 55 |
| content | 69 |

## By dialect

| dialect | Cases | Pass rate | 95% interval |
|---|---|---|---|
| maghrebi | 3 | 0.0% | 0.0% to 56.2% |
| egyptian | 45 | 42.2% | 29.0% to 56.7% |
| gulf | 25 | 52.0% | 33.5% to 70.0% |
| levantine | 19 | 52.6% | 31.7% to 72.7% |
| english | 45 | 57.8% | 43.3% to 71.0% |
| msa | 42 | 59.5% | 44.5% to 73.0% |
| franco | 1 | 100.0% | 20.7% to 100.0% |

## By intent

| intent | Cases | Pass rate | 95% interval |
|---|---|---|---|
| human_agent | 4 | 0.0% | 0.0% to 49.0% |
| out_of_scope | 4 | 0.0% | 0.0% to 49.0% |
| thanks | 4 | 0.0% | 0.0% to 49.0% |
| certificate_verify | 4 | 0.0% | 0.0% to 49.0% |
| course_request | 4 | 0.0% | 0.0% to 49.0% |
| account_security | 4 | 0.0% | 0.0% to 49.0% |
| scholarship | 4 | 0.0% | 0.0% to 49.0% |
| payment | 4 | 25.0% | 4.6% to 69.9% |
| complaint | 4 | 25.0% | 4.6% to 69.9% |
| team_plan | 4 | 25.0% | 4.6% to 69.9% |
| pause_subscription | 4 | 25.0% | 4.6% to 69.9% |
| progress | 4 | 25.0% | 4.6% to 69.9% |
| become_instructor | 4 | 25.0% | 4.6% to 69.9% |
| mentoring | 4 | 25.0% | 4.6% to 69.9% |
| learning_path | 4 | 25.0% | 4.6% to 69.9% |
| support_hours | 4 | 25.0% | 4.6% to 69.9% |
| course_expiry | 4 | 25.0% | 4.6% to 69.9% |
| cancellation | 4 | 50.0% | 15.0% to 85.0% |
| video | 4 | 50.0% | 15.0% to 85.0% |
| payment_methods | 4 | 50.0% | 15.0% to 85.0% |
| invoice | 4 | 50.0% | 15.0% to 85.0% |
| offline_download | 4 | 50.0% | 15.0% to 85.0% |
| gift | 4 | 50.0% | 15.0% to 85.0% |
| devices | 4 | 50.0% | 15.0% to 85.0% |
| double_charge | 4 | 50.0% | 15.0% to 85.0% |
| referral | 4 | 50.0% | 15.0% to 85.0% |
| discounts | 4 | 50.0% | 15.0% to 85.0% |
| pricing | 4 | 75.0% | 30.1% to 95.4% |
| password | 4 | 75.0% | 30.1% to 95.4% |
| mobile_app | 4 | 75.0% | 30.1% to 95.4% |
| exam_retake | 4 | 75.0% | 30.1% to 95.4% |
| assignments | 4 | 75.0% | 30.1% to 95.4% |
| tax | 4 | 75.0% | 30.1% to 95.4% |
| trial | 4 | 75.0% | 30.1% to 95.4% |
| course_language | 4 | 75.0% | 30.1% to 95.4% |
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
