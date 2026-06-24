# FlowBase CRM — Application (Next.js + Supabase)

The open-source build path from `../docs/06-setup-opensource.md`, implemented.
A multi-tenant CRM UI plus the PayPal billing webhook, backed by the Postgres
schema in `../db/`.

## Stack

- **Next.js 14** (App Router) + **TypeScript** + **Tailwind**
- **Supabase** — Postgres + Auth; tenant isolation enforced by RLS (`../db/policies.sql`)
- **PayPal** — recurring £99 subscription webhook (`src/app/api/paypal/webhook/route.ts`)

## What's implemented

| Route | Purpose |
|-------|---------|
| `/login` | Magic-link sign-in (Supabase OTP) |
| `/dashboard` | KPIs from the `v_pipeline_value` / `v_conversion` views |
| `/contacts`, `/contacts/[id]` | Contact list + detail with activity timeline and "log a note" |
| `/pipeline` | Visual board: deals grouped by stage, move via server action |
| `/tasks` | Open tasks with overdue flag; mark done |
| `/admin` | Operator console (platform-admin only): provision clients, view all tenants + MRR |
| `/api/paypal/webhook` | Verifies PayPal signatures; auto-provisions on activation; updates subscriptions/payments/accounts |

Every data read/write goes through the RLS-scoped Supabase client, so a signed-in
user only ever sees their own tenant. The PayPal webhook is the one deliberate
exception: it uses the service-role client (`src/lib/supabase/admin.ts`) because
it must update billing across tenants — it is never imported by client code.

## Run locally

```bash
cp .env.example .env.local      # fill in Supabase + PayPal values
npm install
# Apply the database first (from repo root):
#   psql "$DATABASE_URL" -f ../db/schema.sql
#   psql "$DATABASE_URL" -f ../db/seed.sql
#   psql "$DATABASE_URL" -f ../db/functions.sql
#   psql "$DATABASE_URL" -f ../db/policies.sql
npm run dev                     # http://localhost:3000
```

`npm run build` and `npm run typecheck` both pass.

## Connecting the PayPal webhook

Point your PayPal webhook (docs/07) at `https://<your-domain>/api/paypal/webhook`
and subscribe to `BILLING.SUBSCRIPTION.*` and `PAYMENT.SALE.COMPLETED`. Set
`PAYPAL_WEBHOOK_ID` so signatures verify. The handler is idempotent on PayPal
transaction ids.

## Security & versions

This scaffold pins **Next.js 14.2.35** (latest 14.2.x). `npm audit` still reports
advisories that are only resolved in the Next 15/16 lines (a major upgrade):
- Several do **not** apply to this app: the Image Optimization DoS (no `next/image`
  use) and the Pages-Router i18n middleware bypass (this app is App-Router only,
  no i18n).
- Before a real production launch, plan an upgrade to a current Next major (note
  Next 15+ makes `cookies()`/`headers()` async — `src/lib/supabase/server.ts`
  and the server components would need `await`) and track Next security releases.
