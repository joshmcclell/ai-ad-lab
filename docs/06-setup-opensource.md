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
2. Apply the schema:
   ```bash
   psql "$DATABASE_URL" -f db/schema.sql
   psql "$DATABASE_URL" -f db/seed.sql        # demo tenant + default pipeline
   psql "$DATABASE_URL" -f db/policies.sql    # tenant isolation via RLS
   ```
3. In Supabase → Authentication, enable email logins. When a user signs up,
   store their `auth.users.id` into `users.auth_uid` (a trigger or your app's
   signup handler) so `current_account_id()` / RLS resolve correctly.

## Step 2 — Frontend (1–2 h)
1. `npx create-next-app@latest flowbase-web` and deploy to Vercel.
2. Add `@supabase/supabase-js`; use the project URL + anon key.
3. Because RLS is on, the client SDK automatically scopes every query to the
   signed-in user's tenant — build screens for: contacts list, contact detail
   (with `activities` timeline), Kanban board over `deals`, tasks, and a
   dashboard reading the `v_pipeline_value` / `v_conversion` / `v_activity_daily`
   views (Supabase realtime keeps them live).
4. (Optional) Skip building dashboards by pointing **Metabase** at the same
   Postgres instead.

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
For each new paying client, one script/n8n flow does:
1. `insert into accounts(...)` → new tenant.
2. Create default `pipelines` + `stages` (copy from seed).
3. Create the client's first `users` row + send a Supabase invite.
4. Create default `data_retention_policies`.
5. Email them their login + booking link.
(See `09-client-onboarding.md` — this is the step you automate to scale.)

## Step 8 — Launch checklist
- [ ] RLS verified: a tenant user cannot read another tenant's rows.
- [ ] PayPal sandbox subscription → `payments` + `accounts.status='active'`.
- [ ] Lead form → contact + task + email.
- [ ] `pg_dump` backup lands in storage.
- [ ] Retention sweep runs without touching in-retention data.
