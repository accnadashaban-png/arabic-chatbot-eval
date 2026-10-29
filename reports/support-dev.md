# Chatbot evaluation: Support bot, development set

**Decision: GO** · bot `support-bot` · golden set `19583ed536e0` · 3613 cases

Pass rate **98.9%** (95% interval 98.5% to 99.2%) · language match 100.0% · critical failures **0**

## Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Overall pass rate | 98.9% | >= 90.0% | pass |
| Answer language matches the question | 100.0% | >= 98.0% | pass |
| Critical failures (leaks, failed safety cases) | 0 | <= 0 | pass |
| p95 response time | 80 ms | <= 8000 ms | pass |
| Dialect: maghrebi | 96.8% | >= 80.0% | pass |
| Dialect: levantine | 98.8% | >= 80.0% | pass |
| Dialect: msa | 98.8% | >= 80.0% | pass |
| Dialect: franco | 99.0% | >= 80.0% | pass |
| Dialect: egyptian | 99.2% | >= 80.0% | pass |
| Dialect: gulf | 99.4% | >= 80.0% | pass |
| Dialect: mixed | 99.6% | >= 80.0% | pass |
| Dialect: english | 100.0% | >= 80.0% | pass |
| Intent: assignments | 92.5% | >= 80.0% | pass |
| Intent: course_access | 93.8% | >= 80.0% | pass |
| Intent: thanks | 94.9% | >= 80.0% | pass |
| Intent: team_plan | 95.2% | >= 80.0% | pass |
| Intent: password | 96.2% | >= 80.0% | pass |
| Intent: payment | 96.2% | >= 80.0% | pass |
| Intent: support_hours | 96.2% | >= 80.0% | pass |
| Intent: payment_methods | 97.4% | >= 80.0% | pass |
| Intent: progress | 97.5% | >= 80.0% | pass |
| Intent: vague | 98.6% | >= 80.0% | pass |
| Intent: human_agent | 98.7% | >= 80.0% | pass |
| Intent: certificate_verify | 98.7% | >= 80.0% | pass |
| Intent: offline_download | 98.8% | >= 80.0% | pass |
| Intent: become_instructor | 98.8% | >= 80.0% | pass |
| Intent: course_request | 98.8% | >= 80.0% | pass |
| Intent: scholarship | 98.8% | >= 80.0% | pass |
| Intent: pricing | 98.8% | >= 80.0% | pass |
| Intent: refund | 100.0% | >= 80.0% | pass |
| Intent: certificate | 100.0% | >= 80.0% | pass |
| Intent: live_sessions | 100.0% | >= 80.0% | pass |
| Intent: security | 100.0% | >= 80.0% | pass |
| Intent: gift | 100.0% | >= 80.0% | pass |
| Intent: exam_retake | 100.0% | >= 80.0% | pass |
| Intent: mobile_app | 100.0% | >= 80.0% | pass |
| Intent: cancellation | 100.0% | >= 80.0% | pass |
| Intent: video | 100.0% | >= 80.0% | pass |
| Intent: upgrade_plan | 100.0% | >= 80.0% | pass |
| Intent: invoice | 100.0% | >= 80.0% | pass |
| Intent: account_email | 100.0% | >= 80.0% | pass |
| Intent: data_deletion | 100.0% | >= 80.0% | pass |
| Intent: complaint | 100.0% | >= 80.0% | pass |
| Intent: out_of_scope | 100.0% | >= 80.0% | pass |
| Intent: learning_path | 100.0% | >= 80.0% | pass |
| Intent: account_security | 100.0% | >= 80.0% | pass |
| Intent: tax | 100.0% | >= 80.0% | pass |
| Intent: double_charge | 100.0% | >= 80.0% | pass |
| Intent: course_expiry | 100.0% | >= 80.0% | pass |
| Intent: referral | 100.0% | >= 80.0% | pass |
| Intent: course_language | 100.0% | >= 80.0% | pass |
| Intent: community | 100.0% | >= 80.0% | pass |
| Intent: pause_subscription | 100.0% | >= 80.0% | pass |
| Intent: devices | 100.0% | >= 80.0% | pass |
| Intent: mentoring | 100.0% | >= 80.0% | pass |
| Intent: discounts | 100.0% | >= 80.0% | pass |
| Intent: trial | 100.0% | >= 80.0% | pass |

## Why answers failed

| Reason | Cases |
|---|---|
| behavior | 24 |
| content | 34 |

## By dialect

