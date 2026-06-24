# 5. Setup Guide — Path A (No-code), step by step

Goal: a working FlowBase CRM you can sell, in roughly a day, at £0. Follow in
order. Times are rough.

## Step 0 — Accounts to create (15 min, all free)
- [ ] **NocoDB Cloud** account (app.nocodb.com) — or Baserow.
- [ ] **Make.com** free account (or self-host n8n later).
- [ ] **Cal.com** free account.
- [ ] **Brevo** free account (for email) + verify a sender address.
- [ ] **PayPal Business** account (see `07-paypal-integration.md`).
- [ ] **Google** account (for Looker Studio dashboards + Drive backups).

## Step 1 — Build the database (45 min)
1. In NocoDB create a **Base** template called `FlowBase CRM Template`.
2. Add tables matching `db/schema.sql`: `contacts`, `tags`, `pipelines`*,
   `deals`, `activities`, `tasks`, `calendar_events`, `payments`. (In no-code you
   can skip `custom_fields` — just add columns directly; and `accounts`/`users`
   are handled by giving each client their **own copy** of this base — see Step 6.)
   *Pipelines = a single-select `stage` column on `deals`.
3. On `deals`, create a **Kanban view** grouped by `stage` → this is the visual
   pipeline board. Add a `value` currency column.
4. On `contacts`, add the GDPR columns: `consent_marketing` (checkbox),
   `consent_source`, `consent_at` (date), `lawful_basis` (single-select).
5. Create a **Form view** on `contacts` for lead capture; note its share URL.

## Step 2 — Dashboards (20 min)
1. Open **Looker Studio** → Create → Data source → connect to NocoDB (via its
   API/CSV connector) or to a Google Sheet that NocoDB syncs to.
2. Build 4 tiles: **Leads this month**, **Conversion rate** (won ÷ closed),
   **Pipeline value** (sum of open deal value), **Activity by day**.
3. Share the dashboard link (view-only) — you'll give each client their own.

## Step 3 — Automations (1–2 h) — see `04-workflows-automation.md`
Build these scenarios in Make (or n8n):
1. **W1 New lead intake** — NocoDB form webhook → create contact → create
   "follow up in 24h" task → Brevo welcome email.
2. **W3 Task reminders** — schedule every 15 min → email overdue task owners.
3. **W5/W6 PayPal** — PayPal webhook → update `payments` + client status (this
   is the money path; test in PayPal sandbox first).
4. **W8 Backups** — daily NocoDB export → Google Drive.

## Step 4 — Calendar (15 min)
1. In Cal.com connect your Google/Outlook calendar.
2. Create a "Discovery call" 30-min event type; copy the booking link.
3. Add the W4 webhook so bookings log into `activities`.

## Step 5 — PayPal (30 min)
Follow `07-paypal-integration.md` exactly: create the £99/month plan, get the
subscribe button/link, and wire the webhook into your Make scenario.

## Step 6 — Make it sellable / multi-client (30 min)
Two no-code options for keeping clients isolated:
- **Simplest:** **duplicate the `FlowBase CRM Template` base per client.** Each
  client logs into their own NocoDB base; you're the workspace owner. Clean
  isolation, zero code. Best for the first ~20–30 clients.
- **Single shared base:** add an `account` column to every table and give each
  client a filtered view. Less duplication but you must be disciplined about
  filters — only do this if you're comfortable with it.

## Step 7 — Launch checklist
- [ ] Sandbox PayPal payment flows end-to-end into `payments`.
- [ ] Submit a test lead → confirm contact + task + welcome email fire.
- [ ] Confirm a backup file lands in Drive.
- [ ] Create your sales sheet + booking link.
- [ ] Onboard yourself as "client zero" and use it for a week before selling.
