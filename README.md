# FlowBase CRM

A simplified, automated CRM sold as a **£99/month** managed service to small
businesses, freelancers, startups, and service providers. Built to run on **free
tiers and open-source software** (£0 build cost, £0 fixed running cost), with all
retainer payments flowing directly into your **PayPal** account.

This repository contains the **complete blueprint plus working build artifacts**
to launch the business.

## What's here

| Path | What it is |
|------|-----------|
| `docs/01-business-and-branding.md` | Name, pricing, branding guidance |
| `docs/02-tech-stack.md` | All free tools — No-code (Path A) and Open-source (Path B) |
| `docs/03-data-model.md` | Database/field structure & workflow design, in plain English |
| `docs/04-workflows-automation.md` | The automations (W1–W9) that keep daily workload near zero |
| `docs/05-setup-nocode.md` | Step-by-step launch on the No-code stack |
| `docs/06-setup-opensource.md` | Step-by-step launch on the Open-source stack |
| `docs/07-paypal-integration.md` | Connect PayPal recurring £99 retainer + auto-tracking |
| `docs/08-service-summary.md` | Exactly what the £99/month includes (sales-ready copy) |
| `docs/09-client-onboarding.md` | Sign-up → live client onboarding flow |
| `docs/10-gdpr-uk.md` | UK GDPR & data-protection setup |
| `docs/11-scaling.md` | Add clients without adding time |
| `db/schema.sql` | PostgreSQL schema — the multi-tenant backbone (validated) |
| `db/seed.sql` | Demo tenant + default pipeline + sample data (idempotent) |
| `db/policies.sql` | Row-Level Security: per-tenant isolation (validated) |
| `app/` | **The running application** — Next.js + Supabase CRM + PayPal webhook (builds & type-checks) |
| `n8n/` | Importable automation workflows (lead intake, task reminders) |

## Quick start (open-source path)

```bash
# Any PostgreSQL 14+ (e.g. a free Supabase project)
psql "$DATABASE_URL" -f db/schema.sql     # tables, views, triggers
psql "$DATABASE_URL" -f db/seed.sql        # demo tenant + default pipeline
psql "$DATABASE_URL" -f db/policies.sql    # tenant isolation via RLS
```

Then run the app:

```bash
cd app
cp .env.example .env.local      # Supabase + PayPal credentials
npm install
npm run dev                      # http://localhost:3000
```

See `app/README.md` for the application details and `docs/06-setup-opensource.md`
for the full deployment walkthrough. Prefer no servers? Start with
`docs/05-setup-nocode.md` instead.

## Two build paths — pick one

- **No-code (recommended to launch fast):** NocoDB + Make/n8n + Cal.com + Brevo +
  Looker Studio + PayPal. Lowest maintenance.
- **Open-source (full control):** Supabase (Postgres + Auth + RLS) + Next.js +
  self-hosted n8n + Cal.com + PayPal. The SQL in `db/` targets this path.

See `docs/02-tech-stack.md` for the full list and honest notes on free-tier limits.

> Note on costs: the software is free; PayPal charges a per-transaction fee out of
> revenue (you net ~£95–96 of each £99), and a custom domain (~£10/yr) is optional.
> See `docs/02-tech-stack.md`.
