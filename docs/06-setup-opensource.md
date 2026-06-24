# 6. Setup Guide — Path B (Open-source), step by step

Full control, unlimited, £0 license fees. Uses the SQL in `db/`. Assumes basic
comfort with a terminal.

## Step 0 — Accounts/tools (15 min)
- [ ] **Supabase** project (free) — supabase.com.
- [ ] **Vercel** account (free) for the Next.js frontend.
- [ ] An **Oracle Cloud Always Free** VM (or Railway/Render free) for n8n + Cal.com.
- [ ] **Brevo** + **PayPal Business** accounts.
- [ ] `psql` installed locally (or use the Supabase SQL editor).

## Step 1 — Database (20 min)
1. Create a Supabase project; grab the connection string (`DATABASE_URL`).
2. Apply the database:
   ```bash
   psql "$DATABASE_URL" -f db/schema.sql
   psql "$DATABASE_URL" -f db/seed.sql        # demo tenant + default pipeline
   psql "$DATABASE_URL" -f db/functions.sql   # provision_account(), etc.
   psql "$DATABASE_URL" -f db/policies.sql    # tenant isolation via RLS
   ```
   Optionally run `db/test/run-tests.sh` first to confirm the SQL is healthy.
3. In Supabase → Authentication, enable email logins. When a user signs up,
   store their `auth.users.id` into `users.auth_uid` (a trigger or your app's
   signup handler) so `current_account_id()` / RLS resolve correctly.

## Step 2 — Frontend (1–2 h)
The app in `app/` already implements this (it builds and type-checks). To use it
as-is: `cd app`, copy `.env.example` to `.env.local`, fill in the Supabase +
PayPal values, `npm install`, then `npm run dev` (deploy to Vercel for prod).

It ships: magic-link auth, a dashboard over the `v_pipeline_value` /
`v_conversion` views, contacts list + detail with the `activities` timeline, a
pipeline board over `deals`, tasks, an **operator console** (`/admin`) for
provisioning clients, and the PayPal webhook. Because RLS is on, every query is
automatically scoped to the signed-in user's tenant. (Prefer to build your own
or use Metabase for dashboards? The schema supports it.)

## Step 3 — Automation engine (45 min)
1. On your free VM, run n8n via Docker:
   ```bash
   docker run -d --restart unless-stopped -p 5678:5678 \
     -e N8N_HOST=<your-host> -e WEBHOOK_URL=https://<your-host>/ \
     -v n8n_data:/home/node/.n8n n8nio/n8n
   ```
2. Add Postgres credentials (your Supabase connection) in n8n.
3. Build the workflows from `04-workflows-automation.md` (start with W5/W6 PayPal,
   then W1, W3, W7, W8).

## Step 4 — Scheduling (20 min)
Run Cal.com (cloud free, or self-host on the same VM via Docker Compose), connect
your calendar, and point its booking webhook at n8n (W4).

## Step 5 — PayPal (30 min)
Follow `07-paypal-integration.md`. Webhook target = your n8n W5/W6 webhook URL
(or a Supabase Edge Function if you prefer code).

## Step 6 — Backups & retention (20 min)
- W8: a daily n8n cron node runs `pg_dump` and uploads to Backblaze B2 (10 GB
  free) or Supabase Storage. Keep 7–30 days.
- W7: a daily n8n cron applies `data_retention_policies` (anonymise/delete).

## Step 7 — New-tenant provisioning (the "add a client" routine)
This is built. A single atomic DB function, `provision_account()`
(`db/functions.sql`), creates the tenant + default pipeline & stages + retention
policies + owner user in one transaction. It is the **only** supported way to
create a tenant (a bare `insert into accounts` would skip the defaults).

Three ways it runs:
- **Operator console** — sign in as a platform admin and use `/admin` to add a
  client by name + owner email.
- **Self-serve via PayPal** — on `BILLING.SUBSCRIPTION.ACTIVATED`, the webhook
  (`app/src/app/api/paypal/webhook/route.ts`) auto-provisions from the
  subscriber's details if no tenant exists yet.
- **Script / SQL** — `select provision_account('Acme Ltd', 'jane@acme.co', 'Jane');`

After provisioning, send the owner a Supabase magic-link invite + the booking
link (see `09-client-onboarding.md`).

## Step 8 — Launch checklist
- [ ] `db/test/run-tests.sh` is green (seed idempotency, provisioning, RLS).
- [ ] RLS verified: a tenant user cannot read another tenant's rows.
- [ ] PayPal sandbox subscription → tenant provisioned + `accounts.status='active'`.
- [ ] Lead form → contact + task + email.
- [ ] `pg_dump` backup lands in storage.
- [ ] Retention sweep runs without touching in-retention data.
