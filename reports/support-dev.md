# Chatbot evaluation: Support bot, development set

**Decision: GO** · bot `support-bot` · golden set `cf943a5e20f6` · 1769 cases

Pass rate **98.8%** (95% interval 98.1% to 99.2%) · language match 100.0% · critical failures **0**

## Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Overall pass rate | 98.8% | >= 90.0% | pass |
| Answer language matches the question | 100.0% | >= 98.0% | pass |
| Critical failures (leaks, failed safety cases) | 0 | <= 0 | pass |
| p95 response time | 65 ms | <= 8000 ms | pass |
| Dialect: maghrebi | 96.7% | >= 80.0% | pass |
| Dialect: franco | 98.1% | >= 80.0% | pass |
| Dialect: gulf | 98.8% | >= 80.0% | pass |
| Dialect: msa | 98.8% | >= 80.0% | pass |
| Dialect: levantine | 99.2% | >= 80.0% | pass |
| Dialect: egyptian | 99.2% | >= 80.0% | pass |
| Dialect: mixed | 99.6% | >= 80.0% | pass |
| Dialect: english | 100.0% | >= 80.0% | pass |
| Intent: course_access | 93.8% | >= 80.0% | pass |
| Intent: thanks | 94.9% | >= 80.0% | pass |
| Intent: password | 96.2% | >= 80.0% | pass |
| Intent: payment | 96.2% | >= 80.0% | pass |
| Intent: payment_methods | 97.4% | >= 80.0% | pass |
| Intent: community | 97.5% | >= 80.0% | pass |
| Intent: vague | 98.6% | >= 80.0% | pass |
| Intent: human_agent | 98.7% | >= 80.0% | pass |
| Intent: pricing | 98.8% | >= 80.0% | pass |
| Intent: refund | 100.0% | >= 80.0% | pass |
| Intent: certificate | 100.0% | >= 80.0% | pass |
| Intent: live_sessions | 100.0% | >= 80.0% | pass |
| Intent: security | 100.0% | >= 80.0% | pass |
| Intent: mobile_app | 100.0% | >= 80.0% | pass |
| Intent: cancellation | 100.0% | >= 80.0% | pass |
| Intent: video | 100.0% | >= 80.0% | pass |
| Intent: upgrade_plan | 100.0% | >= 80.0% | pass |
| Intent: invoice | 100.0% | >= 80.0% | pass |
| Intent: account_email | 100.0% | >= 80.0% | pass |
| Intent: data_deletion | 100.0% | >= 80.0% | pass |
| Intent: complaint | 100.0% | >= 80.0% | pass |
| Intent: out_of_scope | 100.0% | >= 80.0% | pass |

## Why answers failed

| Reason | Cases |
|---|---|
| behavior | 21 |
| content | 16 |

## By dialect

| dialect | Cases | Pass rate | 95% interval |
|---|---|---|---|
| maghrebi | 241 | 96.7% | 93.6% to 98.3% |
| franco | 154 | 98.1% | 94.4% to 99.3% |
| gulf | 246 | 98.8% | 96.5% to 99.6% |
| msa | 247 | 98.8% | 96.5% to 99.6% |
| levantine | 241 | 99.2% | 97.0% to 99.8% |
| egyptian | 246 | 99.2% | 97.1% to 99.8% |
| mixed | 234 | 99.6% | 97.6% to 99.9% |
| english | 160 | 100.0% | 97.7% to 100.0% |

## By intent

| intent | Cases | Pass rate | 95% interval |
|---|---|---|---|
| course_access | 80 | 93.8% | 86.2% to 97.3% |
| thanks | 78 | 94.9% | 87.5% to 98.0% |
| password | 80 | 96.2% | 89.5% to 98.7% |
| payment | 80 | 96.2% | 89.5% to 98.7% |
| payment_methods | 78 | 97.4% | 91.1% to 99.3% |
| community | 79 | 97.5% | 91.2% to 99.3% |
| vague | 74 | 98.6% | 92.7% to 99.8% |
| human_agent | 77 | 98.7% | 93.0% to 99.8% |
| pricing | 84 | 98.8% | 93.6% to 99.8% |
| refund | 84 | 100.0% | 95.6% to 100.0% |
| certificate | 84 | 100.0% | 95.6% to 100.0% |
| live_sessions | 84 | 100.0% | 95.6% to 100.0% |
| security | 84 | 100.0% | 95.6% to 100.0% |
| mobile_app | 83 | 100.0% | 95.6% to 100.0% |
| cancellation | 80 | 100.0% | 95.4% to 100.0% |
| video | 80 | 100.0% | 95.4% to 100.0% |
| upgrade_plan | 80 | 100.0% | 95.4% to 100.0% |
| invoice | 80 | 100.0% | 95.4% to 100.0% |
| account_email | 80 | 100.0% | 95.4% to 100.0% |
| data_deletion | 80 | 100.0% | 95.4% to 100.0% |
| complaint | 80 | 100.0% | 95.4% to 100.0% |
| out_of_scope | 80 | 100.0% | 95.4% to 100.0% |

## Examples of failures

| Case | Question | Answer | Why |
|---|---|---|---|
| GS-0155 (mixed) | الـ monthly plan باكم؟ | يمكنك تغيير الباقة في أي وقت من الإعدادات ثم الاشتراك: الترقية تبدأ فورًا، والانتقال إلى خطة أقل يبدأ من التجديد القادم. | content |
| GS-0337 (gulf) | نسيت كلمة اسلر، وش أسوي؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0348 (levantine) | نسيت كلمة اسلر، شو بعمل؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0370 (msa) | نسيت كلمة الرمور، ماذا أفعل؟ | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
| GS-0467 (franco) | el daf3 msh rady yetem | هل يمكنك أن توضح أكثر؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك. | behavior, content |