| dialect | Cases | Pass rate | 95% interval |
|---|---|---|---|
| maghrebi | 494 | 96.8% | 94.8% to 98.0% |
| levantine | 494 | 98.8% | 97.4% to 99.4% |
| msa | 502 | 98.8% | 97.4% to 99.5% |
| franco | 315 | 99.0% | 97.2% to 99.7% |
| egyptian | 502 | 99.2% | 98.0% to 99.7% |
| gulf | 502 | 99.4% | 98.3% to 99.8% |
| mixed | 480 | 99.6% | 98.5% to 99.9% |
| english | 324 | 100.0% | 98.8% to 100.0% |

## By intent

| intent | Cases | Pass rate | 95% interval |
|---|---|---|---|
| assignments | 80 | 92.5% | 84.6% to 96.5% |
| course_access | 80 | 93.8% | 86.2% to 97.3% |
| thanks | 78 | 94.9% | 87.5% to 98.0% |
| team_plan | 83 | 95.2% | 88.3% to 98.1% |
| password | 80 | 96.2% | 89.5% to 98.7% |
| payment | 80 | 96.2% | 89.5% to 98.7% |
| support_hours | 80 | 96.2% | 89.5% to 98.7% |
| payment_methods | 78 | 97.4% | 91.1% to 99.3% |
| progress | 80 | 97.5% | 91.3% to 99.3% |
| vague | 74 | 98.6% | 92.7% to 99.8% |
| human_agent | 77 | 98.7% | 93.0% to 99.8% |
| certificate_verify | 79 | 98.7% | 93.2% to 99.8% |
| offline_download | 80 | 98.8% | 93.3% to 99.8% |
| become_instructor | 80 | 98.8% | 93.3% to 99.8% |
| course_request | 80 | 98.8% | 93.3% to 99.8% |
| scholarship | 80 | 98.8% | 93.3% to 99.8% |
| pricing | 84 | 98.8% | 93.6% to 99.8% |
| refund | 84 | 100.0% | 95.6% to 100.0% |
| certificate | 84 | 100.0% | 95.6% to 100.0% |
| live_sessions | 84 | 100.0% | 95.6% to 100.0% |
| security | 84 | 100.0% | 95.6% to 100.0% |
| gift | 84 | 100.0% | 95.6% to 100.0% |
| exam_retake | 84 | 100.0% | 95.6% to 100.0% |
| mobile_app | 83 | 100.0% | 95.6% to 100.0% |
| cancellation | 80 | 100.0% | 95.4% to 100.0% |
| video | 80 | 100.0% | 95.4% to 100.0% |
| upgrade_plan | 80 | 100.0% | 95.4% to 100.0% |
| invoice | 80 | 100.0% | 95.4% to 100.0% |
| account_email | 80 | 100.0% | 95.4% to 100.0% |
| data_deletion | 80 | 100.0% | 95.4% to 100.0% |
| complaint | 80 | 100.0% | 95.4% to 100.0% |
| out_of_scope | 80 | 100.0% | 95.4% to 100.0% |
| learning_path | 80 | 100.0% | 95.4% to 100.0% |
| account_security | 80 | 100.0% | 95.4% to 100.0% |
| tax | 80 | 100.0% | 95.4% to 100.0% |
| double_charge | 80 | 100.0% | 95.4% to 100.0% |
| course_expiry | 80 | 100.0% | 95.4% to 100.0% |
| referral | 80 | 100.0% | 95.4% to 100.0% |
| course_language | 80 | 100.0% | 95.4% to 100.0% |
| community | 79 | 100.0% | 95.4% to 100.0% |
| pause_subscription | 79 | 100.0% | 95.4% to 100.0% |
| devices | 79 | 100.0% | 95.4% to 100.0% |
| mentoring | 79 | 100.0% | 95.4% to 100.0% |
| discounts | 79 | 100.0% | 95.4% to 100.0% |
| trial | 78 | 100.0% | 95.3% to 100.0% |

## Examples of failures

| Case | Question | Answer | Why |
|---|---|---|---|
| GS-0155 (mixed) | الـ monthly plan باكم؟ | يمكنك تغيير الباقة في أي وقت من الإعدادات ثم الاشتراك: الترقية تبدأ فورًا، والانتقال إلى خطة أقل يبدأ من التجديد القادم. | content |
| GS-0337 (gulf) | نسيت كلمة اسلر، وش أسوي؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0348 (levantine) | نسيت كلمة اسلر، شو بعمل؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0370 (msa) | نسيت كلمة الرمور، ماذا أفعل؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0467 (franco) | el daf3 msh rady yetem | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
