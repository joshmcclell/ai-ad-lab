# 11. Scaling Without Increasing Your Time

The whole system is designed so adding a client adds **near-zero** ongoing work.
The trick is: payment, provisioning, follow-ups, backups, and compliance all run
on automation, not on you.

## What stays constant as clients grow (automated)
- **Provisioning** — PayPal payment auto-creates the tenant (W5).
- **Billing & status** — webhooks keep every account's payment status current
  (W5/W6) + the daily reconciliation safety net (W9).
- **Follow-ups & reminders** — W3 runs for every tenant on a schedule.
- **Backups** — W8 dumps everything nightly regardless of client count.
- **GDPR retention** — W7 sweeps all tenants nightly.

## What grows with clients (and how to keep it flat)
| Grows with clients | Keep it flat by… |
|--------------------|------------------|
| Onboarding time | Pre-recorded walkthrough video + templated emails + CSV self-import (`09-client-onboarding.md`) |
| Support questions | A short FAQ/help doc + the walkthrough video; batch support to set times |
| Free-tier limits | Self-host the capped tools (below) |
| Pipeline tweaks | Ship sensible default stages; only customise on request |

## Free-tier ceilings and the £0 way past each

| Limit | Bites at roughly | Free fix |
|-------|------------------|----------|
| Supabase 500 MB DB | Hundreds of active tenants | Self-host Postgres on the Oracle Always Free VM (unlimited) |
| Make 1,000 ops/mo | ~A few dozen busy tenants | Switch automation to **self-hosted n8n** (unlimited, free) |
| Brevo 300 emails/day | High email volume | Self-host email or rotate to another free tier; throttle non-urgent mail |
| NocoDB Cloud (Path A) | Many duplicated bases | Self-host NocoDB on the free VM |

> The pattern: every paid ceiling has a **self-hosted open-source equivalent**
> that removes the cap at the cost of running one free VM. Plan to self-host
> n8n early — it's the highest-leverage move.

## Tiering for more revenue per hour (optional)
Keep the £99 core, add higher tiers that are still mostly automated:
- **£99 Core** — everything in `08-service-summary.md`.
- **£199 Plus** — more users, priority support, custom dashboard.
- **£399 Pro** — multiple pipelines, deeper integrations, quarterly review.
Higher tiers raise revenue without proportionally raising your time, because the
platform does the work.

## The "10-minutes-a-day" operating routine
1. Skim the **admin dashboard**: any `past_due` accounts? (W6/W9 surface them.)
2. Clear any **support emails** (batched).
3. Check the **nightly backup** succeeded (W8 alerts on failure — usually nothing).
4. Everything else — new signups, payments, follow-ups, retention — already ran
   without you.

## When to hire/outsource
Only when support volume (not provisioning) exceeds your batch time. The first
hire is part-time support, not ops — because ops is automated.
